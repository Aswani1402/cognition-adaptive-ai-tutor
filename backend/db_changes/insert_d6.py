import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D6"
topic = "Sets"

base_content = """
A set is a data structure that stores a collection of unique elements with no duplicates allowed. Unlike arrays or linked lists, a set does not care about the order of elements or their position. It only cares about one thing — whether an element exists or not.

Think of a guest list for an event. Each person can only appear once. You do not care about the order guests are listed. You only care whether a specific person is on the list or not. This is exactly how a set works.

Core properties:
- No duplicate elements — inserting an existing element has no effect
- Membership testing is the primary operation
- No guaranteed order in most implementations
- Elements must be hashable in Python sets (immutable types like int, string, tuple)

Creating and using sets in Python:
s = {1, 2, 3, 4, 5}
print(s)          # {1, 2, 3, 4, 5}

# From a list — duplicates removed automatically
s = set([1, 2, 2, 3, 3, 3, 4])
print(s)          # {1, 2, 3, 4}

# Empty set — must use set(), not {} (that creates a dict)
empty = set()
print(empty)      # set()

Insertion — O(1) average:
s = {1, 2, 3}
s.add(4)
print(s)          # {1, 2, 3, 4}

# Adding existing element has no effect
s.add(2)
print(s)          # {1, 2, 3, 4} — no change

Deletion — O(1) average:
s = {1, 2, 3, 4}
s.remove(3)       # raises KeyError if not found
print(s)          # {1, 2, 4}

s.discard(10)     # no error if not found — safer
print(s)          # {1, 2, 4}

Membership test — O(1) average:
s = {1, 2, 3, 4, 5}
print(3 in s)     # True  — O(1)
print(9 in s)     # False — O(1)

Membership test comparison — set vs list:
import time

data_list = list(range(1000000))
data_set = set(range(1000000))

start = time.time()
999999 in data_list
print("List:", time.time() - start)

start = time.time()
999999 in data_set
print("Set:", time.time() - start)
# Set is dramatically faster for membership testing

Set operations — mathematical operations:

Union — all elements from both sets:
a = {1, 2, 3}
b = {3, 4, 5}
print(a | b)          # {1, 2, 3, 4, 5}
print(a.union(b))     # {1, 2, 3, 4, 5}

Intersection — elements common to both sets:
print(a & b)               # {3}
print(a.intersection(b))   # {3}

Difference — elements in a but not in b:
print(a - b)               # {1, 2}
print(a.difference(b))     # {1, 2}

Symmetric difference — elements in either but not both:
print(a ^ b)                        # {1, 2, 4, 5}
print(a.symmetric_difference(b))    # {1, 2, 4, 5}

Subset and superset checks:
a = {1, 2}
b = {1, 2, 3, 4}
print(a.issubset(b))    # True — all of a is in b
print(b.issuperset(a))  # True — b contains all of a
print(a.isdisjoint(b))  # False — they share elements

How sets work internally:
Python sets are implemented using a hash table. When an element is added, Python computes its hash value and stores it in the hash table at the computed position. This is why membership testing is O(1) — instead of scanning every element, Python computes the hash and checks that one position directly.

This also explains why set elements must be hashable. Lists and dictionaries cannot be added to a set because they are mutable and their hash would change.

s = set()
s.add(1)          # works — int is hashable
s.add("hello")    # works — string is hashable
s.add((1, 2))     # works — tuple is hashable
s.add([1, 2])     # TypeError — list is not hashable

Ordered set behavior:
Python's built-in set is unordered. If insertion order matters, use a different approach:
data = [3, 1, 2, 1, 3, 4]
ordered_unique = list(dict.fromkeys(data))
print(ordered_unique)  # [3, 1, 2, 4]

Time complexity:
Operation        | Average Case              | Worst Case
Add              | O(1)                      | O(n)
Remove           | O(1)                      | O(n)
Membership test  | O(1)                      | O(n)
Union            | O(len(a) + len(b))        | O(len(a) + len(b))
Intersection     | O(min(len(a), len(b)))    | O(len(a) * len(b))

Worst case O(n) happens only during hash collisions — rare in practice with Python's hash implementation.

Strengths:
- Membership testing is O(1) — far faster than lists for this operation
- Automatically eliminates duplicates
- Mathematical set operations built in — union, intersection, difference
- Clean and readable syntax in Python
- Ideal for deduplication and lookup-heavy workloads

Weaknesses:
- No guaranteed order — cannot access elements by index
- Elements must be hashable — mutable types cannot be stored
- Higher memory usage than lists due to hash table overhead
- Not suitable when duplicates or position matter

When to use sets:
- When you need to check if an element exists — membership testing
- When you need to remove duplicates from a collection
- When you need mathematical set operations like union or intersection
- When order does not matter and uniqueness is required

When not to use sets:
- When you need to preserve insertion order
- When you need index-based access
- When duplicate values must be stored
- When elements are mutable types like lists or dictionaries

Comparison with lists:
Feature          | List              | Set
Duplicates       | Allowed           | Not allowed
Order            | Preserved         | Not guaranteed
Membership test  | O(n)              | O(1)
Index access     | O(1)              | Not supported
Memory           | Lower             | Higher
Use case         | Ordered collection| Unique membership

The best data structure is not the most complex one, but the one that matches the required operations.
"""

