# QueryForge – SQL Query Processing System
**Compiler Design Project | Relational Query Compilation & Execution Pipeline**

---

## 1. Project Title
**QueryForge – Educational SQL Query Processing & Relational Compiler System**

---

## 2. Abstract
QueryForge is an interactive desktop compiler design application that demystifies how a relational database management system (RDBMS) processes, transforms, optimizes, and executes Structured Query Language (SQL) queries. Instead of treating database queries as a "black box," QueryForge demonstrates the compilation journey through eight discrete, observable phases: Lexical Analysis, Syntax Analysis, Semantic Analysis, Intermediate Representation (IR), Query Optimization, Query Execution, and Tabular Result Generation. Built using Python 3, Tkinter/ttk, and an in-memory SQLite virtual catalog, QueryForge exposes internal data structures such as token streams, Abstract Syntax Trees (AST), relational algebra operator plans, and rule-based logical optimizations (Predicate Pushdown, Projection Pruning, and Constant Folding).

---

## 3. Problem Statement
In conventional undergraduate Computer Science education, Compiler Design and Database Management Systems are taught as separate theoretical domains. Students learn about lexers, parsers, and ASTs for imperative languages (like C or Java), while SQL is often taught strictly as a declarative data manipulation tool without visual insight into how database query compilers operate. Furthermore, standard database command-line interfaces provide only final outputs or cryptic physical execution logs, hiding intermediate compilation states.

There is a distinct need for a visual, transparent compiler tool that:
1. Breaks down an SQL query into formal compiler stages.
2. Demonstrates lexical tokenization, grammar parsing, and schema validation.
3. Translates declarative queries into Relational Algebra Intermediate Representation (IR).
4. Illustrates how logical query optimizers reorder operations for performance.
5. Provides safe execution against live relational tables with step-by-step educational controls.

---

## 4. Objectives
- **End-to-End Processing Pipeline:** Implement a fully working compiler pipeline from raw text input to executed table results.
- **Custom Lexical & Syntactic Analyzers:** Build a custom tokenizer and recursive descent parser for a rigorous subset of SQL SELECT statements.
- **Explicit Schema Catalog Validation:** Implement a semantic analyzer that checks table existence, column validity, table aliases, and ambiguous references against an active database catalog.
- **Relational Algebra Intermediate Representation (IR):** Emit a canonical linear operator sequence (`SCAN`, `FILTER`, `JOIN`, `GROUP_BY`, `AGGREGATE`, `PROJECT`, `SORT`, `LIMIT`) with mathematical notation.
- **Rule-Based Logical Optimization:** Demonstrate concrete compiler optimizations including Predicate Pushdown (filtering before joins), Projection Pruning (early elimination of unreferenced attributes), and Constant Folding (simplifying tautologies).
- **Execution & Security Authorizer:** Safely execute validated queries against an in-memory database using SQLite with authorizer callbacks preventing unauthorized writes or mutations.
- **Professional Graphical Interface:** Provide a modern dark-theme Tkinter desktop GUI with interactive pipeline indicators, tabbed intermediate stage inspectability, a database explorer, and step-by-step execution mode.

---

## 5. Technologies Used
- **Programming Language:** Python 3 (Tested on Python 3.13)
- **GUI Toolkit:** Python built-in `tkinter` and `ttk` (Themed Tkinter widgets)
- **Database Engine:** Built-in `sqlite3` module (running `:memory:` database with custom authorizers)
- **Architecture Pattern:** Modular Pipeline Architecture (separation of concerns across Lexer, Parser, Semantic Analyzer, IR Generator, Optimizer, and Executor)
- **Operating System:** Windows 11 (fully cross-platform across Windows, macOS, Linux)
- **Dependencies:** 100% Python Standard Library — zero external pip packages or internet access required.

---

## 6. System Architecture

The architecture of QueryForge is organized into decoupled compiler modules:

