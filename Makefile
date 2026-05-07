CONDA_ENV  := pbrecipe
PHP_TEST_DB := /tmp/pbrecipe_php_test.db
ifdef NOCONDA
CONDA_RUN  :=
else
CONDA_RUN  := conda run -n $(CONDA_ENV) --no-capture-output
endif
SRC        := src

ICON_SRC   := src/pbrecipe/resources/icons/pbrecipe-512x512.png
ICON_ICO   := src/pbrecipe/resources/icons/pbrecipe.ico
ICON_ICNS  := src/pbrecipe/resources/icons/pbrecipe.icns

R  := \033[0m
B  := \033[1m
G  := \033[32m
Y  := \033[33m
C  := \033[36m

PY_SOURCES := $(shell find $(SRC)/pbrecipe -name "*.py" ! -path "*/__pycache__/*")

.DEFAULT_GOAL := help
.PHONY: all help icons venv venv-update install run test test-php coverage lint format \
        dist clean hooks

all: icons ## Génère tous les artefacts (icônes)

icons: $(ICON_ICO) $(ICON_ICNS) ## Génère .ico et .icns depuis le PNG source

$(ICON_ICO) $(ICON_ICNS): $(ICON_SRC)
	@printf "$(C)Génération des icônes depuis $<...$(R)\n"
	$(CONDA_RUN) python tools/make_icons.py $(ICON_SRC) $(ICON_ICO) $(ICON_ICNS)
	@printf "$(G)Icônes générées.$(R)\n"

help: ## This help (default target)
	@printf "$(B)$(C)PBRecipe — Development Tasks$(R)\n\n"
	@printf "$(Y)Usage:$(R) make $(G)<target>$(R)\n\n"
	@printf "$(Y)Targets:$(R)\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS=":.*?## "}; {printf "  $(G)%-14s$(R) %s\n", $$1, $$2}'
	@printf "\n$(Y)Variables:$(R)\n"
	@printf "  $(G)NOCONDA$(R)        Bypass conda wrapping; tools must be on PATH\n"
	@printf "                 e.g. $(C)make test NOCONDA=1$(R)  or  $(C)export NOCONDA=1$(R)\n"

venv: ## Create conda env 'pbrecipe' from environment.yml
	@printf "$(C)Creating conda environment '$(CONDA_ENV)'...$(R)\n"
	conda env create -f environment.yml
	@printf "$(G)Done! Activate with:$(R) conda activate $(CONDA_ENV)\n"

venv-update: ## Update existing conda env from environment.yml
	@printf "$(C)Updating conda environment '$(CONDA_ENV)'...$(R)\n"
	conda env update -f environment.yml --prune
	@printf "$(G)Done.$(R)\n"

install: ## Install package in editable mode and register git hooks
	$(CONDA_RUN) pip install -e ".[dev]"
	$(CONDA_RUN) pre-commit install

run: ## Launch PBRecipe from the conda env
	$(CONDA_RUN) python -m pbrecipe

test: ## Run Python test suite
	$(CONDA_RUN) pytest

test-php: ## Run PHP test suite (télécharge composer/phpunit si nécessaire)
	@test -f composer.phar || { \
	    $(CONDA_RUN) php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');" && \
	    $(CONDA_RUN) php composer-setup.php --quiet && \
	    rm -f composer-setup.php; \
	}
	@test -f vendor/bin/phpunit || $(CONDA_RUN) php composer.phar install --no-interaction --quiet
	PBRECIPE_TEST_DB=$(PHP_TEST_DB) $(CONDA_RUN) pytest tests/test_php_fixtures.py
	PBRECIPE_TEST_DB=$(PHP_TEST_DB) $(CONDA_RUN) ./vendor/bin/phpunit

coverage: ## Run test suite and open HTML coverage report
	$(CONDA_RUN) pytest --cov-report=term-missing --cov-report=html
	@printf "$(G)Report:$(R) $(Y)htmlcov/index.html$(R)\n"

hooks: ## Run all pre-commit hooks on all files
	$(CONDA_RUN) pre-commit run --all-files

lint: ## Check code style
	$(CONDA_RUN) ruff check $(SRC)
	$(CONDA_RUN) ruff format --check $(SRC)

format: ## Auto-format source code
	$(CONDA_RUN) ruff format $(SRC)
	$(CONDA_RUN) ruff check --fix $(SRC)

designer: ## Launch Qt Designer
	$(CONDA_RUN) pyside6-designer

dist: ## Build a standalone executable for the current platform
	@printf "$(C)PyInstaller — platform: $(shell $(CONDA_RUN) python -c 'import sys; print(sys.platform)')$(R)\n"
	$(CONDA_RUN) pyinstaller --clean --noconfirm \
	    --distpath dist --workpath build/pyinstaller \
	    pbrecipe.spec
	@printf "$(G)Done.$(R) Executable in $(Y)dist/$(R)\n"

clean: ## Remove all build/cache artifacts
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov vendor composer.phar
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
