#!/usr/bin/env python3
import requests
import sys
import time

# CHANGE THIS if one instance goes down
SEARXNG_INSTANCE = "https://searx.be"

def search(query, limit=5):
    url = f"{SEARXNG_INSTANCE}/search"
    params = {
        "q": query,
        "format": "json",
        "language": "en",
        "categories": "general"
    }

    headers = {
        "User-Agent": "Terminal-AI/1.0"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print("[ERROR] API request failed:", e)
        return []

    results = []
    for r in data.get("results", [])[:limit]:
        results.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content")
        })

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 searxng_client.py \"your query\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"[SEARCH] {query}\n")

    results = search(query)

    if not results:
        print("No results found.")
        sys.exit(0)

    for i, r in enumerate(results, 1):
        print(f"#{i} {r['title']}")
        print(r['url'])
        if r['content']:
            print(r['content'][:300])
        print("-" * 60)
        time.sleep(0.3)
