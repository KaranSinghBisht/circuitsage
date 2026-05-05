# CircuitSage Companion Contract

All companion clients call the same backend endpoint:

```http
POST /api/companion/analyze
Content-Type: application/json
```

Request:

```json
{
  "question": "What should I check next?",
  "image_data_url": "data:image/jpeg;base64,...",
  "app_hint": "auto | tinkercad | ltspice | matlab | electronics_workspace",
  "source_title": "optional active window or captured source title",
  "session_id": "optional CircuitSage lab session id",
  "save_snapshot": true
}
```

Response:

```json
{
  "mode": "ollama_gemma_vision | deterministic_fallback | safety_refusal",
  "workspace": "ltspice",
  "visible_context": "what CircuitSage can actually see",
  "answer": "direct answer",
  "next_actions": ["step 1", "step 2", "step 3"],
  "can_click": false,
  "safety": {"risk_level": "low_voltage_lab", "warnings": []},
  "confidence": "low | medium | high"
}
```
