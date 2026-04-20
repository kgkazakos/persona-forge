"""Data models for persona-forge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BehaviouralTrait:
    """A single behavioural trait with its observed expressions."""

    name: str
    description: str
    expressed_as: list[str] = field(default_factory=list)
    contradicted_by: list[str] = field(default_factory=list)


@dataclass
class PersonaSeed:
    """Minimal seed data for persona generation."""

    role: str
    goals: list[str]
    pain_points: list[str]
    context: str = ""
    age_range: str = ""
    tech_savviness: str = "medium"  # low / medium / high
    decision_style: str = "deliberate"  # impulsive / deliberate / collaborative
    risk_tolerance: str = "moderate"  # low / moderate / high


@dataclass
class Persona:
    """A fully profiled research persona."""

    id: str
    name: str
    role: str
    age_range: str
    tech_savviness: str
    decision_style: str
    risk_tolerance: str
    goals: list[str]
    pain_points: list[str]
    behavioural_traits: list[BehaviouralTrait]
    motivations: list[str]
    frustrations: list[str]
    typical_quotes: list[str]
    context_summary: str
    # LLM-enriched fields (null when no backend)
    enriched_narrative: str | None = None
    enriched_quotes: list[str] | None = None
    enriched_contradictions: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "age_range": self.age_range,
            "tech_savviness": self.tech_savviness,
            "decision_style": self.decision_style,
            "risk_tolerance": self.risk_tolerance,
            "goals": self.goals,
            "pain_points": self.pain_points,
            "behavioural_traits": [
                {
                    "name": t.name,
                    "description": t.description,
                    "expressed_as": t.expressed_as,
                    "contradicted_by": t.contradicted_by,
                }
                for t in self.behavioural_traits
            ],
            "motivations": self.motivations,
            "frustrations": self.frustrations,
            "typical_quotes": self.typical_quotes,
            "context_summary": self.context_summary,
            "enriched_narrative": self.enriched_narrative,
            "enriched_quotes": self.enriched_quotes,
            "enriched_contradictions": self.enriched_contradictions,
        }


@dataclass
class SessionSnapshot:
    """A snapshot of persona behaviour observed in one research session."""

    session_id: str
    persona_id: str
    stated_goals: list[str]
    observed_behaviours: list[str]
    expressed_attitudes: list[str]
    raw_notes: str = ""


@dataclass
class ConsistencyFlag:
    """A single consistency issue flagged between sessions."""

    flag_type: str  # contradiction / drift / gap
    description: str
    session_a: str
    session_b: str
    severity: str  # low / medium / high
    attribute: str


@dataclass
class ConsistencyReport:
    """Cross-session behavioural consistency report for a persona."""

    persona_id: str
    sessions_compared: int
    consistency_score: float  # 0.0 – 1.0
    flags: list[ConsistencyFlag]
    stable_attributes: list[str]
    drifting_attributes: list[str]
    summary: str
    # LLM-enriched
    enriched_diagnosis: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "sessions_compared": self.sessions_compared,
            "consistency_score": round(self.consistency_score, 3),
            "flags": [
                {
                    "flag_type": f.flag_type,
                    "description": f.description,
                    "session_a": f.session_a,
                    "session_b": f.session_b,
                    "severity": f.severity,
                    "attribute": f.attribute,
                }
                for f in self.flags
            ],
            "stable_attributes": self.stable_attributes,
            "drifting_attributes": self.drifting_attributes,
            "summary": self.summary,
            "enriched_diagnosis": self.enriched_diagnosis,
        }
