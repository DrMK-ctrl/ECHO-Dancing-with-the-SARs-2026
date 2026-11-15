# ECHO AI Investigator

## Product role

The Investigator is optional, user-directed assistance in the case evidence workspace. Its actions ask a local language model to organize what the selected case records say, compare hypotheses, surface stated gaps, and suggest evidence checks. It is an interpretation draft, not a measurement, QA decision, validated finding, or replacement for the deterministic investigation workflow.

The backend assembles the dossier from the selected local case review, catalog snapshot, validated linked investigation assessment and source artifact manifest, retained QA reports, and—when present—a checksum-verified single-observation preview. Dossier content is bounded before it is sent to the model. The response cites short record tokens which ECHO resolves to exact evidence IDs; citations outside the selected dossier are rejected. The saved run records the provider/model, prompt version, UTC timestamp, dossier SHA-256, returned citations, and tool-call list. No scientific tool execution is delegated to the model in this first implementation.

The prompt treats source text as untrusted data. Deterministic backend gates require QA-held pair requests to abstain and explicitly state that pair change was not calculated. Diagnostic case assessments cannot state that a flood boundary or cause is established. The model cannot modify source records, QA status, measurements, or case assessment.

## Local configuration

ECHO uses the local Ollama HTTP API on loopback. No API key is needed and the case dossier is not sent to a hosted model provider.

```bash
ollama serve
ollama pull qwen3:4b
ECHO_OLLAMA_MODEL=qwen3:4b .venv/bin/echo serve --host 127.0.0.1 --port 8765
```

`ECHO_OLLAMA_URL` may override the API URL only with an HTTP loopback address. Non-loopback endpoints, endpoint credentials, query strings, or fragments are rejected. `ECHO_OLLAMA_MODEL` defaults to `qwen3:4b`. Keep the ECHO server bound to loopback. AI records are written with restrictive local permissions under `${XDG_DATA_HOME:-~/.local/share}/echo/ai-investigations/<case-id>/`; this directory is outside the repository.

If Ollama is stopped or the model is absent, ECHO reports that no AI response was generated. It does not display canned fallback text.

## Status and limits

The UI is connected to a local model adapter and has deterministic structure/citation validation. A generated response remains an AI-authored draft. The language model can still make interpretation errors even when it cites real records; citation validity is not proof that a citation supports the sentence. The current implementation has no calibrated confidence, no automatic finding update, no model tool calls, no external provider, and no formal benchmark of usefulness or factual grounding. Live successful model behavior must be recorded separately from software tests.

Automated checks:

```bash
.venv/bin/pytest -q tests/test_ai_investigator.py
```

These tests check structure, citation enforcement, prompt policy and narrow hard guards. They do not validate scientific conclusions or establish general model reliability.
