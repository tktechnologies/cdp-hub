# Harness Engineering

## Goal

Make long-running AI-assisted development safe, reviewable, and resumable.

## Task Contract

Every task must define:

- task ID
- goal
- files allowed to change
- acceptance criteria
- required Azure tests
- required logs
- required docs
- required `.agent/` workspace updates
- risks
- done/not done checklist

## AI Workflow

1. Read relevant specs and `.agent/` workspace files.
2. Update specs if behavior changes.
3. Write tests for Azure execution.
4. Implement the smallest production-shaped change.
5. Add logs, metrics, and errors.
6. Update docs and `.agent/` workspace files.
7. Mark complete only after Azure validation.

## Guardrails

- Do not mark work complete from chat memory alone.
- Do not hide failed tests or skipped cloud validation.
- Do not add new Azure services without explicit cost/benefit approval.
