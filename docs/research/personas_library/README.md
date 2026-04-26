# Persona library (agency-agents style)

These are **adapted persona files** in the
[msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)
on-disk format (YAML frontmatter + standardised markdown sections). They are a
**richer source of truth** than the runtime
`src/autoresearch/agents/personas.yaml`, which only carries `system_prompt`,
`allowed_tools`, and `output_kind`.

Why duplicate? Two reasons:

1. **Design-time**: humans iterate on the rich files; the loader will eventually
   compile them down into the runtime YAML. Until that loader lands, these
   files document what the runtime prompts *should* contain.
2. **Standalone use**: the same files can be installed into Claude Code,
   Copilot, Cursor, etc. (via the agency-agents `install.sh` pattern) and used
   for ad-hoc deck authoring outside the harness.

## Roster (this commit)

| File | Maps to | Origin |
|---|---|---|
| [`designer.md`](./designer.md) | runtime `designer` persona | adapted from `design/visual-storyteller` |
| [`visual-designer.md`](./visual-designer.md) | runtime `visual_designer` persona | adapted from `design/image-prompt-engineer` |
| [`brand-guardian.md`](./brand-guardian.md) | new optional QA pass | adapted from `design/brand-guardian` |

See `docs/research/agency_agents.md` for the methodology and full mapping table.
