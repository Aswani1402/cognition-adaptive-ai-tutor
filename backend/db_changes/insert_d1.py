import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D1"
topic = "Arrays"

base_content = """
An array is a linear data structure that stores a fixed-size, ordered collection of elements of the same data type in contiguous memory locations. Each element is identified by a numeric index, starting at 0 in most languages. Arrays are the most fundamental data structure and form the basis for many higher-level structures.

Internal structure and memory:
When an array is declared, the system allocates a single continuous block of memory. If an integer array of size 5 is created and each integer takes 4 bytes, the system reserves 20 consecutive bytes. The starting address is stored, and any element's address is calculated as:

address = base_address + (index x element_size)

This formula makes index-based access instantaneous — O(1) — regardless of array size.

Declaring and accessing an array in Python:
arr = [10, 20, 30, 40, 50]
print(arr[0])   # 10 — first element
print(arr[2])   # 30 — third element
print(arr[-1])  # 50 — last element

Random access:
Because all elements are stored contiguously and element size is fixed, any element can be accessed directly using its index. You do not need to traverse the array to reach a specific position. This is called random access and is the defining strength of arrays.

Cache friendliness:
Arrays benefit from CPU cache behavior. When the CPU loads one element, nearby elements are also pulled into cache automatically. Sequential operations on arrays are therefore faster in practice than theoretical complexity alone suggests.

Traversing an array sequentially:
arr = [10, 20, 30, 40, 50]
for x in arr:
    print(x)
# Output: 10 20 30 40 50

Common operations:

Access by index:
arr = [10, 20, 30, 40, 50]
print(arr[3])  # 40 — O(1)

Search unsorted — O(n):
arr = [10, 20, 30, 40, 50]
for i in range(len(arr)):
    if arr[i] == 30:
        print(f"Found at index {i}")  # Found at index 2

Insertion at end — O(1):
arr = [10, 20, 30]
arr.append(40)
print(arr)  # [10, 20, 30, 40]

Insertion at middle — O(n):
arr = [10, 20, 30, 40]
arr.insert(2, 99)
print(arr)  # [10, 20, 99, 30, 40]

Deletion by index — O(n):
arr = [10, 20, 30, 40]
arr.pop(1)
print(arr)  # [10, 30, 40]

Deletion from end — O(1):
arr = [10, 20, 30, 40]
arr.pop()
print(arr)  # [10, 20, 30]

Strengths:
- Fast random access — O(1) by index
- Memory efficient — no extra pointers or metadata per element
- Cache-friendly due to contiguous memory layout
- Simple to implement and reason about
- Works well with sorting algorithms and binary search

Weaknesses:
- Fixed size in static arrays — cannot grow or shrink after declaration
- Insertion and deletion in the middle are expensive — O(n) due to shifting
- Wastes memory if allocated size is much larger than used size
- All elements must be the same data type in low-level implementations

When to use arrays:
- When size is known in advance and unlikely to change
- When fast index-based access is the primary operation
- When memory layout and cache performance matter
- When working with sorting, searching, or mathematical operations on sequences

When not to use arrays:
- When frequent insertion or deletion in the middle is needed
- When size is highly dynamic and unpredictable
- When you need to store elements of different types

Comparison with Linked List:
Arrays give O(1) access but O(n) insertion and deletion in the middle. Linked lists give O(n) access but O(1) insertion and deletion once the position is known. Arrays are contiguous in memory and cache-friendly. Linked lists are scattered in memory and not cache-friendly. Choose arrays for read-heavy workloads and linked lists for write-heavy ones.

The best data structure is not the most complex one, but the one that matches the required operations.

Types of arrays:
- One-dimensional: a simple flat list of elements
- Multi-dimensional: arrays of arrays, used for matrices and grids
- Dynamic arrays: arrays that resize automatically such as Python lists and Java ArrayLists
"""

