---
name: e2e-testing
description: Guidance and commands for running Frappe E2E test scripts, tsv clone management, seed rebuilds, and UAT workbooks in connect_diagnostics_setup.
argument-hint: "<command or operation>"
---

# End-to-End (E2E) & Rollout Commands Guide

End-to-end tests (`e2e/`, see its README) are the owner's module test scripts and runners on `tsv-*` clones of the live UAT site. They refuse any other site.

## Key Bench Commands

```bash
# E2E test runs
bench e2e run [--spec Selling ...] [--parallel 4] [--ui/--no-ui] [--ui-parallel 3] [--ui-shards 1] [--drop-clones] [--manual-shots <dir>]
              [--impacted-since <rev> [--base-run <prefix>] | --cases-from <impacted.json>]
bench e2e impacted --since <rev> [--base-run <prefix>] [--json <out>] [-v] [--until <rev> --ignore-base]
bench --site tsv-<suffix>-20261019.local e2e workflow-test --spec Selling [--cases ...]
bench --site tsv-<suffix>-20261019.local e2e ui-test --spec Selling [--cases ...] [--port 8600] [--manual-shots <dir>]

# Clone & Seed management
bench e2e clone create|drop|dump|setup|live-seed <suffix> ...
bench --site <site> e2e seed-restore [--seed <dir>] [--no-migrate] [--live]
bench e2e workbook --prefix <run prefix> [--module HR_Payroll ...] [--out-dir ...] [--baseline-dir ...] [--baseline-rev <rev>]
bench e2e guide --prefix <run prefix> --shots <dir> [--shots <dir> ...] [--module Selling ...]
bench e2e handbook [--framework <xlsx> --coverage <json>] [--shots <dir> --prefix <run>]
bench e2e keys [--assign] [--retire-since <rev>]

# Rollout tools (clean up a real site; preview unless confirmed)
bench --site <site> rollout mock-cleanup|item-groups|uom-cleanup|warehouses [--delete|--apply --confirm <TOKEN>]
bench --site <site> rollout access-report [--out DIR]
```

## Seed Policy
- `seed/` in the work directory is the live UAT site equivalent; NEVER modified.
- `seed-current/` is `seed/` plus `bench migrate` on `development`, rebuilt at the end of every PR.
- Clones restore seeds without migrating, running with `TSV_SEED=<work dir>/seed-current`.

## Execution Notes
- `e2e run` creates a fresh clone per spec for workflow loop and browser replay.
- With `--impacted-since <rev>`, server side runs all cases but browser only replays impacted + smoke set (`e2e/smoke.yaml`).
- Test scripts live in `scenarios/<Key>/` (`_module.yaml` + one file per tab, merged by `scenarios/loader.py`); only the hooks (`<Key>_hooks.py`) stay in `e2e/specs/`. Layout and the anchor rule: `scenarios/README.md`.
