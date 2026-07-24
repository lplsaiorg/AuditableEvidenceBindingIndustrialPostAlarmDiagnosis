**English** | [简体中文](README_CN.md)

# Auditable Evidence Binding for Industrial Post-Alarm Diagnosis

This repository is the executable reference implementation for the manuscript:

> **Auditable Evidence Binding for Large Language Model-Assisted Post-Alarm
> Diagnosis in Industrial Sensor Time Series**
>
> Wu Zhang, Tianwu Lei, Luo Xiao, and Yong Yang

The work addresses diagnosis after an industrial anomaly detector has raised an alarm:

> How can an LLM-generated diagnosis remain traceable to sensor evidence from the current
> event, while deterministic software outside the model owns validation, rejection, and
> escalation?

The repository implements the paper's final single-event execution path:

```text
frozen alarm event
  -> candidate observation extraction
  -> event-local aliases and hidden provenance registry
  -> event-specific diagnosis schema
  -> diagnosis backend
  -> strict parsing, schema, provenance, and safety audit
  -> accept, reject, or escalate for human review
```

The output is a rejectable and traceable human-review record. It is not proof of physical
root cause and must not be connected directly to industrial control actions.

## Paper Overview

### 1. Research Problem

Industrial anomaly detectors can identify abnormal intervals, but a structurally valid and
fluent LLM explanation may still:

- cite observations that do not belong to the current alarm event;
- copy evidence identifiers without responding to their sensor content;
- omit contradictory evidence or missing information;
- violate the required data contract;
- express confidence unsupported by the available evidence; or
- recommend high-risk operations such as bypassing an interlock, changing a set point, or
  switching equipment.

The paper therefore evaluates structural validity, provenance integrity, content
responsiveness, semantic support, and operational safety as separate layers. Success at a
later layer cannot repair a failure at an earlier layer.

### 2. Proposed Method

![Auditable post-alarm architecture from the paper](assets/figure-1-auditable-architecture.png)

*Figure 1 from the paper. The model receives event-local candidate observations, while a
model-invisible deterministic layer owns provenance, dynamic foreign keys, schema
validation, and safety gates.*

The paper proposes an auditable context evidence package. For every alarm event, the
method:

1. freezes the alarm interval, detector version, reference-data version, and input
   identity;
2. constructs candidate observation cards from global deviations, local pre-alarm
   deviations, peaks, trends, and quality flags;
3. assigns event-local aliases such as `E01` through `E08`;
4. stores dataset version, source hash, coordinates, detector version, extractor version,
   reference version, and content hash in a registry hidden from the model;
5. requires every diagnosis to state supporting evidence, contradicting evidence, missing
   information, confidence, and one permitted action;
6. validates strict JSON, Draft 2020-12 JSON Schema, dynamic foreign keys, event
   ownership, content hashes, and safety policy outside the model; and
7. assigns `accepted`, `rejected`, or `escalated` before human review.

The record permits at most three candidate explanations. Insufficient evidence is an
explicit method outcome, not a software failure, and must lead to `COLLECT_MORE_DATA` or
`ESCALATE_TO_HUMAN`.

### 3. Experimental Design

The manuscript evaluates the method on two public industrial time-series benchmarks:

| Dataset | Independent evaluation unit | Role in the paper |
| --- | --- | --- |
| HAI 21.03 | Attack or false-alarm cluster | Structural reliability, provenance, identifier shortcuts, and counterfactual tests |
| Tennessee Eastman Process | Independent simulation run | Known fault semantics, selective diagnosis, explanation support, calibration, and safety |

The paired counterfactual conditions include evidence-order permutation,
attribute-to-identifier permutation, direction reversal, cross-event content replacement,
and provenance conflicts. Each comparison changes one labeled factor while holding the
base event and generation conditions fixed.

![Paired counterfactual design from the paper](assets/figure-2-counterfactual-design.png)

