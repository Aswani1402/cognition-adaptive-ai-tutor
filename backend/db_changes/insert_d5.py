import sqlite3

DB_PATH = "external/core_data/data_structures.db"

concept_id = "D5"
topic = "Trees"

base_content = """
A tree is a non-linear hierarchical data structure that consists of nodes connected by edges. Unlike linear structures such as arrays, linked lists, stacks, and queues, a tree organizes data in a parent-child relationship where one node can connect to multiple nodes below it.

Think of a real tree. There is one root at the base, branches spread outward, and leaves sit at the ends. A tree data structure follows the same shape — one root node at the top, branches connecting to child nodes, and leaf nodes at the bottom with no children.

Core terminology:
- root — the topmost node with no parent
- node — each element in the tree
- edge — the connection between a parent and child node
- parent — a node that has one or more children
- child — a node that has a parent
- leaf — a node with no children
- height — the number of edges on the longest path from root to a leaf
- depth — the number of edges from the root to a specific node
- subtree — a node and all its descendants

Tree structure:
        A          <- root
       / \\
      B   C        <- internal nodes
     / \\   \\
    D   E   F      <- leaf nodes

Binary tree:
A binary tree is the most common type of tree. Each node has at most two children — a left child and a right child.

class TreeNode:
    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None

Building a binary tree manually:
root = TreeNode(1)
root.left = TreeNode(2)
root.right = TreeNode(3)
root.left.left = TreeNode(4)
root.left.right = TreeNode(5)

#        1
#       / \\
#      2   3
#     / \\
#    4   5

Binary Search Tree (BST):
A Binary Search Tree is a binary tree with an ordering rule:
- All values in the left subtree are less than the parent node
- All values in the right subtree are greater than the parent node

This rule makes search, insertion, and deletion efficient.

#        10
#       /  \\
#      5    15
#     / \\     \\
#    3   7    20

Inserting into a BST:
def insert(root, data):
    if root is None:
        return TreeNode(data)
    if data < root.data:
        root.left = insert(root.left, data)
    else:
        root.right = insert(root.right, data)
    return root

root = None
for val in [10, 5, 15, 3, 7, 20]:
    root = insert(root, val)

Searching in a BST:
def search(root, target):
    if root is None:
        return False
    if root.data == target:
        return True
    if target < root.data:
        return search(root.left, target)
    return search(root.right, target)

print(search(root, 7))   # True
print(search(root, 99))  # False

Tree traversals:
Traversal means visiting every node in the tree in a specific order. There are four main traversal methods.

Inorder traversal — Left, Root, Right — gives sorted output for BST:
def inorder(root):
    if root:
        inorder(root.left)
        print(root.data, end=" ")
        inorder(root.right)

inorder(root)  # 3 5 7 10 15 20

Preorder traversal — Root, Left, Right — useful for copying a tree:
def preorder(root):
    if root:
        print(root.data, end=" ")
        preorder(root.left)
        preorder(root.right)

preorder(root)  # 10 5 3 7 15 20

Postorder traversal — Left, Right, Root — useful for deleting a tree:
def postorder(root):
    if root:
        postorder(root.left)
        postorder(root.right)
        print(root.data, end=" ")

postorder(root)  # 3 7 5 20 15 10

Level order traversal — level by level using a queue:
from collections import deque

def level_order(root):
    if root is None:
        return
    queue = deque([root])
    while queue:
        node = queue.popleft()
        print(node.data, end=" ")
        if node.left:
            queue.append(node.left)
        if node.right:
            queue.append(node.right)

level_order(root)  # 10 5 15 3 7 20

Common tree types:
- Binary Tree: each node has at most two children
- Binary Search Tree: ordered binary tree for efficient search
- Balanced BST (AVL, Red-Black): self-balancing trees that maintain O(log n) height
- Heap: complete binary tree used for priority queues
- Trie: tree for storing strings character by character
- N-ary Tree: each node can have up to N children

Time complexity for BST operations:
Operation   | Average Case | Worst Case (unbalanced)
Search      | O(log n)     | O(n)
Insertion   | O(log n)     | O(n)
Deletion    | O(log n)     | O(n)
Traversal   | O(n)         | O(n)

Worst case O(n) happens when the BST becomes a straight line — like inserting already sorted values. Balanced trees like AVL trees fix this by keeping height at O(log n) always.

Strengths:
- Hierarchical organization — naturally models parent-child relationships
- BST gives efficient search, insertion, and deletion — O(log n) average
- Traversals give multiple useful orderings of the same data
- Flexible structure — can represent many real-world relationships
- Foundation for advanced structures like heaps, tries, and segment trees

Weaknesses:
- More complex to implement than linear structures
- Unbalanced BST degrades to O(n) for all operations
- No O(1) access like arrays — must traverse from root
- Requires more memory than arrays due to pointer storage per node

When to use trees:
- When data has a natural hierarchical relationship
- When fast search, insertion, and deletion are all needed simultaneously
- When sorted order and range queries are required
- When implementing priority queues, autocomplete, or file systems

When not to use trees:
- When data is flat and sequential with no hierarchy
- When only simple index-based access is needed
- When implementation complexity is a concern for small datasets

Comparison with linear structures:
Arrays and linked lists store data sequentially — access is either O(1) by index or O(n) by traversal. Trees organize data hierarchically — BST gives O(log n) search by splitting the search space in half at each step. For large datasets requiring frequent search, trees outperform linear structures significantly.

The best data structure is not the most complex one, but the one that matches the required operations.
"""

