.PHONY: test test-integration test-integration-down \
        test-integration-postgres test-integration-postgres-down

# Unit tests (no external services required)
test:
	pytest tests/test_services/ tests/test_api/ -v

# Integration tests — SQLite + Qdrant stack (port 8001)
# Requires Ollama running on the host with nomic-embed-text pulled.
test-integration:
	docker compose -f docker-compose.test.yml up -d --build
	INTEGRATION_TESTS=1 pytest tests/integration/ -v; \
	docker compose -f docker-compose.test.yml down -v

# Tear down the SQLite test stack without running tests (cleanup after failure)
test-integration-down:
	docker compose -f docker-compose.test.yml down -v

# Integration tests — PostgreSQL + Qdrant stack (port 8002)
# Runs the same test suite against a real PostgreSQL database.
# Requires Ollama running on the host with nomic-embed-text pulled.
test-integration-postgres:
	docker compose -f docker-compose.test.postgres.yml up -d --build
	INTEGRATION_TESTS=1 MEMORY_API_URL=http://localhost:8002 pytest tests/integration/ -v; \
	docker compose -f docker-compose.test.postgres.yml down -v

# Tear down the PostgreSQL test stack without running tests (cleanup after failure)
test-integration-postgres-down:
	docker compose -f docker-compose.test.postgres.yml down -v
