# Convenience targets. Each part also documents its own commands in its README.
.PHONY: help playwright playwright-smoke selenium api evals evals-run evals-gate jmeter clean

help:
	@echo "make playwright        Run the Playwright suite (chromium and mobile-chrome)"
	@echo "make playwright-smoke  Run only tests tagged @smoke"
	@echo "make selenium          Run the Selenium suite"
	@echo "make api               Run the API contract tests"
	@echo "make evals             Unit tests, eval run and release gate for llm-evals"
	@echo "make jmeter            Run the JMeter smoke profile (needs jmeter or JMETER_HOME)"
	@echo "make clean             Remove reports, caches and build output"

playwright:
	cd playwright && npm ci && npx playwright test

playwright-smoke:
	cd playwright && npm ci && npx playwright test --grep @smoke

selenium:
	cd selenium && pip install -r requirements.txt && python -m pytest

api:
	cd api-tests && pip install -r requirements.txt && python -m pytest

evals: evals-run evals-gate

evals-run:
	cd llm-evals && pip install -e ".[dev]" && python -m pytest && \
	llm-evals run --dataset data/golden.jsonl --extractor regex --out reports/

evals-gate:
	cd llm-evals && llm-evals gate --results reports/results.json --config gate.yaml --history reports/gate_history.json

jmeter:
	cd jmeter && ./run.sh

clean:
	rm -rf playwright/node_modules playwright/test-results playwright/playwright-report playwright/results playwright/.auth
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -prune -exec rm -rf {} +
	rm -rf selenium/results/*.xml selenium/results/screenshots/*.png api-tests/results/*.xml
	rm -rf llm-evals/reports/*.json llm-evals/reports/*.xml llm-evals/reports/*.html llm-evals/src/*.egg-info
	find jmeter/results -mindepth 1 ! -name .gitkeep -exec rm -rf {} +
