# naukri-tool — User Guide

> Personal CLI that searches Naukri.com, ranks openings against your master
> resume, and produces a tailored LaTeX/PDF resume per role for you to review
> before applying.

---

## 1. What this tool does

You give it a keyword (e.g. `"python backend"`). It:

1. **Scrapes** the top ~10 matching jobs from your logged-in Naukri session.
2. **Researches** each JD — extracting stack, seniority, red flags.
3. **Ranks** the jobs against your master resume (0–100 rubric).
4. **Tailors** a truthful, JD-aligned LaTeX/PDF resume per job.

It never auto-applies. It drops everything into a review folder so you look
each tailored resume over before using it.

---

## 2. Current status

| Milestone | Scope                              | Status        |
|-----------|------------------------------------|---------------|
| M1        | Project scaffold, CLI, config      | **Done**      |
| M2        | LaTeX template + YAML → PDF render | Planned       |
| M3        | `bootstrap` — PDF → master.yaml    | Planned       |
| M4        | `login` — saves Playwright session | Planned       |
| M5–M6     | `scrape` — jobs.json + full JDs    | Planned       |
| M7        | Research stage                     | Planned       |
| M8        | Ranking                            | Planned       |
| M9        | Tailor prompt + render             | Planned       |
| M10       | Truthfulness verifier              | Planned       |
| M11       | End-to-end `search` command        | Planned       |
| M12       | Docs + README                      | Planned       |

Today every command is a stub that logs its inputs and tells you which
milestone will implement it. The CLI parses cleanly, config loads, and
logging works — the rails are laid.

---

## 3. System requirements

| Requirement           | Version / notes                                      |
|-----------------------|------------------------------------------------------|
| OS                    | Linux or macOS (Windows via WSL)                     |
| Python                | 3.11+                                                |
| `uv`                  | Recent (0.4+)                                        |
| Anthropic API key     | Needed from M3 onward (research/rank/tailor)         |
| Playwright + Chromium | Installed from M4 onward                             |
| `tectonic`            | Installed from M2 onward (LaTeX → PDF)               |
| Disk                  | ~500 MB (Chromium) + small per run                   |
| Network               | Real-browser traffic to naukri.com, logged in as you |

---

## 4. One-time setup

```bash
# 1. Clone
git clone <repo-url> claude-naukri
cd claude-naukri

# 2. Install deps (creates .venv, installs naukri-tool editable)
uv sync

# 3. Copy env template and fill in
cp .env.example .env
$EDITOR .env        # set ANTHROPIC_API_KEY

# 4. Sanity check — should print help
uv run naukri-tool --help
```

From M4 onward you'll also need to run:

```bash
uv run playwright install chromium
```

From M2 onward, install `tectonic` (single binary, no TeXLive required):

```bash
# macOS
brew install tectonic
# Linux
curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh
```

---

## 5. Environment variables

`.env` (gitignored):

```
ANTHROPIC_API_KEY=sk-ant-...
RESUME_MASTER_PATH=resumes/master.yaml
```

`ANTHROPIC_API_KEY` is optional during M1 — the CLI boots without it.
Stages that call the API will raise a clear error if it's missing.

---

## 6. Architecture

Four independently runnable stages. Each writes to disk so failures are
resumable and state is inspectable.

```
  ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌─────────┐
  │  scrape  │──▶│ research  │──▶│    rank    │──▶│ tailor  │
  └──────────┘   └───────────┘   └────────────┘   └─────────┘
   jobs.json      research.md     rankings.md     resume.pdf
                  research.json                   resume.tex
                                                  diff.md
```

- **scrape** — headless Playwright, reuses saved login. Human-paced (2–5s
  between page loads), no parallelism, max ~10 jobs per run.
- **research** — Claude Haiku extracts structured JD metadata
  (must-haves, seniority, remote flag, red flags).
- **rank** — Claude Haiku scores each job against your resume using a fixed
  0–100 rubric (skill match 40, seniority 20, domain 20, role shape 10,
  red flags −10). Results cached by `job_id`.
