.PHONY: test test-integration test-integration-down

# Unit tests (no external services required)
test:
	pytest tests/test_services/ tests/test_api/ -v

# Integration tests against Docker test stack.
# Starts the stack, runs tests, tears it down.
# Requires Ollama running on the host with nomic-embed-text pulled.
test-integration:
	docker compose -f docker-compose.test.yml up -d --build
	INTEGRATION_TESTS=1 pytest tests/integration/ -v; \
	docker compose -f docker-compose.test.yml down -v

# Tear down the test stack without running tests (cleanup after failure)
test-integration-down:
	docker compose -f docker-compose.test.yml down -v
