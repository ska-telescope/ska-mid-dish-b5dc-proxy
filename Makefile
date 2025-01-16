include .make/base.mk
include .make/python.mk

DOCS_SPHINXOPTS = -n -W --keep-going

docs-pre-build:
	poetry config virtualenvs.create false
	poetry install --no-root --only docs

.PHONY: docs-pre-build

PYTHON_LINE_LENGTH = 88

.PHONY: docs-pre-build python-post-lint
