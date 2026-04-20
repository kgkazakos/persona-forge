"""CLI for persona-forge."""

from __future__ import annotations

import json
import sys

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .consistency import validate_consistency
from .core import generate_persona
from .models import PersonaSeed, SessionSnapshot

console = Console()

_BACKENDS = ["openai", "anthropic", "gemini"]


def _optional_enrich_persona(persona, backend):
    if backend:
        from .llm import enrich_persona
        return enrich_persona(persona, backend)
    return persona


def _optional_enrich_report(report, backend):
    if backend:
        from .llm import enrich_consistency_report
        return enrich_consistency_report(report, backend)
    return report


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="persona-forge")
def cli():
    """persona-forge — controlled persona generation with consistency validation."""


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

@cli.command("generate")
@click.option("--role", required=True, help="Participant role (e.g. 'Senior Product Manager')")
@click.option("--goals", required=True, multiple=True, help="Goals (repeat for multiple)")
@click.option("--pain-points", required=True, multiple=True, help="Pain points (repeat for multiple)")
@click.option("--context", default="", help="Optional context sentence")
@click.option("--age-range", default="", help="Age range, e.g. '35-44'")
@click.option("--tech-savviness", default="medium", type=click.Choice(["low", "medium", "high"]))
@click.option("--decision-style", default="deliberate", type=click.Choice(["impulsive", "deliberate", "collaborative"]))
@click.option("--risk-tolerance", default="moderate", type=click.Choice(["low", "moderate", "high"]))
@click.option("--llm-backend", default=None, type=click.Choice(_BACKENDS), help="LLM backend for enrichment")
@click.option("--json", "output_json", is_flag=True, help="Output JSON for CI/pipeline use")
@click.option("--id", "persona_id", default=None, help="Custom persona ID")
def generate(role, goals, pain_points, context, age_range, tech_savviness,
             decision_style, risk_tolerance, llm_backend, output_json, persona_id):
    """Generate a fully profiled research persona from seed attributes."""
    seed = PersonaSeed(
        role=role,
        goals=list(goals),
        pain_points=list(pain_points),
        context=context,
        age_range=age_range,
        tech_savviness=tech_savviness,
        decision_style=decision_style,
        risk_tolerance=risk_tolerance,
    )

    with console.status("[bold green]Generating persona…"):
        persona = generate_persona(seed, persona_id)

    if llm_backend:
        with console.status(f"[bold blue]Enriching with {llm_backend}…"):
            persona = _optional_enrich_persona(persona, llm_backend)

    if output_json:
        click.echo(json.dumps(persona.to_dict(), indent=2))
        return

    # Rich display
    console.print()
    console.print(Panel(
        f"[bold]{persona.name}[/bold]  ·  [dim]{persona.role}[/dim]"
        + (f"  ·  {persona.age_range}" if persona.age_range else ""),
        title=f"[green]Persona: {persona.id}[/green]",
        border_style="green",
    ))

    console.print(f"\n[dim]{persona.context_summary}[/dim]")

    # Traits
    trait_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    trait_table.add_column("Trait", style="bold", width=28)
    trait_table.add_column("Description", width=42)
    trait_table.add_column("Expressed as", width=38)
    for t in persona.behavioural_traits:
        trait_table.add_row(t.name, t.description, "\n".join(f"• {e}" for e in t.expressed_as))
    console.print("\n[bold]Behavioural Traits[/bold]")
    console.print(trait_table)

    console.print("[bold]Typical Quotes[/bold]")
    for q in persona.typical_quotes:
        console.print(f'  [italic]"{q}"[/italic]')

    console.print("\n[bold]Goals[/bold]")
    for g in persona.goals:
        console.print(f"  • {g}")

    console.print("\n[bold]Pain Points[/bold]")
    for p in persona.pain_points:
        console.print(f"  • {p}")

    if persona.enriched_narrative:
        console.print(Panel(persona.enriched_narrative, title="[blue]LLM Narrative[/blue]", border_style="blue"))

    if persona.enriched_quotes:
        console.print("\n[blue bold]LLM-generated Quotes[/blue bold]")
        for q in persona.enriched_quotes:
            console.print(f'  [italic]"{q}"[/italic]')

    if persona.enriched_contradictions:
        console.print("\n[yellow bold]Behavioural Watch-outs[/yellow bold]")
        for c in persona.enriched_contradictions:
            console.print(f"  ⚠  {c}")

    console.print()


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@cli.command("validate")
@click.argument("snapshots_file", type=click.Path(exists=True))
@click.option("--llm-backend", default=None, type=click.Choice(_BACKENDS))
@click.option("--json", "output_json", is_flag=True)
def validate(snapshots_file, llm_backend, output_json):
    """Validate cross-session behavioural consistency from a JSON snapshots file.

    SNAPSHOTS_FILE must be a JSON array of session snapshot objects:
    [{"session_id": "s1", "persona_id": "p001", "stated_goals": [...],
      "observed_behaviours": [...], "expressed_attitudes": [...], "raw_notes": "..."}]
    """
    try:
        with open(snapshots_file) as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]Error reading snapshots file: {e}[/red]")
        sys.exit(1)

    snapshots = [
        SessionSnapshot(
            session_id=s["session_id"],
            persona_id=s["persona_id"],
            stated_goals=s.get("stated_goals", []),
            observed_behaviours=s.get("observed_behaviours", []),
            expressed_attitudes=s.get("expressed_attitudes", []),
            raw_notes=s.get("raw_notes", ""),
        )
        for s in raw
    ]

    with console.status("[bold green]Validating consistency…"):
        report = validate_consistency(snapshots)

    if llm_backend:
        with console.status(f"[bold blue]Enriching with {llm_backend}…"):
            report = _optional_enrich_report(report, llm_backend)

    if output_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    # Rich display
    score = report.consistency_score
    colour = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
    console.print()
    console.print(Panel(
        f"Consistency Score: [{colour}]{score:.2f}[/{colour}]   "
        f"Sessions compared: {report.sessions_compared}   "
        f"Flags: {len(report.flags)}",
        title=f"[bold]Persona {report.persona_id} — Consistency Report[/bold]",
        border_style=colour,
    ))

    console.print(f"\n[dim]{report.summary}[/dim]")

    if report.flags:
        flag_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        flag_table.add_column("Type", width=14)
        flag_table.add_column("Severity", width=8)
        flag_table.add_column("Attribute", width=22)
        flag_table.add_column("Description", width=52)
        for fl in report.flags:
            sev_colour = "red" if fl.severity == "high" else "yellow" if fl.severity == "medium" else "dim"
            flag_table.add_row(
                fl.flag_type,
                f"[{sev_colour}]{fl.severity}[/{sev_colour}]",
                fl.attribute,
                fl.description,
            )
        console.print("\n[bold]Flags[/bold]")
        console.print(flag_table)

    if report.stable_attributes:
        console.print("[green]Stable:[/green]  " + ", ".join(report.stable_attributes))
    if report.drifting_attributes:
        console.print("[yellow]Drifting:[/yellow] " + ", ".join(report.drifting_attributes))

    if report.enriched_diagnosis:
        console.print(Panel(report.enriched_diagnosis, title="[blue]LLM Diagnosis[/blue]", border_style="blue"))

    console.print()


# ---------------------------------------------------------------------------
# batch-generate
# ---------------------------------------------------------------------------

@cli.command("batch-generate")
@click.argument("seeds_file", type=click.Path(exists=True))
@click.option("--llm-backend", default=None, type=click.Choice(_BACKENDS))
@click.option("--output", default="personas.json", help="Output JSON file path")
def batch_generate(seeds_file, llm_backend, output):
    """Generate multiple personas from a JSON array of seed objects."""
    try:
        with open(seeds_file) as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    results = []
    with console.status("[bold green]Generating personas…") as status:
        for i, s in enumerate(raw, 1):
            status.update(f"[bold green]Persona {i}/{len(raw)}…")
            seed = PersonaSeed(
                role=s["role"],
                goals=s.get("goals", []),
                pain_points=s.get("pain_points", []),
                context=s.get("context", ""),
                age_range=s.get("age_range", ""),
                tech_savviness=s.get("tech_savviness", "medium"),
                decision_style=s.get("decision_style", "deliberate"),
                risk_tolerance=s.get("risk_tolerance", "moderate"),
            )
            persona = generate_persona(seed, s.get("id"))
            if llm_backend:
                persona = _optional_enrich_persona(persona, llm_backend)
            results.append(persona.to_dict())

    with open(output, "w") as f:
        json.dump(results, f, indent=2)

    console.print(f"[green]✓[/green] {len(results)} persona(s) written to [bold]{output}[/bold]")


def main():
    cli()