```
+-------------------------------------------------------------------------+
|                              QueryForge GUI                             |
|        (Tkinter / ttk Dark Theme, Pipeline Indicator, Step Controller)  |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-----------------------+     [Source Text]     +-------------------------+
|   1. Lexical Analyzer | --------------------> | Token Stream            |
|       (lexer.py)      |                       | (Type, Lexeme, Line,Col)|
+-----------------------+                       +-------------------------+
                                                             |
                                                             v
+-----------------------+     [Token Stream]    +-------------------------+
|   2. Syntax Analyzer  | --------------------> | Abstract Syntax Tree    |
|      (parser.py)      |                       | (ParsedQuery AST)       |
+-----------------------+                       +-------------------------+
                                                             |
                                                             v
+-----------------------+     [AST + Schema]    +-------------------------+
| 3. Semantic Analyzer  | --------------------> | Validated AST           |
| (semantic_analyzer.py)|                       | + Resolved Projections  |
+-----------------------+                       +-------------------------+
                                                             |
                                                             v
+-----------------------+     [Validated AST]   +-------------------------+
|  4. IR Generator      | --------------------> | Logical Relational Plan |
| (intermediate_rep.py) |                       | (SCAN, FILTER, JOIN, ..)|
+-----------------------+                       +-------------------------+
                                                             |
                                                             v
+-----------------------+     [Logical Plan]    +-------------------------+
|   5. Query Optimizer  | --------------------> | Optimized Relational    |
|     (optimizer.py)    |                       | Plan + Rule Audit Log   |
+-----------------------+                       +-------------------------+
                                                             |
                                                             v
+-----------------------+     [Safe Query]      +-------------------------+
|   6. Query Executor   | --------------------> | Result Records, Latency,|
|  (query_executor.py)  |                       | Physical SQLite Plan    |
+-----------------------+                       +-------------------------+
                                                             |
                                                             v
+-------------------------------------------------------------------------+
|                      7. Output Generation & Results                     |
|           (Treeview Results Table, Column Headers, Execution Metrics)    |
+-------------------------------------------------------------------------+
```

---

## 7. Query Processing Pipeline

The compilation and execution pipeline transitions through eight distinct states:

```
[1. INPUT] -> [2. LEXICAL] -> [3. SYNTAX] -> [4. SEMANTIC] -> [5. IR] -> [6. OPTIMIZE] -> [7. EXECUTE] -> [8. OUTPUT]
```

1. **INPUT:** Captures user SQL text from the editor.
2. **LEXICAL:** Converts raw characters into discrete tokens.
3. **SYNTAX:** Verifies SQL grammar and constructs an Abstract Syntax Tree (AST).
4. **SEMANTIC:** Validates tables and column references against the active schema catalog.
5. **IR:** Converts declarative AST into an ordered sequence of Relational Algebra operations.
6. **OPTIMIZE:** Applies logical transformation rules (pushing filters, pruning columns).
7. **EXECUTE:** Runs validated queries against SQLite with a read-only authorizer.
8. **OUTPUT:** Renders structured results in a formatted table with execution latency.

---

## 8. Explanation of Lexical Analysis

### Purpose
The Lexical Analyzer (Scanner or Tokenizer) scans the source SQL query character by character, strips redundant whitespace and comments, and groups character sequences into meaningful semantic units called **Tokens**.

### Token Categories Recognized:
- **`KEYWORD`:** Reserved SQL grammar terms (`SELECT`, `FROM`, `WHERE`, `AND`, `OR`, `JOIN`, `INNER`, `ON`, `GROUP`, `BY`, `ORDER`, `ASC`, `DESC`, `LIMIT`, `DISTINCT`).
- **`IDENTIFIER`:** User-defined names referencing database entities like tables (`students`), columns (`marks`), or aliases (`s`).
- **`NUMBER`:** Integer or decimal numeric literals (`80`, `92.5`).
- **`STRING`:** Character literals enclosed in single or double quotes (`'Bangalore'`, `'Computer Science'`).
- **`OPERATOR`:** Relational comparison and arithmetic symbols (`=`, `!=`, `<>`, `<`, `>`, `<=`, `>=`, `+`, `-`).
- **`COMMA` / `PERIOD` / `SEMICOLON`:** Delimiters separating projection lists, qualifying column names (`s.marks`), or terminating statements.
- **`LPAREN` / `RPAREN`:** Parentheses for grouping expressions or enclosing function arguments.
- **`ASTERISK`:** Wildcard symbol representing all columns (`*`).

