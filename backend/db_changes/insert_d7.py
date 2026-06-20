import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D7"
topic = "Graphs"

base_content = """
A graph is a non-linear data structure that consists of a set of vertices (also called nodes) connected by edges. Unlike trees, graphs have no strict parent-child hierarchy and no single root. Any vertex can connect to any other vertex, and connections can go in any direction.

Think of a map of cities. Each city is a vertex. Each road connecting two cities is an edge. Some roads are one-way (directed). Some roads have distances (weighted). The entire road network is a graph. This is exactly how a graph data structure works.

Core terminology:
- vertex — a node in the graph that holds data
- edge — a connection between two vertices
- adjacent — two vertices are adjacent if they share an edge
- degree — the number of edges connected to a vertex
- path — a sequence of vertices connected by edges
- cycle — a path that starts and ends at the same vertex
- connected graph — every vertex is reachable from every other vertex
- disconnected graph — some vertices cannot be reached from others

Undirected graph:
    A --- B
    |     |
    C --- D

Directed graph:
    A --> B
    |     |
    v     v
    C --> D

Types of graphs:
- Undirected graph: A -- B means A connects to B and B connects to A
- Directed graph (digraph): A --> B means A connects to B but not the reverse
- Weighted graph: A --5-- B means the edge between A and B has weight 5
- Unweighted graph: all edges are treated equally
- Cyclic graph: contains at least one cycle — A --> B --> C --> A
- Acyclic graph: contains no cycles — DAG used in task scheduling

Graph representations:

Adjacency List — most common, memory efficient for sparse graphs:
graph = {
    "A": ["B", "C"],
    "B": ["A", "D"],
    "C": ["A", "D"],
    "D": ["B", "C"]
}

directed_graph = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["D"],
    "D": []
}

Adjacency Matrix — good for dense graphs, O(1) edge lookup:
matrix = [
    [0, 1, 1, 0],  # vertex 0 connects to 1 and 2
    [1, 0, 0, 1],  # vertex 1 connects to 0 and 3
    [1, 0, 0, 1],  # vertex 2 connects to 0 and 3
    [0, 1, 1, 0]   # vertex 3 connects to 1 and 2
]
print(matrix[0][1])  # 1 — edge exists — O(1)

Weighted adjacency list:
weighted_graph = {
    "A": [("B", 5), ("C", 3)],
    "B": [("A", 5), ("D", 2)],
    "C": [("A", 3), ("D", 7)],
    "D": [("B", 2), ("C", 7)]
}
# ("B", 5) means edge to B with weight 5

Adding vertices and edges dynamically:
class Graph:
    def __init__(self):
        self.adjacency_list = {}

    def add_vertex(self, vertex):
        if vertex not in self.adjacency_list:
            self.adjacency_list[vertex] = []

    def add_edge(self, v1, v2):
        self.adjacency_list[v1].append(v2)
        self.adjacency_list[v2].append(v1)  # remove for directed graph

    def remove_edge(self, v1, v2):
        self.adjacency_list[v1].remove(v2)
        self.adjacency_list[v2].remove(v1)

    def display(self):
        for vertex, neighbors in self.adjacency_list.items():
            print(f"{vertex} -> {neighbors}")

g = Graph()
g.add_vertex("A")
g.add_vertex("B")
g.add_vertex("C")
g.add_edge("A", "B")
g.add_edge("A", "C")
g.add_edge("B", "C")
g.display()
# A -> ['B', 'C']
# B -> ['A', 'C']
# C -> ['A', 'B']

BFS — Breadth First Search — explores level by level using a queue:
from collections import deque

def bfs(graph, start):
    visited = set()
    queue = deque([start])
    visited.add(start)
    order = []

    while queue:
        vertex = queue.popleft()
        order.append(vertex)
        for neighbor in graph[vertex]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order

graph = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B"],
    "F": ["C"]
}

print(bfs(graph, "A"))
# ['A', 'B', 'C', 'D', 'E', 'F']

DFS — Depth First Search — explores as deep as possible using a stack or recursion:
def dfs(graph, start, visited=None):
    if visited is None:
        visited = set()
    visited.add(start)
    order = [start]
    for neighbor in graph[start]:
        if neighbor not in visited:
            order += dfs(graph, neighbor, visited)
    return order

print(dfs(graph, "A"))
# ['A', 'B', 'D', 'E', 'C', 'F']

BFS vs DFS:
BFS — uses queue — explores wide first — good for shortest path in unweighted graph
DFS — uses stack or recursion — explores deep first — good for cycle detection and path finding

Time and space complexity:
Operation          | Adjacency List | Adjacency Matrix
Add vertex         | O(1)           | O(V squared)
Add edge           | O(1)           | O(1)
Remove edge        | O(E)           | O(1)
Check edge exists  | O(V)           | O(1)
BFS / DFS          | O(V + E)       | O(V squared)
Space              | O(V + E)       | O(V squared)

V = number of vertices, E = number of edges
Adjacency list is preferred for sparse graphs. Adjacency matrix is preferred for dense graphs where O(1) edge lookup is needed frequently.

Strengths:
- Most flexible data structure — can model any relationship between entities
- Supports both directed and undirected relationships
- Weighted edges allow modeling of costs, distances, and priorities
- BFS and DFS enable powerful traversal and search capabilities
- Foundation for shortest path, network flow, and dependency resolution algorithms

Weaknesses:
- More complex to implement than linear structures or trees
- Traversal costs O(V + E) — can be expensive for large dense graphs
- Adjacency matrix wastes memory for sparse graphs — O(V squared) space
- Cycle detection and path finding require careful implementation
- No natural ordering of elements unlike arrays or BSTs

When to use graphs:
- When modeling relationships and connections between entities
- When finding shortest paths between points
- When detecting cycles or dependencies
- When modeling networks — social, computer, road, or task networks

When not to use graphs:
- When data is hierarchical with no cycles — use a tree instead
- When data is sequential — use arrays or linked lists
- When relationships are simple and do not need traversal

Comparison with trees:
A tree is a special case of a graph — specifically a connected, acyclic, undirected graph with one root. Every tree is a graph but not every graph is a tree. Graphs allow cycles, multiple paths between nodes, and no single root. Trees are simpler and more constrained. Graphs are more general and flexible.

The best data structure is not the most complex one, but the one that matches the required operations.
"""

