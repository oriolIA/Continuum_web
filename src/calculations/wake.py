"""
Wake Loss Modeling - Port de WakeCollection.cs i Wake_Model.cs (C#)

Modelat de pèrdues per wake effect entre turbines
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class WakePoint:
    """Un punt de dins el mapa de wake"""
    x: float
    y: float
    z: float = 0.0
    velocity_deficit: float = 0.0
    u: float = 0.0  # Velocitat resultant


@dataclass
class TurbineWake:
    """Wake generat per una turbina"""
    turbine_id: str
    x: float
    y: float
    z: float  # hub height
    rotor_diameter: float
    ct: float  # coeficient d'empenta
    velocity_deficit_initial: float = 0.0
    
    def wake_radius_at_downwind(self, distance: float) -> float:
        """
        Calcula el radi del wake a una distància downstream
        
        Equivalent C#:
        WakeModel.WakeRadiusAtDownwind(double distance)
        """
        # Expansió del wake (aproximació lineal)
        k = 0.1  # constant de decaïment
        expansion_rate = k * distance + 1.0
        return self.rotor_diameter / 2 * expansion_rate


@dataclass
class WakeModelConfig:
    """Configuració del model de wake"""
    wake_model_type: str = "jensen"  # jensen, ainslie, larsen
    k_wake: float = 0.1  # constant de decaïment del wake
    turbulence_intensity: float = 0.1  # intensitat de turbulència
    deflection_coefficient: float = 0.0  # deflectió del wake


class WakeModel:
    """
    Model de pèrdues per wake
    
    Equivalent C#:
    public class WakeModel
    """
    
    def __init__(self, config: WakeModelConfig):
        self.config = config
    
    def jensen_velocity_deficit(
        self,
        downstream_distance: float,
        rotor_diameter: float,
        ct: float,
        hub_height: float,
        target_height: float,
        wake_radius: float
    ) -> float:
        """
        Model de Jensen per defecte de velocitat
        
        Equivalent C#:
        WakeModel.Jensen(double x, double D, double Ct, double Zh, double Zt, double rj)
        
        Args:
            downstream_distance: Distància downstream (m)
            rotor_diameter: Diàmetre del rotor (m)
            ct: Coeficient d'empenta
            hub_height: Alçada del cub (m)
            target_height: Alçada del punt objectiu (m)
            wake_radius: Radi del wake a la distància x
            
        Returns:
            Fractional velocity deficit (0-1)
        """
        # Con pràctica del wake
        con_0 = 0.5 * (1 + np.cos(np.pi * wake_radius / (rotor_diameter / 2)))
        
        # Factor de recuperació
        recovery = np.sqrt(1 - 2 * ct * (1 - con_0) * downstream_distance / 
                          (downstream_distance + 2 * self.config.k_wake * rotor_diameter))
        
        # Defecte de velocitat
        deficit = 1 - recovery
        
        return max(0.0, min(1.0, deficit))
    
    def larsen_velocity_deficit(
        self,
        downstream_distance: float,
        rotor_diameter: float,
        ct: float,
        turbulence_intensity: float
    ) -> float:
        """
        Model de Larsen (més precís per distàncies curtes)
        
        Equivalent C#:
        WakeModel.Larsen(double x, double D, double Ct, double TI)
        """
        # Longitud d'escala del wake
        L = 9.5 * rotor_diameter / (turbulence_intensity + 0.1)
        
        if downstream_distance > L:
            # Zòna de similitud
            sigma = 0.2 * downstream_distance
            deficit = 0.5 * ct * (rotor_diameter / sigma) ** 2
        else:
            # Zona propera
            sigma = 0.3 * downstream_distance
            deficit = 0.5 * ct * (rotor_diameter / sigma) ** 2
        
        return max(0.0, min(1.0, deficit))
    
    def calculate_wake_deficit_at_point(
        self,
        point: WakePoint,
        turbine_wake: TurbineWake,
        wind_direction: float
    ) -> float:
        """
        Calcula el defecte de velocitat en un punt causat per una turbina
        
        Equivalent C#:
        WakeModel.CalculateWakeAtPoint()
        """
        # Vector des de la turbina al punt
        dx = point.x - turbine_wake.x
        dy = point.y - turbine_wake.y
        
        # Distància downstream projectada
        wind_angle_rad = np.deg2rad(wind_direction)
        downstream_dist = -dx * np.cos(wind_angle_rad) - dy * np.sin(wind_angle_rad)
        
        # Si el punt és upstream, no hi ha efecte wake
        if downstream_dist <= 0:
            return 0.0
        
        # Distància lateral
        cross_dist = -dx * np.sin(wind_angle_rad) + dy * np.cos(wind_angle_rad)
        
        # Radi del wake a la distància downstream
        wake_radius = turbine_wake.wake_radius_at_downwind(downstream_dist)
        
        # Verificar si el punt està dins del wake
        if abs(cross_dist) > wake_radius:
            return 0.0
        
        # Calcular defecte segons el model
        if self.config.wake_model_type == "jensen":
            deficit = self.jensen_velocity_deficit(
                downstream_dist,
                turbine_wake.rotor_diameter,
                turbine_wake.ct,
                turbine_wake.z,
                point.z,
                wake_radius
            )
        elif self.config.wake_model_type == "larsen":
            deficit = self.larsen_velocity_deficit(
                downstream_dist,
                turbine_wake.rotor_diameter,
                turbine_wake.ct,
                self.config.turbulence_intensity
            )
        else:
            deficit = self.jensen_velocity_deficit(
                downstream_dist,
                turbine_wake.rotor_diameter,
                turbine_wake.ct,
                turbine_wake.z,
                point.z,
                wake_radius
            )
        
        return deficit
    
    def calculate_total_deficit(
        self,
        point: WakePoint,
        turbine_wakes: list[TurbineWake],
        wind_direction: float
    ) -> float:
        """
        Calcula el defecte total (superposició de múltiples wakes)
        
        Equivalent C#:
        WakeCollection.CalculateTotalDeficit()
        """
        total_deficit = 0.0
        
        for wake in turbine_wakes:
            deficit = self.calculate_wake_deficit_at_point(point, wake, wind_direction)
            
            # Superposició quadràtica (més realista)
            total_deficit = np.sqrt(total_deficit**2 + deficit**2)
        
        return min(1.0, total_deficit)


class WakeCollection:
    """
    Col·lecció de wakes per a tot el parc eòlic
    
    Equivalent C#:
    public class WakeCollection
    """
    
    def __init__(self):
        self.wake_model = WakeModel(WakeModelConfig())
        self.turbine_wakes: list[TurbineWake] = []
    
    def add_turbine_wake(
        self,
        turbine_id: str,
        x: float,
        y: float,
        z: float,
        rotor_diameter: float,
        ct: float
    ):
        """Afegeix un wake al col·lecció"""
        self.turbine_wakes.append(TurbineWake(
            turbine_id=turbine_id,
            x=x,
            y=y,
            z=z,
            rotor_diameter=rotor_diameter,
            ct=ct
        ))
    
    def calculate_wake_map(
        self,
        grid_x: np.ndarray,
        grid_y: np.ndarray,
        hub_height: float,
        wind_direction: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Genera un mapa 2D de defectes de velocitat
        
        Equivalent C#:
        WakeCollection.WakeMap2D()
        """
        deficit_map = np.zeros((len(grid_y), len(grid_x)))
        
        for i, y in enumerate(grid_y):
            for j, x in enumerate(grid_x):
                point = WakePoint(x=x, y=y, z=hub_height)
                deficit = self.wake_model.calculate_total_deficit(
                    point, self.turbine_wakes, wind_direction
                )
                deficit_map[i, j] = deficit
        
        # Crear meshgrid per coordenades
        X, Y = np.meshgrid(grid_x, grid_y)
        
        return X, Y, deficit_map
    
    def calculate_sector_losses(
        self,
        sectors: int = 12
    ) -> dict:
        """
        Calcula pèrdues per sector de direcció
        
        Equivalent C#:
        WakeCollection.SectorWakeLoss()
        """
        sector_size = 360 / sectors
        losses = {}
        
        for sector in range(sectors):
            wind_direction = sector * sector_size
            avg_deficit = 0.0
            n_points = 0
            
            # Calcular per vàries turbines
            for wake in self.turbine_wakes:
                point = WakePoint(
                    x=wake.x + 5 * wake.rotor_diameter,
                    y=wake.y,
                    z=wake.z
                )
                deficit = self.wake_model.calculate_wake_deficit_at_point(
                    point, wake, wind_direction
                )
                avg_deficit += deficit
                n_points += 1
            
            if n_points > 0:
                avg_deficit /= n_points
                losses[f"sector_{sector}"] = {
                    "direction_range": (
                        sector * sector_size,
                        (sector + 1) * sector_size
                    ),
                    "wake_loss_fraction": avg_deficit,
                    "wake_loss_percent": avg_deficit * 100
                }
        
        return losses
    
    def calculate_global_loss(self) -> float:
        """
        Calcula la pèrdua global del parc
        
        Equivalent C#:
        WakeCollection.TotalWakeLoss()
        """
        if not self.turbine_wakes:
            return 0.0
        
        # Simular vents de totes les direccions
        total_deficit = 0.0
        n_directions = 12
        
        for sector in range(n_directions):
            direction = sector * (360 / n_directions)
            avg_deficit = 0.0
            
            for wake in self.turbine_wakes:
                point = WakePoint(
                    x=wake.x + 5 * wake.rotor_diameter,
                    y=wake.y,
                    z=wake.z
                )
                deficit = self.wake_model.calculate_wake_deficit_at_point(
                    point, wake, direction
                )
                avg_deficit += deficit
            
            avg_deficit /= len(self.turbine_wakes)
            total_deficit += avg_deficit
        
        return total_deficit / n_directions


