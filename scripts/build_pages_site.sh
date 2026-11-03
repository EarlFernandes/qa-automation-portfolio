#!/usr/bin/env bash
# Assemble the GitHub Pages site from downloaded CI artifacts.
#
# Usage: scripts/build_pages_site.sh <artifacts dir> <site dir>
#
# Expected artifacts (names from ci.yml):
#   playwright-report   playwright-report/index.html plus results/healing-report.md
#   llm-evals-report    report.html, results.json, junit.xml
# Missing pieces are skipped, and the index says so.
set -euo pipefail

SRC="${1:-artifacts}"
OUT="${2:-site}"
SHA="${SOURCE_SHA:-unknown}"
STAMP="$(date -u +"%Y-%m-%d %H:%M UTC")"

rm -rf "$OUT"
mkdir -p "$OUT"

have_playwright=no
have_healing=no
have_evals=no

# Playwright HTML report: the folder that holds index.html under a playwright-report directory.
pw_index="$(find "$SRC" -type f -path "*playwright-report/index.html" | head -n 1 || true)"
if [ -n "$pw_index" ]; then
  mkdir -p "$OUT/playwright"
  cp -r "$(dirname "$pw_index")/." "$OUT/playwright/"
  have_playwright=yes
fi

# Healing report (markdown) wrapped in a minimal HTML page.
healing_md="$(find "$SRC" -type f -name "healing-report.md" | head -n 1 || true)"
if [ -n "$healing_md" ]; then
  mkdir -p "$OUT/playwright"
  python3 - "$healing_md" "$OUT/playwright/healing-report.html" <<'EOF'
import html, sys
src, dst = sys.argv[1], sys.argv[2]
body = html.escape(open(src, encoding="utf-8").read())
open(dst, "w", encoding="utf-8").write(
    "<!doctype html><meta charset='utf-8'><title>Healing report</title>"
    "<style>body{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 16px;color:#222}"
    "pre{white-space:pre-wrap;background:#f6f8fa;padding:16px;border-radius:6px}</style>"
    "<h1>Self-healing locator report</h1><p>Proposals for review. No test code was changed by a machine.</p>"
    f"<pre>{body}</pre>")
EOF
  have_healing=yes
fi

# LLM eval report.
evals_html="$(find "$SRC" -type f -name "report.html" -path "*llm-evals*" | head -n 1 || true)"
if [ -z "$evals_html" ]; then
  evals_html="$(find "$SRC" -type f -name "report.html" | head -n 1 || true)"
fi
if [ -n "$evals_html" ]; then
  mkdir -p "$OUT/llm-evals"
  cp "$evals_html" "$OUT/llm-evals/index.html"
  results_json="$(find "$(dirname "$evals_html")" -maxdepth 1 -name "results.json" | head -n 1 || true)"
  [ -n "$results_json" ] && cp "$results_json" "$OUT/llm-evals/results.json"
  have_evals=yes
fi

link_or_note() {
  # $1 = yes/no, $2 = href, $3 = label, $4 = description
  if [ "$1" = "yes" ]; then
    echo "<li><a href=\"$2\">$3</a><span>$4</span></li>"
  else
    echo "<li><s>$3</s><span>not in this run</span></li>"
  fi
}

cat > "$OUT/index.html" <<EOF
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QA automation portfolio: reports</title>
<style>
  body { font: 16px/1.55 system-ui, -apple-system, Segoe UI, sans-serif; color: #1f2937; max-width: 820px; margin: 48px auto; padding: 0 20px; }
  h1 { font-size: 28px; margin-bottom: 4px; }
  .meta { color: #6b7280; margin-bottom: 28px; }
  ul { list-style: none; padding: 0; }
  li { padding: 14px 0; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; gap: 16px; }
  li:last-child { border-bottom: 1px solid #e5e7eb; }
  a { color: #0b3d3a; font-weight: 600; text-decoration: none; }
  a:hover { text-decoration: underline; }
  span { color: #6b7280; text-align: right; }
  footer { margin-top: 28px; color: #6b7280; font-size: 14px; }
</style>
<h1>QA automation portfolio: latest reports</h1>
<p class="meta">Built from commit <code>${SHA:0:7}</code> on ${STAMP}. Source: <a href="https://github.com/EarlFernandes/qa-automation-portfolio">github.com/EarlFernandes/qa-automation-portfolio</a></p>
<ul>
$(link_or_note "$have_playwright" "playwright/" "Playwright HTML report" "84 tests on desktop and mobile Chromium, with traces on retry")
$(link_or_note "$have_healing" "playwright/healing-report.html" "Self-healing locator report" "heal-and-propose events from the run")
$(link_or_note "$have_evals" "llm-evals/" "LLM eval report" "14 invoice cases scored against the golden dataset, with the gate result")
</ul>
<footer>Reports are regenerated after every green CI run on main.</footer>
</html>
EOF

echo "site built in $OUT (playwright=$have_playwright healing=$have_healing evals=$have_evals)"