examples = """
Example 1 — Simple (building and displaying a graph):
graph = {
    "A": ["B", "C"],
    "B": ["A", "D"],
    "C": ["A", "D"],
    "D": ["B", "C"]
}

for vertex, neighbors in graph.items():
    print(f"{vertex} -> {neighbors}")

# A -> ['B', 'C']
# B -> ['A', 'D']
# C -> ['A', 'D']
# D -> ['B', 'C']

Example 2 — Slightly deeper (BFS and DFS on same graph):
graph = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B"],
    "F": ["C"]
}

print("BFS:", bfs(graph, "A"))
# BFS: ['A', 'B', 'C', 'D', 'E', 'F'] — level by level

print("DFS:", dfs(graph, "A"))
# DFS: ['A', 'B', 'D', 'E', 'C', 'F'] — deep first

Example 3 — Operation (detecting a cycle using DFS):
def has_cycle(graph, start, visited=None, parent=None):
    if visited is None:
        visited = set()
    visited.add(start)
    for neighbor in graph[start]:
        if neighbor not in visited:
            if has_cycle(graph, neighbor, visited, start):
                return True
        elif neighbor != parent:
            return True
    return False

cyclic_graph = {
    "A": ["B"],
    "B": ["A", "C"],
    "C": ["B", "A"]
}

acyclic_graph = {
    "A": ["B"],
    "B": ["A", "C"],
    "C": ["B"]
}

print(has_cycle(cyclic_graph, "A"))   # True
print(has_cycle(acyclic_graph, "A"))  # False

Example 4 — Concrete real-world comparison:
A social network is a graph. Each user is a vertex. Each friendship is an edge.
Finding mutual friends is a set intersection on neighbor lists.

social_network = {
    "Alice": ["Bob", "Charlie", "David"],
    "Bob": ["Alice", "Charlie"],
    "Charlie": ["Alice", "Bob", "Eve"],
    "David": ["Alice"],
    "Eve": ["Charlie"]
}

alice_friends = set(social_network["Alice"])
bob_friends = set(social_network["Bob"])
mutual = alice_friends & bob_friends
print("Mutual friends:", mutual)   # {'Charlie'}

david_friends = set(social_network["David"])
suggestions = set()
for friend in social_network["David"]:
    for fof in social_network[friend]:
        if fof != "David" and fof not in david_friends:
            suggestions.add(fof)
print("Suggestions for David:", suggestions)
"""

