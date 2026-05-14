SHELL := /usr/bin/env bash

.PHONY: install demo demo-seed test lint clean

BACKEND_PY := backend/.venv/bin/python
UVICORN := backend/.venv/bin/uvicorn

ifneq (,$(wildcard ./.env))
include .env
export
endif

install:
	bash scripts/install.sh

demo:
	@if [ ! -x "$(UVICORN)" ]; then echo "Backend venv missing. Run: make install"; exit 1; fi
	@PYTHONPATH=backend "$(UVICORN)" app.main:app --host 0.0.0.0 --port 8000 > /tmp/circuitsage-backend.log 2>&1 & echo $$! > /tmp/circuitsage-backend.pid
	@sleep 2
	@open http://localhost:5173
	@npm --prefix frontend run dev

demo-seed:
	PYTHONPATH=backend "$(BACKEND_PY)" scripts/demo_seed.py

test:
	npm run test:backend
	npm --prefix frontend run build
	npm --prefix apps/desktop run check
	npm --prefix apps/ios run check

lint:
	@if command -v ruff >/dev/null 2>&1; then ruff check backend; else echo "ruff not installed; skipping Python lint"; fi
	cd frontend && npx tsc -b --noEmit
	npm --prefix apps/ios run check

clean:
	rm -rf backend/.venv node_modules frontend/node_modules frontend/dist apps/desktop/node_modules apps/desktop/dist apps/desktop/out apps/ios/node_modules apps/ios/.expo
