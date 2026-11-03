# Why inverter siting and reactive control help, and where they fail

We compared common-inverter injection at the transformer head, feeder midpoint and far end. The HIL-style Volt–Var curve can raise low voltages or absorb reactive power during overvoltage, but high reactive currents can overload a 5 kVA transformer. A Q-limiting safeguard removed Q-induced overload in the stress cases while sometimes worsening voltage rise.

## Open the images in order

1. [01_min_voltage_by_position.png](01_min_voltage_by_position.png): Voltage improvement from inverter siting and Volt Var control.
2. [02_transformer_loading_by_position.png](02_transformer_loading_by_position.png): Reactive power effect on transformer loading.
3. [03_transformer_guard_stress.png](03_transformer_guard_stress.png): Thermal safeguard success versus voltage rise failure.

## Why the next stage followed

A locally sensible Q command is not always an electrically feasible command. This motivated a coordinated AC controller that checks household voltage and thermal limits together.

Original simulations, raw figures and manifests are retained outside this curated folder; see the [main walkthrough](../README.md) and its figure index.