examples = """
Example 1 — Simple (score list):
scores = [85, 90, 78, 92, 88]
print(scores[2])   # 78 — direct access, O(1)
print(scores[0])   # 85 — first element
print(len(scores)) # 5 — length of array

Example 2 — Slightly deeper (2D grid):
grid = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
print(grid[1][2])  # 6 — row 1, column 2

# Traverse entire grid
for row in grid:
    for val in row:
        print(val, end=" ")
    print()
# Output:
# 1 2 3
# 4 5 6
# 7 8 9

Example 3 — Operation (insertion in middle):
arr = [10, 20, 30, 40, 50]
arr.insert(2, 99)
print(arr)  # [10, 20, 99, 30, 40, 50]
# Elements at index 2 onwards shifted right — O(n)

Example 4 — Concrete real-world comparison:
A cinema seat booking system stores seats as an array — Seat 1 through Seat 200.
The system jumps directly to Seat 150 in O(1) because the index is known.

seats = ["empty"] * 200
seats[149] = "booked"       # Book seat 150 — O(1)
print(seats[149])           # booked

If seats were stored as an unsorted list with no index, finding seat 150 would
require checking every seat one by one — O(n). This is exactly why arrays are
used for fixed, ordered, index-accessed collections.
"""

key_points = """
- Elements are stored in contiguous memory locations
- Indexing starts at 0 in most languages
- Random access by index costs O(1) — fastest possible access
- Insertion and deletion in the middle cost O(n) due to element shifting
- Insertion and deletion at the end cost O(1) if space exists
- Search on unsorted array costs O(n)
- Search on sorted array using binary search costs O(log n)
- Static arrays have fixed size — cannot grow after declaration
- Dynamic arrays resize by allocating new memory and copying all elements
- Memory used equals size multiplied by element size — no per-element overhead
- Arrays are cache-friendly because of contiguous memory layout
- 2D arrays model grids, matrices, and tables
- Arrays are the underlying structure for stacks, heaps, and many other structures
- The best use case for arrays is when size is known and access by index is frequent
"""

misconceptions = """
- "Arrays are slow" — Array access is O(1), which is as fast as retrieval gets. The cost is in insertion and deletion in the middle, not in access.
- "Insertion at the end is always O(n)" — Insertion at the end is O(1) if space exists. It becomes O(n) amortized only when a dynamic array must resize and copy all elements.
- "Dynamic arrays like Python lists are not real arrays" — Python lists are dynamic arrays underneath. They allocate contiguous memory and copy when resizing. The dynamic behavior is abstracted, not fundamentally different.
- "Arrays and lists are the same thing" — In Python, a list is a dynamic array. In other contexts, list means a linked list. The word list is ambiguous. Array has a specific memory meaning.
- "2D arrays store data differently from 1D arrays" — In memory, a 2D array is still a flat contiguous block. The 2D indexing is a calculation on top of the same linear memory layout.
- "You should always use arrays because they are simple" — Arrays are a poor choice when frequent insertions or deletions in the middle are needed. Simplicity does not mean universal suitability.
"""

real_world_use = """
- Image processing stores pixel grids as 2D arrays where each cell holds a color value
- Spreadsheet applications organize cells as a 2D array of rows and columns
- Machine learning uses arrays for feature vectors, weight matrices, and datasets — NumPy arrays are the foundation of most ML pipelines
- CPU memory buffers and instruction queues are implemented as low-level arrays
- Leaderboards and scoreboards store ranked entries as sorted arrays
- Database result sets return rows as arrays before further processing
"""

next_concept_link = """
Arrays store data in contiguous memory with fixed size, making access fast but insertion and deletion expensive. The next structure — Linked List — solves exactly these weaknesses by using dynamic, non-contiguous memory and pointer-based connections between elements, at the cost of losing direct index-based access. Understanding arrays first makes the design tradeoffs of linked lists immediately clear.
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
        topic             = excluded.topic,
        base_content      = excluded.base_content,
        examples          = excluded.examples,
        key_points        = excluded.key_points,
        misconceptions    = excluded.misconceptions,
        real_world_use    = excluded.real_world_use,
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