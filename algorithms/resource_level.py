from typing import Dict, List
from dateutil import parser as dtparser
from datetime import timedelta, date
from .cpm import compute_cpm

def is_weekend(d: date) -> bool:
    # Monday=0 ... Sunday=6
    return d.weekday() >= 5

def add_working_days(start: date, offset_days: int, skip_weekends: bool) -> date:
    """
    Convert a working-day 'slot' index to a calendar date.
    If skip_weekends is False, it's just start + offset_days (calendar days).
    If True, weekends (Sat/Sun) are skipped while counting.
    """
    if not skip_weekends:
        return start + timedelta(days=offset_days)

    d = start
    added = 0
    while added < offset_days:
        d = d + timedelta(days=1)
        if not is_weekend(d):
            added += 1
    return d

def schedule_with_resources(project: Dict) -> List[Dict]:
    """
    project = {
      "startDateISO": "YYYY-MM-DD",
      "resources": ["FE","BE","DS"],
      "tasks": [
        {"id":"A","name":"Define","durationDays":3,"dependsOn":[],"requiredResources":["FE"]}
      ],
      "skipWeekends": true
    }
    """
    start = dtparser.isoparse(project["startDateISO"]).date()
    tasks = project["tasks"]
    skip_weekends = bool(project.get("skipWeekends", False))

    project_duration, info = compute_cpm(tasks)
    id_to = {t["id"]: t for t in tasks}

    # usage keyed by WORKING-DAY SLOTS (0,1,2,...), not calendar dates
    usage: Dict[int, set] = {}

    def free(slot_idx: int, task_id: str) -> bool:
        t = id_to[task_id]
        dur = int(t["durationDays"])
        req = t.get("requiredResources", [])
        for s in range(slot_idx, slot_idx + dur):
            used = usage.get(s, set())
            for r in req:
                if r in used:
                    return False
        return True

    def book(slot_idx: int, task_id: str):
        t = id_to[task_id]
        dur = int(t["durationDays"])
        req = t.get("requiredResources", [])
        for s in range(slot_idx, slot_idx + dur):
            if s not in usage:
                usage[s] = set()
            for r in req:
                usage[s].add(r)

    # Schedule in order of CPM earliest start
    ordered = sorted(info.items(), key=lambda kv: kv[1]["es"])
    result = []
    for tid, meta in ordered:
        slot = meta["es"]
        while not free(slot, tid):
            slot += 1
        book(slot, tid)

        t = id_to[tid]
        dur = int(t["durationDays"])

        # Map working-day slots -> actual calendar dates (skipping weekends if requested)
        sdate = add_working_days(start, slot, skip_weekends)
        edate = add_working_days(start, slot + dur, skip_weekends)

        result.append({
            **t,
            "start": sdate.isoformat(),
            "end": edate.isoformat(),
            "earliestStart": meta["es"], "earliestFinish": meta["ef"],
            "latestStart": meta["ls"],   "latestFinish": meta["lf"],
            "slack": meta["slack"], "critical": meta["critical"]
        })
    return result
