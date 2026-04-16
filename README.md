# naukri-tool

Personal CLI that searches [Naukri.com](https://www.naukri.com), ranks openings
against your master resume, and produces a tailored LaTeX/PDF resume per role
for you to review before applying.

See [`PLAN.md`](./PLAN.md) for the full design, policy/compliance notes, and
milestone breakdown.

---

## Status

**Milestone 1 — project scaffold.** The CLI parses and loads config; every
subcommand is a stub that logs its inputs and points at the milestone that
will implement it.

---

## Quickstart

```bash
# 1. Install (editable) via uv
uv sync

# 2. Copy the env template and fill in your Anthropic key (optional until M3+)
cp .env.example .env
$EDITOR .env

# 3. Confirm the CLI works
uv run naukri-tool --help
uv run naukri-tool --version
uv run naukri-tool scrape "python backend" --limit 10
```

You should see a log line noting the command is a stub plus the milestone
that will implement it.

---

## Planned commands

| Command                                    | Milestone | Status   |
|--------------------------------------------|-----------|----------|
| `naukri-tool bootstrap <pdf>`              | M3        | stub     |
| `naukri-tool login`                        | M4        | stub     |
| `naukri-tool scrape <query> --limit N`     | M5–M6     | stub     |
| `naukri-tool rank <run-id>`                | M8        | stub     |
| `naukri-tool tailor <run-id> <slug>`       | M9        | stub     |
| `naukri-tool tailor <run-id> --all`        | M9        | stub     |
| `naukri-tool search <query> ...`           | M11       | stub     |
| `naukri-tool open <run-id>`                | M11       | stub     |

All commands accept `--dry-run` and `--verbose`.

---

## Project layout

```
src/naukri_tool/
├── __init__.py
├── cli.py              ← Typer commands
├── config.py           ← pydantic-settings
└── logging_setup.py    ← structlog
```

Scrape, research, rank, tailor, compile, and LLM modules land in later
milestones (see `PLAN.md` §11).

---

## Development

```bash
uv run python -c "from naukri_tool.config import get_settings; print(get_settings())"
uv run naukri-tool --help
```

Secrets (`.env`), session state (`auth/`), and runs (`output/`) are
gitignored — see `.gitignore`.