*Figure 2 from the paper. The design distinguishes use of sensor content from copying an
identifier or relying on a fixed position.*

### 4. Main Conclusions

The manuscript reports:

| Reported conclusion | Full evidence package | Comparison | Reported difference |
| --- | ---: | ---: | ---: |
| First-pass strict-schema compliance on HAI | 0.978 | 0.701 | +27.7 percentage points |
| Macro-averaged top-1 recall on TEP | 0.742 | 0.612 | +13.0 percentage points |
| Correct label with an explanation judged supported | 0.714 | 0.548 | +16.6 percentage points |
| Citations following moved content rather than the old identifier | - | - | +58.2 percentage points |
| Insufficient-evidence selection or human escalation after cross-event replacement | - | - | +29.1 percentage points |

These results support the following conclusions:

- structural correctness does not establish evidential correctness;
- valid-identifier coverage cannot prove that a model used the associated evidence;
- event-local binding and counterfactual tests can evaluate content responsiveness;
- an LLM can propose reviewable fault-signature hypotheses;
- deterministic software must own schema enforcement, provenance, dynamic foreign keys,
  hashes, permitted actions, and final status; and
- the system should be a rejectable interface between monitoring and human review, not an
  autonomous controller.

![TEP results from the paper](assets/figure-3-tep-results.png)

*Figure 3 from the paper. TEP fault-level confusion and selective-diagnosis results.*

![Primary effects from the paper](assets/figure-4-primary-effects.png)

*Figure 4 from the paper. Selected effectiveness and safety effects with confidence
intervals.*

## What This Repository Executes

This repository executes the final per-event diagnosis and audit path. It is not merely a
plotting package.

For one frozen event, the software:

1. validates the event data contract;
2. computes and ranks candidate observation cards;
3. assigns event-local aliases independently of candidate rank;
4. separates model-visible context from the model-invisible provenance registry;
5. compiles a JSON Schema against the current event's alias set;
6. invokes the selected diagnosis backend;
7. applies strict parsing, schema, provenance, and safety audits; and
8. writes the diagnosis, audit record, logs, and content-hash manifest.

The offline `rules` backend produces an `accepted` demonstration. The model-free `safe`
backend produces a contract-valid insufficient-evidence record and an `escalated` status.

## Paper Conclusions Mapped to Code

"Directly related" means that the module implements the same method responsibility. It
does not mean that one demonstration run can re-estimate the manuscript's aggregate
statistics.

| Paper responsibility or conclusion | Directly related code | Executable responsibility |
| --- | --- | --- |
| Alarm events must be frozen and validated first | [`domain.py`](src/auditable_evidence_binding/domain.py) | Validates alarm bounds, finite values, signal lengths, unique names, detector metadata, and source information |
| Candidate-observation quality is the diagnostic ceiling | [`evidence.py`](src/auditable_evidence_binding/evidence.py) | Computes global and local robust deviations, peaks, trends, quality flags, and deterministic top-K ranking |
| Evidence identifiers must be scoped to one event | [`provenance.py`](src/auditable_evidence_binding/provenance.py) | Assigns event-local randomized aliases and stores source coordinates, versions, source hashes, and content hashes |
| Structural validity must be separated from semantic judgment | [`diagnosis.py`](src/auditable_evidence_binding/diagnosis.py) | Builds a Draft 2020-12 schema, current-event alias enums, and interchangeable diagnosis backends |
| A model cannot audit its own output | [`audit.py`](src/auditable_evidence_binding/audit.py) | Enforces duplicate-key, non-finite-number, schema, event-ownership, dynamic-key, hash, and safety checks |
| Insufficient evidence must fail safely | [`diagnosis.py`](src/auditable_evidence_binding/diagnosis.py) and [`audit.py`](src/auditable_evidence_binding/audit.py) | Produces the safe default and escalates low-confidence, contradictory, or incomplete evidence |
| Executions must be traceable and replayable | [`pipeline.py`](src/auditable_evidence_binding/pipeline.py) | Orchestrates the stages and writes hashes, manifests, states, and re-auditable artifacts |
| Logs must expose execution of the final method | [`observability.py`](src/auditable_evidence_binding/observability.py) | Writes both an operator-readable log and detailed JSONL records |
| Model providers must remain outside the deterministic core | [`diagnosis.py`](src/auditable_evidence_binding/diagnosis.py) | Isolates safe fallback, offline rules, replay, and model APIs behind one backend protocol |

