# Azure Validation Commands

## Current Entrypoint

```bash
make azure-test
```

Equivalent:

```bash
bash scripts/azure_test.sh
```

Current state: `scripts/azure_test.sh` only prints that Azure-hosted tests are not wired yet.

## Rule

When a task needs official validation, do not mark it complete until Azure-hosted tests, quality gates, logs, and required docs pass. If the Azure path is not wired, report that as blocked.
