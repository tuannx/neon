#!/usr/bin/env python3
"""Deterministic stdlib-only perf harness for neon test_runner pure hot paths.
Fixed inputs, fixed iteration counts, warmup=200, repeat=5, reports min ns/op.
Rust path note: criterion bench for leaf crate tenant_size_model was attempted
2026-11-21; cargo timed out after 1150s in dependency fetch/resolve for the
full workspace (target dir stayed empty on this shared VM) -> this Python
fallback is the measured baseline. See results-round2/neon.md.
Usage: bench_perf.py [--write-baseline] [--compare perf/baseline.json] [--output out.json]
"""
import argparse, json, os, platform, subprocess, sys, timeit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "test_runner"))
from fixtures.common_types import Lsn
from fixtures.pageserver.common_types import parse_delta_layer, parse_image_layer, parse_layer_file_name

IMG = "000000000000000000000000000000000000-000000000000000000000000000000FFFFFF__00000000012AB34C"
DELTA = "000000000000000000000000000000000000-000000000000000000000000000000FFFFFF__000000000000000A-00000000012AB34C"
BENCHES = [
    ("lsn_parse_and_format", lambda: str(Lsn("3/1234ABCD")), 20000),
    ("parse_image_layer_name", lambda: parse_image_layer(IMG), 20000),
    ("parse_layer_file_name_delta", lambda: parse_layer_file_name(DELTA), 20000),
]
WARMUP = 200

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--compare"); ap.add_argument("--output"); a = ap.parse_args()
    results = {}
    for name, fn, n in BENCHES:
        for _ in range(WARMUP): fn()
        best = min(timeit.Timer(fn).repeat(repeat=5, number=n)) / n
        results[name] = {"ns_per_op": round(best*1e9, 1), "ops_per_sec": round(1/best, 1), "unit": "ns/op", "iterations_per_repeat": n, "repeat": 5}
        print(f"{name}: {results[name]['ns_per_op']:.1f} ns/op ({results[name]['ops_per_sec']:.0f} ops/s)")
    try: commit = subprocess.check_output(["git","rev-parse","HEAD"], text=True, cwd=os.path.join(os.path.dirname(__file__),"..")).strip()
    except Exception: commit = "unknown"
    doc = {"repo": "tuannx/neon", "commit": commit, "date": "2026-11-21", "framework": "python stdlib timeit (fallback; Rust criterion attempted, timed out in workspace dependency fetch — see caveats)", "environment": f"Linux VM shared ~1.5 effective CPU, ~7.7GB RAM, Python {platform.python_version()}", "caveats": "Shared VM: absolute numbers noisy, use for relative regression detection only. Scope is narrow: 3 pure parsing/format functions in test_runner (fixtures/common_types.Lsn, fixtures/pageserver/common_types layer-name parsing). No Rust code measured. Rust toolchain: repo pins 1.88.0, local 1.99.1 via RUSTUP_TOOLCHAIN override; cargo bench -p tenant_size_model hit the 1150s time-box while updating git/crates.io dependencies for the full workspace.", "warmup": WARMUP, "benches": results}
    out = a.output or os.path.join(os.path.dirname(__file__), "results.json")
    json.dump(doc, open(out,"w"), indent=2)
    if a.write_baseline:
        json.dump(doc, open(os.path.join(os.path.dirname(__file__),"baseline.json"),"w"), indent=2); print("baseline written")
    if a.compare:
        base = json.load(open(a.compare)); verdict = "pass"
        for name, r in results.items():
            b = base["benches"].get(name, {}).get("ns_per_op")
            if not b: print(f"{name}: no baseline"); continue
            d = (r["ns_per_op"]-b)/b*100; print(f"{name}: delta {d:+.2f}% vs baseline")
            if d > 25: verdict = "block"
            elif d > 10 and verdict == "pass": verdict = "warn"
        print(f"VERDICT: {verdict}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