examples = """
Example 1 — Simple (deduplication):
names = ["Alice", "Bob", "Alice", "Charlie", "Bob", "Alice"]
unique_names = set(names)
print(unique_names)       # {'Alice', 'Bob', 'Charlie'}
print(len(unique_names))  # 3

Example 2 — Slightly deeper (set operations on student data):
math_students = {"Alice", "Bob", "Charlie", "David"}
science_students = {"Charlie", "David", "Eve", "Frank"}

both = math_students & science_students
print("Both:", both)            # {'Charlie', 'David'}

either = math_students | science_students
print("Either:", either)        # {'Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank'}

only_math = math_students - science_students
print("Only math:", only_math)  # {'Alice', 'Bob'}

Example 3 — Operation (fast membership testing):
visited = set()

def visit(url):
    if url in visited:
        print(f"Already visited: {url}")
        return
    visited.add(url)
    print(f"Visiting: {url}")

visit("google.com")     # Visiting: google.com
visit("youtube.com")    # Visiting: youtube.com
visit("google.com")     # Already visited: google.com
print(visited)          # {'google.com', 'youtube.com'}

Example 4 — Concrete real-world comparison:
A spam filter maintains a set of blocked email addresses. When an email arrives,
the filter checks if the sender is in the blocked set. With millions of blocked
addresses, a set checks in O(1). A list would require scanning every address — O(n).

blocked_senders = {"spam@evil.com", "phish@fake.com", "ads@junk.com"}

def is_blocked(email):
    return email in blocked_senders  # O(1)

print(is_blocked("spam@evil.com"))   # True
print(is_blocked("boss@work.com"))   # False
"""

key_points = """
- Set stores only unique elements — duplicates are automatically ignored
- Membership testing costs O(1) average — the primary strength of sets
- No guaranteed order — elements cannot be accessed by index
- Implemented internally using a hash table
- Elements must be hashable — immutable types only
- add() inserts an element — O(1) average
- remove() raises KeyError if element not found — use discard() to avoid errors
- Union combines all elements from both sets
- Intersection returns only common elements
- Difference returns elements in one set but not the other
- Symmetric difference returns elements in either but not both
- Empty set must be created with set() not {} — {} creates a dictionary
- Sets use more memory than lists due to hash table structure
- Use sets when uniqueness and fast lookup matter more than order
"""

misconceptions = """
- "Sets preserve insertion order" — Standard Python sets do not guarantee order. If order matters, use a list or dict.fromkeys() for ordered deduplication.
- "An empty set is created with {}" — {} creates an empty dictionary in Python, not a set. Always use set() for an empty set.
- "Sets are just lists without duplicates" — Sets use a hash table internally. Membership testing is O(1) in sets versus O(n) in lists. They are fundamentally different in structure and performance.
- "You can store any element in a set" — Only hashable elements can be stored. Lists, dictionaries, and other mutable types cannot be added to a set because their hash value can change.
- "Set operations like union and intersection are slow" — Union and intersection are efficient operations on sets. Intersection runs in O(min(len(a), len(b))) which is far faster than doing the same with nested loops on lists.
- "Sets are rarely used in real software" — Sets are used constantly in web crawlers, spam filters, recommendation systems, deduplication pipelines, and graph traversal algorithms.
"""

real_world_use = """
- Web crawlers use sets to track visited URLs and avoid revisiting the same page
- Spam filters use sets of blocked senders for O(1) email filtering
- Recommendation systems use set intersection to find common interests between users
- Database query engines use set operations for joins and deduplication internally
- Graph traversal algorithms like BFS and DFS use sets to track visited nodes
- Tag and category systems use sets to store unique labels per item
"""

next_concept_link = """
Sets store unique elements and excel at membership testing, but they only tell you whether something exists — not how things are connected. The next concept — Graphs — goes further by modeling relationships and connections between elements directly. A graph is the most general and flexible data structure, capable of representing networks, maps, dependencies, and any system where connections between elements matter as much as the elements themselves.
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