See [`docs/architecture.md`](docs/architecture.md) for dependency direction and the trust
boundary.

## Project Structure

```text
.
|-- assets/                         Figures from the paper
|-- configs/                        Method, evidence, and safety configuration
|-- docs/
|   `-- architecture.md            Module and trust boundaries
|-- examples/
|   |-- demo-event.json             Directly executable frozen alarm event
|   `-- expected-pipeline.log       Expected stage sequence
|-- src/auditable_evidence_binding/
|   |-- canonical.py               Canonical JSON and SHA-256
|   |-- config.py                  Configuration loading and validation
|   |-- domain.py                  Domain objects and input contract
|   |-- evidence.py                Candidate observation extraction
|   |-- provenance.py              Evidence aliases and provenance registry
|   |-- diagnosis.py               Dynamic schema and diagnosis backends
|   |-- audit.py                   Deterministic audit
|   |-- observability.py           Human-readable and JSONL logs
|   |-- pipeline.py                End-to-end orchestration
|   `-- cli.py                     Command-line interface
`-- tests/                          Unit and end-to-end tests
```

The implementation keeps the following boundaries:

- evidence extraction does not depend on a model provider;
- diagnosis backends receive only model-visible context and the schema;
- diagnosis backends cannot read the hidden provenance registry;
- the auditor never calls a model;
- the CLI owns only arguments and exit codes;
- the pipeline owns orchestration, not domain algorithms; and
- `--force` can replace only a run directory created by this pipeline.

## Environment

Requirements:

- Python 3.11 or newer
- `pip`
- network access only for an external model backend

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Linux or macOS

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

## Run the Final Pipeline

### 1. Complete Offline Example

```bash
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/demo --backend rules
```

Expected final status:

```text
ACCEPTED
```

Equivalent module command:

```bash
python -m auditable_evidence_binding run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/demo --backend rules
```

### 2. Model-Free Safe Fallback

```bash
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/safe --backend safe
```

Expected final status:

```text
ESCALATED
```

The backend does not guess a fault. It emits:

- `INSUFFICIENT_EVIDENCE`
- `confidence = 0`
- `ESCALATE_TO_HUMAN`

### 3. OpenAI-Compatible Model Endpoint

The application reads environment variables directly and does not load `.env` files
automatically.

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

Run:

```bash
aeb-diagnose run --config configs/tep.toml --input event.json --run-dir runs/model --backend openai-compatible
```

Never commit real credentials. A deployment must also replace `alias_salt` in the selected
configuration and manage it through the deployment environment.

### 4. Replay a Frozen Response

```bash
aeb-diagnose run --config configs/demo.toml --input examples/demo-event.json --run-dir runs/replay --backend replay --replay-response response.json
```

## Diagnosis Backends

| Backend | Purpose | External model |
| --- | --- | --- |
| `safe` | Deterministic insufficient-evidence record and human escalation | No |
| `rules` | Reproducible offline engineering demonstration | No |
| `replay` | Replay and audit a frozen response | No |
| `openai-compatible` | Call a structured-output model endpoint | Yes |

The `rules` backend verifies the software path. It is not one of the experimental models
used in the paper and cannot reproduce the paper's model-effect estimates.

## Input Contract

[`examples/demo-event.json`](examples/demo-event.json) is the minimal complete example. An
input event contains:

