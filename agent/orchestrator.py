from agent.jsonrpc.client import JSONRPCClient
from agent.mcp_adapters.gitlab import GitLabAdapter
from agent.mcp_adapters.mongodb import MongoDBAdapter
from agent.mcp_adapters.fivetran import FivetranAdapter
from agent.mcp_adapters.arize import ArizeAdapter
import time
import uuid


class Orchestrator:
    def __init__(
        self,
        dynatrace_endpoint: str,
        elastic_endpoint: str,
        gitlab_endpoint: str = None,
        mongodb_endpoint: str = None,
        fivetran_endpoint: str = None,
        arize_endpoint: str = None,
    ):
        self.dt_client = JSONRPCClient(dynatrace_endpoint)
        self.es_client = JSONRPCClient(elastic_endpoint)
        self.gitlab = GitLabAdapter(gitlab_endpoint) if gitlab_endpoint else None
        self.mongodb = MongoDBAdapter(mongodb_endpoint) if mongodb_endpoint else None
        self.fivetran = FivetranAdapter(fivetran_endpoint) if fivetran_endpoint else None
        self.arize = ArizeAdapter(arize_endpoint) if arize_endpoint else None

    def stage1_ingest(self, alert_id: str):
        params = {"action": "query_topology", "payload": {"alert_id": alert_id}}
        result = self.dt_client.call_method("mcp.exec", params)
        return result

    def stage2_logs(self, service_name: str, pod_id: str, window: str = None):
        params = {"action": "search_logs", "payload": {"service": service_name, "pod_id": pod_id, "window": window}}
        result = self.es_client.call_method("mcp.exec", params)
        return result

    def stage3_git_remediation(self, error_string: str, file_path: str, pod_id: str):
        if not self.gitlab:
            raise RuntimeError("GitLab endpoint not configured")

        # Query blame to find recent commits
        blame_result = self.gitlab.query_blame(file_path)
        recent_commits = blame_result.get("recent_commits", [])
        suspected_sha = recent_commits[0]["sha"] if recent_commits else "unknown"

        # Create a hotfix branch
        agent_id = str(uuid.uuid4())[:8]
        branch_name = f"hotfix/auto/2026-06-09-{agent_id}"
        branch_result = self.gitlab.create_branch(branch_name, from_sha=suspected_sha)

        # Create a merge request with description
        mr_title = f"[AUTO] Fix: {error_string[:60]}"
        mr_desc = f"Automated hotfix for {file_path}\nError: {error_string}\nSuspected commit: {suspected_sha}\nPod: {pod_id}"
        mr_result = self.gitlab.create_merge_request(branch_name, mr_title, mr_desc)

        return {
            "branch": branch_name,
            "merge_request_url": mr_result.get("merge_request_url"),
            "suspected_commit_sha": suspected_sha,
            "error_string": error_string,
            "file_path": file_path,
        }

    def stage4_db_stabilize(self, db: str, collection: str):
        if not self.mongodb:
            raise RuntimeError("MongoDB endpoint not configured")

        modification = {"validator_action": "warn"}
        result = self.mongodb.modify_collection_validator(db, collection, modification)
        quarantine = self.mongodb.quarantine_documents(db, collection, {"_schema_violation": True}, f"{collection}_quarantine")
        return {"collmod": result, "quarantine": quarantine}

    def stage5_downstream_align(self, connector_id: str, mapping_changes: dict):
        if not self.fivetran:
            raise RuntimeError("Fivetran endpoint not configured")
        adjust = self.fivetran.adjust_connector(connector_id, mapping_changes)
        resync = self.fivetran.trigger_resync(connector_id)
        return {"adjust": adjust, "resync": resync}

    def stage6_cognitive_assess(self, trace: dict):
        if not self.arize:
            raise RuntimeError("Arize endpoint not configured")
        score = self.arize.ingest_trace_and_evaluate(trace)
        report = self.arize.get_compliance_report(score.get("run_id")) if score else {}
        return {"score": score, "report": report}


def run_demo(use_gateway: bool = False):
    if use_gateway:
        # Route through gateway
        endpoint_prefix = "http://127.0.0.1:9003/proxy"
        orch = Orchestrator(endpoint_prefix, endpoint_prefix, endpoint_prefix)
    else:
        # Direct to mocks
        orch = Orchestrator(
            "http://127.0.0.1:9001/mcp",
            "http://127.0.0.1:9002/mcp",
            "http://127.0.0.1:9004/mcp",
            "http://127.0.0.1:9005/mcp",
            "http://127.0.0.1:9006/mcp",
            "http://127.0.0.1:9007/mcp",
        )

    print("[orchestrator] Stage 1: asking Dynatrace for topology")
    dt = orch.stage1_ingest("demo-alert-1")
    print("[orchestrator] Dynatrace result:", dt)

    service = dt.get("service_id")
    pod = dt.get("pod_id")
    window = dt.get("time_window")

    print("[orchestrator] Stage 2: querying Elastic logs")
    es = orch.stage2_logs(service, pod, window)
    print("[orchestrator] Elastic result:", es)

    error_string = es.get("error_string")
    file_path = es.get("file_path")

    print("[orchestrator] Stage 3: GitLab remediation (blame, branch, MR)")
    git = orch.stage3_git_remediation(error_string, file_path, pod)
    print("[orchestrator] GitLab result:", git)

    print("[orchestrator] Stage 4: MongoDB stabilization (collMod & quarantine)")
    db_res = orch.stage4_db_stabilize("demo_db", "orders")
    print("[orchestrator] MongoDB result:", db_res)

    print("[orchestrator] Stage 5: Fivetran downstream alignment")
    fiv = orch.stage5_downstream_align("connector-123", {"orders.amount": "double"})
    print("[orchestrator] Fivetran result:", fiv)

    print("[orchestrator] Stage 6: Cognitive integrity assessment (Arize)")
    trace = {"trace_id": str(uuid.uuid4()), "events": [dt, es, git, db_res, fiv]}
    ar = orch.stage6_cognitive_assess(trace)
    print("[orchestrator] Arize result:", ar)


if __name__ == "__main__":
    print("Run the demo server(s) first (demo/run_demo.py starts mocks). Sleeping briefly to allow startup.")
    time.sleep(1)
    run_demo()
