# Architecture notes

This page explains how each suite is built and why. The diagrams render on GitHub.

## Repository map

```mermaid
flowchart TB
    ROOT["qa-automation-portfolio"]
    ROOT --> PW["playwright/<br/>TypeScript end-to-end suite"]
    ROOT --> SE["selenium/<br/>Python page object suite"]
    ROOT --> API["api-tests/<br/>pytest contract tests"]
    ROOT --> JM["jmeter/<br/>load test plan and run script"]
    ROOT --> EV["llm-evals/<br/>eval harness and release gate"]
    ROOT --> GH[".github/workflows/<br/>ci.yml and jmeter.yml"]
    ROOT --> DOCS["docs/<br/>this page"]
```

## Playwright suite

The suite signs in once, saves the browser state, and reuses it in every test. Page objects reach the tests through fixtures.

```mermaid
flowchart LR
    SETUP["setup project<br/>tests/auth.setup.ts"] -->|"saves"| STATE[".auth/standard_user.json<br/>storageState"]
    STATE --> CHROME["chromium project"]
    STATE --> MOBILE["mobile-chrome project<br/>Pixel 7"]
    CONF["playwright.config.ts<br/>testIdAttribute = data-test<br/>trace on first retry"] --> CHROME
    CONF --> MOBILE
    FIX["src/fixtures/test.ts<br/>loginPage, inventoryPage, cartPage ...<br/>users"] --> TESTS["tests/*.spec.ts<br/>@smoke and @regression tags"]
    PAGES["src/pages/*.page.ts"] --> FIX
    COMP["src/components/<br/>header, product card"] --> PAGES
    UTIL["src/utils/money.ts<br/>cents math"] --> TESTS
    CHROME --> TESTS
    MOBILE --> TESTS
    TESTS --> REP["reports<br/>html, junit, github annotations"]
```

Design choices:

- Locator order: role, label, placeholder, text, then `data-test`. No XPath. No styling classes.
- Product cards are component objects built with `locator.filter({ hasText })`, so a test says "add Sauce Labs Backpack" and never counts rows.
- Every wait is a condition. `waitForURL` after navigation, web-first assertions for state.
- Money is handled in cents. The checkout test asserts item total, 8% tax and grand total from the prices it reads on the page.
- Tags select subsets: `npx playwright test --grep @smoke`.

## Selenium suite

Same site, same page object idea, written the classic way for teams that run Selenium.

```mermaid
flowchart LR
    CONF["conftest.py<br/>driver fixture, headless new,<br/>screenshot on failure"] --> TESTS["tests/test_*.py"]
    BASE["pages/base_page.py<br/>WebDriverWait helpers"] --> PAGES["pages/*_page.py<br/>locator tuples"]
    PAGES --> TESTS
    TESTS --> OUT["results/junit.xml<br/>results/screenshots/"]
```

Selenium Manager downloads the matching driver, so there is no driver to install. Explicit waits replace implicit waits and sleeps.

## API contract tests

```mermaid
flowchart LR
    SCHEMAS["schemas/*.schema.json<br/>JSON Schema 2020-12"] --> CHECK["validate(response, schema)"]
    CLIENT["conftest.py<br/>httpx client, auth token"] --> TESTS["tests/test_auth.py<br/>tests/test_products.py<br/>tests/test_carts.py<br/>tests/test_graphql.py"]
    TESTS --> CHECK
    TESTS --> REST["dummyjson.com"]
    TESTS --> GQL["countries.trevorblades.com"]
```

Each endpoint has a shape test, a behavior test (pagination math, totals, search), and a negative test (unknown id, wrong password). Response time is asserted with a generous bound so the test fails on an outage, not on jitter.

## JMeter load plan

```mermaid
flowchart LR
    PROPS["-J properties<br/>host, threads, ramp_up, loops,<br/>think_time_ms, sla_ms"] --> UDV["User Defined Variables"]
    CSV["data/product_ids.csv"] --> TG["Thread Group"]
    UDV --> TG
    TG --> S1["GET /products?limit=10"]
    TG --> S2["GET /products/${product_id}"]
    TG --> S3["POST /auth/login<br/>JSON Extractor: accessToken"]
    S3 --> S4["GET /auth/me<br/>Authorization: Bearer"]
    S1 & S2 & S3 & S4 --> ASSERT["Response, JSON and Duration assertions"]
    ASSERT --> DASH["run.sh: results.jtl -> HTML dashboard"]
```

## LLM evals and the release gate

The harness treats a model like any other system under test. The dataset is the specification, the scorer is the oracle, and the gate is the pass or fail decision.

```mermaid
flowchart LR
    DS["data/golden.jsonl<br/>14 invoice emails with expected JSON"] --> RUN["llm-evals run"]
    EXT["extractor<br/>regex (offline) or OpenAI or Anthropic"] --> RUN
    RUN --> SCORE["scoring.py<br/>schema conformance<br/>field accuracy, 2% tolerance<br/>completeness<br/>line item matching"]
    SCORE --> JUDGE["judge.py<br/>heuristic second opinion on vendor names"]
    JUDGE --> REP["reports/<br/>results.json, junit.xml, report.html"]
    REP --> GATE["llm-evals gate<br/>gate.yaml thresholds<br/>gate_history.json"]
    GATE -->|"blocking metric fails"| FAIL["exit 1, build fails"]
    GATE -->|"all blocking pass"| PASS["exit 0"]
```

How a metric earns the right to block:

```mermaid
stateDiagram-v2
    [*] --> Candidate: added to gate.yaml with mode candidate
    Candidate --> Candidate: pass (streak < 2) or fail, reported as WARN
    Candidate --> Blocking: passed in 2 consecutive runs
    Blocking --> Failed: value below threshold, exit 1
    Failed --> Blocking: fixed and passing again
```

Rules that keep the signal honest:

- The answer key is never edited to make a run pass. A key entry changes only when the key itself is wrong, and the reason is recorded in `data/README.md`.
- Numbers compare with a 2% relative tolerance or 0.01 absolute, whichever is larger. Strings compare after normalization. Line items match by a fingerprint of description and quantity, then by position.
- Warn-only metrics show up in the report but never fail the build. That keeps new ideas visible without blocking releases.

## CI

```mermaid
flowchart LR
    PUSH["push or pull request"] --> CI["ci.yml"]
    CI --> J1["playwright<br/>npm ci, install chromium,<br/>typecheck, lint, test"]
    CI --> J2["selenium<br/>pip install, pytest"]
    CI --> J3["api-tests<br/>pip install, pytest"]
    CI --> J4["llm-evals<br/>pytest, run, gate"]
    J1 & J2 & J3 & J4 --> ART["artifacts: reports and junit xml"]
    MANUAL["workflow_dispatch"] --> JM["jmeter.yml<br/>threads, loops, sla_ms inputs"]
    JM --> DASH["artifact: HTML dashboard"]
```
