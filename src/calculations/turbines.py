"""
Turbine Library - Dades de turbines eòliques

Models de turbines reals amb corbes de potència:
- Vestas
- Siemens Gamesa
- GE
- Nordex
- Enercon
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np
import pandas as pd


@dataclass
class PowerCurve:
    """Corba de potència d'una turbina"""
    wind_speeds: List[float]  # m/s
    powers: List[float]       # kW
    cut_in: float             # m/s
    cut_out: float            # m/s
    rated: float              # kW
    rated_wind_speed: float   # m/s
    
    def get_power(self, wind_speed: float) -> float:
        """Retorna potència per a una velocitat donada"""
        if wind_speed < self.cut_in or wind_speed > self.cut_out:
            return 0.0
        elif wind_speed >= self.rated_wind_speed:
            return self.rated
        else:
            # Interpolació lineal
            return np.interp(wind_speed, self.wind_speeds, self.powers)


@dataclass
class TurbineModel:
    """Model de turbina eòlica complet"""
    name: str
    manufacturer: str
    rated_power_kw: float
    rotor_diameter_m: float
    hub_height_m: float
    cut_in_speed_ms: float
    cut_out_speed_ms: float
    rated_wind_speed_ms: float
    power_curve: PowerCurve
    thrust_coefficient: float = 0.8
    lifetime_years: int = 25
    IEC_class: str = "IIA"  # IEC 61400 standard
    
    def annual_energy_production(
        self,
        wind_speed_ms: float,
        wind_rose: Dict[str, float],
        capacity_factor_override: float = None
    ) -> dict:
        """
        Calcula AEP (Annual Energy Production)
        
        Args:
            wind_speed_ms: Velocitat mitjana del vent
            wind_rose: Distribució de sectors (%)
            capacity_factor_override: Override del capacity factor
        
        Returns:
            Dict amb AEP i estadístiques
        """
        if capacity_factor_override:
            cf = capacity_factor_override
        else:
            # Estimar CF basat en velocitat
            cf = min(0.5, wind_speed_ms / 25.0)  # Aproximació
        
        # Hores equivalents a l'any
        hours_per_year = 8760
        equivalent_hours = hours_per_year * cf
        
        # AEP brut (MWh/any)
        gross_aep_mwh = self.rated_power_kw * equivalent_hours / 1000
        
        # Pèrdues estimades
        availability = 0.97  # Disponibilitat
        electrical = 0.03   # Pèrdues elèctriques
        wake_losses = 0.10   # Pèrdues de wake (assumit)
        other = 0.05         # Altres pèrdues
        
        total_losses = 1 - (availability * (1 - electrical) * (1 - wake_losses) * (1 - other))
        net_aep_mwh = gross_aep_mwh * (1 - total_losses)
        
        # Capacity factor net
        net_cf = net_aep_mwh / (self.rated_power_kw * hours_per_year / 1000)
        
        return {
            'gross_aep_mwh': round(gross_aep_mwh, 0),
            'net_aep_mwh': round(net_aep_mwh, 0),
            'capacity_factor_gross': round(cf * 100, 1),
            'capacity_factor_net': round(net_cf * 100, 1),
            'equivalent_hours': round(equivalent_hours, 0),
            'losses_breakdown': {
                'availability': f"{(1-availability)*100:.1f}%",
                'electrical': f"{electrical*100:.1f}%",
                'wake': f"{wake_losses*100:.1f}%",
                'other': f"{other*100:.1f}%",
                'total': f"{total_losses*100:.1f}%"
            }
        }
    
    def power_at_wind_speeds(self, speeds: List[float]) -> List[float]:
        """Retorna potències per a múltiples velocitats"""
        return [self.power_curve.get_power(s) for s in speeds]


# Vestas Models
VESTAS_V112 = TurbineModel(
    name="Vestas V112-3.0MW",
    manufacturer="Vestas",
    rated_power_kw=3300,
    rotor_diameter_m=112,
    hub_height_m=84,
    cut_in_speed_ms=3.5,
    cut_out_speed_ms=25.0,
    rated_wind_speed_ms=12.5,
    power_curve=PowerCurve(
        wind_speeds=[0, 3.5, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12.5, 13, 14, 15, 25],
        powers=[0, 0, 180, 480, 880, 1400, 2050, 2600, 2950, 3200, 3300, 3300, 3300, 3300, 3300, 0],
        cut_in=3.5,
        cut_out=25.0,
        rated=3300,
        rated_wind_speed=12.5
    ),
    IEC_class="IEC IIA"
)

