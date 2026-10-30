"""
query_executor.py - Safe Query Execution Engine for QueryForge
Executes validated SELECT queries against an in-memory SQLite database.
Enforces read-only safety via SQLite Authorizers, measures precise execution latency,
retrieves results, and extracts SQLite's physical execution plan (EXPLAIN QUERY PLAN).
"""

import sqlite3
import time
from typing import List, Tuple, Dict, Any, Optional
from database import DatabaseManager


class ExecutionResult:
    """Encapsulates the execution output, timings, column schema, and physical plan."""
    def __init__(self):
        self.success: bool = False
        self.error_message: Optional[str] = None
        self.sql_executed: str = ""
        self.execution_time_ms: float = 0.0
        self.columns: List[str] = []
        self.rows: List[Tuple[Any, ...]] = []
        self.row_count: int = 0
        self.physical_plan: List[Dict[str, Any]] = []

    def format_summary(self) -> str:
        """Returns a concise summary string."""
        if not self.success:
            return f"Execution Failed: {self.error_message}"
        return (
            f"Status: SUCCESS | Rows: {self.row_count} | "
            f"Latency: {self.execution_time_ms:.3f} ms | Columns: {len(self.columns)}"
        )


class QueryExecutor:
    """
    Executes queries with safety constraints and performance measurement.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _authorizer_callback(self, action_code: int, arg1: Any, arg2: Any, db_name: Any, trigger_name: Any) -> int:
        """
        SQLite Authorizer callback: strictly allows read/select operations
        and rejects modifications, attachments, or schema changes.
        """
        # Permitted action codes in SQLite
        # SQLITE_SELECT = 21, SQLITE_READ = 20, SQLITE_FUNCTION = 31
        permitted_codes = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION
        }

        if action_code in permitted_codes:
            return sqlite3.SQLITE_OK

        # Block everything else (INSERT, UPDATE, DELETE, ATTACH, DETACH, PRAGMA, CREATE, DROP)
        return sqlite3.SQLITE_DENY

    def execute(self, sql_query: str) -> ExecutionResult:
        result = ExecutionResult()
        clean_sql = sql_query.strip()
        result.sql_executed = clean_sql

        if not clean_sql:
            result.error_message = "Execution Error: Empty SQL query provided."
            return result

        # Ensure single statement (no multiple statements separated by semicolons)
        semicolon_count = clean_sql.count(';')
        if semicolon_count > 1 or (semicolon_count == 1 and not clean_sql.rstrip().endswith(';')):
            result.error_message = "Execution Error: Multiple statements in single query are rejected for security."
            return result

        # Ensure connection exists
        if not self.db.conn:
            result.error_message = "Execution Error: Database connection is not available."
            return result

        cursor = self.db.conn.cursor()

        try:
            # Install SQLite authorizer
            self.db.conn.set_authorizer(self._authorizer_callback)

            # 1. Fetch SQLite's Physical Execution Plan (EXPLAIN QUERY PLAN)
            try:
                # Strip trailing semicolon for EXPLAIN
                explain_query = f"EXPLAIN QUERY PLAN {clean_sql.rstrip(';')};"
                cursor.execute(explain_query)
                plan_rows = cursor.fetchall()
                # EXPLAIN QUERY PLAN format: (id, parent, notused, detail)
                for row in plan_rows:
                    result.physical_plan.append({
                        "id": row[0],
                        "parent": row[1],
                        "detail": row[3]
                    })
            except Exception as ep_err:
                # Fallback if EXPLAIN fails
                result.physical_plan.append({
                    "id": 0,
                    "parent": 0,
                    "detail": f"Note: EXPLAIN QUERY PLAN generated warning: {str(ep_err)}"
                })

            # 2. Execute Actual SELECT Query with high-precision timing
            start_time = time.perf_counter()
            cursor.execute(clean_sql)
            rows = cursor.fetchall()
            end_time = time.perf_counter()

            result.execution_time_ms = (end_time - start_time) * 1000.0
            result.rows = rows
            result.row_count = len(rows)

            if cursor.description:
                result.columns = [desc[0] for desc in cursor.description]
            else:
                result.columns = []

            result.success = True

        except sqlite3.DatabaseError as db_err:
            result.success = False
            result.error_message = f"Database Execution Error: {str(db_err)}"
        except Exception as ex:
            result.success = False
            result.error_message = f"Unexpected Execution Exception: {str(ex)}"
        finally:
            # Clear authorizer to avoid interfering with internal DB operations
            try:
                self.db.conn.set_authorizer(None)
            except Exception:
                pass

        return result


if __name__ == "__main__":
    db = DatabaseManager()
    executor = QueryExecutor(db)

    test_sql = "SELECT name, marks FROM students WHERE marks > 80 ORDER BY marks DESC LIMIT 5;"
    res = executor.execute(test_sql)
    print("Summary:", res.format_summary())
    print("Columns:", res.columns)
    print("Rows:", res.rows)
    print("Physical Plan:", res.physical_plan)

