# Runs the Playwright suite in the official image that matches the pinned
# @playwright/test version. The image already holds the browsers and their
# system dependencies, so the container needs no `playwright install`.
#
# Build:  docker build -t qa-portfolio-playwright .
# Run:    docker run --rm qa-portfolio-playwright
# Full:   docker run --rm qa-portfolio-playwright npx playwright test
# Report: docker run --rm -v "$PWD/playwright-report:/app/playwright-report" qa-portfolio-playwright
FROM mcr.microsoft.com/playwright:v1.63.0-noble

WORKDIR /app
ENV CI=1

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

CMD ["npx", "playwright", "test", "--project=chromium", "--grep", "@smoke"]
