# Naukri Job Search + Resume Tailoring Tool — Plan

A personal CLI that searches Naukri.com for jobs matching your keywords, researches
each opening, ranks them against your master resume, and emits a tailored LaTeX/PDF
resume per role for you to review before applying.

---

## 1. Goals & Non-Goals

**Goals**
- Pull the top ~10 job matches for a keyword query from Naukri (logged-in).
- For each job, capture the full JD and light company context.
- Score and rank jobs by how closely they match your master resume.
- Produce a tailored LaTeX resume per job (safe, truthful, JD-aligned emphasis) and
  compile to PDF.
- Drop everything into a review folder so nothing auto-applies.

**Non-Goals**
- No auto-apply. No bulk outreach. No data redistribution.
- No fabrication of skills/experience not present in the master resume.
- Not a general job aggregator — Naukri only for v1.

---

## 2. Policy & Compliance

Naukri's Terms of Use restrict automated access. We mitigate risk; we do not pretend
it's zero.

**What we will do**
- **Personal, single-user, logged-in session.** You are an accepted user interacting
  with the site through a real browser profile — not a mass scraper.
- **Human-paced browsing.** Randomized delays (2–5s) between actions, no concurrent
  requests, one page at a time, max ~10 JDs per run.
- **Respect `robots.txt`.** Skip any path disallowed for the user-agent we present.
- **No redistribution.** Scraped JDs and company data stay on your machine.
- **No credential sharing.** Session state stored locally (`auth/storage_state.json`),
  gitignored, never committed.
- **Clear kill switch.** `--dry-run` and a visible banner on first run reminding you
  this is for personal use.

**Risks you accept**
- Naukri may flag/rate-limit/ban the account used. Use your real account, not a
  throwaway, but understand the risk.
- Site DOM changes will break selectors; expect occasional maintenance.

**Safer-but-lossier alternative (documented, not v1)**
- Subscribe to Naukri Job Alert emails and parse them from Gmail. Fully ToS-aligned,
  but JD content in emails is truncated and filters are limited. Keep as fallback.

---

## 3. Architecture

Three stages, each independently runnable so you can re-run just the piece you need.

```
  ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌─────────┐
  │  scrape  │──▶│ research  │──▶│    rank    │──▶│ tailor  │
  └──────────┘   └───────────┘   └────────────┘   └─────────┘
     jobs.json      per-job md      rankings.md     resume.tex→pdf
```

Stages write to disk between steps so failures are resumable and state is inspectable.

---

## 4. Tech Stack

| Concern            | Choice                         | Why                                         |
|--------------------|--------------------------------|---------------------------------------------|
| Language           | Python 3.11+                   | Playwright + Anthropic SDK are first-class  |
| Browser automation | Playwright (Chromium)          | Handles JS-rendered Naukri pages, good session APIs |
| LLM                | Anthropic SDK, `claude-opus-4-6` for tailoring; `claude-haiku-4-5` for ranking | Opus for nuanced rewriting; Haiku is fast/cheap for scoring |
| Prompt caching     | Enabled on master resume + JD schema | Master resume is re-sent per job — cache it |
| LaTeX → PDF        | `tectonic`                     | Single binary, no TeXLive install, reproducible |
| Packaging          | `uv` + `pyproject.toml`        | Fast, lockable                              |
| Config             | `.env` + `pydantic-settings`   | Typed, validated                            |
| Logging            | `structlog` → stdout + file    | Debuggable reruns                           |

---

## 5. Session Management (Logged-In Naukri)

Playwright's `storage_state` pattern — login once, reuse cookies/localStorage across
runs.

**Flow**
1. `naukri-tool login`
   - Launches headful Chromium on `naukri.com/nlogin/login`.
   - You log in manually (including any OTP/captcha).
   - Script waits for navigation to the profile page, then saves
     `auth/storage_state.json`.
2. All other commands launch headless with `storage_state=auth/storage_state.json`.
3. Before each run, hit a cheap authenticated endpoint (e.g. profile page). If
   redirected to login → print "session expired, run `naukri-tool login`" and exit.
4. Session file is `chmod 600`, gitignored, never logged.

**Why not username/password in env?**
- Naukri uses captcha/OTP on many logins; scripted credential entry is fragile and
  more adversarial to the site. Manual login once per ~2 weeks is fine.

---

## 6. Stage 1: Scrape

**Input:** keyword(s), optional filters (experience, location), limit (default 10).

**Steps**
1. Build search URL:
   `https://www.naukri.com/<keyword-slug>-jobs?experience=<N>&location=<loc>`
2. Load results page with Playwright.
3. Extract top N job cards: title, company, location, experience, salary (if shown),
   posted date, job URL, job ID.
4. For each job URL, navigate and extract: full JD text, required skills list,
   company "about" blurb, role type, notice period if present.
5. Write `output/<run-id>/jobs.json`.

**Rate limiting**
- `asyncio.sleep(random.uniform(2, 5))` between page loads.
- No parallelism in v1.

