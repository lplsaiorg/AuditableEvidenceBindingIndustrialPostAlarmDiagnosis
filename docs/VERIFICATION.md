# Verification and reproduction / 验证与复现

## Result as of 17 November 2026

The public reference implementation was cloned, installed in a fresh virtual environment,
and checked on **Windows with CPython 3.12.13**, jsonschema 4.25.0 and pytest 8.4.2.

| Check | Observed result |
| --- | --- |
| Editable installation with development dependencies | Passed |
| Original test suite | 8 passed |
| Suite after replay, integrity and escalation fixes | 15 passed |
| Installed `aeb-diagnose` command, rules backend | `accepted` |
| Safe fallback | `escalated` |
| Replay of the rules response | `accepted` |
| Re-audit of saved artifacts | `accepted`, artifact integrity passed |
| TEP schema export | Completed |

The first test invocation encountered a local Windows temporary-directory permission
error; specifying an accessible pytest `--basetemp` resolved it. This was an environment
issue, not a test failure in the implementation.

No paid or live generation-model API was invoked. The OpenAI-compatible backend therefore
remains unverified against a live provider. The checks above do not re-estimate the
manuscript's HAI or TEP results.

## Run locally

After cloning, from the repository root:

```bash
python -m venv .venv
```

Activate `.venv` using the command for your shell, then:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python scripts/verify_manuscript_package.py
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/check-rules --backend rules
aeb-diagnose verify --config configs/demo.toml --run-dir runs/check-rules
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/check-safe --backend safe
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/check-replay --backend replay --replay-response runs/check-rules/diagnosis/raw-response.txt
aeb-diagnose schema --config configs/tep.toml --output runs/tep.schema.json
```

Use fresh run-directory names on subsequent invocations. A successful `accepted` or
`escalated` execution returns exit code 0; an audit rejection returns 2. An execution
error returns 1. If the system temporary directory is inaccessible, pass pytest an
accessible, dedicated `--basetemp` directory.

## Defects corrected in this update

These were reproduced with failing regression tests before the fixes:

1. **Replay normalized JSON before strict audit.** Duplicate keys could disappear and an
   invalid original response could be accepted. Replay now supplies the saved response
   text directly to the strict parser.
2. **Re-audit omitted manifest verification.** Changes to source coordinates, derived
   records or effective configuration could pass unnoticed. Re-audit now checks required
   artifacts and their hashes, bounds paths to the run directory, and compares the
   effective configuration fingerprint.
3. **Explicit escalation could be marked accepted.** A supported candidate requesting
   `ESCALATE_TO_HUMAN` now produces `escalated`, as do other configured escalation actions.

The local manifest must be trusted. A party able to rewrite both the artifacts and their
manifest can replace their hashes; this mechanism is not a digital-signature system.

## Relation to the manuscript

The reference software implements event-local evidence binding and deterministic audit
responsibilities. It is **not the frozen experimental runner** used to estimate all
reported model effects.

The runtime candidate fields are `label`, `explanation`, `variables`,
`supporting_evidence`, `contradicting_evidence`, `missing_information`, `confidence`
and `action`. The illustrative supplementary JSON uses `diagnostic_label`, `text`,
`supporting_evidence_ids`, `contradicting_evidence_ids`, `missing_evidence`,
`recommended_action` and an additional `claim_id`. The examples are therefore not
interchangeable verbatim; use `aeb-diagnose schema` for the executable contract.

The released backend uses a provider's structured-output interface; it does not include
the paper's frozen Gemma/Qwen generation harness with lm-format-enforcer, the full
HAI/TEP experimental selection, or the automated evaluator pipeline. The source hashes
in the demo identify supplied event values, not independently downloaded official files.
Model-weight hashes, detector configurations, event manifests, frozen prompts, evaluator
judgments and bootstrap records are needed to reconstruct aggregate estimates.

## 中文结论

**当前仓库作为单事件证据绑定、审计、重放的参考实现可运行，15项测试通过。**
本次同时修复了原始响应重放、清单/配置校验和人工升级状态三类问题。

可运行的工程示例、稿件文件校验和论文实验复现是三个不同层次。
本次已验证前两者；未调用在线模型，也未用原始逐记录实验数据重算论文统计结果。
运行时Schema字段与补充材料示例名称不同，应以导出的Schema为准。
