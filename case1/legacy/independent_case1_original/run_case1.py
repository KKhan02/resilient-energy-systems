#!/usr/bin/env python3
"""
Run SEEDExchange Case Study 1 for El Arenal (San Rafael, Antioquia).

Transformer-Constrained PV-BESS Oversizing, Vulnerability and Adaptive
Resilience Assessment.

Usage
-----
    python run_case1.py                       # full study
    python run_case1.py --validate-only       # only the baseline checks
    python run_case1.py --no-validate         # skip the baseline checks
    python run_case1.py --annual-power-flow   # add 8,760 h power flow (slow)
    python run_case1.py --full-outage-grid    # 12 months x 8 hours of outages
    python run_case1.py --houses 6
    python run_case1.py --loading-limit 0.8 --pf-import 0.90
    python run_case1.py --tariff-sensitivity

Required input files, discovered in the working directory, ./data,
./results or the parent directory:

    SimulacionTampico1k.xml                  accepted HOMER model
    NASA_POWER_SanRafael_hourly_2025.csv     raw NASA POWER hourly weather
    Nasa Data.csv                            NASA POWER monthly radiation
                                             (optional; the HOMER monthly
                                             values are used if absent)

Results are written to ./results_case1/ as CSV, with figures under
./results_case1/figures/.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from sanrafael_case1 import Case1Config, Case1Study
from sanrafael_case1.pipeline import run_case1


def build_config(args) -> Case1Config:
    cfg = Case1Config()

    transformer_changes = {}
    if args.loading_limit is not None:
        transformer_changes["loading_limit_pu"] = args.loading_limit
    if args.pf_import is not None:
        transformer_changes["pf_import"] = args.pf_import
    if args.pf_export is not None:
        transformer_changes["pf_export"] = args.pf_export
    if transformer_changes:
        cfg = cfg.with_transformer(**transformer_changes)

    if args.tariff_sensitivity:
        cfg = replace(cfg, economics=replace(cfg.economics,
                                             run_tariff_sensitivity=True))

    if args.project_root is not None:
        from pathlib import Path
        cfg = replace(cfg, paths=replace(cfg.paths,
                                         project_root=Path(args.project_root)))
    return cfg


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="SEEDExchange San Rafael Case Study 1")
    parser.add_argument("--houses", type=int, default=4,
                        help="households in the transformer group (default 4)")
    parser.add_argument("--no-validate", action="store_true",
                        help="skip the v18/v5 baseline validation")
    parser.add_argument("--validate-only", action="store_true",
                        help="run only the baseline validation and exit")
    parser.add_argument("--annual-power-flow", action="store_true",
                        help="add the 8,760 hour power flow (several minutes)")
    parser.add_argument("--full-outage-grid", action="store_true",
                        help="use the full 12 month x 8 hour outage grid")
    parser.add_argument("--loading-limit", type=float, default=None,
                        help="transformer permissible loading, per unit")
    parser.add_argument("--pf-import", type=float, default=None,
                        help="load power factor used for the import limit")
    parser.add_argument("--pf-export", type=float, default=None,
                        help="inverter power factor used for the export limit")
    parser.add_argument("--tariff-sensitivity", action="store_true",
                        help="also run the optional tariff sensitivity")
    parser.add_argument("--no-figures", action="store_true",
                        help="skip figure generation")
    parser.add_argument("--project-root", default=None,
                        help="directory holding the input files")
    args = parser.parse_args(argv)

    cfg = build_config(args)
    cfg.paths.ensure()

    print("San Rafael / El Arenal - Case Study 1")
    print(f"  transformer      {cfg.site.trafo_number}, "
          f"{cfg.site.transformer_kva:.1f} kVA single-phase")
    print(f"  loading limit    {cfg.transformer.loading_limit_pu:.2f} pu")
    print(f"  power factor     import {cfg.transformer.pf_import:.2f}, "
          f"export {cfg.transformer.pf_export:.2f}")
    print(f"  active envelope  import {cfg.import_limit_kw:.3f} kW, "
          f"export {cfg.export_limit_kw:.3f} kW")
    print(f"  households       {args.houses}")
    print(f"  results          {cfg.paths.results_dir}")
    print()

    try:
        study = Case1Study(cfg)
    except FileNotFoundError as exc:
        print("Missing a required input file.\n")
        print(exc)
        print("\nPlace the file in the working directory, ./data, ./results or "
              "the parent directory, or pass --project-root.")
        print("Required inputs:")
        print("  SimulacionTampico1k.xml                the accepted HOMER model")
        print("  NASA_POWER_SanRafael_hourly_2025.csv   raw NASA POWER hourly weather")
        print("  Nasa Data.csv                          NASA POWER monthly radiation "
              "(optional)")
        return 2

    # Print what was actually read, so a wrong or stale input file is visible
    # before any result is produced.
    homer = study.homer
    print(f"  HOMER model      {cfg.paths.homer_xml}")
    print(f"                   PV {homer['pv_kwp']:.2f} kWp, inverter "
          f"{homer['inverter_kw']:.1f} kW, {homer['battery_modules']} battery "
          f"modules, {homer['annual_load_4hh_kwh']:.0f} kWh/yr for "
          f"{homer['reference_houses']} houses")
    print(f"                   tariff {homer['grid_buy_usd_per_kwh']:.3f} buy / "
          f"{homer['grid_sell_usd_per_kwh']:.3f} sell USD/kWh, "
          f"{homer['project_lifetime_y']} y at "
          f"{homer['discount_rate']:.1%}")
    print(f"  weather          {cfg.paths.nasa_hourly_csv.name}, "
          f"{study.decision_profile.diagnostics['annual_pv_dc_kwh_at_reference_kwp']:.1f}"
          f" kWh/yr DC at {homer['pv_kwp']:.2f} kWp")
    print(f"  monthly radiation {study.monthly_radiation_source}")
    print()

    if args.validate_only:
        from sanrafael_case1.validation import run_validation
        table = run_validation(cfg, study, include_sweeps=True, verbose=True)
        path = cfg.paths.results_dir / "baseline_validation.csv"
        table.to_csv(path, index=False)
        print("Saved:", path)
        return 0 if (table["status"] == "PASS").all() else 1

    results = run_case1(
        cfg=cfg, study=study,
        run_validation=not args.no_validate,
        run_annual_power_flow=args.annual_power_flow,
        full_outage_grid=args.full_outage_grid,
        houses=args.houses,
    )

    if not args.no_figures:
        try:
            from sanrafael_case1.figures import make_all_figures
            paths = make_all_figures(results, cfg, study)
            print(f"\nWrote {len(paths)} figures to {cfg.paths.figures_dir}")
        except Exception as exc:  # figures must never fail the study
            print(f"\nFigure generation skipped: {exc}")

    print("\nHeadline results")
    for key, value in results.notes.items():
        print(f"  {key}: {value}")

    validation = results.tables.get("baseline_validation")
    if validation is not None:
        failures = int((validation["status"] == "FAIL").sum())
        print(f"  baseline validation: {len(validation) - failures}"
              f"/{len(validation)} checks passed")
        if failures:
            print("  WARNING: baseline validation failed; Case 1 results "
                  "built on these inputs are not trustworthy")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
