# Continuum Web - Python/FastAPI

Port del toolkit eòlic Continuum (C#) a Python/FastAPI

## 🌬️ Funcionalitats

| Mòdul | Descripció |
|-------|------------|
| **Met Filter** | Filtratge de dades meteorològiques |
| **MCP** | Measure-Correlate-Predict (clàssic + neural) |
| **Wake Modeling** | Jensen, Larsen models |
| **Layout Design** | Grid, Staggered, GA Optimization |
| **Neural MCP** | Xarxes neuronals per correlació |

## 🚀 Instal·lació

```bash
git clone https://github.com/oriolIA/Continuum_web.git
cd Continuum_web
docker-compose up -d
```

## 🌐 Frontend

Obre `frontend/index.html` al navegador:

```bash
# Amb Python
cd frontend
python3 -m http.server 8080
# Obrir: http://localhost:8080
```

## API Endpoints

| Endpoint | Mètode | Descripció |
|----------|--------|------------|
| `/health` | GET | Health check |
| `/met-filter/filter` | POST | Filtrar dades |
| `/mcp/analyze` | POST | MCP clàssic |
| `/wake/calculate` | POST | Calcular pèrdues |
| `/layout/grid` | POST | Crear layout |
| `/layout/optimize` POST | Optimitzar GA |

## Documentació

- [API Docs](http://localhost:8000/docs)
- [Deployment](docs/deployment.md)
- [Usage](docs/usage.md)
