"""
Wind Resource Reports

Generació de reports i visualitzacions per estudis eòlics:
- Histograma de velocitats
- Rosa dels vents
- Distribució Weibull
- Vents extrems
- Taules estadístiques
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class WindReportConfig:
    """Configuració del report"""
    n_sectors: int = 12
    n_hist_bins: int = 20
    speed_bins: List[float] = None
    extreme_threshold: float = 15.0  # m/s per vents extrems


class WindReport:
    """
    Generador de reports eòlics
    
    Args:
        wind_speeds: Array de velocitats (m/s)
        wind_directions: Array de direccions (graus)
        time_index: DatetimeIndex opcional
    """
    
    def __init__(
        self,
        wind_speeds: np.ndarray,
        wind_directions: np.ndarray,
        time_index: Optional[pd.DatetimeIndex] = None
    ):
        self.wind_speeds = np.array(wind_speeds)
        self.wind_directions = np.array(wind_directions) % 360
        self.time_index = time_index
        self.n = len(wind_speeds)
        
        # Filtrar valors vàlids
        valid = ~np.isnan(wind_speeds) & ~np.isnan(wind_directions)
        self.wind_speeds = self.wind_speeds[valid]
        self.wind_directions = self.wind_directions[valid]
        self.valid_n = len(self.wind_speeds)
    
    def histogram(self, n_bins: int = None) -> dict:
        """
        Histograma de velocitats
        
        Returns:
            Dict amb bins, counts i estadístiques
        """
        if n_bins is None:
            n_bins = 20
        
        counts, bin_edges = np.histogram(self.wind_speeds, bins=n_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        return {
            'bin_edges': bin_edges.tolist(),
            'bin_centers': bin_centers.tolist(),
            'counts': counts.tolist(),
            'total_samples': self.valid_n,
            'bins_with_data': int(np.sum(counts > 0))
        }
    
    def wind_rose(self, n_sectors: int = 12) -> dict:
        """
        Rosa dels vents
        
        Returns:
            Dict amb sectors, frequencies i mean speeds
        """
        sector_size = 360 / n_sectors
        
        frequencies = []
        mean_speeds = []
        max_speeds = []
        
        for i in range(n_sectors):
            mask = (self.wind_directions >= i * sector_size) & \
                   (self.wind_directions < (i + 1) * sector_size)
            
            sector_speeds = self.wind_speeds[mask]
            
            frequencies.append(len(sector_speeds) / self.valid_n * 100)
            
            if len(sector_speeds) > 0:
                mean_speeds.append(float(np.mean(sector_speeds)))
                max_speeds.append(float(np.max(sector_speeds)))
            else:
                mean_speeds.append(0.0)
                max_speeds.append(0.0)
        
        sectors = [f"{(i * sector_size):.0f}-{(i + 1) * sector_size:.0f}°" 
                   for i in range(n_sectors)]
        
        return {
            'sectors': sectors,
            'frequencies_percent': frequencies,
            'mean_speeds_ms': mean_speeds,
            'max_speeds_ms': max_speeds,
            'n_sectors': n_sectors,
            'dominant_sector': int(np.argmax(frequencies)),
            'prevailing_direction': sectors[np.argmax(frequencies)]
        }
    
    def weibull_fit(self) -> dict:
        """
        Ajust de distribució Weibull
        
        Returns:
            Dict amb paràmetres i estadístiques
        """
        # Filtrar vents positius
        speeds = self.wind_speeds[self.wind_speeds > 0]
        
        if len(speeds) < 10:
            return {'error': 'Insufficient data for Weibull fit'}
        
        # MLE fit
        shape, loc, scale = stats.weibull_min.fit(speeds, floc=0)
        
        # Calcular A (velocitat mitjana) i k (factor de forma)
        A = scale * np.math.gamma(1 + 1/shape)
        k = shape
        
        # Energia disponible (proporcional a v³)
        mean_cube = np.mean(speeds ** 3)
        AEP_factor = mean_cube / (A ** 3) if A > 0 else 1.0
        
        # Validació: comparar mitjana amb Weibull
        theoretical_mean = scale * np.math.gamma(1 + 1/shape)
        empirical_mean = np.mean(speeds)
        
        return {
            'k_shape': float(k),
            'A_scale_ms': float(scale),
            'mean_weibull_ms': float(theoretical_mean),
            'mean_empirical_ms': float(empirical_mean),
            'aep_factor': float(AEP_factor),
            'gamma_factor': np.math.gamma(1 + 1/shape),
            'r_squared': 1 - (theoretical_mean - empirical_mean)**2 / (empirical_mean**2) if empirical_mean > 0 else 0
        }
    
    def extreme_winds(self, threshold: float = 15.0) -> dict:
        """
        Anàlisi de vents extrems
        
        Args:
            threshold: Velocitat mínima per considerar extrem (m/s)
        
        Returns:
            Dict amb estadístiques d'extrems
        """
        extreme_mask = self.wind_speeds >= threshold
        extreme_speeds = self.wind_speeds[extreme_mask]
        
        # Percentil 99
        p99 = np.percentile(self.wind_speeds, 99)
        
        # Màxim absolut
        max_speed = np.max(self.wind_speeds)
        
        # Direccions dels extrems
        if len(extreme_speeds) > 0:
            extreme_dirs = self.wind_directions[extreme_mask]
            extreme_directions = {}
            
            sector_size = 360 // 12
            for i in range(12):
                mask = (extreme_dirs >= i * sector_size) & \
                       (extreme_dirs < (i + 1) * sector_size)
                extreme_directions[f"{(i * sector_size)}-{(i + 1) * sector_size}°"] = int(np.sum(mask))
        else:
            extreme_directions = {s: 0 for s in [f"{i*30}-{(i+1)*30}°" for i in range(12)]}
        
        return {
            'threshold_ms': threshold,
            'n_extreme_events': int(len(extreme_speeds)),
            'extreme_percent': len(extreme_speeds) / self.valid_n * 100,
            'percentile_99_ms': float(p99),
            'max_speed_ms': float(max_speed),
            'extreme_directions': extreme_directions,
            'return_period_50yr_estimate': self._estimate_return_period(max_speed)
        }
    
    def _estimate_return_period(self, max_speed: float) -> dict:
        """
        Estimació simplificada de període de retorn
        
        Nota: Per càlculs reals caldrien dades de 20+ anys
        """
        # Simplificat: basat en Gumbel
        if self.valid_n < 100:
            return {'error': 'Insufficient data for return period estimate'}
        
        # Assumim 1 mostra per hora → 8760 mostres/any
        years_equivalent = self.valid_n / 8760
        
        if years_equivalent < 1:
            return {'note': f'Equivalent to {years_equivalent:.2f} years - need more data'}
        
        # Gumbel aproximat
        mu = np.mean(self.wind_speeds)
        sigma = np.std(self.wind_speeds)
        
        # Vent de disseny per 50 anys (simplificat)
        design_50yr = mu + sigma * 3.9  # Factor per Gumbel 50-any
        
        return {
            'equivalent_years': round(years_equivalent, 2),
            'design_wind_50yr_ms': round(design_50yr, 2),
            'note': 'Simplified Gumbel estimate - requires longer dataset for accuracy'
        }
    
    def hourly_distribution(self) -> dict:
        """
        Distribució horària del vent
        
        Returns:
            Dict amb estadístiques per hora
        """
        if self.time_index is None:
            return {'error': 'No time index provided'}
        
        df = pd.DataFrame({
            'speed': self.wind_speeds,
            'direction': self.wind_directions
        }, index=self.time_index)
        
        df['hour'] = df.index.hour
        
        hourly = df.groupby('hour').agg({
            'speed': ['mean', 'std', 'min', 'max', 'count']
        })
        
        hourly.columns = ['mean', 'std', 'min', 'max', 'count']
        
        return {
            'hours': list(range(24)),
            'mean_speed_ms': hourly['mean'].tolist(),
            'std_speed_ms': hourly['std'].tolist(),
            'min_speed_ms': hourly['min'].tolist(),
            'max_speed_ms': hourly['max'].tolist(),
            'n_samples': hourly['count'].tolist()
        }
    
    def monthly_distribution(self) -> dict:
        """
        Distribució mensual del vent
        
        Returns:
            Dict amb estadístiques per mes
        """
        if self.time_index is None:
            return {'error': 'No time index provided'}
        
        df = pd.DataFrame({
            'speed': self.wind_speeds,
            'direction': self.wind_directions
        }, index=self.time_index)
        
        df['month'] = df.index.month
        
        monthly = df.groupby('month').agg({
            'speed': ['mean', 'std', 'count']
        })
        
        monthly.columns = ['mean', 'std', 'count']
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        return {
            'months': months,
            'mean_speed_ms': monthly['mean'].tolist(),
            'std_speed_ms': monthly['std'].tolist(),
            'n_samples': monthly['count'].tolist()
        }
    
    def turbulence_intensity(self, std_window: int = 10) -> dict:
        """
        Càlcul de intensitat de turbulència
        
        Args:
            std_window: Mida de la finestra per calcular desviació
        
        Returns:
            Dict amb estadístiques de turbulència
        """
        # Intensitat de turbulència = std / mean
        rolling_mean = pd.Series(self.wind_speeds).rolling(std_window, center=True).mean()
        rolling_std = pd.Series(self.wind_speeds).rolling(std_window, center=True).std()
        
        valid = ~rolling_std.isna() & ~rolling_mean.isna() & (rolling_mean > 0)
        
        ti = rolling_std[valid] / rolling_mean[valid]
        
        return {
            'ti_mean': float(ti.mean()),
            'ti_std': float(ti.std()),
            'ti_max': float(ti.max()),
            'ti_percentile_90': float(np.percentile(ti, 90)),
            'ti_percentile_95': float(np.percentile(ti, 95)),
            'window_size': std_window,
            'n_samples_valid': int(valid.sum())
        }
    
    def full_report(self, config: WindReportConfig = None) -> dict:
        """
        Report complet amb totes les mètriques
        
        Returns:
            Dict amb report complet
        """
        if config is None:
            config = WindReportConfig()
        
        return {
            'summary': {
                'total_samples': self.valid_n,
                'mean_speed_ms': float(np.mean(self.wind_speeds)),
                'std_speed_ms': float(np.std(self.wind_speeds)),
                'max_speed_ms': float(np.max(self.wind_speeds)),
                'min_speed_ms': float(np.min(self.wind_speeds)),
                'median_speed_ms': float(np.median(self.wind_speeds))
            },
            'histogram': self.histogram(config.n_hist_bins),
            'wind_rose': self.wind_rose(config.n_sectors),
            'weibull': self.weibull_fit(),
            'extreme_winds': self.extreme_winds(config.extreme_threshold),
            'hourly': self.hourly_distribution(),
            'monthly': self.monthly_distribution(),
            'turbulence': self.turbulence_intensity()
        }


def generate_report_from_dataframe(
    df: pd.DataFrame,
    speed_col: str = 'wind_speed',
    direction_col: str = 'wind_direction',
    time_col: str = None
) -> dict:
    """
    Genera report des de DataFrame
    
    Args:
        df: DataFrame amb dades
        speed_col: Columna de velocitat
        direction_col: Columna de direcció
        time_col: Columna de temps (opcional)
    
    Returns:
        Report complet
    """
    speeds = df[speed_col].values
    
    if direction_col in df.columns:
        directions = df[direction_col].values
    else:
        directions = np.zeros(len(df))
    
    if time_col and time_col in df.columns:
        time_index = pd.to_datetime(df[time_col])
    else:
        time_index = None
    
    report = WindReport(speeds, directions, time_index)
    return report.full_report()
