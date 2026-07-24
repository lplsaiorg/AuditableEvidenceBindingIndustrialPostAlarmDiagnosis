# Auditable Evidence Binding for Industrial Post-Alarm Diagnosis

Executable reference implementation for the manuscript:

> **Auditable Evidence Binding for Large Language Model-Assisted Post-Alarm
> Diagnosis in Industrial Sensor Time Series**
>
> Wu Zhang, Tianwu Lei, Luo Xiao, and Yong Yang

The software runs the paper's final post-alarm method for one frozen alarm event:
deterministic evidence extraction, event-local evidence binding, structured diagnosis,
provenance verification, safety gating, and an auditable handoff to a human reviewer.
It is a diagnosis support pipeline, not an autonomous control system.

![Auditable post-alarm architecture](assets/figure-1-auditable-architecture.png)

*Figure 1 from the paper. The model-visible path proposes a claim-local diagnosis; the
model-invisible path owns provenance, validation, rejection, and escalation.*

## What the Paper Proposes

An LLM explanation can be fluent while still being disconnected from the alarm event.
The paper therefore separates probabilistic diagnosis from deterministic assurance:

1. freeze the alarm interval, reference data, detector metadata, and source identity;
2. extract ranked observation cards from global and local deviations, peaks, and trends;
3. assign randomized event-local aliases such as `E01` and keep raw provenance hidden
   from the model;
4. require a diagnosis record containing supporting evidence, contradicting evidence,
   missing information, confidence, and one allowed action;
5. validate strict JSON, an event-specific JSON Schema, evidence ownership, content
   hashes, and safety policy outside the model; and
6. accept, reject, or escalate the result for human review.

The final conclusion is an allocation of responsibility: the model proposes reviewable
fault-signature hypotheses, while deterministic code owns the trust boundary.

## Directly Executable Final Pipeline

```text
frozen event
  -> validated domain model
  -> deterministic candidate evidence
  -> event-local aliases + hidden provenance registry
  -> event-specific diagnosis schema
  -> selected diagnosis backend
  -> strict parse + schema + provenance + safety audit
  -> immutable artifacts, hashes, logs, and human-review status
```

The default `safe` backend needs no model service and always fails safely to human
escalation. The `rules` backend makes the included example fully executable offline. The
`openai-compatible` backend runs the same audited pipeline with a compatible structured
output API.

## Repository Structure

```text
.
|-- assets/                         Paper figures
|-- configs/                        Versioned method and safety configuration
|-- docs/architecture.md            Module boundaries and trust model
|-- examples/
|   |-- demo-event.json             Frozen example alarm event
|   `-- expected-pipeline.log       Expected stage sequence
|-- src/auditable_evidence_binding/
|   |-- domain.py                   Validated input types
|   |-- evidence.py                 Evidence extraction and ranking
|   |-- provenance.py               Alias binding and hidden registry
|   |-- diagnosis.py                Schema and replaceable backends
|   |-- audit.py                    Deterministic assurance gates
|   |-- observability.py            Human-readable and JSONL logs
|   |-- pipeline.py                 End-to-end orchestration and safe replacement
|   `-- cli.py                      Command-line interface
`-- tests/                          Unit and end-to-end tests
```

The modules are intentionally cohesive and loosely coupled. Evidence extraction does not
depend on a model provider, model backends cannot read the provenance registry, and the
auditor never calls the model. See [the architecture note](docs/architecture.md).

## Environment

Requirements:

- Python 3.11 or newer
- `pip`
- network access only when using an external model backend

Create an isolated environment.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Runtime-only installation:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

## Quick Start

Run the complete offline example:

```bash
aeb-diagnose run \
  --config configs/demo.toml \
  --input examples/demo-event.json \
  --run-dir runs/demo \
  --backend rules
