# CLAUDE.md - AI Coding Instructions

## Part 1: Core Coding Rules

- **Think Before Coding**: State your assumptions clearly. Discuss trade-offs and ask clarifying questions instead of guessing.
- **Simplicity First**: Write the minimum code required to solve the immediate problem. Avoid speculative features or premature abstractions.
- **Surgical Changes**: Only modify code directly relevant to the task. Do not "clean up" adjacent code, styling, or comments.
- **Goal-Driven Execution**: Define what success looks like (e.g., write a test and make it pass). Let the AI iterate until verification.

## Part 2: Agent Orchestration Rules

- **Keep Deterministic Work out of AI**: Do not make Claude handle raw string formatting or mechanical tasks; delegate these to standard code tools.
- **Manage Token Budgets**: Enforce strict limits on context usage (e.g., 4k per message, 30k per session) to prevent token bloat.
- **Resolve Style Conflicts**: If formatting or lint rules conflict, prioritize a single unified configuration and discard the rest.
- **Verify Context Before Editing**: Always read the surrounding code and imports before writing a single line to ensure compatibility.
- **Use Business-Logic Tests**: Write meaningful tests that validate actual intent and business outcomes, not just empty code coverage.
- **Create Step-by-Step Checkpoints**: For multi-step long tasks, halt at milestones to log what was done, what was verified, and what remains.
- **Match Existing Codebase Style**: Strictly follow established code conventions (e.g., snake_case or class components) even if you disagree.
- **Explicitly Fail Loud (Fail Loud)**: If a step fails, skips data, or cannot be fully verified, report the error immediately. Never hide uncertainties.

## Design System

Always read [`DESIGN.md`](./DESIGN.md) before making any visual or UI decision.
All fonts, colors, spacing, aesthetic direction, and the two-room IA (策略室 / 交易室)
are defined there. Do not deviate without explicit user approval.

- The electric-cyan accent (`--accent`) is reserved for AI / automation only.
- Drive price up/down through `--up` / `--down` tokens — never hardcode green-as-gain
  (台股 inverts the convention via `data-market="tw"`).
- In QA / review, flag any code that does not match DESIGN.md.
