# Inverter siting and local Volt-Var control

**Question:** How does placing a shared inverter at the transformer head, feeder midpoint or end affect customer voltage, transformer loading and electrical losses?

These figures are preserved from the earlier EPM GIS / Volt-Var studies. They use sampled AC operating points, assumed LV house connections, proxy conductors and fixed active-power dispatch. They are **not** manufacturer-SOC-corrected annual control results. Interpret the original reference lines shown inside each chart as historical study criteria, not Colombian regulatory limits.

## Figures

1. [01_min_voltage_by_position.png](01_min_voltage_by_position.png): Lower-household-voltage response by inverter siting and local Volt-Var settings.
2. [02_transformer_loading_by_position.png](02_transformer_loading_by_position.png): Reactive support and transformer apparent-power loading.
3. [03_transformer_guard_stress.png](03_transformer_guard_stress.png): A Q safeguard can remove a thermal overload while worsening voltage control.
4. [04_max_voltage_by_position.png](04_max_voltage_by_position.png): Maximum household voltage. Remote injection can improve weak low voltage yet increase the overvoltage risk.
5. [05_sampled_feeder_losses_by_position.png](05_sampled_feeder_losses_by_position.png): Mean **power losses in kW over selected hours**, not annual loss energy. Reactive flows can increase electrical losses.

## Engineering interpretation

Siting affects **both** minimum and maximum voltage. Increasing available Q is not automatically beneficial: Q changes current, transformer apparent-power loading and line losses. Local Q(U) control has no guarantee of satisfying every feeder constraint at once. This motivated coordinated AC Q selection, presented in [07](../07_Coordinated_AC_Q_Optimization/).

Sources are retained unchanged under [SEEDExchange EPM Q Review](../../research_archive/past_review_packages/SEEDExchange_EPM_Q_Review_2026-11-02/) and [TrafoGuard stress review](../../research_archive/past_review_packages/TrafoGuard_Stress_Review/). The new images are **copies**, not regenerated simulation outputs.
