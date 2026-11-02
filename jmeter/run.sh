#!/usr/bin/env bash
# Run the DummyJSON load test in non GUI mode and build the HTML dashboard.
#
# Usage:
#   ./run.sh                      # smoke profile: 2 users, 1 loop
#   THREADS=20 LOOPS=10 ./run.sh  # load profile
#
# Variables (all optional):
#   THREADS, RAMP_UP, LOOPS, THINK_TIME_MS, SLA_MS, HOST
#   JMETER_HOME   path to an Apache JMeter install when jmeter is not on PATH
set -euo pipefail

cd "$(dirname "$0")"

THREADS="${THREADS:-2}"
RAMP_UP="${RAMP_UP:-2}"
LOOPS="${LOOPS:-1}"
THINK_TIME_MS="${THINK_TIME_MS:-300}"
SLA_MS="${SLA_MS:-2000}"
HOST="${HOST:-dummyjson.com}"

if command -v jmeter >/dev/null 2>&1; then
  JMETER_BIN="jmeter"
elif [[ -n "${JMETER_HOME:-}" && -x "${JMETER_HOME}/bin/jmeter" ]]; then
  JMETER_BIN="${JMETER_HOME}/bin/jmeter"
else
  echo "jmeter was not found. Install Apache JMeter 5.6 or set JMETER_HOME." >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="results/${STAMP}"
mkdir -p "${RUN_DIR}"

echo "Running ${THREADS} users x ${LOOPS} loops against ${HOST} (ramp up ${RAMP_UP}s, think time ${THINK_TIME_MS}ms, SLA ${SLA_MS}ms)"

"${JMETER_BIN}" -n \
  -t test-plans/dummyjson_load_test.jmx \
  -l "${RUN_DIR}/results.jtl" \
  -j "${RUN_DIR}/jmeter.log" \
  -e -o "${RUN_DIR}/dashboard" \
  -Jhost="${HOST}" \
  -Jthreads="${THREADS}" \
  -Jramp_up="${RAMP_UP}" \
  -Jloops="${LOOPS}" \
  -Jthink_time_ms="${THINK_TIME_MS}" \
  -Jsla_ms="${SLA_MS}"

echo
echo "Raw results:  ${RUN_DIR}/results.jtl"
echo "Dashboard:    ${RUN_DIR}/dashboard/index.html"
