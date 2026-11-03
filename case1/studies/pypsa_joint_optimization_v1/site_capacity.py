"""Site A geometric sensitivity, not a surveyed ground-mount PV design.

The site polygon gross area and panel size are previously documented sources.
Usable fraction and installed-area allowance are research scenario inputs.
"""
from dataclasses import dataclass
from math import floor

SITE_A_GROSS_M2 = 1759.26  # user-digitised satellite boundary, not verified land survey
PANEL_FACE_M2 = 1.722 * 1.134
REFERENCE_PANEL_KWP = 0.435


@dataclass(frozen=True)
class SolarAreaCase:
    usable_fraction: float
    installed_m2_per_panel: float = 6.0
    gross_m2: float = SITE_A_GROSS_M2

    def __post_init__(self):
        if not 0 < self.usable_fraction <= 1:
            raise ValueError('usable_fraction must be between 0 and 1')
        if self.installed_m2_per_panel < PANEL_FACE_M2:
            raise ValueError('installed area cannot be smaller than module face area')
        if self.gross_m2 <= 0:
            raise ValueError('gross site area must be positive')

    @property
    def usable_m2(self):
        return self.gross_m2 * self.usable_fraction

    @property
    def geometric_panel_bound(self):
        return floor(self.usable_m2 / self.installed_m2_per_panel + 1e-10)

    def as_record(self, inverter_max_kva=24., dc_ac_ratio=1.5):
        hardware_bound = floor(inverter_max_kva * dc_ac_ratio / REFERENCE_PANEL_KWP + 1e-10)
        model_bound = min(self.geometric_panel_bound, hardware_bound)
        return dict(site='Site A', usable_fraction=self.usable_fraction,
                    gross_area_m2=self.gross_m2, usable_area_m2=self.usable_m2,
                    installed_m2_per_panel=self.installed_m2_per_panel,
                    panel_face_m2=PANEL_FACE_M2,
                    geometric_panel_bound=self.geometric_panel_bound,
                    geometric_pv_kwp=self.geometric_panel_bound * REFERENCE_PANEL_KWP,
                    hardware_panel_bound=hardware_bound,
                    model_panel_bound=model_bound,
                    model_pv_kwp=model_bound * REFERENCE_PANEL_KWP,
                    limitation='ASSUMED SITE GEOMETRY AND EXISTING INVERTER CATALOGUE; NOT MAXIMUM PHYSICAL PV POTENTIAL')


def site_cases(fractions=(.25, .50, .75), installed_m2_per_panel=6.0, gross_m2=SITE_A_GROSS_M2,
               inverter_max_kva=24., dc_ac_ratio=1.5):
    return [SolarAreaCase(f,installed_m2_per_panel,gross_m2).as_record(inverter_max_kva,dc_ac_ratio)
            for f in fractions]
