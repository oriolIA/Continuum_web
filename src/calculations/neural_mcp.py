"""
Neural MCP - Xarxes Neuronals per Measure-Correlate-Predict

Avantatges sobre mètodes clàssics:
- No assumeix relació lineal
- Pot capturar relacions complexes
- Millor per dades amb noise
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


@dataclass
class NeuralMCPConfig:
    """Configuració per Neural MCP"""
    input_features: int = 2  # [wind_speed_ref, wind_dir_ref]
    hidden_layers: list = None
    output_features: int = 1  # wind_speed_target
    activation: str = "relu"
    dropout: float = 0.1
    learning_rate: float = 1e-3
    epochs: int = 500
    batch_size: int = 32


class NeuralMCPNetwork(nn.Module):
    """
    Xarxa neuronal per predicció de velocitat de vent
    
    Arquitectura: MLP amb capas ocultes
    """
    
    def __init__(self, config: NeuralMCPConfig):
        super().__init__()
        self.config = config
        
        layers = []
        in_features = config.input_features
        
        if config.hidden_layers is None:
            config.hidden_layers = [64, 32, 16]
        
        for hidden_size in config.hidden_layers:
            layers.append(nn.Linear(in_features, hidden_size))
            layers.append(nn.BatchNorm1d(hidden_size))
            layers.append(nn.Dropout(config.dropout))
            
            if config.activation == "relu":
                layers.append(nn.ReLU())
            elif config.activation == "tanh":
                layers.append(nn.Tanh())
            
            in_features = hidden_size
        
        layers.append(nn.Linear(in_features, config.output_features))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class NeuralMCP:
    """
    Neural Measure-Correlate-Predict
    
    Utilitza xarxes neuronals per estimar la relació
    entre estació de referència i estació objectiu
    """
    
    def __init__(self, config: Optional[NeuralMCPConfig] = None):
        self.config = config or NeuralMCPConfig()
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.history = None
    
    def _prepare_data(
        self,
        ref_data: pd.DataFrame,
        target_data: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepara dades per entrenament
        
        Input: [wind_speed_ref, wind_dir_ref]
        Output: [wind_speed_target]
        """
        # Combinar dades
        df = pd.DataFrame({
            'ref_ws': ref_data['wind_speed'].values,
            'ref_dir': ref_data['wind_direction'].values,
            'target_ws': target_data['wind_speed'].values
        })
        
        # Treure NaN
        df = df.dropna()
        
        # Codificar direcció com a features cícliques
        df['dir_sin'] = np.sin(np.deg2rad(df['ref_dir']))
        df['dir_cos'] = np.cos(np.deg2rad(df['ref_dir']))
        
        # Features d'entrada
        X = df[['ref_ws', 'dir_sin', 'dir_cos']].values
        y = df[['target_ws']].values
        
        return X, y
    
    def _preprocess(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        """Normalitza dades"""
        if self.scaler_X is None:
            self.scaler_X = {
                'mean': X.mean(axis=0),
                'std': X.std(axis=0) + 1e-8
            }
        
        return (X - self.scaler_X['mean']) / self.scaler_X['std']
    
    def _preprocess_y(self, y: np.ndarray, fit: bool = False) -> np.ndarray:
        """Normalitza output"""
        if self.scaler_y is None:
            self.scaler_y = {
                'mean': y.mean(),
                'std': y.std() + 1e-8
            }
        
        return (y - self.scaler_y['mean']) / self.scaler_y['std']
    
    def _inverse_transform_y(self, y_norm: np.ndarray) -> np.ndarray:
        """Desnormalitza output"""
        return y_norm * self.scaler_y['std'] + self.scaler_y['mean']
    
    def train(
        self,
        ref_data: pd.DataFrame,
        target_data: pd.DataFrame,
        val_split: float = 0.2
    ) -> dict:
        """
        Entrena el model Neural MCP
        
        Args:
            ref_data: DataFrame amb dades de referència
            target_data: DataFrame amb dades objectiu
            val_split: fracció per validació
        """
        # Preparar dades
        X, y = self._prepare_data(ref_data, target_data)
        X = self._preprocess(X, fit=True)
        y = self._preprocess_y(y, fit=True)
        
        # Train/val split
        n = len(X)
        split_idx = int(n * (1 - val_split))
        
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Convertir a tensors
        X_train_t = torch.FloatTensor(X_train)
        y_train_t = torch.FloatTensor(y_train)
        X_val_t = torch.FloatTensor(X_val)
        y_val_t = torch.FloatTensor(y_val)
        
        # DataLoaders
        train_ds = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_ds, batch_size=self.config.batch_size, shuffle=True)
        
        # Inicialitzar model
        self.model = NeuralMCPNetwork(self.config)
        
        # Optimitzador i loss
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        criterion = nn.MSELoss()
        
        # Entrenament
        self.history = {'train_loss': [], 'val_loss': []}
        
        self.model.train()
        for epoch in range(self.config.epochs):
            epoch_loss = 0
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                pred = self.model(X_batch)
                loss = criterion(pred, y_batch)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            
            # Validació
            self.model.eval()
            with torch.no_grad():
                val_pred = self.model(X_val_t)
                val_loss = criterion(val_pred, y_val_t).item()
            
            self.history['train_loss'].append(epoch_loss / len(train_loader))
            self.history['val_loss'].append(val_loss)
            
            if epoch % 100 == 0:
                print(f"Epoch {epoch}: Train Loss = {self.history['train_loss'][-1]:.4f}, Val Loss = {val_loss:.4f}")
        
        self.model.eval()
        return self.history
    
    def predict(self, ref_data: pd.DataFrame) -> np.ndarray:
        """
        Prediu velocitats a l'estació objectiu
        
        Args:
            ref_data: DataFrame amb dades de referència
            
        Returns:
            Prediccions de velocitat
        """
        self.model.eval()
        
        # Preparar input
        df = ref_data.copy()
        df['dir_sin'] = np.sin(np.deg2rad(df['wind_direction']))
        df['dir_cos'] = np.cos(np.deg2rad(df['wind_direction']))
        
        X = df[['wind_speed', 'dir_sin', 'dir_cos']].values
        X = self._preprocess(X)
        
        # Predir
        with torch.no_grad():
            X_t = torch.FloatTensor(X)
            y_pred_norm = self.model(X_t).numpy()
        
        # Desnormalitzar
        y_pred = self._inverse_transform_y(y_pred_norm)
        
        return y_pred.flatten()
    
    def sector_training(
        self,
        ref_data: pd.DataFrame,
        target_data: pd.DataFrame,
        n_sectors: int = 12
    ) -> dict:
        """
        Entrena models separats per cada sector de direcció
        """
        sector_size = 360 // n_sectors
        models = {}
        results = {}
        
        for sector in range(n_sectors):
            dir_min = sector * sector_size
            dir_max = (sector + 1) * sector_size
            
            # Filtrar dades del sector
            mask = (ref_data['wind_direction'] >= dir_min) & \
                   (ref_data['wind_direction'] < dir_max)
            
            if mask.sum() < 50:  # Mínim mostres
                continue
            
            ref_sector = ref_data[mask]
            target_sector = target_data[mask]
            
            # Entrenar model
            model = NeuralMCP(self.config)
            history = model.train(ref_sector, target_sector)
            
            models[f"sector_{sector}"] = model
            results[f"sector_{sector}"] = {
                "direction_range": (dir_min, dir_max),
                "n_samples": len(ref_sector),
                "final_val_loss": history['val_loss'][-1]
            }
        
        return {"models": models, "results": results}
    
    def evaluate(
        self,
        ref_data: pd.DataFrame,
        target_data: pd.DataFrame
    ) -> dict:
        """
        Avalua el model
        """
        predictions = self.predict(ref_data)
        actuals = target_data['wind_speed'].values
        
        # Mètriques
        mae = np.mean(np.abs(predictions - actuals))
        rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
        correlation = np.corrcoef(predictions, actuals)[0, 1]
        
        # Errors per rang de velocitat
        bins = [0, 5, 10, 15, 25]
        errors_by_bin = {}
        for i in range(len(bins) - 1):
            mask = (actuals >= bins[i]) & (actuals < bins[i + 1])
            if mask.sum() > 0:
                errors_by_bin[f"{bins[i]}-{bins[i+1]}"] = {
                    "mae": np.mean(np.abs(predictions[mask] - actuals[mask])),
                    "count": mask.sum()
                }
        
        return {
            "mae": mae,
            "rmse": rmse,
            "correlation": correlation,
            "r2": correlation ** 2,
            "errors_by_bin": errors_by_bin,
            "n_samples": len(actuals)
        }


