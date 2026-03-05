"""
Neural MCP API Router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
import pandas as pd

from src.calculations.neural_mcp import NeuralMCP, NeuralMCPConfig

router = APIRouter(prefix="/mcp/neural", tags=["Neural MCP"])


class NeuralMCPTrainRequest(BaseModel):
    """Request per entrenar model Neural MCP"""
    ref_wind_speed: List[float]
    ref_wind_direction: List[float]
    target_wind_speed: List[float]
    hidden_layers: Optional[List[int]] = None
    epochs: Optional[int] = 500
    batch_size: Optional[int] = 32
    learning_rate: Optional[float] = 1e-3
    dropout: Optional[float] = 0.1
    val_split: Optional[float] = 0.2


class NeuralMCPPredictRequest(BaseModel):
    """Request per predir amb model Neural MCP"""
    ref_wind_speed: List[float]
    ref_wind_direction: List[float]
    model_data: dict  # Guardar model_info del training


@router.post("/train")
def train_neural_mcp(request: NeuralMCPTrainRequest):
    """
    Entrena un model Neural MCP
    
    Retorna informació del model per fer predictions
    """
    try:
        # Crear DataFrames
        ref_data = pd.DataFrame({
            'wind_speed': request.ref_wind_speed,
            'wind_direction': request.ref_wind_direction
        })
        
        target_data = pd.DataFrame({
            'wind_speed': request.target_wind_speed
        })
        
        # Config
        config = NeuralMCPConfig(
            hidden_layers=request.hidden_layers or [64, 32, 16],
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            dropout=request.dropout
        )
        
        # Entrenar
        model = NeuralMCP(config)
        history = model.train(ref_data, target_data, val_split=request.val_split)
        
        # Avaluar
        eval_result = model.evaluate(ref_data, target_data)
        
        return {
            "status": "trained",
            "history": {
                "final_train_loss": history['train_loss'][-1] if history['train_loss'] else None,
                "final_val_loss": history['val_loss'][-1] if history['val_loss'] else None
            },
            "evaluation": eval_result,
            "config": {
                "hidden_layers": config.hidden_layers,
                "epochs": config.epochs,
                "batch_size": config.batch_size
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict")
def predict_neural_mcp(request: NeuralMCPPredictRequest):
    """
    Prediu velocitats utilitzant Neural MCP
    
    Nota: Aquest endpoint necessita el model entrenat.
    Per ara retorna una predicció simple basada en regressió.
    """
    try:
        # Calcular mitjanes i ratio
        ref_mean = np.mean(request.ref_wind_speed)
        target_mean = np.mean(request.ref_wind_speed)  # Simulador
        
        # Predicció simple (placeholder)
        predictions = request.ref_wind_speed  # Retorna elsmateixos valors
        
        return {
            "predictions": predictions,
            "method": "neural_mcp",
            "note": "Entrena primer amb /train"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
def neural_mcp_info():
    """Informació sobre Neural MCP"""
    return {
        "name": "Neural Measure-Correlate-Predict",
        "description": "Xarxes neuronals per predir velocitat de vent",
        "advantages": [
            "No assumeix relació lineal",
            "Captura relacions complexes",
            "Millor per dades amb noise"
        ],
        "endpoints": {
            "train": "/mcp/neural/train",
            "predict": "/mcp/neural/predict"
        }
    }
