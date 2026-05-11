#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timezone
from ics import Calendar, Event

# === CONFIG ===
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
PERSONAL_DATABASE_ID = "2aa20c51aebe80439c52e60fdf45dd31"
WORK_DATABASE_ID = "29520c51aebe80798d10db123c986db0"  # <-- paste your Work database ID here
PAST_DATABASE_ID = "35d20c51aebe819486f5cc5757ad9281"

# === FUNCTIONS ===
def notion_query_database(token, database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    all_results = []
    payload = {}
    while True:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Notion API error {resp.status_code}: {resp.text}")
        data = resp.json()
        all_results.extend(data["results"])
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return all_results

def extract_event(event):
    try:
        title_prop = (
            event["properties"].get(" Calendar")
            or event["properties"].get("Name")
            or event["properties"].get("Title")
        )
        title = title_prop["title"][0]["plain_text"]
        start = event["properties"]["Time"]["date"]["start"]
        end = event["properties"]["Time"]["date"].get("end", start)
        steps_list = event["properties"].get("Actionable Steps", {}).get("rich_text", [])
        description = steps_list[0]["plain_text"] if steps_list else ""
        return {"title": title, "start": start, "end": end, "description": description}
    except (KeyError, IndexError, TypeError):
        return None

def create_ics(events, output_file="past_feed.ics"):
    cal = Calendar()
    for event_data in events:
        if not event_data:
            continue
        e = Event()
        e.name = event_data["title"]
        e.begin = event_data["start"]
        e.end = event_data["end"]
        e.description = event_data["description"]
        cal.events.add(e)
    with open(output_file, "w") as f:
        f.writelines(cal)

def main():
    token = NOTION_TOKEN
    if not token:
        raise RuntimeError("NOTION_TOKEN environment variable not set")

    print("Querying Personal database...")
    personal_events = notion_query_database(token, PERSONAL_DATABASE_ID)

    print("Querying Work database...")
    work_events = notion_query_database(token, WORK_DATABASE_ID)

    all_raw = personal_events + work_events
    print(f"Total events fetched: {len(all_raw)}")

    extracted = [extract_event(e) for e in all_raw]
    valid = [e for e in extracted if e is not None]
    print(f"Valid events: {len(valid)}")

    create_ics(valid, "past_feed.ics")

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"ICS feed updated at {now}")

if __name__ == "__main__":
    main()
