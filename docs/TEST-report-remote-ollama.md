# Test Report: Remote Ollama Validation

## Scope

Validate that the remote Ollama endpoint can be used for embeddings in this project and is suitable for integration testing.

- Remote endpoint: `https://ollama.mmz.sh`
- Embedding model: `nomic-embed-text:latest`

## Checks Performed

1. **Service availability**
   - `GET /api/version`
   - Result: success (`0.19.0`)

2. **Model availability**
   - `GET /api/tags`
   - Result: `nomic-embed-text:latest` is present

3. **Model pull operation**
   - `POST /api/pull` with `{"name":"nomic-embed-text:latest","stream":false}`
   - Result: success

4. **Embedding generation**
   - `POST /api/embed` with a test input string
   - Result: success, valid embedding vector returned

## Outcome

Remote Ollama is operational and can be used for embedding-based tests.

## Test Stack File

A dedicated compose file is included for this setup:

- `docker-compose.test.remote-ollama.yml`

It configures the API container to use:

- `OLLAMA_HOST=https://ollama.mmz.sh`
- `EMBEDDING_MODEL=nomic-embed-text`

## Suggested Run

1. Start stack:

```bash
docker compose -f docker-compose.test.remote-ollama.yml up -d --build
```

2. Run integration tests:

```bash
INTEGRATION_TESTS=1 uv run pytest tests/integration/ -v
```

3. Shutdown stack:

```bash
docker compose -f docker-compose.test.remote-ollama.yml down -v
```
