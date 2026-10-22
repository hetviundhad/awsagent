#!/usr/bin/env python3
"""
Decider 2B vs Amazon Bedrock (Claude Haiku) on the SAME task: classify a student message into a pedagogy policy.

    1. strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8099
    2. aws credentials configured (optional - Bedrock column is skipped without them)
    3. python scripts/benchmark_decider.py

Writes data/storage/decider_benchmark.json (shown in the Decision Lab) and docs/BENCHMARK.md.
Honesty rules: refuses to run against the MOCK server unless --allow-mock (then clearly labelled);
never reports fallback answers as model results.
"""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("STORAGE_DIR", str(ROOT / "backend" / "data" / "storage"))

from backend.app.decider import patterns as P                    # noqa: E402
from backend.app.decider.client import DeciderClient             # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))] if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "policy_eval.jsonl"))
    ap.add_argument("--allow-mock", action="store_true")
    ap.add_argument("--no-bedrock", action="store_true")
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.data, encoding="utf-8") if l.strip()]
    client = DeciderClient(allow_fallback=False, timeout=60)
    h = client.health()
    if not h.get("ok"):
        sys.exit(f"Decider server not reachable: {h.get('error')}\n  start it: {h.get('hint')}")
    mock = bool(h.get("mock"))
    if mock and not a.allow_mock:
        sys.exit("The server is the MOCK keyword server - refusing to publish benchmark numbers from it. Use --allow-mock to override.")

    pat = P.pedagogy_policy("Algorithms", ["Dynamic Programming", "Graph Algorithms", "Sorting"])
    opts = pat.options
    client.ask("warm up", {"policy": pat.question()})                      # one-time warm-up, excluded from timings

    d_ok, d_ms, d_conf, d_rows = 0, [], [], []
    for r in rows:
        state = P.build_state(course="Algorithms", topics=["Dynamic Programming", "Graph Algorithms", "Sorting"],
                              weak=[], mastered=[], locked=[], student_history=[], message=r["text"])
        res = client.ask(state, {"policy": pat.question()})
        ans = res.answers["policy"]
        d_ms.append(res.latency_ms)
        d_conf.append(ans.confidence)
        ok = ans.choice == r["label"]
        d_ok += ok
        d_rows.append({"text": r["text"], "label": r["label"], "pred": ans.choice, "conf": round(ans.confidence, 3), "ok": ok})

    # calibration: accuracy among high-confidence predictions
    hi = [x for x in d_rows if x["conf"] >= 0.8]
    out = {
        "task": "pedagogy policy classification (7 classes)", "n": len(rows), "mock_server": mock,
        "decider": {"checkpoint": h.get("checkpoint"), "device": h.get("device"),
                    "accuracy": round(d_ok / len(rows), 3), "latency_ms_median": round(statistics.median(d_ms), 1),
                    "latency_ms_p95": round(pct(d_ms, 0.95), 1), "mean_confidence": round(statistics.mean(d_conf), 3),
                    "accuracy_when_conf_ge_0.8": round(sum(x["ok"] for x in hi) / len(hi), 3) if hi else None,
                    "n_conf_ge_0.8": len(hi), "cost_per_call_usd": 0.0},
        "errors": [x for x in d_rows if not x["ok"]][:12],
    }

    if not a.no_bedrock:
        try:
            from backend.app.providers.bedrock_provider import get_bedrock
            br = get_bedrock()
            if not br.available():
                raise RuntimeError(br.status()["error"])
            names = [k for k in opts if k != "none_of_these"] + ["none_of_these"]
            sys_p = ("Classify the student's message into exactly one category. Reply with the category name only.\n"
                     + "\n".join(f"- {k}: {v}" for k, v in opts.items()))
            l_ok, l_ms = 0, []
            for r in rows:
                o = br.converse([{"role": "user", "content": r["text"]}], system=sys_p, tier="fast", max_tokens=12, temperature=0)
                pred = next((n for n in names if n in o["text"].lower().replace(" ", "_")), "none_of_these")
                l_ok += pred == r["label"]
                l_ms.append(o["latency_ms"])
            out["bedrock_fast"] = {"model_id": br.models["fast"], "accuracy": round(l_ok / len(rows), 3),
                                   "latency_ms_median": round(statistics.median(l_ms), 1), "latency_ms_p95": round(pct(l_ms, 0.95), 1),
                                   "confidence_exposed": False}
            out["speedup_median"] = round(statistics.median(l_ms) / statistics.median(d_ms), 2)
        except Exception as exc:  # noqa: BLE001
            out["bedrock_fast"] = {"skipped": str(exc)}

    store = Path(os.environ["STORAGE_DIR"]); store.mkdir(parents=True, exist_ok=True)
    (store / "decider_benchmark.json").write_text(json.dumps(out, indent=2))
    md = ["# Benchmark: Decider 2B vs Bedrock on pedagogy-policy classification", "",
          f"*{len(rows)} labelled student messages, 7 classes. Server: `{h.get('checkpoint')}` on `{h.get('device')}`"
          + (" — **MOCK SERVER, NOT THE MODEL**" if mock else "") + "*", "",
          "| | accuracy | median latency | p95 latency | $ / call | calibrated confidence |", "|---|---|---|---|---|---|",
          f"| Strands Decider 2B | {out['decider']['accuracy']:.1%} | {out['decider']['latency_ms_median']} ms | {out['decider']['latency_ms_p95']} ms | $0 (local) | yes |"]
    b = out.get("bedrock_fast", {})
    if "accuracy" in b:
        md.append(f"| Bedrock `{b['model_id']}` | {b['accuracy']:.1%} | {b['latency_ms_median']} ms | {b['latency_ms_p95']} ms | per-token | no |")
        md += ["", f"Median speed-up: **{out['speedup_median']}x**."]
    else:
        md += ["", f"_Bedrock column skipped: {b.get('skipped')}_"]
    if out["decider"]["accuracy_when_conf_ge_0.8"] is not None:
        md += ["", f"When the Decider's confidence was ≥ 0.8 ({out['decider']['n_conf_ge_0.8']} messages) it was right "
                   f"**{out['decider']['accuracy_when_conf_ge_0.8']:.1%}** of the time — that is why the gate branches on the number, not the label."]
    (ROOT / "docs" / "BENCHMARK.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "errors"}, indent=2))


if __name__ == "__main__":
    main()