def calculate_wake_losses(
    turbines: list,
    wind_data: pd.DataFrame,
    grid_resolution: int = 50
) -> dict:
    """
    Funció d'utilitat per calcular pèrdues de wake completes
    
    Args:
        turbines: Llista de turbines
        wind_data: DataFrame amb dades de vent
        grid_resolution: Resolució del mapa de wake
        
    Returns:
        Dictionary amb resultats
    """
    wake_collection = WakeCollection()
    
    # Afegir wakes de cada turbina
    for t in turbines:
        ct = getattr(t, 'ct', 0.8)  # Defecte: 0.8 si no existeix
        wake_collection.add_turbine_wake(
            turbine_id=getattr(t, 'name', 'unknown'),
            x=getattr(t, 'x', 0),
            y=getattr(t, 'y', 0),
            z=getattr(t, 'hub_height', 80),
            rotor_diameter=getattr(t, 'rotor_diameter', 100),
            ct=ct
        )
    
    # Calcular pèrdues globals
    global_loss = wake_collection.calculate_global_loss()
    
    # Calcular pèrdues per sector
    sector_losses = wake_collection.calculate_sector_losses()
    
    return {
        "global_wake_loss": global_loss,
        "global_wake_loss_percent": global_loss * 100,
        "sector_losses": sector_losses,
        "n_turbines": len(turbines)
    }
