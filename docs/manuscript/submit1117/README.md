# 17 November 2026 manuscript / 2026年11月17日稿件

This is the substantially revised manuscript prepared for **Applied Sciences**:

**Auditable Evidence Binding for Large Language Model-Assisted Post-Alarm Diagnosis
in Industrial Sensor Time Series**

The authors confirm that this manuscript has not been submitted to a journal.
The earlier README label referring to a Sensors submission was incorrect.

本目录保存面向 Applied Sciences 准备的大幅修订稿。作者确认尚未实际向期刊投稿；
旧版 README 中关于 Sensors 投稿的标注属于错误说明。

## Files / 文件

| File | Description |
| --- | --- |
| [manuscript.docx](manuscript.docx) | November 17 main manuscript / 11月17日主文 |
| [supplementary.docx](supplementary.docx) | Accompanying supplementary materials / 补充材料 |
| [numerical_comparison.json](numerical_comparison.json) | Document comparison against November 10 / 与11月10日稿件对照 |
| [manifest.json](manifest.json) | Byte lengths and SHA-256 checksums / 文件大小与校验值 |

Verify the package from the repository root:

```bash
python scripts/verify_manuscript_package.py
```

## Numerical preservation / 数值保留

The main manuscript changes 19 paragraphs. Its six Word table objects, 42 Office Math
objects (including inline mathematics), and eight embedded media files are unchanged.
The supplementary DOCX is byte-identical to the November 10 file.

The numerical-token changes are:

- Abstract: adds 0.701 and 0.978, already reported in the prior introduction/results.
- Introduction: removes the roadmap reference to Section 2.
- Discussion: repeats the existing 35.1-percentage-point result.

All other numerical-token sequences in changed paragraphs are retained. The four
manuscript figures in `assets/` are refreshed directly from this DOCX.

主文修改19段，表格、Office Math对象及内嵌媒体文件保持不变。
补充材料与11月10日稿件逐字节一致。新增数字均来自已有结果，删除的数字仅为
章节导读中的 Section 2。本检查确认文档之间的保留情况，不验证原始结果的正确性，
也不意味着文字改写后的全部科学推理均已获得额外实验支持。

## Software and experimental scope / 软件与实验范围

The public code runs the single-event reference workflow. Installation, offline execution,
replay and artifact verification are documented in [the verification guide](../../VERIFICATION.md).
The runtime JSON field names and backend interface are documented there separately from
the manuscript's illustrative schema.

Exact aggregate-table reconstruction still requires the original frozen event manifests,
experimental model responses, evaluator controls and judgments, and statistical artifacts.
This manuscript snapshot and the runnable example do not supply those missing records.
