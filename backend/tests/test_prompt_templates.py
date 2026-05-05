from app.services.prompt_templates import STRUCTURED_DIAGNOSIS_PROMPT


def test_structured_diagnosis_prompt_accepts_context_formatting() -> None:
    prompt = STRUCTURED_DIAGNOSIS_PROMPT.format(context='{"ok": true}')

    assert '{"ok": true}' in prompt
    assert '"likely_faults"' in prompt
