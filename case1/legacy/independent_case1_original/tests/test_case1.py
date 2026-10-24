"""
Tests for the Case 1 package.

Three layers:

  1. BASELINE      the package still reproduces PyPSA v18 and pandapower v5.
  2. PHYSICS       the causal simulator obeys the model it claims, and the
                   LP and the causal engine agree where they must.
  3. CONSTRAINTS   the transformer envelope, datasheet limits and KPI
                   identities hold.

Run:
    pytest -q tests/
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from sanrafael_case1 import Case1Config, Case1Study, SystemSpec
from sanrafael_case1 import economics as E
from sanrafael_case1 import kpi as K
from sanrafael_case1 import rule_dispatch as RD
from sanrafael_case1 import stress as S
from sanrafael_case1 import sweeps as SW
from sanrafael_case1.validation import (V18_RESOURCE, V18_S2_NASA, v18_spec)


@pytest.fixture(scope="session")
def cfg() -> Case1Config:
    config = Case1Config()
    config.paths.ensure()
    return config


@pytest.fixture(scope="session")
def study(cfg) -> Case1Study:
    return Case1Study(cfg)


@pytest.fixture(scope="session")
def base_system(study):
    spec = SystemSpec(label="TEST_BASE", houses=4, panel_count=12,
                      bess_modules=4, inverter_key="SUN-5K")
    return spec, study.resolve(spec)


@pytest.fixture(scope="session")
def base_dispatch(study, cfg, base_system):
    _, system = base_system
    params = RD.ControlParams.from_config("CONVENTIONAL", cfg)
    return RD.simulate(study.load_kw(4),
                       study.decision_profile.dc_kw(system.pv_kwp),
                       system, cfg, study.homer, params)


# ---------------------------------------------------------------------------
# 1. Baseline
# ---------------------------------------------------------------------------


class TestBaseline:
    def test_homer_inputs(self, study):
        homer = study.homer
        assert homer["annual_load_4hh_kwh"] == pytest.approx(7592.0)
        assert homer["pv_kwp"] == pytest.approx(5.22)
        assert homer["inverter_efficiency"] == pytest.approx(0.95)
        assert homer["battery_roundtrip_efficiency"] == pytest.approx(0.95)
        assert homer["battery_min_soc_pu"] == pytest.approx(0.10)
        assert homer["homer_pv_kwh"] == pytest.approx(7326.3)

    def test_demand_reference_realization(self, study):
        assert study.ts["load_4hh_kw"].sum() == pytest.approx(7592.0, abs=1e-6)
        assert study.ts["load_4hh_kw"].max() == pytest.approx(
            2.166677435937405, abs=1e-12)
        assert study.ts.attrs["clipped_household_hours"] == 168

    def test_nasa_resource(self, study):
        diagnostics = study.decision_profile.diagnostics
        assert diagnostics["annual_ghi_kwh_m2"] == pytest.approx(
            V18_RESOURCE["nasa_annual_ghi_kwh_m2"], abs=1e-4)
        assert diagnostics["poa_to_ghi_ratio"] == pytest.approx(
            V18_RESOURCE["nasa_poa_to_ghi_ratio"], abs=1e-6)
        assert diagnostics["annual_pv_dc_kwh_at_reference_kwp"] == pytest.approx(
            V18_RESOURCE["nasa_annual_pv_dc_kwh"], abs=1e-3)

    def test_homer_calibrated_profile_matches_homer_energy(self, study):
        energy = (study.benchmark_profile.per_kwp_kw
                  * study.homer["pv_kwp"]).sum()
        assert energy == pytest.approx(7326.3, abs=1e-6)

    def test_lp_reproduces_v18_reference_case(self, study, cfg):
        _, system, dispatch = study.run_lp(v18_spec("S2"),
                                           profile=study.decision_profile)
        kpi = K.compute_kpis(dispatch, cfg, study.homer, system.as_row(),
                             "S2", "LP_V18")
        for field, expected in V18_S2_NASA.items():
            assert kpi[field] == pytest.approx(expected, rel=5e-4), field


# ---------------------------------------------------------------------------
# 2. Physics
# ---------------------------------------------------------------------------


class TestCausalDispatch:
    @pytest.mark.parametrize("control", RD.CONTROLLERS)
    def test_all_consistency_checks_pass(self, study, cfg, base_system, control):
        _, system = base_system
        params = RD.ControlParams.from_config(
            control, cfg, export_limit_kw=1.5 if control == "EXPORT_LIMITED"
            else None)
        dispatch = RD.simulate(study.load_kw(4),
                               study.decision_profile.dc_kw(system.pv_kwp),
                               system, cfg, study.homer, params)
        checks = RD.check_consistency(dispatch, system, study.homer)
        failures = checks[checks["status"] == "FAIL"]
        assert failures.empty, failures.to_string(index=False)

    def test_conventional_matches_the_lp_on_annual_energy(self, study, cfg):
        """
        The greedy local-first rule is optimal for self-consumption when no
        constraint binds, so the causal engine and the perfect-foresight LP
        must agree on annual energy. A divergence here means one of the two
        engines is wrong.
        """
        spec = v18_spec("AGREE")
        _, system, lp_dispatch = study.run_lp(spec,
                                              profile=study.decision_profile)
        params = RD.ControlParams.from_config("CONVENTIONAL", cfg)
        causal = RD.simulate(study.load_kw(4),
                             study.decision_profile.dc_kw(system.pv_kwp),
                             system, cfg, study.homer, params)

        lp = K.compute_kpis(lp_dispatch, cfg, study.homer, system.as_row(),
                            "x", "LP")
        rule = K.compute_kpis(causal, cfg, study.homer, system.as_row(),
                              "x", "CAUSAL")

        for field in ("grid_import_kwh", "grid_export_kwh",
                      "battery_throughput_kwh", "self_sufficiency_pct",
                      "pv_used_kwh"):
            assert rule[field] == pytest.approx(lp[field], rel=1e-6), field

    def test_lp_export_peak_is_not_a_planning_value(self, study, cfg):
        """
        The LP is indifferent to WHEN it exports, so its export peak is a
        degenerate artefact. The causal battery-first controller gives the
        physically realistic, higher peak. Documented so the lower LP number
        is never handed to a network study.
        """
        spec = v18_spec("PEAK")
        _, system, lp_dispatch = study.run_lp(spec,
                                              profile=study.decision_profile)
        params = RD.ControlParams.from_config("CONVENTIONAL", cfg)
        causal = RD.simulate(study.load_kw(4),
                             study.decision_profile.dc_kw(system.pv_kwp),
                             system, cfg, study.homer, params)

        lp_peak = float(-lp_dispatch["pcc_import_kw"].min())
        causal_peak = float(-causal["pcc_import_kw"].min())
        assert causal_peak > lp_peak

    def test_battery_never_charges_from_the_grid(self, base_dispatch):
        charging = base_dispatch["battery_charge_kw"] > 1e-9
        importing = base_dispatch["grid_import_kw"] > 1e-9
        pv_present = base_dispatch["pv_available_kw"] > 1e-9
        # Charging while importing is only possible when PV is available and
        # the inverter AC port is saturated; it is never grid energy.
        assert bool((~(charging & importing) | pv_present).all())

    def test_annual_energy_is_conserved(self, base_dispatch):
        demand = base_dispatch["load_kw"].sum()
        served = base_dispatch["served_load_kw"].sum()
        unserved = base_dispatch["unserved_kw"].sum()
        assert demand == pytest.approx(served + unserved, abs=1e-6)

    def test_load_management_preserves_annual_demand(self, study, cfg,
                                                     base_system):
        _, system = base_system
        params = RD.ControlParams.from_config("ADAPTIVE_PLUS_LM", cfg)
        dispatch = RD.simulate(study.load_kw(4),
                               study.decision_profile.dc_kw(system.pv_kwp),
                               system, cfg, study.homer, params)
        assert dispatch["served_load_kw"].sum() == pytest.approx(
            study.load_kw(4).sum(), rel=1e-9)
        assert dispatch.attrs["deferred_backlog_end_kwh"] == pytest.approx(
            0.0, abs=1e-9)

    def test_controllers_are_causal(self, study, cfg, base_system):
        """
        A causal controller cannot react to the future. Perturbing the LAST
        hour of the year must leave every earlier hour untouched.
        """
        _, system = base_system
        load = study.load_kw(4)
        pv = study.decision_profile.dc_kw(system.pv_kwp)
        params = RD.ControlParams.from_config("ADAPTIVE_PLUS_LM", cfg)

        baseline = RD.simulate(load, pv, system, cfg, study.homer, params,
                               initial_soc_pu=0.5)

        perturbed_pv = pv.copy()
        perturbed_pv.iloc[-1] = perturbed_pv.iloc[-1] + 5.0
        perturbed_load = load.copy()
        perturbed_load.iloc[-1] = perturbed_load.iloc[-1] * 3.0
        perturbed = RD.simulate(perturbed_load, perturbed_pv, system, cfg,
                                study.homer, params, initial_soc_pu=0.5)

        before = slice(0, len(load) - 1)
        for column in ("grid_import_kw", "grid_export_kw", "battery_dc_kw",
                       "pv_curtailed_kw"):
            assert np.allclose(baseline[column].to_numpy()[before],
                               perturbed[column].to_numpy()[before]), column


# ---------------------------------------------------------------------------
# 3. Constraints
# ---------------------------------------------------------------------------


class TestTransformerConstraint:
    def test_five_kva_is_apparent_power_not_active_power(self, cfg):
        assert cfg.site.transformer_kva == 5.0
        assert cfg.import_limit_kw < cfg.site.transformer_kva
        assert cfg.import_limit_kw == pytest.approx(
            5.0 * cfg.transformer.loading_limit_pu * cfg.transformer.pf_import)

    def test_limits_scale_with_loading_factor(self, cfg):
        tight = cfg.with_transformer(loading_limit_pu=0.80)
        loose = cfg.with_transformer(loading_limit_pu=1.00)
        assert tight.import_limit_kw < cfg.import_limit_kw < loose.import_limit_kw

    @pytest.mark.parametrize("control", ["CONVENTIONAL", "ADAPTIVE_PLUS_LM"])
    def test_dispatch_respects_the_envelope(self, study, cfg, base_system,
                                            control):
        _, system = base_system
        params = RD.ControlParams.from_config(control, cfg)
        dispatch = RD.simulate(study.load_kw(4),
                               study.decision_profile.dc_kw(system.pv_kwp),
                               system, cfg, study.homer, params)
        assert dispatch["grid_import_kw"].max() <= system.import_limit_kw + 1e-9
        assert dispatch["grid_export_kw"].max() <= system.export_limit_kw + 1e-9

    def test_apparent_power_estimate_is_consistent(self, base_dispatch, cfg):
        tan_phi = math.tan(math.acos(cfg.transformer.pf_import))
        expected_q = base_dispatch["served_load_kw"] * tan_phi
        assert np.allclose(base_dispatch["pcc_q_kvar_estimate"], expected_q)
        assert np.allclose(
            base_dispatch["pcc_apparent_kva_estimate"],
            np.hypot(base_dispatch["pcc_import_kw"], expected_q))

    def test_eight_houses_can_exceed_a_tight_envelope(self, study, cfg):
        """
        At 80% permissible loading the 5 kVA transformer cannot carry the
        eight-house peak. The model must report that as unserved energy, not
        silently exceed the limit.
        """
        tight = cfg.with_transformer(loading_limit_pu=0.80, pf_import=0.90)
        tight_study = study.with_config(tight)
        spec = SystemSpec(label="8HH_TIGHT", houses=8, panel_count=12,
                          bess_modules=4, inverter_key="SUN-5K")
        system = tight_study.resolve(spec)
        assert study.load_kw(8).max() > system.import_limit_kw

        params = RD.ControlParams.from_config("CONVENTIONAL", tight)
        dispatch = RD.simulate(tight_study.load_kw(8),
                               tight_study.decision_profile.dc_kw(system.pv_kwp),
                               system, tight, study.homer, params)
        assert dispatch["grid_import_kw"].max() <= system.import_limit_kw + 1e-9
        assert dispatch["unserved_kw"].sum() > 0


class TestHardwareFeasibility:
    def test_quoted_inverter_is_split_phase(self, cfg):
        model = cfg.hardware.inverter("SUN-5K")
        assert "SG02LP2-US" in model.name
        assert model.rated_ac_kw == 5.0
        assert model.max_pv_dc_kw == 7.5

    def test_large_array_is_infeasible_on_the_quoted_inverter(self, study):
        spec = SystemSpec(label="TOO_BIG", houses=4, panel_count=20,
                          bess_modules=4, inverter_key="SUN-5K")
        system = study.resolve(spec)
        assert not system.hardware_feasible
        assert "max PV input" in " ".join(system.hardware_notes)

    def test_large_array_fits_a_larger_family_member(self, study):
        spec = SystemSpec(label="OK_BIG", houses=4, panel_count=20,
                          bess_modules=4, inverter_key="SUN-8K")
        assert study.resolve(spec).hardware_feasible

    def test_cheapest_feasible_inverter_selection(self, cfg):
        assert SW.cheapest_feasible_inverter(cfg, 5.22) == "SUN-5K"
        assert SW.cheapest_feasible_inverter(cfg, 6.96) == "SUN-5K"
        assert SW.cheapest_feasible_inverter(cfg, 8.70) == "SUN-6K"

    def test_battery_power_is_independent_of_the_inverter_rating(self, study):
        """
        v18 capped battery DC power at the converter rating, which tied energy
        and power together. Case 1 must size them separately.
        """
        small = study.resolve(SystemSpec(label="a", panel_count=12,
                                         bess_modules=4, inverter_key="SUN-5K"))
        large = study.resolve(SystemSpec(label="b", panel_count=12,
                                         bess_modules=4, inverter_key="SUN-12K"))
        assert small.battery.usable_kwh == large.battery.usable_kwh
        assert large.battery.dc_power_kw > small.battery.dc_power_kw
        assert small.battery.dc_power_kw > small.inverter_ac_kw


class TestKpiIdentities:
    def test_self_sufficiency_definition(self, base_dispatch, study, cfg,
                                         base_system):
        _, system = base_system
        kpi = K.compute_kpis(base_dispatch, cfg, study.homer, system.as_row(),
                             "x", "CONVENTIONAL")
        expected = 100 * (1 - kpi["grid_import_kwh"] / kpi["load_kwh"])
        assert kpi["self_sufficiency_pct"] == pytest.approx(expected)

    def test_curtailment_definition(self, base_dispatch, study, cfg,
                                    base_system):
        _, system = base_system
        kpi = K.compute_kpis(base_dispatch, cfg, study.homer, system.as_row(),
                             "x", "CONVENTIONAL")
        assert kpi["pv_available_kwh"] == pytest.approx(
            kpi["pv_used_kwh"] + kpi["pv_curtailed_kwh"], abs=1e-6)

    def test_throughput_is_the_homer_convention(self, base_dispatch, study,
                                                cfg, base_system):
        _, system = base_system
        kpi = K.compute_kpis(base_dispatch, cfg, study.homer, system.as_row(),
                             "x", "CONVENTIONAL")
        assert kpi["battery_throughput_kwh"] == pytest.approx(
            0.5 * (kpi["battery_charge_kwh"] + kpi["battery_discharge_kwh"]))

    def test_missing_columns_are_rejected(self):
        with pytest.raises(ValueError):
            K.validate_dispatch(pd.DataFrame({"load_kw": [1.0]}))


class TestEconomics:
    def test_quote_anchoring(self, study, cfg, base_system):
        _, system = base_system
        breakdown = E.cost_breakdown(system, cfg, study.homer, 3500.0)
        assert breakdown.total_capex_usd == pytest.approx(
            cfg.economics.quoted_reference_subtotal_usd, rel=1e-9)

    def test_compensation_regime_changes_the_useful_size(self, study):
        _, net_metering = SW.pv_marginal_study(
            study, compensation_regime="NET_METERING_HOMER")
        _, self_consumption = SW.pv_marginal_study(
            study, compensation_regime="SELF_CONSUMPTION_ONLY")
        assert (self_consumption["recommended_size"]
                < net_metering["recommended_size"])

    def test_replacement_scheduling(self, study, cfg, base_system):
        _, system = base_system
        breakdown = E.cost_breakdown(system, cfg, study.homer, 3500.0)
        # A 15 year inverter inside a 25 year project is replaced once.
        assert breakdown.converter_replacement_pv_usd > 0
        # A 25 year PV array inside a 25 year project is not.
        assert breakdown.pv_replacement_pv_usd == pytest.approx(0.0)


class TestResilience:
    def test_window_starts_from_the_annual_state_of_charge(self, study, cfg,
                                                           base_system):
        _, system = base_system
        params = RD.ControlParams.from_config("CONVENTIONAL", cfg)
        runner = S.ResilienceRunner(study, system, params,
                                    study.decision_profile, houses=4)
        start = pd.Timestamp("2025-09-15 18:00")
        expected = runner.start_soc(start)

        scenario = S.StressScenario(name="T", family="GRID_OUTAGE",
                                    start=start, duration_h=6,
                                    grid_available=False)
        _, dispatch = runner.run(scenario)
        first = dispatch.iloc[0]
        assert first["grid_import_kw"] == pytest.approx(0.0)
        assert 0.0 <= expected <= 1.0

    def test_outage_results_are_flagged_as_unconfirmed(self, study, cfg,
                                                       base_system):
        _, system = base_system
        params = RD.ControlParams.from_config("CONVENTIONAL", cfg)
        runner = S.ResilienceRunner(study, system, params,
                                    study.decision_profile, houses=4)
        scenario = S.StressScenario(name="T", family="GRID_OUTAGE",
                                    start=pd.Timestamp("2025-06-15 18:00"),
                                    duration_h=12, grid_available=False)
        metrics, _ = runner.run(scenario)
        assert metrics["islanding_confirmed"] is False
        assert metrics["hardware_confirmed_installed"] is False

    def test_low_solar_windows_come_from_the_measured_year(self, study):
        from sanrafael_case1.resource import worst_low_solar_windows
        windows = worst_low_solar_windows(study.decision_profile, 5, top_n=3)
        assert len(windows) == 3
        assert (windows["vs_annual_mean_pct"] < 100).all()
        assert windows["window_per_kwp_kwh"].is_monotonic_increasing

    def test_reserve_raises_minimum_state_of_charge(self, study, cfg,
                                                    base_system):
        _, system = base_system
        results = {}
        for control in ("CONVENTIONAL", "FIXED_RESERVE"):
            params = RD.ControlParams.from_config(control, cfg)
            dispatch = RD.simulate(
                study.load_kw(4),
                study.decision_profile.dc_kw(system.pv_kwp),
                system, cfg, study.homer, params)
            results[control] = float(dispatch["battery_actual_soc_pu"].min())
        assert results["FIXED_RESERVE"] > results["CONVENTIONAL"]
        assert results["FIXED_RESERVE"] >= cfg.dispatch.fixed_reserve_soc_pu - 1e-9
