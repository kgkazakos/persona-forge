"""Rule-based persona generation — zero API calls required."""

from __future__ import annotations

import hashlib
import random
from typing import Any

from .models import BehaviouralTrait, Persona, PersonaSeed

# ---------------------------------------------------------------------------
# Trait library — keyed by (tech_savviness, decision_style, risk_tolerance)
# ---------------------------------------------------------------------------

_TRAIT_POOL: dict[str, list[dict[str, Any]]] = {
    "tech_high": [
        {
            "name": "Tool-first problem solving",
            "description": "Reaches for software or automation before manual approaches",
            "expressed_as": ["searches for plugins/extensions immediately", "builds scripts for repetitive tasks"],
            "contradicted_by": ["avoids new tools without research", "prefers pen-and-paper for ideation"],
        },
        {
            "name": "Abstraction comfort",
            "description": "Comfortable reasoning in systems and layers rather than surface UI",
            "expressed_as": ["talks in APIs and data models", "sketches system diagrams unprompted"],
            "contradicted_by": ["gets lost in UI navigation", "prefers step-by-step screenshots"],
        },
    ],
    "tech_medium": [
        {
            "name": "Selective adoption",
            "description": "Adopts tools when they reduce effort, not for novelty",
            "expressed_as": ["waits for social proof", "asks colleagues before switching tools"],
            "contradicted_by": ["installs every new app", "manually processes data that could be automated"],
        },
        {
            "name": "Template reliance",
            "description": "Reaches for templates and prior examples to reduce cognitive load",
            "expressed_as": ["keeps personal libraries of past work", "searches Notion/Google Docs before starting fresh"],
            "contradicted_by": ["always starts from blank", "rejects structure as limiting"],
        },
    ],
    "tech_low": [
        {
            "name": "Tactile preference",
            "description": "Trusts physical or visible artefacts over digital abstractions",
            "expressed_as": ["prints reports to annotate", "prefers whiteboards over Miro"],
            "contradicted_by": ["comfortable with complex dashboards", "manages work entirely in task software"],
        },
        {
            "name": "Social validation loop",
            "description": "Validates understanding through conversation rather than documentation",
            "expressed_as": ["calls colleagues to confirm before acting", "distrusts information not spoken by a person"],
            "contradicted_by": ["trusts automated system outputs", "acts on dashboards without discussion"],
        },
    ],
    "decision_impulsive": [
        {
            "name": "Speed-over-completeness bias",
            "description": "Acts on sufficient information rather than waiting for certainty",
            "expressed_as": ["ships before full validation", "says 'we can iterate' when others want more data"],
            "contradicted_by": ["requests exhaustive analysis before deciding", "pauses on low-stakes decisions"],
        },
    ],
    "decision_deliberate": [
        {
            "name": "Evidence anchoring",
            "description": "Explicitly references data or precedent before committing to a direction",
            "expressed_as": ["quotes research in meetings", "returns to original brief when scope creeps"],
            "contradicted_by": ["decides without citing evidence", "moves quickly on gut feel"],
        },
    ],
    "decision_collaborative": [
        {
            "name": "Consensus building",
            "description": "Delays commitment until key stakeholders have been heard",
            "expressed_as": ["holds pre-mortem discussions", "shares drafts widely before finalising"],
            "contradicted_by": ["decides unilaterally", "avoids sharing work before it is polished"],
        },
    ],
    "risk_low": [
        {
            "name": "Reversibility seeking",
            "description": "Prefers decisions that can be undone or adjusted",
            "expressed_as": ["favours pilots over full rollouts", "asks 'can we turn this off?' before committing"],
            "contradicted_by": ["makes irreversible architectural decisions quickly", "comfortable with permanent changes"],
        },
    ],
    "risk_moderate": [
        {
            "name": "Bounded experimentation",
            "description": "Willing to try new approaches within defined guardrails",
            "expressed_as": ["runs A/B tests", "sets explicit success criteria before experimenting"],
            "contradicted_by": ["experiments without metrics", "refuses to deviate from proven patterns"],
        },
    ],
    "risk_high": [
        {
            "name": "Opportunity cost sensitivity",
            "description": "Weighs the risk of inaction as heavily as the risk of action",
            "expressed_as": ["frames delay as the dangerous option", "references competitors when pushing for boldness"],
            "contradicted_by": ["defaults to 'wait and see'", "avoids committing until risk is minimal"],
        },
    ],
}

_PERSONA_NAMES = [
    "Alex Chen", "Morgan Reyes", "Sam Okafor", "Jordan Patel", "Taylor Müller",
    "Drew Nakamura", "Casey Lindqvist", "Riley Osei", "Quinn Fernandez", "Avery Kowalski",
    "Blake Andersen", "Skyler Nguyen", "Jamie Okonkwo", "Rowan Bergström", "Finley Delacroix",
]

