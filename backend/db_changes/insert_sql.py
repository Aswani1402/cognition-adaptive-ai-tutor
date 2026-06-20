import sqlite3

DB_PATH = "external/core_data/database_sql.db"

def get_concepts():
    return [

# ============================================================
# S1 — Database Basics
# ============================================================
{
"concept_id": "S1",
"topic": "Database Basics",
"base_content": """
A database is an organized collection of structured data stored electronically in a computer system. A database is managed by a Database Management System (DBMS) — software that controls how data is stored, retrieved, updated, and secured.

Without a database, data would be stored in flat files or spreadsheets. These work for small data but break down at scale — they are slow to search, hard to keep consistent, and difficult to share across multiple users or applications.

Why databases exist:
- To store large amounts of data reliably and efficiently
- To allow multiple users to access and modify data simultaneously
- To enforce data integrity and consistency rules
- To provide fast querying and retrieval through structured access
- To protect data through access control and security

Types of databases:
Relational databases store data in tables made of rows and columns. Tables relate to each other through keys. SQL (Structured Query Language) is used to interact with them. Examples: PostgreSQL, MySQL, SQLite, Microsoft SQL Server.

Non-relational databases (NoSQL) store data in formats like documents, key-value pairs, graphs, or wide columns. Examples: MongoDB (documents), Redis (key-value), Cassandra (wide column).

For this module, the focus is on relational databases and SQL.

Tables, rows, and columns:
A table is the fundamental unit of a relational database. It is similar to a spreadsheet.
- A column (also called a field or attribute) defines a type of data — like name, age, or email
- A row (also called a record or tuple) is one entry in the table — like one person's data
- Every table should have a primary key — a column or set of columns that uniquely identifies each row

Example table structure:
Table: students
student_id | name       | age | grade
1          | Alice      | 20  | A
2          | Bob        | 22  | B
3          | Charlie    | 21  | A

Primary key: student_id — uniquely identifies each student

Keys and relationships:
Primary key — uniquely identifies each row in a table. Cannot be null or duplicate.
Foreign key — a column in one table that references the primary key of another table. This creates a relationship between tables.

Example:
Table: enrollments
enrollment_id | student_id | course_id
1             | 1          | 101
2             | 2          | 102
3             | 1          | 103

student_id in enrollments is a foreign key referencing student_id in students.

Data types:
Each column in a table has a data type that defines what kind of data it can hold.
- INTEGER or INT — whole numbers
- VARCHAR(n) or TEXT — variable-length strings
- FLOAT or DECIMAL — decimal numbers
- DATE or DATETIME — date and time values
- BOOLEAN — true or false values

Constraints:
Constraints are rules enforced on columns to maintain data integrity.
- NOT NULL — the column cannot be empty
- UNIQUE — all values in the column must be different
- PRIMARY KEY — combination of NOT NULL and UNIQUE
- FOREIGN KEY — enforces referential integrity between tables
- DEFAULT — sets a default value if none is provided
- CHECK — ensures values meet a specific condition

Creating a table in SQL:
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    grade TEXT DEFAULT 'N/A'
);

Inserting data:
INSERT INTO students (student_id, name, age, grade)
VALUES (1, 'Alice', 20, 'A');

INSERT INTO students (student_id, name, age, grade)
VALUES (2, 'Bob', 22, 'B');

Viewing data:
SELECT * FROM students;

-- Output:
-- student_id | name  | age | grade
-- 1          | Alice | 20  | A
-- 2          | Bob   | 22  | B

ACID properties:
A reliable database follows ACID properties for transactions.
- Atomicity — a transaction is all or nothing. If one step fails, the whole transaction rolls back.
- Consistency — the database always moves from one valid state to another.
- Isolation — concurrent transactions do not interfere with each other.
- Durability — once a transaction is committed, it stays committed even after a crash.

Strengths of relational databases:
- Structured and consistent data storage
- Powerful querying with SQL
- Strong data integrity through constraints and transactions
- Mature technology with strong tooling and community support
- Good for complex relationships between data entities

Weaknesses of relational databases:
- Schema must be defined upfront — changes can be costly
- Horizontal scaling is harder than NoSQL databases
- Not ideal for unstructured or highly variable data
- Performance can degrade with very large tables if not properly indexed

When to use a relational database:
- When data has clear structure and relationships
- When data integrity and consistency are critical
- When complex queries across multiple tables are needed
- When working with financial, medical, or enterprise data

When not to use a relational database:
- When data is unstructured or highly variable in shape
- When extreme horizontal scale is needed across many servers
- When the application needs flexible schema that changes frequently
""",

"examples": """
Example 1 — Simple (creating and inserting into a table):
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price DECIMAL(10, 2),
    stock INTEGER DEFAULT 0
);

INSERT INTO products VALUES (1, 'Laptop', 999.99, 50);
INSERT INTO products VALUES (2, 'Mouse', 25.50, 200);
INSERT INTO products VALUES (3, 'Keyboard', 45.00, 150);

SELECT * FROM products;
-- product_id | name     | price  | stock
-- 1          | Laptop   | 999.99 | 50
-- 2          | Mouse    | 25.50  | 200
-- 3          | Keyboard | 45.00  | 150

Example 2 — Slightly deeper (primary key and foreign key relationship):
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product TEXT,
    amount DECIMAL(10, 2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

INSERT INTO customers VALUES (1, 'Alice', 'alice@email.com');
INSERT INTO customers VALUES (2, 'Bob', 'bob@email.com');

INSERT INTO orders VALUES (1, 1, 'Laptop', 999.99);
INSERT INTO orders VALUES (2, 1, 'Mouse', 25.50);
INSERT INTO orders VALUES (3, 2, 'Keyboard', 45.00);

-- Alice has 2 orders, Bob has 1 order
-- customer_id links orders back to customers

Example 3 — Operation (constraints in action):
INSERT INTO customers VALUES (3, NULL, 'test@email.com');
-- ERROR: NOT NULL constraint failed: customers.name

INSERT INTO customers VALUES (4, 'Dave', 'alice@email.com');
-- ERROR: UNIQUE constraint failed: customers.email

-- Constraints protect data integrity automatically

Example 4 — Concrete real-world comparison:
An e-commerce platform stores customers, products, and orders in separate tables.
Each table has one responsibility. Foreign keys link them together.
This avoids storing the same customer name and address in every single order row —
which would waste space and cause inconsistency if the name changes.

-- Without a database (flat file approach — bad):
-- order_id | customer_name | customer_email | product | price
-- 1        | Alice         | alice@x.com    | Laptop  | 999.99
-- 2        | Alice         | alice@x.com    | Mouse   | 25.50
-- Alice's email appears twice — update one, miss the other = inconsistency

-- With a relational database:
-- customers table has Alice once
-- orders table references her by customer_id
-- Update email once in customers — all orders stay consistent
""",

"key_points": """
- A database is an organized collection of structured data managed by a DBMS
- Relational databases store data in tables made of rows and columns
- A table row is one record — a column is one attribute or field
- Primary key uniquely identifies each row — cannot be null or duplicate
- Foreign key links one table to another — creates relationships between tables
- Data types define what kind of data each column can hold
- Constraints enforce data integrity rules — NOT NULL, UNIQUE, PRIMARY KEY, FOREIGN KEY
- SQL is the language used to interact with relational databases
- ACID properties ensure reliable transactions — Atomicity, Consistency, Isolation, Durability
- Relational databases are ideal for structured data with clear relationships
- NoSQL databases handle unstructured or highly variable data
- Schemas must be defined upfront in relational databases
- Indexes speed up data retrieval — covered in S5
""",

"misconceptions": """
- "A database is just a spreadsheet" — A spreadsheet has no enforcement of relationships, constraints, or concurrent access. A database enforces structure, integrity, and handles thousands of simultaneous users.
- "SQL is only for reading data" — SQL handles creating tables, inserting, updating, deleting, and complex querying. It is a complete data manipulation language.
- "Primary keys must be integers" — Primary keys can be any data type as long as values are unique and not null. UUIDs and strings are also used as primary keys.
- "Foreign keys automatically delete related rows" — Foreign keys enforce referential integrity but do not automatically delete related rows unless CASCADE is explicitly configured.
- "NoSQL databases are always faster than relational databases" — NoSQL databases trade consistency and structure for flexibility and scale. For structured data with complex queries, relational databases are often faster.
- "One big table is simpler than multiple related tables" — One big table leads to data duplication, update anomalies, and inconsistency. Proper table design with relationships is more efficient and reliable.
""",

"real_world_use": """
- E-commerce platforms store customers, products, orders, and payments in related tables
- Banking systems use relational databases to manage accounts, transactions, and balances with ACID guarantees
- Hospital management systems store patients, doctors, appointments, and medical records in structured tables
- School and university systems manage students, courses, enrollments, and grades using relational databases
- Social media platforms use databases to store user profiles, posts, relationships, and activity logs
- Government systems use relational databases for tax records, voter registration, and identification data
""",

"next_concept_link": """
Database basics establish the foundation — tables, rows, columns, keys, and constraints. The next concept — SQL SELECT Queries — is where data retrieval begins. SELECT is the most used SQL command and is the entry point to reading, filtering, sorting, and aggregating data from tables.
"""
},

# ============================================================
# S2 — SQL SELECT Queries
# ============================================================
{
"concept_id": "S2",
"topic": "SQL SELECT Queries",
"base_content": """
The SELECT statement is the most fundamental SQL command. It is used to retrieve data from one or more tables in a database. Every data retrieval operation in SQL starts with SELECT.

Basic SELECT syntax:
SELECT column1, column2 FROM table_name;

To select all columns:
SELECT * FROM table_name;

Setup — sample table used throughout:
CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    salary DECIMAL(10,2),
    hire_date DATE,
    city TEXT
);

INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 85000, '2020-03-15', 'Mumbai');
INSERT INTO employees VALUES (2, 'Bob', 'Marketing', 60000, '2019-07-22', 'Delhi');
INSERT INTO employees VALUES (3, 'Charlie', 'Engineering', 92000, '2018-01-10', 'Mumbai');
INSERT INTO employees VALUES (4, 'Diana', 'HR', 55000, '2021-11-05', 'Bangalore');
INSERT INTO employees VALUES (5, 'Eve', 'Marketing', 67000, '2020-08-30', 'Delhi');

Selecting specific columns:
SELECT name, department, salary FROM employees;
-- name    | department  | salary
-- Alice   | Engineering | 85000
-- Bob     | Marketing   | 60000
-- Charlie | Engineering | 92000
-- Diana   | HR          | 55000
-- Eve     | Marketing   | 67000

Selecting all columns:
SELECT * FROM employees;

Column aliases using AS:
SELECT name AS employee_name, salary AS monthly_salary
FROM employees;
-- employee_name | monthly_salary
-- Alice         | 85000
-- Bob           | 60000

Arithmetic in SELECT:
SELECT name, salary, salary * 1.10 AS salary_with_raise
FROM employees;
-- name    | salary | salary_with_raise
-- Alice   | 85000  | 93500.0
-- Bob     | 60000  | 66000.0
-- Charlie | 92000  | 101200.0

ORDER BY — sorting results:
SELECT name, salary FROM employees
ORDER BY salary DESC;
-- name    | salary
-- Charlie | 92000
-- Alice   | 85000
-- Eve     | 67000
-- Bob     | 60000
-- Diana   | 55000

ORDER BY multiple columns:
SELECT name, department, salary FROM employees
ORDER BY department ASC, salary DESC;

DISTINCT — removing duplicate values:
SELECT DISTINCT department FROM employees;
-- department
-- Engineering
-- Marketing
-- HR

LIMIT — restricting number of rows returned:
SELECT name, salary FROM employees
ORDER BY salary DESC
LIMIT 3;
-- name    | salary
-- Charlie | 92000
-- Alice   | 85000
-- Eve     | 67000

Aggregate functions:
Aggregate functions perform calculations on a set of rows and return a single value.

COUNT — number of rows:
SELECT COUNT(*) AS total_employees FROM employees;
-- total_employees
-- 5

SUM — total of a numeric column:
SELECT SUM(salary) AS total_salary FROM employees;
-- total_salary
-- 359000

AVG — average value:
SELECT AVG(salary) AS average_salary FROM employees;
-- average_salary
-- 71800

MAX and MIN:
SELECT MAX(salary) AS highest, MIN(salary) AS lowest FROM employees;
-- highest | lowest
-- 92000   | 55000

GROUP BY — grouping rows by a column:
GROUP BY groups rows that have the same value in a specified column. Aggregate functions are then applied per group.

SELECT department, COUNT(*) AS headcount, AVG(salary) AS avg_salary
FROM employees
GROUP BY department;
-- department  | headcount | avg_salary
-- Engineering | 2         | 88500
-- Marketing   | 2         | 63500
-- HR          | 1         | 55000

HAVING — filtering after GROUP BY:
HAVING filters groups after GROUP BY. WHERE filters rows before grouping. They are different.

SELECT department, AVG(salary) AS avg_salary
FROM employees
GROUP BY department
HAVING AVG(salary) > 60000;
-- department  | avg_salary
-- Engineering | 88500
-- Marketing   | 63500

Full query clause order:
SELECT columns
FROM table
WHERE conditions
GROUP BY columns
HAVING group_conditions
ORDER BY columns
LIMIT n;

This is the exact order SQL clauses must appear in a query.

Strengths of SELECT:
- Extremely flexible — can retrieve any subset of data
- Aggregate functions provide powerful summary statistics
- GROUP BY enables per-category analysis
- ORDER BY and LIMIT make result sets manageable
- Aliases make output readable and usable in applications

Weaknesses to be aware of:
- SELECT * retrieves all columns — expensive on wide tables
- Without WHERE, SELECT scans the entire table — slow on large datasets
- GROUP BY without indexes can be slow on large tables
- HAVING is evaluated after grouping — cannot use it to filter individual rows
""",

"examples": """
Example 1 — Simple (basic SELECT with ORDER BY):
SELECT name, salary
FROM employees
ORDER BY salary DESC;
-- name    | salary
-- Charlie | 92000
-- Alice   | 85000
-- Eve     | 67000
-- Bob     | 60000
-- Diana   | 55000

Example 2 — Slightly deeper (GROUP BY with aggregates):
SELECT department,
       COUNT(*) AS total,
       AVG(salary) AS avg_salary,
       MAX(salary) AS top_salary
FROM employees
GROUP BY department
ORDER BY avg_salary DESC;
-- department  | total | avg_salary | top_salary
-- Engineering | 2     | 88500      | 92000
-- Marketing   | 2     | 63500      | 67000
-- HR          | 1     | 55000      | 55000

Example 3 — Operation (HAVING to filter groups):
SELECT department, COUNT(*) AS headcount
FROM employees
GROUP BY department
HAVING COUNT(*) > 1;
-- department  | headcount
-- Engineering | 2
-- Marketing   | 2
-- HR is excluded because it has only 1 employee

Example 4 — Concrete real-world comparison:
An HR system needs a monthly salary report showing average salary per department,
only for departments with more than one employee, sorted by average salary.

SELECT department,
       COUNT(*) AS employees,
       ROUND(AVG(salary), 2) AS avg_salary,
       SUM(salary) AS total_payroll
FROM employees
GROUP BY department
HAVING COUNT(*) > 1
ORDER BY avg_salary DESC;
-- department  | employees | avg_salary | total_payroll
-- Engineering | 2         | 88500.00   | 177000
-- Marketing   | 2         | 63500.00   | 127000
""",

"key_points": """
- SELECT retrieves data from one or more tables
- SELECT * retrieves all columns — use specific column names when possible
- AS creates an alias for a column or expression in the result
- ORDER BY sorts results — ASC is default, DESC reverses order
- DISTINCT removes duplicate values from results
- LIMIT restricts the number of rows returned
- COUNT, SUM, AVG, MAX, MIN are aggregate functions that summarize data
- GROUP BY groups rows with the same value — used with aggregate functions
- HAVING filters groups after GROUP BY — different from WHERE
- WHERE filters individual rows before grouping
- Correct clause order: SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT
- Aggregate functions ignore NULL values by default
- SELECT without WHERE scans the entire table — always filter when possible
""",

"misconceptions": """
- "SELECT * is fine for all queries" — SELECT * retrieves every column including ones not needed. On wide tables this wastes memory and slows queries. Always select only the columns you need.
- "HAVING and WHERE do the same thing" — WHERE filters individual rows before grouping. HAVING filters groups after GROUP BY. You cannot use HAVING to filter individual rows.
- "ORDER BY is applied before WHERE" — SQL processes clauses in this order: FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY. ORDER BY is always last.
- "COUNT(*) and COUNT(column) are the same" — COUNT(*) counts all rows including nulls. COUNT(column) counts only non-null values in that column.
- "AVG calculates the average of all rows including nulls" — AVG ignores NULL values. If 5 rows exist but one salary is NULL, AVG divides by 4 not 5.
- "DISTINCT removes all duplicates across all columns" — DISTINCT applies to the combination of all selected columns. SELECT DISTINCT name, city removes duplicate name+city pairs, not just duplicate names.
""",

"real_world_use": """
- Business intelligence dashboards use GROUP BY and aggregates to show sales by region, department, or time period
- E-commerce platforms use SELECT with ORDER BY and LIMIT to show top-selling products
- HR systems use AVG and GROUP BY to generate salary reports by department or role
- Analytics tools use COUNT and DISTINCT to measure unique users, sessions, and events
- Inventory systems use SUM and MIN to track total stock and identify low-stock items
- Financial reporting systems use SUM and GROUP BY to aggregate revenue and expenses by category
""",

"next_concept_link": """
SELECT retrieves data from tables but returns all rows by default. The next concept — WHERE and Filters — adds precision to queries by specifying exactly which rows to retrieve. WHERE is what makes queries targeted, efficient, and useful for real-world data retrieval.
"""
},

# ============================================================
# S3 — WHERE and Filters
# ============================================================
{
"concept_id": "S3",
"topic": "WHERE and Filters",
"base_content": """
The WHERE clause filters rows in a SQL query based on one or more conditions. Only rows that satisfy the condition are included in the result. WHERE is applied before GROUP BY, aggregation, and ORDER BY — it filters raw rows from the table.

Basic WHERE syntax:
SELECT columns FROM table WHERE condition;

Setup — sample table used throughout:
CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    salary DECIMAL(10,2),
    hire_date TEXT,
    city TEXT,
    active INTEGER
);

INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 85000, '2020-03-15', 'Mumbai', 1);
INSERT INTO employees VALUES (2, 'Bob', 'Marketing', 60000, '2019-07-22', 'Delhi', 1);
INSERT INTO employees VALUES (3, 'Charlie', 'Engineering', 92000, '2018-01-10', 'Mumbai', 1);
INSERT INTO employees VALUES (4, 'Diana', 'HR', 55000, '2021-11-05', 'Bangalore', 0);
INSERT INTO employees VALUES (5, 'Eve', 'Marketing', 67000, '2020-08-30', 'Delhi', 1);
INSERT INTO employees VALUES (6, 'Frank', 'Engineering', 78000, '2022-06-01', 'Pune', 1);

Comparison operators:
SELECT name, salary FROM employees WHERE salary > 70000;
-- name    | salary
-- Alice   | 85000
-- Charlie | 92000

SELECT name, salary FROM employees WHERE salary = 60000;
-- name | salary
-- Bob  | 60000

SELECT name, salary FROM employees WHERE salary != 60000;
-- returns all rows except Bob

Comparison operators available:
= equal
!= or <> not equal
> greater than
< less than
>= greater than or equal
<= less than or equal

Logical operators — AND, OR, NOT:
AND — both conditions must be true:
SELECT name, department, salary FROM employees
WHERE department = 'Engineering' AND salary > 80000;
-- name    | department  | salary
-- Alice   | Engineering | 85000
-- Charlie | Engineering | 92000

OR — at least one condition must be true:
SELECT name, city FROM employees
WHERE city = 'Mumbai' OR city = 'Delhi';
-- name    | city
-- Alice   | Mumbai
-- Bob     | Delhi
-- Charlie | Mumbai
-- Eve     | Delhi

NOT — negates a condition:
SELECT name, department FROM employees
WHERE NOT department = 'HR';
-- returns everyone except Diana

Combining AND and OR — use parentheses:
SELECT name, department, salary FROM employees
WHERE (department = 'Engineering' OR department = 'Marketing')
AND salary > 65000;
-- name    | department  | salary
-- Alice   | Engineering | 85000
-- Charlie | Engineering | 92000
-- Eve     | Marketing   | 67000

BETWEEN — range filter (inclusive):
SELECT name, salary FROM employees
WHERE salary BETWEEN 60000 AND 85000;
-- name  | salary
-- Alice | 85000
-- Bob   | 60000
-- Eve   | 67000
-- Frank | 78000

IN — match against a list of values:
SELECT name, city FROM employees
WHERE city IN ('Mumbai', 'Pune');
-- name    | city
-- Alice   | Mumbai
-- Charlie | Mumbai
-- Frank   | Pune

NOT IN — exclude a list of values:
SELECT name, department FROM employees
WHERE department NOT IN ('HR', 'Marketing');
-- name    | department
-- Alice   | Engineering
-- Charlie | Engineering
-- Frank   | Engineering

LIKE — pattern matching for text:
% matches zero or more characters
_ matches exactly one character

SELECT name FROM employees WHERE name LIKE 'A%';
-- name
-- Alice

SELECT name FROM employees WHERE name LIKE '%e';
-- name
-- Alice
-- Eve

SELECT name FROM employees WHERE name LIKE '_o%';
-- name
-- Bob

IS NULL and IS NOT NULL:
SELECT name FROM employees WHERE city IS NULL;
-- returns rows where city has no value

SELECT name FROM employees WHERE city IS NOT NULL;
-- returns rows where city has a value
-- All 6 employees in our example

NULL checks — never use = for NULL:
-- WRONG:
SELECT * FROM employees WHERE city = NULL;  -- returns nothing, always

-- CORRECT:
SELECT * FROM employees WHERE city IS NULL;

Filtering with dates:
SELECT name, hire_date FROM employees
WHERE hire_date >= '2020-01-01';
-- name   | hire_date
-- Alice  | 2020-03-15
-- Diana  | 2021-11-05
-- Eve    | 2020-08-30
-- Frank  | 2022-06-01

WHERE with boolean/integer flags:
SELECT name FROM employees WHERE active = 1;
-- returns all active employees

SELECT name FROM employees WHERE active = 0;
-- name
-- Diana

WHERE vs HAVING:
WHERE filters rows before grouping — used on individual row data
HAVING filters groups after GROUP BY — used on aggregated data

-- Using WHERE to filter before aggregation:
SELECT department, AVG(salary) AS avg_salary
FROM employees
WHERE active = 1
GROUP BY department;
-- Only active employees are included before averaging

Strengths of WHERE:
- Makes queries precise and targeted
- Reduces the amount of data scanned and returned
- Works with all data types — numbers, strings, dates, booleans
- Supports complex conditions with AND, OR, NOT, IN, BETWEEN, LIKE

Weaknesses to be aware of:
- Using functions on columns in WHERE prevents index usage — slows queries
- LIKE with a leading % cannot use indexes — full table scan
- Complex WHERE with many OR conditions can be hard to optimize
- NULL comparisons require IS NULL not = NULL — a common mistake
""",

"examples": """
Example 1 — Simple (basic comparison filter):
SELECT name, salary FROM employees
WHERE salary > 70000;
-- name    | salary
-- Alice   | 85000
-- Charlie | 92000
-- Frank   | 78000

Example 2 — Slightly deeper (combining multiple conditions):
SELECT name, department, salary, city
FROM employees
WHERE (department = 'Engineering' OR department = 'Marketing')
  AND salary >= 65000
  AND active = 1;
-- name    | department  | salary | city
-- Alice   | Engineering | 85000  | Mumbai
-- Charlie | Engineering | 92000  | Mumbai
-- Eve     | Marketing   | 67000  | Delhi
-- Frank   | Engineering | 78000  | Pune

Example 3 — Operation (IN, BETWEEN, LIKE together):
-- Find employees in specific cities with salary in a range whose name starts with a vowel
SELECT name, city, salary
FROM employees
WHERE city IN ('Mumbai', 'Delhi', 'Pune')
  AND salary BETWEEN 60000 AND 90000
  AND name LIKE 'A%' OR name LIKE 'E%';
-- name  | city   | salary
-- Alice | Mumbai | 85000
-- Eve   | Delhi  | 67000

Example 4 — Concrete real-world comparison:
An HR system needs to find all active Engineering employees hired after 2019
with a salary above 75000 for a performance review shortlist.

SELECT name, salary, hire_date, city
FROM employees
WHERE department = 'Engineering'
  AND active = 1
  AND hire_date > '2019-12-31'
  AND salary > 75000
ORDER BY salary DESC;
-- name  | salary | hire_date  | city
-- Alice | 85000  | 2020-03-15 | Mumbai
-- Frank | 78000  | 2022-06-01 | Pune
""",

"key_points": """
- WHERE filters rows before any grouping or aggregation
- Comparison operators: =, !=, <>, >, <, >=, <=
- AND requires both conditions to be true
- OR requires at least one condition to be true
- NOT negates a condition
- BETWEEN is inclusive on both ends
- IN matches against a list of values — cleaner than multiple OR conditions
- LIKE uses % for zero or more characters and _ for exactly one character
- IS NULL and IS NOT NULL check for missing values — never use = NULL
- LIKE with a leading % causes a full table scan — avoid when possible
- Use parentheses when combining AND and OR to control evaluation order
- WHERE is applied before GROUP BY — HAVING is applied after
- Filtering with functions on indexed columns prevents index usage
""",

"misconceptions": """
- "WHERE column = NULL works" — NULL is not a value, it is the absence of a value. = NULL always returns nothing. Always use IS NULL or IS NOT NULL.
- "BETWEEN is exclusive on the endpoints" — BETWEEN is inclusive on both ends. BETWEEN 10 AND 20 includes both 10 and 20.
- "WHERE and HAVING are interchangeable" — WHERE filters rows before grouping. HAVING filters groups after GROUP BY. Using HAVING where WHERE belongs is inefficient and sometimes incorrect.
- "LIKE '%value' is fast" — LIKE with a leading % cannot use an index and causes a full table scan on the column. It is slow on large tables.
- "OR conditions are always safe" — Many OR conditions on different columns can prevent index usage and slow queries significantly. IN is often more efficient than multiple OR conditions on the same column.
- "NOT IN is always safe with subqueries" — NOT IN with a subquery that returns NULL values produces no results. Use NOT EXISTS instead when dealing with subqueries that might return NULLs.
""",

"real_world_use": """
- E-commerce platforms filter orders by status, date range, and customer ID to show relevant order history
- Banking applications filter transactions by account, date, and amount to generate statements
- HR systems filter employees by department, location, and status for payroll and reporting
- Healthcare systems filter patient records by diagnosis, date, and doctor for case management
- Inventory systems filter products by stock level, category, and supplier for reorder reports
- Analytics platforms filter event logs by user, time window, and event type for behavioral analysis
""",

"next_concept_link": """
WHERE filters rows within a single table. The next concept — JOIN Operations — extends this by combining rows from multiple tables based on a related column. JOINs are how relational databases fulfill their core promise — linking separate tables together to answer questions that span multiple entities.
"""
},

# ============================================================
# S4 — JOIN Operations
# ============================================================
{
"concept_id": "S4",
"topic": "JOIN Operations",
"base_content": """
A JOIN combines rows from two or more tables based on a related column between them. JOINs are the mechanism that makes relational databases relational — they allow you to query data that is spread across multiple tables as if it were one unified result.

Why JOINs exist:
In a well-designed database, data is split across tables to avoid duplication. Customer data lives in a customers table. Order data lives in an orders table. To answer the question "what did each customer order?" you need to JOIN these two tables on the shared customer_id column.

Setup — sample tables used throughout:
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT,
    city TEXT
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product TEXT,
    amount DECIMAL(10,2)
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT,
    price DECIMAL(10,2)
);

INSERT INTO customers VALUES (1, 'Alice', 'Mumbai');
INSERT INTO customers VALUES (2, 'Bob', 'Delhi');
INSERT INTO customers VALUES (3, 'Charlie', 'Pune');
INSERT INTO customers VALUES (4, 'Diana', 'Bangalore');

INSERT INTO orders VALUES (1, 1, 'Laptop', 999.99);
INSERT INTO orders VALUES (2, 1, 'Mouse', 25.50);
INSERT INTO orders VALUES (3, 2, 'Keyboard', 45.00);
INSERT INTO orders VALUES (4, 3, 'Monitor', 299.99);

-- Note: Diana (customer_id 4) has no orders
-- Note: No order references customer_id 5 (does not exist)

INNER JOIN — returns only matching rows from both tables:
INNER JOIN is the most common join type. It returns rows where the join condition is satisfied in both tables. Non-matching rows are excluded.

SELECT customers.name, orders.product, orders.amount
FROM customers
INNER JOIN orders ON customers.customer_id = orders.customer_id;
-- name    | product  | amount
-- Alice   | Laptop   | 999.99
-- Alice   | Mouse    | 25.50
-- Bob     | Keyboard | 45.00
-- Charlie | Monitor  | 299.99
-- Diana is excluded — she has no orders

Using aliases to simplify JOIN queries:
SELECT c.name, o.product, o.amount
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id;

LEFT JOIN (LEFT OUTER JOIN) — returns all rows from the left table:
LEFT JOIN returns all rows from the left table and matching rows from the right table. If no match exists, NULL is returned for right table columns.

SELECT c.name, o.product, o.amount
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id;
-- name    | product  | amount
-- Alice   | Laptop   | 999.99
-- Alice   | Mouse    | 25.50
-- Bob     | Keyboard | 45.00
-- Charlie | Monitor  | 299.99
-- Diana   | NULL     | NULL  <- Diana included with NULL for order columns

LEFT JOIN is used when you want all records from the primary table regardless of whether a match exists in the secondary table.

Finding customers with NO orders using LEFT JOIN:
SELECT c.name
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL;
-- name
-- Diana

RIGHT JOIN (RIGHT OUTER JOIN) — returns all rows from the right table:
RIGHT JOIN is the mirror of LEFT JOIN. All rows from the right table are returned. Rows from the left table with no match return NULL.

SELECT c.name, o.product
FROM customers c
RIGHT JOIN orders o ON c.customer_id = o.customer_id;
-- Returns all orders, matching customer names where available
-- Most databases support RIGHT JOIN but LEFT JOIN is preferred by convention

FULL OUTER JOIN — returns all rows from both tables:
FULL OUTER JOIN returns all rows from both tables. Rows with no match in the other table return NULL for those columns.

SELECT c.name, o.product
FROM customers c
FULL OUTER JOIN orders o ON c.customer_id = o.customer_id;
-- Returns all customers and all orders
-- Diana appears with NULL product
-- Any orphaned order appears with NULL customer name

Note: SQLite does not support FULL OUTER JOIN natively. Use UNION of LEFT JOIN and RIGHT JOIN.

CROSS JOIN — cartesian product of both tables:
CROSS JOIN returns every combination of rows from both tables. If table A has 4 rows and table B has 3 rows, CROSS JOIN returns 12 rows.

SELECT c.name, p.name AS product
FROM customers c
CROSS JOIN products p;
-- Returns every customer paired with every product
-- Used for generating combinations — rarely used in practice

SELF JOIN — joining a table with itself:
A SELF JOIN is when a table is joined to itself. Useful for hierarchical data like employee-manager relationships.

CREATE TABLE staff (
    id INTEGER PRIMARY KEY,
    name TEXT,
    manager_id INTEGER
);

INSERT INTO staff VALUES (1, 'Alice', NULL);   -- Alice is the top manager
INSERT INTO staff VALUES (2, 'Bob', 1);         -- Bob reports to Alice
INSERT INTO staff VALUES (3, 'Charlie', 1);     -- Charlie reports to Alice
INSERT INTO staff VALUES (4, 'Diana', 2);       -- Diana reports to Bob

SELECT e.name AS employee, m.name AS manager
FROM staff e
LEFT JOIN staff m ON e.manager_id = m.id;
-- employee | manager
-- Alice    | NULL
-- Bob      | Alice
-- Charlie  | Alice
-- Diana    | Bob

Joining more than two tables:
SELECT c.name, o.product, o.amount
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
INNER JOIN products p ON o.product = p.name
WHERE p.category = 'Electronics';

JOIN with WHERE and aggregation:
SELECT c.name, COUNT(o.order_id) AS order_count, SUM(o.amount) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC;
-- name    | order_count | total_spent
-- Alice   | 2           | 1025.49
-- Charlie | 1           | 299.99
-- Bob     | 1           | 45.00
-- Diana   | 0           | NULL

Strengths of JOINs:
- Enable querying across normalized tables without duplicating data
- INNER JOIN is fast and precise — returns only relevant rows
- LEFT JOIN is safe — always returns the primary table rows
- Multiple JOINs can answer complex multi-entity questions

Weaknesses to be aware of:
- JOINs on large tables without indexes are slow
- Multiple JOINs increase query complexity and can reduce readability
- CROSS JOIN on large tables produces enormous result sets
- Incorrect join conditions produce wrong or duplicate results silently
""",

"examples": """
Example 1 — Simple (INNER JOIN):
SELECT c.name, o.product, o.amount
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id;
-- name    | product  | amount
-- Alice   | Laptop   | 999.99
-- Alice   | Mouse    | 25.50
-- Bob     | Keyboard | 45.00
-- Charlie | Monitor  | 299.99

Example 2 — Slightly deeper (LEFT JOIN with NULL detection):
SELECT c.name,
       COALESCE(CAST(COUNT(o.order_id) AS TEXT), '0') AS orders,
       COALESCE(CAST(SUM(o.amount) AS TEXT), '0.00') AS total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC NULLS LAST;
-- name    | orders | total_spent
-- Alice   | 2      | 1025.49
-- Charlie | 1      | 299.99
-- Bob     | 1      | 45.00
-- Diana   | 0      | 0.00

Example 3 — Operation (find customers with no orders):
SELECT c.name, c.city
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL;
-- name  | city
-- Diana | Bangalore

Example 4 — Concrete real-world comparison:
An e-commerce report needs each customer's name, city, number of orders,
and total amount spent — including customers who have never ordered.

SELECT c.name,
       c.city,
       COUNT(o.order_id) AS total_orders,
       ROUND(COALESCE(SUM(o.amount), 0), 2) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.city
ORDER BY total_spent DESC;
-- name    | city      | total_orders | total_spent
-- Alice   | Mumbai    | 2            | 1025.49
-- Charlie | Pune      | 1            | 299.99
-- Bob     | Delhi     | 1            | 45.00
-- Diana   | Bangalore | 0            | 0.00
""",

"key_points": """
- JOIN combines rows from two or more tables based on a related column
- INNER JOIN returns only rows with matching values in both tables
- LEFT JOIN returns all rows from the left table — non-matching right rows become NULL
- RIGHT JOIN returns all rows from the right table — non-matching left rows become NULL
- FULL OUTER JOIN returns all rows from both tables — NULLs where no match
- CROSS JOIN returns every combination of rows — use with caution
- SELF JOIN joins a table to itself — useful for hierarchical data
- Always specify the join condition with ON — missing ON causes a cartesian product
- Use table aliases to simplify multi-table queries
- LEFT JOIN with WHERE right_table.column IS NULL finds rows with no match
- JOIN conditions should be on indexed columns for best performance
- Multiple JOINs are chained — each JOIN adds another table to the result
- INNER JOIN is the most commonly used and most efficient join type
""",

"misconceptions": """
- "LEFT JOIN and INNER JOIN return the same results" — INNER JOIN excludes rows with no match. LEFT JOIN includes all left table rows even with no match. The results are different when unmatched rows exist.
- "JOIN order does not matter" — For INNER JOIN, order does not affect results but affects performance. For LEFT and RIGHT JOINs, order matters because it determines which table is the primary table.
- "You can only JOIN on primary and foreign keys" — You can JOIN on any columns with matching values. But joining on indexed primary and foreign keys is the most efficient.
- "CROSS JOIN is rarely useful" — CROSS JOIN is useful for generating test data, date ranges, and combination reports. It is dangerous on large tables but has legitimate uses.
- "A missing ON clause causes an error" — In some databases, a missing ON clause causes a CROSS JOIN, not an error. This silently returns an enormous result set.
- "JOINs duplicate data" — JOINs do not duplicate stored data. They temporarily combine rows in the result set. The underlying tables remain unchanged.
""",

"real_world_use": """
- E-commerce platforms JOIN customers, orders, and products to generate order history and receipts
- HR systems JOIN employees, departments, and salaries to generate payroll and org chart reports
- School systems JOIN students, enrollments, and courses to show each student's class schedule
- Banking systems JOIN accounts, transactions, and branches to generate account statements
- Healthcare systems JOIN patients, doctors, and appointments to manage scheduling and records
- Analytics platforms JOIN user events, sessions, and campaigns to measure marketing attribution
""",

"next_concept_link": """
JOINs allow querying across multiple tables. As tables grow to millions of rows, queries become slow without optimization. The next concept — Indexes — explains how databases create special data structures to speed up lookups, dramatically reducing query time on large datasets.
"""
},

# ============================================================
# S5 — Indexes
# ============================================================
{
"concept_id": "S5",
"topic": "Indexes",
"base_content": """
An index is a database object that speeds up data retrieval by creating a separate data structure that the database can search more efficiently than scanning every row in a table. An index in a database works similarly to an index at the back of a book — instead of reading every page, you look up the word in the index and jump directly to the right page.

Why indexes exist:
Without an index, every query that filters or searches a table must perform a full table scan — reading every single row. On a table with 10 million rows, this is slow. An index allows the database to jump directly to the relevant rows using a sorted or hashed structure.

How indexes work internally:
Most database indexes use a B-tree (Balanced Tree) structure. The B-tree keeps data sorted and allows searches, insertions, and deletions in O(log n) time.

When you query:
SELECT * FROM employees WHERE name = 'Alice';

Without index: database reads all rows, checks each name — O(n)
With index on name: database traverses B-tree, finds Alice directly — O(log n)

Creating an index:
-- Basic index on a single column
CREATE INDEX idx_employees_name ON employees(name);

-- Index on multiple columns (composite index)
CREATE INDEX idx_employees_dept_salary ON employees(department, salary);

-- Unique index — enforces uniqueness and speeds up lookups
CREATE UNIQUE INDEX idx_employees_email ON employees(email);

Viewing indexes:
-- In SQLite:
PRAGMA index_list('employees');

-- In PostgreSQL / MySQL:
SHOW INDEXES FROM employees;

Dropping an index:
DROP INDEX idx_employees_name;

When indexes help:
-- This query benefits from an index on department:
SELECT * FROM employees WHERE department = 'Engineering';

-- This query benefits from an index on salary:
SELECT * FROM employees WHERE salary > 80000 ORDER BY salary;

-- This query benefits from a composite index on (department, salary):
SELECT * FROM employees WHERE department = 'Engineering' AND salary > 80000;

When indexes do NOT help or hurt:
-- LIKE with leading wildcard cannot use B-tree index:
SELECT * FROM employees WHERE name LIKE '%alice%';

-- Function on indexed column prevents index use:
SELECT * FROM employees WHERE LOWER(name) = 'alice';

-- Small tables — full scan is faster than index lookup overhead:
SELECT * FROM tiny_table WHERE id = 5;

-- High write frequency — indexes slow down INSERT, UPDATE, DELETE:
INSERT INTO employees VALUES (...); -- must update all indexes on this table

Types of indexes:

Single column index:
CREATE INDEX idx_name ON employees(name);
-- Best for queries that filter or sort by one column

Composite index:
CREATE INDEX idx_dept_salary ON employees(department, salary);
-- Best for queries that filter on multiple columns together
-- Column order matters — this index helps WHERE department = ? AND salary > ?
-- But does NOT help WHERE salary > ? alone (salary is not the leading column)

Unique index:
CREATE UNIQUE INDEX idx_email ON employees(email);
-- Enforces uniqueness like a UNIQUE constraint
-- Also speeds up lookups on the email column

Partial index (PostgreSQL):
CREATE INDEX idx_active_employees ON employees(name) WHERE active = 1;
-- Index only covers rows where active = 1
-- Smaller and faster for queries that always filter by active = 1

How the database decides to use an index:
The query optimizer decides whether to use an index. It estimates the cost of using the index versus doing a full scan. If the query returns a large percentage of rows, a full scan may be faster. If the query is highly selective (few matching rows), the index is used.

-- Check query execution plan in SQLite:
EXPLAIN QUERY PLAN
SELECT * FROM employees WHERE department = 'Engineering';
-- Shows whether index is used or full scan is performed

Index trade-offs:
Indexes speed up reads but slow down writes.
Every INSERT, UPDATE, or DELETE on an indexed column requires updating the index.
Indexes also consume additional disk space.

Read-heavy tables: add indexes generously
Write-heavy tables: add indexes carefully — only where reads are critical

Strengths of indexes:
- Dramatically reduce query time on large tables — O(n) to O(log n)
- Speed up ORDER BY and GROUP BY on indexed columns
- Enforce uniqueness with UNIQUE indexes
- Composite indexes support multi-column filter queries

Weaknesses of indexes:
- Slow down INSERT, UPDATE, DELETE operations
- Consume additional disk space
- Wrong indexes can mislead the optimizer
- Too many indexes create maintenance overhead
- Leading wildcard LIKE and functions on columns bypass indexes
""",

"examples": """
Example 1 — Simple (creating and using a single index):
-- Without index — full table scan on 1 million rows
SELECT * FROM employees WHERE department = 'Engineering';
-- Slow — reads every row

-- Create index
CREATE INDEX idx_department ON employees(department);

-- With index — B-tree lookup directly to Engineering rows
SELECT * FROM employees WHERE department = 'Engineering';
-- Fast — jumps directly to matching rows

Example 2 — Slightly deeper (composite index and column order):
-- Create composite index
CREATE INDEX idx_dept_salary ON employees(department, salary);

-- This query USES the index (department is the leading column):
SELECT * FROM employees
WHERE department = 'Engineering' AND salary > 80000;

-- This query also USES the index (leading column only):
SELECT * FROM employees WHERE department = 'Engineering';

-- This query does NOT use the composite index (salary alone, not leading column):
SELECT * FROM employees WHERE salary > 80000;
-- Needs a separate index on salary alone for this to be fast

Example 3 — Operation (checking query plan):
-- Create table and index
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    amount DECIMAL(10,2)
);
CREATE INDEX idx_customer ON orders(customer_id);

-- Check if index is used:
EXPLAIN QUERY PLAN
SELECT * FROM orders WHERE customer_id = 42;
-- Output will show: SEARCH orders USING INDEX idx_customer

EXPLAIN QUERY PLAN
SELECT * FROM orders WHERE amount > 100;
-- Output will show: SCAN orders (full table scan — no index on amount)

Example 4 — Concrete real-world comparison:
An e-commerce platform has 10 million orders. Customers check their order history
frequently. Without an index on customer_id, every order history request scans
10 million rows. With an index, it jumps directly to that customer's orders.

-- Slow without index:
SELECT * FROM orders WHERE customer_id = 1001;
-- Scans 10 million rows every time

-- Fast with index:
CREATE INDEX idx_orders_customer ON orders(customer_id);
SELECT * FROM orders WHERE customer_id = 1001;
-- Jumps directly to customer 1001's orders in O(log n)
""",

"key_points": """
- An index is a data structure that speeds up row lookups — similar to a book index
- Without an index, every query does a full table scan — O(n)
- With a B-tree index, lookups cost O(log n)
- CREATE INDEX creates an index on a column or set of columns
- Indexes speed up SELECT, WHERE, ORDER BY, GROUP BY, and JOIN operations
- Indexes slow down INSERT, UPDATE, DELETE because indexes must also be updated
- Composite indexes work best when the leading column is used in the query
- Column order in a composite index matters — leading column is most important
- LIKE with a leading % cannot use a B-tree index
- Functions applied to indexed columns in WHERE prevent index usage
- UNIQUE indexes enforce uniqueness and speed up lookups
- Use EXPLAIN or EXPLAIN QUERY PLAN to check if an index is being used
- Too many indexes waste disk space and slow down writes
- Indexes are most valuable on large tables with selective filter queries
""",

"misconceptions": """
- "More indexes always means faster queries" — Too many indexes slow down writes because every insert and update must update all indexes. Only add indexes where they provide measurable read benefit.
- "An index on a column means every query on that column uses it" — The query optimizer decides when to use an index. If the query returns most rows, a full scan may be faster than an index lookup.
- "Composite index on (A, B) helps queries filtering only on B" — Composite indexes must be used starting from the leading column. An index on (A, B) does not help queries that only filter on B alone.
- "LIKE queries always use indexes" — LIKE with a leading wildcard like '%value' cannot use a B-tree index. LIKE 'value%' can use an index because it has a known starting point.
- "Indexes are only useful for SELECT queries" — Indexes also speed up JOIN conditions and ORDER BY operations. They are not limited to WHERE clause filtering.
- "Primary keys do not need separate indexes" — Primary keys automatically create an index in most databases. You do not need to create a separate index on the primary key column.
""",

"real_world_use": """
- E-commerce platforms index customer_id in orders tables to speed up order history lookups
- Search engines index title and content columns to power fast keyword search
- Banking systems index account_id and transaction_date to speed up statement generation
- HR systems index department and hire_date for fast employee filtering and reporting
- Healthcare systems index patient_id and doctor_id to speed up appointment and record lookups
- Analytics platforms index event_type and timestamp for fast time-range queries on large event logs
""",

"next_concept_link": """
Indexes optimize basic query performance. The next concept — Window Functions — introduces a more advanced SQL feature that performs calculations across a set of related rows without collapsing them into a single result. Window functions enable powerful analytics like running totals, rankings, and moving averages that GROUP BY alone cannot produce.
"""
},

# ============================================================
# S6 — Window Functions
# ============================================================
{
"concept_id": "S6",
"topic": "Window Functions",
"base_content": """
A window function performs a calculation across a set of rows that are related to the current row — called a window — without collapsing those rows into a single output row like GROUP BY does. Window functions allow you to compute aggregates, rankings, and running totals while still seeing all individual rows in the result.

Why window functions exist:
GROUP BY aggregates rows into groups and collapses them. You lose the individual rows. Window functions compute across a window of rows and return a value for every row — the original rows are preserved.

GROUP BY collapses rows — one output row per group:
SELECT department, AVG(salary) FROM employees GROUP BY department;
-- Engineering | 88500
-- Marketing   | 63500
-- You cannot see individual employees anymore

Window function — computes per group but keeps all rows:
SELECT name, department, salary,
       AVG(salary) OVER (PARTITION BY department) AS dept_avg
FROM employees;
-- name    | department  | salary | dept_avg
-- Alice   | Engineering | 85000  | 88500
-- Charlie | Engineering | 92000  | 88500
-- Bob     | Marketing   | 60000  | 63500
-- Eve     | Marketing   | 67000  | 63500
-- Diana   | HR          | 55000  | 55000

Window function syntax:
function_name() OVER (
    PARTITION BY column    -- divide rows into groups (optional)
    ORDER BY column        -- define row order within the window (optional)
    ROWS/RANGE BETWEEN ... -- define window frame (optional)
)

Setup — sample table:
CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    salary DECIMAL(10,2),
    hire_date TEXT
);

INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 85000, '2020-03-15');
INSERT INTO employees VALUES (2, 'Bob', 'Marketing', 60000, '2019-07-22');
INSERT INTO employees VALUES (3, 'Charlie', 'Engineering', 92000, '2018-01-10');
INSERT INTO employees VALUES (4, 'Diana', 'HR', 55000, '2021-11-05');
INSERT INTO employees VALUES (5, 'Eve', 'Marketing', 67000, '2020-08-30');
INSERT INTO employees VALUES (6, 'Frank', 'Engineering', 78000, '2022-06-01');

PARTITION BY — dividing the window into groups:
PARTITION BY divides rows into groups. The window function is applied independently within each partition.

SELECT name, department, salary,
       MAX(salary) OVER (PARTITION BY department) AS dept_max_salary
FROM employees;
-- name    | department  | salary | dept_max_salary
-- Alice   | Engineering | 85000  | 92000
-- Charlie | Engineering | 92000  | 92000
-- Frank   | Engineering | 78000  | 92000
-- Bob     | Marketing   | 60000  | 67000
-- Eve     | Marketing   | 67000  | 67000
-- Diana   | HR          | 55000  | 55000

Ranking functions:

ROW_NUMBER — unique sequential number for each row:
SELECT name, department, salary,
       ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS row_num
FROM employees;
-- name    | department  | salary | row_num
-- Charlie | Engineering | 92000  | 1
-- Alice   | Engineering | 85000  | 2
-- Frank   | Engineering | 78000  | 3
-- Eve     | Marketing   | 67000  | 1
-- Bob     | Marketing   | 60000  | 2
-- Diana   | HR          | 55000  | 1

RANK — rank with gaps for ties:
SELECT name, salary,
       RANK() OVER (ORDER BY salary DESC) AS salary_rank
FROM employees;
-- If two rows tie at rank 2, the next rank is 4 (gap)

DENSE_RANK — rank without gaps for ties:
SELECT name, salary,
       DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank
FROM employees;
-- If two rows tie at rank 2, the next rank is 3 (no gap)

Finding top N per group using ROW_NUMBER:
SELECT name, department, salary
FROM (
    SELECT name, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
    FROM employees
) ranked
WHERE rn = 1;
-- Returns the highest-paid employee in each department
-- name    | department  | salary
-- Charlie | Engineering | 92000
-- Eve     | Marketing   | 67000
-- Diana   | HR          | 55000

LAG and LEAD — accessing previous and next rows:
LAG accesses the value from a previous row. LEAD accesses the value from a next row.

SELECT name, salary,
       LAG(salary) OVER (ORDER BY salary) AS prev_salary,
       LEAD(salary) OVER (ORDER BY salary) AS next_salary
FROM employees;
-- name    | salary | prev_salary | next_salary
-- Diana   | 55000  | NULL        | 60000
-- Bob     | 60000  | 55000       | 67000
-- Eve     | 67000  | 60000       | 78000
-- Frank   | 78000  | 67000       | 85000
-- Alice   | 85000  | 78000       | 92000
-- Charlie | 92000  | 85000       | NULL

Salary difference from previous row:
SELECT name, salary,
       salary - LAG(salary) OVER (ORDER BY salary) AS salary_diff
FROM employees;

Running totals using SUM with ORDER BY in OVER:
SELECT name, department, salary,
       SUM(salary) OVER (PARTITION BY department ORDER BY hire_date) AS running_total
FROM employees;
-- Shows cumulative salary within each department ordered by hire date

FIRST_VALUE and LAST_VALUE:
SELECT name, salary,
       FIRST_VALUE(name) OVER (PARTITION BY department ORDER BY salary DESC) AS top_earner
FROM employees;
-- Shows the top earner in each department alongside every row

NTILE — divide rows into buckets:
SELECT name, salary,
       NTILE(4) OVER (ORDER BY salary) AS salary_quartile
FROM employees;
-- Divides employees into 4 salary quartiles
-- name    | salary | salary_quartile
-- Diana   | 55000  | 1
-- Bob     | 60000  | 1
-- Eve     | 67000  | 2
-- Frank   | 78000  | 2
-- Alice   | 85000  | 3
-- Charlie | 92000  | 4

Strengths of window functions:
- Preserve individual rows while computing group-level statistics
- Enable complex analytics that GROUP BY cannot produce
- Clean syntax compared to correlated subqueries
- Highly efficient — computed in a single pass over the data
- Support ranking, running totals, lag/lead comparisons, and percentiles

Weaknesses to be aware of:
- Cannot be used in WHERE or HAVING clauses directly — use a subquery
- Can be computationally expensive on very large datasets without proper indexing
- Syntax varies slightly across database systems
- Require careful understanding of PARTITION BY and ORDER BY interaction
""",

"examples": """
Example 1 — Simple (department average alongside each row):
SELECT name, department, salary,
       ROUND(AVG(salary) OVER (PARTITION BY department), 2) AS dept_avg,
       salary - AVG(salary) OVER (PARTITION BY department) AS diff_from_avg
FROM employees;
-- name    | department  | salary | dept_avg | diff_from_avg
-- Alice   | Engineering | 85000  | 85000    | -3500
-- Charlie | Engineering | 92000  | 85000    | +3500
-- Frank   | Engineering | 78000  | 85000    | -6500
-- Bob     | Marketing   | 60000  | 63500    | -3500
-- Eve     | Marketing   | 67000  | 63500    | +3500
-- Diana   | HR          | 55000  | 55000    | 0

Example 2 — Slightly deeper (ranking within department):
SELECT name, department, salary,
       ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank,
       RANK() OVER (ORDER BY salary DESC) AS overall_rank
FROM employees;
-- name    | department  | salary | dept_rank | overall_rank
-- Charlie | Engineering | 92000  | 1         | 1
-- Alice   | Engineering | 85000  | 2         | 2
-- Frank   | Engineering | 78000  | 3         | 3
-- Eve     | Marketing   | 67000  | 1         | 4
-- Bob     | Marketing   | 60000  | 2         | 5
-- Diana   | HR          | 55000  | 1         | 6

Example 3 — Operation (top earner per department):
SELECT name, department, salary
FROM (
    SELECT name, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
    FROM employees
) sub
WHERE rn = 1;
-- name    | department  | salary
-- Charlie | Engineering | 92000
-- Eve     | Marketing   | 67000
-- Diana   | HR          | 55000

Example 4 — Concrete real-world comparison:
A finance team needs a report showing each employee's salary,
their department's average, their rank within the company,
and how their salary compares to the previous rank.

SELECT name, department, salary,
       ROUND(AVG(salary) OVER (PARTITION BY department), 2) AS dept_avg,
       RANK() OVER (ORDER BY salary DESC) AS company_rank,
       salary - LAG(salary) OVER (ORDER BY salary DESC) AS gap_from_above
FROM employees
ORDER BY company_rank;
-- name    | department  | salary | dept_avg | company_rank | gap_from_above
-- Charlie | Engineering | 92000  | 85000    | 1            | NULL
-- Alice   | Engineering | 85000  | 85000    | 2            | -7000
-- Frank   | Engineering | 78000  | 85000    | 3            | -7000
-- Eve     | Marketing   | 67000  | 63500    | 4            | -11000
-- Bob     | Marketing   | 60000  | 63500    | 5            | -7000
-- Diana   | HR          | 55000  | 55000    | 6            | -5000
""",

"key_points": """
- Window functions compute across a set of related rows without collapsing them
- GROUP BY collapses rows — window functions preserve all rows
- OVER() defines the window — it is required for all window functions
- PARTITION BY divides rows into groups within the window
- ORDER BY within OVER defines row order inside the window
- ROW_NUMBER assigns a unique sequential number — no ties
- RANK assigns rank with gaps for ties
- DENSE_RANK assigns rank without gaps for ties
- LAG accesses the value from a previous row — useful for comparisons
- LEAD accesses the value from a next row
- SUM with ORDER BY in OVER creates a running total
- NTILE divides rows into equal-sized buckets
- FIRST_VALUE and LAST_VALUE access the first and last value in the window
- Window functions cannot be used directly in WHERE or HAVING — wrap in a subquery
""",

"misconceptions": """
- "Window functions and GROUP BY do the same thing" — GROUP BY collapses rows into one per group. Window functions compute group statistics but keep every individual row in the output.
- "PARTITION BY is required in window functions" — PARTITION BY is optional. Without it, the entire result set is treated as one window. Only ORDER BY or ROWS/RANGE may be specified.
- "ROW_NUMBER, RANK, and DENSE_RANK are interchangeable" — ROW_NUMBER always gives unique numbers. RANK leaves gaps after ties. DENSE_RANK does not leave gaps. They produce different results when ties exist.
- "Window functions can be filtered with WHERE" — Window functions are computed after WHERE is applied. You cannot filter on a window function result in WHERE. Use a subquery or CTE.
- "LAG always looks at the immediately previous row" — LAG accepts an optional offset parameter. LAG(salary, 2) looks back two rows. The default offset is 1.
- "Window functions are only for analytics and reporting" — Window functions are also used in application queries for features like next/previous record navigation, running balances, and streak counting.
""",

"real_world_use": """
- Financial systems use running SUM window functions to calculate cumulative revenue and account balances over time
- HR systems use RANK and DENSE_RANK to generate salary percentile reports within departments
- E-commerce platforms use ROW_NUMBER to find the most recent order per customer
- Analytics dashboards use LAG to compute week-over-week or month-over-month changes in metrics
- Leaderboard systems use RANK and DENSE_RANK to show player rankings in games and competitions
- Data pipelines use NTILE to divide datasets into quantiles for statistical analysis and machine learning preprocessing
""",

"next_concept_link": """
Window functions enable powerful row-level analytics. The next concept — Common Table Expressions (CTEs) — provides a way to write cleaner, more readable, and reusable SQL queries by defining named temporary result sets. CTEs make complex queries with multiple steps — including recursive queries — far easier to write and understand.
"""
},

# ============================================================
# S7 — Common Table Expressions (CTE)
# ============================================================
{
"concept_id": "S7",
"topic": "Common Table Expressions (CTE)",
"base_content": """
A Common Table Expression (CTE) is a named temporary result set defined within a SQL query using the WITH keyword. A CTE exists only for the duration of the query and can be referenced like a table within that query. CTEs make complex queries easier to read, write, and maintain by breaking them into named, logical steps.

Why CTEs exist:
Complex SQL queries often require subqueries nested inside other subqueries. This becomes hard to read, debug, and maintain. CTEs allow you to define each logical step separately, name it clearly, and reference it by name — making the query read like a sequence of steps.

Basic CTE syntax:
WITH cte_name AS (
    SELECT ...
    FROM ...
    WHERE ...
)
SELECT * FROM cte_name;

Setup — sample tables used throughout:
CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    salary DECIMAL(10,2),
    manager_id INTEGER
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    amount DECIMAL(10,2),
    order_date TEXT
);

INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 92000, NULL);
INSERT INTO employees VALUES (2, 'Bob', 'Engineering', 85000, 1);
INSERT INTO employees VALUES (3, 'Charlie', 'Marketing', 67000, NULL);
INSERT INTO employees VALUES (4, 'Diana', 'Marketing', 60000, 3);
INSERT INTO employees VALUES (5, 'Eve', 'HR', 55000, NULL);

INSERT INTO orders VALUES (1, 101, 500.00, '2024-01-10');
INSERT INTO orders VALUES (2, 102, 1200.00, '2024-01-15');
INSERT INTO orders VALUES (3, 101, 300.00, '2024-02-01');
INSERT INTO orders VALUES (4, 103, 800.00, '2024-02-10');
INSERT INTO orders VALUES (5, 102, 450.00, '2024-03-05');

Simple CTE — replacing a subquery:
Without CTE (hard to read):
SELECT name, salary
FROM (
    SELECT name, salary FROM employees WHERE department = 'Engineering'
) eng
WHERE salary > 88000;

With CTE (much cleaner):
WITH engineering AS (
    SELECT name, salary
    FROM employees
    WHERE department = 'Engineering'
)
SELECT name, salary
FROM engineering
WHERE salary > 88000;
-- name  | salary
-- Alice | 92000

Multiple CTEs — chaining steps:
You can define multiple CTEs in one query, separated by commas.

WITH
dept_avg AS (
    SELECT department, AVG(salary) AS avg_salary
    FROM employees
    GROUP BY department
),
above_avg AS (
    SELECT e.name, e.department, e.salary, d.avg_salary
    FROM employees e
    JOIN dept_avg d ON e.department = d.department
    WHERE e.salary > d.avg_salary
)
SELECT name, department, salary, ROUND(avg_salary, 2) AS dept_avg
FROM above_avg
ORDER BY department, salary DESC;
-- name  | department  | salary | dept_avg
-- Alice | Engineering | 92000  | 88500
-- Eve   | HR          | 55000  | 55000  (only employee in HR, equals avg)

CTE with window functions:
WITH ranked AS (
    SELECT name, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
    FROM employees
)
SELECT name, department, salary
FROM ranked
WHERE rn = 1;
-- Returns top earner per department
-- name    | department  | salary
-- Alice   | Engineering | 92000
-- Charlie | Marketing   | 67000
-- Eve     | HR          | 55000

CTE for running totals:
WITH monthly_orders AS (
    SELECT
        strftime('%Y-%m', order_date) AS month,
        SUM(amount) AS monthly_total
    FROM orders
    GROUP BY strftime('%Y-%m', order_date)
)
SELECT month, monthly_total,
       SUM(monthly_total) OVER (ORDER BY month) AS cumulative_total
FROM monthly_orders;
-- month   | monthly_total | cumulative_total
-- 2024-01 | 1700.00       | 1700.00
-- 2024-02 | 1100.00       | 2800.00
-- 2024-03 | 450.00        | 3250.00

Recursive CTE — traversing hierarchical data:
A recursive CTE references itself. It is used to traverse hierarchical or graph-like data such as org charts, file systems, and category trees.

Recursive CTE syntax:
WITH RECURSIVE cte_name AS (
    -- Base case (anchor member) — starting point
    SELECT ...

    UNION ALL

    -- Recursive case — references the CTE itself
    SELECT ...
    FROM cte_name
    JOIN ...
)
SELECT * FROM cte_name;

Org chart traversal — find all reports under a manager:
WITH RECURSIVE org_chart AS (
    -- Base case: start with top-level managers (no manager)
    SELECT emp_id, name, department, manager_id, 0 AS level
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive case: find employees who report to someone in the CTE
    SELECT e.emp_id, e.name, e.department, e.manager_id, oc.level + 1
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.emp_id
)
SELECT name, department, level,
       CASE level
           WHEN 0 THEN 'Manager'
           WHEN 1 THEN 'Direct Report'
           ELSE 'Sub-Report'
       END AS role
FROM org_chart
ORDER BY level, name;
-- name    | department  | level | role
-- Alice   | Engineering | 0     | Manager
-- Charlie | Marketing   | 0     | Manager
-- Eve     | HR          | 0     | Manager
-- Bob     | Engineering | 1     | Direct Report
-- Diana   | Marketing   | 1     | Direct Report

CTE vs subquery comparison:
Both CTEs and subqueries can solve the same problems. CTEs are preferred when:
- The same subquery is referenced more than once
- The query has multiple logical steps
- Readability and maintainability matter
- Recursive logic is needed (subqueries cannot be recursive)

Subqueries are fine for:
- Simple one-time nested queries
- Queries where the overhead of naming a CTE is unnecessary

Strengths of CTEs:
- Dramatically improve query readability and structure
- Allow reuse of the same result set within one query
- Enable recursive queries for hierarchical data
- Make debugging easier — each CTE can be tested independently
- Clean replacement for deeply nested subqueries

Weaknesses to be aware of:
- CTEs are not materialized in all databases — they may be re-evaluated each time
- Recursive CTEs must have a termination condition or they loop infinitely
- In some databases, CTEs have slightly more overhead than equivalent subqueries
- CTEs exist only for the duration of the query — not reusable across queries
""",

"examples": """
Example 1 — Simple (CTE replacing a subquery):
WITH high_earners AS (
    SELECT name, salary
    FROM employees
    WHERE salary > 70000
)
SELECT name, salary
FROM high_earners
ORDER BY salary DESC;
-- name  | salary
-- Alice | 92000
-- Bob   | 85000

Example 2 — Slightly deeper (multiple CTEs chained):
WITH
dept_stats AS (
    SELECT department,
           COUNT(*) AS headcount,
           AVG(salary) AS avg_salary,
           MAX(salary) AS max_salary
    FROM employees
    GROUP BY department
),
above_company_avg AS (
    SELECT department, headcount, avg_salary, max_salary
    FROM dept_stats
    WHERE avg_salary > (SELECT AVG(salary) FROM employees)
)
SELECT department,
       headcount,
       ROUND(avg_salary, 2) AS avg_salary,
       max_salary
FROM above_company_avg
ORDER BY avg_salary DESC;
-- department  | headcount | avg_salary | max_salary
-- Engineering | 2         | 88500.00   | 92000

Example 3 — Operation (recursive CTE for org chart):
WITH RECURSIVE org_chart AS (
    SELECT emp_id, name, manager_id, 0 AS depth
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    SELECT e.emp_id, e.name, e.manager_id, oc.depth + 1
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.emp_id
)
SELECT name,
       depth,
       REPLACE('          ', '          ', REPEAT('  ', depth)) || name AS indented
FROM org_chart
ORDER BY depth, name;
-- name    | depth
-- Alice   | 0
-- Charlie | 0
-- Eve     | 0
-- Bob     | 1
-- Diana   | 1

Example 4 — Concrete real-world comparison:
A finance team needs monthly revenue, the previous month's revenue,
and the percentage change — all in one clean query.

WITH monthly AS (
    SELECT
        strftime('%Y-%m', order_date) AS month,
        SUM(amount) AS revenue
    FROM orders
    GROUP BY strftime('%Y-%m', order_date)
),
with_lag AS (
    SELECT month, revenue,
           LAG(revenue) OVER (ORDER BY month) AS prev_revenue
    FROM monthly
)
SELECT month,
       revenue,
       prev_revenue,
       CASE
           WHEN prev_revenue IS NULL THEN 'First Month'
           ELSE ROUND(((revenue - prev_revenue) / prev_revenue) * 100, 2) || '%'
       END AS pct_change
FROM with_lag
ORDER BY month;
-- month   | revenue | prev_revenue | pct_change
-- 2024-01 | 1700.00 | NULL         | First Month
-- 2024-02 | 1100.00 | 1700.00      | -35.29%
-- 2024-03 | 450.00  | 1100.00      | -59.09%
""",

"key_points": """
- CTE stands for Common Table Expression — defined using the WITH keyword
- A CTE is a named temporary result set that exists only for the duration of the query
- CTE syntax: WITH name AS (SELECT ...) SELECT ... FROM name
- Multiple CTEs are separated by commas after the WITH keyword
- CTEs dramatically improve query readability compared to nested subqueries
- The same CTE can be referenced multiple times within the same query
- Recursive CTEs use WITH RECURSIVE and reference themselves
- Recursive CTEs require a base case and a recursive case joined with UNION ALL
- Recursive CTEs must have a termination condition to avoid infinite loops
- CTEs work well with window functions — define the window logic in one CTE, filter in another
- CTEs are not stored — they are computed fresh each time the query runs
- CTEs make debugging easier — each CTE can be tested independently
- CTE vs subquery — CTEs win on readability and reuse, subqueries win on simplicity for one-time use
""",

"misconceptions": """
- "CTEs are stored like views or tables" — CTEs are not stored. They exist only for the duration of the query. A view is stored and reusable across queries. A CTE is not.
- "CTEs always improve performance" — CTEs improve readability but not always performance. In many databases, a CTE is not materialized — it is re-evaluated each time it is referenced. An equivalent subquery may perform the same or better.
- "Recursive CTEs can loop indefinitely without causing errors" — Recursive CTEs without a proper termination condition will run until they hit a recursion limit or time out. Most databases have a default maximum recursion depth.
- "A CTE can only be used once in a query" — A CTE can be referenced multiple times within the same query. This is one of the main advantages over subqueries.
- "CTEs and subqueries cannot be combined" — CTEs can contain subqueries inside them. Subqueries can also reference CTEs. They are not mutually exclusive.
- "WITH RECURSIVE is only for trees and org charts" — Recursive CTEs are useful for any hierarchical data — file systems, category trees, bill of materials, network path traversal, and series generation.
""",

"real_world_use": """
- Financial reporting uses CTEs to compute monthly revenue, running totals, and period-over-period comparisons in clean multi-step queries
- HR systems use recursive CTEs to traverse org charts and find all reports under any manager at any depth
- E-commerce platforms use CTEs to identify top customers, segment users, and calculate lifetime value in structured queries
- Data pipelines use multiple CTEs to transform raw data through a series of cleaning and aggregation steps before loading into reports
- Analytics tools use CTEs with window functions to compute cohort retention, session attribution, and funnel analysis
- Content management systems use recursive CTEs to traverse category hierarchies and nested comment threads
""",

"next_concept_link": """
Common Table Expressions complete the SQL module by providing clean, readable structure for even the most complex queries. With all seven SQL concepts covered — from database basics to advanced CTEs — the natural next step is to move into HTML and Web Basics, starting with what HTML is and how it gives structure to every page on the web.
"""
}

    ] # end of concept list


def insert_concepts(concepts):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_resources (
            concept_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            base_content TEXT,
            examples TEXT,
            key_points TEXT,
            misconceptions TEXT,
            real_world_use TEXT,
            next_concept_link TEXT
        )
    """)

    for c in concepts:
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
            c["concept_id"],
            c["topic"],
            c["base_content"].strip(),
            c["examples"].strip(),
            c["key_points"].strip(),
            c["misconceptions"].strip(),
            c["real_world_use"].strip(),
            c["next_concept_link"].strip()
        ))

        print(f"Inserted: {c['concept_id']} — {c['topic']}")

    conn.commit()
    conn.close()
    print("\nAll SQL concepts inserted successfully into database_sql.db")


if __name__ == "__main__":
    concepts = get_concepts()
    insert_concepts(concepts)