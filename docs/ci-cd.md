# CI/CD Contract

## Pipeline Stages

The GitLab pipeline runs in this order:

1. `verify`
   - `python_tests`
   - `cli_tests`
2. `integration`
   - `integration_postgres`
3. `build`
   - `build_cli_artifact`
4. `publish`
   - `publish_image`
   - `publish_cli_package` (tag pipelines)

## Required Runner Capabilities

- Docker engine access (`docker ps` works)
- Docker Compose plugin (`docker compose version`)
- `uv` installed and usable
- Go toolchain installed
- Outbound network access to the configured Ollama endpoint

## Container Registry Output

The `publish_image` job pushes:

- Immutable image tag: `$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA`
- Branch convenience tag: `$CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG` (for branch pipelines)
- Git tag convenience tag: `$CI_REGISTRY_IMAGE:$CI_COMMIT_TAG` (for tag pipelines)

The job also exports a dotenv artifact (`build.env`) with:

- `IMAGE_REF`
- `IMAGE_TAG`
- `CLI_ARTIFACT_URL` (tag pipelines)

## CLI Artifact Output

The `build_cli_artifact` job publishes CI artifacts:

- `cli/dist/memory`
- `cli/dist/memory-cli-linux-amd64-<short_sha>.tar.gz`

Tag pipelines also upload the CLI tarball to GitLab Generic Package Registry:

- package: `memory-cli`
- version: `$CI_COMMIT_TAG`
- file: `memory-cli-linux-amd64-$CI_COMMIT_TAG.tar.gz`

## Integration Test Stack

`integration_postgres` uses `docker-compose.test.postgres.yml` and runs:

- API + PostgreSQL + Qdrant stack
- Python integration suite excluding auth tests
- CLI smoke script: `scripts/ci_smoke.sh`

`OLLAMA_HOST` is configurable and defaults to `https://ollama.mmz.sh` in CI.

## Downstream Deploy Contract (homelab-services)

Deploy consumers should use the immutable image from `IMAGE_REF`.

Minimum deploy input:

- `IMAGE_REF`
- target environment (`uat` or `prod`)

Recommended flow:

1. Backup target data.
2. Pull and deploy `IMAGE_REF`.
3. Run post-deploy health + smoke checks.
