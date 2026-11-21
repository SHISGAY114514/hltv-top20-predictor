"""Content identities for the 17 November comparison, including report references."""
import hashlib

from .core import fingerprint, require
from .pipeline import ROOT

BASELINE = {"4.4": "4.3", "4.4.1": "4.4", "4.4.2": "4.4.1", "4.4.3": "4.4.2"}

INPUTS = (
    "config/model.json", "config/watchlist.json", "config/season_model.json",
    "config/season_4_2.json", "config/season_4_3.json", "data/2026/singapore/event.json",
    "data/2026/aggregate_snapshot.json", "data/2026/award_snapshot.json",
    "data/2026/stage_maps.csv.gz", "data/2026/series_ratings.json",
    "data/2026/published_stage_ratings.json", "data/reference/evp_orders_2026.json",
    "data/reference/event_tiers_2026_user.json", "data/reference/first_evp_context.json",
    "data/reference/peak_context.json", "data/reference/season_stage_catalog.json",
    "data/reference/event_formats_4_3.json", "data/reference/vrs_top10_monthly.json",
    "data/reference/stage_collection_audit.json", "data/reference/official_vps_4_3.json",
    "output/forecast_4_1_1/scores.json",
)


def input_hashes():
    hashes = {}
    for name in INPUTS:
        data = (ROOT / name).read_bytes()
        if name.startswith("output/"):
            # Git treats the reference report as text, unlike the immutable data inputs.
            data = data.replace(b"\r\n", b"\n")
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def configure(config, revision, scenario):
    require(fingerprint(input_hashes()) == revision["input_hash"], "4.4 frozen input hash mismatch")
    config.update(revision)
    if scenario == "nested_opponents":
        del config["opponent_bands"]
    if scenario == "equal_tiers":
        config["tier_shares"] = dict.fromkeys(config["tier_shares"], 1 / len(config["tier_shares"]))
    config["assume_unknown_6_10"] = scenario == "unknown_6_10"
    return [] if scenario == "legacy_stage" else revision["stage_exceptions"]
