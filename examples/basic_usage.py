"""Basic usage examples for persona-forge."""

from persona_forge import generate_persona, validate_consistency, PersonaSeed, SessionSnapshot

# --- Generate a persona ---
seed = PersonaSeed(
    role="Senior Product Manager",
    goals=["reduce time-to-insight", "align team on priorities"],
    pain_points=["too many tools", "inconsistent data quality"],
    context="Works at a mid-size SaaS company with a 6-person UXR team.",
    age_range="35-44",
    tech_savviness="medium",
    decision_style="deliberate",
    risk_tolerance="moderate",
)

persona = generate_persona(seed, persona_id="pm_senior_001")

print(f"Name: {persona.name}")
print(f"Role: {persona.role}")
print(f"\nContext: {persona.context_summary}")
print(f"\nBehavioural traits:")
for t in persona.behavioural_traits:
    print(f"  • {t.name}: {t.description}")

print(f"\nTypical quotes:")
for q in persona.typical_quotes:
    print(f'  "{q}"')

# --- Validate consistency across sessions ---
snapshots = [
    SessionSnapshot(
        session_id="session_01",
        persona_id="pm_senior_001",
        stated_goals=["reduce time-to-insight", "align team on priorities"],
        observed_behaviours=["checked dashboard before speaking", "asked for data before deciding"],
        expressed_attitudes=["confident about roadmap", "trusts research team"],
    ),
    SessionSnapshot(
        session_id="session_02",
        persona_id="pm_senior_001",
        stated_goals=["align team", "get to decision faster"],
        observed_behaviours=["referenced prior research", "asked clarifying questions"],
        expressed_attitudes=["relies on data", "open to challenge"],
    ),
]

report = validate_consistency(snapshots)
print(f"\n--- Consistency Report ---")
print(f"Score: {report.consistency_score:.2f}")
print(f"Summary: {report.summary}")
if report.flags:
    print(f"Flags: {len(report.flags)}")
    for f in report.flags:
        print(f"  [{f.severity}] {f.flag_type}: {f.description}")