```

The equivalent module command is:

```bash
python -m auditable_evidence_binding run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/demo --backend rules
```

Use a new run directory for each execution. To intentionally replace an existing run,
add `--force`.

Run the fail-safe path without a model:

```bash
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/safe --backend safe
```

This finishes with `escalated`, a valid diagnosis contract, zero confidence, and
`ESCALATE_TO_HUMAN`.

## Model Backend

For an OpenAI-compatible structured output endpoint, set the three environment variables
shown in `.env.example`. The application reads environment variables directly and does
not load `.env` files automatically.

Windows PowerShell:

```powershell
$env:AEB_LLM_BASE_URL = "https://api.example.com/v1"
$env:AEB_LLM_API_KEY = "replace-with-a-secret"
$env:AEB_LLM_MODEL = "replace-with-a-model-id"
```

Linux or macOS:

```bash
export AEB_LLM_BASE_URL="https://api.example.com/v1"
export AEB_LLM_API_KEY="replace-with-a-secret"
export AEB_LLM_MODEL="replace-with-a-model-id"
```

Then execute:

```bash
aeb-diagnose run --config configs/tep.toml --input event.json --run-dir runs/model --backend openai-compatible
```

Do not commit credentials. A deployment should also replace `alias_salt` in the selected
configuration and protect it as deployment configuration.

Available backends:

| Backend | Purpose | External service |
| --- | --- | --- |
| `safe` | Deterministic abstention and human escalation | No |
| `rules` | Reproducible offline demonstration | No |
| `replay` | Audit a frozen diagnosis response | No |
| `openai-compatible` | Structured model generation | Yes |

Replay a saved response:

```bash
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/replay --backend replay --replay-response response.json
```

## Input Contract

`examples/demo-event.json` is the canonical example. An event contains:

- a stable event identifier;
- a frozen alarm interval expressed as inclusive sample indices;
- detector name, version, score, and threshold;
- a source descriptor with dataset name, version, and stable source identifier;
- ordered timestamps; and
- one or more signals with values and frozen reference values.

Every signal value array must have the same length as `timestamps`; each frozen reference
array must be non-empty. The alarm indices must be valid, numeric values must be finite,
and signal names must be unique. The pipeline derives SHA-256 identities for the complete
input, every source-bearing signal, each evidence card, the configuration, and all run
artifacts. Invalid input fails before model invocation.

## Output and Logs

Each run creates self-contained artifacts under the chosen run directory:

```text
runs/demo/
|-- context/
|   |-- model-visible-context.json
|   `-- provenance-registry.json
|-- diagnosis/
|   |-- diagnosis.schema.json
|   |-- raw-response.txt
|   `-- record.json
|-- audit/
|   `-- audit-record.json
|-- logs/
|   |-- pipeline.log
|   `-- pipeline.jsonl
`-- run-manifest.json
```

`pipeline.log` is intended for operators. `pipeline.jsonl` contains the same process as
structured records with stage duration, hashes, aliases, audit-layer outcomes, and final
status. A successful offline run makes the complete assurance path visible:

```text
[01] pipeline             RUNNING    auditable diagnosis run started
[02] load_event           RUNNING    load_event started
[03] load_event           COMPLETED  load_event completed
[04] extract_evidence     RUNNING    extract_evidence started
[05] extract_evidence     COMPLETED  extract_evidence completed
[06] bind_provenance      RUNNING    bind_provenance started
[07] bind_provenance      COMPLETED  bind_provenance completed
[08] build_schema         RUNNING    build_schema started
[09] build_schema         COMPLETED  build_schema completed
[10] generate_diagnosis   RUNNING    generate_diagnosis started
[11] generate_diagnosis   COMPLETED  generate_diagnosis completed
[12] audit_diagnosis      RUNNING    audit_diagnosis started
[13] audit_diagnosis      COMPLETED  audit_diagnosis completed
[14] write_manifest       RUNNING    write_manifest started
[15] write_manifest       COMPLETED  write_manifest completed
[16] pipeline             ACCEPTED   auditable diagnosis run completed: accepted
```

The committed [expected log](examples/expected-pipeline.log) is a stage-order reference.
Run-specific identifiers, timestamps, durations, hashes, and evidence details are recorded
only in generated JSONL logs and manifests. No output records an absolute filesystem path.

Re-run the deterministic audit over an existing run:

```bash
aeb-diagnose verify --config configs/demo.toml --run-dir runs/demo
```

