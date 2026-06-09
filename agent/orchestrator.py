from agent.jsonrpc.client import JSONRPCClient
from agent.mcp_adapters.gitlab import GitLabAdapter
from agent.mcp_adapters.mongodb import MongoDBAdapter
from agent.mcp_adapters.fivetran import FivetranAdapter
from agent.mcp_adapters.arize import ArizeAdapter
from agent.schemas.handshake import Handshake, Stage
import time
import uuid
from typing import Optional
from agent import config


class Orchestrator:
    def __init__(
        self,
        dynatrace_endpoint: str,
        elastic_endpoint: str,
        gitlab_endpoint: str = None,
        mongodb_endpoint: str = None,
        fivetran_endpoint: str = None,
        arize_endpoint: str = None,
        *,
        signing_key: str = None,
        audit_log_path: str = None,
        agent_id: str = "agent-orchestrator",
    ):
        # Shared identity for every JSON-RPC client we own
        common = dict(agent_id=agent_id, signing_key=signing_key, audit_log_path=audit_log_path)
        self.dt_client = JSONRPCClient(dynatrace_endpoint, **common)
        self.es_client = JSONRPCClient(elastic_endpoint, **common)
        self.gitlab = GitLabAdapter(gitlab_endpoint, **common) if gitlab_endpoint else None
        self.mongodb = MongoDBAdapter(mongodb_endpoint, **common) if mongodb_endpoint else None
        self.fivetran = FivetranAdapter(fivetran_endpoint, **common) if fivetran_endpoint else None
        self.arize = ArizeAdapter(arize_endpoint, **common) if arize_endpoint else None
        self.agent_id = agent_id

    # ── Handshake-aware stages ────────────────────────────────────────────────
    def stage1_ingest(self, alert_id: str) -> Handshake:
        """Stage 1: ask Dynatrace for topology; produce a Handshake."""
        params = {"action": "query_topology", "payload": {"alert_id": alert_id}}
        result = self.dt_client.call_method("mcp.exec", params)
        h = Handshake.from_stage1(
            alert_id=alert_id,
            service_id=result.get("service_id", "unknown-svc"),
            pod_id=result.get("pod_id", "unknown-pod"),
            time_window=result.get("time_window", "now"),
            container_signature=result.get("container_signature"),
            agent_id=self.agent_id,
        )
        return h

    def stage2_logs(self, h: Handshake) -> Handshake:
        """Stage 2: query Elastic logs based on the Stage-1 Handshake."""
        params = h.to_json_rpc_params("search_logs")
        result = self.es_client.call_method("mcp.exec", params)
        h.error_string = result.get("error_string")
        h.file_path = result.get("file_path")
        h.line_number = result.get("line_number")
        h.sample_log_entries = result.get("sample_log_entries", [])
        h.record_stage(Stage.LOGS, f"matched error in {h.file_path}")
        return h

    def stage3_git_remediation(self, h: Handshake) -> Handshake:
        if not self.gitlab:
            raise RuntimeError("GitLab endpoint not configured")
        if not h.file_path:
            raise ValueError("Handshake has no file_path — run stage2 first")

        blame_result = self.gitlab.query_blame(h.file_path)
        recent_commits = blame_result.get("recent_commits", [])
        h.suspected_commit_sha = recent_commits[0]["sha"] if recent_commits else "unknown"

        branch_name = f"hotfix/auto/{time.strftime('%Y-%m-%d')}-{self.agent_id[:8]}"
        self.gitlab.create_branch(branch_name, from_sha=h.suspected_commit_sha)

        mr_title = f"[AUTO] Fix: {(h.error_string or '')[:60]}"
        mr_desc = (
            f"Automated hotfix for {h.file_path}\n"
            f"Error: {h.error_string}\n"
            f"Suspected commit: {h.suspected_commit_sha}\n"
            f"Pod: {h.pod_id}\n"
            f"Correlation ID: {h.correlation_id}"
        )
        mr_result = self.gitlab.create_merge_request(branch_name, mr_title, mr_desc)

        h.branch = branch_name
        h.merge_request_url = mr_result.get("merge_request_url")
        h.patch_summary = mr_desc
        h.record_stage(Stage.GIT, f"opened MR {h.merge_request_url}")
        return h

    def stage4_db_stabilize(self, h: Handshake, db: str, collection: str) -> Handshake:
        if not self.mongodb:
            raise RuntimeError("MongoDB endpoint not configured")

        modification = {"validator_action": "warn"}
        # Pass the existing schema_patch if Stage 3 already produced one
        if h.schema_patch:
            modification.update(h.schema_patch)
        # Respect the operator approval gate: if auto-approve is disabled,
        # record the intended change and mark the handshake as awaiting approval.
        if not config.AUTO_APPROVE_SCHEMA_CHANGES:
            h.schema_patch = modification
            h.quarantine_collection = f"{collection}_quarantine"
            h.record_stage(Stage.DB, f"awaiting_approval: collMod pending for {collection}")
            return h

        # Auto-approve path: apply changes and quarantine immediately
        result = self.mongodb.modify_collection_validator(db, collection, modification)
        quarantine = self.mongodb.quarantine_documents(
            db, collection, {"_schema_violation": True}, f"{collection}_quarantine"
        )
        h.schema_patch = modification
        h.quarantine_collection = f"{collection}_quarantine"
        h.record_stage(Stage.DB, f"collMod applied, quarantine={quarantine.get('count', 0)} docs")
        return h

    def approve_stage4(self, h: Handshake, db: str, collection: str) -> Handshake:
        """Operator-approved path to apply a pending collMod and perform quarantine.

        This method should be called after an operator reviews `h.audit_trail` and
        decides to approve the change. It will apply the `h.schema_patch` to the
        provided collection and record the action in the handshake.
        """
        if not h.schema_patch:
            raise ValueError("no pending schema_patch to approve on handshake")
        result = self.mongodb.modify_collection_validator(db, collection, h.schema_patch)
        quarantine = self.mongodb.quarantine_documents(
            db, collection, {"_schema_violation": True}, h.quarantine_collection or f"{collection}_quarantine"
        )
        h.record_stage(Stage.DB, f"approved_and_applied: quarantine={quarantine.get('count', 0)} docs")
        return h

    def stage5_downstream_align(self, h: Handshake, connector_id: str, mapping_changes: dict) -> Handshake:
        if not self.fivetran:
            raise RuntimeError("Fivetran endpoint not configured")
        self.fivetran.adjust_connector(connector_id, mapping_changes)
        resync = self.fivetran.trigger_resync(connector_id)
        h.resync_status = resync.get("status", "unknown")
        h.record_stage(Stage.PIPELINE, f"connector {connector_id} resync={h.resync_status}")
        return h

    def stage6_cognitive_assess(self, h: Handshake) -> Handshake:
        if not self.arize:
            raise RuntimeError("Arize endpoint not configured")
        trace = {
            "trace_id": h.correlation_id,
            "events": [e.model_dump() if hasattr(e, "model_dump") else e
                       for e in h.audit_trail],
        }
        score = self.arize.ingest_trace_and_evaluate(trace)
        report = self.arize.get_compliance_report(score.get("run_id")) if score else {}
        h.compliance_score = report.get("compliance_score")
        h.drift_score = report.get("drift_score")
        h.record_stage(Stage.COGNITIVE, f"compliance={h.compliance_score} drift={h.drift_score}")
        return h

    # ── end-to-end convenience ───────────────────────────────────────────────
    def heal(self, alert_id: str, *, db: str = "demo_db", collection: str = "orders",
             connector_id: str = "connector-123") -> Handshake:
        """Run all 6 stages in sequence, threading a single Handshake through them."""
        h = self.stage1_ingest(alert_id)
        h = self.stage2_logs(h)
        h = self.stage3_git_remediation(h)
        h = self.stage4_db_stabilize(h, db, collection)
        h = self.stage5_downstream_align(h, connector_id, {f"{collection}.amount": "double"})
        h = self.stage6_cognitive_assess(h)
        return h


def run_demo(use_gateway: bool = False):
    if use_gateway:
        endpoint_prefix = "http://127.0.0.1:9003/proxy"
        orch = Orchestrator(endpoint_prefix, endpoint_prefix, endpoint_prefix)
    else:
        orch = Orchestrator(
            "http://127.0.0.1:9001/mcp",
            "http://127.0.0.1:9002/mcp",
            "http://127.0.0.1:9004/mcp",
            "http://127.0.0.1:9005/mcp",
            "http://127.0.0.1:9006/mcp",
            "http://127.0.0.1:9007/mcp",
        )

    print("[orchestrator] Running full 6-stage self-healing loop")
    h = orch.heal("demo-alert-1")
    print(f"[orchestrator] done — correlation_id={h.correlation_id}")
    print(f"[orchestrator] final compliance={h.compliance_score} drift={h.drift_score}")
    print(f"[orchestrator] audit trail entries: {len(h.audit_trail)}")
    return h


if __name__ == "__main__":
    print("Run the demo server(s) first (demo/run_demo.py starts mocks). Sleeping briefly to allow startup.")
    time.sleep(1)
    run_demo()
