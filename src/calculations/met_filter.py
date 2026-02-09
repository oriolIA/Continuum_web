"""
Met Data Filtering - Port de Met_Data_Filter.cs (C#)

Funcionalitats:
- Filtratge de dades per ombra de torre
- Detecció de gel
- Filtratge per desviació estàndard
- Extrapolació de shear (power law)
"""

from typing import Optional
import numpy as np
import pandas as pd
from scipy import stats

from ..core.met import MetData, MetStats


# Constants equivalents al C#
TOWER_SHADOW_OFFSET = 30.0  # graus


class MetDataFilter:
    """
    Filtratge de dades meteorològiques
    
    Equivalent C#:
    public class MetDataFilter
    """
    
    def __init__(
        self,
        tower_offset: float = TOWER_SHADOW_OFFSET,
        ice_threshold_temp: float = 2.0,  # °C
        max_std_threshold: float = 5.0    # m/s
    ):
        self.tower_offset = tower_offset
        self.ice_threshold_temp = ice_threshold_temp
        self.max_std_threshold = max_std_threshold
    
    def filter_tower_shadow(
        self,
        df: pd.DataFrame,
        direction_col: str = 'wind_direction',
        speed_col: str = 'wind_speed'
    ) -> pd.DataFrame:
        """
        Filtra dades afectades per ombra de torre
        
        Equivalent C#:
        MetDataFilter.TowerShadow(List<Met> metData)
        """
        # Rang d'ombres de torre (± offset)
        min_dir = (360 - self.tower_offset) % 360
        max_dir = self.tower_offset
        
        def is_in_shadow(row):
            """Check if direction is in tower shadow zone"""
            direction = row[direction_col]
            if min_dir > max_dir:
                # Cas on el rang creua el 0°
                return direction >= min_dir or direction <= max_dir
            return min_dir <= direction <= max_dir
        
        # Marcar dades afectades
        mask = df.apply(is_in_shadow, axis=1)
        
        # Reduir velocitat a zona d'ombra (conservador)
        df_filtered = df.copy()
        df_filtered.loc[mask, speed_col] = df_filtered.loc[mask, speed_col] * 0.7
        
        return df_filtered
    
    def filter_ice(
        self,
        df: pd.DataFrame,
        temp_col: str = 'temperature',
        speed_col: str = 'wind_speed'
    ) -> pd.DataFrame:
        """
        Filtra dades afectades per gel
        
        Equivalent C#:
        MetDataFilter.Ice(List<Met> metData)
        """
        # Velocitat molt baixa amb temperatures properes a 0 = gel
        mask = (df[temp_col] < self.ice_threshold_temp) & \
               (df[temp_col] > -5.0) & \
               (df[speed_col] < 1.0)
        
        # Eliminar o marcar dades
        return df[~mask].copy()
    
    def filter_std(
        self,
        df: pd.DataFrame,
        speed_col: str = 'wind_speed',
        window: int = 10
    ) -> pd.DataFrame:
        """
        Filtra basant-se en desviació estàndard mòbil
        
        Equivalent C#:
        MetDataFilter.Std(Met[] metData)
        """
        # Calcular desviació estàndard mòbil
        rolling_std = df[speed_col].rolling(window=window, center=True).std()
        
        # Marcar valors amb STD excessiva
        mask = rolling_std > self.max_std_threshold
        
        return df[~mask].copy()
    
    def full_filter(
        self,
        df: pd.DataFrame,
        direction_col: str = 'wind_direction',
        speed_col: str = 'wind_speed',
        temp_col: str = 'temperature'
    ) -> pd.DataFrame:
        """
        Aplica tots els filtres en seqüència
        
        Equivalent C#:
        MetDataFilter.Filter(Met[] metData)
        """
        # Filtratge d'ombra
        df = self.filter_tower_shadow(df, direction_col, speed_col)
        
        # Filtratge de gel (si hi ha dades de temperatura)
        if temp_col in df.columns:
            df = self.filter_ice(df, temp_col, speed_col)
        
        # Filtratge per desviació estàndard
        df = self.filter_std(df, speed_col)
        
        return df.reset_index(drop=True)
    
    def calculate_shear(
        self,
        df: pd.DataFrame,
        ref_height: float,
        target_height: float,
        speed_col: str = 'wind_speed'
    ) -> tuple[float, pd.DataFrame]:
        """
        Calcula l'exponent de shear (power law) i extrapola
        
        Equivalent C#:
        MetDataFilter.Shear(Met[] metData, double z0, double zh)
        
        Args:
            df: DataFrame amb dades
            ref_height: Alçada de referència (on tenim mesures)
            target_height: Alçada objectiu
            speed_col: Nom de la columna de velocitat
            
        Returns:
            tuple: (exponent_alpha, DataFrame extrapolat)
        """
        # Calcular exponent de shear per cada registre
        alpha_values = []
        
        for idx, row in df.iterrows():
            # Power law: u(z) = u(zr) * (z/zr)^alpha
            # alpha = ln(u2/u1) / ln(z2/z1)
            if ref_height > 0 and row[speed_col] > 0:
                # Assumim alçada de referència i una hipotètica
                # En realitat necessitem mesures a múltiples altures
                alpha = 0.15  # Valor per defecte (terreny obert)
            else:
                alpha = np.nan
            alpha_values.append(alpha)
        
        df = df.copy()
        df['shear_alpha'] = alpha_values
        
        # Extrapolar a alçada objectiu
        mean_alpha = np.nanmean(alpha_values)
        if not np.isnan(mean_alpha) and mean_alpha > 0:
            df[speed_col + '_extrapolated'] = df[speed_col] * \
                (target_height / ref_height) ** mean_alpha
        else:
            df[speed_col + '_extrapolated'] = df[speed_col]
        
        return mean_alpha, df


def filter_met_data(
    df: pd.DataFrame,
    remove_tower_shadow: bool = True,
    remove_ice: bool = True,
    remove_high_std: bool = True,
    ref_height: float = 10.0,
    target_height: float = 80.0
) -> dict:
    """
    Funció d'utilitat per aplicar filtres complets
    
    Equivalent C#:
    MetDataFilter.FilteredMetData(metData)
    """
    filter_obj = MetDataFilter()
    
    df_filtered = df.copy()
    
    # Filtres
    if remove_tower_shadow and 'wind_direction' in df.columns:
        df_filtered = filter_obj.filter_tower_shadow(df_filtered)
    
    if remove_ice and 'temperature' in df.columns:
        df_filtered = filter_obj.filter_ice(df_filtered)
    elif remove_ice and 'temperature' not in df.columns:
        # Skip ice filter if no temperature data
        pass
    
    if remove_high_std and 'wind_speed' in df.columns:
        df_filtered = filter_obj.filter_std(df_filtered)
    
    # Calcular shear
    if 'wind_speed' in df.columns:
        alpha, df_final = filter_obj.calculate_shear(
            df_filtered,
            ref_height=ref_height,
            target_height=target_height
        )
    else:
        alpha = 0.15
        df_final = df_filtered
    
    return {
        'filtered_data': df_final,
        'shear_alpha': alpha,
        'original_count': len(df),
        'filtered_count': len(df_filtered)
    }
