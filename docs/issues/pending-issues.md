# Pending Issues

Required by `AGENTS_FoodFlow.md` §14. Every issue affecting correctness, quantity integrity,
Agent behaviour, state transitions, test gates, or pitch completion is recorded here with root
cause, hypothesis, change, result, and evidence.

**Three-attempt limit.** A maximum of three substantive remediation attempts per root cause.
Read-only inspection does not count as an attempt. Re-running the same command without a new
hypothesis does not count as an attempt. After the third failure, stop modifying and report the
blocker — do not lower a quality gate or silently mark the issue resolved.

Pure typos and one-step mechanical formatting fixes do not require an entry.

---

## Template

```
### ISSUE-NNN — <short title>
- **Status:** open | resolved | blocked
- **Affects:** correctness | quantity integrity | Agent behaviour | state transition | gate | pitch
- **Root cause:**
- **Attempt 1 —** hypothesis / change / result / evidence
- **Attempt 2 —** …
- **Attempt 3 —** …
- **Outcome:**
```

---

## ISSUE-001 — Exposed DeepSeek API key in `.env`

- **Status:** partially resolved — **rotation still outstanding**
- **Affects:** security
- **Root cause:** The repository had no `.gitignore`. `.env` held a live DeepSeek key under the
  non-conforming variable name `DeepSeekAPI_KEY`. The file was untracked but not ignored, so a
  single `git add -A` would have committed a live credential to a public GitHub repository.
- **Attempt 1 —** *Hypothesis:* absence of `.gitignore` is the whole cause.
  *Change:* added `.gitignore` covering `.env`, Python/Node build artefacts, and `*.db`.
  *Result:* `git check-ignore -v .env` → `.gitignore:2:.env`.
  *Evidence:* `git status -uall` no longer lists `.env`.
- **Outstanding:** the key must still be **rotated** at platform.deepseek.com. Assume exposure —
  rotation is cheap and the file was unprotected for the life of the repository. Variable names
  must also be migrated to the `clean_code_spec` §6.4 contract (`DEEPSEEK_API_KEY` etc.);
  `.env_example` has been updated to the full five-key form.

---

## ISSUE-002 — P0 spike: ADK 2.x ↔ DeepSeek V4 tool-call reliability

- **Status:** resolved — keep ADK `LiteLlm`; thinking disabled is mandatory
- **Affects:** Agent behaviour, pitch completion
- **Root cause:** `google/adk-python` #5024 reports that with LiteLLM proxying DeepSeek, the first
  tool call intermittently fails to parse, returning raw text containing `<|tool_calls_begin|>`
  special tokens instead of a structured function call. This project routes 18 tools through that
  path, twice per demo, in front of judges.
- **Competing hypothesis (R-29):** `deepseek-v4-flash` defaults to **thinking enabled**, and
  thinking-by-default is independently reported to cause JSON parse failures
  (`Graphify-Labs/graphify` #1621). The reported intermittency fits this at least as well as a
  serialisation defect. If the failures vanish with thinking explicitly disabled, the
  "bypass LiteLLM" contingency is unnecessary work.
- **Implemented measurement:**
  `backend/tests/spike/test_deepseek_toolcalls.py`, two arms × 30 turns. It is skipped and
  deselected by default; the explicit opt-in command is
  `pytest backend/tests/spike -v --no-skip`.
  Arm A with `extra_body={"thinking": {"type": "disabled"}}`, Arm B default. Arm A must **assert
  `reasoning_content` is absent** — ADK's `LiteLlm` wrapper forwarding `extra_body` through to
  DeepSeek is undocumented and LiteLLM has a history of silent passthrough failures
  (BerriAI/litellm #20982, #18039). Absence of an error proves nothing.
- **Live result (2026-08-08):** `pytest backend/tests/spike -v --no-skip -s` completed all
  60 turns. Arm A (thinking disabled) had 0/30 failures, p95 2.460 s, 60 provider responses,
  and 0 responses containing `reasoning_content`. Arm B (provider default) had 0/30 failures,
  p95 2.688 s, 60 provider responses, and all 60 contained `reasoning_content`.
- **Outcome:** keep ADK `LiteLlm`; do not build the direct adapter contingency. Every product
  call must pass `extra_body={"thinking": {"type": "disabled"}}`. Provider-default mode is
  incompatible with the no-chain-of-thought boundary even though its tool calls were reliable.

---

## ISSUE-003 — litellm reaches the dependency tree via `google-adk[eval]`

- **Status:** resolved (monitoring)
- **Affects:** security, gate
- **Root cause:** The original audit stated litellm was not an ADK extra. It is: `google-adk[eval]`
  and `google-adk[extensions]` both depend on it (`google/adk-python` #4981, where PyPI's
  quarantine of litellm broke both extras outright). Since `clean_code_spec` §11 makes
  `agent: core_eval` a required gate, litellm is on the critical path **even if the model
  transport bypasses it**.
- **Attempt 1 —** *Change:* pinned `litellm>=1.84` in `pyproject.toml` (1.82.7 and 1.82.8 are
  compromised releases containing a credential stealer).
  *Result:* installed 1.95.0.
  *Evidence:* `find .venv -name 'litellm_init.pth'` returned empty — the 1.82.8 persistence
  artefact is absent.
- **Outcome:** pinned and verified clean. Monitor for further advisories.