_MOTIVATION_MAP = {
    "impulsive": ["making a visible impact quickly", "being the first to ship", "maintaining momentum"],
    "deliberate": ["reaching the right answer", "protecting the team from avoidable mistakes", "building durable knowledge"],
    "collaborative": ["bringing everyone along", "creating shared ownership", "avoiding surprises for stakeholders"],
}

_FRUSTRATION_MAP = {
    "low": ["being pushed to move before risks are understood", "decisions made without her input", "scope expanding mid-project"],
    "moderate": ["analysis paralysis in others", "unclear success criteria", "inconsistent access to user data"],
    "high": ["excessive process when speed matters", "stakeholders who optimise for comfort over outcomes", "being asked to wait"],
}

_QUOTE_TEMPLATES = {
    ("high", "impulsive", "high"): [
        "We have enough signal — let's ship and learn.",
        "The real risk is doing nothing.",
    ],
    ("high", "deliberate", "moderate"): [
        "I want to see the data before we commit to this direction.",
        "What does the research actually say about this?",
    ],
    ("medium", "collaborative", "low"): [
        "Let me get a few more eyes on this before we decide.",
        "I need to understand what's driving this before I can support it.",
    ],
    ("low", "deliberate", "low"): [
        "Can we print the report so I can go through it properly?",
        "I'd rather call a quick sync than assume I've understood correctly.",
    ],
    ("medium", "impulsive", "moderate"): [
        "Good enough to start — we'll fix it as we go.",
        "I'd rather have something in front of users than keep refining in a vacuum.",
    ],
}


def _pick_quotes(seed: PersonaSeed, rng: random.Random) -> list[str]:
    key = (seed.tech_savviness, seed.decision_style, seed.risk_tolerance)
    direct = _QUOTE_TEMPLATES.get(key)
    if direct:
        return direct
    # fall back: pick from nearest key
    all_quotes = [q for qs in _QUOTE_TEMPLATES.values() for q in qs]
    rng.shuffle(all_quotes)
    return all_quotes[:2]


def _select_traits(seed: PersonaSeed, rng: random.Random) -> list[BehaviouralTrait]:
    pool: list[dict[str, Any]] = []
    pool += _TRAIT_POOL.get(f"tech_{seed.tech_savviness}", [])
    pool += _TRAIT_POOL.get(f"decision_{seed.decision_style}", [])
    pool += _TRAIT_POOL.get(f"risk_{seed.risk_tolerance}", [])
    rng.shuffle(pool)
    selected = pool[:4]
    return [
        BehaviouralTrait(
            name=t["name"],
            description=t["description"],
            expressed_as=t["expressed_as"],
            contradicted_by=t["contradicted_by"],
        )
        for t in selected
    ]


def _stable_seed(seed: PersonaSeed) -> int:
    """Derive a stable integer seed from the PersonaSeed for reproducible names."""
    key = f"{seed.role}|{seed.tech_savviness}|{seed.decision_style}|{seed.risk_tolerance}"
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)


def generate_persona(seed: PersonaSeed, persona_id: str | None = None) -> Persona:
    """
    Generate a fully profiled persona from a PersonaSeed.

    Fully rule-based — no API calls.
    """
    rng = random.Random(_stable_seed(seed))

    pid = persona_id or f"persona_{abs(hash(seed.role)) % 9999:04d}"
    name = rng.choice(_PERSONA_NAMES)

    traits = _select_traits(seed, rng)
    motivations = _MOTIVATION_MAP.get(seed.decision_style, ["doing good work", "making progress"])
    frustrations = _FRUSTRATION_MAP.get(seed.risk_tolerance, ["unclear expectations", "slow feedback loops"])
    quotes = _pick_quotes(seed, rng)

    context_summary = (
        f"{name} is a {seed.role} "
        + (f"({seed.age_range}) " if seed.age_range else "")
        + f"with {seed.tech_savviness} technical savviness, "
        f"a {seed.decision_style} decision style, and {seed.risk_tolerance} risk tolerance. "
        + (f"{seed.context} " if seed.context else "")
        + f"Their primary goals are: {'; '.join(seed.goals[:2])}."
    )

    return Persona(
        id=pid,
        name=name,
        role=seed.role,
        age_range=seed.age_range,
        tech_savviness=seed.tech_savviness,
        decision_style=seed.decision_style,
        risk_tolerance=seed.risk_tolerance,
        goals=seed.goals,
        pain_points=seed.pain_points,
        behavioural_traits=traits,
        motivations=motivations,
        frustrations=frustrations,
        typical_quotes=quotes,
        context_summary=context_summary,
    )
