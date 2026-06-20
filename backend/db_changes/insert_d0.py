import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D0"
topic = "Introduction to Data Structures"

base_content = """
A data structure is a way of organizing, storing, and managing data in a computer so that it can be accessed and modified efficiently. Data structures are not just storage containers — they define how data is arranged in memory and how operations like insertion, deletion, search, and traversal are performed on it.

Every program works with data. Without structure, data is just a pile of values with no meaningful relationship. A data structure gives that data shape, order, and rules — making it possible for algorithms to work on it predictably and efficiently.

What an algorithm is:
An algorithm is a step-by-step procedure to solve a problem. Data structures and algorithms are deeply connected — the right data structure makes an algorithm faster and simpler. The wrong one makes it slow or impossible to implement cleanly.

Why data organization matters:
Imagine searching for a name in an unsorted list of 10 million entries versus a sorted, indexed one. The difference is not just speed — it determines whether a solution is practical at all. Data structures make the difference between O(n) and O(log n), between milliseconds and minutes.

Linear vs Non-linear structures:
Data structures are broadly divided into two categories.

Linear structures store data in a sequential order where each element has exactly one predecessor and one successor except the first and last. Examples: Arrays, Linked Lists, Stacks, Queues.

Non-linear structures store data in a hierarchical or networked way where one element can connect to many others. Examples: Trees, Graphs.

Efficiency idea:
Choosing a data structure is always a tradeoff between time and space. Some structures give fast access but slow insertion. Others give flexible size but slow search. Understanding these tradeoffs is the entire point of studying data structures.

The best data structure is not the most complex one, but the one that matches the required operations.

Why choosing the right structure matters:
Using an array when you need frequent insertions in the middle is inefficient. Using a linked list when you need random access by index is equally inefficient. The choice of data structure directly determines the performance and simplicity of your solution.

Where DSA is used:
Data structures appear in every area of software. Databases use B-trees for indexing. Operating systems use queues for scheduling. Compilers use stacks for expression parsing. Browsers use trees for the DOM. Social networks use graphs for connections.
"""

examples = """
Example 1 — Simple (to-do list):
A to-do list is a linear structure. Each task follows the previous one. You can add to the end, remove from any position, and read in order. This maps to an array or linked list.

Example 2 — Non-linear (employee hierarchy):
A company's employee hierarchy is a non-linear structure. The CEO is at the top, managers branch below, and employees sit under managers. No single chain connects them all. This maps to a tree.

Example 3 — Concrete comparison (sorted contacts vs unsorted list):
Your phone's contact list finds "Rahul" instantly because contacts are stored in sorted, indexed order. If contacts were stored as an unsorted pile, your phone would have to check every single contact one by one every time you searched. This is the direct difference a data structure makes — same data, completely different performance based on how it is organized.
"""

key_points = """
- A data structure organizes data so it can be stored, accessed, and modified efficiently
- Algorithms and data structures are inseparable — the right structure makes algorithms faster and simpler
- Linear structures store elements sequentially: Arrays, Linked Lists, Stacks, Queues
- Non-linear structures store elements hierarchically or as networks: Trees, Graphs
- Every data structure involves a tradeoff between time efficiency and space efficiency
- Access, insertion, deletion, and traversal costs differ across structures
- The right structure reduces both time complexity and code complexity
- The best data structure is not the most complex — it is the one that fits the required operations
- Choosing the wrong structure makes even correct solutions impractical at scale
- DSA is used in databases, operating systems, compilers, browsers, and network systems
"""

misconceptions = """
- "Data structures are just arrays and lists" — Arrays and lists are only two examples. Trees, Graphs, and Sets are equally fundamental and widely used.
- "DSA is only needed for interviews" — Every real software system relies on data structure choices. Performance issues in production are often the result of poor structure decisions made early.
- "Any structure works as long as the logic is correct" — Correctness and efficiency are separate concerns. A correct but wrong-structure solution can be too slow to be usable in practice.
- "Non-linear structures are advanced and rarely used" — Trees are used in every database and file system. Graphs model every network, map, and social platform.
- "More complex structure always means better solution" — The goal is to match the structure to the problem. Overcomplicating the structure adds implementation cost without benefit.
"""

real_world_use = """
- Databases use B-trees and hash indexes to retrieve records in milliseconds from millions of rows
- Operating systems use queues to manage process scheduling and execution order
- Browsers use tree structures to represent and render HTML pages
- Compilers use stacks to parse expressions and manage function call depth
- Navigation systems use graphs and shortest-path algorithms to find routes
- Social networks model user connections as graphs
"""

next_concept_link = """
The first concrete data structure to study is the Array — the simplest and most fundamental linear structure. Arrays introduce the idea of indexed, contiguous memory storage, which becomes the reference point for comparing every other structure that follows.
"""

# --- Insert or Update ---

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO concept_resources (
        concept_id,
        topic,
        base_content,
        examples,
        key_points,
        misconceptions,
        real_world_use,
        next_concept_link
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(concept_id) DO UPDATE SET
        topic           = excluded.topic,
        base_content    = excluded.base_content,
        examples        = excluded.examples,
        key_points      = excluded.key_points,
        misconceptions  = excluded.misconceptions,
        real_world_use  = excluded.real_world_use,
        next_concept_link = excluded.next_concept_link
""", (
    concept_id,
    topic,
    base_content.strip(),
    examples.strip(),
    key_points.strip(),
    misconceptions.strip(),
    real_world_use.strip(),
    next_concept_link.strip()
))

conn.commit()
conn.close()

print(f"Success — concept '{concept_id}: {topic}' inserted or updated in concept_resources.")