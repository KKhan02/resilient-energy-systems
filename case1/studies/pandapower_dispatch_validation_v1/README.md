# SEEDExchange pandapower sweep extension v1.2

This adds three inverter siting choices (`lv_head`, `middle`, `far_end`) to the existing representative radial feeder, and supports **5 through 15 households**. It is a scenario study, NOT reconstruction of the actual El Arenal service lines or transformer territories.

**Install:** Unzip at the `resilient-energy-systems` repository root, overwriting only `case1/studies/pandapower_dispatch_validation_v1/run_validation.py`. The ZIP does not contain input dispatch files or historical results; it keeps your previous results and original notebooks intact. The `--plots-only` fix from v1.1 remains included.

## Run in Miniforge Prompt (Windows CMD)

From the repository root:

```bat
cd case1\studies\pandapower_dispatch_validation_v1
python -m unittest discover -s tests -v
python export_missing_dispatch.py --dry-run
```

The dry run checks which household counts lack an 8760-hour optimized schedule. By default, seven, nine and twelve already exist, so eight *new* PyPSA solves are needed. Export one case first if you prefer:

```bat
python export_missing_dispatch.py --cases 5
```

Or produce the whole missing population using the existing fixed-panel MILP (no 6840-task rerun):

```bat
python export_missing_dispatch.py
```

It reads `../pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv`, chooses the minimum annual-cost optimal fixed-PV 5 kVA design for each household count and re-solves 8760 hourly PyPSA dispatch for cases without a CSV. It needs the **same full-study source input and recent model.py** as the prior optimization. It compares solved annual costs against the saved selected results and refuses to pass off mismatched results as identical. Existing 7/9/12 files are not rewritten.

Then run the **critical-hour sweep across all 11 household counts, 3 PV/BESS locations, two household load allocations and two power factors**:

```bat
python run_validation.py --mode critical --cases 5 6 7 8 9 10 11 12 13 14 15 --siting lv_head middle far_end --allocation equal far_end_heavy --power-factors 0.98 0.90 --output outputs/critical_5_to_15_all_sitings
```

This checks all 11 × 3 × 2 × 2 = **132 conditional operating scenarios**, each at selected critical hours. It does **not** represent 132 different existing EPM feeders.

For a **full-year baseline sweep** across 5–15 houses, use only one siting, load distribution and PF initially (11 × 8760 = **96,360** pandapower calculations):

```bat
python run_validation.py --mode full --cases 5 6 7 8 9 10 11 12 13 14 15 --siting lv_head --allocation equal --power-factors 0.98 --output outputs/full_5_to_15_reference
```

For the 12-house comparative full-year siting study, if you want the extra depth:

```bat
python run_validation.py --mode full --cases 12 --siting lv_head middle far_end --allocation equal --power-factors 0.98 --output outputs/full_12_siting_comparison
```

Do not run all 132 variants for all 8760 hours unless specifically warranted. The original script stores **every tap profile every simulated hour**, which makes full 132-variant runs particularly large.

**Scope limitations:** Same fixed 324.5 m representative LV length for every household count; 1–2 households per tap. Not GIS-derived conductor lengths, phase allocations, verified house-to-EPM-transformer wiring, inverter electrical dynamics, curtailment or Volt-Var control. Moving the inverter changes voltage/losses but does not automatically optimize its placement. Existing physical 5 kVA and 4.5 kVA screening thresholds remain unchanged. The original PyPSA dispatch limits the pre-loss PCC; pandapower computes AC losses/Q independently.

**Do not interrupt:** Running twelve-house AC analyses may continue in their own terminals. New results use separate output folders and do not touch ongoing outputs.
