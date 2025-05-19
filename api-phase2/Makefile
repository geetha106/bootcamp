.PHONY: help install run api-run test clean docker-build docker-run watch-dir build-pkg publish-pkg docker-compose-up docker-compose-down

# API key for curl commands
API_KEY = figurex2023
API_URL = http://0.0.0.0:8000/api

help:
	@echo "Available commands:"
	@echo "  make install         - Install dependencies"
	@echo "  make run             - Run the watched directory processor"
	@echo "  make api-run         - Run the API server"
	@echo "  make test            - Run tests"
	@echo "  make clean           - Clean temporary files"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-run      - Run Docker container"
	@echo "  make build-pkg       - Build Python package"
	@echo "  make publish-pkg     - Publish package to PyPI"
	@echo "  make docker-compose-up   - Start services with docker-compose"
	@echo "  make docker-compose-down - Stop services with docker-compose"

install:
	pip install -r requirements.txt
	pip install watchdog

run:
	python watcher.py

# Legacy CLI commands for reference
cli-commands:
	@echo "Available CLI commands:"
	@echo "  python -m cli.cli ingest test.txt"
	@echo "  python -m cli.cli batch PMC7696669 29355051"
	@echo "  python -m cli.cli batch PMC7696669 29355051 --format csv"
	@echo "  python -m cli.cli batch PMC7696669 17299597 --format json"
	@echo "  python -m cli.cli batch PMC7696669 29355051 --output results.json"
	@echo "  python -m cli.cli reset"
	@echo "  python -m cli.cli reset --force"

api-run:
	python run_api.py

test:
	pytest tests/

clean:
	rm -rf __pycache__
	rm -rf */__pycache__
	rm -rf */*/__pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-build:
	docker build -t figurex:latest .

docker-run:
	docker run -p 8000:8000 figurex:latest

build-pkg: clean
	pip install --upgrade build
	python -m build

publish-pkg: build-pkg
	pip install --upgrade twine
	python -m twine upload dist/*

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down
