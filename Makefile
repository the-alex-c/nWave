PLATFORM ?= pi

.PHONY: test install upgrade

test:
	uv run --extra test pytest tests $(ARGS)

install:
	pipx install --force .

upgrade: install
	nwave-ai install --platform $(PLATFORM)
