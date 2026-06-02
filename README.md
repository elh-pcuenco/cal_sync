# Calendar Sync

## Overview

Calendar Sync is a Python-based utility that synchronizes events from multiple Google Calendars into a single destination calendar, creating a consolidated "single pane of glass" view of organizational schedules.

The application is designed to provide visibility across multiple source calendars without requiring users to subscribe to numerous calendars individually. Events are mirrored from source calendars into a designated destination calendar and kept synchronized on a scheduled basis.

## Features

* Synchronizes events from multiple Google Calendars into a single destination calendar.
* Maintains a mapping between source and mirrored events.
* Updates destination events when source events change.
* Removes mirrored events when source events are deleted.
* Supports recurring synchronization through cron scheduling.
* Uses a local SQLite database to track event mappings.
* Authenticates using a Google Workspace service account with Domain-Wide Delegation.

## Environment

* Ubuntu Linux
* Python 3.x
* Google Calendar API
* SQLite
* Service Account Authentication

## Directory Structure

```text
cal_sync/
├── cal_sync_ubuntu.py      # Main synchronization script
├── mirror_map_demo4.db     # Event mapping database (not committed)
├── sync.log                # Synchronization log file (not committed)
├── secrets/                # Service account credentials (not committed)
├── venv/                   # Python virtual environment (not committed)
├── .gitignore
└── README.md
```

## Authentication

The application uses a Google Cloud Service Account with Domain-Wide Delegation enabled.

Required Google API scopes include:

* https://www.googleapis.com/auth/calendar

The service account credentials file is stored locally within the `secrets` directory and is intentionally excluded from source control.

## How It Works

1. The script reads the configured list of source calendars.
2. Events are retrieved from each source calendar.
3. The application compares source events against previously synchronized events stored in the SQLite mapping database.
4. New events are created in the destination calendar.
5. Updated events are modified in the destination calendar.
6. Deleted source events are removed from the destination calendar.
7. Event mappings are updated in the local database.

## Scheduling

The synchronization job is executed through cron.

Example:

```cron
0 6,14 * * 1-5 root /opt/elh/cal_sync/venv/bin/python3 /opt/elh/cal_sync/cal_sync_ubuntu.py
```

This example runs the synchronization at 6:00 AM and 2:00 PM Monday through Friday.

## Logging

Synchronization activity is written to:

```text
sync.log
```

Logs include:

* Synchronization start/end times
* Event creation
* Event updates
* Event deletions
* Errors and exceptions

## Installation

Clone the repository:

```bash
git clone git@github.com:elh-pcuenco/cal_sync.git
cd cal_sync
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the required directories:

```bash
mkdir secrets
```

Place the Google service account JSON file in the `secrets` directory.

## Security

The following items are intentionally excluded from source control:

* Service account credentials
* Private keys
* SQLite databases
* Log files
* Virtual environments

Refer to `.gitignore` for the full exclusion list.

## Use Case

This project was developed to provide a consolidated calendar view for organizational scheduling, allowing authorized users to view events from multiple Google Calendars in a single destination calendar while maintaining the original source calendars as the system of record.

## Author

Pete Cuenco
E.L. Haynes Public Charter School
