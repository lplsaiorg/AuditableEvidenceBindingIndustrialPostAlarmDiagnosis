# Auditable Evidence Binding for LLM-Assisted Industrial Post-Alarm Diagnosis

This repository accompanies the manuscript:

> **Auditable Evidence Binding for Large Language Model-Assisted Post-Alarm Diagnosis in Industrial Sensor Time Series**
>
> Wu Zhang, Tianwu Lei, Luo Xiao, and Yong Yang

The paper studies a specific problem that begins after an industrial anomaly detector has
raised an alarm: how can a large language model propose a useful diagnosis without
disconnecting its explanation from the sensor observations that actually belong to the
event?

The proposed answer is an **auditable context evidence package**. It turns a frozen alarm
interval into a claim-local diagnostic record whose structure, provenance, evidence links,
and permitted actions can be checked outside the language model. The intended output is a
rejectable handoff to a human reviewer, not an autonomous control decision.

## Paper at a Glance

### Problem

An LLM-generated post-alarm explanation can fail in several independent ways:

- it may not satisfy the required output schema;
- it may cite an identifier that is syntactically valid but belongs to another event;
- it may copy visible identifiers without using the associated sensor content;
- it may omit contradictory observations or missing information;
- it may express unjustified confidence or recommend a hazardous action.

The paper argues that these failures cannot be represented by one accuracy or citation
score. Structural validity, provenance integrity, content responsiveness, semantic support,
and operational safety must be evaluated separately.

### Proposed Evidence Contract

![Auditable post-alarm architecture](assets/figure-1-auditable-architecture.png)

*Figure 1. Auditable post-alarm architecture. The model-visible path produces a
claim-local record, while the model-invisible layer owns provenance, schema validation,
dynamic foreign keys, safety gating, and audit status.*

For each alarm event, the method:

1. builds up to eight candidate observation cards from global and local deviations,
   temporal features, detector contributions, process metadata, and quality flags;
2. assigns randomized event-local aliases such as `E01` through `E08`;
3. stores source coordinates, file hashes, dataset versions, extractor versions, and
   content hashes in a model-invisible registry;
4. asks the LLM for up to three ranked explanations, each with supporting evidence,
   contradicting evidence, missing information, confidence, and an allowed action; and
5. rejects records that fail strict parsing, JSON Schema, runtime foreign keys,
   event ownership, provenance hashes, or safety policy.

Shutdown, interlock bypass, set-point modification, and equipment switching are not
directly executable outputs. Conflicting or insufficient evidence must lead to more data
collection or human escalation.

### Evaluation

The manuscript uses two public industrial time-series benchmarks for complementary
purposes:

| Dataset | Evaluation unit | Role in the paper |
| --- | --- | --- |
| HAI 21.03 | Attack or false-alarm cluster | Schema reliability, provenance, identifier shortcuts, counterfactual evidence tests, and held-out alarms |
| Tennessee Eastman Process (TEP) | Independent simulation run | Known fault signatures, selective diagnosis, calibration, explanation support, and safety |

The retrospective HAI evaluation contains 137 alarm records nested in 50 independent
clusters. The primary TEP evaluation contains 500 independent runs: 20 runs from each of
20 fault classes and 100 normal runs. Repeated generation conditions and evaluator calls
remain attached to their underlying event and do not increase the statistical sample size.

The paired experimental conditions include:

- ordinary versus schema-constrained generation;
- full evidence versus an information-matched summary;
- order-only permutation as a null control;
- attribute-to-identifier permutation;
- direction reversal;
- cross-event content replacement;
- provenance conflicts that must be rejected before model invocation; and
- deterministic identifier-copying controls.

![Paired counterfactual design](assets/figure-2-counterfactual-design.png)

*Figure 2. Paired counterfactual design. Every comparison keeps the base event and
generation settings fixed while changing only the labeled factor.*

## Main Conclusions

The paper's final conclusion is not simply that an LLM becomes more accurate when given a
longer prompt. It is that an industrial post-alarm system should divide responsibility
between two components:

- the LLM proposes reviewable fault-signature hypotheses and explains support,
  contradiction, and uncertainty;
- deterministic code owns schema enforcement, event-local provenance, dynamic foreign
  keys, content hashes, action restrictions, rejection, and escalation.

The current manuscript draft reports the following headline values:

| Conclusion tested | Full evidence | Paired comparison | Difference |
| --- | ---: | ---: | ---: |
| First-pass strict-schema compliance on HAI | 0.978 | 0.701 ordinary generation | +27.7 percentage points |
| Citations following moved attributes | 0.776 | 0.194 retaining the old identifier | +58.2 percentage points |
| TEP macro-averaged top-1 recall | 0.742 | 0.612 information-matched summary | +13.0 percentage points |
| Correct TEP label with a supported explanation | 0.714 | 0.548 information-matched summary | +16.6 percentage points |
| Potentially hazardous recommendation rate | 0.008 | 0.016 information-matched summary | -0.8 percentage points |

These claims concern auditability, content responsiveness, and fault-signature support.
They do not establish physical root causes, industrial-domain expert acceptance, field
safety, or autonomous-control readiness.

![TEP confusion matrix and selective diagnosis](assets/figure-3-tep-results.png)

*Figure 3. TEP fault-level confusion matrix and selective-diagnosis characteristics shown
in the manuscript.*

![Selected effects and confidence intervals](assets/figure-4-primary-effects.png)