VESTAS_V136 = TurbineModel(
    name="Vestas V136-4.2MW",
    manufacturer="Vestas",
    rated_power_kw=4200,
    rotor_diameter_m=136,
    hub_height_m=105,
    cut_in_speed_ms=3.0,
    cut_out_speed_ms=25.0,
    rated_wind_speed_ms=11.5,
    power_curve=PowerCurve(
        wind_speeds=[0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 11.5, 12, 13, 14, 15, 25],
        powers=[0, 0, 250, 700, 1250, 2000, 2850, 3650, 4150, 4200, 4200, 4200, 4200, 4200, 4200, 0],
        cut_in=3.0,
        cut_out=25.0,
        rated=4200,
        rated_wind_speed=11.5
    ),
    IEC_class="IEC IIIA"
)

# Siemens Gamesa Models
SIEMENS_G114 = TurbineModel(
    name="Siemens Gamesa SG 4.0-114",
    manufacturer="Siemens Gamesa",
    rated_power_kw=4000,
    rotor_diameter_m=114,
    hub_height_m=93,
    cut_in_speed_ms=3.0,
    cut_out_speed_ms=25.0,
    rated_wind_speed_ms=12.5,
    power_curve=PowerCurve(
        wind_speeds=[0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12.5, 13, 14, 15, 25],
        powers=[0, 0, 220, 620, 1150, 1850, 2700, 3500, 3950, 4000, 4000, 4000, 4000, 4000, 4000, 0],
        cut_in=3.0,
        cut_out=25.0,
        rated=4000,
        rated_wind_speed=12.5
    ),
    IEC_class="IEC IIA"
)

SIEMENS_G145 = TurbineModel(
    name="Siemens Gamesa SG 5.0-145",
    manufacturer="Siemens Gamesa",
    rated_power_kw=5000,
    rotor_diameter_m=145,
    hub_height_m=120,
    cut_in_speed_ms=3.0,
    cut_out_speed_ms=25.0,
    rated_wind_speed_ms=11.5,
    power_curve=PowerCurve(
        wind_speeds=[0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 11.5, 12, 13, 14, 15, 25],
        powers=[0, 0, 300, 850, 1500, 2400, 3400, 4400, 5000, 5000, 5000, 5000, 5000, 5000, 5000, 0],
        cut_in=3.0,
        cut_out=25.0,
        rated=5000,
        rated_wind_speed=11.5
    ),
    IEC_class="IEC IIIA"
)

# GE Models
GE_158 = TurbineModel(
    name="GE 6.0-158",
    manufacturer="GE Renewable Energy",
    rated_power_kw=6000,
    rotor_diameter_m=158,
    hub_height_m=135,
    cut_in_speed_ms=3.5,
    cut_out_speed_ms=25.0,
    rated_wind_speed_ms=12.5,
    power_curve=PowerCurve(
        wind_speeds=[0, 3.5, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12.5, 13, 14, 15, 25],
        powers=[0, 0, 350, 1000, 1800, 2900, 4200, 5400, 6000, 6000, 6000, 6000, 6000, 6000, 6000, 0],
        cut_in=3.5,
        cut_out=25.0,
        rated=6000,
        rated_wind_speed=12.5
    ),
    IEC_class="IEC IIA"
)

# Nordex Models
NORDEX_Gamma = TurbineModel(
    name="Nordex Gamma 5.8-155",
    manufacturer="Nordex",
    rated_power_kw=5800,
    rotor_diameter_m=155,
    hub_height_m=135,
    cut_in_speed_ms=2.5,
    cut_out_speed_ms=25.0,
    rated_wind_speed_ms=11.5,
    power_curve=PowerCurve(
        wind_speeds=[0, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 11.5, 12, 13, 14, 25],
        powers=[0, 0, 150, 550, 1200, 2000, 3100, 4300, 5400, 5800, 5800, 5800, 5800, 5800, 5800, 0],
        cut_in=2.5,
        cut_out=25.0,
        rated=5800,
        rated_wind_speed=11.5
    ),
    IEC_class="IEC S"
)

