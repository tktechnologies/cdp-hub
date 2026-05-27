#!/usr/bin/env bash
set -euo pipefail

required_specs=(
  specs/001-project-overview.md
  specs/002-api-contract.md
  specs/003-job-lifecycle.md
  specs/004-database-design.md
  specs/005-testing-strategy.md
  specs/006-harness-engineering.md
  specs/007-observability.md
  specs/008-security-and-secrets.md
  specs/009-azure-infrastructure.md
  specs/010-queue-processing.md
  specs/011-agent-workspace-management.md
  specs/012-operational-runbook.md
)

for spec in "${required_specs[@]}"; do
  test -s "$spec"
done

echo "All required specs exist."
