"""Typer CLI surface — see PLAN.md §12.

Milestone 1 delivers a working command parser with typed options and a clean
help surface. Each command is a stub that logs its inputs and notes the
milestone that will implement it. Running any command proves: (a) the package
installs, (b) config loads, (c) logging works, (d) option parsing matches the
planned surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer

from naukri_tool import __version__
from naukri_tool.config import get_settings
from naukri_tool.logging_setup import configure_logging

app = typer.Typer(
    name="naukri-tool",
    help="Personal Naukri job search + resume tailoring tool.",
    no_args_is_help=True,
    add_completion=False,
)

log = structlog.get_logger(__name__)


# --- Global state set by the root callback -------------------------------

class _GlobalOptions:
    dry_run: bool = False
    verbose: bool = False


def _stub(milestone: int, command: str, **inputs: object) -> None:
    """Log that a command is a stub and show what it would have run on.

    Exits 0 so scripting stays predictable; the log line makes the stub
    status obvious.
    """
    log.info(
        "stub.not_implemented",
        command=command,
        milestone=f"M{milestone}",
        dry_run=_GlobalOptions.dry_run,
        **inputs,
    )
    typer.echo(
        f"[{command}] stub — will be implemented in Milestone {milestone}. "
        "See PLAN.md §14.",
    )


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"naukri-tool {__version__}")
        raise typer.Exit()


# --- Root callback --------------------------------------------------------

@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable DEBUG-level logging."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Skip LLM calls and non-scrape network writes. See PLAN.md §12.",
        ),
    ] = False,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Shared options applied to every subcommand."""
    _GlobalOptions.verbose = verbose
    _GlobalOptions.dry_run = dry_run
    configure_logging(verbose=verbose)

    # Touch settings early so a malformed .env fails loud here, not mid-run.
    settings = get_settings()
    log.debug(
        "config.loaded",
        resume_master_path=str(settings.resume_master_path),
        auth_dir=str(settings.auth_dir),
        output_dir=str(settings.output_dir),
        has_anthropic_key=bool(settings.anthropic_api_key),
    )


# --- Commands -------------------------------------------------------------

@app.command()
def bootstrap(
    pdf_path: Annotated[
        Path,
        typer.Argument(
            help="Path to your existing resume PDF.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
) -> None:
    """One-time: extract your PDF into `resumes/master.yaml.draft` for review."""
    _stub(3, "bootstrap", pdf_path=str(pdf_path))


@app.command()
def login() -> None:
    """Headful Naukri login; saves `auth/storage_state.json`."""
    _stub(4, "login")


@app.command()
def search(
    query: Annotated[str, typer.Argument(help='Keyword query, e.g. "python backend".')],
    exp: Annotated[
        int | None,
        typer.Option("--exp", help="Years of experience filter."),
    ] = None,
    loc: Annotated[
        str | None,
        typer.Option("--loc", help="Location filter, e.g. 'bangalore'."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Max jobs to process."),
    ] = 10,
) -> None:
    """Full pipeline: scrape → research → rank → tailor."""
    _stub(11, "search", query=query, exp=exp, loc=loc, limit=limit)


@app.command()
def scrape(
    query: Annotated[str, typer.Argument(help="Keyword query.")],
    limit: Annotated[int, typer.Option("--limit", help="Max jobs to scrape.")] = 10,
) -> None:
    """Scrape only — writes `jobs.json` and per-job JD pages."""
    _stub(5, "scrape", query=query, limit=limit)


@app.command()
def rank(
    run_id: Annotated[str, typer.Argument(help="Run folder under `output/`.")],
) -> None:
    """Re-rank a prior run without re-scraping."""
    _stub(8, "rank", run_id=run_id)


@app.command()
def tailor(
    run_id: Annotated[str, typer.Argument(help="Run folder under `output/`.")],
    job_slug: Annotated[
        str | None,
        typer.Argument(help="Specific job folder; omit with --all to tailor every job."),
    ] = None,
    all_jobs: Annotated[
        bool,
        typer.Option("--all", help="Re-tailor every job in the run."),
    ] = False,
) -> None:
    """Re-tailor one job (or every job with --all)."""
    if all_jobs and job_slug is not None:
        raise typer.BadParameter("Pass either a job_slug or --all, not both.")
    if not all_jobs and job_slug is None:
        raise typer.BadParameter("Pass a job_slug or --all.")
    _stub(9, "tailor", run_id=run_id, job_slug=job_slug, all_jobs=all_jobs)


# "open" shadows the builtin — register under a renamed Python function.
@app.command("open")
def open_run(
    run_id: Annotated[str, typer.Argument(help="Run folder under `output/`.")],
) -> None:
    """Open a run's `rankings.md` in `$EDITOR`."""
    _stub(11, "open", run_id=run_id)


if __name__ == "__main__":
    app()
