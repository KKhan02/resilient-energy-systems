# SEEDExchange: professor research walkthrough

**Status: research storyline updated 25 November 2026.** The figure index contains **37 curated figures** across 15 numbered stages, including eight newly regenerated Python figures. Additional Stage 14 local PNGs retain their own manifest. It is not a field-certification report or final poster. All figure copies retain links to original data and code; no original simulation outputs are moved or rewritten.

## Research storyline

The study begins with 35 provisional candidate properties, 2025 NASA POWER resource and synthetic household demand, and an EPM GIS-backed low-voltage skeleton with assumed service connections. A full 6,840-task PyPSA/Linopy campaign then optimizes integer PV/BESS/inverter choices and chronological 8,760-hour dispatch under **perfect foresight**.

Independent pandapower tests show why aggregate energy/PCC feasibility does not establish household voltage or thermal feasibility. We examine inverter siting, local Volt-Var, transformer safeguards, coordinated reactive power and their effects on voltage and losses.

**New since the original 3 November walkthrough:** a manufacturer's 20% minimum battery-SOC restriction, successful **SOC-consistent 7-house active-power feedback** under the stricter original voltage research band, and a **12-house reference full-year 0.95–1.05 pu AC pass** with nighttime Q disabled. Full-year stress screening also demonstrates how the original 0.97 pu threshold can classify hours differently from a 0.95 pu engineering target. A reuse-first AC-validation campaign is assessing previously optimized equipment choices; no complete network-feasible economic frontier is claimed yet.

For the historical connected narrative see [RESEARCH_NARRATIVE.md](RESEARCH_NARRATIVE.md). For the explicit continuation of the research story after Stage 11, see [RESEARCH_STORY_AFTER_STAGE11.md](RESEARCH_STORY_AFTER_STAGE11.md). For original source paths see [FIGURE_INDEX.csv](FIGURE_INDEX.csv).

## Presentation order

| Stage | Topic | Key purpose |
|---|---|---|
| 01 | [Community and inputs](01_Community_and_Inputs/) | Geography, 35 provisional houses, EPM GIS and resource evidence |
| 02 | [Joint PV/BESS sizing](02_Joint_PV_BESS_Sizing/) | Reuse the 6,840-task investment campaign and price/self-sufficiency trade-offs |
| 03 | [Annual battery operation](03_Chronological_Battery_Dispatch/) | Optimized chronological battery charge/discharge and SOC |
| 04 | [Representative feeder AC](04_Representative_Feeder_AC_Screen/) | Why economic screening is not household AC feasibility |
| 05 | [EPM GIS network evidence](05_Geographic_EPM_Feeder_Evidence/) | Infrastructure-backed conductor graph and uncertain service attachments |
| 06 | [Inverter siting and local Volt-Var](06_Inverter_Siting_and_VoltVar/) | Lower/upper voltage, thermal loading, guard behavior and feeder loss |
| 07 | [Coordinated Q and capability](07_Coordinated_AC_Q_Optimization/) | Q-ratio feasibility versus voltage and transformer-loading trade-offs |
| 08 | [Full-year AC and uncertainty](08_Annual_AC_and_Uncertainty/) | Revised voltage bands, 7- and 12-house annual AC and sensitivity limits |
| 09 | [SOC-consistent AC-aware redispatch](09_AC_Aware_Redispatch/) | Four strict-screen 94022 failures resolved by changing annual active-power timing |
| 10 | [Full-campaign equipment feasibility](10_Campaign_Equipment_Feasibility/) | Historical investment reuse, manufacturer SOC and annual AC queue, still in progress |
| 11 | [Next research decisions](11_Next_Research_Decisions/) | Field evidence, loss-aware sizing, resilience and forecasting gaps |
| 12 | [Geographic assignment and routing](12_Geographic_Assignment_and_Routing/) | A0/A1 spatial evidence, 92395 proposed STAR/MST electrical trade-off |
| 13 | [Annual AC corrections and conditional retrofit](13_Annual_AC_Corrections_and_Conditional_Retrofit/) | Original versus corrected 432-case results; strictly hypothetical A0 five-edge network sensitivity |
| 14 | [PV/BESS sizing and utilization](14_PVBESS_Sizing_and_Utilization/) | 34-house annual cost-import-curtailment diagram, marginal storage value, later six-design AC evidence and PV-first timing diagnostic and two-territory sizing comparison |
| 15 | [Matched hardware and AC robustness](15_Matched_Hardware_and_AC_Robustness/) | Same-hardware 34-house assignment controls and 113699 PF/length undervoltage vulnerability |

