# Architecture

The package implements the paper's final post-alarm handoff as a sequence of cohesive
components. Each component owns one reason to change and communicates through plain
domain objects or JSON-compatible contracts.

## Dependency Direction

```text
CLI
  -> Pipeline
       -> Event domain and configuration
       -> Evidence extraction
       -> Provenance binding
       -> Diagnosis backend
       -> Deterministic audit
       -> Observability and artifact storage
```

Low-level modules do not import the CLI or pipeline. Evidence extraction does not know
which model generates a diagnosis. Diagnosis backends do not read the model-invisible
registry. Audit code does not call a model. This separation keeps model behavior outside
the deterministic trust boundary.

## Modules

| Module | Responsibility |
| --- | --- |
| `domain.py` | Validated event, signal, alarm, detector, and evidence-card types |
| `config.py` | Immutable configuration loaded from TOML |
| `evidence.py` | Robust global/local sensor features and top-K card selection |
| `provenance.py` | Randomized event-local aliases, content hashes, registry, and model-visible context |
| `diagnosis.py` | Dynamic schema and replaceable generation backends |
| `audit.py` | Strict JSON, Draft 2020-12 schema, provenance, and safety validation |
| `observability.py` | Human-readable and JSONL run logs |
| `pipeline.py` | Stage orchestration and immutable run artifacts |
| `cli.py` | User-facing commands and exit codes |

## Trust Boundary

The model receives only the model-visible context and dynamic output schema. It never
receives raw event identifiers, source coordinates, source hashes, or the provenance
registry. After generation, deterministic code resolves every evidence alias and applies
the safety policy. A failure at an earlier layer cannot be repaired by a later layer.

## Extension Points

Implement the `DiagnosisBackend` protocol to add another model runtime. The new backend
must accept model-visible context and a dynamic JSON schema and return one raw response
string. It must not access or mutate the provenance registry.

New evidence extractors should return `EvidenceCard` values and retain all raw-source
coordinates in the registry-building layer. New safety policies belong in the audit layer,
not in model prompts alone.
