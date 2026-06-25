CONDA_ENV  := pbrecipe
PHP_TEST_DB := /tmp/pbrecipe_php_test.db
ifdef NOCONDA
CONDA_RUN  :=
else
CONDA_RUN  := conda run -n $(CONDA_ENV) --no-capture-output
endif
SRC        := src
DOCS       := docs

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
        dist srcdist clean hooks update-vendors _php-vendor \
        bump-release bump-year bump-set \
        docs docs-live

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

ARGS ?=
run: ## Launch PBRecipe from the conda env  (pass extra args with ARGS="--debug …")
	$(CONDA_RUN) python -m pbrecipe $(ARGS)

test: ## Run Python test suite
	$(CONDA_RUN) pytest

_php-vendor:
	@test -f composer.phar || { \
	    $(CONDA_RUN) php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');" && \
	    $(CONDA_RUN) php composer-setup.php --quiet && \
	    rm -f composer-setup.php; \
	}
	@test -f vendor/bin/phpunit || $(CONDA_RUN) php composer.phar install --no-interaction --quiet

test-php: _php-vendor ## Run PHP test suite (télécharge composer/phpunit si nécessaire)
	PBRECIPE_TEST_DB=$(PHP_TEST_DB) $(CONDA_RUN) pytest tests/test_php_fixtures.py
	PBRECIPE_TEST_DB=$(PHP_TEST_DB) $(CONDA_RUN) ./vendor/bin/phpunit

coverage: _php-vendor ## Run test suite and open HTML coverage report
	PBRECIPE_TEST_DB=$(PHP_TEST_DB) $(CONDA_RUN) pytest --cov-report=term-missing --cov-report=html
	# Couverture PHP : nécessite Xdebug ou PCOV.
	# PHP 8.5 (conda-forge) n'est pas encore supporté par Xdebug/PCOV ; on bascule
	# sur le PHP système (ex. 8.3 + php-xdebug via apt) si disponible.
	# Quand Xdebug/PCOV supporteront PHP 8.5, remplacer les deux branches elif/else
	# par une seule invocation conda : $(CONDA_RUN) ./vendor/bin/phpunit --coverage-html htmlcov/php
	@if $(CONDA_RUN) php -r 'exit(extension_loaded("xdebug") || extension_loaded("pcov") ? 0 : 1);' 2>/dev/null; then \
		PBRECIPE_TEST_DB=$(PHP_TEST_DB) $(CONDA_RUN) ./vendor/bin/phpunit --coverage-html htmlcov/php; \
		printf "$(G)Report PHP:$(R)    $(Y)htmlcov/php/index.html$(R)\n"; \
	elif php -r 'exit(extension_loaded("xdebug") || extension_loaded("pcov") ? 0 : 1);' 2>/dev/null; then \
		XDEBUG_MODE=coverage PBRECIPE_TEST_DB=$(PHP_TEST_DB) php ./vendor/bin/phpunit --coverage-html htmlcov/php; \
		printf "$(G)Report PHP:$(R)    $(Y)htmlcov/php/index.html$(R)\n"; \
	else \
		printf "$(Y)Couverture PHP ignorée$(R) : aucun driver disponible (Xdebug ou PCOV requis).\n"; \
		PBRECIPE_TEST_DB=$(PHP_TEST_DB) $(CONDA_RUN) ./vendor/bin/phpunit; \
	fi
	@printf "$(G)Report Python:$(R) $(Y)htmlcov/index.html$(R)\n"

hooks: ## Run all pre-commit hooks on all files
	$(CONDA_RUN) pre-commit run --all-files

lint: ## Check code style
	$(CONDA_RUN) ruff check $(SRC)
	$(CONDA_RUN) ruff format --check $(SRC)

format: ## Auto-format source code
	$(CONDA_RUN) ruff format $(SRC)
	$(CONDA_RUN) ruff check --fix $(SRC)

dist: ## Build a standalone executable for the current platform (pbrecipe-version-os-arch)
	$(eval _VER  := $(shell bash tools/git_version.sh))
	$(eval _OS   := $(shell uname -s | tr A-Z a-z | sed 's/darwin/macos/'))
	$(eval _ARCH := $(shell uname -m))
	@printf "$(C)PyInstaller — version $(_VER), platform $(_OS)-$(_ARCH)$(R)\n"
	$(CONDA_RUN) pyinstaller --clean --noconfirm \
	    --distpath dist --workpath build/pyinstaller \
	    pbrecipe.spec
	mv dist/pbrecipe dist/pbrecipe-$(_VER)-$(_OS)-$(_ARCH)
	@printf "$(G)Done.$(R) Exécutable : $(Y)dist/pbrecipe-$(_VER)-$(_OS)-$(_ARCH)$(R)\n"

srcdist: ## Build a source distribution (archive dans dist/)
	$(eval _VER := $(shell bash tools/git_version.sh))
	@printf "$(C)Source distribution — version $(_VER)$(R)\n"
	$(CONDA_RUN) python -m build --sdist --outdir dist/
	@printf "$(G)Done.$(R) Archive dans $(Y)dist/$(R)\n"

update-vendors: ## Update vendored JS/CSS libraries (Tom Select, …)
	@printf "$(C)Updating vendored libraries...$(R)\n"
	@TS_VER=$$(curl -s https://api.github.com/repos/orchidjs/tom-select/releases/latest \
	    | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'].lstrip('v'))") && \
	printf "  Tom Select v$$TS_VER...\n" && \
	curl -sL "https://cdn.jsdelivr.net/npm/tom-select@$$TS_VER/dist/js/tom-select.complete.min.js" \
	    -o src/pbrecipe/resources/php/js/tom-select.min.js && \
	curl -sL "https://cdn.jsdelivr.net/npm/tom-select@$$TS_VER/dist/css/tom-select.min.css" \
	    -o src/pbrecipe/resources/php/css/tom-select.min.css
	@printf "$(G)Libraries updated.$(R)\n"

# ── Versioning ────────────────────────────────────────────────────────────────

bump-release: ## Bump release number (2026.5 → 2026.6)
	@$(CONDA_RUN) python tools/bump_version.py release

bump-year: ## New year, reset release to 1 (2026.5 → 2027.1)
	@$(CONDA_RUN) python tools/bump_version.py year

bump-set: ## Force a specific version (usage: make bump-set VERSION=2026.x)
	@test -n "$(VERSION)" || { \
	    printf "$(Y)Usage:$(R) make bump-set VERSION=<AAAA.x>\n"; exit 1; }
	@$(CONDA_RUN) python tools/bump_version.py set $(VERSION)

docs: ## Build HTML documentation
	$(CONDA_RUN) sphinx-build -b html $(DOCS) $(DOCS)/_build/html
	@printf "$(G)Open:$(R) $(DOCS)/_build/html/index.html\n"

docs-live: ## Build docs and watch for changes (hot reload)
	$(CONDA_RUN) sphinx-autobuild $(DOCS) $(DOCS)/_build/html

clean: ## Remove all build/cache artifacts
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov vendor composer.phar \
	    $(DOCS)/_build $(DOCS)/changelog.rst
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
