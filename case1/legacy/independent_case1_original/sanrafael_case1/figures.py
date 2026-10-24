"""
Figures for Case 1.

Charts are secondary to the CSV tables: every figure plots a table that is
already written to `results_case1/`, so nothing here is a source of numbers.

Colour handling follows one rule set:

  * categorical hues are assigned in a FIXED order and never cycled, so a
    controller keeps its colour across every figure;
  * magnitude uses a single hue, light to dark, never a rainbow;
  * feasible / infeasible uses the reserved status pair and always carries a
    label or marker as well, never colour alone;
  * every series is directly labelled, because three of the categorical hues
    sit below 3:1 contrast on the chart surface.

The palette is a validated categorical set (adjacent-pair CVD and
normal-vision separation checked); the perfect-foresight LP bound is drawn as
a neutral reference line rather than a sixth hue, because it is an upper bound
on performance, not a control option the community could choose.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# --- palette ---------------------------------------------------------------

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf",
              "#184f95", "#0d366b"]
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"

CONTROL_ORDER = ["CONVENTIONAL", "EXPORT_LIMITED", "FIXED_RESERVE",
                 "ADAPTIVE_RESERVE", "ADAPTIVE_PLUS_LM"]
CONTROL_COLOUR = dict(zip(CONTROL_ORDER, SERIES))
CONTROL_SHORT = {
    "CONVENTIONAL": "Conventional",
    "EXPORT_LIMITED": "Export-limited",
    "FIXED_RESERVE": "Fixed reserve",
    "ADAPTIVE_RESERVE": "Adaptive reserve",
    "ADAPTIVE_PLUS_LM": "Adaptive + load mgmt",
}


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_SECONDARY,
        "axes.titlecolor": INK_PRIMARY,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.axisbelow": True,
        "axes.labelsize": 9.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
        "font.size": 10,
    })
    return plt


def _finish(fig, path: Path, subtitle: str | None = None):
    if subtitle:
        fig.text(0.01, -0.01, subtitle, fontsize=8, color=INK_MUTED,
                 ha="left", va="top", wrap=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return str(path)


def _sequential_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("seq_blue", SEQUENTIAL)


# ---------------------------------------------------------------------------
# 1. Export control counterfactual - the headline figure
# ---------------------------------------------------------------------------


def fig_export_control(table: pd.DataFrame, cfg, path: Path) -> str:
    plt = _style()
    limit_pct = 100.0 * cfg.transformer.loading_limit_pu

    controlled = table[table["export_control"]
                       == "CONTROLLED_TO_TRANSFORMER_ENVELOPE"].sort_values("pv_kwp")
    uncontrolled = table[table["export_control"]
                         == "UNCONTROLLED_INVERTER_LIMITED"].sort_values("pv_kwp")

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

    # Uncontrolled first so the controlled line stays visible where the two
    # coincide, which they do until the export cap starts to bind.
    for frame, colour, label, width in (
        (uncontrolled, SERIES[1], "Export limited only by inverter", 2.0),
        (controlled, SERIES[0], "Export held to transformer envelope", 2.6),
    ):
        ax.plot(frame["pv_kwp"], frame["max_transformer_loading_pct"],
                color=colour, label=label, linewidth=width, zorder=3)
        for _, row in frame.iterrows():
            feasible = bool(row["electrically_feasible"])
            ax.plot(row["pv_kwp"], row["max_transformer_loading_pct"],
                    marker="o" if feasible else "X",
                    markersize=8 if feasible else 12,
                    color=colour, markeredgecolor=SURFACE, markeredgewidth=2,
                    zorder=5, linestyle="none")

    ax.axhline(limit_pct, color=INK_MUTED, linestyle="--", linewidth=1.2,
               zorder=1)
    ax.axhline(100.0, color=STATUS_CRITICAL, linestyle=":", linewidth=1.2,
               zorder=1)

    x_left = float(controlled["pv_kwp"].min())
    ax.text(x_left, limit_pct - 4.5, f"{limit_pct:.0f}% permissible loading",
            fontsize=8.5, color=INK_MUTED, va="top")
    ax.text(x_left, 102, "100% nameplate", fontsize=8.5,
            color=STATUS_CRITICAL, va="bottom")

    if not uncontrolled.empty:
        worst = uncontrolled.iloc[-1]
        ax.annotate(f"{worst['max_transformer_loading_pct']:.0f}%",
                    (worst["pv_kwp"], worst["max_transformer_loading_pct"]),
                    xytext=(-8, -4), textcoords="offset points",
                    fontsize=9.5, color=SERIES[1], ha="right", va="top")
    if not controlled.empty:
        best = controlled.iloc[-1]
        ax.annotate(f"{best['max_transformer_loading_pct']:.0f}%",
                    (best["pv_kwp"], best["max_transformer_loading_pct"]),
                    xytext=(0, -14), textcoords="offset points",
                    fontsize=9.5, color=SERIES[0], ha="center", va="top")

    ax.set_xlabel("Centralized PV array [kWp DC]")
    ax.set_ylabel("Peak transformer loading [%]")
    ax.set_title("Export control sets the feasible PV size")
    ax.set_ylim(top=float(uncontrolled["max_transformer_loading_pct"].max()) * 1.10
                if not uncontrolled.empty else None)
    ax.grid(True, axis="y")
    handles, labels_ = ax.get_legend_handles_labels()
    ax.legend(handles, labels_, loc="upper left")
    ax.plot([], [], marker="X", linestyle="none", color=STATUS_CRITICAL,
            markersize=9, label="breaches a screening limit")
    ax.legend(loc="upper left")

    ax2.plot(controlled["pv_kwp"], controlled["pv_curtailment_pct"],
             marker="o", color=SERIES[0], label="Curtailment under export control")
    for _, row in controlled.iterrows():
        ax2.annotate(f"{row['pv_curtailment_pct']:.2f}%",
                     (row["pv_kwp"], row["pv_curtailment_pct"]),
                     xytext=(0, 8), textcoords="offset points",
                     fontsize=8.5, color=SERIES[0], ha="center")
    ax2.plot(controlled["pv_kwp"], controlled["energy_self_sufficiency_pct"],
             marker="s", color=SERIES[2], label="Operational self-sufficiency")
    for _, row in controlled.iterrows():
        ax2.annotate(f"{row['energy_self_sufficiency_pct']:.1f}%",
                     (row["pv_kwp"], row["energy_self_sufficiency_pct"]),
                     xytext=(0, -16), textcoords="offset points",
                     fontsize=8.5, color=SERIES[2], ha="center")

    ax2.set_xlabel("Centralized PV array [kWp DC]")
    ax2.set_ylabel("Share of available PV / annual demand [%]")
    ax2.set_title("What export control costs")
    ax2.set_ylim(-4, 108)
    ax2.grid(True, axis="y")
    ax2.legend(loc="center right")

    fig.tight_layout()
    return _finish(fig, path,
                   "Transformer 94022, 5 kVA single-phase. Critical hours of the "
                   "causal conventional dispatch, solved in pandapower. "
                   "X marks a configuration that breaches a screening limit.")


# ---------------------------------------------------------------------------
# 2. Oversizing grid
# ---------------------------------------------------------------------------


def fig_oversizing(table: pd.DataFrame, path: Path) -> str:
    plt = _style()
    work = table[table["hardware_feasible"] == True].copy()  # noqa: E712
    work = work.dropna(subset=["self_sufficiency_pct"])

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

    modules = sorted(work["bess_modules"].unique())[:len(SERIES)]
    for colour, module_count in zip(SERIES, modules):
        frame = (work[work["bess_modules"] == module_count]
                 .groupby("pv_kwp", as_index=False)
                 .agg({"self_sufficiency_pct": "max",
                       "pv_curtailment_pct": "max"})
                 .sort_values("pv_kwp"))
        label = f"{int(module_count)} battery modules"
        ax.plot(frame["pv_kwp"], frame["self_sufficiency_pct"],
                marker="o", color=colour, label=label)
        last = frame.iloc[-1]
        ax.annotate(f"{int(module_count)}B", (last["pv_kwp"],
                                              last["self_sufficiency_pct"]),
                    xytext=(6, 0), textcoords="offset points",
                    fontsize=9, color=colour, va="center")
        ax2.plot(frame["pv_kwp"], frame["pv_curtailment_pct"],
                 marker="o", color=colour, label=label)

    ax.set_xlabel("Centralized PV array [kWp DC]")
    ax.set_ylabel("Operational self-sufficiency [%]")
    ax.set_title("Self-sufficiency against PV and storage size")
    ax.grid(True, axis="y")
    ax.legend(loc="lower right")

    ax2.set_xlabel("Centralized PV array [kWp DC]")
    ax2.set_ylabel("PV curtailment [% of available DC]")
    ax2.set_title("Curtailment against PV and storage size")
    ax2.grid(True, axis="y")

    fig.tight_layout()
    return _finish(fig, path,
                   "Causal conventional controller, 4 households, export held "
                   "inside the derated transformer envelope. Each point uses the "
                   "best datasheet-feasible inverter for that array.")


# ---------------------------------------------------------------------------
# 3. Controller comparison
# ---------------------------------------------------------------------------


def fig_control_comparison(comparison: pd.DataFrame,
                           family: pd.DataFrame,
                           system: str, path: Path) -> str:
    plt = _style()

    energy = comparison[comparison["case"] == system].set_index("control")
    outage = family[(family["system"] == system)
                    & (family["family"] == "GRID_OUTAGE")].set_index("control")

    controls = [c for c in CONTROL_ORDER if c in energy.index]
    x = np.arange(len(controls))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6))

    values = [energy.at[c, "self_sufficiency_pct"] for c in controls]
    bars = ax.bar(x, values, width=0.62,
                  color=[CONTROL_COLOUR[c] for c in controls])
    for bar, value in zip(bars, values):
        ax.annotate(f"{value:.1f}%", (bar.get_x() + bar.get_width() / 2, value),
                    xytext=(0, 5), textcoords="offset points",
                    ha="center", fontsize=9, color=INK_PRIMARY)

    top = max(values) * 1.30
    if "LP_PERFECT_FORESIGHT" in energy.index:
        bound = float(energy.at["LP_PERFECT_FORESIGHT", "self_sufficiency_pct"])
        ax.axhline(bound, color=INK_MUTED, linestyle="--", linewidth=1.3,
                   zorder=1)
        ax.text(-0.45, top * 0.97,
                f"perfect-foresight bound {bound:.1f}%  (not a control option)",
                fontsize=8.5, color=INK_MUTED, ha="left", va="top")

    ax.set_xticks(x)
    ax.set_xticklabels([CONTROL_SHORT[c] for c in controls], rotation=18,
                       ha="right")
    ax.set_ylabel("Operational self-sufficiency [%]")
    ax.set_ylim(0, top)
    ax.set_title("Energy independence by control strategy")
    ax.grid(True, axis="y")

    def _column(name):
        return [float(outage.at[c, name]) if (c in outage.index
                                              and name in outage.columns)
                else np.nan for c in controls]

    firm = _column("survived_firm_load_pct")
    all_demand = _column("served_all_demand_pct")

    width = 0.36
    bars_firm = ax2.bar(x - width / 2, firm, width=width,
                        color=[CONTROL_COLOUR[c] for c in controls])
    bars_all = ax2.bar(x + width / 2, all_demand, width=width,
                       color=[CONTROL_COLOUR[c] for c in controls],
                       alpha=0.45, hatch="//", edgecolor=SURFACE, linewidth=1.5)

    for group_bars, series in ((bars_firm, firm), (bars_all, all_demand)):
        for bar, value in zip(group_bars, series):
            if np.isfinite(value):
                ax2.annotate(f"{value:.0f}",
                             (bar.get_x() + bar.get_width() / 2, value),
                             xytext=(0, 4), textcoords="offset points",
                             ha="center", fontsize=8.5, color=INK_PRIMARY)

    ax2.set_xticks(x)
    ax2.set_xticklabels([CONTROL_SHORT[c] for c in controls], rotation=18,
                        ha="right")
    ax2.set_ylabel("Sampled outages served [%]")
    ax2.set_ylim(0, 118)
    ax2.set_title("Outage survival: firm load vs all demand")
    ax2.grid(True, axis="y")

    import matplotlib.patches as mpatches
    ax2.legend(handles=[
        mpatches.Patch(facecolor=INK_MUTED, label="firm load served"),
        mpatches.Patch(facecolor=INK_MUTED, alpha=0.45, hatch="//",
                       edgecolor=SURFACE, label="all demand served in window"),
    ], loc="upper left", ncol=1)

    fig.tight_layout()
    return _finish(fig, path,
                   f"System {system}. Left: annual causal dispatch; no "
                   "controller reaches the perfect-foresight bound, which is "
                   "not achievable without forecasting. Right: solid bars count "
                   "windows with no firm demand unserved; hatched bars also "
                   "require nothing left deferred, so a controller that wins on "
                   "solid and loses on hatched is shifting demand rather than "
                   "supplying it. Islanding capability at this site is "
                   "unconfirmed.")


# ---------------------------------------------------------------------------
# 4. Vulnerability heatmap
# ---------------------------------------------------------------------------


def fig_vulnerability(family: pd.DataFrame, system: str, path: Path) -> str:
    plt = _style()

    work = family[family["system"] == system]
    families = [f for f in ("LOW_SOLAR", "HIGH_DEMAND", "HIGH_PV_EXPORT_LIMITED",
                            "GRID_OUTAGE", "COMBINED")
                if f in set(work["family"])]
    controls = [c for c in CONTROL_ORDER if c in set(work["control"])]

    matrix = np.full((len(families), len(controls)), np.nan)
    for i, fam in enumerate(families):
        for j, control in enumerate(controls):
            cell = work[(work["family"] == fam) & (work["control"] == control)]
            if not cell.empty:
                column = ("survived_firm_load_pct"
                          if "survived_firm_load_pct" in cell.columns
                          else "survived_full_window_pct")
                matrix[i, j] = float(cell.iloc[0][column])

    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    image = ax.imshow(matrix, cmap=_sequential_cmap(), vmin=0, vmax=100,
                      aspect="auto")

    ax.set_xticks(np.arange(len(controls)))
    ax.set_xticklabels([CONTROL_SHORT[c] for c in controls], rotation=18,
                       ha="right")
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels([f.replace("_", " ").title() for f in families])
    ax.set_xticks(np.arange(len(controls) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(families) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)

    for i in range(len(families)):
        for j in range(len(controls)):
            value = matrix[i, j]
            if not np.isfinite(value):
                continue
            ax.text(j, i, f"{value:.0f}", ha="center", va="center", fontsize=9,
                    color="#ffffff" if value > 55 else INK_PRIMARY)

    ax.set_title("Stress windows with firm load fully served [%]")
    bar = fig.colorbar(image, ax=ax, pad=0.02)
    bar.set_label("Scenarios served in full [%]", color=INK_SECONDARY,
                  fontsize=9)
    bar.outline.set_edgecolor(AXIS)

    fig.tight_layout()
    return _finish(fig, path,
                   f"System {system}. Each cell is the share of that stressor "
                   "family's scenarios in which no firm demand went unserved; "
                   "load deferred by the load-management controller is "
                   "credited here and counted against it in the control "
                   "comparison. Numbers are printed because colour alone must "
                   "not carry the value.")


# ---------------------------------------------------------------------------
# 5. Marginal value of capacity
# ---------------------------------------------------------------------------


def fig_marginal_value(pv_marginal: pd.DataFrame, cfg, path: Path) -> str:
    plt = _style()
    threshold = cfg.economics.useful_size_benefit_cost_ratio

    fig, ax = plt.subplots(figsize=(7.6, 4.4))

    regimes = ["NET_METERING_HOMER", "SELF_CONSUMPTION_ONLY"]
    labels = {
        "NET_METERING_HOMER": "Net metering, sellback 0.275 USD/kWh",
        "SELF_CONSUMPTION_ONLY": "Self-consumption only, no export credit",
    }

    for colour, regime in zip(SERIES, regimes):
        frame = (pv_marginal[pv_marginal["compensation_regime"] == regime]
                 .dropna(subset=["benefit_cost_ratio"])
                 .sort_values("panel_count"))
        if frame.empty:
            continue
        ax.plot(frame["panel_count"], frame["benefit_cost_ratio"],
                marker="o", color=colour, label=labels[regime])
        for _, row in frame.iterrows():
            ax.annotate(f"{row['benefit_cost_ratio']:.2f}",
                        (row["panel_count"], row["benefit_cost_ratio"]),
                        xytext=(0, 8), textcoords="offset points",
                        fontsize=8.5, color=colour, ha="center")

    ax.axhline(threshold, color=INK_MUTED, linestyle="--", linewidth=1.3)
    ax.text(ax.get_xlim()[1], threshold * 1.08, "breaks even", fontsize=8.5,
            color=INK_MUTED, ha="right")

    ax.set_yscale("log")
    ax.set_xlabel("PV panels (435 Wp each)")
    ax.set_ylabel("Annual benefit per USD of annualized cost")
    ax.set_title("Where adding PV stops paying for itself")
    ax.grid(True, axis="y")
    ax.legend(loc="upper right")

    fig.tight_layout()
    return _finish(fig, path,
                   "Each point is the increment FROM the previous array size. "
                   "Whether a 5 kVA rural connection is compensated for exports "
                   "is a regulatory question, so both regimes are shown.")


# ---------------------------------------------------------------------------
# 6. Transformer envelope
# ---------------------------------------------------------------------------


def fig_transformer_envelope(table: pd.DataFrame, cfg, path: Path) -> str:
    plt = _style()

    fig, ax = plt.subplots(figsize=(8.0, 4.4))

    loading_levels = sorted(table["loading_limit_pu"].unique())
    pf_reference = cfg.transformer.pf_import
    work = table[np.isclose(table["pf_import"], pf_reference)]

    for colour, k_load in zip(SERIES, loading_levels):
        frame = work[np.isclose(work["loading_limit_pu"], k_load)
                     ].sort_values("houses")
        if frame.empty:
            continue
        limit = float(frame["import_limit_kw"].iloc[0])
        ax.axhline(limit, color=colour, linestyle="--", linewidth=1.4)
        ax.text(frame["houses"].min() - 0.05, limit + 0.04,
                f"{k_load:.0%} loading limit = {limit:.2f} kW",
                fontsize=8.5, color=colour, va="bottom")

    peaks = work.groupby("houses", as_index=False)["group_peak_load_kw"].max()
    ax.plot(peaks["houses"], peaks["group_peak_load_kw"], marker="o",
            color=INK_PRIMARY, linewidth=2.2, label="Group peak demand")
    for _, row in peaks.iterrows():
        ax.annotate(f"{row['group_peak_load_kw']:.2f}",
                    (row["houses"], row["group_peak_load_kw"]),
                    xytext=(0, -16), textcoords="offset points",
                    fontsize=8.5, color=INK_PRIMARY, ha="center")

    infeasible = work[~work["energy_feasible"].astype(bool)]
    if not infeasible.empty:
        ax.scatter(infeasible["houses"], infeasible["group_peak_load_kw"],
                   marker="X", s=130, color=STATUS_CRITICAL, zorder=6,
                   label="Demand cannot be met in all hours")

    ax.set_xlabel("Households behind transformer 94022")
    ax.set_ylabel("Active power [kW]")
    ax.set_title(
        f"Active-power import envelope of a 5 kVA transformer at PF "
        f"{pf_reference:.2f}")
    ax.grid(True, axis="y")
    ax.legend(loc="upper left")

    fig.tight_layout()
    return _finish(fig, path,
                   "The 5 kVA nameplate is apparent power. The usable active "
                   "import limit is 5 kVA x permissible loading x power factor, "
                   "which is what the group's peak demand must fit inside.")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def make_all_figures(results, cfg, study=None) -> list[str]:
    """Draw every figure whose source table is present. Never raises."""
    tables = results.tables if hasattr(results, "tables") else results
    out_dir = Path(cfg.paths.figures_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    plan = [
        ("network_export_control_counterfactual",
         lambda t: fig_export_control(t, cfg,
                                      out_dir / "01_export_control.png")),
        ("oversizing_grid",
         lambda t: fig_oversizing(t, out_dir / "02_oversizing_grid.png")),
        ("transformer_sensitivity",
         lambda t: fig_transformer_envelope(
             t, cfg, out_dir / "03_transformer_envelope.png")),
        ("pv_marginal_value",
         lambda t: fig_marginal_value(t, cfg,
                                      out_dir / "05_marginal_value.png")),
    ]

    for name, draw in plan:
        table = tables.get(name)
        if table is None or table.empty:
            continue
        try:
            paths.append(draw(table))
        except Exception as exc:
            print(f"  figure {name} skipped: {exc}")

    comparison = tables.get("control_comparison")
    family = tables.get("vulnerability_by_family")
    if comparison is not None and family is not None and not family.empty:
        systems = [s for s in family["system"].unique()]
        preferred = [s for s in systems if s.startswith("REF")] or systems[:1]
        for index, system in enumerate(preferred + [s for s in systems
                                                    if s not in preferred][:1]):
            try:
                paths.append(fig_control_comparison(
                    comparison, family, system,
                    out_dir / f"04_control_comparison_{system}.png"))
                paths.append(fig_vulnerability(
                    family, system,
                    out_dir / f"06_vulnerability_{system}.png"))
            except Exception as exc:
                print(f"  figures for {system} skipped: {exc}")

    return paths