- a stable event identifier;
- dataset name, version, and source identifier;
- timestamps aligned with the signal arrays;
- alarm start and end indices plus the alarm score;
- detector name, version, and threshold; and
- signal name, unit, process role, event values, and frozen reference values.

Before invoking a model, the software rejects:

- non-object inputs or missing core structures;
- alarm intervals with no pre-alarm data or invalid bounds;
- non-integer alarm indices;
- `NaN`, infinity, and other non-finite values;
- signal arrays whose length differs from the timestamp array;
- case-insensitive duplicate signal names; and
- empty reference arrays.

## Run Artifacts

Every run writes:

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

| Artifact | Content |
| --- | --- |
| `model-visible-context.json` | Event-local evidence that may be sent to the diagnosis backend |
| `provenance-registry.json` | Model-hidden event ownership, coordinates, versions, and hashes |
| `diagnosis.schema.json` | Output contract generated for the current event |
| `raw-response.txt` | Unmodified backend response |
| `record.json` | Diagnosis record after strict parsing |
| `audit-record.json` | Status and reasons for every deterministic audit layer |
| `run-manifest.json` | Software, input, configuration, backend, and SHA-256 identities for core artifacts |

The manifest and logs use relative artifact names and never record an absolute local
filesystem path.

## Logs Expose the Complete Method

`pipeline.log` is intended for operators. `pipeline.jsonl` supports audit, retrieval, and
automated analysis. An accepted offline run shows the complete assurance path:

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

The JSONL log additionally records:

- stage duration;
- input and configuration hashes;
- backend and model metadata;
- candidate count and scores;
- aliases registered for the event;
- context, registry, schema, and response hashes;
- strict-parse, schema, provenance, and safety-layer outcomes; and
- the final `accepted`, `rejected`, or `escalated` state.

See [`examples/expected-pipeline.log`](examples/expected-pipeline.log) for the committed
stage-order reference.

## Re-Audit and Export the Schema

Re-audit an existing run:

```bash
aeb-diagnose verify --config configs/demo.toml --run-dir runs/demo
```

Export the schema for a configuration:

```bash
aeb-diagnose schema --config configs/tep.toml --output diagnosis.schema.json
```

## Tests

```bash
python -m pytest
```

The test suite covers:

- candidate ranking and event-local aliases;
- integer alarm indices and case-insensitive signal-name ambiguity;
- content-hash tampering rejection;
- forbidden high-risk language;
- safe fallback and human escalation;
- complete offline end-to-end execution;
- relative manifest entries and visible pipeline stages; and
- `--force` protection for directories not created by the pipeline.

## Reproducibility Scope

This repository directly executes and verifies the final per-event method. The included
example alone cannot re-estimate the manuscript's aggregate HAI and TEP results.

Exact reconstruction of the paper's tables, confidence intervals, and figures additionally
requires the study's frozen:

- HAI and TEP event manifests and split indices;
- data hashes and reference versions;
- models and generation environment;
- raw model responses;
- third-party automated evaluation records; and
- paired statistical-analysis and resampling artifacts.

The runner does not fabricate or substitute those materials. Consequently:

- the numerical values in this README are values reported by the manuscript;
- the `rules` example demonstrates execution, not aggregate empirical reproduction;
- one `accepted` run does not reproduce the paper's overall effects;
- automated evaluation is not industrial-expert validation;
- results on simulated TEP faults do not certify field safety; and
- content responsiveness and fault-signature consistency do not prove physical causal
  root cause.

## Safety Boundary

- The system must never execute equipment-control actions directly.
- Interlock bypass, shutdown, set-point changes, and equipment switching require a human
  workflow.
- Contradictory evidence, missing information, and low confidence require escalation.
- Candidate-observation quality remains the ceiling for downstream diagnosis.
- Deployment still requires access control, secret management, runtime monitoring,
  incident replay, operator approval, and organizational accountability.

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
