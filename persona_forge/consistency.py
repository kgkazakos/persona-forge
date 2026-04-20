"""Cross-session behavioural consistency validation — rule-based core."""

from __future__ import annotations

from itertools import combinations

from .models import ConsistencyFlag, ConsistencyReport, SessionSnapshot

# ---------------------------------------------------------------------------
# Contradiction detection helpers
# ---------------------------------------------------------------------------

_GOAL_ANTONYMS: list[tuple[set[str], set[str]]] = [
    ({"speed", "fast", "quick", "now"}, {"thorough", "complete", "exhaustive", "careful"}),
    ({"automate", "scale", "bulk"}, {"manual", "personal", "bespoke", "custom"}),
    ({"reduce", "cut", "simplify", "less"}, {"add", "expand", "grow", "more"}),
    ({"consensus", "align", "agree"}, {"decide", "unilateral", "own", "independent"}),
]

_ATTITUDE_ANTONYMS: list[tuple[set[str], set[str]]] = [
    ({"love", "like", "enjoy", "prefer"}, {"hate", "dislike", "avoid", "reject"}),
    ({"trust", "rely", "confident"}, {"doubt", "distrust", "uncertain", "unsure"}),
    ({"urgent", "critical", "priority"}, {"low priority", "later", "eventually", "backlog"}),
]


def _keyword_overlap(text_a: str, text_b: str) -> float:
    """Simple Jaccard overlap on word sets."""
    wa = set(text_a.lower().split())
    wb = set(text_b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _detect_antonym_clash(items_a: list[str], items_b: list[str],
                           antonym_table: list[tuple[set[str], set[str]]]) -> list[str]:
    """Return descriptions of detected antonym clashes across two lists."""
    clashes = []
    for a_item in items_a:
        for b_item in items_b:
            for side_x, side_y in antonym_table:
                a_words = set(a_item.lower().split())
                b_words = set(b_item.lower().split())
                if (a_words & side_x and b_words & side_y) or (a_words & side_y and b_words & side_x):
                    clashes.append(f"'{a_item}' vs '{b_item}'")
    return clashes


def _compare_sessions(snap_a: SessionSnapshot, snap_b: SessionSnapshot) -> list[ConsistencyFlag]:
    """Compare two session snapshots and return consistency flags."""
    flags: list[ConsistencyFlag] = []

    # --- Goal contradictions
    goal_clashes = _detect_antonym_clash(snap_a.stated_goals, snap_b.stated_goals, _GOAL_ANTONYMS)
    for clash in goal_clashes:
        flags.append(ConsistencyFlag(
            flag_type="contradiction",
            description=f"Opposing goals detected: {clash}",
            session_a=snap_a.session_id,
            session_b=snap_b.session_id,
            severity="high",
            attribute="stated_goals",
        ))

    # --- Attitude contradictions
    attitude_clashes = _detect_antonym_clash(
        snap_a.expressed_attitudes, snap_b.expressed_attitudes, _ATTITUDE_ANTONYMS
    )
    for clash in attitude_clashes:
        flags.append(ConsistencyFlag(
            flag_type="contradiction",
            description=f"Opposing attitudes detected: {clash}",
            session_a=snap_a.session_id,
            session_b=snap_b.session_id,
            severity="medium",
            attribute="expressed_attitudes",
        ))

    # --- Goal overlap drift (goals diverge with no overlap)
    a_goals_text = " ".join(snap_a.stated_goals)
    b_goals_text = " ".join(snap_b.stated_goals)
    overlap = _keyword_overlap(a_goals_text, b_goals_text)
    if overlap < 0.1 and snap_a.stated_goals and snap_b.stated_goals:
        flags.append(ConsistencyFlag(
            flag_type="drift",
            description=f"Goal language shifted significantly (overlap={overlap:.2f}) — possible role or context drift",
            session_a=snap_a.session_id,
            session_b=snap_b.session_id,
            severity="medium",
            attribute="stated_goals",
        ))

    # --- Behaviour gaps (behaviours in A absent from B)
    for beh in snap_a.observed_behaviours:
        b_text = " ".join(snap_b.observed_behaviours).lower()
        words = set(beh.lower().split())
        if not any(w in b_text for w in words if len(w) > 4):
            flags.append(ConsistencyFlag(
                flag_type="gap",
                description=f"Behaviour '{beh}' observed in {snap_a.session_id} but absent in {snap_b.session_id}",
                session_a=snap_a.session_id,
                session_b=snap_b.session_id,
                severity="low",
                attribute="observed_behaviours",
            ))

    return flags


def validate_consistency(snapshots: list[SessionSnapshot]) -> ConsistencyReport:
    """
    Validate behavioural consistency across all provided session snapshots.

    Fully rule-based — no API calls.
    """
    if not snapshots:
        raise ValueError("At least one session snapshot is required.")

    persona_id = snapshots[0].persona_id
    all_flags: list[ConsistencyFlag] = []

    for snap_a, snap_b in combinations(snapshots, 2):
        all_flags.extend(_compare_sessions(snap_a, snap_b))

    # --- Score calculation
    total_pairs = max(len(list(combinations(snapshots, 2))), 1)
    high_flags = sum(1 for f in all_flags if f.severity == "high")
    medium_flags = sum(1 for f in all_flags if f.severity == "medium")
    low_flags = sum(1 for f in all_flags if f.severity == "low")
    penalty = (high_flags * 0.15 + medium_flags * 0.07 + low_flags * 0.02) / total_pairs
    consistency_score = max(0.0, 1.0 - penalty)

    # --- Stable vs drifting attributes
    flagged_attrs = {f.attribute for f in all_flags}
    all_attrs = {"stated_goals", "observed_behaviours", "expressed_attitudes"}
    stable_attributes = sorted(all_attrs - flagged_attrs)
    drifting_attributes = sorted(flagged_attrs)

    # --- Summary
    if not all_flags:
        summary = f"No consistency issues detected across {len(snapshots)} session(s). Persona behaves stably."
    else:
        summary = (
            f"{len(all_flags)} consistency flag(s) detected across {len(snapshots)} session(s): "
            f"{high_flags} high, {medium_flags} medium, {low_flags} low severity. "
            f"Consistency score: {consistency_score:.2f}. "
            f"Drifting attributes: {', '.join(drifting_attributes) or 'none'}."
        )

    return ConsistencyReport(
        persona_id=persona_id,
        sessions_compared=len(snapshots),
        consistency_score=consistency_score,
        flags=all_flags,
        stable_attributes=stable_attributes,
        drifting_attributes=drifting_attributes,
        summary=summary,
    )
