# El Arenal / San Rafael: evidence-based figure pack (27 October 2026)

These figures were generated **locally** from values read from the current GitLab `main` repository at commit `1fdf097a`. No GitLab commits or pipelines were triggered. The simplified CSV extracts included under `figure_source_extracts/` reproduce the selected plotted values; the complete authoritative CSVs remain in GitLab.

## Included figures

| Figure prefix | Repository destination | Meaning |
|---|---|---|
| 01, 02, 02b | `case1/studies/community_georef/field_review_2026_10_27/figures/` | Provisional house locations and transformer assignment counts |
| 03, 04 | `case1/studies/reference_v5_baseline/figures/` | Archived representative feeder transformer and voltage screens |
| 05, 06 | `case1/studies/conditional_94022_pv_bess/figures/` | Actual AC snapshot PV and BESS placement sensitivities |
| 07, 08, 09, 10, 11 | `case1/studies/annual_shared_pvbess/figures/` | Saved 8760h energy screening results, not PyPSA optimization |

## Evidence limitations

1. **Do not present dotted/colored candidate associations as existing wires.** Only transformer 94022 and a separate northern 25 kVA candidate have supplied coordinates. The other transformer poles are unlocated. The 35 properties are not verified service meters.
2. Transformer 106039 / node 923494 has 12 *provisionally nominated* properties and a portal value of **5 kW**, not a verified 5 kVA nameplate.
3. The archived v5 household limits belong to a representative synthetic feeder, not to a verified EPM asset.
4. The seven-property AC plots use separate PV-only and storage-only rectilinear snapshot assumptions, not combined annual power flow.
5. The annual plots use the **myopic 8760h sizing screen**. They are not an optimal capacity expansion result, not network-compliant designs, and their cost results omit installation-specific cables, protection, utility works and various lifecycle expenses.
6. C / K architecture comparison is from the historical study and does not establish preferred neighborhood grouping. The corrected next-phase priority is existing transformer + all current candidate customers, then PV/BESS feasibility, then additional hosting capacity and physical cross-transformer reassignment screening.

## How to use

Extract the archive into the **root of your local GitLab checkout**, preserving `case1/studies/.../figures/` paths. The images are static drafts for group/professor review and can be used in presentations with the above disclaimers. Keep the existing modelling scripts and outputs intact. Do not stage the standalone convenience folder `figure_source_extracts/` if you prefer to rely on the original source CSVs in the repo.

Figure 10 and 11 juxtapose matched equipment assumptions for 7 versus 12 candidate properties; source profiles, true electrical connectivity, and 106039 nameplate remain unverified.

No optimization or new simulations were carried out to make these plots. Recreate plots from the authoritative complete CSVs for each future run, including a timestamp and scenario metadata.
