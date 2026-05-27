# Implementation Flow

1. Read `.agent/rules.md`.
2. Read `.agent/index.md`.
3. Read the relevant specs and source files.
4. Confirm the task contract when the change is non-trivial.
5. Write or update tests, or document why Azure validation is the first executable test surface.
6. Implement the smallest production-shaped change.
7. Add structured logs, metrics, traces, and errors where relevant.
8. Run local feedback checks.
9. Run or clearly mark blocked Azure validation.
10. Update docs, specs, and `.agent/`.
11. Summarize what changed, what passed, and what remains unvalidated.
