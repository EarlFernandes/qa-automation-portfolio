# Architecture notes

This page explains how each suite is built and why. The diagrams render on GitHub.

## Repository map

```mermaid
flowchart TB
    ROOT["qa-automation-portfolio"]
    ROOT --> PW["playwright/"]
    ROOT --> SE["selenium/"]
    ROOT --> API["api-tests/"]
    ROOT --> JM["jmeter/"]
    ROOT --> EV["llm-evals/"]
    ROOT --> GH[".github/workflows/"]
    ROOT --> DOCS["docs/"]
```

## Playwright suite

The suite signs in once, saves the browser state, and reuses it in every test. Page objects reach the tests through fixtures.

```mermaid
flowchart LR
    SETUP["setup project"] -->|"saves storageState"| STATE[".auth/standard_user.json"]
    STATE --> CHROME["chromium project"]
    STATE --> MOBILE["mobile-chrome project"]
    CONF["playwright.config.ts"] --> CHROME
    CONF --> MOBILE
    COMP["components"] --> PAGES["page objects"]
    PAGES --> FIX["fixtures: test.ts"]
    FIX --> TESTS["tests/*.spec.ts"]
    CHROME --> TESTS
    MOBILE --> TESTS
    TESTS --> REP["html, junit and github reports"]
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
    CONF["conftest.py: driver fixture"] --> TESTS["tests/test_*.py"]
    BASE["base_page.py: explicit waits"] --> PAGES["page objects"]
    PAGES --> TESTS
    TESTS --> OUT["junit.xml and screenshots"]
```

Selenium Manager downloads the matching driver, so there is no driver to install. Explicit waits replace implicit waits and sleeps.

## API contract tests

```mermaid
flowchart LR
    SCHEMAS["schemas/*.schema.json"] --> CHECK["validate response against schema"]
    CLIENT["conftest.py: httpx client and token"] --> TESTS["tests/test_*.py"]
    TESTS --> CHECK
    TESTS --> REST["dummyjson.com"]
    TESTS --> GQL["countries GraphQL API"]
```

Each endpoint has a shape test, a behavior test (pagination math, totals, search), and a negative test (unknown id, wrong password). Response time is asserted with a generous bound so the test fails on an outage, not on jitter.

## JMeter load plan

```mermaid
flowchart LR
    PROPS["-J properties"] --> UDV["User Defined Variables"]
    CSV["product_ids.csv"] --> TG["Thread Group"]
    UDV --> TG
    TG --> S1["GET /products"]
    TG --> S2["GET /products/id"]
    TG --> S3["POST /auth/login"]
    S3 -->|"accessToken"| S4["GET /auth/me"]
    S1 & S2 & S3 & S4 --> ASSERT["response, JSON and duration assertions"]
    ASSERT --> DASH["run.sh builds the HTML dashboard"]
```

## LLM evals and the release gate

The harness treats a model like any other system under test. The dataset is the specification, the scorer is the oracle, and the gate is the pass or fail decision.

```mermaid
flowchart LR
    DS["golden.jsonl: 14 cases"] --> RUN["llm-evals run"]
    EXT["extractor: regex, OpenAI or Anthropic"] --> RUN
    RUN --> SCORE["scoring.py"]
    SCORE --> JUDGE["judge.py"]
    JUDGE --> REP["reports: json, junit, html"]
    REP --> GATE["llm-evals gate"]
    GATE -->|"a blocking metric fails"| FAIL["exit 1, build fails"]
    GATE -->|"all blocking metrics pass"| PASS["exit 0"]
```

How a metric earns the right to block:

```mermaid
stateDiagram-v2
    [*] --> Candidate: added to gate.yaml as candidate
    Candidate --> Candidate: pass with streak under 2, or fail (WARN only)
    Candidate --> Blocking: passed in 2 consecutive runs
    Blocking --> Failed: value below threshold, exit 1
    Failed --> Blocking: fixed and passing again
```

Rules that keep the signal honest:

- The answer key is never edited to make a run pass. A key entry changes only when the key itself is wrong, and the reason is recorded in `data/README.md`.
- Numbers compare with a 2% relative tolerance or 0.01 absolute, whichever is larger. Strings compare after normalization. Line items match by a fingerprint of description and quantity, then by position.
- Warn-only metrics show up in the report but never fail the build. That keeps new ideas visible without blocking releases.

## Self-healing locators

`playwright/src/healing/heal.ts` resolves an ordered list of locator candidates. The first candidate is the one the test author wrote. When it is not attached within a short timeout, the next candidate is tried. A fallback that wins is recorded as a healing event with the test title, the page URL, the primary locator, the winner and a proposed code change. The global teardown writes `results/healing-report.md` and appends it to the GitHub job summary.

```mermaid
flowchart LR
    T["test calls healingLocator"] --> P["primary candidate"]
    P -->|"attached"| ACT["action runs"]
    P -->|"not found in 1.5 s"| F1["fallback 1: role and name"]
    F1 -->|"attached"| LOG["record heal event, annotate test"] --> ACT
    F1 -->|"not found"| F2["fallback 2: css"]
    F2 -->|"attached"| LOG
    F2 -->|"not found"| ERR["error lists every candidate"]
    LOG --> REP["healing-report.md and CI job summary"]
```

The policy is heal-and-propose. The unhealed run stays the gate in CI. A person reviews each proposal and decides whether the locator was stale or the product regressed.

## Live LLM evals

`llm-evals-live.yml` runs the same harness with the Anthropic or OpenAI adapter. Prompts embed the JSON schema and ask for JSON only. Calls retry with backoff on rate limits and connection errors, never on auth errors. Token usage is recorded per case. The live gate (`gate.live.yaml`) keeps schema conformance, extraction rate and latency blocking from the first run, and starts accuracy and completeness as candidates that earn blocking status after two consecutive passes.

## Published reports

`pages.yml` waits for a green CI run on main, downloads its artifacts, assembles a small site with `scripts/build_pages_site.sh`, and deploys it to GitHub Pages: the Playwright HTML report, the healing report and the LLM eval report.

## CI

```mermaid
flowchart LR
    PUSH["push or pull request"] --> CI["ci.yml"]
    CI --> J1["playwright job"]
    CI --> J2["selenium job"]
    CI --> J3["api-tests job"]
    CI --> J4["llm-evals job: pytest, run, gate"]
    J1 & J2 & J3 & J4 --> ART["artifacts: reports and junit xml"]
    ART -->|"green run on main"| PAGES["pages.yml: GitHub Pages site"]
    SCHED["weekly schedule"] --> LIVE["llm-evals-live.yml: real model + live gate"]
    MANUAL["workflow_dispatch"] --> JM["jmeter.yml"]
    JM --> DASH["artifact: HTML dashboard"]
    DOCK["docker.yml"] --> IMG["build image, run smoke tests inside"]
```
