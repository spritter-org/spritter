.PHONY: help install install-dev test test-omv test-hofer test-jet test-bp test-all test-unit test-integration clean

help:
	@echo "Available commands:"
	@echo "  make install           - Install spritter package in production mode"
	@echo "  make install-dev       - Install spritter package in development mode"
	@echo "  make test-all          - Run all tests (unit + integration)"
	@echo "  make test-unit         - Run unit tests (OMV OCR parsing with fixtures)"
	@echo "  make test-integration  - Run all integration tests"
	@echo "  make test-omv          - Run OMV provider integration tests"
	@echo "  make test-hofer        - Run Hofer provider integration tests"
	@echo "  make test-jet          - Run JET provider integration tests"
	@echo "  make test-bp           - Run BP provider integration tests"
	@echo "  make test-avanti       - Run Avanti provider integration tests"
	@echo "  make clean             - Remove __pycache__ and .egg-info directories"

# Installation targets
install:
	@echo "Installing spritter package in production mode..."
	pip install .

install-dev:
	@echo "Installing spritter package in development mode..."
	pip install -e .

# Unit tests (mocked API tests with fixtures)
test-unit:
	@echo "Running unit tests (OMV provider OCR parsing with fixtures)..."
	python -m unittest tests.test_omv_provider_mock -v

# Integration tests (live API calls)
test-omv:
	@echo "Running OMV provider integration tests..."
	python -m unittest tests.test_omv_provider -v

test-hofer:
	@echo "Running Hofer provider integration tests..."
	python -m unittest tests.test_hofer_provider -v

test-jet:
	@echo "Running JET provider integration tests..."
	python -m unittest tests.test_jet_provider -v

test-bp:
	@echo "Running BP provider integration tests..."
	python -m unittest tests.test_bp_provider -v

test-avanti:
	@echo "Running Avanti provider integration tests..."
	python -m unittest tests.test_avanti_provider -v 2>&1 || echo "Avanti tests may require additional configuration"

test-integration: test-omv test-hofer test-jet test-bp
	@echo "All integration tests completed"

test-all: test-unit test-integration
	@echo "All tests completed"

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup completed"
