import sqlite3

DB_PATH = "external/core_data/python_learning.db"
def create_concept_resources_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_resources (
            concept_id TEXT PRIMARY KEY,
            topic TEXT,
            base_content TEXT,
            examples TEXT,
            key_points TEXT,
            misconceptions TEXT,
            real_world_use TEXT,
            next_concept_link TEXT
        );
    """)
# ============================================================
# P1: Variables
# ============================================================

p1_id = "P1"
p1_topic = "Variables"

p1_base_content = """
A variable is a named storage location that holds a value. In Python, you do not declare a variable's type explicitly. Python determines the type automatically based on the value you assign. This is called dynamic typing.

When you write x = 10, Python creates an integer object with value 10 and binds the name x to it. The variable name is just a label pointing to an object in memory.

Variable assignment:
x = 10
name = "Alice"
is_active = True
price = 3.99

Python variables are case-sensitive:
age = 25
Age = 30
AGE = 35
# These are three completely separate variables

Variable naming rules:
- Must start with a letter or underscore
- Can contain letters, digits, and underscores
- Cannot start with a digit
- Cannot use Python reserved keywords (if, for, while, class, etc.)

Valid names: user_name, _count, totalAmount, score2
Invalid names: 2score, my-var, for, class

Python naming conventions (PEP 8):
- Variables and functions: snake_case (user_name, total_score)
- Constants: UPPER_SNAKE_CASE (MAX_SIZE, PI)
- Classes: PascalCase (UserAccount, DataProcessor)

Multiple assignment:
a, b, c = 1, 2, 3
x = y = z = 0

Swapping values:
a, b = b, a
# No temporary variable needed — Pythonic swap

Checking type:
x = 42
print(type(x))   # <class 'int'>

Checking identity vs equality:
x = [1, 2, 3]
y = [1, 2, 3]
print(x == y)    # True  — same value
print(x is y)    # False — different objects in memory

Variables in Python are references to objects, not containers that hold values directly. Understanding this distinction matters when working with mutable objects like lists and dictionaries.
"""

p1_examples = """
Example 1 — Basic assignment and printing:
name = "Alice"
age = 30
height = 5.6
is_student = False

print(name)        # Alice
print(age)         # 30
print(type(age))   # <class 'int'>

Example 2 — Multiple assignment:
x, y, z = 10, 20, 30
print(x, y, z)   # 10 20 30

a = b = c = 0
print(a, b, c)   # 0 0 0

Example 3 — Swapping variables:
a = "hello"
b = "world"
a, b = b, a
print(a)   # world
print(b)   # hello

Example 4 — Variable reassignment changes type:
x = 10
print(type(x))   # <class 'int'>

x = "now I am a string"
print(type(x))   # <class 'str'>
# Python has no issue with this — dynamic typing

Example 5 — Constants by convention:
MAX_RETRIES = 5
PI = 3.14159
DATABASE_URL = "postgresql://localhost/mydb"
# Python has no true constants — UPPER_CASE signals intent to other developers

Example 6 — Reference behavior with mutable objects:
a = [1, 2, 3]
b = a            # b points to the same list, not a copy
b.append(4)
print(a)         # [1, 2, 3, 4] — a is affected too

b = a.copy()     # now b is an independent copy
b.append(5)
print(a)         # [1, 2, 3, 4] — a is not affected
"""

p1_key_points = """
- A variable is a name bound to an object in memory
- Python uses dynamic typing — type is determined by the assigned value, not a declaration
- Variables are case-sensitive: age, Age, and AGE are three different variables
- Names must start with a letter or underscore, not a digit
- Python reserved keywords cannot be used as variable names
- PEP 8 convention: snake_case for variables, UPPER_SNAKE_CASE for constants, PascalCase for classes
- Multiple assignment: a, b, c = 1, 2, 3
- Pythonic swap: a, b = b, a — no temporary variable needed
- type() returns the type of a variable's value
- == checks value equality; is checks object identity (same memory location)
- Variables referencing mutable objects (lists, dicts) share the same object unless explicitly copied
- Python has no true constants — UPPER_CASE naming is a convention to signal immutability intent
"""

p1_misconceptions = """
- "Python variables store values directly" — Python variables are references (labels) pointing to objects in memory. The variable does not contain the value; it points to the object that does.
- "Reassigning a variable changes the object" — Reassignment makes the variable point to a new object. The original object is unchanged and may be garbage collected if nothing else references it.
- "a = b creates an independent copy" — For mutable objects like lists, a = b makes both names point to the same object. Modifying through b also changes what a sees. Use .copy() or copy.deepcopy() for independence.
- "Python variables have fixed types" — Python is dynamically typed. The same variable can reference an integer now and a string a line later with no error.
- "UPPER_CASE variables are actually constant in Python" — Python has no enforcement mechanism for constants. UPPER_CASE is a convention that signals to other developers that the value should not be changed.
- "is and == are interchangeable" — == compares values. is compares object identity (whether two names point to the exact same object in memory). Small integers and interned strings may appear to pass is by coincidence due to Python's caching, but this should never be relied upon.
"""

p1_real_world_use = """
- Configuration values are stored in clearly named variables or constants at the top of scripts for easy modification
- Loop counters, accumulators, and flags are standard variable use in data processing pipelines
- API responses are bound to descriptive variable names to make code readable and maintainable
- Environment-specific settings (database URLs, API keys) are stored as variables loaded from environment files
- Data science code assigns datasets, model objects, and results to descriptive variables for clarity across long notebooks
- Swap idiom (a, b = b, a) is used in sorting algorithms and state management throughout Python programs
"""

p1_next_concept_link = """
Variables store single values of a specific kind. The next concept — Data Types — covers the full set of built-in types Python provides: integers, floats, strings, booleans, lists, tuples, dictionaries, and sets, and how each type behaves, what operations it supports, and when to choose one over another.
"""

# ============================================================
# P2: Data Types
# ============================================================

p2_id = "P2"
p2_topic = "Data Types"

p2_base_content = """
Python has a rich set of built-in data types. Every value in Python belongs to a type, and that type determines what operations you can perform on the value.

Python's core built-in types:

