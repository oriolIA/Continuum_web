"""
Turbine Structures - Port de Turbine.cs (C#)

Estructures de dades per a turbines eòliques
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class Turbine:
    """
    Estructura per a una turbina eòlica
    
    Equivalent C#:
    public class Turbine
    """
    name: str
    x: float              # Coordenada X (UTM Easting)
    y: float              # Coordenada Y (UTM Northing)
    hub_height: float     # Alçada del cub (m)
    rotor_diameter: float # Diàmetre del rotor (m)
    
    # Curva de potència (wind_speed -> power)
    power_curve_ws: list = field(default_factory=list)   # m/s
    power_curve_power: list = field(default_factory=list) # kW
    
    # Paràmetres opcionals
    rated_power: Optional[float] = None      # kW
    cut_in_speed: Optional[float] = None     # m/s
    cut_out_speed: Optional[float] = None   # m/s
    
    def radius(self) -> float:
        """Retorna el radi del rotor"""
        return self.rotor_diameter / 2
    
    def swept_area(self) -> float:
        """Retorna l'àrea de pas del rotor"""
        return np.pi * self.radius()**2
    
    def get_power(self, wind_speed: float) -> float:
        """
        Calcula la potència produïda per una velocitat de vent
        
        Equivalent C#:
        Turbine.GetPower(double WS)
        """
        if wind_speed < (self.cut_in_speed or 0) or wind_speed >= (self.cut_out_speed or 50):
            return 0.0
        
        if self.rated_power and wind_speed >= (self.cut_in_speed or 0) and wind_speed < self.rated_power:
            # Interpolar a la corba de potència
            return np.interp(wind_speed, self.power_curve_ws, self.power_curve_power)
        
        return self.rated_power or 0.0
    
    def thrust_coefficient(self, wind_speed: float) -> float:
        """
        Calcula el coeficient d'empenta (Thrust Coefficient)
        
        Equivalent C#:
        Turbine.ThrustCoef(double WS)
        """
        # Simplificat - es pot millorar amb dades del fabricant
        if wind_speed < (self.cut_in_speed or 0) or wind_speed >= (self.cut_out_speed or 50):
            return 0.0
        
        # Aproximació: Ct ~ 0.8 a velocitats mitges
        if wind_speed < 10:
            return 0.8
        else:
            # Decaïment progressiu
            return max(0.1, 0.8 - 0.05 * (wind_speed - 10))


@dataclass
class WindFarm:
    """
    Conjunt de turbines
    
    Equivalent C#:
    public class WindFarm
    """
    name: str
    turbines: list[Turbine] = field(default_factory=list)
    
    def add_turbine(self, turbine: Turbine):
        """Afegeix una turbina al parc"""
        self.turbines.append(turbine)
    
    def count(self) -> int:
        """Retorna el nombre de turbines"""
        return len(self.turbines)
    
    def total_rated_power(self) -> float:
        """Retorna la potència total instal·lada"""
        return sum(t.rated_power or 0 for t in self.turbines)
    
    def bounding_box(self) -> tuple[float, float, float, float]:
        """
        Retorna el bounding box del parc
        Returns: (min_x, min_y, max_x, max_y)
        """
        xs = [t.x for t in self.turbines]
        ys = [t.y for t in self.turbines]
        return (min(xs), min(ys), max(xs), max(ys))
