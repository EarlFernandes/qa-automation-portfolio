# Test strategy

This is the strategy behind the suites in this repository. It is written the way I write one for a product team: short, with the decisions and the reasons.

## Scope

System under test: a public demo shop ([saucedemo.com](https://www.saucedemo.com)) for browser tests, a public REST API ([dummyjson.com](https://dummyjson.com)) and a public GraphQL API for API and load tests, and a synthetic invoice extraction task for the LLM evals.

In scope: sign-in, product list, cart and checkout flows; API contracts, auth, pagination and error handling; load behaviour of the read and login endpoints; extraction quality of an LLM feature.

Out of scope: payment, email, and anything that needs an account we do not own.

## Risks and where the tests sit

| Risk | Level that catches it | Suite |
| --- | --- | --- |
| A user cannot sign in, buy, or see correct totals | End-to-end browser tests on the real UI | Playwright, Selenium |
| The API shape changes and breaks clients | Contract tests from JSON Schema files | api-tests |
| Auth or pagination logic regresses | Behaviour and negative API tests | api-tests |
| The service slows down under load | Load plan with duration assertions | jmeter |
| A model change lowers extraction quality | Golden dataset scored in CI with a gate | llm-evals |
| Screens break for keyboard and screen reader users | axe scans with a baseline ratchet | Playwright a11y project |
| Layout regresses without a functional failure | Screenshot comparison, run on demand | Playwright visual project |

The pyramid is deliberate. Most checks are fast API and unit level. Browser tests cover the flows a user would notice within a minute. Visual and load tests run on demand because they are slower or platform specific.

## Environments and data

Every target is public, so there is no environment to provision. Base URLs come from environment variables with public defaults. Test accounts are the published demo accounts. No secrets are stored in the repository. The live LLM run uses a repository secret and never runs on pull requests.

## Entry and exit criteria

A change can merge when the CI workflow is green: Playwright, Selenium, API tests, and the offline LLM eval gate. A release of the model feature can go ahead when the live eval gate passes its blocking metrics. Warn-only metrics inform but never block.

## Flaky tests

Every wait is for a condition, never a sleep. CI retries a failed test twice with a trace on the retry. A test that flakes twice in a week gets the `@quarantine` tag and an issue link, is excluded from CI, and is fixed within the sprint. The quarantine list is reviewed at every release.

## Self-healing locators

Healing is heal-and-propose. When a primary locator fails, the test falls through an ordered list of candidates, continues, and records the heal as a proposal in the report and the CI job summary. No test code is rewritten by a machine. The unhealed run remains the gate: a heal that passes the wrong element would hide a real regression, so every proposal is reviewed by a person before the locator changes.

## LLM evaluation gate

The golden dataset is the specification. Each case is scored for schema conformance, field accuracy with a tolerance, completeness and line item matching. Metrics have thresholds in `gate.yaml`. A new metric starts as a candidate and becomes blocking only after it passes in two consecutive runs. The answer key is never edited to make a run pass; a key entry changes only when the key itself is wrong and the reason is recorded.

## Reporting

Each suite writes JUnit XML for CI, plus an HTML report. The latest Playwright report, healing report and LLM eval report are published to GitHub Pages after every green run on main. The CI job summary shows pass counts and heals at a glance.

## What I would add with more time

Consumer-driven contract tests with Pact for an API we own. A k6 performance test with thresholds in CI, in place of the manual JMeter run. Mutation testing on the eval harness to prove the scorer fails when it should. A second model in the live evals to compare providers side by side.