Numeric types:
- int — whole numbers, any size: 42, -7, 1000000
- float — decimal numbers: 3.14, -0.5, 2.0
- complex — complex numbers: 3+4j (rarely needed in general programming)

Text type:
- str — a sequence of Unicode characters: "hello", 'world', ""multiline""

Boolean type:
- bool — True or False (subtype of int: True == 1, False == 0)

Sequence types:
- list — ordered, mutable collection: [1, 2, 3]
- tuple — ordered, immutable collection: (1, 2, 3)
- range — immutable sequence of numbers: range(0, 10)

Mapping type:
- dict — key-value pairs, ordered (Python 3.7+), mutable: {"name": "Alice", "age": 30}

Set types:
- set — unordered, mutable, no duplicates: {1, 2, 3}
- frozenset — unordered, immutable, no duplicates

None type:
- None — represents the absence of a value. Not zero, not False, not an empty string. It is its own type.

Type conversion (casting):
int("42")        # 42
float("3.14")    # 3.14
str(100)         # "100"
list((1, 2, 3))  # [1, 2, 3]
tuple([1, 2, 3]) # (1, 2, 3)
bool(0)          # False
bool(1)          # True
bool("")         # False
bool("hello")    # True

Mutable vs immutable:
- Mutable types can be changed after creation: list, dict, set
- Immutable types cannot be changed after creation: int, float, str, tuple, bool, frozenset

Truthiness (falsy values in Python):
False, None, 0, 0.0, "", [], {}, set(), ()
Everything else evaluates to True in a boolean context.

Checking types:
type(x)           # returns the type
isinstance(x, int) # True if x is an int or a subclass of int
"""

p2_examples = """
Example 1 — Basic types:
x = 42           # int
y = 3.14         # float
name = "Alice"   # str
flag = True      # bool
nothing = None   # NoneType

print(type(x))       # <class 'int'>
print(type(name))    # <class 'str'>
print(type(nothing)) # <class 'NoneType'>

Example 2 — List vs Tuple:
fruits = ["apple", "banana", "cherry"]   # mutable
fruits[0] = "mango"
print(fruits)   # ['mango', 'banana', 'cherry']

coords = (10.5, 20.3)   # immutable
# coords[0] = 5  ← TypeError — tuples cannot be changed

Example 3 — Dictionary:
person = {"name": "Alice", "age": 30, "city": "Berlin"}
print(person["name"])    # Alice
person["age"] = 31
print(person)            # {'name': 'Alice', 'age': 31, 'city': 'Berlin'}

Example 4 — Set (no duplicates):
numbers = {1, 2, 2, 3, 3, 3}
print(numbers)   # {1, 2, 3} — duplicates removed automatically

Example 5 — Type conversion:
age_str = "25"
age_int = int(age_str)
print(age_int + 5)   # 30

pi_str = str(3.14)
print("Pi is " + pi_str)   # Pi is 3.14

Example 6 — Truthiness:
values = [0, "", None, [], False, 42, "hello", [1]]
for v in values:
    print(f"{repr(v):12} -> {bool(v)}")
# 0            -> False
# ''           -> False
# None         -> False
# []           -> False
# False        -> False
# 42           -> True
# 'hello'      -> True
# [1]          -> True

Example 7 — isinstance check:
x = 42
print(isinstance(x, int))    # True
print(isinstance(x, float))  # False
print(isinstance(x, (int, float)))  # True — check against multiple types
"""

p2_key_points = """
- Python has built-in types: int, float, complex, str, bool, list, tuple, range, dict, set, frozenset, None
- Mutable types can be changed after creation: list, dict, set
- Immutable types cannot be changed: int, float, str, tuple, bool, frozenset
- None is its own type (NoneType) and represents the absence of a value
- bool is a subtype of int: True == 1 and False == 0
- Falsy values: False, None, 0, 0.0, "", [], {}, set(), ()
- Type conversion functions: int(), float(), str(), list(), tuple(), bool()
- type() returns the exact type; isinstance() checks type including subclasses
- Dictionaries are ordered by insertion order since Python 3.7
- Sets automatically remove duplicates and do not maintain order
- Tuples are used for data that should not change — coordinates, RGB values, database records
- Strings are immutable — every string operation creates a new string object
"""

p2_misconceptions = """
- "None and False are the same" — None is its own type meaning absence of value. False is a boolean. They both evaluate as falsy, but they are different types and different objects.
- "Lists and tuples are interchangeable" — Lists are mutable and intended for collections of similar items. Tuples are immutable and intended for fixed-structure data. Choosing the right one communicates intent clearly.
- "An empty list is False" — An empty list [] evaluates as falsy in a boolean context, which is useful in conditions. But it is a real object with a type and methods — it is not the same as None or False.
- "type() and isinstance() are always equivalent" — type(x) == int is True only if x is exactly an int. isinstance(x, int) is True if x is an int or any subclass of int. For most checks, isinstance is preferred.
- "Dictionaries are unordered" — This was true before Python 3.7. Since Python 3.7, dictionaries maintain insertion order as part of the language specification.
- "You can mix types freely in arithmetic" — int and float mix freely (3 + 2.0 gives 5.0). But mixing str with int raises a TypeError. Python does not silently convert types the way JavaScript does.
"""

p2_real_world_use = """
- APIs return JSON responses that map directly to Python dicts, lists, strings, ints, floats, and None
- Data validation checks types with isinstance() to ensure inputs are the expected kind before processing
- Sets are used to remove duplicates from large datasets or to compute intersections and differences efficiently
- Tuples represent fixed records — database rows, coordinate pairs, RGB color values
- None is used as a default sentinel value in function parameters to distinguish between "not provided" and "zero" or "empty"
- Configuration files and environment variables are loaded as strings and converted to the correct type (int, float, bool) before use
"""

p2_next_concept_link = """
Now that you know the types Python provides, the next concept — Conditionals — shows how to make decisions in code using if, elif, and else, how Python evaluates conditions using truthiness, and how to combine conditions with and, or, and not.
"""

# ============================================================
# P3: Conditionals
# ============================================================

p3_id = "P3"
p3_topic = "Conditionals"

p3_base_content = """
Conditionals allow your program to make decisions. Based on whether a condition is True or False, Python executes different blocks of code.

Basic structure:
if condition:
    # runs if condition is True
