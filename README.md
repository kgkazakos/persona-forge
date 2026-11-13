# persona-forge

**Controlled persona generation with cross-session behavioural consistency validation.**

Part of the [CPR Orbital series](https://github.com/kgkazakos) — 40 open-source tools for AI-native product research, shipping every Friday.

---

## The problem

Most research personas are demographic snapshots dressed up as behavioural profiles. They list age ranges and job titles, then get used inconsistently across sessions — the "deliberate decision-maker" from the discovery study becomes impulsive in usability testing because nobody tracked the drift.

`persona-forge` treats personas as behavioural contracts. It generates richly profiled participants from seed attributes — decision style, risk tolerance, tech savviness — and validates whether they behave consistently across research sessions.

---

## Features

- **Controlled generation** — Deterministic personas from seed attributes: role, goals, pain points, decision style, risk tolerance, tech savviness
- **Behavioural trait library** — Rule-based trait assignment keyed to persona profile combinations
- **Cross-session consistency validation** — Detects contradictions, drift, and behavioural gaps across session snapshots
- **Severity-weighted consistency score** — High/medium/low severity flags weighted into a 0.0–1.0 score
- **Optional LLM enrichment** — Enriched narrative, realistic verbatim quotes, and subtle contradiction watch-outs via OpenAI / Anthropic / Gemini
- **Batch generation** — Generate multiple personas from a JSON seed array
- **JSON mode** — Full `--json` flag for CI and pipeline integration
- **Zero API key required** — All core functionality runs rule-based

---

## Install

```bash
pip install persona-forge
```

With LLM enrichment backends:

```bash
pip install 'persona-forge[openai]'
pip install 'persona-forge[anthropic]'
pip install 'persona-forge[gemini]'
pip install 'persona-forge[all]'   # all three
```

---

## CLI usage

### Generate a persona

```bash
persona-forge generate \
  --role "Senior Product Manager" \
  --goals "reduce time-to-insight" \
  --goals "align team on priorities" \
  --pain-points "too many tools" \
  --pain-points "inconsistent data" \
  --age-range "35-44" \
  --tech-savviness medium \
  --decision-style deliberate \
  --risk-tolerance moderate
```

**With LLM enrichment:**

```bash
persona-forge generate \
  --role "Staff Engineer" \
  --goals "automate everything" \
  --pain-points "manual toil" \
  --tech-savviness high \
  --decision-style impulsive \
  --risk-tolerance high \
  --llm-backend anthropic
```

**JSON output (CI-friendly):**

```bash
persona-forge generate \
  --role "Designer" \
  --goals "create usable interfaces" \
  --pain-points "vague feedback" \
  --json > persona.json
```

### Validate cross-session consistency

```bash
persona-forge validate tests/fixtures/sample_snapshots.json
```

With LLM-enriched clinical diagnosis:

```bash
persona-forge validate sessions.json --llm-backend openai --json
```

### Batch generate

```bash
persona-forge batch-generate seeds.json --output personas.json
```

Where `seeds.json` is an array of seed objects:

```json
[
  {
    "role": "Product Manager",
    "goals": ["reduce churn", "align team"],
    "pain_points": ["inconsistent data", "too many tools"],
    "tech_savviness": "medium",
    "decision_style": "deliberate",
    "risk_tolerance": "moderate"
  }
]
```

---

## Python API

```python
from persona_forge import generate_persona, validate_consistency, PersonaSeed, SessionSnapshot

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
print(persona.context_summary)

# Cross-session consistency
snapshots = [
    SessionSnapshot(
        session_id="s1",
        persona_id="pm_senior_001",
        stated_goals=["reduce time-to-insight"],
        observed_behaviours=["checked dashboard before speaking"],
        expressed_attitudes=["confident about roadmap"],
    ),
    SessionSnapshot(
        session_id="s2",
        persona_id="pm_senior_001",
        stated_goals=["get to decision faster"],
        observed_behaviours=["asked for data before committing"],
        expressed_attitudes=["trusts research team"],
    ),
]

report = validate_consistency(snapshots)
print(f"Score: {report.consistency_score:.2f}")
print(report.summary)
```

---

## Snapshot file format

The `validate` command accepts a JSON array of session snapshots:

```json
[
  {
    "session_id": "session_01",
    "persona_id": "pm_senior_001",
    "stated_goals": ["reduce time-to-insight", "align team"],
    "observed_behaviours": ["opened dashboard before speaking", "asked for data"],
    "expressed_attitudes": ["confident about roadmap", "trusts research team"],
    "raw_notes": "Optional free-text moderator notes."
  }
]
```

---

## LLM enrichment

All enrichment is additive — the rule-based output is always complete without API keys.

| Flag | Model | Adds to persona | Adds to report |
|---|---|---|---|
| `--llm-backend openai` | `gpt-4o-mini` | narrative, quotes, watch-outs | clinical diagnosis |
| `--llm-backend anthropic` | `claude-sonnet-4-6` | narrative, quotes, watch-outs | clinical diagnosis |
| `--llm-backend gemini` | `gemini-4-argon` | narrative, quotes, watch-outs | clinical diagnosis |

Set the appropriate environment variable before use:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GEMINI_API_KEY=...
```

Enriched fields appear under `enriched_narrative`, `enriched_quotes`, `enriched_contradictions`, and `enriched_diagnosis` in JSON output. These fields are `null` when no backend is specified.

The `llm.py` module is provided as community extension reference scaffolding and is not tested in CI.

---

## Consistency scoring

Flags are severity-weighted and normalised by the number of session pairs:

| Severity | Trigger | Weight |
|---|---|---|
| High | Direct goal contradiction (e.g. "speed" vs "thorough") | 0.15 |
| Medium | Attitude antonyms across sessions | 0.07 |
| Low | Behavioural gap (observed in session A, absent in session B) | 0.02 |

Score of 0.8+ indicates stable persona behaviour. Below 0.5 suggests significant drift worth probing in the next session.

---

## Part of the CPR Ecosystem

`persona-forge` is tool 10 of 40 in the [CPR Orbital series](https://github.com/kgkazakos).

**Closely related tools:**

- [`synthetic-participants`](https://github.com/kgkazakos/synthetic-participants) — richly profiled synthetic UX research participants
- [`interview-sim`](https://github.com/kgkazakos/interview-sim) — simulates full user interview sessions using generated personas
- [`bias-audit`](https://github.com/kgkazakos/bias-audit) — detects interviewer bias patterns across transcript corpora
- [`behavioral-profile`](https://github.com/kgkazakos/behavioral-profile) — models participant behavioural tendencies from prior research data

**The CPR Orbital series** covers the full AI-native research lifecycle: qualitative analysis, quantitative rigour, synthetic simulation, evaluation, research ops, and impact tracking. All tools are MIT-licensed, model-agnostic, and pip-installable.

---

## Development

```bash
git clone https://github.com/kgkazakos/persona-forge
cd persona-forge
pip install -e '.[dev]'
pytest tests/ -v
ruff check persona_forge/
```

CI runs on Python 3.10, 3.11, and 3.12.

---

## License

MIT — see [LICENSE](LICENSE).
