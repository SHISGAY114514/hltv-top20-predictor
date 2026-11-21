"""Rebuild the paired 17 November snapshots and reconcile all 177 scores."""
import argparse

from htpm.core import require
from htpm.frozen_4_4 import BASELINE
from htpm.forecast_4_2 import calculate, publish
from htpm.pipeline import ROOT

from .compare_4_4 import DAY, compare, write_csv


def run(model="4.4.2"):
    old = calculate(today=DAY, model=BASELINE[model])
    baseline = publish(old, verify=True).parent.name
    new = calculate(today=DAY, model=model)
    require(new["baseline_snapshot"] == baseline and old["input_hash"] == new["input_hash"]
            and old["scope"] == new["scope"] and len(new["scope"]) == 23
            and old["cutoff"] == new["cutoff"] == DAY.isoformat(), "Snapshot mismatch")
    rows = compare(old, new)
    require(len(rows) == sum(p["eligible"] for p in new["players"]) == 177
            and all(r["new_rank"] == r["natural_rank"] for r in rows), "Cohort mismatch")
    keys = ("id", "name", "old_rank", "new_rank", "rank_gain", "old_score", "new_score",
            "score_delta", *(k + "_delta" for k in new["players"][0]["contributions"]))
    path = publish(new)
    publish(new, verify=True)
    dest = ROOT / "output" / ("comparison_" + model.replace(".", "_"))
    write_csv(dest / "comparison.csv", [{k: r[k] for k in keys} for r in rows])
    print(len(rows), baseline, path.parent.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("4.4.2", "4.4.3"), default="4.4.2")
    run(parser.parse_args().model)
