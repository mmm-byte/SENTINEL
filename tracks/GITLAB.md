# Track 5: GitLab — WIN Proof

## Judging Criteria: Duo Agent Platform + Custom Agents + MCP + AI Catalog

### What We Built

SENTINEL is registered as a GitLab Duo Custom Agent. It opens automated rollback Merge Requests when a schema violation cannot be auto-remediated, and it is callable by GitLab CI pipelines as a native Duo skill.

### 1. GitLab MCP Server (Primary — WIN Condition)

**File:** `agent/.adk/config.json`

```json
"gitlab": {
  "command": "npx",
  "args": ["-y", "@gitlab-org/gitlab-mcp-server"],
  "env": {
    "GITLAB_TOKEN": "${GITLAB_TOKEN}",
    "GITLAB_API_URL": "${GITLAB_API_URL}"
  }
}
```

Gemini calls `create_merge_request`, `search_commits`, and `list_pipelines` as native MCP tools.

### 2. GitLab Duo Custom Agent Registration

**File:** `orchestrator/gitlab_agent.py` — `register_sentinel_as_duo_agent()`

SENTINEL is registered in GitLab’s AI Catalog as a Custom Agent:

```python
{
  "name": "sentinel-schema-guardian",
  "description": "Autonomous MongoDB schema continuity agent. Invoke with: /sentinel analyze-schema-break collection=<name>",
  "system_prompt": "You are SENTINEL..."
}
```

GitLab CI pipelines and MR reviewers can invoke SENTINEL natively via `@gitlab-duo`.

### 3. Automated Rollback MR on ESCALATE

When SENTINEL cannot auto-remediate (status = `ESCALATE`), it opens a GitLab MR with:
- Full violation summary
- Quarantine collection reference
- Duo invocation command for engineers: `/sentinel analyze-schema-break collection=orders`
- Checklist: identify breaking commit → fix producer → restore strict validation → re-trigger Fivetran

### 4. Setup

```bash
npm install -g @gitlab-org/gitlab-mcp-server

export GITLAB_TOKEN=your_personal_access_token  # api + write_repository scopes
export GITLAB_PROJECT_ID=your_project_id
export GITLAB_DUO_NAMESPACE=your_namespace

# Register as Duo Agent (one-time setup)
python -c "from orchestrator.gitlab_agent import register_sentinel_as_duo_agent; print(register_sentinel_as_duo_agent())"
```

---

*SENTINEL · GitLab Track · Google Cloud Rapid Agent Hackathon 2026*
