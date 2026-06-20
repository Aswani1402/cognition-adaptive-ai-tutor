import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D2"
topic = "Linked List"

base_content = """
A linked list is a linear data structure where elements called nodes are stored in non-contiguous memory locations and connected through pointers. Unlike arrays, a linked list does not require a contiguous block of memory. Each node holds two things: the data it stores, and a reference (pointer) to the next node in the sequence.

Node structure:
Each node in a linked list contains:
- data — the actual value stored
- next — a pointer to the next node (null in the last node)

Building a basic node in Python:
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

Creating a simple linked list manually:
n1 = Node(10)
n2 = Node(20)
n3 = Node(30)
n1.next = n2
n2.next = n3
# List: 10 -> 20 -> 30 -> None

Head and tail:
The linked list is accessed through a reference called the head, which points to the first node. The last node's next pointer is None, signaling the end of the list. Some implementations also maintain a tail pointer for O(1) insertion at the end.

class LinkedList:
    def __init__(self):
        self.head = None

Types of linked lists:
- Singly linked list: each node points only to the next node. Traversal is one-directional.
- Doubly linked list: each node points to both next and previous. Traversal is bidirectional.
- Circular linked list: the last node points back to the head instead of None.

Doubly linked node:
class DoublyNode:
    def __init__(self, data):
        self.data = data
        self.next = None
        self.prev = None

Memory behavior:
Nodes are allocated individually in heap memory wherever space is available. There is no requirement for adjacency. This makes linked lists highly flexible in size — they grow and shrink dynamically without reallocation or copying. However, each node carries pointer overhead (4 or 8 bytes per pointer depending on the system), which increases total memory usage compared to arrays.

Traversal and search:
To access any element, you must start from the head and follow pointers one by one. There is no index-based formula. Accessing the nth element costs O(n). Searching for a value also costs O(n).

def traverse(head):
    current = head
    while current is not None:
        print(current.data, end=" -> ")
        current = current.next
    print("None")
# Output: 10 -> 20 -> 30 -> None

Searching for a value:
def search(head, target):
    current = head
    index = 0
    while current is not None:
        if current.data == target:
            return f"Found at index {index}"
        current = current.next
        index += 1
    return "Not found"

Insertion:

Insertion at head — O(1):
def insert_at_head(head, data):
    new_node = Node(data)
    new_node.next = head
    return new_node  # new head

head = insert_at_head(head, 5)
# List: 5 -> 10 -> 20 -> 30 -> None

Insertion at end — O(n) without tail pointer:
def insert_at_end(head, data):
    new_node = Node(data)
    if head is None:
        return new_node
    current = head
    while current.next is not None:
        current = current.next
    current.next = new_node
    return head

head = insert_at_end(head, 40)
# List: 10 -> 20 -> 30 -> 40 -> None

Insertion at a specific position:
def insert_at_position(head, data, position):
    new_node = Node(data)
    if position == 0:
        new_node.next = head
        return new_node
    current = head
    for _ in range(position - 1):
        if current is None:
            break
        current = current.next
    new_node.next = current.next
    current.next = new_node
    return head

head = insert_at_position(head, 99, 2)
# List: 10 -> 20 -> 99 -> 30 -> None

Deletion:

Deletion at head — O(1):
def delete_at_head(head):
    if head is None:
        return None
    return head.next  # new head

head = delete_at_head(head)
# List: 20 -> 30 -> None

Deletion by value — O(n):
def delete_by_value(head, target):
    if head is None:
        return None
    if head.data == target:
        return head.next
    current = head
    while current.next is not None:
        if current.next.data == target:
            current.next = current.next.next
            return head
        current = current.next
    return head

head = delete_by_value(head, 20)
# List: 10 -> 30 -> None

Strengths:
- Dynamic size — grows and shrinks without reallocation
- Efficient insertion and deletion — O(1) once position is known
- No memory waste from pre-allocation
- Doubly linked lists support bidirectional traversal

Weaknesses:
- No random access — must traverse from head to reach any element O(n)
- Extra memory per node for pointer storage
- Not cache-friendly — nodes scattered in memory
- More complex to implement than arrays
- Reverse traversal requires doubly linked list

When to use linked lists:
- When the size of data changes frequently
- When frequent insertion and deletion at the beginning or middle is needed
- When you do not need random index-based access
- When implementing stacks or queues with dynamic sizing

When not to use linked lists:
- When fast random access by index is required
- When memory overhead per element is a concern
- When cache performance matters

Comparison with Arrays:
Operation         | Array              | Linked List
Access by index   | O(1)               | O(n)
Search            | O(n)               | O(n)
Insert at head    | O(n)               | O(1)
Insert at middle  | O(n)               | O(1) after traversal
Insert at end     | O(1)               | O(1) with tail pointer
Delete at head    | O(n)               | O(1)
Memory layout     | Contiguous         | Scattered
Cache behavior    | Friendly           | Not friendly

The best data structure is not the most complex one, but the one that matches the required operations.
"""

