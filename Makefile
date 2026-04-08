.PHONY: help install run test clean lint format

help:
	@echo "Price-It - Available commands:"
	@echo ""
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run the API server"
	@echo "  make test       - Run tests"
	@echo "  make test-api   - Test API with sample address"
	@echo "  make cli        - Run interactive CLI"
	@echo "  make discord    - Run Discord bot"
	@echo "  make clean      - Clean cache files"
	@echo ""

install:
	pip install -r requirements.txt

run:
	python src/main.py

test:
	pytest tests/ -v

test-api:
	python scripts/test_api.py

cli:
	python scripts/cli.py -i

discord:
	python src/chatbot/discord_bot.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

lint:
	ruff check src/ scripts/
	mypy src/

format:
	ruff format src/ scripts/
