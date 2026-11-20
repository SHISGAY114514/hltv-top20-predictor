"""Collect published series Rating 3.0 tables for the twelve high-tier events.

Offline builds consume the saved snapshot. A series must match all ten local
player IDs and every player's series kill/death totals before it is accepted.
"""
import csv
import gzip
import json
import re
import tempfile
import hashlib
import time
from pathlib import Path
from collections import defaultdict
from datetime import date, timedelta

from htpm.pipeline import ROOT, load
from htpm.core import HIGH


BASE = "https://www.hltv.org"
CURRENT_IDS = {"IEM Kraków 2026":8240, "BLAST Open Rotterdam 2026":8248,
               "IEM Cologne Major 2026":8301, "Esports World Cup 2026":8261,
               "BLAST Open Porto 2026":8249, "ESL Pro League Season 24":8244}
_last_request = 0.


def page(url):
    global _last_request
    import requests
    from bs4 import BeautifulSoup
    cache = Path(tempfile.gettempdir())/"htpm41-public-news"
    cache.mkdir(exist_ok=True)
    path = cache/(hashlib.sha256(url.encode()).hexdigest()+".gz")
    if path.exists():
        return BeautifulSoup(gzip.decompress(path.read_bytes()), "lxml")
    time.sleep(max(0.,1.5-(time.monotonic()-_last_request)))
    response = requests.get(url, timeout=12)
    _last_request = time.monotonic()
    if response.status_code==429:
        time.sleep(8)
        response=requests.get(url,timeout=12)
        _last_request=time.monotonic()
    response.raise_for_status()
    path.write_bytes(gzip.compress(response.content))
    return BeautifulSoup(response.content, "lxml")


def collect():
    lookup = {}
    windows = defaultdict(list)
    ids = {}
    for year, events in load("data/reference/season_stage_catalog.json").items():
        for event in events:
            if event["tier"] in HIGH:
                ids[event["event"]] = (CURRENT_IDS[event["event"]] if year == "2026"
                                        else int(event["source"].split("/events/")[1].split("/")[0]))
        scores = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        with gzip.open(ROOT/"data"/year/"stage_maps.csv.gz","rt",encoding="utf8") as stream:
            for row in csv.DictReader(stream):
                event = row["event"]
                if event not in ids:
                    continue
                windows[event].append(date.fromisoformat(row["date"]))
                key = (year,event,row["match"],row["stage"])
                kd = scores[key][row["player"].casefold()]
                kd[0] += int(row["kills"])
                kd[1] += int(row["deaths"])
        for key, players in scores.items():
            signature = tuple(sorted((p,*kd) for p,kd in players.items()))
            if signature in lookup:
                raise ValueError("Ambiguous scoreboard")
            lookup[signature] = key
    urls = {BASE+"/news/43841/zywoo-shines-as-vitality-take-iem-krakow-title-over-furia",
            BASE+"/news/43449/vitality-beat-faze-3-1-to-become-back-to-back-major-champions-in-budapest"}
    failures = []
    for event, event_id in sorted(ids.items(),key=lambda kv:kv[0] not in CURRENT_IDS):
        start, end = min(windows[event]), max(windows[event])+timedelta(days=2)
        url = BASE+"/news/archive?event="+str(event_id)
        try:
            listing = page(url)
            recaps=[]
            for link in listing.select("a.newsline.article"):
                stamp = link.select_one(".newsrecent")
                title = link.select_one(".newstext").get_text(" ",strip=True)
                if re.search(r'["“:]|\b(?:fantasy|highlights|live updates|as it happened|MVP|bracket set|viewership|gallery|EVPs|to face)\b',title,re.I):
                    continue
                if stamp and start.isoformat() <= stamp.get_text(strip=True) <= end.isoformat():
                    recaps.append(BASE+link["href"])
            # Spread the supplemental observations across the event calendar.
            for i in range(min(14,len(recaps))):
                urls.add(recaps[round(i*(len(recaps)-1)/max(1,min(14,len(recaps))-1))])
        except (OSError,ValueError) as err:
            failures.append((url,str(err)))
    print("Linked articles",len(urls),"local series",len(lookup),"failed listings",failures,flush=True)
    def read_article(url):
        try:
            soup = page(url)
        except (OSError,ValueError) as err:
            return [],(url,str(err))
        matches = []
        tables = soup.select("table.newsitem-match-stats-table")
        for left,right in zip(tables[::2],tables[1::2]):
            if not all("Rating 3.0" in t.get_text(" ",strip=True) for t in (left,right)):
                continue
            players = {}
            signature = []
            for row in left.select("tr.newsitem-match-stats-row")+right.select("tr.newsitem-match-stats-row"):
                pid = row.select_one("a.smartphone-only").get_text(strip=True).casefold()
                kills,deaths = map(int,row.select_one(".newsitem-match-stats-kd").get_text().split("-"))
                rating = row.select_one(".newsitem-match-stats-rating").get_text(strip=True)
                if rating in ("-", ""):
                    continue
                players[pid] = float(rating)
                signature.append((pid,kills,deaths))
            key = lookup.get(tuple(sorted(signature)))
            if key and len(players)==10:
                matches.append((key, {"ratings":players,"source":url}))
        return matches,None
    verified = {}
    for url in sorted(urls):
        matches,error=read_article(url)
        if error:
            failures.append(error)
        for key, record in matches:
            if key in verified and verified[key]["ratings"] != record["ratings"]:
                raise ValueError("Conflicting series ratings")
            verified.setdefault(key,record)
    print("Matched series",len(verified),"failed pages",len(failures),failures[:2],flush=True)
    for year in ("2025","2026"):
        matches = [dict(event=k[1],match=k[2],stage=k[3],**v) for k,v in sorted(verified.items()) if k[0]==year]
        dest = ROOT/"data"/year/"series_ratings.json"
        if dest.exists():
            previous = {(r["event"],r["match"]):r for r in json.loads(dest.read_text(encoding="utf8"))["series"]}
            for row in matches:
                k = row["event"],row["match"]
                if k in previous and previous[k]["ratings"] != row["ratings"]:
                    raise ValueError("Existing source differs: "+str(k))
                previous.setdefault(k,row)
            matches = [previous[k] for k in sorted(previous)]
        if not matches:
            raise ValueError("No verified series ratings available for "+year)
        data = {"rating":"HLTV Rating 3.0", "scope":"published high-tier series, matched on ten names and ten K/D totals",
                "events":{e:i for e,i in ids.items() if any(k[:2]==(year,e) for k in lookup.values())},
                "series":matches}
        dest.write_text(json.dumps(data,ensure_ascii=False,indent=1)+"\n",encoding="utf8")
        print(year,len(matches),flush=True)
    print("Articles checked",len(urls),"failed pages",len(failures),flush=True)


if __name__ == "__main__":
    collect()
