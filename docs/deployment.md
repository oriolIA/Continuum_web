# HOWTO: Desplegar Continuum Web

## Requisits

| Component | Versió mínima |
|-----------|--------------|
| Docker | 20.10 |
| Docker Compose | 2.0 |
| RAM | 4 GB |
| Disc | 10 GB |

## Pas 1: Instal·lar Docker (Linux)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Fer logout/login
```

## Pas 2: Clonar repositori

```bash
git clone https://github.com/oriolIA/Continuum_web.git
cd Continuum_web
```

## Pas 3: Configurar

```bash
# Crear directori de dades
mkdir -p data

# Opcional: configurar variables d'entorn
cp .env.example .env
# Editar .env si cal
```

## Pas 4: Desplegar API

```bash
# Construir i iniciar
docker-compose up -d --build

# Verificar
docker-compose ps

# Logs
docker-compose logs -f continuum-api
```

## Pas 5: Frontend

Obrir el frontend:

```bash
# Amb Python
python3 serve_frontend.py

# Obrir: http://localhost:8080
```

O directament: obrir `frontend/index.html` al navegador.

## Pas 6: Verificar

```bash
# Health check API
curl http://localhost:8000/health

# Documentació API
# Obrir: http://localhost:8000/docs
```

## Comandes útils

| Acció | Comanda |
|-------|---------|
| Aturar | `docker-compose down` |
| Reiniciar | `docker-compose restart` |
| Actualitzar | `docker-compose pull && docker-compose up -d` |
| Veure logs | `docker-compose logs -f` |

## Accés

| Servei | URL |
|--------|-----|
| API REST | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| **Frontend Web** | http://localhost:8080 |

## Resoldre problemes

```bash
# Error de permisos
sudo chmod -R 755 data/

# Error de memòria
docker-compose down

# Reconstruir imatge
docker-compose build --no-cache
```

## Producció

Per a producció, canviar:
- `docker-compose.yml`: Afegir reverse proxy (nginx)
- Secrets: No hardcodar contrasenyes
- SSL: Configurar certbot