elif another_condition:
    # runs if previous was False and this is True
else:
    # runs if all conditions above were False

Python uses indentation (4 spaces by convention) to define blocks. There are no curly braces. The indentation is the syntax.

Comparison operators:
==   equal to
!=   not equal to
>    greater than
<    less than
>=   greater than or equal to
<=   less than or equal to

Logical operators:
and  — True if both sides are True
or   — True if at least one side is True
not  — inverts the boolean value

Membership operators:
in     — True if value is in a sequence
not in — True if value is not in a sequence

Identity operators:
is     — True if both refer to the same object
is not — True if they refer to different objects

Truthiness in conditionals:
Python evaluates any value as True or False in a condition context.
Falsy: False, None, 0, 0.0, "", [], {}, set()
Everything else is truthy.

if my_list:          # True if list is not empty
if user:             # True if user is not None
if count:            # True if count is not zero

Ternary (one-line) conditional:
result = "even" if x % 2 == 0 else "odd"

Chained comparisons (Pythonic):
if 0 < age < 18:   # True if age is between 0 and 18
    print("minor")

Match statement (Python 3.10+):
match command:
    case "quit":
        print("Quitting")
    case "help":
        print("Showing help")
    case _:
        print("Unknown command")
"""

p3_examples = """
Example 1 — Basic if/elif/else:
score = 75

if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 70:
    print("C")
else:
    print("F")
# Output: C

Example 2 — Logical operators:
age = 20
has_id = True

if age >= 18 and has_id:
    print("Access granted")
else:
    print("Access denied")
# Output: Access granted

Example 3 — Truthiness check:
items = []

if items:
    print("List has items")
else:
    print("List is empty")
# Output: List is empty

user = None
if user:
    print("User logged in")
else:
    print("No user")
# Output: No user

Example 4 — Ternary conditional:
temperature = 35
status = "hot" if temperature > 30 else "cool"
print(status)   # hot

Example 5 — in operator:
allowed_users = ["alice", "bob", "carol"]
username = "bob"

if username in allowed_users:
    print("Welcome")
else:
    print("Access denied")
# Output: Welcome

Example 6 — Chained comparison:
x = 15
if 10 < x < 20:
    print("x is between 10 and 20")
# Output: x is between 10 and 20

Example 7 — Match statement (Python 3.10+):
status_code = 404

match status_code:
    case 200:
        print("OK")
    case 404:
        print("Not Found")
    case 500:
        print("Server Error")
    case _:
        print("Unknown status")
# Output: Not Found
"""

p3_key_points = """
- if / elif / else controls which block of code runs based on boolean conditions
- Python uses indentation (4 spaces) to define code blocks — not curly braces
- Comparison operators: ==, !=, >, <, >=, <=
- Logical operators: and, or, not
- Membership operators: in, not in
- Identity operators: is, is not
- Any value can be used as a condition — falsy values: False, None, 0, "", [], {}, ()
- Ternary: result = value_if_true if condition else value_if_false
- Chained comparisons are Pythonic: 0 < x < 10 instead of x > 0 and x < 10
- match/case was introduced in Python 3.10 for structural pattern matching
- elif can appear multiple times; else is optional and runs only when all conditions fail
- Checking truthiness directly (if my_list:) is more Pythonic than (if len(my_list) > 0:)
"""

p3_misconceptions = """
- "== and is are interchangeable for comparisons" — == compares values. is compares object identity. Use == for value comparison. Use is only for None checks (if x is None).
- "else is required after if" — else is optional. An if block without else simply does nothing when the condition is False.
- "elif and else if are the same" — Python uses elif as a single keyword. Writing else if (two words) creates a nested if inside an else block, not an elif chain.
- "Python conditionals require parentheses around conditions" — Parentheses are optional and generally omitted in Python: if x > 0: not if (x > 0):.
- "Indentation errors only happen to beginners" — Mixing tabs and spaces causes IndentationError even in experienced developers' code. Configure your editor to use spaces consistently.
- "The match statement works in all Python versions" — match/case was introduced in Python 3.10. Code using it will fail on Python 3.9 and earlier.
"""

p3_real_world_use = """
- Input validation uses conditionals to check if user-provided data meets requirements before processing
- Authentication logic uses if/else to grant or deny access based on credentials and permissions
- API response handling uses conditionals to branch on status codes and handle errors appropriately
- Feature flags use conditional checks on configuration values to enable or disable functionality at runtime
- Data cleaning pipelines use conditionals to handle missing values, outliers, and unexpected formats
- Game logic, scoring systems, and state machines are built entirely on conditional branches
"""

p3_next_concept_link = """
Conditionals execute a block once when a condition is met. The next concept — Loops — executes blocks repeatedly: for loops iterate over sequences, while loops continue as long as a condition holds, and both support break, continue, and else clauses for fine-grained control.
"""

# ============================================================
# P4: Loops
# ============================================================

p4_id = "P4"
p4_topic = "Loops"

p4_base_content = """
Loops execute a block of code repeatedly. Python has two types of loops: for and while.

for loop:
Iterates over any iterable — a list, string, range, tuple, dictionary, set, or any object that supports iteration. You do not need an index counter unless you specifically want one.

for item in collection:
    # process item

while loop:
Continues executing as long as the condition is True. Used when the number of iterations is not known in advance.

while condition:
    # do something
    # update condition to eventually exit

Loop control statements:
- break — immediately exits the loop
- continue — skips the rest of the current iteration and moves to the next one
- else — runs after the loop completes normally (not triggered if break was used)

range():
range(stop)         # 0 to stop-1
range(start, stop)  # start to stop-1
range(start, stop, step)  # with step size

Iterating with index — enumerate():
for index, value in enumerate(items):
    print(index, value)

Iterating over dictionary:
for key in my_dict:           # keys only
for value in my_dict.values():  # values only
for key, value in my_dict.items():  # both

List comprehension (compact loop for building lists):
squares = [x**2 for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]

Nested loops:
for i in range(3):
    for j in range(3):
        print(i, j)

Infinite loop with break:
while True:
    user_input = input("Enter command: ")
    if user_input == "quit":
        break

zip() — iterate over two sequences in parallel:
for a, b in zip(list1, list2):
    print(a, b)
