from typing import List, Dict, Tuple
from .topological import topo_sort

def compute_cpm(tasks: List[Dict]) -> Tuple[int, Dict[str, Dict]]:
    """
    tasks: [{id, durationDays, dependsOn}]
    Returns: (projectDurationDays, info_by_task_id)
    """
    id_to = {t["id"]: t for t in tasks}
    nodes = [t["id"] for t in tasks]
    edges = [(p, t["id"]) for t in tasks for p in t.get("dependsOn", [])]
    order = topo_sort(nodes, edges)

    ES, EF = {}, {}
    for tid in order:
        t = id_to[tid]
        es = max([EF[p] for p in t.get("dependsOn", [])], default=0)
        ES[tid] = es
        EF[tid] = es + int(t["durationDays"])

    project_duration = max(EF.values(), default=0)

    LS, LF = {}, {}
    succs = {n: [v for (u, v) in edges if u == n] for n in nodes}
    for tid in reversed(order):
        lf = min([LS[s] for s in succs[tid]], default=project_duration)
        LF[tid] = lf
        LS[tid] = lf - int(id_to[tid]["durationDays"])

    info = {}
    for tid in nodes:
        slack = LS[tid] - ES[tid]
        info[tid] = dict(es=ES[tid], ef=EF[tid], ls=LS[tid], lf=LF[tid],
                         slack=slack, critical=(slack == 0))
    return project_duration, info
