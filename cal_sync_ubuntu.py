import os
import sqlite3
import time
import logging
import sys
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ========== CONFIG ==========
BASE_DIR = "/opt/elh/cal_sync"
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "secrets/cloud-auth.json")
IMPERSONATE_USER = "svc.email@elhaynes.org"

# Target Calendar ID (test2-ll-view or your final production one)
TARGET_CALENDAR_ID = "c_b95a4104af32fe7f5d37497542b1e442157dc08a6594a70ea14aad02fc481693@group.calendar.google.com"

# MAP: Source Identifier -> Friendly Name
# This allows you to use long IDs in SOURCE_CALENDAR_NAMES but see nice labels
FRIENDLY_NAMES = {
    "operations@elhaynes.org": "Operations",
    "svc.email@elhaynes.org": "IIQ Events",
    "c_1e64da3ce14d22f2020ce55dc8f36a9e99d7677ab7918e7c79538868917da5ee@group.calendar.google.com": "Cross Campus"
}

# MAP: Source Identifier -> Google Color ID
# 9: Blue, 8: Gray, 7: Green, 10: Light Blue
COLOR_MAP = {
    "operations@elhaynes.org": "8",
    "svc.email@elhaynes.org": "7",
    "c_1e64da3ce14d22f2020ce55dc8f36a9e99d7677ab7918e7c79538868917da5ee@group.calendar.google.com": "10"
}

SOURCE_CALENDAR_NAMES = list(FRIENDLY_NAMES.keys())

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DB_FILE = os.path.join(BASE_DIR, "mirror_map_demo4.db")
LOG_FILE = os.path.join(BASE_DIR, "sync.log")
LOCK_FILE = os.path.join(BASE_DIR, "sync.lock")

PAST_DAYS = 30
FUTURE_DAYS = 45

# Logging setup
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ========== LOCKFILE LOGIC ==========
def is_process_running(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

# ========== AUTH & DB ==========
def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds.with_subject(IMPERSONATE_USER))

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS event_map (source_calendar_id TEXT, source_event_id TEXT, target_event_id TEXT, PRIMARY KEY (source_calendar_id, source_event_id))")
    return conn

# ========== HELPERS ==========
def list_calendars(service):
    calendars = {}
    page_token = None
    while True:
        resp = service.calendarList().list(pageToken=page_token).execute()
        for item in resp.get("items", []):
            calendars[item["summary"].lower()] = item["id"]
        page_token = resp.get("nextPageToken")
        if not page_token: break
    return calendars

def find_calendar_id(calendars, identifier):
    if "@" in identifier: return identifier
    return calendars.get(identifier.lower())

# ========== MAIN ==========
def main():
    # PID Lock Check
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if is_process_running(old_pid):
                logging.warning(f"Sync already running (PID {old_pid}). Skipping.")
                return
        except: pass

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        logging.info("--- Sync Started ---")
        service = get_calendar_service()
        conn = init_db()
        cur = conn.cursor()

        cals = list_calendars(service)
        sources = [(n, find_calendar_id(cals, n)) for n in SOURCE_CALENDAR_NAMES if find_calendar_id(cals, n)]

        now = datetime.now(timezone.utc)
        t_min, t_max = (now - timedelta(days=PAST_DAYS)).isoformat(), (now + timedelta(days=FUTURE_DAYS)).isoformat()
        seen_keys = set()

        for friendly_id, cid in sources:
            display_name = FRIENDLY_NAMES.get(friendly_id, friendly_id)
            events = service.events().list(calendarId=cid, timeMin=t_min, timeMax=t_max, singleEvents=True).execute().get("items", [])
            
            for ev in events:
                if ev.get("status") == "cancelled": continue
                sid = ev["id"]
                seen_keys.add((cid, sid))

                mirrored = {
                    "summary": f"[{display_name}] {ev.get('summary', 'Busy')}",
                    "start": ev["start"],
                    "end": ev["end"],
                    "location": ev.get("location", ""),
                    "description": ev.get("description", ""),
                    "colorId": COLOR_MAP.get(friendly_id, "8")
                }

                cur.execute("SELECT target_event_id FROM event_map WHERE source_calendar_id=? AND source_event_id=?", (cid, sid))
                row = cur.fetchone()

                if row:
                    service.events().update(calendarId=TARGET_CALENDAR_ID, eventId=row[0], body=mirrored).execute()
                else:
                    created = service.events().insert(calendarId=TARGET_CALENDAR_ID, body=mirrored).execute()
                    cur.execute("INSERT INTO event_map VALUES (?, ?, ?)", (cid, sid, created["id"]))
                    conn.commit()
                time.sleep(0.1)

        # Cleanup Deletions
        cur.execute("SELECT source_calendar_id, source_event_id, target_event_id FROM event_map")
        for scid, seid, teid in cur.fetchall():
            if (scid, seid) not in seen_keys:
                try:
                    service.events().delete(calendarId=TARGET_CALENDAR_ID, eventId=teid).execute()
                except: pass
                cur.execute("DELETE FROM event_map WHERE source_calendar_id=? AND source_event_id=?", (scid, seid))
                conn.commit()

        logging.info("--- Sync Complete ---")
    finally:
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()
