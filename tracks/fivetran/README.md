# SENTINEL · Fivetran Track

Hero story: keep warehouse pipelines healthy after upstream schema changes.

See [docs/complete_plan.md](../docs/complete_plan.md) for the full plan and
the cross-track architecture. The shared core engine is in `../agent/` and
the SRE Control Cockpit is in `../ui/cockpit/`.

## Run the demo

```bash
pip install -r ../requirements.txt
cp .env.example .env
python -m demo.run_full_demo
```

Then open the cockpit:

```bash
python -m agent.ui_server
# open http://127.0.0.1:8080
```