**Resilience**
- Selectors in one module (`scrape/selectors.py`) so DOM drift = one-file fix.
- Save raw HTML of each JD page alongside parsed JSON for re-parsing without
  re-scraping.

---

## 7. Stage 2: Research

Light enrichment, not deep investigation.

**Per job**
1. **Company snippet** — pull the Naukri company page's about/size/rating if linked.
2. **Red flags** — regex for phrases like "immediate joiner only", "unpaid",
   "commission only", extreme tenure requirements.
3. **Stack extraction** — LLM call (Haiku) that reads JD and returns structured JSON:
   `{must_have: [...], nice_to_have: [...], seniority: "...", remote: bool, ...}`.
4. Write `output/<run-id>/<job-slug>/research.md` + `research.json`.

Prompt caching: the research prompt template is cached; only the JD varies per call.

---

## 8. Stage 3: Rank

**Inputs:** master resume (parsed once into structured skills/experience), all 10
`research.json` files.

**Scoring** — LLM (Haiku) with a fixed rubric, scored 0–100:
- **Skill match (40)** — overlap between JD `must_have` and resume skills.
- **Seniority fit (20)** — years of experience band alignment.
- **Domain/stack fit (20)** — languages, frameworks, industry.
- **Role shape (10)** — IC vs lead match, scope alignment (team size, ownership).
- **Red flags (−10 to 0)** — penalties from research stage.

Output: `output/<run-id>/rankings.md` — a sorted table with score, breakdown, one-line
rationale, and link to the job folder. This is your triage view.

Scores are cached by `job_id` so re-running doesn't re-bill the LLM.

---

## 9. Stage 4: Tailor Resume

**The truthfulness contract**
The tailor prompt is pinned to these rules, repeated in the system prompt:
1. NEVER invent skills, roles, employers, dates, or metrics not present in the master.
2. You MAY reorder bullets, reword for JD vocabulary, and change emphasis.
3. You MAY hide (omit) bullets/skills irrelevant to the JD.
4. You MAY rewrite the summary paragraph using only facts present in the master.
5. Every claim in the output must be traceable to a line in the master. Output a
   `provenance` map `{tailored_bullet_id: master_bullet_id}` for verification.

**Flow per job**
1. Load `resumes/master.tex` (structured into labeled sections — see §10).
2. Load JD + research for the job.
3. Call Opus with: master resume (cached), JD (not cached), tailor rules (cached).
4. Expect structured output: `{summary, sections: [...], provenance, diff_summary}`.
5. Render back into `resume.tex` using a Jinja template that mirrors the master's
   layout.
6. Compile with `tectonic resume.tex` → `resume.pdf`.
7. Write `diff.md` — human-readable summary of what changed vs master and why.

**Verification pass**
After generation, a second Haiku call reads the tailored resume + master and flags
any claim not traceable to master. If it flags anything, the job is marked
`⚠ needs review` in the rankings file and the PDF is still produced but labeled.

---

## 10. Master Resume Format

`resumes/master.yaml` is the **source of truth** for content; `master.tex` is
generated from it via a Jinja template. This separation means the LLM never
hand-writes LaTeX (avoids syntax breakage) and styling lives in one template file.

**Structure**
```yaml
contact: { name, email, phone, location, links: [...] }
summary: "..."
skills:
  - group: "Languages"
    items: ["Python", "Go", ...]
experience:
  - id: exp-2023-acme
    company: "Acme"
    role: "Senior Engineer"
    dates: "2023–present"
    bullets:
      - { id: exp-2023-acme-b1, text: "..." }
education: [...]
projects: [...]
```

Every bullet has a stable `id` — this is what the tailor stage's `provenance` map
references to prove each tailored line traces to a master line.

**One-time bootstrap from your existing PDF** — see §10a.

---

## 10a. Bootstrapping from PDF (one-time)

Since your master lives in PDF today, we need a one-time extract → structure → review
flow. New command:

```
naukri-tool bootstrap path/to/your_resume.pdf
```

**Steps**
1. **Extract text** with `pymupdf` (preserves reading order better than `pdfplumber`
   for resumes). Also dump per-page text for debugging.
2. **Structure with LLM** (Opus) — prompt: "Parse this resume text into the YAML
   schema below. Preserve wording exactly. Do not infer or add content. If a field
   is missing, omit it." Output → `resumes/master.yaml.draft`.
3. **Render preview** — pick a template (see below), render
   `master.yaml.draft` → `master.tex.draft` → `master.pdf.draft`.
4. **You review** the YAML side-by-side with your original PDF, edit anything the
   LLM got wrong (names, dates, bullet wording), then `mv master.yaml.draft
   master.yaml`.
5. Re-render to confirm the generated PDF reads correctly. Done.

**Template choice (v1)** — we do NOT try to visually match your existing PDF
(layout-matching is brittle and rarely worth it). Instead, ship 2 clean templates
in `resumes/templates/`:
- `classic.tex.j2` — single-column, serif, ATS-friendly (recommended default).
- `modern.tex.j2` — single-column, sans-serif, subtle accent color.

