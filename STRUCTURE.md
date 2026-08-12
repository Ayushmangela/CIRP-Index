# What each file is for

Drop this whole tree into your repo root. Files load at different times — that
is the point. A single giant instruction file gets skim-read; a small root file
plus on-demand docs does not.

| File | When it loads | Why |
|---|---|---|
| `AGENTS.md` | Every session, every agent | Cross-tool standard. Commands, rules, boundaries. Under 200 lines on purpose. |
| `CLAUDE.md` | Every Claude Code session | Thin bridge — imports `@AGENTS.md`, adds Claude-specific behaviour (plan mode, subagents, skills). |
| `README.md` | Humans, and agents reading context | Public-facing. Holds the real accuracy numbers and the limitations. |
| `docs/DATA_SOURCE.md` | Only for ingestion work | IBBI endpoints, table shape, case-number formats, access rules. |
| `docs/EXTRACTION_CONTRACT.md` | Only for LLM work | The span-verification rule. The most important file here. |
| `docs/SCHEMA.md` | Only for model/migration work | Fixed schema. Agent is denied write access to it. |
| `docs/DESIGN_SYSTEM.md` | Only for UI work | Tokens, components, three screens, mandatory disclaimer. |
| `docs/EVALUATION.md` | Only for accuracy work | Gold set process and metric definitions. |
| `docs/decisions/*.md` | When someone asks "why is it like this" | ADRs. Stops the agent relitigating settled decisions. |
| `.claude/skills/*/SKILL.md` | Auto-invoked on matching task | Domain logic that repeats. Also usable as `/span-verify` etc. |
| `.claude/settings.json` | Session start | Pre-approves safe commands, blocks writes to ground truth and to the fixed specs. |

## Also add

`PROJECT_SPEC.md` and `docs/BUILD_PROMPTS.md` from the build-plan document —
the nine sequential prompts and the full spec.

## Maintenance

Treat these as code. Commit them, review changes to them, prune them on a
schedule. A stale rule in `AGENTS.md` is worse than a missing one, because the
agent trusts it. When Claude gets something wrong, add one line to `AGENTS.md`
under "Mistakes made before" — one line, not a paragraph, and only after it
actually happens.

Do not let an agent write these files for you. That is the documented way to
make them worse.