### Lexical Output Format:
Each token records its stream index, category, lexeme, and source coordinates:
```
Position | Token Type | Lexeme   | Coordinates
1        | KEYWORD    | SELECT   | Line 1 : Col 1
2        | IDENTIFIER | name     | Line 1 : Col 8
3        | COMMA      | ,        | Line 1 : Col 12
4        | IDENTIFIER | marks    | Line 1 : Col 14
5        | KEYWORD    | FROM     | Line 2 : Col 1
6        | IDENTIFIER | students | Line 2 : Col 6
7        | KEYWORD    | WHERE    | Line 3 : Col 1
8        | IDENTIFIER | marks    | Line 3 : Col 7
9        | OPERATOR   | >        | Line 3 : Col 13
10       | NUMBER     | 80       | Line 3 : Col 15
11       | SEMICOLON  | ;        | Line 3 : Col 17
```

---

## 9. Explanation of Syntax Analysis

### Purpose
The Syntax Analyzer (Parser) takes the linear token stream and verifies that it adheres to the formal grammar of the supported SQL dialect. It uses a **Recursive Descent** parser ($LL(k)$ predictive parsing technique).

### Grammar Specification (EBNF):
```
Query           ::= SELECT [DISTINCT] SelectList FROM TableRef [JoinClause]* [WhereClause]? [GroupByClause]? [OrderByClause]? [LimitClause]? [';']?
SelectList      ::= '*' | SelectItem (',' SelectItem)*
SelectItem      ::= (AggregateCall | ColumnRef) [('AS')? Identifier]?
AggregateCall   ::= ('COUNT' | 'SUM' | 'AVG' | 'MIN' | 'MAX') '(' ('*' | ColumnRef) ')'
TableRef        ::= Identifier [('AS')? Identifier]?
JoinClause      ::= ('INNER')? 'JOIN' TableRef 'ON' Condition
WhereClause     ::= 'WHERE' Condition
Condition       ::= OrExpr
OrExpr          ::= AndExpr ('OR' AndExpr)*
AndExpr         ::= CompExpr ('AND' CompExpr)*
CompExpr        ::= '(' Condition ')' | ColumnRef ('=' | '!=' | '<>' | '<' | '<=' | '>' | '>=') Value | ColumnRef 'IS' ('NOT')? 'NULL'
GroupByClause   ::= 'GROUP' 'BY' ColumnRef (',' ColumnRef)*
OrderByClause   ::= 'ORDER' 'BY' OrderItem (',' OrderItem)*
OrderItem       ::= ColumnRef ('ASC' | 'DESC')?
LimitClause     ::= 'LIMIT' Number
```

### AST Representation:
When valid, the parser builds a hierarchical `ParsedQuery` node. For example, for:
`SELECT name, marks FROM students WHERE marks > 80 ORDER BY marks DESC LIMIT 5;`

```
Parsed Query Structure:
  |-- SELECT:
  |   |-- name
  |   \-- marks
  |-- FROM: students
  |-- WHERE: (marks > 80)
  |-- ORDER BY: marks DESC
  \-- LIMIT: 5
```

If syntax errors occur (such as missing commas, dangling clauses, or invalid keywords), the parser halts execution, pinpoints the offending token position, and displays a precise error message.

---

## 10. Explanation of Semantic Analysis

### Purpose
While the parser validates grammatical structure, the **Semantic Analyzer** ensures logical correctness against the database catalog. A query can be syntactically valid yet semantically meaningless (e.g., querying columns or tables that do not exist).

### Semantic Verification Rules:
1. **Table Existence:** Verifies that relations named in `FROM` and `JOIN` clauses exist in the database catalog.
2. **Column Existence:** Ensures all referenced columns exist in their respective tables.
3. **Ambiguity Resolution:** If an unqualified column name appears in a multi-table query and exists in more than one joined table, an ambiguity error is raised.
4. **Alias Binding:** Validates table aliases (`students s`) and verifies that qualified column references (`s.name`) match declared aliases.
5. **Aggregate Rules:** Validates aggregate function arguments (e.g., preventing `SUM(*)` while allowing `COUNT(*)`).

### Example Semantic Error Handling:
- Query: `SELECT unknown_column FROM students;`
  - Output: `Semantic Error: Column 'unknown_column' does not exist in referenced table(s): 'students'.`