**As of 22 November 2026:** the original-network corrected portfolio remains 376/432 AC feasible, while 408/432 is a conditional total only if the hypothetical five-edge 94022 retrofit is substituted. A later six-design A1 106039 model comparison now has 27/27 source-stitched annual factor cases passing after SOC-aware correction, with narrow assumed transformer margins. The selected A1-origin SS90 matched-hardware portfolio now has conditional reference PF0.98 annual AC and loss-cost evidence in both assignments (common hypothetical 92395 STAR); other matched portfolios remain partially AC-verified. The 113699 PF/length uncertainty result is a 25-hour sampled AC screen, not an annual nine-factor pass. Hydropower is excluded.

## Interpretation requirements

- **Voltage bands are separate:** 0.97–1.03 pu is the old strict model sensitivity; 0.95–1.05 pu is the proposed engineering magnitude target. Reference to Colombia's national 0.90–1.10 pu or historical EPM 0.90–1.05 pu does **not** make hourly balanced-proxy simulations regulatory certification.
- **AC and energy models are distinct:** PyPSA optimizes fixed-hardware operation with SOC; pandapower independently replays AC voltage and currents. Active-power feedback for **one seven-house reference** was completed, not yet generalized to the archived campaign.
- **Old Q-control plots differ:** earlier sampled coordinated-Q studies used different nighttime Q and SOC assumptions. Preserve them as historic controller comparisons, not direct manufacturer-supported annual dispatch.
- **Costs and grid data are conditional:** demand is synthetic, conductor/service data and some transformer nameplates are provisional or hypothetical, and pandapower losses are not integrated into equipment-cost optimization. Do not claim commercially verified designs.
- **No duplication or invalid completion claims:** the campaign uses the archived 6,840 optimized energy tasks; unvalidated or partial annual-AC output folders remain pending.

## Original studies

- [Current numerical AC and campaign work](../studies/ac_aware_redispatch_v1/)
- [Original PyPSA full study](../studies/pypsa_joint_optimization_v1/)
- [EPM GIS and coordinated Q](../studies/epm_gis_pandapower_v1/)
- [Research status audit](../RESEARCH_STATUS_AND_AUDIT.md) (older document; later progress appears here)
- [Figure provenance index](FIGURE_INDEX.csv)

## Python-only figure reproducibility (25 November 2026)

User instruction: all research figures must be generated by Python from actual numerical data, with executable plotting source and provenance. Existing SVGs 30–35 are retained as historical files; they are not accepted as Python-reproduced merely because they have source tables. Use `generate_figures_30_36.py` to regenerate six figures and produce new Figure 36 (eight-design annual reference portfolio). The script checks the eight source CSVs against GitLab content SHA-256 (only uniform LF/CRLF conversion allowed), validates row counts and key identities, and writes PNG, SVG and a source/output manifest into a new folder. No numerical simulations. The new files are **pending local execution and visual review**, and should replace the active index paths only after verification. Figures 1–29 and supplemental historical files still need an inventory-level plotting-code provenance audit; no claim of complete Python reproduction yet.

From repository root (Miniforge):

```bat
set "WALK=case1\professor_walkthrough"
python "%WALK%\generate_figures_30_36.py" --repo-root . --out "%WALK%\python_figures_30_36_v1" --preflight-only
python "%WALK%\generate_figures_30_36.py" --repo-root . --out "%WALK%\python_figures_30_36_v1"
```

## 25 November: completed Python figure upload and sizing robustness

Seven PNGs (30–36) now match the uploaded Python manifest byte-for-byte according to GitLab content metadata. Active figure index uses these PNGs; original SVGs preserved. The seven uploaded regenerated SVG metadata hashes differ from the local receipt; newline conversion is plausible, not independently established. Figure 36 visually inspected. [Python outputs](python_figures_30_36_v1/). Figure 37 (sample-only eight-design nine-factor matrix) is prepared by `plot_sizing_nine_factor.py`, pending generation/upload. Study A is intentionally the reusable modelling foundation for B and C; do not transfer territory-specific feasibility or hardware directly.

## Active stage-local Python figures

[Stage 14: Figures 32–36](14_PVBESS_Sizing_and_Utilization/python_figures/) and [Stage 15: Figures 30, 31, 37](15_Matched_Hardware_and_AC_Robustness/python_figures/). Active index paths are relative to each stage. These are copies of original Python outputs, not new plots. Original generator folders and receipts remain unchanged; future figures should be generated within the relevant stage.
