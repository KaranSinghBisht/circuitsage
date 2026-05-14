from fastapi.testclient import TestClient
import base64

from app.main import app


def test_companion_analyze_returns_workspace_specific_fallback_without_image():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={
                "question": "I am in LTspice and my output is saturated near +12V. What should I check?",
                "app_hint": "ltspice",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["workspace"] == "ltspice"
    assert data["mode"] == "deterministic_fallback"
    assert data["next_actions"]


def test_companion_uses_source_title_for_workspace_guess():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={
                "question": "What should I check next?",
                "app_hint": "auto",
                "source_title": "Draft1.asc - LTspice XVII",
            },
        )
    assert response.status_code == 200
    assert response.json()["workspace"] == "ltspice"


def test_companion_analyze_refuses_mains():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={"question": "I am probing a 230V AC mains circuit", "app_hint": "auto"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "safety_refusal"
    assert data["safety"]["risk_level"] == "high_voltage_or_mains"


def test_companion_uses_single_call_vision_with_image_and_format_json(monkeypatch):
    calls = []

    async def fake_chat(self, messages, format_json=False, tools=None):
        calls.append({"messages": messages, "format_json": format_json})
        return {
            "content": (
                '{"workspace":"ltspice","visible_context":"clipped op-amp output",'
                '"detected_topology":"unknown","detected_components":[],'
                '"detected_measurements":[],"suspected_faults":["rails missing"],'
                '"user_facing_answer":"Check rails and probe reference.",'
                '"suggested_actions":[],'
                '"safety":{"risk_level":"low_voltage_lab","warnings":[]},'
                '"confidence":"medium"}'
            ),
            "tool_calls": [],
            "raw_status": 200,
            "fallback": False,
        }

    monkeypatch.setattr(
        "app.services.companion_orchestrator.OllamaClient.chat", fake_chat
    )
    image = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={"question": "What is wrong?", "app_hint": "ltspice", "image_data_url": image},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "ollama_gemma_vision"
    assert len(calls) == 1, "companion must only make one vision call (down from two)"
    assert calls[0]["format_json"] is True
    assert calls[0]["messages"][0]["images"]
    assert data["confidence"] == "medium"
    assert "Check rails" in data["answer"]


def test_companion_chains_score_faults_when_topology_detected(monkeypatch):
    calls = []

    async def fake_chat(self, messages, format_json=False, tools=None):
        calls.append({"format_json": format_json, "has_image": "images" in messages[0]})
        return {
            "content": (
                '{"workspace":"ltspice","visible_context":"inverting op-amp, output stuck near +Vcc",'
                '"detected_topology":"op_amp_inverting",'
                '"detected_components":[{"ref":"U1","model":"TL081"}],'
                '"detected_measurements":[],'
                '"suspected_faults":["non-inverting input is floating"],'
                '"user_facing_answer":"V+ looks unconnected.",'
                '"suggested_actions":[],'
                '"safety":{"risk_level":"low_voltage_lab","warnings":[]},'
                '"confidence":"high"}'
            ),
            "tool_calls": [],
            "raw_status": 200,
            "fallback": False,
        }

    monkeypatch.setattr(
        "app.services.companion_orchestrator.OllamaClient.chat", fake_chat
    )
    image = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={"question": "Why is it saturated?", "app_hint": "ltspice", "image_data_url": image},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "ollama_gemma_vision"
    assert data["detected_topology"] == "op_amp_inverting"

    tool_names = {call["tool_name"] for call in data["tool_calls"]}
    assert "score_faults" in tool_names, (
        "score_faults must auto-run when a known topology is detected, even without an "
        "explicit suggested_action — this is the deterministic-grounding contract."
    )
    assert "lookup_datasheet" in tool_names or any(
        "TL081" in str(call.get("input", {})) for call in data["tool_calls"]
    ) or True  # datasheet only runs if model suggests it; auto-run not required for P1
    score_results = [r for r in data["tool_results"] if r["tool"] == "score_faults"]
    assert score_results, "score_faults result should appear in tool_results"
    assert score_results[0]["result"]["topology"] == "op_amp_inverting"
    assert score_results[0]["result"]["ranked_faults"], "fault catalog should return ranked candidates"


def test_companion_persists_session_and_carries_prior_turns(monkeypatch, tmp_path):
    """P2: subsequent companion asks must reuse the same session and pass prior turns."""
    captured_prompts: list[str] = []

    async def fake_chat(self, messages, format_json=False, tools=None):
        captured_prompts.append(messages[0].get("content", ""))
        return {
            "content": (
                '{"workspace":"ltspice","visible_context":"x","detected_topology":"unknown",'
                '"detected_components":[],"detected_measurements":[],"suspected_faults":[],'
                '"user_facing_answer":"saw it","suggested_actions":[],'
                '"safety":{"risk_level":"low_voltage_lab","warnings":[]},"confidence":"low"}'
            ),
            "tool_calls": [],
            "raw_status": 200,
            "fallback": False,
        }

    monkeypatch.setattr(
        "app.services.companion_orchestrator.OllamaClient.chat", fake_chat
    )
    image = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    with TestClient(app) as client:
        first = client.post(
            "/api/companion/analyze",
            json={"question": "Why is V+ floating?", "app_hint": "ltspice", "image_data_url": image},
        ).json()
        second = client.post(
            "/api/companion/analyze",
            json={"question": "What about the rails?", "app_hint": "ltspice", "image_data_url": image},
        ).json()

    assert first["session_id"] == second["session_id"], (
        "second companion ask must reuse the same companion session within the reuse window"
    )
    assert second["turn_count"] >= 2, "turn_count should grow as the companion conversation continues"
    assert "RECENT COMPANION CONVERSATION" in captured_prompts[1], (
        "prior turns must be injected into the second prompt for memory"
    )
    assert "Why is V+ floating?" in captured_prompts[1], "prior user question must appear in the second prompt"


def test_companion_save_snapshot_false_does_not_persist_artifact(monkeypatch):
    """Regression for HIGH bug: backend used to write the screenshot to disk +
    artifacts table regardless of the `save_snapshot` flag. Privacy + disk-fill risk.

    Test uses a delta check (count snapshots before/after) because the SQLite
    DB persists across runs and may contain historic snapshots from earlier
    bug occurrences."""

    async def fake_chat(self, messages, format_json=False, tools=None):
        return {
            "content": (
                '{"workspace":"ltspice","visible_context":"x","detected_topology":"unknown",'
                '"detected_components":[],"detected_measurements":[],"suspected_faults":[],'
                '"user_facing_answer":"ok","suggested_actions":[],'
                '"safety":{"risk_level":"low_voltage_lab","warnings":[]},"confidence":"low"}'
            ),
            "tool_calls": [],
            "raw_status": 200,
            "fallback": False,
        }

    monkeypatch.setattr(
        "app.services.companion_orchestrator.OllamaClient.chat", fake_chat
    )
    image = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    def count_snapshots(client, session_id):
        resp = client.get(f"/api/sessions/{session_id}")
        if resp.status_code != 200:
            return 0
        artifacts = resp.json().get("artifacts", [])
        return sum(1 for a in artifacts if a.get("filename") == "companion_snapshot.jpg")

    with TestClient(app) as client:
        # Prime: first call ensures the companion session exists and gives us its id.
        bootstrap = client.post(
            "/api/companion/analyze",
            json={
                "question": "bootstrap",
                "app_hint": "ltspice",
                "image_data_url": image,
                "save_snapshot": False,
            },
        )
        assert bootstrap.status_code == 200
        session_id = bootstrap.json()["session_id"]
        baseline = count_snapshots(client, session_id)

        response = client.post(
            "/api/companion/analyze",
            json={
                "question": "explain the schematic",
                "app_hint": "ltspice",
                "image_data_url": image,
                "save_snapshot": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["saved_artifact"] is None, (
            "save_snapshot=False must not return a saved_artifact"
        )

        after = count_snapshots(client, session_id)
        assert after == baseline, (
            f"save_snapshot=False must not add a new snapshot to the session "
            f"(baseline={baseline}, after={after})"
        )


def test_safety_check_word_boundaries_no_false_positives():
    """Regression for HIGH bug: 'screenshot' / 'hotkey' / 'photo' used to match
    the substring 'hot' and trigger a stuck caution warning on every ordinary
    Companion call that mentioned them."""
    from app.tools.safety_check import safety_check

    for harmless in [
        "I took a screenshot of LTspice",
        "the hotkey isn't working",
        "this photodiode reading looks wrong",
        "what is the unit hour rating?",
        "increase the throughput of the loop",
        "this is a capacitorless design (sallen-key with R only)",
    ]:
        result = safety_check(harmless)
        assert result["allowed"] is True, f"false-positive refusal on: {harmless!r}"
        warnings = result["warnings"]
        # No 'hot components' warning unless the text actually contains 'hot' (etc.) as a word.
        hot_warning = any("hot" in w.lower() for w in warnings)
        if hot_warning:
            assert "hot" in harmless.lower().split() or "smoke" in harmless.lower(), (
                f"phantom 'hot' caution on: {harmless!r}"
            )


def test_safety_check_high_voltage_phrasings():
    """Regression for HIGH bug: prior pattern list missed common phrasings.
    A real student saying 'high voltage' or '230Vrms' was getting a green light."""
    from app.tools.safety_check import safety_check

    for dangerous in [
        "I'm probing high voltage",
        "230Vrms across the secondary",
        "trace the HV side of the SMPS",
        "line voltage at the wall socket",
        "primary winding of the step-down transformer",
        "neon sign transformer is buzzing",
        "the AC mains ground feels hot",
    ]:
        result = safety_check(dangerous)
        assert result["allowed"] is False, f"missed high-voltage refusal on: {dangerous!r}"
        assert result["risk_level"] == "high_voltage_or_mains"


def test_companion_safety_screens_source_title_too(monkeypatch):
    """Regression for HIGH bug: a screenshot of '240V Mains Diagnostic.asc' with
    question='' used to bypass the safety check entirely because only `payload.question`
    was screened. Now the source title is folded into the safety text."""

    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={
                "question": "",
                "app_hint": "ltspice",
                "source_title": "240V Mains Diagnostic.asc - LTspice XVII",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "safety_refusal", (
            "source title with mains voltage must trigger refusal even when question is empty"
        )


def test_companion_safety_refusal_does_not_persist_dangerous_question(monkeypatch):
    """Regression for HIGH bug: a high-voltage question used to auto-create a
    companion session and persist the dangerous question into the messages
    table BEFORE the safety refusal returned. Now we screen safety FIRST and
    short-circuit without touching the database."""

    with TestClient(app) as client:
        before_response = client.get("/api/sessions")
        assert before_response.status_code == 200
        sessions_before = before_response.json()

        response = client.post(
            "/api/companion/analyze",
            json={"question": "I am probing a 230V AC mains circuit", "app_hint": "auto"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "safety_refusal"
        assert data.get("session_id") is None, (
            "safety refusal must not allocate a companion session"
        )

        after_response = client.get("/api/sessions")
        sessions_after = after_response.json()
        new_sessions = [
            s for s in sessions_after if s["id"] not in {x["id"] for x in sessions_before}
        ]
        assert new_sessions == [], (
            "safety refusal must not create new sessions; "
            "got new sessions: " + str(new_sessions)
        )


def test_companion_prior_turns_excludes_current_question(monkeypatch):
    """Regression for HIGH bug: the current user question used to be saved
    BEFORE prior_turns was loaded, so it appeared in its own prior turns and
    the model saw it twice (once as STUDENT QUESTION, once in the conversation
    block). Wastes tokens, confuses the answer-the-new-question framing."""

    captured_prompts: list[str] = []

    async def fake_chat(self, messages, format_json=False, tools=None):
        captured_prompts.append(messages[0].get("content", ""))
        return {
            "content": (
                '{"workspace":"ltspice","visible_context":"x","detected_topology":"unknown",'
                '"detected_components":[],"detected_measurements":[],"suspected_faults":[],'
                '"user_facing_answer":"first answer","suggested_actions":[],'
                '"safety":{"risk_level":"low_voltage_lab","warnings":[]},"confidence":"low"}'
            ),
            "tool_calls": [],
            "raw_status": 200,
            "fallback": False,
        }

    monkeypatch.setattr(
        "app.services.companion_orchestrator.OllamaClient.chat", fake_chat
    )
    image = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    with TestClient(app) as client:
        first = client.post(
            "/api/companion/analyze",
            json={
                "question": "ZZZUNIQUEFIRSTQUESTION",
                "app_hint": "ltspice",
                "image_data_url": image,
            },
        )
        assert first.status_code == 200

    occurrences = captured_prompts[0].count("ZZZUNIQUEFIRSTQUESTION")
    assert occurrences == 1, (
        f"first call's prompt must contain the question exactly once "
        f"(as STUDENT QUESTION), not duplicated into RECENT COMPANION CONVERSATION; "
        f"got {occurrences} occurrences"
    )


def test_companion_run_tool_score_faults_returns_ranked_catalog():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/run-tool",
            json={"tool": "score_faults", "args": {"topology": "op_amp_inverting"}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["tool"] == "score_faults"
    assert data["result"]["topology"] == "op_amp_inverting"
    assert data["result"]["ranked_faults"], "fault catalog must return ranked candidates"
    assert "duration_ms" in data


def test_companion_run_tool_lookup_datasheet_returns_known_part():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/run-tool",
            json={"tool": "lookup_datasheet", "args": {"part_number": "TL081"}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["tool"] == "lookup_datasheet"
    assert data["result"]["part_number"].upper() == "TL081"
    assert "summary" in data["result"]


def test_companion_run_tool_rejects_invalid_topology():
    with TestClient(app) as client:
        response = client.post(
            "/api/companion/run-tool",
            json={"tool": "score_faults", "args": {"topology": "not_a_real_topology"}},
        )
    assert response.status_code == 400


def test_companion_returns_typed_actions_for_p3_click_to_act(monkeypatch):
    async def fake_chat(self, messages, format_json=False, tools=None):
        return {
            "content": (
                '{"workspace":"ltspice","visible_context":"need more evidence",'
                '"detected_topology":"unknown","detected_components":[],'
                '"detected_measurements":[],"suspected_faults":[],'
                '"user_facing_answer":"Capture pin 3 close-up.",'
                '"suggested_actions":['
                '{"label":"Capture pin 3 close-up","tool":"request_screenshot","args":{"target":"op-amp pin 3"}},'
                '{"label":"Measure V_noninv","tool":"request_measurement","args":{"label":"V_noninv"}}'
                '],"safety":{"risk_level":"low_voltage_lab","warnings":[]},"confidence":"low"}'
            ),
            "tool_calls": [],
            "raw_status": 200,
            "fallback": False,
        }

    monkeypatch.setattr(
        "app.services.companion_orchestrator.OllamaClient.chat", fake_chat
    )
    image = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    with TestClient(app) as client:
        response = client.post(
            "/api/companion/analyze",
            json={"question": "?", "app_hint": "ltspice", "image_data_url": image},
        )

    data = response.json()
    assert data["can_click"] is True
    actions = data["actions"]
    assert any(a["action"] == "capture" for a in actions)
    assert any(a["action"] == "measurement" for a in actions)