# Enercon Models
ENERCON_E138 = TurbineModel(
    name="Enercon E-138 EP3",
    manufacturer="Enercon",
    rated_power_kw=4200,
    rotor_diameter_m=138,
    hub_height_m=131,
    cut_in_speed_ms=2.5,
    cut_out_speed_ms=28.0,  # Enercon pot anar més alt
    rated_wind_speed_ms=11.5,
    power_curve=PowerCurve(
        wind_speeds=[0, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 11.5, 12, 13, 14, 28],
        powers=[0, 0, 180, 600, 1150, 1900, 2900, 3800, 4200, 4200, 4200, 4200, 4200, 4200, 4200, 0],
        cut_in=2.5,
        cut_out=28.0,
        rated=4200,
        rated_wind_speed=11.5
    ),
    IEC_class="IEC IIIA"
)


# Catàleg complet
TURBINE_CATALOG: Dict[str, TurbineModel] = {
    "vestas_v112": VESTAS_V112,
    "vestas_v136": VESTAS_V136,
    "siemens_g114": SIEMENS_G114,
    "siemens_g145": SIEMENS_G145,
    "ge_158": GE_158,
    "nordex_gamma": NORDEX_Gamma,
    "enercon_e138": ENERCON_E138,
    # Alias
    "v112": VESTAS_V112,
    "v136": VESTAS_V136,
    "sg114": SIEMENS_G114,
    "sg145": SIEMENS_G145,
    "ge6mw": GE_158,
}


def get_turbine(name: str) -> Optional[TurbineModel]:
    """Retorna un model de turbina pel nom"""
    key = name.lower().replace("-", "_").replace(" ", "_")
    return TURBINE_CATALOG.get(key)


def list_turbines() -> List[Dict]:
    """Llista tots els models disponibles"""
    return [
        {
            "id": key,
            "name": t.name,
            "manufacturer": t.manufacturer,
            "rated_power_mw": t.rated_power_kw / 1000,
            "rotor_diameter_m": t.rotor_diameter_m,
            "hub_height_m": t.hub_height_m,
            "iec_class": t.IEC_class
        }
        for key, t in TURBINE_CATALOG.items()
    ]


def compare_turbines(turbine_names: List[str], wind_speed_ms: float) -> pd.DataFrame:
    """
    Compara múltiples turbines a una velocitat donada
    
    Args:
        turbine_names: Llista de noms de turbines
        wind_speed_ms: Velocitat de vent
    
    Returns:
        DataFrame comparatiu
    """
    data = []
    for name in turbine_names:
        t = get_turbine(name)
        if t:
            power = t.power_curve.get_power(wind_speed_ms)
            cf = power / t.rated_power_kw * 100 if t.rated_power_kw > 0 else 0
            data.append({
                "turbine": t.name,
                "manufacturer": t.manufacturer,
                "rated_power_mw": t.rated_power_kw / 1000,
                "power_at_ws_kw": power,
                "capacity_factor_percent": round(cf, 1),
                "rotor_diameter_m": t.rotor_diameter_m
            })
    
    return pd.DataFrame(data)


def estimate_park_energy(
    turbines: List[TurbineModel],
    wind_speed_ms: float,
    wind_rose: Dict[str, float],
    layout_spacing_x: float = 5,   # diàmetres
    layout_spacing_y: float = 7    # diàmetres
) -> dict:
    """
    Estimació d'energia per un parc eòlic
    
    Args:
        turbines: Llista de turbines
        wind_speed_ms: Velocitat mitjana
        wind_rose: Distribució direccional
        layout_spacing: Espaiat entre turbines (en diàmetres)
    
    Returns:
        Dict amb producció estimada
    """
    if not turbines:
        return {"error": "No turbines provided"}
    
    # Assumim turbines homogenis
    t = turbines[0]
    spacing_x = t.rotor_diameter_m * layout_spacing_x
    spacing_y = t.rotor_diameter_m * layout_spacing_y
    
    # Calcular pèrdues de wake (simplificat)
    wake_loss = 0.10  # 10% per defecte
    
    # AEP per turbina
    aep_single = t.annual_energy_production(wind_speed_ms, wind_rose)
    
    # AEP del parc
    n = len(turbines)
    park_aep = {
        'n_turbines': n,
        'total_rated_mw': n * t.rated_power_kw / 1000,
        'gross_aep_gwh': aep_single['gross_aep_mwh'] * n / 1000,
        'net_aep_gwh': aep_single['net_aep_mwh'] * n / 1000,
        'wake_losses_percent': wake_loss * 100,
        'capacity_factor_net': aep_single['capacity_factor_net'],
        'equivalent_hours': aep_single['equivalent_hours'],
        'turbine_model': t.name
    }
    
    return park_aep