*Figure 4. Selected effectiveness and safety effects with the confidence intervals shown
in the manuscript.*

## Code Directly Tied to the Conclusions

The following map identifies the development code that is directly responsible for each
step between an industrial event and a paper conclusion. These files currently live in the
authors' development workspace and must be transferred with their dependencies and frozen
artifacts for the public reproducibility release.

| Paper conclusion or responsibility | Development code | What the code does |
| --- | --- | --- |
| Official data and file identity are frozen | `docs/paper/code/paper1/data_contracts.py` | Scans HAI and TEP source files and records file-level hashes and contracts |
| Schema, evidence roles, safe actions, and rejection are deterministic | `docs/paper/code/paper1/protocol_v6.py` | Builds the Draft 2020-12 schema; performs strict parsing and runtime validation; creates the safe skeleton and identifier-copying baseline |
| Constrained generation changes structure while evidence remains fixed | `docs/paper/code/paper1/scripts/run_paper1_0712_llm.py` | Renders prompts, binds the runtime schema to `lm-format-enforcer`, executes generation, validates first-pass outputs, and records model and environment metadata |
| HAI structural and counterfactual conditions are paired by event | `docs/paper/code/paper1/scripts/build_paper1_0712_hai_e1_e3.py` | Builds ordinary, constrained, identifier-only, order, attribute-permutation, direction-reversal, cross-event, and provenance-conflict conditions |
| HAI structural and evidence-response effects are computed | `docs/paper/code/paper1/scripts/evaluate_paper1_0712_hai_e1_e3.py` | Calculates strict-schema and dynamic-key rates, counterfactual metrics, failure accounting, and 5,000-resample cluster bootstrap intervals |
| TEP candidate cards and blinded conditions are built | `docs/paper/code/paper1/tep_semantic_v2.py` and `docs/paper/code/paper1/scripts/build_paper1_0712_tep_e4_e6.py` | Loads official TEP runs, extracts candidate cards, freezes fault references and partitions, randomizes aliases, constructs matched conditions, and computes candidate-card pilot metrics |
| Automated evaluator controls are tested | `build_paper1_0713_deepseek_control.py`, `run_paper1_0713_deepseek_control.py`, and `audit_paper1_0713_deepseek_control.py` under `docs/paper/code/paper1/scripts/` | Builds seven control strata, runs three isolated evaluator calls per case, aggregates majority decisions, and audits accuracy and prompt-injection resistance |
| Manuscript figures and table consistency are checked | `docs/paper/latex/paper1_2/sensors/tools/plot_sensors_results.py` | Checks arithmetic consistency in the manuscript result dataset and renders the failure, TEP, and effect figures |

The intended trace is:

```text
official data
  -> hashed data contracts and frozen event manifests
  -> candidate observation cards and event-local registry
  -> paired model-visible conditions
  -> raw constrained and unconstrained generations
  -> strict validation and safety decisions
  -> HAI / TEP / evaluator metrics with event-level resampling
  -> manuscript tables, figures, and conclusions
```

The public release should preserve this chain rather than publish only plotting code or
already aggregated numbers.

## Current Numerical-Evidence Status

There is an important distinction between code that implements the proposed protocol and
code that currently supplies the final manuscript numbers.

The current plotting script reads:

```text
docs/paper/latex/paper1_2/innovation_review/prospective_scenario.json
```

That file declares:

```text
status: illustrative_prospective_simulation_not_observed_except_previously_available_table8_pilot
purpose: Pre-study novelty review and protocol stress testing only
```

Accordingly, `plot_sensors_results.py` currently validates the internal arithmetic of a
prepared scenario and renders it; it does not reconstruct all headline values from raw
model responses and evaluator records. The numerical table above therefore describes the
values stated in the current manuscript draft, not results independently reproduced by
this repository.

Before the repository can support the final empirical conclusions, the release must:

1. replace the prospective scenario with observed, frozen result artifacts;
2. connect raw model and evaluator outputs to all HAI and TEP metrics;
3. implement and expose the TEP paired bootstrap, multiplicity corrections, calibration,
   safety bounds, and failure denominators used by the manuscript;
4. generate the result dataset consumed by the plotting script from those artifacts; and
5. provide one documented command sequence that rebuilds every reported table and figure.

This status note should be updated only when that end-to-end chain is deposited and
verified.

## Responsible Interpretation

- Candidate observation quality remains a diagnostic ceiling: the extractor may include
  irrelevant cards or omit relevant mechanisms.
- TEP is simulated, while HAI lacks complete variable-level causal labels.
- Automated evaluation is not a substitute for industrial-domain expert review.
- Benchmark safety rates cannot certify field deployment.
- The system is a human-review interface and must never be connected directly to
  industrial control actions.

## Citation

The manuscript is currently under submission. Until final bibliographic metadata is
available, please cite:

```bibtex
@unpublished{zhang2026auditable,
  title  = {Auditable Evidence Binding for Large Language Model-Assisted
            Post-Alarm Diagnosis in Industrial Sensor Time Series},
  author = {Zhang, Wu and Lei, Tianwu and Xiao, Luo and Yang, Yong},
  note   = {Manuscript submitted to Sensors},
  year   = {2026}
}
```

The DOI in the current journal template is a placeholder and should not be used as a
persistent identifier.

## Contact

Yong Yang, corresponding author: `YongYang@tiangong.edu.cn`
