# HOWTO: Ús de Continuum Web

## Accés

| Servei | URL |
|--------|-----|
| API REST | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

## Exemple 1: Filtrar dades meteorològiques

```bash
curl -X POST "http://localhost:8000/met-filter/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"wind_speed": 8.5, "wind_direction": 270, "temperature": 15},
      {"wind_speed": 2.1, "wind_direction": 45, "temperature": -1}
    ],
    "remove_tower_shadow": true,
    "remove_ice": true,
    "target_height": 80
  }'
```

## Exemple 2: MCP (correlació d'estacions)

### MCP Clàssic
```bash
curl -X POST "http://localhost:8000/mcp/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_data": [
      {"wind_speed": 8.5, "wind_direction": 270},
      {"wind_speed": 7.2, "wind_direction": 280}
    ],
    "target_data": [
      {"wind_speed": 8.1, "wind_direction": 275},
      {"wind_speed": 6.9, "wind_direction": 278}
    ],
    "method": "orthogonal",
    "sectors": 12
  }'
```

### MCP Neural (Xarxa Neuronal)
```python
import httpx

async def neural_mcp():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/mcp/neural/train",
            json={
                "reference_data": [...],
                "target_data": [...],
                "hidden_layers": [64, 32, 16],
                "epochs": 500
            }
        )
        return response.json()
```

## Exemple 3: Calcular pèrdues de wake

```bash
curl -X POST "http://localhost:8000/wake/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "turbines": [
      {
        "name": "T1",
        "x": 0,
        "y": 0,
        "hub_height": 80,
        "rotor_diameter": 100,
        "ct": 0.8
      },
      {
        "name": "T2",
        "x": 300,
        "y": 0,
        "hub_height": 80,
        "rotor_diameter": 100,
        "ct": 0.8
      }
    ],
    "grid_resolution": 50,
    "sectors": 12
  }'
```

## Exemple 4: Disseny de Layout

### Crear layout en graella
```bash
curl -X POST "http://localhost:8000/layout/grid" \
  -H "Content-Type: application/json" \
  -d '{
    "n_rows": 5,
    "n_cols": 4,
    "spacing_x": 800,
    "spacing_y": 600,
    "staggered": true
  }'
```

### Optimitzar layout (Algorisme Genètic)
```bash
curl -X POST "http://localhost:8000/layout/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "n_turbines": 20,
    "min_x": 0,
    "max_x": 4000,
    "min_y": 0,
    "max_y": 3000,
    "method": "ga"
  }'
```

## Exemple 5: Vent Mig

```python
from src.calculations.neural_mcp import calculate_mean_wind

result = calculate_mean_wind(
    wind_speeds=np.array([5, 8, 12, 7]),
    wind_directions=np.array([270, 280, 290, 275]),
    method="vectorial"
)
print(result)
# {'mean_speed_ms': 8.0, 'mean_direction_deg': 278.5, ...}
```

## Python client example

```python
import httpx

async def run_mcp():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/mcp/analyze",
            json={
                "reference_data": [...],
                "target_data": [...],
                "method": "orthogonal"
            }
        )
        return response.json()
```

## Més informació

Vegeu [API Reference](api.md) per tots els endpoints.
