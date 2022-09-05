build:
	poetry build

publish: build
	poetry publish

run = poetry run

format:
	$(run) black .
	$(run) isort .

lint:
	$(run) black --check .
	$(run) isort --check .
	$(run) flake8 .
	$(run) mypy .

test:
	$(run) poetry run pytest tests -v
