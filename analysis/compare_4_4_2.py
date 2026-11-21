"""Rebuild the paired 17 November snapshots and reconcile all 177 scores."""
from htpm.core import require
from htpm.forecast_4_2 import calculate, publish
from htpm.pipeline import ROOT

from .compare_4_4 import DAY, compare, write_csv


def run():
    old = calculate(today=DAY, model="4.4.1")
    baseline = publish(old, verify=True).parent.name
    new = calculate(today=DAY, model="4.4.2")
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
    write_csv(ROOT/"output/comparison_4_4_2/comparison.csv", [{k: r[k] for k in keys} for r in rows])
    print(len(rows), baseline, path.parent.name)


if __name__ == "__main__":
    run()
