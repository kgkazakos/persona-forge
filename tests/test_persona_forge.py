"""Tests for persona-forge."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from persona_forge import (
    generate_persona,
    validate_consistency,
    PersonaSeed,
    SessionSnapshot,
)
from persona_forge.core import _stable_seed
from persona_forge.models import BehaviouralTrait, ConsistencyFlag


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_seed():
    return PersonaSeed(
        role="Senior Product Manager",
        goals=["reduce time-to-insight", "align team on priorities"],
        pain_points=["too many tools", "inconsistent data"],
        context="Works at a mid-size SaaS company.",
        age_range="35-44",
        tech_savviness="medium",
        decision_style="deliberate",
        risk_tolerance="moderate",
    )


@pytest.fixture
def high_tech_seed():
    return PersonaSeed(
        role="Staff Engineer",
        goals=["automate everything", "scale systems"],
        pain_points=["manual toil", "slow deploys"],
        tech_savviness="high",
        decision_style="impulsive",
        risk_tolerance="high",
    )


@pytest.fixture
def low_tech_seed():
    return PersonaSeed(
        role="Customer Support Lead",
        goals=["resolve tickets fast", "reduce escalations"],
        pain_points=["complex tools", "lack of training"],
        tech_savviness="low",
        decision_style="collaborative",
        risk_tolerance="low",
    )


@pytest.fixture
def stable_snapshots():
    return [
        SessionSnapshot(
            session_id="s1",
            persona_id="p001",
            stated_goals=["reduce time-to-insight", "align team"],
            observed_behaviours=["checked dashboard first", "asked for data before deciding"],
            expressed_attitudes=["confident about the roadmap", "trusts the research team"],
        ),
        SessionSnapshot(
            session_id="s2",
            persona_id="p001",
            stated_goals=["reduce time-to-insight", "align on priorities"],
            observed_behaviours=["referenced past research", "asked for data"],
            expressed_attitudes=["confident about the plan", "relies on research"],
        ),
    ]


@pytest.fixture
def contradictory_snapshots():
    return [
        SessionSnapshot(
            session_id="s1",
            persona_id="p002",
            stated_goals=["speed up delivery", "ship fast"],
            observed_behaviours=["skipped review step"],
            expressed_attitudes=["loves the new tool", "urgent to move"],
        ),
        SessionSnapshot(
            session_id="s2",
            persona_id="p002",
            stated_goals=["thorough validation", "complete testing"],
            observed_behaviours=["requested exhaustive analysis"],
            expressed_attitudes=["hates rushing", "rejects incomplete work"],
        ),
    ]


# ---------------------------------------------------------------------------
# core.py tests
# ---------------------------------------------------------------------------

class TestGeneratePersona:
    def test_returns_persona(self, basic_seed):
        p = generate_persona(basic_seed)
        assert p.name
        assert p.role == "Senior Product Manager"
        assert p.tech_savviness == "medium"
        assert p.decision_style == "deliberate"
        assert p.risk_tolerance == "moderate"

    def test_goals_preserved(self, basic_seed):
        p = generate_persona(basic_seed)
        assert p.goals == basic_seed.goals

    def test_pain_points_preserved(self, basic_seed):
        p = generate_persona(basic_seed)
        assert p.pain_points == basic_seed.pain_points

    def test_traits_generated(self, basic_seed):
        p = generate_persona(basic_seed)
        assert len(p.behavioural_traits) >= 1
        assert all(isinstance(t, BehaviouralTrait) for t in p.behavioural_traits)

    def test_traits_have_required_fields(self, basic_seed):
        p = generate_persona(basic_seed)
        for t in p.behavioural_traits:
            assert t.name
            assert t.description
            assert isinstance(t.expressed_as, list)
            assert isinstance(t.contradicted_by, list)

    def test_typical_quotes_generated(self, basic_seed):
        p = generate_persona(basic_seed)
        assert len(p.typical_quotes) >= 1
        assert all(isinstance(q, str) for q in p.typical_quotes)

    def test_context_summary_contains_role(self, basic_seed):
        p = generate_persona(basic_seed)
        assert "Senior Product Manager" in p.context_summary

    def test_custom_id(self, basic_seed):
        p = generate_persona(basic_seed, persona_id="custom-001")
        assert p.id == "custom-001"

    def test_deterministic(self, basic_seed):
        p1 = generate_persona(basic_seed)
        p2 = generate_persona(basic_seed)
        assert p1.name == p2.name
        assert p1.behavioural_traits[0].name == p2.behavioural_traits[0].name

    def test_high_tech_seed(self, high_tech_seed):
        p = generate_persona(high_tech_seed)
        assert p.role == "Staff Engineer"
        assert p.tech_savviness == "high"

    def test_low_tech_seed(self, low_tech_seed):
        p = generate_persona(low_tech_seed)
        assert p.role == "Customer Support Lead"
        assert p.tech_savviness == "low"

    def test_motivations_not_empty(self, basic_seed):
        p = generate_persona(basic_seed)
        assert len(p.motivations) >= 1

    def test_frustrations_not_empty(self, basic_seed):
        p = generate_persona(basic_seed)
        assert len(p.frustrations) >= 1

    def test_llm_fields_null_without_backend(self, basic_seed):
        p = generate_persona(basic_seed)
        assert p.enriched_narrative is None
        assert p.enriched_quotes is None
        assert p.enriched_contradictions is None

    def test_age_range_optional(self):
        seed = PersonaSeed(
            role="Designer",
            goals=["create usable interfaces"],
            pain_points=["unclear requirements"],
        )
        p = generate_persona(seed)
        assert p.age_range == ""

    def test_to_dict_keys(self, basic_seed):
        p = generate_persona(basic_seed)
        d = p.to_dict()
        for key in ["id", "name", "role", "goals", "pain_points",
                    "behavioural_traits", "typical_quotes",
                    "enriched_narrative", "enriched_quotes"]:
            assert key in d

    def test_to_dict_traits_structure(self, basic_seed):
        p = generate_persona(basic_seed)
        d = p.to_dict()
        for t in d["behavioural_traits"]:
            assert "name" in t
            assert "description" in t
            assert "expressed_as" in t

    def test_different_seeds_different_traits(self, basic_seed, high_tech_seed):
        p1 = generate_persona(basic_seed)
        p2 = generate_persona(high_tech_seed)
        names1 = {t.name for t in p1.behavioural_traits}
        names2 = {t.name for t in p2.behavioural_traits}
        # At least one different trait expected
        assert names1 != names2 or p1.name != p2.name  # different profile

    def test_stable_seed_deterministic(self, basic_seed):
        s1 = _stable_seed(basic_seed)
        s2 = _stable_seed(basic_seed)
        assert s1 == s2

    def test_stable_seed_varies_by_role(self, basic_seed, high_tech_seed):
        s1 = _stable_seed(basic_seed)
        s2 = _stable_seed(high_tech_seed)
        assert s1 != s2


# ---------------------------------------------------------------------------
# consistency.py tests
# ---------------------------------------------------------------------------

class TestValidateConsistency:
    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_consistency([])

    def test_single_session_no_flags(self, stable_snapshots):
        report = validate_consistency([stable_snapshots[0]])
        assert report.sessions_compared == 1
        assert len(report.flags) == 0
        assert report.consistency_score == 1.0

    def test_stable_sessions_high_score(self, stable_snapshots):
        report = validate_consistency(stable_snapshots)
        assert report.consistency_score >= 0.7
        # Should have few or no high-severity flags
        high_flags = [f for f in report.flags if f.severity == "high"]
        assert len(high_flags) == 0

    def test_contradictory_sessions_lower_score(self, contradictory_snapshots):
        report = validate_consistency(contradictory_snapshots)
        assert report.consistency_score < 1.0
        assert len(report.flags) > 0

    def test_contradiction_flag_type(self, contradictory_snapshots):
        report = validate_consistency(contradictory_snapshots)
        types = {f.flag_type for f in report.flags}
        assert "contradiction" in types

    def test_flag_has_required_fields(self, contradictory_snapshots):
        report = validate_consistency(contradictory_snapshots)
        for f in report.flags:
            assert isinstance(f, ConsistencyFlag)
            assert f.flag_type in {"contradiction", "drift", "gap"}
            assert f.severity in {"low", "medium", "high"}
            assert f.session_a
            assert f.session_b

    def test_score_bounded(self, contradictory_snapshots):
        report = validate_consistency(contradictory_snapshots)
        assert 0.0 <= report.consistency_score <= 1.0

    def test_stable_attributes_populated(self, stable_snapshots):
        report = validate_consistency(stable_snapshots)
        assert isinstance(report.stable_attributes, list)

    def test_summary_not_empty(self, stable_snapshots):
        report = validate_consistency(stable_snapshots)
        assert len(report.summary) > 10

    def test_persona_id_preserved(self, stable_snapshots):
        report = validate_consistency(stable_snapshots)
        assert report.persona_id == "p001"

    def test_to_dict_keys(self, stable_snapshots):
        report = validate_consistency(stable_snapshots)
        d = report.to_dict()
        for key in ["persona_id", "sessions_compared", "consistency_score",
                    "flags", "stable_attributes", "drifting_attributes", "summary"]:
            assert key in d

    def test_enriched_diagnosis_null_without_backend(self, stable_snapshots):
        report = validate_consistency(stable_snapshots)
        assert report.enriched_diagnosis is None

    def test_multiple_sessions(self):
        snaps = [
            SessionSnapshot(
                session_id=f"s{i}",
                persona_id="p003",
                stated_goals=["improve workflow", "reduce errors"],
                observed_behaviours=["uses shortcuts", "checks documentation"],
                expressed_attitudes=["confident", "trusts the process"],
            )
            for i in range(4)
        ]
        report = validate_consistency(snaps)
        assert report.sessions_compared == 4
        assert report.consistency_score >= 0.8

    def test_gap_detection(self):
        snaps = [
            SessionSnapshot(
                session_id="s1",
                persona_id="p004",
                stated_goals=["automate reporting"],
                observed_behaviours=["wrote a script to automate the task"],
                expressed_attitudes=["confident"],
            ),
            SessionSnapshot(
                session_id="s2",
                persona_id="p004",
                stated_goals=["automate reporting"],
                observed_behaviours=["did something completely unrelated"],
                expressed_attitudes=["confident"],
            ),
        ]
        report = validate_consistency(snaps)
        gap_flags = [f for f in report.flags if f.flag_type == "gap"]
        assert len(gap_flags) >= 1

    def test_high_severity_penalises_more(self):
        high_severity_snaps = [
            SessionSnapshot(
                session_id="s1",
                persona_id="p005",
                stated_goals=["speed things up quickly"],
                observed_behaviours=[],
                expressed_attitudes=[],
            ),
            SessionSnapshot(
                session_id="s2",
                persona_id="p005",
                stated_goals=["thorough exhaustive complete process"],
                observed_behaviours=[],
                expressed_attitudes=[],
            ),
        ]
        report = validate_consistency(high_severity_snaps)
        # High contradictions should drop score below 0.9
        assert report.consistency_score < 0.9


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

class TestCLIImport:
    def test_cli_importable(self):
        from persona_forge.cli import cli
        assert cli is not None

    def test_generate_command_registered(self):
        from persona_forge.cli import cli
        assert "generate" in cli.commands

    def test_validate_command_registered(self):
        from persona_forge.cli import cli
        assert "validate" in cli.commands

    def test_batch_generate_command_registered(self):
        from persona_forge.cli import cli
        assert "batch-generate" in cli.commands


class TestCLIGenerateRunner:
    def test_generate_json_output(self, tmp_path):
        from click.testing import CliRunner
        from persona_forge.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--role", "Product Manager",
            "--goals", "reduce churn",
            "--goals", "increase NPS",
            "--pain-points", "no time",
            "--json",
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["role"] == "Product Manager"
        assert data["goals"] == ["reduce churn", "increase NPS"]
        assert data["enriched_narrative"] is None

    def test_generate_rich_output(self):
        from click.testing import CliRunner
        from persona_forge.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--role", "Designer",
            "--goals", "create beautiful interfaces",
            "--pain-points", "unclear briefs",
            "--tech-savviness", "high",
        ])
        assert result.exit_code == 0, result.output
        assert "Designer" in result.output

    def test_generate_custom_id(self):
        from click.testing import CliRunner
        from persona_forge.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--role", "Engineer",
            "--goals", "automate tasks",
            "--pain-points", "manual work",
            "--id", "eng-001",
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "eng-001"


class TestCLIValidateRunner:
    def test_validate_json_output(self, tmp_path):
        from click.testing import CliRunner
        from persona_forge.cli import cli

        snapshots = [
            {
                "session_id": "s1",
                "persona_id": "p001",
                "stated_goals": ["improve workflow"],
                "observed_behaviours": ["checked dashboard"],
                "expressed_attitudes": ["confident"],
            },
            {
                "session_id": "s2",
                "persona_id": "p001",
                "stated_goals": ["improve workflow"],
                "observed_behaviours": ["referenced past data"],
                "expressed_attitudes": ["trusts process"],
            },
        ]
        snap_file = tmp_path / "snaps.json"
        snap_file.write_text(json.dumps(snapshots))

        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(snap_file), "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["persona_id"] == "p001"
        assert "consistency_score" in data


class TestBatchGenerateCLI:
    def test_batch_generate(self, tmp_path):
        from click.testing import CliRunner
        from persona_forge.cli import cli

        seeds = [
            {
                "role": "PM",
                "goals": ["ship faster"],
                "pain_points": ["too much process"],
                "tech_savviness": "medium",
                "decision_style": "impulsive",
                "risk_tolerance": "high",
            },
            {
                "role": "Designer",
                "goals": ["improve usability"],
                "pain_points": ["vague feedback"],
                "tech_savviness": "medium",
                "decision_style": "deliberate",
                "risk_tolerance": "moderate",
            },
        ]
        seeds_file = tmp_path / "seeds.json"
        seeds_file.write_text(json.dumps(seeds))
        output_file = tmp_path / "out.json"

        runner = CliRunner()
        result = runner.invoke(cli, [
            "batch-generate", str(seeds_file), "--output", str(output_file)
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(output_file.read_text())
        assert len(data) == 2
        assert data[0]["role"] == "PM"
        assert data[1]["role"] == "Designer"
