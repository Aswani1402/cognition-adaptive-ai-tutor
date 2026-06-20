import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D3"
topic = "Stack"

base_content = """
A stack is a linear data structure that follows a strict rule for how elements are added and removed. That rule is called LIFO — Last In, First Out. The last element inserted into the stack is the first one to be removed. You can only interact with the top of the stack at any time.

Think of a stack of plates. You place plates on top and remove plates from the top. You cannot remove a plate from the middle without disturbing the ones above it. This is exactly how a stack data structure works.

Core operations:
- push — add an element to the top of the stack
- pop — remove and return the top element
- peek — view the top element without removing it
- is_empty — check if the stack has no elements
- size — return the number of elements in the stack

Stack using a Python list (array-based):
stack = []

# Push
stack.append(10)
stack.append(20)
stack.append(30)
print(stack)        # [10, 20, 30]

# Peek
print(stack[-1])    # 30 — top element

# Pop
print(stack.pop())  # 30
print(stack.pop())  # 20
print(stack)        # [10]

# Check empty
print(len(stack) == 0)  # False

Stack using a linked list (node-based):
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class Stack:
    def __init__(self):
        self.top = None
        self.size = 0

    def push(self, data):
        new_node = Node(data)
        new_node.next = self.top
        self.top = new_node
        self.size += 1

    def pop(self):
        if self.is_empty():
            return "Stack underflow"
        popped = self.top.data
        self.top = self.top.next
        self.size -= 1
        return popped

    def peek(self):
        if self.is_empty():
            return "Stack is empty"
        return self.top.data

    def is_empty(self):
        return self.top is None

s = Stack()
s.push(10)
s.push(20)
s.push(30)
print(s.peek())   # 30
print(s.pop())    # 30
print(s.peek())   # 20

Array vs Linked List implementation:
Array-based stacks are simpler and cache-friendly but have a fixed capacity in static implementations. Linked list-based stacks are dynamic and never overflow unless memory runs out, but carry pointer overhead per node. For most practical purposes, Python's built-in list is sufficient for stack implementation.

Overflow and underflow:
- Stack overflow occurs when you try to push onto a full stack (relevant in fixed-size implementations or deep recursion)
- Stack underflow occurs when you try to pop from an empty stack

stack = []
if not stack:
    print("Stack underflow — nothing to pop")
else:
    stack.pop()

Time complexity of all operations:
Operation    | Time Complexity
Push         | O(1)
Pop          | O(1)
Peek         | O(1)
Search       | O(n)
Is empty     | O(1)

All core stack operations are O(1) — this is what makes stacks efficient and predictable.

Strengths:
- All primary operations are O(1)
- Simple and predictable behavior
- Easy to implement using arrays or linked lists
- Natural fit for problems involving reversal, backtracking, and nesting

Weaknesses:
- No random access — can only interact with the top
- Search costs O(n) — must pop elements to search
- Fixed capacity in array-based static implementations
- Not suitable when you need access to elements other than the top

When to use stacks:
- When you need to reverse a sequence
- When tracking history and need to undo the last action
- When solving problems with nested structure like brackets and tags
- When managing function calls and recursion depth

When not to use stacks:
- When you need access to elements in the middle
- When order of processing should be first in first out
- When random access by index is required

Comparison with Queue:
A stack is LIFO — the last element in is the first out. A queue is FIFO — the first element in is the first out. A stack interacts only with the top. A queue interacts with the front for removal and the rear for insertion. Stacks are used for undo and recursion. Queues are used for scheduling and buffering.

The best data structure is not the most complex one, but the one that matches the required operations.
"""

examples = """
Example 1 — Simple (push and pop):
stack = []
stack.append("a")
stack.append("b")
stack.append("c")

print(stack)        # ['a', 'b', 'c']
print(stack.pop())  # 'c' — last in, first out
print(stack.pop())  # 'b'
print(stack)        # ['a']

Example 2 — Slightly deeper (reversing a string):
def reverse_string(s):
    stack = []
    for char in s:
        stack.append(char)
    result = ""
    while stack:
        result += stack.pop()
    return result

print(reverse_string("hello"))  # "olleh"

Each character is pushed onto the stack. Popping reverses the order automatically because of LIFO behavior.

Example 3 — Operation (balanced brackets checker):
def is_balanced(expression):
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for char in expression:
        if char in '([{':
            stack.append(char)
        elif char in ')]}':
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()
    return len(stack) == 0

print(is_balanced("(a + [b * c])"))  # True
print(is_balanced("(a + [b * c)"))   # False

This is one of the most classic stack use cases — matching opening and closing brackets using LIFO order.

Example 4 — Concrete real-world comparison:
Every time you press Ctrl+Z to undo in a text editor, the editor pops the last action from a stack. Each action you perform is pushed onto the stack. Undoing pops the most recent action first — exactly LIFO behavior.

actions = []
actions.append("typed: H")
actions.append("typed: e")
actions.append("typed: l")
actions.append("typed: l")
actions.append("typed: o")

print("Current:", actions)

# Undo last action
actions.pop()
print("After undo:", actions)
# After undo: ['typed: H', 'typed: e', 'typed: l', 'typed: l']
"""

key_points = """
- Stack follows LIFO — Last In First Out
- Only the top element is accessible at any time
- Push adds to the top — O(1)
- Pop removes from the top — O(1)
- Peek views the top without removing — O(1)
- Search requires popping elements — O(n)
- Stack overflow happens when pushing onto a full fixed-size stack
- Stack underflow happens when popping from an empty stack
- Can be implemented using arrays or linked lists
- Array-based stacks are simpler and cache-friendly
- Linked list-based stacks are dynamic and never overflow from capacity
- Natural fit for reversal, backtracking, nested structure problems
- Function call management in programs uses a call stack internally
- Stacks are the opposite behavior of queues
"""

misconceptions = """
- "Stack and queue are the same thing" — A stack is LIFO and a queue is FIFO. They are opposite in behavior. Using one when you need the other completely changes the result.
- "You can access any element in a stack" — You can only access the top. Reaching a deeper element requires popping everything above it first.
- "Stack overflow only happens in code errors" — Stack overflow is a real data structure concept. In fixed-size stacks, pushing beyond capacity causes overflow. In recursion, calling too deep causes the call stack to overflow.
- "Array-based stacks are always better because they are simpler" — Array-based stacks have fixed capacity in static implementations. Linked list-based stacks are better when size is unpredictable and dynamic growth is needed.
- "Pop and peek do the same thing" — Peek only views the top element without changing the stack. Pop removes the top element and changes the stack. They are different operations.
- "Stacks are only useful for simple problems" — Stacks power expression evaluation, syntax parsing, compiler design, recursion management, and undo systems in real software.
"""

real_world_use = """
- Text editors use a stack to implement undo and redo functionality
- Compilers use stacks to parse and evaluate arithmetic expressions
- Browsers use a stack to manage the back button history within a single tab
- Programming languages use a call stack to manage function calls and return addresses
- Syntax checkers use stacks to validate matching brackets, tags, and parentheses
- Operating systems use stacks to store local variables and return addresses during function execution
"""

next_concept_link = """
A stack restricts insertion and removal to one end using LIFO order. The next concept — Queue — also restricts access to its ends, but follows the opposite rule: FIFO, First In First Out. In a queue, elements enter at the rear and leave from the front, making it the natural structure for scheduling and ordered processing rather than reversal and backtracking.
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