# Stage 15. Matched-hardware assignment and AC robustness

**Research question:** Does reassignment A0 to A1 save energy and money when equipment is held fixed, and is the corrected six-house 113699 network robust to household PF and uncertain provisional service lengths?

## Figure 01 | 34-house matched-hardware economics

[01_34house_matched_assignment_energy.svg](01_34house_matched_assignment_energy.svg)

- Paired definition: **delta = A1 customer assignment minus A0 customer assignment**, with the *same* total fixed PV, battery, DC battery power, inverter ratings and source 2025 demand traces within each pair. Both alternatives have the same 34 individual synthetic households and **64,532 kWh/year** of gross demand.
- Frozen A0-origin equipment, minimum cost: A1 increases import **159.371 kWh/year** and assumed annual equipment+grid energy cost **USD 46.217/year**.
- A0-origin, SS90: A1 increases import **1,424.628 kWh/year**, cost **USD 413.142/year**.
- A1-origin, minimum cost: A1 decreases import **1,070.384 kWh/year**, cost **USD 310.411/year**.
- A1-origin, SS90: A1 decreases import **2,204.165 kWh/year**, cost **USD 639.208/year**.

**What this does and does not mean:** The advantage changes sign with equipment origin. It is therefore incorrect to recommend A0 or A1 as a universal winner on energy alone. The comparisons reuse a **proposed 92395 STAR** shared on both sides. They do not include a full comparable 34-house AC, losses integrated with the optimizer, new service connection CAPEX, actual transformer circuits, permitting or installation quotes. No reported pair has `AC_verified=True`. This is an **ENERGY-ONLY** controlled comparison, not an engineering grid approval.

Source: `StudyA_A0_A1_MatchedHardware_Full_v1/MATCHED_A0_VS_A1_SAME_HARDWARE_PAIRS.csv`, independent signed 16-case audit at `case1/studies/SEEDExchange_StudyA_Matched_Hardware_2026-11-21/FULL_16_REMOTE_AUDIT_2026-11-21.md`, source commit `120c4e96`.

## Figure 02 | 113699 voltage sensitivity, same stress hours

[02_113699_pf_length_sampled_ac.svg](02_113699_pf_length_sampled_ac.svg)

- Six provisional A1 household connections on EPM GIS LV proxy transformer 113699, **3 kVA assumed**.
- Two frozen, previously cyclic-SOC-corrected equipment origins: A0 (17 panels/3 battery modules/5 kVA inverter), A1 (20 panels/4 battery modules/6 kVA inverter).
- PF 0.95/0.98/1.00 × provisional service cable multiplier 1.0/1.3/1.6. **25 common timestamps** selected from the two existing complete reference AC datasets. Exactly **450 saved AC case-hours** and 18 factor-origin groups, all CONVERGED.
- PF=0.95 main research voltage band 0.95–1.05 pu: A0 hardware **1/3/3** voltage-failed sampled hours across the three lengths; A1 hardware **1/2/2**. Hence **12 case-hour failures in total**, occurring at three different dates: 2025-03-14 19:00, 2025-03-30 19:00 and 2025-11-30 20:00.
- PF=0.98 and PF=1.00: zero sampled main-band failures across the six groups for each hardware origin. Both equipment sets have identical recorded minimum sampled voltage per PF/length (worst time common), though their other hours and AC losses are not identical.
- **No transformer or LV line overloads in any 450 sampled AC case-hours.** At PF .95 length 1.6, minimum **0.948734337 pu**, peak transformer **99.373870%** on an **assumed** 3 kVA nameplate, peak modelled line loading **11.061548%**.
- The stricter 0.97–1.03 pu threshold is violated by every factor group. It is a separate research screen, not EPM compliance determination.

**Annual versus sampled:** The previously signed **two full-year** PF .98/length1.0 replays each passed the principal AC screen in all **8,760 hours**. They had **245 and 120 annual hours below .97 pu**, respectively. The latest PF and length variation replays **25 hours only**, not 8,760. Summed sampled case-hour counts cannot be annualized. All 34-house assignment scenarios remain separate from this one-transformer feeder validation.

Sources: `StudyA_A0_A1_MatchedHardware_113699_NineFactorStress_v1/{RUN_MANIFEST.json,factor_ac_hourly.csv,factor_summary.csv}`, user result commit `ce8301b6`; original full-year AC independent audit `case1/studies/SEEDExchange_StudyA_Matched_Hardware_2026-11-21/AC113699_TWO_8760H_AC_REMOTE_AUDIT_2026-11-22.md`.

## Poster decisions and limitations

Keep both figures only when the story needs controlled assignment and voltage robustness. The important conclusions are **conditional energy comparison** and **reactive-demand sensitivity**, not utility connection approval. For the eventual poster, pair Figure 01 with the original A0/A1 geospatial map in Stage 12, and Figure 02 with Stage 13's annual SOC-corrective mechanism. Do not put either figure in a results panel labelled installed network, field-verified transformer, complete nine-factor annual validation or grid-code compliance.

Both SVGs are editable vector plots built deterministically from the recorded source CSV fields; axes, units and sample denominators are included. Existing historical walkthrough PNGs are unchanged.

Python-rendered [Figures 30–31](../python_figures_30_36_v1/) are now uploaded. For the later, distinct four-house 113699 and ten-house 94022 eight-design screen, see the new Figure 37 generator and battery closure audit. These populations and matched six-house A1 113699 are different.
