"""
database.py - In-memory SQLite Database Manager for QueryForge
Provides schema definition, sample data population, catalog inspection,
and safe reset functionality.
"""

import sqlite3
from typing import Dict, List, Tuple, Any


class DatabaseManager:
    """Manages the in-memory SQLite database and provides schema introspection."""

    def __init__(self):
        self.conn: sqlite3.Connection | None = None
        self.initialize_database()

    def initialize_database(self) -> None:
        """Create a fresh in-memory database with tables and sample records."""
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._create_tables()
        self._populate_sample_data()

    def _create_tables(self) -> None:
        """Create sample tables: students, courses, and enrollments."""
        cursor = self.conn.cursor()

        # Table 1: students
        cursor.execute("""
            CREATE TABLE students (
                student_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL,
                marks REAL NOT NULL,
                city TEXT NOT NULL
            );
        """)

        # Table 2: courses
        cursor.execute("""
            CREATE TABLE courses (
                course_id INTEGER PRIMARY KEY,
                course_name TEXT NOT NULL,
                department TEXT NOT NULL,
                credits INTEGER NOT NULL
            );
        """)

        # Table 3: enrollments
        cursor.execute("""
            CREATE TABLE enrollments (
                enrollment_id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                grade TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (course_id) REFERENCES courses(course_id)
            );
        """)

        self.conn.commit()

    def _populate_sample_data(self) -> None:
        """Populate realistic sample records."""
        cursor = self.conn.cursor()

        students_data = [
            (101, 'Aarav Sharma', 'Computer Science', 6, 88.5, 'Bangalore'),
            (102, 'Diya Patel', 'Computer Science', 6, 92.0, 'Mumbai'),
            (103, 'Rohan Verma', 'Information Tech', 4, 76.5, 'Delhi'),
            (104, 'Sneha Reddy', 'Electronics', 6, 84.0, 'Hyderabad'),
            (105, 'Vikram Malhotra', 'Mechanical', 4, 69.5, 'Pune'),
            (106, 'Ananya Iyer', 'Computer Science', 4, 95.0, 'Chennai'),
            (107, 'Kabir Sen', 'Information Tech', 6, 81.0, 'Kolkata'),
            (108, 'Meera Nair', 'Electronics', 4, 73.0, 'Kochi'),
            (109, 'Aditya Joshi', 'Mechanical', 6, 86.5, 'Ahmedabad'),
            (110, 'Pooja Hegde', 'Computer Science', 6, 91.5, 'Bangalore'),
        ]
        cursor.executemany(
            "INSERT INTO students VALUES (?, ?, ?, ?, ?, ?);", students_data
        )

        courses_data = [
            (201, 'Compiler Design', 'Computer Science', 4),
            (202, 'Database Management', 'Computer Science', 4),
            (203, 'Computer Networks', 'Information Tech', 3),
            (204, 'VLSI Design', 'Electronics', 4),
            (205, 'Thermodynamics', 'Mechanical', 3),
            (206, 'Artificial Intelligence', 'Computer Science', 4),
        ]
        cursor.executemany(
            "INSERT INTO courses VALUES (?, ?, ?, ?);", courses_data
        )

        enrollments_data = [
            (1, 101, 201, 'A'),
            (2, 101, 202, 'A+'),
            (3, 102, 201, 'A+'),
            (4, 102, 206, 'A+'),
            (5, 103, 202, 'B+'),
            (6, 103, 203, 'A'),
            (7, 104, 204, 'A'),
            (8, 105, 205, 'B'),
            (9, 106, 201, 'A+'),
            (10, 106, 206, 'A+'),
            (11, 107, 203, 'A'),
            (12, 108, 204, 'B+'),
            (13, 109, 205, 'A'),
            (14, 110, 201, 'A'),
            (15, 110, 202, 'A'),
        ]
        cursor.executemany(
            "INSERT INTO enrollments VALUES (?, ?, ?, ?);", enrollments_data
        )

        self.conn.commit()

    def get_schema_catalog(self) -> Dict[str, Dict[str, str]]:
        """
        Returns catalog mapping:
        { table_name: { column_name: data_type, ... }, ... }
        """
        catalog = {}
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            # pragma table_info columns: cid, name, type, notnull, dflt_value, pk
            cols = {row[1]: (row[2] if row[2] else 'ANY') for row in cursor.fetchall()}
            catalog[table] = cols

        return catalog

    def get_table_names(self) -> List[str]:
        """Returns list of user tables in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [row[0] for row in cursor.fetchall()]

    def get_table_columns_info(self, table_name: str) -> List[Tuple[str, str, bool, bool]]:
        """
        Returns detailed column info for a table:
        [(col_name, type, not_null, is_pk), ...]
        """
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        # cid, name, type, notnull, dflt_value, pk
        return [(row[1], row[2], bool(row[3]), bool(row[5])) for row in cursor.fetchall()]

    def get_table_data(self, table_name: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
        """Returns (column_names, rows) for a table."""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name};")
        col_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return col_names, rows

    def get_table_row_count(self, table_name: str) -> int:
        """Returns row count for a table."""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        return cursor.fetchone()[0]


if __name__ == "__main__":
    db = DatabaseManager()
    print("Catalog:", db.get_schema_catalog())
    for t in db.get_table_names():
        cols, rows = db.get_table_data(t)
        print(f"Table {t} ({len(rows)} rows): {cols}")

