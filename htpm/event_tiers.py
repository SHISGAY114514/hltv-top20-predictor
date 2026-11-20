"""User's 2026 overrides take precedence over the MVP medal category."""

POLICY = "user-2026-11-16-medal"
ADDITIONAL_MAJORS = {"PGL Major Singapore 2026"}
OVERRIDES = {
    "IEM Cologne Major 2026": "Major",
    "IEM Kraków 2026": "Super-elite",
    "Esports World Cup 2026": "Elite",
    "ESL Pro League Season 24": "Elite",
    "BLAST Open Porto 2026": "Elite",
    "BLAST Open Rotterdam 2026": "Elite",
}


def classify(event, medal):
    if medal not in {"gold", "silver", "bronze"}:
        raise ValueError("MVP medal must be verified before classification")
    if event in OVERRIDES:
        return OVERRIDES[event]
    if event in ADDITIONAL_MAJORS and medal == "gold":
        return "Major"
    if medal == "bronze":
        return "Medium"
    if medal == "silver":
        return "Big"
    raise ValueError("An additional gold-medal event needs an explicit Major rule")