Both are ATS-safe (no tables/columns/images for content). You can swap templates via
`--template modern` at render time; the YAML is template-agnostic.

**Fidelity expectations** — the bootstrap LLM will get 90%+ right on a
straightforward resume but may: misattribute a bullet to the wrong role, drop a
sub-bullet, or mangle unusual characters. Budget 15–30 min to review the YAML once.
After that, the YAML is hand-edited like any other source file.

---

## 11. Directory Layout

```
naukri/
├── PLAN.md                       ← this file
├── README.md                     ← quickstart
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore                    ← auth/, output/, .env
├── src/naukri_tool/
│   ├── cli.py                    ← Typer commands
│   ├── config.py
│   ├── session.py                ← Playwright auth
│   ├── scrape/
│   │   ├── search.py
│   │   ├── jd.py
│   │   └── selectors.py
│   ├── research.py
│   ├── rank.py
│   ├── tailor/
│   │   ├── prompt.py
│   │   ├── render.py             ← YAML → tex
│   │   └── verify.py             ← truthfulness check
│   ├── compile.py                ← tectonic wrapper
│   └── llm.py                    ← Anthropic client + caching
├── prompts/
│   ├── research.md
│   ├── rank.md
│   ├── tailor.md
│   └── verify.md
├── resumes/
│   ├── master.tex
│   ├── master.yaml
│   └── template.tex.j2
├── auth/                         ← gitignored
│   └── storage_state.json
└── output/
    └── 2026-04-16_python-backend/
        ├── jobs.json
        ├── rankings.md
        └── 087_acme_senior-backend/
            ├── jd.md
            ├── research.md
            ├── research.json
            ├── resume.yaml
            ├── resume.tex
            ├── resume.pdf
            └── diff.md
```

Folder prefix `087_` = match score, so `ls` gives you a ranked view.

---

## 12. CLI Surface

```
naukri-tool bootstrap path/to/your_resume.pdf
    → one-time: extracts PDF → resumes/master.yaml.draft for your review

naukri-tool login
    → headful login, saves auth/storage_state.json

naukri-tool search "python backend" --exp 8 --loc bangalore --limit 10
    → full pipeline: scrape → research → rank → tailor
    → writes output/<run-id>/

naukri-tool scrape "python backend" --limit 10
    → scrape only

naukri-tool tailor <run-id> <job-slug>
    → re-tailor one job (e.g., after editing master)

naukri-tool tailor <run-id> --all
    → re-tailor every job in a run

naukri-tool rank <run-id>
    → re-rank without re-scraping

naukri-tool open <run-id>
    → open the rankings.md in $EDITOR
```

All commands accept `--dry-run` (no LLM calls, no network writes beyond scrape) and
`--verbose`.

---

## 13. Config & Secrets

`.env` (gitignored):
```
ANTHROPIC_API_KEY=...
RESUME_MASTER_PATH=resumes/master.yaml
```

No default location or experience filters — if you don't pass `--loc` / `--exp`,
Naukri's unfiltered results are used.

`auth/storage_state.json` — session cookies, `chmod 600`, gitignored.

No Naukri credentials in env — login is always manual through the browser.

---

## 14. Implementation Milestones

Each milestone is independently testable.

| # | Milestone                          | Deliverable                                     |
|---|------------------------------------|-------------------------------------------------|
| 1  | Project scaffold                    | `uv` project, CLI stub, config loading          |
| 2  | LaTeX templates + renderer          | `master.yaml` → `.tex` → PDF via `tectonic`     |
| 3  | PDF bootstrap (`bootstrap` command) | Your PDF → `master.yaml.draft` for review       |
| 4  | Session login                       | `naukri-tool login` saves working storage_state |
| 5  | Search scrape                       | `jobs.json` for a query, 10 rows                |
| 6  | JD scrape                           | Full JD text + skills per job                   |
| 7  | Research stage                      | `research.json` + `research.md` per job         |
| 8  | Ranking                             | `rankings.md` with scored, sorted table         |
| 9  | Tailor prompt + render              | `resume.tex` + `resume.pdf` per job             |
| 10 | Truthfulness verifier               | `⚠ needs review` flag when claims drift         |
| 11 | End-to-end `search` command         | Single command runs full pipeline               |
| 12 | Docs + README                       | Quickstart, login, troubleshooting              |

Rough effort: M1–M3 are ~half a day (bootstrap review by you is the longest part);
M4–M6 ~1 day; M7–M11 ~1 day; M12 an hour.

---

## 15. Decisions (locked)

1. **Default template** — `classic` (single-column, serif, ATS-safe). `modern`
   remains available via `--template modern`.
2. **Default search filters** — none. If `--loc` / `--exp` are omitted, Naukri's
   unfiltered results are used.
3. **Remote preference** — ignored in ranking. Role location is captured in the
   scrape for your manual triage but does not affect the score.
4. **Output retention** — keep forever. No auto-prune.
5. **Master PDF** — drop your resume PDF anywhere and pass the path to
   `naukri-tool bootstrap`.

Ready to start Milestone 1.
