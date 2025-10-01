from typing import Dict, List
from dateutil import parser as dtparser
from datetime import timedelta
from .cpm import compute_cpm

def schedule_with_resources(project: Dict) -> List[Dict]:
    """
    project = {
      "startDateISO": "YYYY-MM-DD",
      "resources": ["FE","BE","DS"],
      "tasks": [
        {"id":"A","name":"Define","durationDays":3,"dependsOn":[],"requiredResources":["FE"]}
      ]
    }
    """
    start = dtparser.isoparse(project["startDateISO"]).date()
    tasks = project["tasks"]
    _, info = compute_cpm(tasks)
    id_to = {t["id"]: t for t in tasks}

    usage = {}  # day_index -> set(resource ids used)

    def free(day_idx: int, task_id: str) -> bool:
        t = id_to[task_id]
        dur = int(t["durationDays"])
        req = t.get("requiredResources", [])
        for d in range(day_idx, day_idx + dur):
            used = usage.get(d, set())
            for r in req:
                if r in used:
                    return False
        return True

    def book(day_idx: int, task_id: str):
        t = id_to[task_id]
        dur = int(t["durationDays"])
        req = t.get("requiredResources", [])
        for d in range(day_idx, day_idx + dur):
            if d not in usage:
                usage[d] = set()
            for r in req:
                usage[d].add(r)

    ordered = sorted(info.items(), key=lambda kv: kv[1]["es"])
    result = []
    for tid, meta in ordered:
        start_idx = meta["es"]
        while not free(start_idx, tid):
            start_idx += 1
        book(start_idx, tid)
        t = id_to[tid]
        sdate = start + timedelta(days=start_idx)
        edate = start + timedelta(days=start_idx + int(t["durationDays"]))
        result.append({
            **t,
            "start": sdate.isoformat(),
            "end": edate.isoformat(),
            "earliestStart": meta["es"], "earliestFinish": meta["ef"],
            "latestStart": meta["ls"],   "latestFinish": meta["lf"],
            "slack": meta["slack"], "critical": meta["critical"]
        })
    return result
