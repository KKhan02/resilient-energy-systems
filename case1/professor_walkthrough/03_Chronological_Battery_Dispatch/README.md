# How the optimized battery is used across time

Rather than treating battery capacity as a static energy reserve, the optimizer selected hourly charging, discharging and state of charge. It balanced PV, local demand, grid imports, and equipment limits over 8,760 consecutive hours. The sampled week and monthly balances show what the investment actually does through seasons.

## Open the images in order

1. [01_12_houses_weekly_operation.png](01_12_houses_weekly_operation.png): Hourly charging discharge and SOC in one week.
2. [02_12_houses_monthly_energy.png](02_12_houses_monthly_energy.png): Monthly energy balance and seasonality.
3. [03_annual_grid_exchange.png](03_annual_grid_exchange.png): annual grid exchange across the optimized chronological schedule.

## Why the next stage followed

The annual schedule is noncausal perfect-foresight economic operation. We next replayed its active-power injections in a separate AC network model, rather than claiming that the energy constraint proves voltage feasibility.

Original simulations, raw figures and manifests are retained outside this curated folder; see the [main walkthrough](../README.md) and its figure index.