- Query: `SELECT name FROM missing_table;`
  - Output: `Semantic Error: Table 'missing_table' does not exist in database schema.`

---

## 11. Intermediate Representation (IR)

### Purpose
The Intermediate Representation (IR) bridges high-level declarative SQL with low-level execution logic. QueryForge translates the validated AST into a linear sequence of relational algebra operators:

| Operator | Relational Algebra Symbol | Operation Name | Description |
| :--- | :--- | :--- | :--- |
| **`SCAN`** | $R$ | Relation Scan | Performs sequential or index access over base relation. |
| **`FILTER`** | $\sigma$ (Sigma) | Selection | Eliminates non-qualifying tuples matching condition predicate. |
| **`JOIN`** | $\bowtie$ (Bowtie) | Theta-Join | Computes relational product matching join condition predicate. |
| **`GROUP_BY`** | $\gamma$ (Gamma) | Grouping | Partitions tuples into equivalence classes by grouping keys. |
| **`AGGREGATE`** | $\gamma$ (Gamma) | Aggregation | Evaluates summary functions (`AVG`, `COUNT`, `SUM`, `MIN`, `MAX`). |
| **`PROJECT`** | $\pi$ (Pi) | Projection | Selects specified attributes and discards unneeded columns. |
| **`SORT`** | $\tau$ (Tau) | Ordering | Sorts output tuples in ascending (`ASC`) or descending (`DESC`) order. |
| **`LIMIT`** | $\lambda$ (Lambda) | Cardinality Restriction | Restricts the number of output tuples produced. |

### Generated IR Example:
```
OP1: SCAN students
OP2: FILTER (marks > 80)
OP3: PROJECT name, marks
OP4: SORT marks DESC
OP5: LIMIT 5
```

---

## 12. Query Optimization Techniques

QueryForge implements an educational, rule-based logical query optimizer:

### A. Projection Pruning
- **Concept:** Identifies all attributes required by downstream projections, filters, join conditions, and sorting clauses. Any unreferenced table columns are marked as pruned early during relation scanning.
- **Benefit:** Minimizes memory bandwidth, cache usage, and row serialization overhead.
- **Example:** For `SELECT name, marks FROM students`, the optimizer identifies that `student_id`, `department`, `semester`, and `city` are not needed and prunes them from the physical read.

### B. Predicate Pushdown
- **Concept:** Moves filter (`FILTER / σ`) operations as close to the leaf `SCAN` operations as possible, executing selections before expensive multi-table joins.
- **Benefit:** Reduces intermediate join cardinality.
- **Example:**
  - *Original Plan:* `SCAN students -> JOIN enrollments -> JOIN courses -> FILTER (s.marks > 85)`
  - *Optimized Plan:* `SCAN students -> FILTER (s.marks > 85) -> JOIN enrollments -> JOIN courses`
  - *Impact:* Tuples with `marks <= 85` are filtered immediately, avoiding unnecessary join lookups on the `enrollments` table.

### C. Constant Simplification / Folding
- **Concept:** Evaluates constant boolean tautologies or expressions at compile time.
- **Example:** `WHERE 1 = 1 AND marks >= 90` is simplified to `WHERE marks >= 90`, eliminating redundant per-row comparison evaluations.

### D. Logical Plan Simplification
- **Concept:** Detects redundant operations (such as `LIMIT <= 0`) and produces an immediate empty relation plan without executing costly table scans.

---

## 13. Query Execution

