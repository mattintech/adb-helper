.PHONY: clean clean-build clean-pyc clean-test test install build upload help

help:
	@echo "Available commands:"
	@echo "  make clean        - Remove all build, test, coverage and Python artifacts"
	@echo "  make test         - Run tests"
	@echo "  make install      - Install the package locally in development mode"
	@echo "  make build        - Build source and wheel packages"
	@echo "  make upload       - Upload to PyPI (production)"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

clean-test:
	rm -rf .tox/
	rm -f .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache

test:
	python -m pytest tests/

install:
	pip install -e .

build: clean
	python -m pip install --upgrade build
	python -m build

upload: build
	python -m pip install --upgrade twine
	python -m twine upload dist/*

check:
	python -m pip install --upgrade twine
	python -m twine check dist/*

test-install: clean
	python -m venv test-env
	./test-env/bin/pip install -e .
	@echo "Test installation complete. Activate with: source test-env/bin/activate"
	@echo "Then test with: adbhelper --help"