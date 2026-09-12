.PHONY: help install test clean

help:
	@echo "Available commands:"
	@echo "  make install           - Install spritter package in production mode"
	@echo "  make test              - Run all tests"
	@echo "  make clean             - Remove __pycache__ and .egg-info directories"

install:
	@echo "Installing spritter"
	pip install -e .

test:
	@echo "Running all tests..."
	python -m unittest discover -s tests -p "test_*.py" -v

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup completed"
