"""
Economics: installed cost, replacements, net present cost, and the test for
the economically useful PV/BESS size (objective 4).

Cost basis, unchanged from v18 where it overlaps:

  * The COMPONENT SPLIT comes from the accepted HOMER model
    (PV 3,856 / battery bank 4,770 / converter 3,330 USD).
  * The overall LEVEL is anchored to the project quotation subtotal
    (11,974.79 USD), by scaling the HOMER allocation by
    11,974.79 / (3,856 + 4,770 + 3,330) = 1.0016.
  * Alternative sizes are LINEAR SCREENING EXTRAPOLATIONS, not supplier
    quotations. Nothing here is a quoted price for a size that was not quoted.

Case 1 additions:

  * replacement scheduling inside the 25 year project life, for the inverter
    (15 y) and the battery (the lesser of float life and throughput life),
  * net present cost and a levelised cost of served energy,
  * a marginal benefit/cost test that identifies where oversizing stops
    paying for itself, instead of extrapolating capacity indefinitely and
    curtailing the surplus.

DOUBLE-COUNTING NOTE
--------------------
v18 charged a battery wear cost of 0.052 USD/kWh of throughput AND treated
CAPEX separately. Charging wear and scheduling replacements both represent
the same degradation, so the Case 1 net present cost uses REPLACEMENTS only
and reports the wear charge separately as a diagnostic. Both conventions are
returned so the v18 figures remain reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import Case1Config
from .lp_model import ResolvedSystem


def capital_recovery_factor(rate: float, years: float) -> float:
    if rate == 0:
        return 1.0 / years
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


def present_value(amount: float, rate: float, year: float) -> float:
    return amount / (1 + rate) ** year


# ---------------------------------------------------------------------------
# Installed cost
# ---------------------------------------------------------------------------


@dataclass
class CostBreakdown:
    pv_capex_usd: float
    battery_capex_usd: float
    converter_capex_usd: float
    total_capex_usd: float
    quote_scale: float
    pv_replacement_pv_usd: float
    battery_replacement_pv_usd: float
    converter_replacement_pv_usd: float
    replacement_pv_usd: float
    battery_life_y: float
    battery_life_basis: str

    def as_row(self) -> dict:
        return {
            "pv_capex_usd": self.pv_capex_usd,
            "battery_capex_usd": self.battery_capex_usd,
            "converter_capex_usd": self.converter_capex_usd,
            "capex_usd": self.total_capex_usd,
            "quote_scale": self.quote_scale,
            "replacement_pv_usd": self.replacement_pv_usd,
            "pv_replacement_pv_usd": self.pv_replacement_pv_usd,
            "battery_replacement_pv_usd": self.battery_replacement_pv_usd,
            "converter_replacement_pv_usd": self.converter_replacement_pv_usd,
            "battery_life_y": self.battery_life_y,
            "battery_life_basis": self.battery_life_basis,
        }


def component_capex(system: ResolvedSystem, cfg: Case1Config, homer: dict
                    ) -> tuple[float, float, float, float]:
    """Return (pv, battery, converter, quote_scale) installed cost in USD."""
    econ = cfg.economics
    reference_panels = round(homer["pv_kwp"] / (cfg.hardware.module.rated_w / 1000.0))
    panels = system.spec.panel_count
    modules = system.spec.bess_modules
    converter_kw = system.inverter_ac_kw

    if panels == 0:
        pv = 0.0
    elif panels == reference_panels:
        pv = homer["pv_capex_usd"]
    elif econ.linear_pv_capex:
        pv = homer["pv_capex_usd"] * panels / reference_panels
    else:
        pv = np.nan

    if modules == 0:
        battery = 0.0
    elif modules == homer["battery_modules"]:
        battery = homer["battery_bank_capex_usd"]
    elif econ.linear_bess_capex:
        battery = homer["battery_bank_capex_usd"] * modules / homer["battery_modules"]
    else:
        battery = np.nan

    if converter_kw == 0:
        converter = 0.0
    elif np.isclose(converter_kw, homer["inverter_kw"]):
        converter = homer["converter_capex_usd"]
    elif econ.linear_converter_capex:
        converter = homer["converter_capex_usd"] * converter_kw / homer["inverter_kw"]
    else:
        converter = np.nan

    reference_allocation = (
        homer["pv_capex_usd"] + homer["battery_bank_capex_usd"]
        + homer["converter_capex_usd"]
    )
    quote_scale = econ.quoted_reference_subtotal_usd / reference_allocation

    return pv, battery, converter, quote_scale


def cost_breakdown(system: ResolvedSystem, cfg: Case1Config, homer: dict,
                   annual_battery_throughput_kwh: float = 0.0) -> CostBreakdown:
    econ = cfg.economics
    rate = homer["discount_rate"]
    life = homer["project_lifetime_y"]

    pv, battery, converter, scale = component_capex(system, cfg, homer)
    if any(np.isnan(v) for v in (pv, battery, converter)):
        nan = float("nan")
        return CostBreakdown(nan, nan, nan, nan, scale, nan, nan, nan, nan,
                             nan, "undefined")

    pv_s, battery_s, converter_s = pv * scale, battery * scale, converter * scale
    total = pv_s + battery_s + converter_s

    # --- battery life -----------------------------------------------------
    modules = system.spec.bess_modules
    if modules <= 0 or annual_battery_throughput_kwh <= 0:
        battery_life = econ.battery_float_life_y
        basis = "float life (no cycling)" if modules > 0 else "no battery"
    else:
        throughput_capacity = (
            modules * homer["battery_lifetime_throughput_kwh_per_module"])
        throughput_life = throughput_capacity / annual_battery_throughput_kwh
        if throughput_life < econ.battery_float_life_y:
            battery_life, basis = throughput_life, "throughput limited"
        else:
            battery_life, basis = econ.battery_float_life_y, "float life limited"

    def replacement_pv(capex: float, component_life: float) -> float:
        if capex <= 0 or component_life <= 0:
            return 0.0
        total_pv = 0.0
        year = component_life
        while year < life - 1e-9:
            total_pv += present_value(capex, rate, year)
            year += component_life
        return total_pv

    pv_rep = replacement_pv(pv_s, econ.pv_lifetime_y)
    battery_rep = replacement_pv(battery_s, battery_life)
    converter_rep = replacement_pv(converter_s, econ.inverter_lifetime_y)

    return CostBreakdown(
        pv_capex_usd=pv_s,
        battery_capex_usd=battery_s,
        converter_capex_usd=converter_s,
        total_capex_usd=total,
        quote_scale=scale,
        pv_replacement_pv_usd=pv_rep,
        battery_replacement_pv_usd=battery_rep,
        converter_replacement_pv_usd=converter_rep,
        replacement_pv_usd=pv_rep + battery_rep + converter_rep,
        battery_life_y=battery_life,
        battery_life_basis=basis,
    )


# ---------------------------------------------------------------------------
# Scoring one case
# ---------------------------------------------------------------------------


def evaluate_economics(kpi: dict, system: ResolvedSystem, cfg: Case1Config,
                       homer: dict,
                       tariff_usd_per_kwh: float | None = None,
                       sellback_usd_per_kwh: float | None = None) -> dict:
    """
    Add economic indicators to a KPI dictionary.

    `tariff_usd_per_kwh` overrides the HOMER purchase tariff for the optional
    tariff sensitivity; the default keeps HOMER's 0.29 USD/kWh so Case 1
    headline economics stay comparable with v18.
    """
    rate = homer["discount_rate"]
    life = homer["project_lifetime_y"]
    crf = capital_recovery_factor(rate, life)

    buy = homer["grid_buy_usd_per_kwh"] if tariff_usd_per_kwh is None \
        else float(tariff_usd_per_kwh)
    sell = homer["grid_sell_usd_per_kwh"] if sellback_usd_per_kwh is None \
        else float(sellback_usd_per_kwh)

    throughput = float(kpi.get("battery_throughput_kwh", 0.0))
    breakdown = cost_breakdown(system, cfg, homer, throughput)

    import_cost = kpi["grid_import_kwh"] * buy
    export_credit = kpi["grid_export_kwh"] * sell
    net_energy_cost = import_cost - export_credit
    wear_cost = throughput * homer["battery_wear_cost_usd_per_kwh"]

    annuity_factor = (1 - (1 + rate) ** -life) / rate if rate else life

    npc = (
        breakdown.total_capex_usd
        + breakdown.replacement_pv_usd
        + net_energy_cost * annuity_factor
    )
    annualized_capex = (
        breakdown.total_capex_usd + breakdown.replacement_pv_usd) * crf

    served = kpi.get("served_load_kwh", kpi["load_kwh"])

    out = {
        **breakdown.as_row(),
        "tariff_usd_per_kwh": buy,
        "sellback_usd_per_kwh": sell,
        "annual_grid_import_cost_usd": import_cost,
        "annual_grid_export_credit_usd": export_credit,
        "annual_net_grid_cost_usd": net_energy_cost,
        "annual_battery_wear_cost_usd": wear_cost,
        "capital_recovery_factor": crf,
        "annualized_capex_usd": annualized_capex,
        "annualized_total_cost_usd": annualized_capex + net_energy_cost,
        "annualized_gross_cost_burden_usd": annualized_capex + import_cost,
        "npc_usd": npc,
        "lcoe_usd_per_kwh": (npc * crf / served) if served > 0 else np.nan,
        # v18-comparable screening metrics
        "capex_plus_grid_import_cost_usd": (
            breakdown.total_capex_usd + import_cost),
        "annualized_total_cost_v18_convention_usd": (
            breakdown.total_capex_usd * crf + net_energy_cost + wear_cost),
    }
    return out


# ---------------------------------------------------------------------------
# Export compensation regimes
# ---------------------------------------------------------------------------

#: The compensation regime decides whether oversizing has any economic limit
#: at all, so it is reported as an explicit axis rather than buried in a
#: single sellback number.
#:
#: NET_METERING_HOMER
#:     The accepted HOMER model: buy 0.290, sell 0.275 USD/kWh. Exported
#:     energy is worth 95% of imported energy, so surplus PV is almost as
#:     valuable as self-consumed PV. Retained as the comparable base case.
#: SELF_CONSUMPTION_ONLY
#:     Exported energy earns nothing. This is the conservative regime, and it
#:     is the one in which storage, export limits and curtailment carry real
#:     economic weight.
#:
#: Which regime a 5 kVA rural residential connection actually gets is a
#: REGULATORY question for EPM and CREG, not a modelling result. Both are
#: reported so the recommendation can be read under either.
COMPENSATION_REGIMES: dict[str, dict] = {
    "NET_METERING_HOMER": {
        "sellback_usd_per_kwh": None,   # None keeps the HOMER value
        "note": "HOMER net metering, sellback 0.275 USD/kWh (95% of purchase)",
    },
    "SELF_CONSUMPTION_ONLY": {
        "sellback_usd_per_kwh": 0.0,
        "note": "no compensation for exported energy",
    },
}


# ---------------------------------------------------------------------------
# Economically useful size (objective 4)
# ---------------------------------------------------------------------------


def marginal_value_table(df: pd.DataFrame,
                         size_column: str,
                         cfg: Case1Config,
                         benefit_column: str = "annual_grid_import_cost_usd",
                         ) -> pd.DataFrame:
    """
    Walk an ordered size sweep and test each increment on its own merits.

    For each step from the previous size:

        incremental annualised cost = d(annualised CAPEX + replacements)
        annual benefit              = reduction in annual gross import cost
                                      + change in export credit
        benefit_cost_ratio          = benefit / incremental cost

    An increment is ECONOMICALLY USEFUL when the ratio reaches the configured
    threshold (default 1.0). The recommended size is the largest size reached
    through an unbroken chain of useful increments: the first increment that
    fails ends the chain, so capacity is not justified by a later step.

    This replaces unlimited oversizing-with-curtailment with an explicit stop
    condition.
    """
    work = df.sort_values(size_column).reset_index(drop=True).copy()

    work["delta_size"] = work[size_column].diff()
    work["delta_annualized_capex_usd"] = work["annualized_capex_usd"].diff()
    work["delta_import_cost_usd"] = work[benefit_column].diff()
    work["delta_export_credit_usd"] = work["annual_grid_export_credit_usd"].diff()

    work["annual_benefit_usd"] = (
        -work["delta_import_cost_usd"] + work["delta_export_credit_usd"])

    with np.errstate(divide="ignore", invalid="ignore"):
        work["benefit_cost_ratio"] = (
            work["annual_benefit_usd"] / work["delta_annualized_capex_usd"])

    work["delta_self_sufficiency_pp"] = work["self_sufficiency_pct"].diff()
    with np.errstate(divide="ignore", invalid="ignore"):
        work["usd_per_added_self_sufficiency_pp"] = (
            work["delta_annualized_capex_usd"] / work["delta_self_sufficiency_pp"])
        work["delta_avoided_import_kwh"] = -work["grid_import_kwh"].diff()
        work["usd_per_avoided_import_kwh"] = (
            work["delta_annualized_capex_usd"] / work["delta_avoided_import_kwh"])

    threshold = cfg.economics.useful_size_benefit_cost_ratio
    work["increment_useful"] = work["benefit_cost_ratio"] >= threshold
    work.loc[work.index[0], "increment_useful"] = True  # the base size itself

    chain = True
    useful_chain = []
    for value in work["increment_useful"]:
        chain = chain and bool(value)
        useful_chain.append(chain)
    work["within_useful_chain"] = useful_chain

    return work


def economically_useful_size(marginal: pd.DataFrame, size_column: str) -> dict:
    """Summarise the marginal table into a single recommendation."""
    useful = marginal[marginal["within_useful_chain"]]
    if useful.empty:
        return {"recommended_size": np.nan, "reason": "no size evaluated"}

    best = useful.iloc[-1]
    beyond = marginal[~marginal["within_useful_chain"]]

    reason = "largest size reached through consecutive cost-effective increments"
    if not beyond.empty:
        first_failed = beyond.iloc[0]
        reason = (
            f"next increment to {size_column}="
            f"{first_failed[size_column]:g} returns "
            f"{first_failed['benefit_cost_ratio']:.2f} USD per USD, below the "
            f"threshold"
        )

    return {
        "recommended_size": float(best[size_column]),
        "self_sufficiency_pct": float(best["self_sufficiency_pct"]),
        "pv_curtailment_pct": float(best.get("pv_curtailment_pct", np.nan)),
        "annualized_total_cost_usd": float(best["annualized_total_cost_usd"]),
        "lcoe_usd_per_kwh": float(best.get("lcoe_usd_per_kwh", np.nan)),
        "npc_usd": float(best.get("npc_usd", np.nan)),
        "reason": reason,
    }
