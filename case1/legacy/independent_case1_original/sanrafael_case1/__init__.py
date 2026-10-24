"""
SEEDExchange El Arenal (San Rafael, Antioquia) - Case Study 1.

Transformer-Constrained PV-BESS Oversizing, Vulnerability and Adaptive
Resilience Assessment.

Research question
-----------------
To what extent can centralized PV and battery capacities be increased behind
the existing 5 kVA EPM transformer 94022 through controlled import/export,
battery charging and PV curtailment, while maintaining electrical
feasibility, improving energy independence, and reducing vulnerability to
disturbances?

Provenance
----------
This package extends, and does not replace, two verified baselines:

    SanRafael_PyPSA_Scenarios_v18_uncertainty.ipynb
    SanRafael_pandapower_Grid_Check_v5_uncertainty.ipynb

The HOMER reference, the stochastic household demand model and the NASA POWER
GHI + Erbs PV model are ported with their physics unchanged, and
`validation.py` asserts that this package reproduces the v18 and v5 published
numbers before any Case 1 extension is applied.

Scope notes
-----------
* The community system is CENTRALIZED and SHARED. Individual rooftop
  PV/BESS comparison is not a Case 1 objective.
* Case 1 uses NO solar forecasting. The LP is a perfect-foresight upper
  bound and is labelled as such everywhere; the control comparison uses
  causal, no-forecast controllers in `rule_dispatch`.
* Hardware is PROPOSED, not confirmed installed. Real islanding capability
  and inverter/site compatibility are unconfirmed, so outage results are
  qualified accordingly.
* Household demand is SYNTHETIC, built with the HOMER variability settings.
  It still requires validation against measured data.
"""

from .config import (Case1Config, DemandConfig, DispatchConfig,
                     EconomicsConfig, HardwareConfig, INVERTER_FAMILY,
                     NetworkConfig, Paths, ResourceConfig, SiteConfig,
                     StressConfig, TransformerConstraint, provenance_table)
from .homer import parse_homer_xml
from .lp_model import ResolvedSystem, SystemSpec, resolve_system
from .study import Case1Study

__all__ = [
    "Case1Config", "Case1Study", "SystemSpec", "ResolvedSystem",
    "resolve_system", "parse_homer_xml", "provenance_table",
    "INVERTER_FAMILY", "Paths", "SiteConfig", "TransformerConstraint",
    "HardwareConfig", "DemandConfig", "ResourceConfig", "DispatchConfig",
    "StressConfig", "EconomicsConfig", "NetworkConfig",
]

__version__ = "1.0.0-case1"
