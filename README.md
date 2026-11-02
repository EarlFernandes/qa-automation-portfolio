# QA automation portfolio

[![CI](https://github.com/EarlFernandes/qa-automation-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/EarlFernandes/qa-automation-portfolio/actions/workflows/ci.yml)
[![JMeter](https://github.com/EarlFernandes/qa-automation-portfolio/actions/workflows/jmeter.yml/badge.svg)](https://github.com/EarlFernandes/qa-automation-portfolio/actions/workflows/jmeter.yml)
![Playwright 1.63](https://img.shields.io/badge/Playwright-1.63-45ba4b)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![License MIT](https://img.shields.io/badge/License-MIT-lightgrey)

Sample test code by **Earl Fernandes**, Senior QA Engineer and SDET. Every suite in this repository runs against a public demo site or a public API, so anyone can clone it and run it. The code shows the patterns I use at work: page objects with fixtures, a strict locator strategy, contract tests from JSON Schema files, a parameterized load test, and a release gate for an LLM feature that scores a model against a golden dataset in CI.

Nothing here comes from an employer. All data, targets and names are public or synthetic.

## Start here

If you have five minutes, read these in order:

1. [`playwright/src/fixtures/test.ts`](playwright/src/fixtures/test.ts) and [`playwright/tests/checkout.spec.ts`](playwright/tests/checkout.spec.ts). Page objects arrive through fixtures, tests read like a user story, and the totals math is asserted in cents.
2. [`llm-evals/src/llm_evals/scoring.py`](llm-evals/src/llm_evals/scoring.py) and [`llm-evals/gate.yaml`](llm-evals/gate.yaml). How an LLM output is scored field by field, and how a metric earns the right to block a release.
3. [`.github/workflows/ci.yml`](.github/workflows/ci.yml). All four suites run on every push. The eval gate runs after the unit tests and fails the build when a blocking metric drops.

## What is inside

| Folder | Stack | What it shows | Size |
| --- | --- | --- | --- |
| [`playwright/`](playwright/) | TypeScript, Playwright 1.63, ESLint | Page objects plus fixtures, `data-test` locators, sign-in once with `storageState`, aria snapshots, tags, network control, desktop and mobile projects | 68 tests |
| [`selenium/`](selenium/) | Python, Selenium 4, pytest | Classic page object model with explicit waits, Selenium Manager, screenshots on failure, data-driven login | 13 tests |
| [`api-tests/`](api-tests/) | Python, pytest, httpx, JSON Schema | Contract tests for a REST API and a GraphQL API, auth token flow, pagination math, negative cases, response time checks | 19 tests |
| [`jmeter/`](jmeter/) | Apache JMeter 5.6 | Parameterized load plan with CSV data, JSON extraction, assertions and a non GUI run script that builds the HTML dashboard | 4 samplers |
| [`llm-evals/`](llm-evals/) | Python, pydantic 2 | Golden dataset, field accuracy with numeric tolerance, completeness, schema conformance, line item matching, heuristic judge, HTML and JUnit reports, CI release gate with a promotion policy | 14 cases, 30 unit tests |

Targets: [saucedemo.com](https://www.saucedemo.com) for the browser suites, [dummyjson.com](https://dummyjson.com) and [countries.trevorblades.com](https://countries.trevorblades.com) for the API and load tests. The eval harness runs offline with a rule-based extractor and has reference adapters for OpenAI and Anthropic models.

## How the parts fit together

```mermaid
flowchart TB
    CI["GitHub Actions: ci.yml<br/>runs on every push and pull request"]
    CI --> PW & SE & CT & EV
    subgraph UI["Browser tests"]
        PW["Playwright<br/>TypeScript"]
        SE["Selenium<br/>Python"]
    end
    subgraph API["API tests"]
        CT["Contract tests<br/>pytest + JSON Schema"]
        JM["Load test<br/>JMeter, manual workflow"]
    end
    subgraph AI["AI quality"]
        EV["LLM evals<br/>golden dataset + scoring"] --> GT["Release gate<br/>fails the build when a blocking metric drops"]
    end
    PW & SE --> SITE["saucedemo.com"]
    CT & JM --> DJ["dummyjson.com<br/>countries GraphQL"]
```

More diagrams, including the Playwright fixture graph and the eval pipeline, are in [`docs/architecture.md`](docs/architecture.md).

## Quick start

Each folder has a README with the full commands. The short version:

```bash
# Playwright (Node 22)
cd playwright && npm ci && npx playwright install --with-deps chromium && npx playwright test

# Selenium (Python 3.11+, Chrome installed)
cd selenium && pip install -r requirements.txt && python -m pytest

# API contract tests
cd api-tests && pip install -r requirements.txt && python -m pytest

# LLM evals: unit tests, eval run, release gate
cd llm-evals && pip install -e ".[dev]" && python -m pytest
llm-evals run --dataset data/golden.jsonl --extractor regex --out reports/
llm-evals gate --results reports/results.json --config gate.yaml --history reports/gate_history.json

# JMeter (Java 17 and Apache JMeter 5.6)
cd jmeter && ./run.sh
```

A `Makefile` at the root wraps the same commands: `make playwright`, `make selenium`, `make api`, `make evals`, `make jmeter`.

## Principles I follow

**Locators.** Prefer what the user sees: `getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`. Then a dedicated test attribute (`data-test` here). Never XPath, never CSS tied to styling classes. The Selenium suite follows the same order with locator tuples.

**Page objects plus fixtures.** Page objects hold locators and actions. Fixtures build them and hand them to tests, so tests have no setup noise. Sign-in happens once in a setup project and every test starts signed in through `storageState`.

**No sleeps.** Every wait is for a condition: a URL, a visible element, a text value. Flaky tests are fixed at the cause and the fix is explained in a comment.

**Contracts as files.** API shapes live in JSON Schema files next to the tests, so a schema change is a reviewable diff.

**Evals are tests.** An LLM feature gets a golden dataset, metrics with thresholds, and a gate in CI. A new metric starts as a candidate and becomes blocking only after it passes in two consecutive runs. The answer key is never edited to make a run pass.

**Small load, real signal.** The load plan runs against a public API, so the default profile is tiny. The point is the plan design: parameters from properties, data from CSV, token extraction, assertions, and a dashboard you can read.

## CI

[`ci.yml`](.github/workflows/ci.yml) runs four jobs in parallel on every push and pull request: Playwright, Selenium, API tests, and the LLM eval run followed by the gate. Each job uploads its report as an artifact. The gate history is cached between runs so the promotion policy works in CI too. [`jmeter.yml`](.github/workflows/jmeter.yml) runs by hand with the user count and loop count as inputs.

## About me

Senior QA Engineer and SDET with 8+ years in test automation, API testing, performance testing and release quality, now focused on quality for AI and LLM products. Open to remote roles.

- LinkedIn: [linkedin.com/in/earl-a-5434b02a8](https://www.linkedin.com/in/earl-a-5434b02a8)
- Email: earlspen2001@gmail.com

## License

MIT. See [`LICENSE`](LICENSE).
