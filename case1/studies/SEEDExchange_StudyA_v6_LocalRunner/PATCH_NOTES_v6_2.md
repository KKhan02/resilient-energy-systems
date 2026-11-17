# Study A v6.2, transformer proximity correction

- User correction: house-to-transformer distance determines the A1 **candidate membership**. Missing EPM LV GIS does not mean LV service is absent.
- Historical A0 remains based on the original recorded transformer association, with unchanged profile indices.
- A1 now computes the closest transformer from **projected transformer coordinates** among the six original study territories, without checking LV segments for membership.
- The expected H03/H06 -> 113699 and H13 -> 85398 movements are retained only as a regression assertion. Other households, including H30-H33 on 92395, remain with their source transformer under the six-territory comparison.
- Only after transformer choice, the selected transformer's LV geometry is used for provisional AC attachment. Missing LV geometry blocks constructing that AC graph, not customer membership or load-only assessment.
- The manifest records each house's ranking and distances to all six transformers, making assignments independently auditable.
- Transformer 113306, an EPM-recorded 5-kVA asset east of H31-H33, is a **separate potential sensitivity**, not automatically in the six-territory A1 comparison. If included in pure nearest ranking, H32/H33 become 113306 candidates, but connection, capacity and existing served load remain unverified.
- No other model, tariff, PF, equipment, inverter, battery, cost, or source-file change. No numerical PyPSA or pandapower was run for this package. GitLab untouched.

From repo root in Miniforge Prompt/Anaconda Prompt:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\tests" -v
python "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\seed_study_a_v6.py" prepare --repo-root . --v4-run-dir "case1\studies\SEEDExchange_StudyA_LocalPreflight_v4\outputs\run_02" --out "case1\studies\SEEDExchange_StudyA_v6_LocalRunner\outputs\run_01\input_manifest_v6_2.json"
```

If input_manifest_v6_2.json already exists, use a **new filename or run folder**, never overwrite it. If the source transformer count or nearest ranking changes, the runner fails closed rather than changing assignments silently.