examples = """
Example 1 — Simple (building and traversing a binary tree):
root = TreeNode(1)
root.left = TreeNode(2)
root.right = TreeNode(3)
root.left.left = TreeNode(4)
root.left.right = TreeNode(5)

#        1
#       / \\
#      2   3
#     / \\
#    4   5

inorder(root)   # 4 2 5 1 3
preorder(root)  # 1 2 4 5 3
postorder(root) # 4 5 2 3 1

Example 2 — Slightly deeper (BST insert and search):
root = None
values = [10, 5, 15, 3, 7, 20]
for val in values:
    root = insert(root, val)

#        10
#       /  \\
#      5    15
#     / \\     \\
#    3   7    20

inorder(root)  # 3 5 7 10 15 20 — always sorted for BST

print(search(root, 7))    # True
print(search(root, 12))   # False

Example 3 — Operation (finding height of a tree):
def height(root):
    if root is None:
        return 0
    left_height = height(root.left)
    right_height = height(root.right)
    return 1 + max(left_height, right_height)

print(height(root))  # 3

Example 4 — Concrete real-world comparison:
A file system on your computer is a tree. The root directory is the root node.
Each folder is an internal node. Files with no subfolders are leaf nodes.

file_system = TreeNode("root")
file_system.left = TreeNode("documents")
file_system.right = TreeNode("downloads")
file_system.left.left = TreeNode("resume.pdf")
file_system.left.right = TreeNode("notes.txt")
file_system.right.left = TreeNode("photo.png")

#           root
#          /    \\
#    documents  downloads
#      /    \\      /
# resume  notes  photo
"""

key_points = """
- Tree is a non-linear hierarchical data structure
- Root is the topmost node with no parent
- Each node has at most one parent and zero or more children
- Leaf nodes have no children
- Binary tree — each node has at most two children
- BST ordering rule — left subtree values are smaller, right subtree values are larger
- Inorder traversal of BST always gives sorted output
- Four traversal methods — inorder, preorder, postorder, level order
- BST search, insertion, deletion average O(log n)
- Unbalanced BST degrades to O(n) in worst case
- Balanced trees like AVL maintain O(log n) always
- Height is the longest path from root to a leaf
- Trees use more memory than arrays due to pointer storage per node
- Trees are the foundation for heaps, tries, segment trees, and databases
"""

misconceptions = """
- "A tree is just a linked list with more pointers" — A linked list is linear with one path from head to tail. A tree is hierarchical with branching paths and parent-child rules. They are structurally and behaviorally different.
- "BST search is always O(log n)" — BST search is O(log n) only when the tree is balanced. Inserting sorted values creates a straight line tree where search degrades to O(n).
- "Inorder traversal works the same on all trees" — Inorder gives sorted output only on a BST. On a general binary tree it just gives left-root-right order with no sorting guarantee.
- "Trees can have cycles" — Trees by definition have no cycles. If a cycle exists, the structure is a graph, not a tree. Every node in a tree has exactly one parent except the root.
- "The root is at the bottom" — In computer science diagrams, trees are drawn upside down compared to real trees. The root is always at the top and leaves are at the bottom.
- "All binary trees are BSTs" — A binary tree just limits children to two. A BST adds the ordering rule on top. Every BST is a binary tree but not every binary tree is a BST.
"""

real_world_use = """
- File systems use trees to organize directories and files hierarchically
- Databases use B-trees and B+ trees to index records for fast retrieval
- Browsers use the DOM tree to represent and render HTML structure
- Compilers use abstract syntax trees to parse and evaluate source code
- Autocomplete and spell checkers use tries to store and search words efficiently
- Priority queues and heap sort use binary heap trees for efficient min and max retrieval
"""

next_concept_link = """
Trees organize data hierarchically with parent-child relationships and no cycles. The next concept — Sets — shifts focus entirely to membership and uniqueness. A set stores only unique elements with no duplicates and no guaranteed order, making it the natural structure when the question is not where something is stored but simply whether it exists.
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