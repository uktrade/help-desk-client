# helpdesk-client

A Python client for interfacing with helpdesk services.

## Requirements

- [poetry](https://python-poetry.org)

## Setup local development

1. `poetry install`

## Run tests

1. `make test`

## Create a PyPI release (and create tag)

* Merge PR into main (making sure you have bumped the version in the .toml)

* Pull the main branch to your machine

* `git tag [new version #]`

* `git push origin --tags`

* `make publish`
