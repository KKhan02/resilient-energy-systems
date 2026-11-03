# Annual PV+BESS time-series figure generator

This plotting script **does not simulate or optimize PV+BESS**. It produces day/week/month/year diagrams **from one canonical, already validated, 8760-hour simulation export**. It is purposely decoupled from dispatch calculations to avoid creating a fifth, unvalidated battery controller.

To use after the reconciled DC-coupled dispatch writes a complete hourly CSV:

```bash
python report_timeseries.py --input annual_dispatch_8760.csv --outdir figures
```

Required columns and explicit units appear in `report_timeseries.py` and the paired next-phase spec. Year 2025, 8760 hourly local solar-time records, are required. Demand must balance `requested = served + ENS`; PV and battery flow columns must be computed using the canonical core and battery SOC must **not** restart each month.

Outputs include daily, weekly, monthly and annual summary CSVs; PNG+SVG for a highest-demand day, low-solar/high-load day, high-demand week, monthly grid and generation, monthly irradiation and battery charge/discharge, and annual daily trajectories; and an automatic monthly grid-independence summary. The day/week selection is data-driven.

**Not a substitute for coupled pandapower**: network metrics will be omitted unless the source export contains real independently computed AC results. Do not treat reference October 386 energy-screen rows, which contain only annual aggregates and have identified dispatch-model differences, as valid hourly exports.

Uses pandas, numpy and matplotlib; no external web request or GitLab CI is needed to plot already-generated local inputs.

## Included source-derived NASA radiation figures

`source_NASA_2025_figures/` contains genuine 2025 NASA POWER daily/monthly GHI CSV and PNG/SVG charts. These were generated **directly from the user-supplied NASA_POWER_SanRafael_hourly_2025.csv**, in Wh/m² per hour (summed and converted to kWh/m²). **They are not PV generation or self-sufficiency results.** Recreate them with `plot_nasa_ghi.py`. Solar-input results have been produced; PV generation, charging/discharging, import/export and self-sufficiency still require corrected canonical 8760-hour simulation exports.
