PLATFORM ?= pi

.PHONY: test-py test-js install upgrade

test: test-py test-js

test-py:
	uv run --extra test pytest tests -n auto $(ARGS)

test-js:
	cd pi-code-nwave && npm install --no-audit --no-fund && npx vitest run $(ARGS)

install:
	pipx install --force .

upgrade: install
	nwave-ai install --platform $(PLATFORM)
