import json
import time

from backend.config import settings


GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_FALLBACK_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
)
GEMINI_REQUEST_TIMEOUT_SECONDS = 30
_MODEL_COOLDOWN_UNTIL: dict[str, float] = {}


def refine_plan_with_gemini(goal_query: str, plan: dict) -> dict | None:
    prompt = f"""
You improve a deterministic research plan for ScoutFlow.
Return JSON only. No markdown. No explanation.

User goal:
{goal_query}

Existing deterministic plan:
{json.dumps(plan)}

Return this exact JSON shape:
{{
  "extra_targets": [],
  "extra_queries": [],
  "monitoring_focus": [],
  "entities": []
}}

Rules:
- Add only useful research targets and queries.
- Generalize across domains.
- Do not invent facts or events.
- Keep each list short and practical.
"""
    return _generate_json(prompt)


def refine_insights_with_gemini(validated_output: dict, insight_output: dict) -> dict | None:
    findings = validated_output.get("validated_findings", [])[:8]
    goal = validated_output.get("goal", insight_output.get("goal", ""))
    prompt = f"""
You are ScoutFlow's intelligence analyst.
Improve ScoutFlow insights using only validated findings.
Return JSON only. No markdown. No explanation.

User goal:
{goal}

Validated findings:
{json.dumps(findings)}

Current deterministic insight:
{json.dumps(insight_output)}

Return this exact JSON shape:
{{
  "signals": [],
  "summary": "",
  "business_implications": [],
  "recommendations": []
}}

Rules:
- Ground everything only in the validated findings.
- Do not invent companies, funding, dates, launches, or events.
- signals must be 3 to 5 concise labels, each 2 to 5 words.
- signals must be contextual to the user's domain, not generic categories.
- signals must reflect actual market movement in the findings.
- Replace generic labels like Product Expansion or Market Consolidation with specific labels when the findings support it.
- Avoid generic buzzwords like Future Transformation, Technology Revolution, Business Excellence.
- Write the summary like an analyst-grade intelligence brief.
- Make business implications query-aware and evidence-grounded.
- Keep recommendations practical and tied to observed findings.
- If evidence is weak, be cautious.
"""
    return _generate_json(prompt)


def _generate_json(prompt: str) -> dict | None:
    if not settings.gemini_api_key:
        return None

    try:
        import google.generativeai as genai
    except Exception as e:  # pragma: no cover - import guard
        print("\nGEMINI IMPORT ERROR:", type(e).__name__, e)
        return None

    genai.configure(api_key=settings.gemini_api_key)

    now = time.time()
    last_error: Exception | None = None

    for model_name in GEMINI_FALLBACK_MODELS:
        cooldown_until = _MODEL_COOLDOWN_UNTIL.get(model_name, 0.0)
        if cooldown_until > now:
            continue

        text = ""
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
                request_options={"timeout": GEMINI_REQUEST_TIMEOUT_SECONDS},
            )
            text = _clean_json_text(_response_text(response))
            data = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"\nGEMINI JSON PARSE ERROR ({model_name}):", type(e).__name__, e)
            print("Raw response:", text or "<empty>")
            last_error = e
            continue
        except Exception as e:
            error_name = type(e).__name__
            message = str(e)
            is_quota = (
                error_name in {"ResourceExhausted", "TooManyRequests"}
                or "429" in message
                or "quota" in message.lower()
                or "exhausted" in message.lower()
                or "rate limit" in message.lower()
            )
            if is_quota:
                cooldown = _parse_retry_delay(message)
                _MODEL_COOLDOWN_UNTIL[model_name] = time.time() + cooldown
                print(
                    f"\nGEMINI QUOTA HIT ({model_name}): cooling down {int(cooldown)}s, "
                    f"falling back to next model."
                )
                last_error = e
                continue
            print(f"\nGEMINI ERROR ({model_name}):", error_name, e)
            last_error = e
            continue

        if not isinstance(data, dict):
            print(
                f"\nGEMINI JSON SHAPE ERROR ({model_name}):"
                f" expected object, got {type(data).__name__}"
            )
            continue

        return data

    if last_error is not None:
        print("\nGEMINI: all fallback models unavailable; using deterministic output.")
    return None


def _parse_retry_delay(message: str) -> float:
    """Best-effort parse of `retry_delay { seconds: N }` from API error message."""
    import re

    match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", message)
    if match:
        return float(match.group(1)) + 1.0
    return 60.0


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


def _response_text(response: object) -> str:
    text = getattr(response, "text", "")
    if text:
        return str(text)

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return ""

    parts = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", "")
            if part_text:
                parts.append(str(part_text))

    return "\n".join(parts)
