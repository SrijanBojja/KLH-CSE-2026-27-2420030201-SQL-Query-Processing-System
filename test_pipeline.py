"""
test_pipeline.py - Comprehensive Automated Verification Suite for QueryForge
Tests all 8 compilation stages, all 9 demonstration queries, security rules,
database integrity, and headless GUI simulation.
"""

import sys
import unittest
import tkinter as tk

from database import DatabaseManager
from lexer import SQLLexer, LexerError
from parser import SQLParser, ParserError, parse_sql
from semantic_analyzer import SemanticAnalyzer
from intermediate_representation import IRGenerator
from optimizer import QueryOptimizer
from query_executor import QueryExecutor
from main import QueryForgeApp, SAMPLE_QUERIES


class TestQueryForgePipeline(unittest.TestCase):
    """Test suite verifying compilation pipeline correctness."""

    def setUp(self):
        self.db = DatabaseManager()
        self.catalog = self.db.get_schema_catalog()
        self.ir_gen = IRGenerator()
        self.optimizer = QueryOptimizer(self.catalog)
        self.executor = QueryExecutor(self.db)

    def test_database_initialization(self):
        """Verifies database tables and sample records exist."""
        tables = self.db.get_table_names()
        self.assertIn("students", tables)
        self.assertIn("courses", tables)
        self.assertIn("enrollments", tables)

        self.assertGreaterEqual(self.db.get_table_row_count("students"), 8)
        self.assertGreaterEqual(self.db.get_table_row_count("courses"), 5)
        self.assertGreaterEqual(self.db.get_table_row_count("enrollments"), 10)

    def test_query_1_basic_select(self):
        """SELECT * FROM students;"""
        sql = "SELECT * FROM students;"
        tokens = SQLLexer(sql).tokenize()
        self.assertGreater(len(tokens), 3)

        ast = SQLParser(tokens, raw_query=sql).parse()
        self.assertEqual(len(ast.select_items), 1)
        self.assertEqual(ast.select_items[0].expression, "*")
        self.assertEqual(ast.from_table.name, "students")

        sem = SemanticAnalyzer(self.catalog).analyze(ast)
        self.assertTrue(sem.is_valid)

        ir = self.ir_gen.generate(ast)
        self.assertIn("SCAN students", ir.to_text())
        self.assertIn("PROJECT *", ir.to_text())

        opt = self.optimizer.optimize(ast, ir)
        self.assertIsNotNone(opt.optimized_ir)

        res = self.executor.execute(sql)
        self.assertTrue(res.success)
        self.assertEqual(res.row_count, 10)
        self.assertIn("student_id", res.columns)

    def test_query_2_filtering(self):
        """SELECT name, marks FROM students WHERE marks > 80;"""
        sql = "SELECT name, marks FROM students WHERE marks > 80;"
        ast = parse_sql(sql)
        sem = SemanticAnalyzer(self.catalog).analyze(ast)
        self.assertTrue(sem.is_valid)

        ir = self.ir_gen.generate(ast)
        self.assertIn("FILTER (marks > 80)", ir.to_text())

        res = self.executor.execute(sql)
        self.assertTrue(res.success)
        self.assertGreater(res.row_count, 0)
        for row in res.rows:
            self.assertGreater(row[1], 80.0)

    def test_query_3_sorting_and_limit(self):
        """SELECT name, marks FROM students ORDER BY marks DESC LIMIT 5;"""
        sql = "SELECT name, marks FROM students ORDER BY marks DESC LIMIT 5;"
        ast = parse_sql(sql)
        sem = SemanticAnalyzer(self.catalog).analyze(ast)
        self.assertTrue(sem.is_valid)

        ir = self.ir_gen.generate(ast)
        self.assertIn("SORT marks DESC", ir.to_text())
        self.assertIn("LIMIT 5", ir.to_text())

        res = self.executor.execute(sql)
        self.assertTrue(res.success)
        self.assertEqual(res.row_count, 5)
        # Check sorted descending
        marks = [r[1] for r in res.rows]
        self.assertEqual(marks, sorted(marks, reverse=True))

    def test_query_4_aggregation(self):
        """SELECT department, AVG(marks) AS average_marks FROM students GROUP BY department;"""
        sql = "SELECT department, AVG(marks) AS average_marks FROM students GROUP BY department;"
        ast = parse_sql(sql)
        sem = SemanticAnalyzer(self.catalog).analyze(ast)
        self.assertTrue(sem.is_valid)

        ir = self.ir_gen.generate(ast)
        self.assertIn("GROUP_BY department", ir.to_text())
        self.assertIn("AGGREGATE AVG(marks)", ir.to_text())

        res = self.executor.execute(sql)
        self.assertTrue(res.success)
        self.assertGreater(res.row_count, 0)
        self.assertIn("department", res.columns)

    def test_query_5_join(self):
        """Multi-table join across students, enrollments, courses."""
        sql = (
            "SELECT s.name, c.course_name, e.grade "
            "FROM students s "
            "INNER JOIN enrollments e ON s.student_id = e.student_id "
            "INNER JOIN courses c ON e.course_id = c.course_id;"
        )
        ast = parse_sql(sql)
        sem = SemanticAnalyzer(self.catalog).analyze(ast)
        self.assertTrue(sem.is_valid)
        self.assertEqual(len(sem.resolved_projections), 3)

        ir = self.ir_gen.generate(ast)
        self.assertIn("JOIN enrollments AS e", ir.to_text())
        self.assertIn("JOIN courses AS c", ir.to_text())

        res = self.executor.execute(sql)
        self.assertTrue(res.success)
        self.assertGreater(res.row_count, 0)
        self.assertEqual(len(res.columns), 3)

    def test_query_6_semantic_error(self):
        """SELECT unknown_column FROM students;"""
        sql = "SELECT unknown_column FROM students;"
        ast = parse_sql(sql)
        sem = SemanticAnalyzer(self.catalog).analyze(ast)
        self.assertFalse(sem.is_valid)
        self.assertTrue(any("unknown_column" in err for err in sem.errors))

    def test_query_7_syntax_error(self):
        """SELECT name marks FROM students WHERE;"""
        sql = "SELECT name marks FROM students WHERE;"
        tokens = SQLLexer(sql).tokenize()
        with self.assertRaises(ParserError):
            SQLParser(tokens, raw_query=sql).parse()

    def test_query_8_predicate_pushdown(self):
        """Join query with WHERE on base table demonstrating Predicate Pushdown."""
        sql = (
            "SELECT s.name, c.course_name "
            "FROM students s "
            "INNER JOIN enrollments e ON s.student_id = e.student_id "
            "INNER JOIN courses c ON e.course_id = c.course_id "
            "WHERE s.marks > 85;"
        )
        ast = parse_sql(sql)
        ir = self.ir_gen.generate(ast)
        opt = self.optimizer.optimize(ast, ir)

        applied_names = [r["name"] for r in opt.rules_applied]
        self.assertIn("Predicate Pushdown", applied_names)
        self.assertIn("Projection Pruning", applied_names)

        # In optimized plan, FILTER must appear BEFORE the JOINs
        opt_text = opt.optimized_ir.to_text()
        filter_pos = opt_text.find("FILTER")
        join_pos = opt_text.find("JOIN")
        self.assertLess(filter_pos, join_pos, "Predicate Pushdown failed to position FILTER before JOIN!")

    def test_query_9_constant_folding(self):
        """Constant expression 1 = 1 folded."""
        sql = "SELECT name, department, marks FROM students WHERE 1 = 1 AND marks >= 90;"
        ast = parse_sql(sql)
        ir = self.ir_gen.generate(ast)
        opt = self.optimizer.optimize(ast, ir)

        applied_names = [r["name"] for r in opt.rules_applied]
        self.assertIn("Constant Simplification / Folding", applied_names)

    def test_security_authorizer(self):
        """Verifies malicious/mutation queries are blocked."""
        malicious_queries = [
            "DROP TABLE students;",
            "INSERT INTO students VALUES (999, 'Hacker', 'CS', 1, 100, 'Nowhere');",
            "UPDATE students SET marks = 100;",
            "DELETE FROM students;"
        ]
        for q in malicious_queries:
            res = self.executor.execute(q)
            self.assertFalse(res.success, f"Security vulnerability: query '{q}' was executed!")
            self.assertIn("not authorized", res.error_message.lower())

    def test_gui_app_simulation(self):
        """Simulates GUI interaction and verifies widget bindings."""
        root = tk.Tk()
        root.withdraw()  # Hide window during test
        app = QueryForgeApp(root)

        # 1. Test sample query loading
        for i, item in enumerate(SAMPLE_QUERIES):
            app.sample_combo.current(i)
            app._on_sample_selected()
            editor_content = app.sql_editor.get("1.0", tk.END).strip()
            self.assertEqual(editor_content, item["sql"].strip())

        # 2. Test full pipeline processing on Query 2
        app.sample_combo.current(1)  # Query 2
        app._on_sample_selected()
        app.process_all_stages()

        self.assertGreater(len(app.current_tokens), 0)
        self.assertIsNotNone(app.current_ast)
        self.assertTrue(app.current_semantic_res.is_valid)
        self.assertIsNotNone(app.current_ir)
        self.assertIsNotNone(app.current_opt_res)
        self.assertTrue(app.current_exec_res.success)
        self.assertGreater(app.current_exec_res.row_count, 0)

        # 3. Test Step-by-Step execution mode
        app.sample_combo.current(0)  # Query 1
        app._on_sample_selected()
        app.start_step_mode()
        self.assertTrue(app.step_mode_active)

        # Step through all phases
        for _ in range(7):
            if app.step_mode_active:
                app.execute_next_step()

        self.assertFalse(app.step_mode_active, "Step mode should terminate after results stage.")

        # 4. Test Error Handling in GUI (Query 6 - Semantic Error & Query 7 - Syntax Error)
        # Monkeypatch messagebox.showerror to prevent modal blocking during automated testing
        error_dialog_messages = []
        original_showerror = tk.messagebox.showerror
        tk.messagebox.showerror = lambda title, msg: error_dialog_messages.append((title, msg))

        try:
            # Query 6 (Semantic Error)
            app.sample_combo.current(5)
            app._on_sample_selected()
            app.process_all_stages()
            self.assertEqual(app.stage_badges["SEMANTIC"].cget("text"), "4. SEMANTIC")
            self.assertEqual(app.stage_badges["SEMANTIC"].cget("bg"), "#f38ba8")

            # Query 7 (Syntax Error)
            app.sample_combo.current(6)
            app._on_sample_selected()
            app.process_all_stages()
            self.assertEqual(app.stage_badges["SYNTAX"].cget("text"), "3. SYNTAX")
            self.assertEqual(app.stage_badges["SYNTAX"].cget("bg"), "#f38ba8")

            self.assertGreaterEqual(len(error_dialog_messages), 2)
        finally:
            tk.messagebox.showerror = original_showerror

        # 5. Clean up root
        root.destroy()


if __name__ == "__main__":
    unittest.main()