"""

p4_examples = """
Example 1 — Basic for loop:
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)
# apple
# banana
# cherry

Example 2 — range() loop:
for i in range(5):
    print(i)
# 0 1 2 3 4

for i in range(2, 10, 2):
    print(i)
# 2 4 6 8

Example 3 — while loop:
count = 0
while count < 5:
    print(count)
    count += 1
# 0 1 2 3 4

Example 4 — break and continue:
for i in range(10):
    if i == 3:
        continue   # skip 3
    if i == 7:
        break      # stop at 7
    print(i)
# 0 1 2 4 5 6

Example 5 — enumerate():
languages = ["Python", "Go", "Rust"]
for index, lang in enumerate(languages):
    print(f"{index}: {lang}")
# 0: Python
# 1: Go
# 2: Rust

Example 6 — Dictionary iteration:
person = {"name": "Alice", "age": 30, "city": "Berlin"}
for key, value in person.items():
    print(f"{key}: {value}")
# name: Alice
# age: 30
# city: Berlin

Example 7 — List comprehension:
squares = [x**2 for x in range(1, 6)]
print(squares)   # [1, 4, 9, 16, 25]

evens = [x for x in range(10) if x % 2 == 0]
print(evens)     # [0, 2, 4, 6, 8]

Example 8 — Loop else:
for i in range(5):
    if i == 10:
        break
else:
    print("Loop completed without break")
# Output: Loop completed without break

Example 9 — zip():
names = ["Alice", "Bob", "Carol"]
scores = [95, 87, 92]
for name, score in zip(names, scores):
    print(f"{name}: {score}")
# Alice: 95
# Bob: 87
# Carol: 92
"""

p4_key_points = """
- for loops iterate over any iterable: list, string, range, dict, tuple, set
- while loops run as long as a condition is True
- break exits the loop immediately
- continue skips the rest of the current iteration
- else on a loop runs only if the loop completed without hitting a break
- range(start, stop, step) generates a sequence of integers
- enumerate(iterable) gives index and value together in each iteration
- dict.items() gives key-value pairs; dict.keys() gives keys; dict.values() gives values
- zip(a, b) iterates over two sequences in parallel, stopping at the shorter one
- List comprehension [expr for item in iterable if condition] is a compact, Pythonic loop
- while True with break is the standard pattern for input loops and event loops
- Nested loops multiply iterations — an outer loop of N and inner of M gives N*M total iterations
"""

p4_misconceptions = """
- "for loops require an index variable" — Python for loops iterate directly over items. You only need an index if you specifically want one, in which case enumerate() provides it cleanly.
- "while loops are always more flexible than for loops" — for loops are appropriate when iterating over a known sequence. while loops are for conditions that change during execution. Using while where for is natural creates unnecessary complexity.
- "break exits all nested loops" — break only exits the innermost loop it is inside. To exit multiple nested loops, you need flags, functions with return, or other strategies.
- "list comprehensions are just shorter for loops" — Comprehensions are also generally faster than equivalent for loops because they are optimized at the bytecode level.
- "The loop else clause runs when the loop condition is False" — The else clause runs when the loop finishes normally without a break. It has nothing to do with the loop condition being False.
- "Modifying a list while iterating over it is safe" — Modifying a list during iteration produces unpredictable results. Iterate over a copy or build a new list instead.
"""

p4_real_world_use = """
- Data processing pipelines iterate over rows in datasets using for loops to transform, filter, or aggregate
- Web scrapers use while loops to paginate through results until no more pages exist
- Input validation uses while True loops to keep prompting until the user provides valid data
- Batch operations (sending emails, processing files, database writes) loop over collections of items
- List comprehensions are used throughout Python codebases to build filtered or transformed lists concisely
- Game loops, server event loops, and background workers use while True loops as their core execution structure
"""

p4_next_concept_link = """
Loops repeat blocks of code over sequences and conditions. The next concept — Functions — shows how to define reusable, named blocks of logic with parameters and return values, how Python handles scope, and how to write clean, focused functions that do one thing well.
"""

# ============================================================
# P5: Functions
# ============================================================

p5_id = "P5"
p5_topic = "Functions"

p5_base_content = """
A function is a named, reusable block of code that performs a specific task. Functions take input (parameters), execute logic, and optionally return output. They are the fundamental unit of code organization in Python.

Defining and calling a function:
def function_name(parameters):
    # body
    return value

A function with no return statement returns None implicitly.

Parameters and arguments:
- Parameter — the variable name in the function definition
- Argument — the actual value passed when calling the function

Types of parameters:
- Positional — matched by position: def add(a, b)
- Keyword — matched by name: add(a=1, b=2)
- Default — has a fallback value: def greet(name="World")
- *args — collects extra positional arguments as a tuple
- **kwargs — collects extra keyword arguments as a dictionary

Return values:
def square(x):
    return x * x

Functions can return multiple values as a tuple:
def min_max(lst):
    return min(lst), max(lst)

lo, hi = min_max([3, 1, 4, 1, 5])

Scope — LEGB rule:
Python resolves names in this order:
L — Local: inside the current function
E — Enclosing: in any enclosing function (for nested functions)
G — Global: at module level
B — Built-in: Python's built-in names (print, len, etc.)

Lambda functions (anonymous, single-expression):
square = lambda x: x * x
sorted_items = sorted(items, key=lambda x: x[1])

First-class functions:
Functions in Python are objects. They can be assigned to variables, passed as arguments, and returned from other functions.

def apply(func, value):
    return func(value)

result = apply(str.upper, "hello")

Docstrings:
def add(a, b):
    ""Return the sum of a and b.""
    return a + b

print(add.__doc__)   # Return the sum of a and b.
"""

p5_examples = """
Example 1 — Basic function:
def greet(name):
    return f"Hello, {name}!"

print(greet("Alice"))   # Hello, Alice!

Example 2 — Default parameter:
def greet(name="World"):
    return f"Hello, {name}!"

print(greet())          # Hello, World!
print(greet("Bob"))     # Hello, Bob!

Example 3 — *args and **kwargs:
def total(*args):
    return sum(args)

print(total(1, 2, 3, 4))   # 10