### Engine & Authorizer Constraints:
- Executed against an in-memory SQLite database (`:memory:`) populated at startup.
- **Read-Only SQLite Authorizer:** Uses `sqlite3.set_authorizer` to permit only `SQLITE_SELECT`, `SQLITE_READ`, and `SQLITE_FUNCTION` codes.
- **Mutation Rejection:** Any attempted data modifications (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ATTACH`, `PRAGMA`) are immediately denied by the database authorizer with `not authorized`.
- **Latency Measurement:** Queries are timed using high-precision counters (`time.perf_counter()`) displaying runtime in milliseconds.
- **Physical Query Planner (`EXPLAIN QUERY PLAN`):** SQLite's internal physical execution tree (e.g., `SCAN students`, `USE TEMP B-TREE FOR ORDER BY`) is retrieved and displayed alongside the compiler's logical IR plan.

---

## 14. Sample Queries and Expected Results

| # | Demonstration Query | Compilation Highlights | Expected Output |
| :--- | :--- | :--- | :--- |
| **1** | `SELECT * FROM students;` | Wildcard expansion; Projection pruning evaluated as not applicable. | 10 student records with all 6 columns. |
| **2** | `SELECT name, marks FROM students WHERE marks > 80;` | Selection predicate filter; Prunes 4 unused columns. | 6 records with marks above 80. |
| **3** | `SELECT name, marks FROM students ORDER BY marks DESC LIMIT 5;` | IR includes `SORT` and `LIMIT`; Demonstrates SQLite temp B-tree. | Top 5 students sorted by marks descending. |
| **4** | `SELECT department, AVG(marks) AS average_marks FROM students GROUP BY department;` | Aggregation & Grouping operator $\gamma$; Computes partitioned averages. | 4 departments with computed average marks. |
| **5** | `SELECT s.name, c.course_name, e.grade FROM students s INNER JOIN enrollments e ON s.student_id = e.student_id INNER JOIN courses c ON e.course_id = c.course_id;` | Multi-way relational join ($\bowtie$); Alias resolution and column bindings. | 15 enrollment records joining student and course names. |
| **6** | `SELECT unknown_column FROM students;` | Syntax succeeds; Semantic Analyzer detects missing column and halts pipeline. | Red error indicator; pipeline halts before IR/execution. |
| **7** | `SELECT name marks FROM students WHERE;` | Lexer succeeds; Syntax Analyzer detects missing comma/dangling WHERE. | Red error indicator; displays token line and column. |
| **8** | `SELECT s.name, c.course_name FROM students s INNER JOIN enrollments e ON s.student_id = e.student_id INNER JOIN courses c ON e.course_id = c.course_id WHERE s.marks > 85;` | **Predicate Pushdown:** Moves `s.marks > 85` before the joins. | 7 join matches with students having marks > 85. |
| **9** | `SELECT name, department, marks FROM students WHERE 1 = 1 AND marks >= 90;` | **Constant Folding:** Simplifies `1 = 1` to `TRUE`. | 3 student records with marks >= 90. |

---

## 15. Instructions to Execute the Project on Windows

### Prerequisites:
- Windows 10 or Windows 11
- Python 3.8 or higher (Standard Python from python.org or Microsoft Store)
- Tkinter included by default with standard Python Windows installations.

### Step 1: Open Terminal in Project Directory
Open PowerShell or Command Prompt in the project folder:
```powershell
cd "c:\Users\srija\Desktop\New folder\3 - 1\CD\Project(1)"
```

### Step 2: Run Automated Test Suite
Verify that all compiler modules and test cases pass:
```powershell
python test_pipeline.py
```
*Expected Output:* `Ran 12 tests in 0.700s ... OK`

### Step 3: Launch QueryForge GUI
```powershell
python main.py
```

The application window will open with the dark theme, sample queries dropdown, and interactive pipeline.

---

## 16. Limitations
1. **Query Scope:** QueryForge focuses on declarative query compilation for the relational `SELECT` subset. Write queries (`INSERT`, `UPDATE`, `DELETE`) and DDL (`CREATE`, `DROP`) are intentionally blocked for safety and educational scope.
2. **Subqueries & CTEs:** Nested `SELECT` subqueries (e.g., `WHERE x IN (SELECT ...)`) and Common Table Expressions (`WITH ...`) are not currently parsed by this recursive descent grammar.
3. **Outer Joins:** Supports `INNER JOIN` and standard `JOIN`; full outer joins (`FULL OUTER JOIN`) are outside the educational subset.
4. **Single In-Memory Catalog:** Operates on an in-memory SQLite catalog with pre-loaded `students`, `courses`, and `enrollments` tables. External database file attachments are restricted by design.

---

## 17. Conclusion
QueryForge bridges the educational divide between theoretical compiler design and practical database systems. By exposing every intermediate transformation—from raw text tokenization to recursive descent AST generation, schema-catalog semantic verification, relational algebra IR generation, logical query optimization, and sandboxed execution—it provides computer science students and instructors with a clear, interactive window into the internal mechanics of database query engines.