key_points = """
- Graph consists of vertices (nodes) and edges (connections)
- Vertices store data — edges define relationships
- Undirected graph — edges go both ways
- Directed graph — edges have a specific direction
- Weighted graph — edges carry a cost or distance value
- Adjacency list is memory efficient — preferred for sparse graphs
- Adjacency matrix gives O(1) edge lookup — preferred for dense graphs
- BFS uses a queue — explores level by level — good for shortest path
- DFS uses a stack or recursion — explores deep first — good for cycle detection
- BFS and DFS both run in O(V + E) with adjacency list
- A tree is a special case of a graph — connected, acyclic, with one root
- Graphs can contain cycles — trees cannot
- Degree of a vertex is the number of edges connected to it
- Graphs are the foundation for shortest path, network flow, and dependency algorithms
"""

misconceptions = """
- "Graphs and trees are completely different structures" — A tree is actually a special type of graph. Specifically it is a connected acyclic undirected graph. Every tree is a graph but not every graph is a tree.
- "Graphs must be connected" — Graphs can be disconnected. Some vertices may not be reachable from others. Disconnected graphs are valid and common in real-world modeling.
- "BFS and DFS always give the same result" — BFS and DFS visit different nodes in different orders. BFS explores wide first level by level. DFS explores deep first along one path. They are suited for different problems.
- "Adjacency matrix is always better because edge lookup is O(1)" — Adjacency matrix uses O(V squared) space. For sparse graphs with few edges, this wastes enormous memory. Adjacency list is almost always preferred unless the graph is very dense.
- "Weighted graphs are only for maps and distances" — Weights can represent anything — time, cost, capacity, priority, probability. They are used in network flow, task scheduling, and recommendation systems.
- "Graphs are too complex for practical use" — Graphs are used in every major software system. Social networks, maps, compilers, package managers, and recommendation engines are all graph problems.
"""

real_world_use = """
- Social networks model users and friendships as graphs for friend suggestions and influencer detection
- Navigation systems like Google Maps use weighted directed graphs to find shortest routes
- Internet routing protocols use graphs to determine the best path for data packets
- Package managers like pip and npm use directed acyclic graphs to resolve dependencies
- Recommendation engines use graphs to find connections between users and items
- Compilers use graphs to detect circular dependencies and optimize instruction order
"""

next_concept_link = """
Graphs complete the Data Structures module by providing the most general and flexible way to model relationships between any entities. With all eight data structures covered — from the simplicity of arrays to the power of graphs — the natural next step is to move into version control with Git, starting with what version control is and why managing change in software systems requires its own dedicated structure and tooling.
"""

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO concept_resources (
        concept_id, topic, base_content, examples, key_points,
        misconceptions, real_world_use, next_concept_link
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(concept_id) DO UPDATE SET
        topic             = excluded.topic,
        base_content      = excluded.base_content,
        examples          = excluded.examples,
        key_points        = excluded.key_points,
        misconceptions    = excluded.misconceptions,
        real_world_use    = excluded.real_world_use,
        next_concept_link = excluded.next_concept_link
""", (
    concept_id, topic,
    base_content.strip(), examples.strip(), key_points.strip(),
    misconceptions.strip(), real_world_use.strip(), next_concept_link.strip()
))

conn.commit()
conn.close()
print(f"Success — concept '{concept_id}: {topic}' inserted or updated in concept_resources.")