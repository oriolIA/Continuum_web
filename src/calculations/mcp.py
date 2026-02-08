"""
MCP (Measure-Correlate-Predict) - Port de MCP.cs (C#)

Mètodes de correlació entre estacions meteorològiques:
- Orthogonal Regression
- Method of Bins
- Matrix-LastWS
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class MCPConfig:
    """Configuració per a MCP"""
    reference_station: str
    target_station: str
    method: str = "orthogonal_regression"
    sectors: int = 12  # Per anàlisi sectorial
    confidence_level: float = 0.95


@dataclass
class MCPSectorResult:
    """Resultat de MCP per un sector"""
    sector: int
    direction_range: tuple[float, float]
    slope: float
    intercept: float
    correlation: float
    uncertainty: float
    n_samples: int


@dataclass
class MCPResult:
    """Resultat complet de MCP"""
    method: str
    global_slope: float
    global_intercept: float
    global_correlation: float
    sector_results: list[MCPSectorResult]
    predicted_data: pd.DataFrame
    uncertainty_summary: dict


class MCP:
    """
    Measure-Correlate-Predict per correlació d'estacions
    
    Equivalent C#:
    public class MCP
    """
    
    def __init__(self, config: MCPConfig):
        self.config = config
    
    def orthogonal_regression(
        self,
        ref_data: np.ndarray,
        target_data: np.ndarray
    ) -> tuple[float, float, float]:
        """
        Regressió Ortogonal (TLS - Total Least Squares)
        
        Equivalent C#:
        MCP.OrthogonalRegression(double[] reference, double[] target)
        
        Returns: (slope, intercept, correlation)
        """
        # Centrar les dades
        ref_mean = np.mean(ref_data)
        target_mean = np.mean(target_data)
        
        ref_centered = ref_data - ref_mean
        target_centered = target_data - target_mean
        
        # Covariança i variàncies
        covariance = np.mean(ref_centered * target_centered)
        var_ref = np.mean(ref_centered ** 2)
        var_target = np.mean(target_centered ** 2)
        
        # Regressió ortogonal
        # Minimitza distàncies perpendiculars a la línia
        if var_ref > 0 and var_target > 0:
            # Solució analítica per TLS
            theta = 0.5 * np.arctan2(
                2 * covariance,
                var_ref - var_target
            )
            
            slope = np.tan(theta)
            intercept = target_mean - slope * ref_mean
            
            # Correlació
            if var_ref > 0 and var_target > 0:
                correlation = covariance / np.sqrt(var_ref * var_target)
            else:
                correlation = 0.0
        else:
            slope, intercept, correlation = 1.0, 0.0, 0.0
        
        return slope, intercept, correlation
    
    def method_of_bins(
        self,
        ref_data: np.ndarray,
        target_data: np.ndarray,
        n_bins: int = 10
    ) -> tuple[float, float, float]:
        """
        Mètode de Bins - mitjana per intervals
        
        Equivalent C#:
        MCP.MethodOfBins(double[] reference, double[] target, int nBins)
        
        Returns: (slope, intercept, correlation)
        """
        # Crear bins basats en dades de referència
        ref_min, ref_max = np.min(ref_data), np.max(ref_data)
        bins = np.linspace(ref_min, ref_max, n_bins + 1)
        
        bin_means_ref = []
        bin_means_target = []
        
        for i in range(n_bins):
            mask = (ref_data >= bins[i]) & (ref_data < bins[i + 1])
            if np.sum(mask) > 0:
                bin_means_ref.append(np.mean(ref_data[mask]))
                bin_means_target.append(np.mean(target_data[mask]))
        
        bin_means_ref = np.array(bin_means_ref)
        bin_means_target = np.array(bin_means_target)
        
        # Regressió lineal simple sobre les mitjanes dels bins
        if len(bin_means_ref) >= 2:
            slope, intercept = np.polyfit(bin_means_ref, bin_means_target, 1)
            
            # Correlació sobre bins
            correlation = np.corrcoef(bin_means_ref, bin_means_target)[0, 1]
        else:
            slope, intercept, correlation = 1.0, 0.0, 0.0
        
        return slope, intercept, correlation
    
    def matrix_last_ws(
        self,
        ref_data: np.ndarray,
        target_data: np.ndarray,
        ref_dirs: Optional[np.ndarray] = None,
        target_dirs: Optional[np.ndarray] = None,
        n_sectors: int = 12
    ) -> tuple[float, float, float]:
        """
        Matriu de correcció per velocitat i direcció
        
        Equivalent C#:
        MCP.Matrix_LastWS(double[] reference, double[] target, double[] refDirs, double[] targDirs)
        
        Returns: (slope, intercept, correlation)
        """
        # Matriu de sectors
        sector_size = 360 / n_sectors
        
        if ref_dirs is None:
            ref_dirs = np.zeros(len(ref_data))
        if target_dirs is None:
            target_dirs = np.zeros(len(target_data))
        
        # Calcular factors de correcció per sector
        sector_corrections = np.ones(n_sectors)
        sector_counts = np.zeros(n_sectors)
        
        for i in range(len(ref_data)):
            sector = int(ref_dirs[i] // sector_size) % n_sectors
            if ref_data[i] > 0:
                factor = target_data[i] / ref_data[i]
                sector_corrections[sector] = (sector_corrections[sector] * sector_counts[sector] + factor) / (sector_counts[sector] + 1)
                sector_counts[sector] += 1
        
        # Aplicar correcció sectorial i calcular regressió global
        corrected_target = np.zeros(len(target_data))
        for i in range(len(ref_data)):
            sector = int(ref_dirs[i] // sector_size) % n_sectors
            corrected_target[i] = target_data[i] / sector_corrections[sector]
        
        # Regressió simple
        slope, intercept = np.polyfit(ref_data, corrected_target, 1)
        correlation = np.corrcoef(ref_data, corrected_target)[0, 1]
        
        return slope, intercept, correlation
    
    def run_sector_analysis(
        self,
        ref_df: pd.DataFrame,
        target_df: pd.DataFrame
    ) -> list[MCPSectorResult]:
        """
        Anàlisi MCP per sectors de direcció
        
        Equivalent C#:
        MCP.SectorialAnalysis()
        """
        sector_size = 360 // self.config.sectors
        results = []
        
        for sector in range(self.config.sectors):
            dir_min = sector * sector_size
            dir_max = (sector + 1) * sector_size
            
            # Filtrar dades del sector
            mask = (ref_df['wind_direction'] >= dir_min) & \
                   (ref_df['wind_direction'] < dir_max)
            
            if mask.sum() < 10:  # Mínim mostres
                continue
            
            ref_sector = ref_df.loc[mask, 'wind_speed'].values
            target_sector = target_df.loc[mask, 'wind_speed'].values
            
            # Executar mètode seleccionat
            if self.config.method == "orthogonal":
                slope, intercept, corr = self.orthogonal_regression(ref_sector, target_sector)
            elif self.config.method == "bins":
                slope, intercept, corr = self.method_of_bins(ref_sector, target_sector)
            else:
                slope, intercept, corr = self.orthogonal_regression(ref_sector, target_sector)
            
            # Incertesa (basada en residuals)
            predicted = slope * ref_sector + intercept
            residuals = target_sector - predicted
            uncertainty = np.std(residuals)
            
            results.append(MCPSectorResult(
                sector=sector,
                direction_range=(dir_min, dir_max),
                slope=slope,
                intercept=intercept,
                correlation=corr,
                uncertainty=uncertainty,
                n_samples=int(mask.sum())
            ))
        
        return results
    
    def run(
        self,
        ref_df: pd.DataFrame,
        target_df: pd.DataFrame
    ) -> MCPResult:
        """
        Executa MCP complet
        
        Equivalent C#:
        MCP.Run()
        """
        # Dades globals
        ref_global = ref_df['wind_speed'].values
        target_global = target_df['wind_speed'].values
        
        # Executar mètode global
        if self.config.method == "orthogonal":
            slope, intercept, corr = self.orthogonal_regression(ref_global, target_global)
        elif self.config.method == "bins":
            slope, intercept, corr = self.method_of_bins(ref_global, target_global)
        elif self.config.method == "matrix":
            ref_dirs = ref_df.get('wind_direction', np.zeros(len(ref_global))).values
            target_dirs = target_df.get('wind_direction', np.zeros(len(target_global))).values
            slope, intercept, corr = self.matrix_last_ws(ref_global, target_global, ref_dirs, target_dirs)
        else:
            slope, intercept, corr = self.orthogonal_regression(ref_global, target_global)
        
        # Anàlisi sectorial
        sector_results = self.run_sector_analysis(ref_df, target_df)
        
        # Predir dades futures
        predicted_data = target_df.copy()
        predicted_data['predicted_ws'] = slope * ref_global + intercept
        
        # Resum d'incertesa
        residuals = target_global - predicted_data['predicted_ws'].values
        uncertainty_summary = {
            'mean_uncertainty': np.mean([r.uncertainty for r in sector_results]),
            'max_uncertainty': np.max([r.uncertainty for r in sector_results]),
            'min_correlation': np.min([r.correlation for r in sector_results]),
            'global_correlation': corr
        }
        
        return MCPResult(
            method=self.config.method,
            global_slope=slope,
            global_intercept=intercept,
            global_correlation=corr,
            sector_results=sector_results,
            predicted_data=predicted_data,
            uncertainty_summary=uncertainty_summary
        )
