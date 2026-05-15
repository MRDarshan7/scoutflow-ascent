import json

from backend.config import settings


GEMINI_MODEL = "gemini-2.5-flash"


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
    prompt = f"""
You improve ScoutFlow insights using only validated findings.
Return JSON only. No markdown. No explanation.

Validated findings:
{json.dumps(findings)}

Current deterministic insight:
{json.dumps(insight_output)}

Return this exact JSON shape:
{{
  "summary": "",
  "business_implications": [],
  "recommendations": []
}}

Rules:
- Ground everything only in the validated findings.
- Do not invent companies, funding, dates, launches, or events.
- Improve wording and business context.
- Keep recommendations practical.
- If evidence is weak, be cautious.
"""
    return _generate_json(prompt)


def _generate_json(prompt: str) -> dict | None:
    if not settings.gemini_api_key:
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = _clean_json_text(getattr(response, "text", ""))
        data = json.loads(text)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned
