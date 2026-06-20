import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D4"
topic = "Queue"

base_content = """
A queue is a linear data structure that follows a strict rule for how elements are added and removed. That rule is called FIFO — First In, First Out. The first element inserted into the queue is the first one to be removed. Elements enter from the rear and leave from the front.

Think of a line of people waiting at a ticket counter. The first person to join the line is the first person to be served. Nobody can jump to the front. This is exactly how a queue data structure works.

Core operations:
- enqueue — add an element to the rear of the queue
- dequeue — remove and return the element from the front
- peek — view the front element without removing it
- is_empty — check if the queue has no elements
- size — return the number of elements in the queue

Queue using Python collections.deque (recommended):
from collections import deque

queue = deque()

# Enqueue
queue.append(10)
queue.append(20)
queue.append(30)
print(queue)               # deque([10, 20, 30])

# Peek
print(queue[0])            # 10 — front element

# Dequeue
print(queue.popleft())     # 10 — first in, first out
print(queue.popleft())     # 20
print(queue)               # deque([30])

# Check empty
print(len(queue) == 0)     # False

Why not use a plain list for queue:
# This works but is inefficient
queue = []
queue.append(10)       # enqueue — O(1)
queue.pop(0)           # dequeue — O(n) because all elements shift left
# deque.popleft() is O(1) — always prefer deque for queues

Queue using a linked list (node-based):
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class Queue:
    def __init__(self):
        self.front = None
        self.rear = None
        self.size = 0

    def enqueue(self, data):
        new_node = Node(data)
        if self.rear is None:
            self.front = self.rear = new_node
        else:
            self.rear.next = new_node
            self.rear = new_node
        self.size += 1

    def dequeue(self):
        if self.is_empty():
            return "Queue underflow"
        removed = self.front.data
        self.front = self.front.next
        if self.front is None:
            self.rear = None
        self.size -= 1
        return removed

    def peek(self):
        if self.is_empty():
            return "Queue is empty"
        return self.front.data

    def is_empty(self):
        return self.front is None

q = Queue()
q.enqueue(10)
q.enqueue(20)
q.enqueue(30)
print(q.peek())      # 10
print(q.dequeue())   # 10
print(q.peek())      # 20

Circular queue:
In a standard array-based queue, dequeuing from the front wastes the empty spaces at the beginning of the array. A circular queue solves this by connecting the end of the array back to the beginning, reusing those empty slots.

class CircularQueue:
    def __init__(self, capacity):
        self.capacity = capacity
        self.queue = [None] * capacity
        self.front = -1
        self.rear = -1

    def enqueue(self, data):
        if (self.rear + 1) % self.capacity == self.front:
            return "Queue is full"
        if self.front == -1:
            self.front = 0
        self.rear = (self.rear + 1) % self.capacity
        self.queue[self.rear] = data

    def dequeue(self):
        if self.front == -1:
            return "Queue is empty"
        removed = self.queue[self.front]
        if self.front == self.rear:
            self.front = self.rear = -1
        else:
            self.front = (self.front + 1) % self.capacity
        return removed

cq = CircularQueue(4)
cq.enqueue(10)
cq.enqueue(20)
cq.enqueue(30)
print(cq.dequeue())   # 10
cq.enqueue(40)        # reuses the freed slot

Time complexity of all operations:
Operation   | Time Complexity
Enqueue     | O(1)
Dequeue     | O(1)
Peek        | O(1)
Search      | O(n)
Is empty    | O(1)

All core queue operations are O(1) — same efficiency as a stack but with opposite ordering behavior.

Strengths:
- All primary operations are O(1)
- Preserves order of arrival — fair and predictable
- Natural fit for scheduling, buffering, and ordered processing
- Easy to implement using deque or linked list

Weaknesses:
- No random access — can only interact with front and rear
- Search costs O(n)
- Plain list-based implementation has O(n) dequeue due to shifting
- Not suitable when you need LIFO behavior or middle access

When to use queues:
- When order of arrival must be preserved
- When managing tasks, requests, or jobs that must be processed in sequence
- When implementing BFS graph traversal
- When buffering data streams between producers and consumers

When not to use queues:
- When you need to process the most recently added element first
- When random access by index is required
- When elements need to be processed by priority rather than arrival order

Comparison with Stack:
A queue is FIFO — the first element in is the first out. A stack is LIFO — the last element in is the first out. A queue interacts with both the front and rear. A stack interacts only with the top. Queues are used for scheduling and ordered processing. Stacks are used for reversal and backtracking.

The best data structure is not the most complex one, but the one that matches the required operations.
"""

examples = """
Example 1 — Simple (enqueue and dequeue):
from collections import deque

queue = deque()
queue.append("first")
queue.append("second")
queue.append("third")

print(queue)                # deque(['first', 'second', 'third'])
print(queue.popleft())      # 'first' — first in, first out
print(queue.popleft())      # 'second'
print(queue)                # deque(['third'])

Example 2 — Slightly deeper (BFS using a queue):
from collections import deque

def bfs(graph, start):
    visited = set()
    queue = deque([start])
    visited.add(start)
    order = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order

graph = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["E"],
    "D": [],
    "E": []
}

print(bfs(graph, "A"))  # ['A', 'B', 'C', 'D', 'E']

BFS explores nodes level by level. A queue ensures nodes are visited in the exact
order they were discovered — FIFO behavior is what makes BFS work correctly.

Example 3 — Operation (printer job queue):
from collections import deque

printer_queue = deque()

printer_queue.append("Document1.pdf")
printer_queue.append("Photo.png")
printer_queue.append("Report.docx")

print("Jobs waiting:", list(printer_queue))

while printer_queue:
    job = printer_queue.popleft()
    print(f"Printing: {job}")

# Output:
# Printing: Document1.pdf
# Printing: Photo.png
# Printing: Report.docx

Example 4 — Concrete real-world comparison:
A customer support system receives requests from users. The first user to submit
a request is the first to be attended to. No user can jump the line.
This is a queue — fair, ordered, and predictable.

from collections import deque

support_queue = deque()

support_queue.append("User A — login issue")
support_queue.append("User B — payment failed")
support_queue.append("User C — account locked")

print("Support queue:", list(support_queue))

next_request = support_queue.popleft()
print(f"Now handling: {next_request}")
# Now handling: User A — login issue
"""

key_points = """
- Queue follows FIFO — First In First Out
- Elements enter at the rear and leave from the front
- Enqueue adds to the rear — O(1)
- Dequeue removes from the front — O(1)
- Peek views the front element without removing — O(1)
- Search requires traversal — O(n)
- Plain list dequeue is O(n) due to shifting — always use deque for queues in Python
- deque.popleft() is O(1) — correct and efficient
- Circular queue reuses freed array slots to avoid wasted space
- Linked list queue uses front and rear pointers for O(1) enqueue and dequeue
- Queue overflow happens when pushing beyond fixed capacity
- Queue underflow happens when dequeuing from an empty queue
- Natural fit for scheduling, buffering, and BFS traversal
- Queues are the opposite behavior of stacks
"""

misconceptions = """
- "Queue and stack are the same thing" — A queue is FIFO and a stack is LIFO. They are opposite in behavior. Using one when you need the other changes the result completely.
- "You can use a plain Python list as a queue efficiently" — list.pop(0) is O(n) because all remaining elements shift left. Always use collections.deque for queue behavior in Python.
- "Circular queue is a completely different data structure" — A circular queue is just an array-based queue that reuses freed space at the front by wrapping the index around. It is an optimization, not a new structure.
- "Dequeue and deque are the same word" — Dequeue is the operation of removing from the front of a queue. Deque (double-ended queue) is a data structure that supports insertion and removal from both ends. They are different things.
- "Queue can only be implemented using arrays" — Queues can be implemented using arrays, linked lists, or deque. Linked list implementation gives natural O(1) enqueue and dequeue without circular index management.
- "BFS can use any data structure for traversal" — BFS specifically requires a queue. Using a stack instead gives DFS behavior. The choice of structure changes which nodes are visited and in what order.
"""

real_world_use = """
- Operating systems use queues to schedule processes and manage CPU job execution order
- Printers use a print queue to process documents in the order they were submitted
- Web servers use request queues to handle incoming HTTP requests in arrival order
- Keyboards use a queue internally to buffer keystrokes in the order they were pressed
- BFS graph traversal uses a queue to explore nodes level by level
- Customer support and ticketing systems use queues to serve users in order of arrival
"""

next_concept_link = """
Queues and stacks are both linear structures that restrict access to specific ends. The next concept — Trees — moves beyond linear structure entirely. A tree organizes data hierarchically, where one node can connect to many children, enabling faster search, sorted storage, and hierarchical representation that linear structures cannot efficiently support.
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