examples = """
Example 1 — Simple (basic linked list):
n1 = Node(10)
n2 = Node(20)
n3 = Node(30)
n1.next = n2
n2.next = n3

current = n1
while current:
    print(current.data, end=" -> ")
    current = current.next
print("None")
# Output: 10 -> 20 -> 30 -> None

Example 2 — Slightly deeper (doubly linked list):
class DoublyNode:
    def __init__(self, data):
        self.data = data
        self.next = None
        self.prev = None

d1 = DoublyNode(10)
d2 = DoublyNode(20)
d3 = DoublyNode(30)

d1.next = d2
d2.prev = d1
d2.next = d3
d3.prev = d2

# Forward traversal
current = d1
while current:
    print(current.data, end=" -> ")
    current = current.next
print("None")
# Output: 10 -> 20 -> 30 -> None

# Backward traversal
current = d3
while current:
    print(current.data, end=" -> ")
    current = current.prev
print("None")
# Output: 30 -> 20 -> 10 -> None

Example 3 — Operation (insert and delete):
# Start: 10 -> 20 -> 30 -> None
# Insert 99 at position 1
head = insert_at_position(head, 99, 1)
# Result: 10 -> 99 -> 20 -> 30 -> None

# Delete value 20
head = delete_by_value(head, 20)
# Result: 10 -> 99 -> 30 -> None

Example 4 — Concrete real-world comparison:
A browser's back and forward navigation works exactly like a doubly linked list.
Each page visited is a node. Clicking back follows the prev pointer.
Clicking forward follows the next pointer.

class Page:
    def __init__(self, url):
        self.url = url
        self.next = None
        self.prev = None

p1 = Page("google.com")
p2 = Page("youtube.com")
p3 = Page("github.com")

p1.next = p2
p2.prev = p1
p2.next = p3
p3.prev = p2

current = p3
print("Current:", current.url)        # github.com
print("Back:", current.prev.url)      # youtube.com
print("Back:", current.prev.prev.url) # google.com
"""

key_points = """
- Each node holds data and a pointer to the next node
- Head points to the first node — last node's next is None
- No contiguous memory required — nodes live anywhere in heap
- Access and search cost O(n) — no index formula exists
- Insertion and deletion at head cost O(1)
- Insertion and deletion at a known position cost O(1) for pointer update only
- Finding a position before inserting still costs O(n) traversal
- Dynamic size — grows and shrinks without copying or reallocation
- Extra memory per node for pointer storage
- Not cache-friendly — scattered memory layout
- Singly linked: one direction only
- Doubly linked: bidirectional traversal and easier deletion
- Circular: last node points back to head — used in scheduling and buffers
- Linked lists are the base for dynamic stacks, queues, and hash table chaining
"""

misconceptions = """
- "Linked lists are faster than arrays" — Linked lists are faster for insertion and deletion at known positions, but slower for access and search. Neither is universally faster.
- "Linked list insertion is always O(1)" — Finding the position costs O(n). Only the pointer update itself is O(1). Full insertion from scratch is O(n) unless inserting at the head.
- "Doubly linked lists are always better than singly linked lists" — Doubly linked lists use more memory per node and add implementation complexity. Use them only when bidirectional traversal or efficient deletion is needed.
- "Linked lists solve all array problems" — Linked lists solve insertion and deletion overhead but introduce access overhead and memory overhead per node. Each structure has its domain.
- "Circular linked lists are just a bug where someone forgot to set None" — Circular linked lists are intentional. The loop is useful for round-robin scheduling, music playlists, and circular buffer management.
- "You can do index-based access in a linked list just like arrays" — There is no index formula in a linked list. Accessing index 4 still traverses 4 nodes internally — it is O(n), not O(1).
"""

real_world_use = """
- Browser history navigation uses doubly linked lists for back and forward page movement
- Music playlist management uses circular or doubly linked lists for previous and next track navigation
- Operating system process scheduling uses linked lists to manage process queues dynamically
- Hash table collision resolution using chaining stores colliding entries as a linked list at each bucket
- Memory allocators use linked lists to track free memory blocks of varying sizes
- Undo and redo systems in text editors use doubly linked lists to store state history
"""

next_concept_link = """
Linked lists introduce dynamic, pointer-based structure where insertion and deletion are efficient but access requires traversal. The next concept — Stack — is a restricted linear structure built on a single rule: the last element inserted is the first to be removed. Stacks can be implemented using either arrays or linked lists, making this a natural next step that builds directly on both structures studied so far.
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