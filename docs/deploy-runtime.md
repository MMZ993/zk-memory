# Deployment Runtime Contract

## Compose Files

- `docker-compose.deploy.yml`: image-based deployment stack for UAT/PROD
- `.env.deploy.example`: required environment contract template

## Required Inputs

- `IMAGE_REF`: immutable container image reference from CI
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `OLLAMA_HOST`

## Data Paths

The deploy compose supports host bind paths through environment variables:

- `APP_DATA_DIR`
- `POSTGRES_DATA_DIR`
- `QDRANT_DATA_DIR`

These should map to persistent storage on the deployment host.

## Deployment Command

```bash
docker compose --env-file .env.deploy -f docker-compose.deploy.yml pull
docker compose --env-file .env.deploy -f docker-compose.deploy.yml up -d
```

## Pre-Deploy and Post-Deploy Checks

Pre-deploy:

1. Backup `POSTGRES_DATA_DIR` and `QDRANT_DATA_DIR`
2. Verify `IMAGE_REF` exists in registry

Post-deploy:

1. `GET /api/health`
2. `GET /api/readiness`
3. Run `scripts/ci_smoke.sh` against the deployed endpoint

## Rollback

Rollback is image-tag based:

1. Set previous known-good `IMAGE_REF`
2. Run compose pull/up again
3. Re-run health/readiness/smoke checks