class WindFieldCalibrator:
    """
    Calibració de camps de vent WRF amb dades observades
    
    Utilitza xarxes neuronals per aprendre correccions
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
    
    def create_calibration_model(
        self,
        wrf_data: np.ndarray,  # shape: (n_times, n_lat, n_lon)
        obs_data: np.ndarray,   # shape: (n_times,) velocitats observades
        wrf_at_obs_locations: np.ndarray  # shape: (n_times, n_points)
    ):
        """
        Crea model de calibració WRF
        
        Aprèn correccions entre sortida WRF i observacions
        """
        # Features: WRF a ubicacions d'observació + components U, V
        X = wrf_at_obs_locations  # (n_times, n_points)
        y = obs_data  # (n_times,)
        
        # Normalitzar
        self.scaler = {
            'mean': X.mean(axis=0),
            'std': X.std(axis=0) + 1e-8,
            'y_mean': y.mean(),
            'y_std': y.std() + 1e-8
        }
        
        X_norm = (X - self.scaler['mean']) / self.scaler['std']
        y_norm = (y - self.scaler['y_mean']) / self.scaler['y_std']
        
        # Xarxa neuronal
        model = nn.Sequential(
            nn.Linear(X.shape[1], 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # Entrenar
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.MSELoss()
        
        X_t = torch.FloatTensor(X_norm)
        y_t = torch.FloatTensor(y_norm.reshape(-1, 1))
        
        model.train()
        for epoch in range(500):
            optimizer.zero_grad()
            pred = model(X_t)
            loss = criterion(pred, y_t)
            loss.backward()
            optimizer.step()
        
        self.model = model
        return model
    
    def apply_calibration(
        self,
        wrf_field: np.ndarray,
        wrf_at_locations: np.ndarray
    ) -> np.ndarray:
        """
        Aplica calibració a camp de vent sencer
        
        Args:
            wrf_field: camp original (n_lat, n_lon)
            wrf_at_locations: valors WRF a punts de calibració
            
        Returns:
            Camp de vent calibrat
        """
        if self.model is None:
            raise ValueError("Model no entrenat")
        
        self.model.eval()
        
        # Normalitzar input
        X = (wrf_at_locations - self.scaler['mean']) / self.scaler['std']
        X_t = torch.FloatTensor(X.reshape(1, -1))
        
        # Predir factor de correcció
        with torch.no_grad():
            correction = self.model(X_t).numpy()[0, 0]
        
        # Aplicar correcció global
        # Simplificat: correcció global constant
        calibrated = wrf_field * (1 + correction * 0.1)
        
        return calibrated


def calculate_mean_wind(
    wind_speeds: np.ndarray,
    wind_directions: np.ndarray,
    method: str = "vectorial"
) -> dict:
    """
    Calcula el vent mig de diverses maneres
    
    Args:
        wind_speeds: array de velocitats (m/s)
        wind_directions: array de direccions (graus)
        method: 'scalar', 'vectorial', 'weibull_fit'
    
    Returns:
        Dict amb resultats
    """
    if method == "scalar":
        mean_speed = np.mean(wind_speeds)
        mean_dir = np.mean(wind_directions)
    
    elif method == "vectorial":
        # Mitjana vectorial (correcta per dades cícliques)
        u = -wind_speeds * np.sin(np.deg2rad(wind_directions))  # component E
        v = -wind_speeds * np.cos(np.deg2rad(wind_directions))  # component N
        
        u_mean = np.mean(u)
        v_mean = np.mean(v)
        
        mean_speed = np.sqrt(u_mean**2 + v_mean**2)
        mean_dir = (np.arctan2(-u_mean, -v_mean) * 180 / np.pi) % 360
    
    elif method == "weibull_fit":
        # Ajustar distribució Weibull
        from scipy import stats
        
        # MLE per Weibull
        shape, loc, scale = stats.weibull_min.fit(wind_speeds, floc=0)
        
        mean_speed = scale * np.math.gamma(1 + 1/shape)
        a = scale * np.math.gamma(1 + 1/shape)
        
        # Direcció predominant
        mean_dir = np.median(wind_directions)
    
    return {
        "mean_speed_ms": mean_speed,
        "mean_direction_deg": mean_dir,
        "std_speed_ms": np.std(wind_speeds),
        "method": method
    }
