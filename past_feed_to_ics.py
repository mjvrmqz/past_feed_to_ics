#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timezone
from ics import Calendar, Event

# === CONFIG ===
NOTION_TOKEN     = os.environ.get("NOTION_TOKEN", "")
PERSONAL_TIME_DB = "2aa20c51aebe80439c52e60fdf45dd31"
WORK_DB          = "29520c51aebe80798d10db123c986db0"
PAST_FEED_DB     = "35d20c51aebe819486f5cc5757ad9281"

if not NOTION_TOKEN:
    raise RuntimeError("NOTION_TOKEN environment variable not set. Copy .env.example to .env and fill it in.")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# === HELPERS ===

def query_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    results = []
    payload = {}
    while True:
        resp = requests.post(url, headers=HEADERS, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Notion API error {resp.status_code}: {resp.text}")
        data = resp.json()
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results

def get_existing_titles(database_id):
    pages = query_database(database_id)
    titles = set()
    for page in pages:
        try:
            title = page["properties"][" Calendar"]["title"][0]["plain_text"]
            titles.add(title)
        except (KeyError, IndexError):
            continue
    return titles

def extract_props(page):
    props = page["properties"]

    def get_title():
        try:
            return props[" Calendar"]["title"][0]["plain_text"]
        except (KeyError, IndexError):
            return None

    def get_select(field):
        try:
            return props[field]["select"]["name"]
        except (KeyError, TypeError):
            return None

    def get_multi_select(field):
        try:
            return [o["name"] for o in props[field]["multi_select"]]
        except (KeyError, TypeError):
            return []

    def get_rich_text(field):
        try:
            items = props[field]["rich_text"]
            return items[0]["plain_text"] if items else ""
        except (KeyError, IndexError):
            return ""

    def get_number(field):
        try:
            return props[field]["number"]
        except (KeyError, TypeError):
            return None

    def get_date(field):
        try:
            return props[field]["date"]
        except (KeyError, TypeError):
            return None

    return {
        "title":            get_title(),
        "time":             get_date("Time"),
        "actionable_steps": get_rich_text("Actionable Steps"),
        "done":             get_select("Done?"),
        "reflection":       get_select("Reflection"),
        "priority":         get_select("Priority"),
        "why":              get_select("Why?"),
        "hours":            get_number("Hours"),
        "block":            get_multi_select("Block"),
    }

def build_page_payload(props):
    properties = {
        " Calendar": {
            "title": [{"type": "text", "text": {"content": props["title"]}}]
        },
        "Actionable Steps": {
            "rich_text": [{"type": "text", "text": {"content": props["actionable_steps"]}}]
            if props["actionable_steps"] else {"rich_text": []}
        },
    }
    if props["time"]:
        properties["Time"] = {"date": props["time"]}
    if props["done"]:
        properties["Done?"] = {"select": {"name": props["done"]}}
    if props["reflection"]:
        properties["Reflection"] = {"select": {"name": props["reflection"]}}
    if props["priority"]:
        properties["Priority"] = {"select": {"name": props["priority"]}}
    if props["why"]:
        properties["Why?"] = {"select": {"name": props["why"]}}
    if props["hours"] is not None:
        properties["Hours"] = {"number": props["hours"]}
    if props["block"]:
        properties["Block"] = {"multi_select": [{"name": n} for n in props["block"]]}
    return {
        "parent": {"database_id": PAST_FEED_DB},
        "properties": properties,
    }

def create_page(payload):
    resp = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to create page: {resp.status_code} {resp.text}")
    return resp.json()

def create_ics(pages, output_file="past_feed.ics"):
    cal = Calendar()
    for page in pages:
        try:
            title = page["properties"][" Calendar"]["title"][0]["plain_text"]
            time_prop = page["properties"]["Time"]["date"]
            if not time_prop:
                continue
            start = time_prop["start"]
            end = time_prop.get("end") or start
            steps_list = page["properties"]["Actionable Steps"]["rich_text"]
            description = steps_list[0]["plain_text"] if steps_list else ""
        except (KeyError, IndexError, TypeError):
            continue
        e = Event()
        e.name = title
        e.begin = start
        e.end = end
        e.description = description
        cal.events.add(e)
    with open(output_file, "w") as f:
        f.writelines(cal)
    print(f"  Wrote {output_file}")

# === MAIN ===

def main():
    print("Fetching existing Past Feed entries...")
    existing_titles = get_existing_titles(PAST_FEED_DB)
    print(f"  {len(existing_titles)} existing entries found")

    print("Fetching Personal Time entries...")
    personal_pages = query_database(PERSONAL_TIME_DB)
    print(f"  {len(personal_pages)} entries")

    print("Fetching Work entries...")
    work_pages = query_database(WORK_DB)
    print(f"  {len(work_pages)} entries")

    all_pages = personal_pages + work_pages
    skipped = 0
    created = 0

    for page in all_pages:
        props = extract_props(page)
        if not props["title"]:
            skipped += 1
            continue
        if props["title"] in existing_titles:
            skipped += 1
            continue
        payload = build_page_payload(props)
        create_page(payload)
        existing_titles.add(props["title"])
        created += 1
        print(f"  + {props['title']}")

    print(f"\nDone. Created: {created}, Skipped: {skipped}")

    print("\nGenerating ICS feed from Past Feed...")
    past_feed_pages = query_database(PAST_FEED_DB)
    create_ics(past_feed_pages, output_file="past_feed.ics")

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"Feed updated at {now}")

if __name__ == "__main__":
    main()