Materialize the configured dynamic schema:

```bash
aeb-diagnose schema --config configs/tep.toml --output diagnosis.schema.json
```

## Paper Conclusion to Code

| Final method responsibility | Executable code | Enforced behavior |
| --- | --- | --- |
| Freeze and validate the event | [`domain.py`](src/auditable_evidence_binding/domain.py) | Rejects malformed alarms, non-finite values, length mismatches, duplicate signals, and invalid source identity |
| Construct evidence cards | [`evidence.py`](src/auditable_evidence_binding/evidence.py) | Computes global/local robust deviations, peaks, trends, quality flags, and deterministic top-K ranking |
| Bind evidence to one event | [`provenance.py`](src/auditable_evidence_binding/provenance.py) | Creates randomized event-local aliases and seals hidden source coordinates and content hashes |
| Constrain the diagnosis record | [`diagnosis.py`](src/auditable_evidence_binding/diagnosis.py) | Builds Draft 2020-12 JSON Schema with runtime evidence-alias enums and interchangeable backends |
| Keep assurance outside the LLM | [`audit.py`](src/auditable_evidence_binding/audit.py) | Applies strict parsing, schema, event ownership, content-hash, evidence-support, confidence, and action gates |
| Preserve an auditable execution | [`pipeline.py`](src/auditable_evidence_binding/pipeline.py) and [`observability.py`](src/auditable_evidence_binding/observability.py) | Writes content-hashed artifacts, SHA-256 manifests, human logs, structured logs, rejection, and escalation status |

The code therefore executes the paper's operational conclusion directly: the LLM may
propose a diagnosis, but it cannot decide whether its own output is structurally valid,
event-bound, supported, or safe.

![Paired counterfactual design](assets/figure-2-counterfactual-design.png)

*Figure 2 from the paper. Counterfactual evaluation changes one labeled factor while
holding the base event and generation settings fixed.*

## Evaluation Scope

The manuscript evaluates the method on HAI 21.03 and the Tennessee Eastman Process (TEP),
including schema constraints, evidence counterfactuals, selective diagnosis, explanation
support, calibration, and safety.

![TEP confusion matrix and selective diagnosis](assets/figure-3-tep-results.png)

*Figure 3 from the paper. TEP fault-level confusion and selective-diagnosis results.*

![Selected effects and confidence intervals](assets/figure-4-primary-effects.png)

*Figure 4 from the paper. Selected effectiveness and safety effects.*

This repository executes the final per-event method and its deterministic audit. Exact
reconstruction of aggregate manuscript tables and figures additionally requires the
frozen benchmark partitions, raw model responses, evaluator records, and model artifacts
used for the study. Those materials are not synthesized by this runner, and the offline
demo must not be interpreted as an independent reproduction of the paper's aggregate
numerical claims.

## Verification

Run the complete test suite:

```bash
python -m pytest
```

The tests cover evidence ranking, deterministic alias binding, strict parsing,
cross-event and tampering rejection, safety escalation, both offline backends, artifact
creation, relative manifest entries, and visible pipeline stages.

## Safety and Limitations

- The system produces a human-review record, never a control command.
- Interlock bypass, direct set-point changes, automatic equipment switching, and similar
  hazardous recommendations are outside the allowed action vocabulary.
- Insufficient or weakly supported evidence forces data collection or human escalation.
- Candidate evidence quality remains a diagnostic ceiling; omitted evidence cannot be
  recovered by the model.
- Benchmark results cannot certify safety in a live plant.
- Deployment requires domain-specific input adapters, frozen references, access control,
  secret management, monitoring, and expert validation.

## Citation

```bibtex
@unpublished{zhang2026auditable,
  title  = {Auditable Evidence Binding for Large Language Model-Assisted
            Post-Alarm Diagnosis in Industrial Sensor Time Series},
  author = {Zhang, Wu and Lei, Tianwu and Xiao, Luo and Yang, Yong},
  note   = {Manuscript submitted to Sensors},
  year   = {2026}
}
```

The DOI in the journal template is a placeholder and should not be used as a persistent
identifier.
