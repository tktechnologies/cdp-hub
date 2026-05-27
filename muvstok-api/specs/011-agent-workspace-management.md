# Agent Workspace Management

## Purpose

Keep durable project memory and reusable agent assets in the repository so future sessions do not depend on chat history.

`.agent/` is the canonical home for project knowledge, skills, commands, sub-agent briefs, and other agent-facing workflows.

## Required Knowledge Files

- `.agent/rules.md`
- `.agent/index.md`
- `.agent/memory/project-memory.md`
- `.agent/memory/decisions.md`
- `.agent/memory/glossary.md`
- `.agent/memory/known-issues.md`
- `.agent/memory/implementation-state.md`
- `.agent/standards/coding-standards.md`
- `.agent/standards/testing-playbook.md`
- `.agent/standards/security-and-secrets.md`
- `.agent/standards/observability.md`
- `.agent/standards/azure-playbook.md`
- `.agent/workflows/implementation-flow.md`
- `.agent/workflows/task-contract.md`
- `.agent/workflows/review-checklist.md`
- `.agent/workflows/operational-runbook.md`

## Smart Agent Assets

- `.agent/skills/` stores reusable project-specific skills and playbooks.
- `.agent/commands/` stores repeatable command recipes and operational runbooks.
- `.agent/sub-agents/` stores role briefs, delegation contracts, and specialist instructions.
- `.agent/references/` stores compact repo maps and source-oriented notes.

## Update Rule

After important implementation work, update the relevant `.agent/` file with decisions, patterns, open issues, validation results, and reusable workflows.
