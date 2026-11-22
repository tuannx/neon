#!/bin/sh
# Re-run neon perf benches (Python timeit fallback harness) and compare vs perf/baseline.json
# regression >10% = warn, >25% = block
set -e; cd "$(dirname "$0")/.."
if [ -f perf/baseline.json ]; then python3 perf/bench_perf.py --compare perf/baseline.json; else python3 perf/bench_perf.py; fi