def describe(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")

describe(name="Alice", age=30, city="Berlin")
# name: Alice
# age: 30
# city: Berlin

Example 4 — Multiple return values:
def stats(numbers):
    return min(numbers), max(numbers), sum(numbers) / len(numbers)

lo, hi, avg = stats([10, 20, 30, 40])
print(lo, hi, avg)   # 10 40 25.0

Example 5 — Lambda with sorted:
students = [("Alice", 88), ("Bob", 95), ("Carol", 72)]
ranked = sorted(students, key=lambda s: s[1], reverse=True)
print(ranked)
# [('Bob', 95), ('Alice', 88), ('Carol', 72)]

Example 6 — Function as argument:
def apply_twice(func, value):
    return func(func(value))

result = apply_twice(lambda x: x * 2, 3)
print(result)   # 12  (3 * 2 = 6, 6 * 2 = 12)

Example 7 — Scope:
x = "global"

def outer():
    x = "enclosing"
    def inner():
        x = "local"
        print(x)   # local
    inner()
    print(x)       # enclosing

outer()
print(x)           # global
"""

p5_key_points = """
- A function is defined with def, has a name, parameters, a body, and an optional return value
- Functions with no return statement implicitly return None
- Positional arguments are matched by order; keyword arguments are matched by name
- Default parameters provide fallback values when arguments are not supplied
- *args collects extra positional arguments as a tuple; **kwargs collects extra keyword arguments as a dict
- Functions can return multiple values as a tuple, which can be unpacked on assignment
- LEGB rule: Python resolves names Local → Enclosing → Global → Built-in
- Lambda creates a small anonymous function with a single expression
- Functions are first-class objects — they can be assigned, passed, and returned
- Docstrings (triple-quoted strings as the first line) document what a function does
- Mutable default arguments (def f(x=[]):) are a common bug — the default is shared across calls
- Keep functions small and focused — a function should do one thing well
"""

p5_misconceptions = """
- "A function must have a return statement" — Functions without return implicitly return None. Many useful functions (printing, modifying in place) return nothing.
- "Default parameter values are re-created on every call" — Default values are evaluated once when the function is defined. Using a mutable default like def f(x=[]) shares the same list across all calls — a notorious Python bug.
- "*args and **kwargs are required syntax" — The * and ** are the syntax. The names args and kwargs are conventions. You could write *numbers or **options and the behavior is identical.
- "Lambda and def functions are fundamentally different" — Lambda creates a function object just like def. The only restriction is that a lambda body must be a single expression — no statements, no assignments.
- "Variables inside a function change global variables" — Assignment inside a function creates a local variable by default. To modify a global, you must explicitly declare it with the global keyword.
- "Functions can only return one value" — Functions return one object. That object can be a tuple containing multiple values, which can be unpacked by the caller. Effectively you get multiple return values.
"""

p5_real_world_use = """
- Every meaningful operation in a Python program is organized into functions for reuse and readability
- API endpoint handlers, data transformers, validators, and formatters are all implemented as functions
- Sorting, filtering, and mapping operations use lambda functions as keys or predicates
- Utility libraries expose functions that users call with their own data — all of Python's standard library is built this way
- Testing frameworks call functions automatically — every test is a function that asserts expected behavior
- Higher-order functions (functions that take or return other functions) are the foundation of decorators, callbacks, and functional programming patterns in Python
"""

p5_next_concept_link = """
Functions organize logic into reusable units. The next concept — Object-Oriented Programming (OOP) — takes this further by grouping related data and functions into classes and objects, enabling you to model real-world entities, manage state cleanly, and build larger programs with clear structure through encapsulation, inheritance, and polymorphism.
"""

# ============================================================
# P6: Object-Oriented Programming (OOP)
# ============================================================

p6_id = "P6"
p6_topic = "Object-Oriented Programming (OOP)"

p6_base_content = """
Object-Oriented Programming is a programming paradigm that organizes code around objects — entities that combine data (attributes) and behavior (methods) into a single unit called a class.

A class is a blueprint. An object (instance) is a specific thing created from that blueprint.

The four pillars of OOP:

1. Encapsulation — bundling data and methods together, hiding internal details
2. Inheritance — a class can inherit attributes and methods from another class
3. Polymorphism — different classes can implement the same method differently
4. Abstraction — exposing only what is necessary, hiding implementation complexity

Defining a class:
class Dog:
    species = "Canis lupus familiaris"   # class attribute (shared by all instances)

    def __init__(self, name, age):       # constructor — runs when object is created
        self.name = name                 # instance attribute (unique to each object)
        self.age = age

    def bark(self):                      # instance method
        return f"{self.name} says woof!"

dog1 = Dog("Rex", 3)
dog2 = Dog("Bella", 5)

Special (dunder) methods:
__init__   — constructor, called on object creation
__str__    — string representation for print()
__repr__   — developer-friendly representation
__len__    — called by len()
__eq__     — called by ==
__lt__     — called by <

Inheritance:
class Animal:
    def __init__(self, name):
        self.name = name
    def speak(self):
        return "..."

class Dog(Animal):
    def speak(self):           # overrides parent method — polymorphism
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

super():
Calls the parent class's method. Used in __init__ to avoid duplicating parent setup.

class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)   # calls Animal.__init__
        self.breed = breed

Access modifiers by convention (Python has no enforcement):
self.name      — public
self._name     — protected (convention: internal use)
self.__name    — private (name mangling applied by Python)

Class methods and static methods:
@classmethod   — receives the class as first argument (cls), not the instance
@staticmethod  — receives neither class nor instance — a plain function in the class namespace
"""

p6_examples = """
Example 1 — Basic class and instance:
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def greet(self):
        return f"Hi, I'm {self.name} and I'm {self.age} years old."

p = Person("Alice", 30)
print(p.greet())   # Hi, I'm Alice and I'm 30 years old.

Example 2 — __str__ and __repr__:
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f"Point({self.x}, {self.y})"

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

p = Point(3, 4)
print(p)        # Point(3, 4)
print(repr(p))  # Point(x=3, y=4)

Example 3 — Inheritance and polymorphism:
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "..."

class Dog(Animal):
    def speak(self):
        return f"{self.name} says Woof!"

