"""`autoresearch` Typer CLI."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help="Compliance-training deck generator.")


@app.command()
def generate(
    topic: str = typer.Option(..., help="Compliance topic, e.g. 'Anti-bribery for partners'."),
    audience: str = typer.Option("procurement partners", help="Audience persona."),
    out: Path = typer.Option(Path("out.pptx"), help="Output .pptx path."),
    mode: str = typer.Option(
        "demo",
        help=(
            "'demo' uses seeded FakeLLMClient (no API keys); "
            "'baseline' uses the sparse pre-harness seed; "
            "'real' would use a live LLM (not yet wired)."
        ),
    ),
) -> None:
    """Run the full pipeline and write a .pptx deck."""
    from .graph import build_pipeline
    from .seeds import baseline_client, upgraded_client

    if mode == "baseline":
        client, search = baseline_client(topic, audience)
    elif mode == "demo":
        client, search = upgraded_client(topic, audience)
    elif mode == "real":
        raise typer.BadParameter("real mode requires a live LLM client; not yet wired in this POC.")
    else:
        raise typer.BadParameter(f"unknown mode {mode!r}; choose demo|baseline|real")

    graph = build_pipeline(client=client, out_path=out, search=search)
    final = graph.invoke({"topic": topic, "audience": audience})
    typer.echo(final.get("output_path", "(no output)"))


@app.command()
def score(
    topic: str = typer.Option(...),
    audience: str = typer.Option("procurement partners"),
    mode: str = typer.Option("demo", help="demo|baseline"),
) -> None:
    """Generate (in-memory) and print the eval rubric scores."""
    import tempfile

    from .evals import score_deck
    from .graph import build_pipeline
    from .seeds import baseline_client, upgraded_client

    client, search = (upgraded_client if mode == "demo" else baseline_client)(topic, audience)
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        out_path = tmp.name
    graph = build_pipeline(client=client, out_path=out_path, search=search)
    final = graph.invoke({"topic": topic, "audience": audience})
    s = score_deck(final["deck_plan"])
    typer.echo(s.as_table())


@app.command()
def version() -> None:
    """Print package version."""
    from . import __version__

    typer.echo(__version__)


if __name__ == "__main__":  # pragma: no cover
    app()
