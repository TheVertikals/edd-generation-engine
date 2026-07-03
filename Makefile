.PHONY: test hooks
test:
	python3 -m pytest -q
hooks:
	@git config core.hooksPath .githooks && echo "pre-push gate enabled (.githooks/pre-push)"
