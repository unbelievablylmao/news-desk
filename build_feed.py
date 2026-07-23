#!/usr/bin/env python3
"""
Narrative Labs — news desk builder.

Reads sources.json + tags.json, pulls every RSS feed, tags each headline by
keyword, clusters versions of the same story across outlets, and writes
feed.json for the dashboard to read.

Run locally:   python3 build_feed.py
On a schedule: see .github/workflows/refresh.yml
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "feed.json")

RETENTION_HOURS = 72       # how long a story stays on the board
SIM_THRESHOLD = 0.42       # 0-1. higher = stricter about calling two headlines the same story
CLUSTER_WINDOW_H = 14      # only cluster headlines published within this many hours of each other
TIMEOUT = 20

UA = "Mozilla/5.0 (compatible; NarrativeLabsDesk/1.0; +https://github.com)"

STOP = {
    "the", "and", "for", "with", "from", "that", "this", "has", "have", "are", "was",
    "were", "will", "its", "into", "amid", "after", "over", "says", "said", "new",
    "more", "than", "but", "not", "how", "why", "what", "who", "all", "can", "you",
    "your", "his", "her", "they", "their", "our", "out", "off", "now", "one", "two",
    "may", "could", "would", "should", "about", "as", "at", "by", "in", "of", "on",
    "to", "up", "it", "is", "be", "a", "an", "or", "if", "so", "we", "he", "she",
}


# ---------------------------------------------------------------- helpers

def load(name):
    with open(os.path.join(HERE, name), "r", encoding="utf-8") as f:
        return json.load(f)


def clean_title(t):
    t = re.sub(r"\s+", " ", (t or "")).strip()
    t = t.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
    return t


UNIT = {"billion": "b", "bn": "b", "million": "m", "mn": "m",
        "trillion": "t", "thousand": "k", "percent": "%"}


def stem(w):
    """Crude stem: drop a plural 's', then truncate. 'cuts'->'cut',
    'liquidations' and 'liquidated' both -> 'liquid'."""
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    return w[:6] if len(w) > 6 else w


def signature(title):
    """
    Weighted fingerprint of a headline: {token: weight}.

    Outlets rewrite almost every word of a story, so plain word overlap fails.
    What survives rewriting is the numbers and the proper nouns, so those
    carry the weight:  numbers 3, proper nouns 2, ordinary words 1.
    """
    low = title.lower().replace(",", "")
    for word, sym in UNIT.items():
        low = re.sub(r"(\d[\d.]*)\s*" + word, r"\1" + sym, low)

    sig = {}

    # numbers, incl. magnitude suffix:  1.4b   118k   47m   78%
    for n in re.findall(r"(?<![a-z0-9.])\$?(\d[\d.]*\s?[bmkt%]?)", low):
        n = n.replace(" ", "").rstrip(".")
        if n and n not in ("0", "1", "2", "3", "4", "5"):
            sig[n] = 3

    # proper nouns — capitalised mid-sentence, or all-caps tickers
    words = re.findall(r"[A-Za-z][A-Za-z.&'-]*", title)
    for i, w in enumerate(words):
        if i == 0 or len(w) < 2:
            continue
        if w[0].isupper():
            k = stem(w.lower().strip(".'-"))
            if k and k not in STOP:
                sig[k] = max(sig.get(k, 0), 2)

    # everything else
    for w in re.findall(r"[a-z]{3,}", low):
        if w not in STOP:
            sig.setdefault(stem(w), 1)

    return sig


def similarity(sig_a, sig_b):
    """Weighted containment, not Jaccard — tolerant of very different lengths."""
    if not sig_a or not sig_b:
        return 0.0
    shared = sum(min(sig_a[k], sig_b[k]) for k in sig_a.keys() & sig_b.keys())
    return shared / min(sum(sig_a.values()), sum(sig_b.values()))


def build_matchers(tagmap):
    """Precompile one regex per tag so matching is fast and word-boundary aware."""
    out = {}
    for tag, words in tagmap.items():
        if tag.startswith("_"):
            continue
        parts = []
        for w in words:
            w = re.escape(w.lower()).replace(r"\ ", r"\s+")
            parts.append(r"(?<![a-z0-9])" + w + r"(?![a-z0-9])")
        out[tag] = re.compile("|".join(parts), re.I)
    return out


def tag_text(text, matchers):
    return sorted(t for t, rx in matchers.items() if rx.search(text))


def to_dt(entry):
    for key in ("published_parsed", "updated_parsed"):
        v = entry.get(key)
        if v:
            try:
                return datetime.fromtimestamp(time.mktime(v), tz=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- fetching

def fetch(src):
    """Returns (items, error_or_None). Never raises — a dead feed must not kill the run."""
    try:
        r = requests.get(src["url"], timeout=TIMEOUT, headers={"User-Agent": UA})
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"

    if not parsed.entries:
        return [], "no entries"

    items = []
    for e in parsed.entries[:40]:
        title = clean_title(e.get("title"))
        link = e.get("link") or ""
        if not title or not link:
            continue

        source = src["name"]
        # Google News wraps titles as "Headline - Publisher" — split the real outlet out.
        if src.get("gnews"):
            if " - " in title:
                title, source = title.rsplit(" - ", 1)
                title, source = clean_title(title), clean_title(source)
            else:
                source = "Google News"

        summary = re.sub(r"<[^>]+>", " ", e.get("summary", ""))[:400]

        items.append({
            "title": title,
            "url": link,
            "source": source,
            "weight": src.get("weight", 5),
            "require_tag": src.get("require_tag", False),
            "dt": to_dt(e),
            "blob": title + " " + summary,
            "sig": signature(title),
        })
    return items, None


# ---------------------------------------------------------------- clustering

def cluster(items):
    """Greedy single pass. Items arrive newest-first."""
    clusters = []
    for it in items:
        placed = False
        for c in clusters:
            if abs((c["dt"] - it["dt"]).total_seconds()) > CLUSTER_WINDOW_H * 3600:
                continue
            # compare against a few members, not just the first — stories drift
            if any(similarity(m["sig"], it["sig"]) >= SIM_THRESHOLD
                   for m in c["members"][:4]):
                c["members"].append(it)
                placed = True
                break
        if not placed:
            clusters.append({"title": it["title"], "dt": it["dt"], "members": [it]})
    return clusters


def shape(c):
    """Turn a cluster into the record the dashboard renders."""
    members = c["members"]
    # lead = highest-weight source; ties broken by earliest publication
    lead = sorted(members, key=lambda m: (-m["weight"], m["dt"]))[0]

    seen, srcs = set(), []
    for m in sorted(members, key=lambda m: -m["weight"]):
        if m["source"] not in seen:
            seen.add(m["source"])
            srcs.append(m["source"])

    tags = sorted({t for m in members for t in m["tags"]})

    alt, used = [], {lead["url"]}
    for m in members:
        if m["url"] in used or m["title"] == lead["title"]:
            continue
        used.add(m["url"])
        alt.append([m["source"], m["title"], m["url"]])

    return {
        "h": lead["title"],
        "url": lead["url"],
        "ts": min(m["dt"] for m in members).isoformat().replace("+00:00", "Z"),
        "tags": tags,
        "srcs": srcs,
        "alt": alt[:6],
    }


# ---------------------------------------------------------------- main

def main():
    sources = load("sources.json")
    matchers = build_matchers(load("tags.json"))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=RETENTION_HOURS)
    raw, report = [], []

    for src in sources:
        items, err = fetch(src)
        kept = 0
        for it in items:
            if it["dt"] < cutoff:
                continue
            it["tags"] = tag_text(it["blob"], matchers)
            if it["require_tag"] and not it["tags"]:
                continue
            raw.append(it)
            kept += 1
        report.append((src["name"], kept, err))
        print(f"  {'ok ' if not err else 'FAIL'} {src['name']:<18} {kept:>3} items"
              + (f"   [{err[:60]}]" if err else ""))

    # exact-URL dedupe, then newest-first, then cluster
    seen, deduped = set(), []
    for it in sorted(raw, key=lambda x: -x["dt"].timestamp()):
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)

    clusters = cluster(deduped)
    records = [shape(c) for c in clusters]
    records.sort(key=lambda r: r["ts"], reverse=True)

    payload = {
        "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sources_ok": sum(1 for _, _, e in report if not e),
        "sources_total": len(report),
        "items": records,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    dead = [n for n, _, e in report if e]
    print(f"\n{len(deduped)} headlines -> {len(records)} stories"
          f"   ({payload['sources_ok']}/{len(report)} feeds ok)")
    if dead:
        print("dead feeds:", ", ".join(dead))
    if payload["sources_ok"] == 0:
        print("ERROR: every feed failed — not overwriting a good feed.json", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
