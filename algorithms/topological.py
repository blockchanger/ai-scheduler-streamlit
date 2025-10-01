from collections import deque, defaultdict
from typing import List, Tuple

def topo_sort(nodes: List[str], edges: List[Tuple[str, str]]) -> List[str]:
    in_deg = {n: 0 for n in nodes}
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        in_deg[v] += 1
    q = deque([n for n, d in in_deg.items() if d == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                q.append(v)
    if len(order) != len(nodes):
        raise ValueError("Cycle detected in dependencies.")
    return order