- **tailor** — Claude Opus rewrites the resume with a truthfulness contract
  (never invents content; only reorders, rewords, hides). Emits a
  provenance map; a second Haiku pass verifies traceability.

---

## 7. Typical workflow

```bash
# One-time — extract your existing PDF into structured YAML
uv run naukri-tool bootstrap ~/Documents/resume.pdf
$EDITOR resumes/master.yaml.draft   # review, fix anything wrong
mv resumes/master.yaml.draft resumes/master.yaml

# One-time (per ~2 weeks) — log in to Naukri in a real browser
uv run naukri-tool login

# Each time you want fresh results
uv run naukri-tool search "python backend" --exp 8 --loc bangalore --limit 10

# Review rankings
uv run naukri-tool open <run-id>
```

---

## 8. Commands

| Command                                         | Does what                                               |
|-------------------------------------------------|---------------------------------------------------------|
| `naukri-tool bootstrap <pdf>`                   | One-time: PDF → `master.yaml.draft` for review          |
| `naukri-tool login`                             | Headful login, saves `auth/storage_state.json`          |
| `naukri-tool search <query> [--exp --loc --limit]` | Full pipeline end-to-end                             |
| `naukri-tool scrape <query> [--limit]`          | Scrape only                                             |
| `naukri-tool rank <run-id>`                     | Re-rank without re-scraping                             |
| `naukri-tool tailor <run-id> <slug>`            | Re-tailor one job                                       |
| `naukri-tool tailor <run-id> --all`             | Re-tailor every job in a run                            |
| `naukri-tool open <run-id>`                     | Open `rankings.md` in `$EDITOR`                         |

**Global flags**

- `--verbose` / `-v` — DEBUG-level logging.
- `--dry-run` — skip LLM calls and non-scrape network writes.
- `--version` — print version.

---

## 9. Output layout

```
output/
└── 2026-04-16_python-backend/       ← run-id
    ├── jobs.json                    ← raw scrape
    ├── rankings.md                  ← your triage view
    └── 087_acme_senior-backend/     ← prefix = score; ls gives sorted view
        ├── jd.md
        ├── research.md
        ├── research.json
        ├── resume.yaml
        ├── resume.tex
        ├── resume.pdf
        └── diff.md                  ← what changed vs master & why
```

`output/` is gitignored. Nothing is auto-pruned — old runs stick around
until you delete them.

---

## 10. Policy & compliance

Naukri's ToU restricts automated access. This tool is designed for **single
personal use**:

- You are an accepted Naukri user interacting through your own logged-in
  real browser profile. No credential sharing, no throwaway accounts.
- Human-paced browsing (2–5s random delays, no parallelism, max ~10 JDs).
- Respects `robots.txt` for the user-agent we present.
- Scraped JDs and company data stay on your machine.

You accept that Naukri may flag or rate-limit the account. DOM changes may
break selectors — expect occasional selector maintenance.

**Do not** share `auth/storage_state.json` — it's your session. It's
`chmod 600`, gitignored, never logged.

---

## 11. Troubleshooting

| Symptom                                          | Fix                                                         |
|--------------------------------------------------|-------------------------------------------------------------|
| `session expired, run naukri-tool login`        | Re-run `naukri-tool login` and log in again.                 |
| `ANTHROPIC_API_KEY is not set`                   | Fill it into `.env`.                                         |
| Scrape returns 0 jobs                             | DOM changed — check `scrape/selectors.py`.                   |
| `⚠ needs review` on a tailored resume            | Verifier flagged a claim not traceable to master. Open `diff.md`. |
| Login loop / captcha                             | Log in via the headful window. Manual is fine.               |
| `tectonic` not found                              | Install per §4; it's a single binary.                        |

---

## 12. Where to go next

- `PLAN.md` — full design, decisions, and milestone breakdown.
- `README.md` — quickstart + milestone status.

Questions or bugs: open an issue in this repo.