class Cat(Animal):
    def speak(self):
        return f"{self.name} says Meow!"

animals = [Dog("Rex"), Cat("Whiskers"), Dog("Buddy")]
for animal in animals:
    print(animal.speak())
# Rex says Woof!
# Whiskers says Meow!
# Buddy says Woof!

Example 4 — super():
class Vehicle:
    def __init__(self, make, model):
        self.make = make
        self.model = model

class Car(Vehicle):
    def __init__(self, make, model, doors):
        super().__init__(make, model)
        self.doors = doors

c = Car("Toyota", "Corolla", 4)
print(c.make, c.model, c.doors)   # Toyota Corolla 4

Example 5 — Class method and static method:
class Circle:
    PI = 3.14159

    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return Circle.PI * self.radius ** 2

    @classmethod
    def from_diameter(cls, diameter):
        return cls(diameter / 2)

    @staticmethod
    def is_valid_radius(r):
        return r > 0

c = Circle.from_diameter(10)
print(c.radius)                     # 5.0
print(Circle.is_valid_radius(5))    # True
print(c.area())                     # 78.53975
"""

p6_key_points = """
- A class is a blueprint; an object (instance) is a specific creation from that blueprint
- __init__ is the constructor — it runs automatically when an object is created
- self refers to the specific instance the method is called on
- Instance attributes (self.x) are unique per object; class attributes are shared by all instances
- The four pillars: encapsulation, inheritance, polymorphism, abstraction
- Inheritance: class Child(Parent) gives Child all of Parent's attributes and methods
- Polymorphism: different classes implement the same method name with different behavior
- super() calls the parent class implementation — essential in __init__ chains
- Dunder methods (__str__, __repr__, __eq__, __len__) define how objects behave with built-in operations
- _name is convention for protected; __name triggers name mangling for private
- @classmethod receives the class; @staticmethod receives neither class nor instance
- Prefer composition over inheritance when the relationship is "has-a" rather than "is-a"
"""

p6_misconceptions = """
- "self is a Python keyword" — self is a convention, not a keyword. You could name it anything. By universal convention, it is always self.
- "Python enforces private attributes with __" — Python does not enforce access restrictions. Double underscore triggers name mangling (_ClassName__attr) which makes accidental access harder, but it is not true privacy.
- "Inheritance is always the right tool for code reuse" — Inheritance models "is-a" relationships. For "has-a" relationships, composition is more appropriate. Overusing inheritance creates fragile, tightly coupled hierarchies.
- "Class attributes and instance attributes are the same" — Class attributes are shared across all instances. Instance attributes are specific to each object. Setting a class attribute on an instance creates a new instance attribute that shadows the class one.
- "__init__ is the constructor" — Technically __new__ creates the object and __init__ initializes it. For practical purposes, __init__ is treated as the constructor in Python.
- "Polymorphism requires inheritance" — Python uses duck typing. If an object has the right method, it works — regardless of its inheritance chain. Formal inheritance is not required for polymorphism in Python.
"""

p6_real_world_use = """
- Web frameworks like Django and Flask use classes extensively for views, models, and middleware
- Django's ORM represents database tables as Python classes, with rows as instances
- Data science libraries like PyTorch and TensorFlow define neural network layers as classes
- GUI frameworks use class hierarchies to represent widgets — buttons, windows, and forms inherit from base components
- Game engines represent game entities (players, enemies, items) as objects with shared and specialized behaviors
- Python's standard library is built on classes — file objects, exceptions, data structures, and threading primitives are all class-based
"""

p6_next_concept_link = """
OOP gives you the structure to model complex systems. The next concept — Decorators and Generators — introduces two powerful Python features: decorators that wrap and extend functions without modifying them, and generators that produce sequences lazily one item at a time, enabling memory-efficient processing of large or infinite data streams.
"""

# ============================================================
# P7: Decorators and Generators
# ============================================================

p7_id = "P7"
p7_topic = "Decorators and Generators"

p7_base_content = """
DECORATORS

A decorator is a function that wraps another function to extend or modify its behavior without changing its source code. Decorators use Python's first-class function support: functions can be passed as arguments and returned from other functions.

Basic decorator structure:
def my_decorator(func):
    def wrapper(*args, **kwargs):
        # before
        result = func(*args, **kwargs)
        # after
        return result
    return wrapper

Applying a decorator with @ syntax:
@my_decorator
def say_hello():
    print("Hello!")

This is exactly equivalent to:
say_hello = my_decorator(say_hello)

Common built-in decorators:
@staticmethod  — marks a method as static (no self or cls)
@classmethod   — marks a method as a class method (receives cls)
@property      — makes a method accessible as an attribute

functools.wraps:
Always use @functools.wraps(func) inside your decorator's wrapper function. Without it, the wrapped function loses its __name__ and __doc__, making debugging and introspection harder.

Decorators with arguments:
To pass arguments to a decorator, add another level of nesting — a function that returns the decorator.

---

GENERATORS

A generator is a function that produces a sequence of values lazily, one at a time, using the yield keyword instead of return. Each time yield is reached, the function pauses, returns the value, and resumes from the same point on the next call.

Why generators:
- Memory efficient — values are produced one at a time, not all at once
- Can represent infinite sequences
- Ideal for processing large files, streams, and pipelines

def countdown(n):
    while n > 0:
        yield n
        n -= 1

for num in countdown(5):
    print(num)   # 5, 4, 3, 2, 1

Generator expressions (like list comprehensions but lazy):
squares_gen = (x**2 for x in range(1000000))
# Nothing is computed yet — only produced when consumed

next():
Call next() on a generator to get the next value manually.

gen = countdown(3)
print(next(gen))   # 3
print(next(gen))   # 2
print(next(gen))   # 1
# next(gen) now raises StopIteration

