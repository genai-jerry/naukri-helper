"""Render docs/user-guide.pdf from docs/USER_GUIDE.md.

Run:
    uv run --with reportlab python docs/build_user_guide.py

Keeps the markdown as the source of truth; this script composes the PDF
layout (typography, tables, architecture diagram) directly with reportlab
so we don't depend on pandoc/latex in dev environments.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.graphics.shapes import Drawing, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).parent / "user-guide.pdf"

# --- Palette -------------------------------------------------------------

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#555555")
ACCENT = colors.HexColor("#2b6cb0")
ACCENT_BG = colors.HexColor("#ebf4fb")
STAGE_FILL = colors.HexColor("#e6f0fa")
STAGE_EDGE = colors.HexColor("#2b6cb0")
OUTPUT_FILL = colors.HexColor("#f3f4f6")
OUTPUT_EDGE = colors.HexColor("#9ca3af")
WARN_BG = colors.HexColor("#fff8e1")
WARN_EDGE = colors.HexColor("#d4a20f")


# --- Styles --------------------------------------------------------------

_base = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "Title", parent=_base["Title"], fontName="Helvetica-Bold",
    fontSize=26, textColor=INK, spaceAfter=4, alignment=TA_LEFT,
)
SUBTITLE = ParagraphStyle(
    "Subtitle", parent=_base["Normal"], fontName="Helvetica",
    fontSize=12, textColor=MUTED, spaceAfter=18, leading=16,
)
H1 = ParagraphStyle(
    "H1", parent=_base["Heading1"], fontName="Helvetica-Bold",
    fontSize=16, textColor=INK, spaceBefore=18, spaceAfter=8,
)
H2 = ParagraphStyle(
    "H2", parent=_base["Heading2"], fontName="Helvetica-Bold",
    fontSize=12, textColor=INK, spaceBefore=10, spaceAfter=4,
)
BODY = ParagraphStyle(
    "Body", parent=_base["BodyText"], fontName="Helvetica",
    fontSize=10, textColor=INK, leading=14, spaceAfter=6,
)
MUTED_BODY = ParagraphStyle(
    "MutedBody", parent=BODY, textColor=MUTED,
)
CODE = ParagraphStyle(
    "Code", parent=_base["Code"], fontName="Courier",
    fontSize=9, textColor=INK, leading=12, leftIndent=10,
    backColor=colors.HexColor("#f5f5f5"), borderPadding=6,
    spaceBefore=4, spaceAfter=8,
)
CALLOUT = ParagraphStyle(
    "Callout", parent=BODY, fontName="Helvetica", fontSize=10,
    leading=14, textColor=INK, backColor=ACCENT_BG,
    borderPadding=10, leftIndent=0, spaceBefore=6, spaceAfter=10,
)
WARN = ParagraphStyle(
    "Warn", parent=BODY, fontName="Helvetica", fontSize=10,
    leading=14, textColor=INK, backColor=WARN_BG,
    borderPadding=10, leftIndent=0, spaceBefore=6, spaceAfter=10,
)


# --- Helpers -------------------------------------------------------------

def code(text: str) -> Paragraph:
    """Render a preformatted code block (line breaks preserved)."""
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace(" ", "&nbsp;")
        .replace("\n", "<br/>")
    )
    return Paragraph(escaped, CODE)


def simple_table(rows: list[list[str]], col_widths: list[float]) -> Table:
    """A two-plus-column table with a header row."""
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), INK),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                    [colors.white, colors.HexColor("#f7fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, ACCENT),
                ("LINEBELOW", (0, -1), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    return tbl


def architecture_diagram() -> Drawing:
    """Four stages across the page with arrows, outputs labeled below.

    Layout (all in points):
      - Drawing is 480 wide x 180 tall.
      - Four stage boxes centred in a row; arrows between them.
      - Each stage has an output caption directly beneath.
    """
    d = Drawing(480, 180)

    stages = [
        ("scrape", "jobs.json"),
        ("research", "research.json\nresearch.md"),
        ("rank", "rankings.md"),
        ("tailor", "resume.pdf\ndiff.md"),
    ]

    box_w, box_h = 90, 42
    gap = (480 - (box_w * 4)) / 5   # even spacing
    top = 110                        # box top
    y = top - box_h                  # box bottom

    centers: list[float] = []
    for i, (name, outputs) in enumerate(stages):
        x = gap + i * (box_w + gap)
        cx = x + box_w / 2
        centers.append(cx)

        d.add(
            Rect(
                x, y, box_w, box_h,
                fillColor=STAGE_FILL, strokeColor=STAGE_EDGE,
                strokeWidth=1.25, rx=6, ry=6,
            )
        )
        d.add(
            String(
                cx, y + box_h / 2 - 4, name,
                textAnchor="middle", fontName="Helvetica-Bold",
                fontSize=12, fillColor=INK,
            )
        )

        # Output caption under each box
        for j, line in enumerate(outputs.split("\n")):
            d.add(
                String(
                    cx, y - 14 - j * 11, line,
                    textAnchor="middle", fontName="Courier",
                    fontSize=8, fillColor=MUTED,
                )
            )

    # Arrows between stages
    arrow_y = y + box_h / 2
    for i in range(len(stages) - 1):
        x1 = centers[i] + box_w / 2 + 2
        x2 = centers[i + 1] - box_w / 2 - 2
        # shaft
        d.add(
            Polygon(
                points=[
                    x1, arrow_y - 0.8,
                    x2 - 6, arrow_y - 0.8,
                    x2 - 6, arrow_y + 0.8,
                    x1, arrow_y + 0.8,
                ],
                fillColor=MUTED, strokeColor=MUTED, strokeWidth=0,
            )
        )
        # head
        d.add(
            Polygon(
                points=[x2 - 6, arrow_y - 4, x2, arrow_y, x2 - 6, arrow_y + 4],
                fillColor=MUTED, strokeColor=MUTED, strokeWidth=0,
            )
        )

    # Caption
    d.add(
        String(
            240, 10, "Each stage writes to disk — failures are resumable, state is inspectable.",
            textAnchor="middle", fontName="Helvetica-Oblique",
            fontSize=9, fillColor=MUTED,
        )
    )

    return d


# --- Page footer ---------------------------------------------------------

def _footer(canvas, doc):  # noqa: ANN001 - reportlab signature
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(inch * 0.75, inch * 0.5, "naukri-tool — User Guide")
    canvas.drawRightString(
        LETTER[0] - inch * 0.75, inch * 0.5, f"Page {doc.page}"
    )
    canvas.restoreState()


# --- Document composition ------------------------------------------------

def build() -> None:
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        leftMargin=inch * 0.75,
        rightMargin=inch * 0.75,
        topMargin=inch * 0.75,
        bottomMargin=inch * 0.75,
        title="naukri-tool — User Guide",
        author="naukri-tool",
    )

    story: list = []

    # --- Cover -----------------------------------------------------------
    story += [
        Paragraph("naukri-tool", TITLE),
        Paragraph(
            "User Guide &middot; Personal Naukri job search + resume tailoring CLI",
            SUBTITLE,
        ),
        Paragraph(
            "<b>Status:</b> Milestone 1 shipped — project scaffold, CLI surface, "
            "config loading, and logging are working. Every command parses; "
            "feature implementations land in Milestones 2–12. "
            "This guide documents the planned system end-to-end.",
            CALLOUT,
        ),
    ]

    # --- 1. What it does -------------------------------------------------
    story += [
        Paragraph("1. What this tool does", H1),
        Paragraph(
            "You give it a keyword query (e.g. <i>\"python backend\"</i>). It:",
            BODY,
        ),
        Paragraph(
            "&nbsp;&nbsp;1. <b>Scrapes</b> the top ~10 matching jobs from your "
            "logged-in Naukri session.<br/>"
            "&nbsp;&nbsp;2. <b>Researches</b> each JD — stack, seniority, red flags.<br/>"
            "&nbsp;&nbsp;3. <b>Ranks</b> the jobs against your master resume "
            "(0–100 rubric).<br/>"
            "&nbsp;&nbsp;4. <b>Tailors</b> a truthful LaTeX/PDF resume per job.",
            BODY,
        ),
        Paragraph(
            "It never auto-applies. Tailored resumes land in a review folder "
            "so you inspect each one before using it.",
            BODY,
        ),
    ]

    # --- 2. Architecture -------------------------------------------------
    story += [
        Paragraph("2. Architecture", H1),
        Paragraph(
            "Four stages, each independently runnable so you can re-run just "
            "the piece you need.",
            BODY,
        ),
        KeepTogether(architecture_diagram()),
        Spacer(1, 6),
        Paragraph(
            "<b>scrape</b> — headless Playwright, reuses saved login. "
            "Human-paced (2–5s random delays, no parallelism, max ~10 JDs).",
            BODY,
        ),
        Paragraph(
            "<b>research</b> — Claude Haiku extracts structured JD metadata "
            "(must-haves, seniority, remote flag, red flags).",
            BODY,
        ),
        Paragraph(
            "<b>rank</b> — Claude Haiku scores jobs with a fixed 0–100 rubric "
            "(skill match 40, seniority 20, domain 20, role shape 10, red flags −10). "
            "Cached by <font face='Courier'>job_id</font>.",
            BODY,
        ),
        Paragraph(
            "<b>tailor</b> — Claude Opus rewrites with a truthfulness contract "
            "(never invents content; only reorders, rewords, hides). Emits a "
            "provenance map; a second Haiku pass verifies traceability.",
            BODY,
        ),
    ]

    # --- 3. System requirements -----------------------------------------
    story += [
        PageBreak(),
        Paragraph("3. System requirements", H1),
        simple_table(
            [
                ["Requirement", "Version / notes"],
                ["OS", "Linux or macOS (Windows via WSL)"],
                ["Python", "3.11+"],
                ["uv", "0.4+"],
                ["Anthropic API key", "Needed from M3 onward"],
                ["Playwright + Chromium", "Installed from M4 onward"],
                ["tectonic", "LaTeX → PDF; installed from M2 onward"],
                ["Disk", "~500 MB (Chromium) + small per run"],
                ["Network", "Real-browser traffic to naukri.com, logged in as you"],
            ],
            col_widths=[1.6 * inch, 4.8 * inch],
        ),
    ]

    # --- 4. Setup --------------------------------------------------------
    story += [
        Paragraph("4. One-time setup", H1),
        code(
            "# 1. Clone the repo\n"
            "git clone <repo-url> claude-naukri\n"
            "cd claude-naukri\n\n"
            "# 2. Install deps (creates .venv, installs naukri-tool editable)\n"
            "uv sync\n\n"
            "# 3. Copy env template and fill in\n"
            "cp .env.example .env\n"
            "$EDITOR .env          # set ANTHROPIC_API_KEY\n\n"
            "# 4. Sanity check\n"
            "uv run naukri-tool --help"
        ),
        Paragraph(
            "From M4 onward you'll also need Playwright browsers:",
            BODY,
        ),
        code("uv run playwright install chromium"),
        Paragraph(
            "From M2 onward, install <b>tectonic</b> (single binary, "
            "no TeXLive required):",
            BODY,
        ),
        code(
            "# macOS\n"
            "brew install tectonic\n\n"
            "# Linux\n"
            "curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh"
        ),
        Paragraph("Environment variables", H2),
        code(
            "ANTHROPIC_API_KEY=sk-ant-...\n"
            "RESUME_MASTER_PATH=resumes/master.yaml"
        ),
        Paragraph(
            "<font face='Courier'>ANTHROPIC_API_KEY</font> is optional while "
            "only M1 is shipped — the CLI boots without it. Stages that call "
            "the API raise a clear error when it's missing.",
            MUTED_BODY,
        ),
    ]

    # --- 5. Typical workflow --------------------------------------------
    story += [
        PageBreak(),
        Paragraph("5. Typical workflow", H1),
        Paragraph("<b>Once, during setup:</b>", BODY),
        code(
            "# Extract your existing PDF into structured YAML\n"
            "uv run naukri-tool bootstrap ~/Documents/resume.pdf\n"
            "$EDITOR resumes/master.yaml.draft       # review, fix anything wrong\n"
            "mv resumes/master.yaml.draft resumes/master.yaml"
        ),
        Paragraph("<b>Every ~2 weeks (session expiry):</b>", BODY),
        code("uv run naukri-tool login"),
        Paragraph("<b>Each time you want fresh results:</b>", BODY),
        code(
            'uv run naukri-tool search "python backend" \\\n'
            "      --exp 8 --loc bangalore --limit 10\n\n"
            "uv run naukri-tool open <run-id>         # review rankings.md"
        ),
    ]

    # --- 6. Commands -----------------------------------------------------
    story += [
        Paragraph("6. Command reference", H1),
        simple_table(
            [
                ["Command", "Does what", "Milestone"],
                ["bootstrap <pdf>", "PDF → master.yaml.draft for review (one-time)", "M3"],
                ["login", "Headful login; saves auth/storage_state.json", "M4"],
                ["search <q> …", "Full pipeline end-to-end", "M11"],
                ["scrape <q> [--limit]", "Scrape only", "M5–M6"],
                ["rank <run-id>", "Re-rank without re-scraping", "M8"],
                ["tailor <run-id> <slug>", "Re-tailor one job", "M9"],
                ["tailor <run-id> --all", "Re-tailor every job in a run", "M9"],
                ["open <run-id>", "Open rankings.md in $EDITOR", "M11"],
            ],
            col_widths=[2.1 * inch, 3.5 * inch, 0.8 * inch],
        ),
        Paragraph("<b>Global flags</b> available on every command:", BODY),
        Paragraph(
            "<font face='Courier'>--verbose</font> / "
            "<font face='Courier'>-v</font> — DEBUG-level logging.<br/>"
            "<font face='Courier'>--dry-run</font> — skip LLM calls and "
            "non-scrape network writes.<br/>"
            "<font face='Courier'>--version</font> — print version.",
            BODY,
        ),
    ]

    # --- 7. Output layout -----------------------------------------------
    story += [
        PageBreak(),
        Paragraph("7. Output layout", H1),
        Paragraph(
            "Each run creates a dated folder under <font face='Courier'>"
            "output/</font>. The score prefix on per-job folders makes "
            "<font face='Courier'>ls</font> give you a ranked view.",
            BODY,
        ),
        code(
            "output/\n"
            "└── 2026-04-16_python-backend/        # run-id\n"
            "    ├── jobs.json                     # raw scrape\n"
            "    ├── rankings.md                   # your triage view\n"
            "    └── 087_acme_senior-backend/      # prefix = score\n"
            "        ├── jd.md\n"
            "        ├── research.md\n"
            "        ├── research.json\n"
            "        ├── resume.yaml\n"
            "        ├── resume.tex\n"
            "        ├── resume.pdf\n"
            "        └── diff.md                   # what changed vs master"
        ),
        Paragraph(
            "<font face='Courier'>output/</font> is gitignored. Nothing is "
            "auto-pruned — old runs stick around until you delete them.",
            MUTED_BODY,
        ),
    ]

    # --- 8. Policy -------------------------------------------------------
    story += [
        Paragraph("8. Policy &amp; compliance", H1),
        Paragraph(
            "Naukri's Terms of Use restrict automated access. This tool is "
            "built for <b>single personal use</b>:",
            WARN,
        ),
        Paragraph(
            "&bull; You log in through your own real browser profile — "
            "no credential sharing, no throwaway accounts.<br/>"
            "&bull; Human-paced browsing (2–5s random delays, no parallelism, "
            "max ~10 JDs per run).<br/>"
            "&bull; Respects <font face='Courier'>robots.txt</font> for the "
            "user-agent we present.<br/>"
            "&bull; Scraped JDs and company data stay on your machine.<br/>"
            "&bull; <font face='Courier'>auth/storage_state.json</font> is "
            "chmod 600, gitignored, never logged. Don't share it.",
            BODY,
        ),
        Paragraph(
            "You accept that Naukri may flag or rate-limit the account, and "
            "that DOM changes may break selectors — expect occasional "
            "selector maintenance.",
            MUTED_BODY,
        ),
    ]

    # --- 9. Troubleshooting ---------------------------------------------
    story += [
        Paragraph("9. Troubleshooting", H1),
        simple_table(
            [
                ["Symptom", "Fix"],
                ["session expired, run naukri-tool login",
                    "Re-run naukri-tool login and log in again."],
                ["ANTHROPIC_API_KEY is not set",
                    "Fill it into .env."],
                ["Scrape returns 0 jobs",
                    "DOM changed — update scrape/selectors.py."],
                ["⚠ needs review flag on a tailored resume",
                    "Verifier flagged an un-traceable claim. Open diff.md."],
                ["Login loop / captcha",
                    "Log in via the headful window — manual is fine."],
                ["tectonic: command not found",
                    "Install per §4; single binary."],
            ],
            col_widths=[2.4 * inch, 4.0 * inch],
        ),
    ]

    # --- 10. Further reading --------------------------------------------
    story += [
        Paragraph("10. Further reading", H1),
        Paragraph(
            "&bull; <font face='Courier'>PLAN.md</font> — full design, "
            "decisions, milestone breakdown.<br/>"
            "&bull; <font face='Courier'>README.md</font> — quickstart and "
            "live milestone status.<br/>"
            "&bull; <font face='Courier'>docs/USER_GUIDE.md</font> — "
            "markdown source of this document.",
            BODY,
        ),
    ]

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"wrote {OUT.relative_to(OUT.parents[1])}")


if __name__ == "__main__":
    build()
