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
	# TODO - reinstate $(run) mypy . --exclude '/zenpy$'

test:
	$(run) pytest tests -v
