"""
Optional LLM enrichment layer for persona-forge.

All enrichment is additive — the rule-based core runs first.
Activated only when --llm-backend is supplied.
This module is community extension reference scaffolding:
it is not tested in CI and requires optional API-key extras.
"""

from __future__ import annotations

import json
import os

from .models import ConsistencyReport, Persona

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_PERSONA_ENRICH_PROMPT = """\
You are a senior UX research expert specialising in persona development.

Below is a rule-generated research persona. Your task is to:
1. Write an enriched 3–4 sentence narrative that brings this persona to life
   (first person voice, natural and specific, avoid clichés).
2. Generate 3 realistic verbatim quotes this person might say in a research session.
3. Identify up to 3 subtle behavioural contradictions that a researcher should watch for
   (based on the combination of goals, pain points, and traits listed).

Respond ONLY with valid JSON — no markdown fences, no preamble:
{{
  "enriched_narrative": "<string>",
  "enriched_quotes": ["<string>", "<string>", "<string>"],
  "enriched_contradictions": ["<string>", ...]
}}

PERSONA:
{persona_json}
"""

_CONSISTENCY_ENRICH_PROMPT = """\
You are a senior UX researcher reviewing a behavioural consistency report.

Below is a rule-based consistency analysis for a research persona across multiple sessions.
Write a 2–3 sentence clinical diagnosis of what this pattern suggests about the persona's
reliability as a research participant, and what a researcher should probe in the next session.

Respond ONLY with valid JSON:
{{
  "enriched_diagnosis": "<string>"
}}

REPORT:
{report_json}
"""

# ---------------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------------


def _call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as e:
        raise ImportError("Install openai: pip install 'persona-forge[openai]'") from e
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=800,
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(prompt: str, model: str = "claude-sonnet-4-6") -> str:
    try:
        import anthropic  # type: ignore
    except ImportError as e:
        raise ImportError("Install anthropic: pip install 'persona-forge[anthropic]'") from e
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model=model,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text if msg.content else ""


def _call_gemini(prompt: str, model: str = "gemini-4-argon") -> str:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError as e:
        raise ImportError("Install google-genai: pip install 'persona-forge[gemini]'") from e
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=800,
        ),
    )
    return resp.text or ""


def _dispatch(prompt: str, backend: str) -> str:
    if backend == "openai":
        return _call_openai(prompt)
    if backend == "anthropic":
        return _call_anthropic(prompt)
    if backend == "gemini":
        return _call_gemini(prompt)
    raise ValueError(f"Unknown backend: {backend!r}. Choose openai | anthropic | gemini")


def _safe_parse(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public enrichment functions
# ---------------------------------------------------------------------------


def enrich_persona(persona: Persona, backend: str) -> Persona:
    """Enrich a rule-generated persona with LLM-generated narrative and quotes."""
    prompt = _PERSONA_ENRICH_PROMPT.format(
        persona_json=json.dumps(persona.to_dict(), indent=2)
    )
    raw = _dispatch(prompt, backend)
    try:
        data = _safe_parse(raw)
        persona.enriched_narrative = data.get("enriched_narrative")
        persona.enriched_quotes = data.get("enriched_quotes", [])
        persona.enriched_contradictions = data.get("enriched_contradictions", [])
    except (json.JSONDecodeError, KeyError):
        pass  # graceful degradation — rule-based output still valid
    return persona


def enrich_consistency_report(report: ConsistencyReport, backend: str) -> ConsistencyReport:
    """Enrich a consistency report with LLM-generated clinical diagnosis."""
    prompt = _CONSISTENCY_ENRICH_PROMPT.format(
        report_json=json.dumps(report.to_dict(), indent=2)
    )
    raw = _dispatch(prompt, backend)
    try:
        data = _safe_parse(raw)
        report.enriched_diagnosis = data.get("enriched_diagnosis")
    except (json.JSONDecodeError, KeyError):
        pass
    return report