send() and two-way generators:
Generators can also receive values via send(), enabling coroutine-like behavior, though async/await is preferred for coroutines in modern Python.
"""

p7_examples = """
Example 1 — Basic decorator:
def logger(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Done {func.__name__}")
        return result
    return wrapper

@logger
def add(a, b):
    return a + b

print(add(3, 4))
# Calling add
# Done add
# 7

Example 2 — Decorator with functools.wraps:
import functools

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper

@timer
def slow_function():
    import time
    time.sleep(0.1)

slow_function()   # slow_function took 0.1001s

Example 3 — Decorator with arguments:
def repeat(n):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(n):
                func(*args, **kwargs)
        return wrapper
    return decorator

@repeat(3)
def greet():
    print("Hello!")

greet()
# Hello!
# Hello!
# Hello!

Example 4 — @property decorator:
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def fahrenheit(self):
        return self._celsius * 9/5 + 32

t = Temperature(100)
print(t.fahrenheit)   # 212.0   — accessed as attribute, not method call

Example 5 — Basic generator:
def count_up(limit):
    n = 0
    while n < limit:
        yield n
        n += 1

for num in count_up(5):
    print(num)   # 0 1 2 3 4

Example 6 — Infinite generator:
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

gen = fibonacci()
for _ in range(8):
    print(next(gen), end=" ")
# 0 1 1 2 3 5 8 13

Example 7 — Generator expression vs list:
# List — all values computed and stored in memory at once
squares_list = [x**2 for x in range(1000000)]

# Generator — values computed one at a time, minimal memory
squares_gen = (x**2 for x in range(1000000))

print(sum(squares_gen))   # Computed lazily, memory efficient
"""

p7_key_points = """
- A decorator is a function that wraps another function to add behavior before or after it
- The @ syntax is shorthand for function = decorator(function)
- Always use @functools.wraps(func) in your wrapper to preserve the original function's metadata
- Decorators with arguments require three levels of nesting: argument function → decorator → wrapper
- @property, @classmethod, and @staticmethod are built-in decorators
- A generator uses yield instead of return to produce values one at a time
- Generator functions pause at each yield and resume from the same point on the next call
- Generators are memory-efficient — values are produced lazily, not all stored at once
- Generator expressions use () instead of [] and are evaluated lazily
- next() retrieves the next value from a generator; StopIteration is raised when exhausted
- Generators can represent infinite sequences — impossible with lists
- Decorators and generators are both built on Python's first-class function and iterator protocol
"""

p7_misconceptions = """
- "Decorators modify the original function" — Decorators create a new wrapper function. The original function's code is unchanged. The decorator replaces the name binding, not the function body.
- "yield and return are interchangeable" — return exits the function permanently and returns a value once. yield pauses execution, returns a value, and allows the function to resume — fundamentally different mechanisms.
- "Generator expressions and list comprehensions are equally efficient" — List comprehensions compute and store all values in memory immediately. Generator expressions are lazy — nothing is computed until consumed. For large data, generators are far more memory efficient.
- "Generators can only be used once" — A generator object is exhausted after one full iteration. If you need to iterate again, you must create a new generator from the function.
- "functools.wraps is optional in decorators" — Without it, the wrapped function loses its __name__, __doc__, and __module__, breaking introspection, debugging tools, and documentation systems.
- "Decorators only work on functions" — Decorators can be applied to classes as well. Class decorators receive the class object and return a modified version, enabling patterns like registration, validation, and auto-generation of methods.
"""

p7_real_world_use = """
- Web frameworks use decorators to define routes: @app.route("/home") in Flask marks a function as an HTTP handler
- Authentication and authorization use decorators: @login_required wraps views to check credentials before allowing access
- Caching decorators like @functools.lru_cache memoize expensive function results to avoid recomputation
- Retry decorators automatically re-run functions that raise exceptions due to transient network or service failures
- Generators process large log files, CSV files, and database result sets line by line without loading everything into memory
- Data pipelines chain generators to transform, filter, and aggregate streaming data efficiently at each stage
"""

p7_next_concept_link = """
Decorators and generators complete Python's advanced function patterns. The next concept — File Handling and I/O — covers reading and writing files, working with text and binary data, using context managers (with statement), handling file paths, and processing structured formats like CSV and JSON, which are essential for any real-world data processing task.
"""

# ============================================================
# P8: File Handling and I/O
# ============================================================

p8_id = "P8"
p8_topic = "File Handling and I/O"

p8_base_content = """
File handling allows Python programs to read data from files, write results to files, and interact with the filesystem. Almost every real-world program reads configuration, processes data files, or writes output.

Opening a file — open():
open(filepath, mode, encoding)

Common modes:
"r"  — read (default) — file must exist
"w"  — write — creates file or overwrites existing
"a"  — append — adds to end, creates if not exists
"x"  — exclusive create — fails if file exists
"rb" — read binary
"wb" — write binary

The with statement (context manager):
Always use with when working with files. It automatically closes the file when the block exits, even if an exception occurs.

with open("file.txt", "r") as f:
    content = f.read()
# File is automatically closed here

Reading methods:
f.read()           — reads entire file as a single string
f.read(n)          — reads n characters
f.readline()       — reads one line including the newline
f.readlines()      — reads all lines into a list
for line in f:     — iterates line by line (memory efficient for large files)

Writing methods:
f.write(string)    — writes a string, returns number of characters written
f.writelines(list) — writes a list of strings (no newlines added automatically)

File paths — pathlib (modern, preferred):
from pathlib import Path

p = Path("data/output.txt")
p.parent      # data/
p.name        # output.txt
p.stem        # output
p.suffix      # .txt
p.exists()    # True or False
p.read_text() # reads entire file
p.write_text("content")

Working with CSV:
import csv

with open("data.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["name"], row["score"])

Working with JSON:
import json

with open("config.json", "r") as f:
    data = json.load(f)     # parse JSON into Python dict

with open("output.json", "w") as f:
    json.dump(data, f, indent=2)   # write Python dict as JSON

Exception handling with files:
try:
    with open("file.txt") as f:
        content = f.read()
except FileNotFoundError:
    print("File does not exist")
except PermissionError:
    print("No permission to read file")
"""

p8_examples = """
Example 1 — Reading a file:
with open("notes.txt", "r", encoding="utf-8") as f:
    content = f.read()
print(content)

Example 2 — Writing to a file:
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("Line one\n")
    f.write("Line two\n")

Example 3 — Appending to a file:
with open("log.txt", "a") as f:
    f.write("New log entry\n")

Example 4 — Reading line by line (memory efficient):
with open("large_file.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line:
            print(line)

Example 5 — Reading all lines into a list:
with open("names.txt") as f:
    names = [line.strip() for line in f]
print(names)

Example 6 — pathlib:
from pathlib import Path

path = Path("data") / "results.txt"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("Score: 99\n")
print(path.read_text())   # Score: 99

Example 7 — CSV reading with DictReader:
import csv

with open("students.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"{row['name']}: {row['grade']}")

Example 8 — CSV writing:
import csv

students = [
    {"name": "Alice", "grade": "A"},
    {"name": "Bob", "grade": "B"},
]

with open("output.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "grade"])
    writer.writeheader()
    writer.writerows(students)

Example 9 — JSON load and dump:
import json

with open("config.json", "r") as f:
    config = json.load(f)

config["version"] = "2.0"

with open("config.json", "w") as f:
    json.dump(config, f, indent=2)

Example 10 — Exception handling:
from pathlib import Path

filepath = Path("data.txt")

try:
    content = filepath.read_text()
except FileNotFoundError:
    print(f"{filepath} does not exist")
except PermissionError:
    print(f"Cannot read {filepath} — permission denied")
"""

p8_key_points = """
- open(filepath, mode) opens a file; always use with to ensure it is closed automatically
- Common modes: r (read), w (write/overwrite), a (append), x (exclusive create), rb/wb (binary)
- f.read() reads the whole file; iterating with for line in f is memory-efficient for large files
- f.write() writes a string; f.writelines() writes a list of strings
- pathlib.Path is the modern way to handle file paths — cross-platform and expressive
- Path operators: / for joining, .exists(), .read_text(), .write_text(), .mkdir()
- csv.DictReader reads CSV rows as dictionaries; csv.DictWriter writes dictionaries as CSV rows
- json.load() parses a JSON file into Python objects; json.dump() writes Python objects as JSON
- Always specify encoding="utf-8" when reading or writing text files to avoid platform-specific issues
- Always handle FileNotFoundError and PermissionError when working with files in production code
- newline="" should be passed to open() when using the csv module on Windows to avoid extra blank lines
- The with statement uses the context manager protocol — __enter__ and __exit__ — ensuring cleanup happens reliably
"""

p8_misconceptions = """
- "open() automatically closes the file" — open() alone does not close the file. Without with, you must call f.close() explicitly. If an exception occurs before close(), the file stays open. Always use with.
- "w mode adds to the end of an existing file" — w mode truncates (empties) the file before writing. To add to an existing file without erasing it, use a (append) mode.
- "f.readlines() is the most efficient way to read a file" — readlines() loads the entire file into a list in memory. For large files, iterating with for line in f reads one line at a time and is far more memory efficient.
- "pathlib and os.path are equivalent — use either" — pathlib is the modern, object-oriented path handling library. os.path is the older string-based approach. pathlib is preferred in new code for readability and cross-platform safety.
- "json.load() and json.loads() do the same thing" — json.load() reads from a file object. json.loads() parses a JSON string already in memory. The s in loads stands for string.
- "Binary mode is only needed for images and videos" — Any file where exact byte preservation matters requires binary mode: executables, compressed files, encrypted data, and some database files all need rb/wb.
"""

p8_real_world_use = """
- Configuration files (JSON, YAML, TOML) are loaded at application startup using file reading and JSON/YAML parsers
- Data science workflows read CSV and Excel files containing datasets for processing and analysis
- Log files are written using append mode so application events accumulate over time without overwriting history
- ETL pipelines read data from flat files, transform it, and write results to output files or databases
- Web scrapers save downloaded HTML and JSON responses to files for offline processing and caching
- Build tools and deployment scripts use pathlib to manage file paths, create directories, and copy artifacts cross-platform
"""

p8_next_concept_link = """
File handling completes the Python knowledge graph. You now have a full picture from variables and data types through conditionals, loops, functions, OOP, advanced patterns with decorators and generators, and practical I/O with files. The next subject in your curriculum is HTML — starting with What is HTML, which covers the structure and purpose of markup language as the foundation of every web page.
"""

# ============================================================
# DATABASE INSERT — ALL CONCEPTS
# ============================================================

def insert_concept(cursor, concept_id, topic, base_content, examples,
                   key_points, misconceptions, real_world_use, next_concept_link):
    cursor.execute("""
        INSERT INTO concept_resources (
            concept_id, topic, base_content, examples,
            key_points, misconceptions, real_world_use, next_concept_link
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
        base_content.strip(), examples.strip(),
        key_points.strip(), misconceptions.strip(),
        real_world_use.strip(), next_concept_link.strip()
    ))
    print(f"Success — concept '{concept_id}: {topic}' inserted or updated.")


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ✅ Always ensure table exists
create_concept_resources_table(cursor)

# Insert all concepts
insert_concept(cursor, p1_id, p1_topic, p1_base_content, p1_examples,
               p1_key_points, p1_misconceptions, p1_real_world_use, p1_next_concept_link)

insert_concept(cursor, p2_id, p2_topic, p2_base_content, p2_examples,
               p2_key_points, p2_misconceptions, p2_real_world_use, p2_next_concept_link)

insert_concept(cursor, p3_id, p3_topic, p3_base_content, p3_examples,
               p3_key_points, p3_misconceptions, p3_real_world_use, p3_next_concept_link)

insert_concept(cursor, p4_id, p4_topic, p4_base_content, p4_examples,
               p4_key_points, p4_misconceptions, p4_real_world_use, p4_next_concept_link)

insert_concept(cursor, p5_id, p5_topic, p5_base_content, p5_examples,
               p5_key_points, p5_misconceptions, p5_real_world_use, p5_next_concept_link)

insert_concept(cursor, p6_id, p6_topic, p6_base_content, p6_examples,
               p6_key_points, p6_misconceptions, p6_real_world_use, p6_next_concept_link)

insert_concept(cursor, p7_id, p7_topic, p7_base_content, p7_examples,
               p7_key_points, p7_misconceptions, p7_real_world_use, p7_next_concept_link)

insert_concept(cursor, p8_id, p8_topic, p8_base_content, p8_examples,
               p8_key_points, p8_misconceptions, p8_real_world_use, p8_next_concept_link)

conn.commit()
conn.close()

print("\nAll Python concepts P1–P8 inserted successfully into python_learning.db")