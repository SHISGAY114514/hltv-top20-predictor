"""Offline fixed-cohort comparison and one-policy-at-a-time reversals."""
from htpm.core import fingerprint, require
from htpm.forecast_4_2 import calculate, publish
from htpm.pipeline import ROOT, load

from .compare_4_4 import DAY, json_file, keyed, rank, write_csv

SCENARIOS = ("restore_R", "restore_event_multipliers", "matched_only", "previous_award_context")


def run():
    old = calculate(today=DAY, model="4.4")
    snapshot = publish(old, verify=True).parent.name
    require(snapshot == load("config/season_4_4_1.json")["base_snapshot"], "Wrong 4.4 archive")
    new = calculate(today=DAY, model="4.4.1")
    require(old["scope"] == new["scope"] and len(new["scope"]) == 23 and
            old["cutoff"] == new["cutoff"] == DAY.isoformat(), "Scope mismatch")
    left = keyed(old)
    ids = {pid for pid, p in left.items() if p["eligible"]}
    cohort = fingerprint(sorted(ids))
    require(len(ids) == 177 and cohort == load("config/season_4_4.json")["base_cohort_hash"], "Cohort mismatch")
    variants = {}
    for scenario in SCENARIOS:
        variants[scenario] = keyed(calculate(today=DAY, model="4.4.1", scenario=scenario))
    for table in [keyed(new), *variants.values()]:
        require(ids == {pid for pid, p in table.items() if p["eligible"]}, "Eligibility changed")
    no_h = {p["id"]: p["score"]-p["contributions"]["H"] for p in new["players"] if p["eligible"]}
    no_h_ranks = rank(no_h)
    rows = []
    for p in new["players"]:
        if p["id"] not in ids:
            continue
        before = left[p["id"]]
        row = dict(id=p["id"], name=p["name"], old_rank=before["rank"], new_rank=p["rank"],
                   rank_gain=before["rank"]-p["rank"], old_score=before["score"], new_score=p["score"],
                   delta=p["score"]-before["score"], partial_rating_events=sum("whole_event_observation" in e for e in p["events"]),
                   has_community_table=p["published"] is not None)
        for k, value in p["contributions"].items():
            row[k+"_old"] = before["contributions"][k]
            row[k+"_new"] = value
            row[k+"_delta"] = value-row[k+"_old"]
        require(abs(row["delta"]-sum(row[k+"_delta"] for k in p["contributions"])) < 1e-10, "Contributions mismatch")
        for scenario, table in variants.items():
            alt = table[p["id"]]
            row[scenario+"_rank"], row[scenario+"_score"] = alt["rank"], alt["score"]
        row["no_H_rank"], row["no_H_score"] = no_h_ranks[p["id"]], no_h[p["id"]]
        rows.append(row)
    path = publish(new)
    publish(new, verify=True)
    dest = ROOT/"output/comparison_4_4_1"
    write_csv(dest/"comparison.csv", rows)
    json_file(dest/"manifest.json", dict(models=[old["version"],new["version"]], snapshots=[snapshot,path.parent.name],
              cutoff=new["cutoff"], events=new["scope"], input_hash=new["input_hash"], cohort_sha256=cohort,
              cohort=len(ids), scenarios=[*SCENARIOS, "no_H"], top20_overlap=sum(r["old_rank"]<=20 for r in rows[:20]),
              spearman=1-6*sum(r["rank_gain"]**2 for r in rows)/(len(rows)*(len(rows)**2-1)),
              revision_policy_sha256=fingerprint(load("config/season_4_4_1.json"))))
    print(dest, len(rows), path.parent.name)


if __name__ == "__main__":
    run()
