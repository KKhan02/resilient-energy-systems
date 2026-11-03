# SEEDExchange San Rafael, October 27, 2026: consolidated local upload

**Repository target:** `https://gitlab.com/KKhan02/resilient-energy-systems` at recorded main HEAD `1fdf097a`. No GitLab commits, pushes, merge requests or pipelines were created when preparing this ZIP.

## Completed in this package

- `case1/studies/integrated_dispatch_v1/`: new bridge to existing canonical DC-coupled `wp1_v3.model`, annual 2025 outputs, time-series reports, SOC/conservation checks, figure routines, provisional nodal P/Q handoff and conditional pandapower snapshot validator.
- Separate base/no-DER and matched PV+BESS reference runs configured for seven houses, eight with H01, eight with H02, nine with both, and twelve on transformer node 923494.
- `run_parameter_sweep.py`: explicit PV kWp, BESS usable kWh, BESS power kW and inverter kVA axes, with hardware rejection reasons, energy-only cost/self-sufficiency and sensitivity plots.
- Existing reconstructed October study figures from earlier deliverable, paired PNG and SVG with provenance. These figures use the saved **earlier study** data. Do not present them as newly AC-validated annual model outputs.
- Existing source NASA irradiation figures, plus a new 7/9/12-house monthly demand versus GHI source-input comparison. The monthly demand curves were independently rebuilt from the original attached v18 notebook and HOMER XML, and their annual totals match the original saved 2025 references.
- Local unit tests: **9 passed**. Synthetic 8760h reporting smoke generated 6 PNG figures and 4 period tables, in a temporary directory only.

## Not yet done, requires final repository environment and inputs

- Execute canonical 7/8/9/12 home full-year numeric configurations, including monthly self-sufficiency and actual daily/weekly/monthly/yearly PV/BESS figures.
- Execute pandapower conditional critical-hour and 8760h studies; the author's isolated runtime lacked the pinned `pandapower` package and the entire GitLab repository source tree. No completed AC verification is claimed.
- Cross-transformer reassignment optimization, EPM certified wire geometry, verified 106039 nameplate, neutral currents, legal metering, inverter/BMS control testing, complete costs and joint AC-constrained optimization.
- Zero-export policy needs an explicit cap inside the canonical dispatch model; no invalid after-the-fact export clipping is introduced.

## Why the first model uses an assumed 5 kVA for twelve houses

Node 923494/transformer 106039's current source says **5 kW**, not a verified **5 kVA** nameplate. The installed canonical model is hardwired to an assumed 5 kVA reference. Twelve-house results in this initial package are therefore **what-if sensitivity only**. The separate northern 25 kVA transformer remains a valid alternative for H01/H02; no transfer is asserted.

## Upload

Extract into a local clone or use GitLab Web IDE's upload function while preserving the relative paths. Do **not** replace existing `case1` input data or historical saved results. A new feature branch is preferable to direct main editing. Intermediate pushes can start CI; consolidate the verified results before deliberately initiating one final pipeline.

## One terminal command when ready

From repository root (with pinned requirements installed):

```bash
python case1/studies/integrated_dispatch_v1/run_all.py --repo-root . --outdir case1/studies/integrated_dispatch_v1/outputs
```

Then run the needed AC validators for each scenario, e.g.:

```bash
python case1/studies/integrated_dispatch_v1/validate_ac_snapshots.py --repo-root . --hourly case1/studies/integrated_dispatch_v1/outputs/territories/seven/pv_bess/annual_dispatch_8760.csv --outdir case1/studies/integrated_dispatch_v1/outputs/territories/seven/pv_bess/ac_critical --mode critical
```

**Do not publish or treat numerical designs as validated until the real canonical run and appropriate pandapower scenarios pass with source hashes, complete inputs and no unserved load.**
