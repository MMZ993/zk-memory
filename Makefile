.PHONY: test test-cli \
        test-integration test-integration-down \
        test-integration-postgres test-integration-postgres-down \
        test-integration-auth test-integration-auth-down

# Python unit tests (no external services required)
test:
	pytest tests/test_services/ tests/test_api/ -v

# Go unit tests for the CLI client layer
test-cli:
	cd cli && go test ./...

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

# Auth integration tests — API with all five MEMORY_API_KEY_* scopes configured (port 8003)
# Builds the CLI binary before running, so CLI subprocess tests work.
# Requires Ollama running on the host with nomic-embed-text pulled.
test-integration-auth:
	docker compose -f docker-compose.test.auth.yml up -d --build
	cd cli && go build -o dist/memory .
	INTEGRATION_TESTS=1 AUTH_TESTS=1 AUTH_API_URL=http://localhost:8003 pytest tests/integration/test_auth.py -v; \
	docker compose -f docker-compose.test.auth.yml down -v

# Tear down the auth test stack without running tests (cleanup after failure)
test-integration-auth-down:
	docker compose -f docker-compose.test.auth.yml down -v
