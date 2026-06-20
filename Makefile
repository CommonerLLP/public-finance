# budget-crawler — common operations.
# `make help` lists everything.

VENV   := .venv
PYTHON := $(VENV)/bin/python

$(PYTHON):
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

.PHONY: test sync-agents audit clean hooks prune data-init data-link help

test: $(PYTHON)
	$(PYTHON) -m pytest tests/ -v

sync-agents: $(PYTHON)
	$(PYTHON) scripts/sync_agents.py

hooks:  ## Install git pre-commit hook (run once after clone)
	bash ../_org/scripts/install-hooks.sh

prune:  ## Delete local branches already merged into main
	git fetch --prune
	git branch --merged main | grep -vE '^\*|main' | xargs -r git branch -d

audit: $(PYTHON)
	$(VENV)/bin/pip-audit || true

clean:
	find . -name __pycache__ -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

help:
	@echo "budget-crawler operations:"
	@echo "  make test          — run pytest tests/ (write tests as you implement scrapers)"
	@echo "  make sync-agents   — regenerate CLAUDE.md + AGENTS.md from CONTEXT.md"
	@echo "  make audit         — run pip-audit on dependencies"
	@echo "  make clean         — drop __pycache__ and .pyc files"
	@echo "  make hooks         — install pre-commit hook into .git/hooks/"
	@echo "  make prune         — delete local branches merged into main"

data-init:  ## Create data/ as a real directory (default — no external drive needed)
	mkdir -p data

data-link:  ## Symlink data/ to external storage: make data-link EXTERNAL=/path/to/external-drive
	@test -n "$(EXTERNAL)" || (echo "Usage: make data-link EXTERNAL=/path/to/external-drive"; exit 1)
	mkdir -p $(EXTERNAL)/$(shell basename $(CURDIR))/data
	ln -sfn $(EXTERNAL)/$(shell basename $(CURDIR))/data data
	@echo "data/ -> $(EXTERNAL)/$(shell basename $(CURDIR))/data"
