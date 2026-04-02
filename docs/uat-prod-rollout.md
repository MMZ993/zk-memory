# UAT/PROD Rollout Runbook

## Environments

- UAT host: deploys from `develop` image tags
- PROD host: deploys from approved `main`/release image tags

Both environments use `docker-compose.deploy.yml` with environment-specific `.env.deploy` files.

## Standard Rollout Sequence

1. Select immutable `IMAGE_REF` from CI (`build.env`)
2. Run backup on target host:
   - PostgreSQL data path
   - Qdrant data path
3. Pull and deploy:
   - `docker compose --env-file .env.deploy -f docker-compose.deploy.yml pull`
   - `docker compose --env-file .env.deploy -f docker-compose.deploy.yml up -d`
4. Run verification:
   - `/api/health`
   - `/api/readiness`
   - `scripts/ci_smoke.sh`

## Promotion Policy

1. Deploy candidate image to UAT
2. Execute smoke checks and manual query checks
3. Promote same `IMAGE_REF` to PROD

No rebuild is allowed between UAT and PROD promotion.

## Rollback Policy

1. Set previous known-good `IMAGE_REF`
2. Pull and redeploy compose
3. Re-run verification sequence

If rollback includes data restore, restore PostgreSQL and Qdrant from the pre-deploy backup made for that deployment.

## Backup Cadence

- Nightly scheduled backups for UAT/PROD data paths
- Mandatory pre-deploy backup before every rollout
- Keep retention policy managed by homelab-services backup jobs
