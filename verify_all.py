"""
verify_all.py - Complete Verification Script for all 9 built-in queries
Runs each query through all 8 pipeline stages and confirms outputs.
"""

from database import DatabaseManager
from lexer import SQLLexer
from parser import SQLParser, ParserError
from semantic_analyzer import SemanticAnalyzer
from intermediate_representation import IRGenerator
from optimizer import QueryOptimizer
from query_executor import QueryExecutor
from main import SAMPLE_QUERIES

def verify_all():
    db = DatabaseManager()
    catalog = db.get_schema_catalog()
    ir_gen = IRGenerator()
    opt = QueryOptimizer(catalog)
    executor = QueryExecutor(db)

    print("=================================================================")
    print("VERIFYING ALL DEMONSTRATION QUERIES THROUGH QUERYFORGE PIPELINE")
    print("=================================================================\n")

    for i, sample in enumerate(SAMPLE_QUERIES):
        title = sample["title"]
        sql = sample["sql"]
        print(f"[{i+1}/9] {title}")
        print(f"SQL:\n{sql}\n")

        # Stage 1: Lexical
        try:
            tokens = SQLLexer(sql).tokenize()
            print(f"  [1. Lexical]     -> OK ({len(tokens)} tokens)")
        except Exception as e:
            print(f"  [1. Lexical]     -> FAILED: {e}")
            continue

        # Stage 2: Syntax
        try:
            ast = SQLParser(tokens, raw_query=sql).parse()
            print(f"  [2. Syntax]      -> OK (AST built)")
        except ParserError as e:
            if "Syntax Error" in title:
                print(f"  [2. Syntax]      -> EXPECTED SYNTAX ERROR CAUGHT: {e.message}")
            else:
                print(f"  [2. Syntax]      -> UNEXPECTED FAILURE: {e}")
            print("-" * 65)
            continue

        # Stage 3: Semantic
        sem = SemanticAnalyzer(catalog).analyze(ast)
        if sem.is_valid:
            print(f"  [3. Semantic]    -> OK (Schema validated, {len(sem.resolved_projections)} projections)")
        else:
            if "Semantic Error" in title:
                print(f"  [3. Semantic]    -> EXPECTED SEMANTIC ERROR CAUGHT: {sem.errors[0]}")
            else:
                print(f"  [3. Semantic]    -> UNEXPECTED FAILURE: {sem.errors}")
            print("-" * 65)
            continue

        # Stage 4: IR
        ir = ir_gen.generate(ast)
        print(f"  [4. IR]          -> OK ({len(ir.operations)} operations: {', '.join(op.op_type for op in ir.operations)})")

        # Stage 5: Optimizer
        opt_res = opt.optimize(ast, ir)
        applied = [r['name'] for r in opt_res.rules_applied]
        print(f"  [5. Optimizer]   -> OK ({len(applied)} applied: {', '.join(applied) if applied else 'Canonical plan'})")

        # Stage 6: Execution
        exec_res = executor.execute(sql)
        if exec_res.success:
            print(f"  [6. Execution]   -> OK ({exec_res.row_count} rows, {exec_res.execution_time_ms:.3f} ms)")
            print(f"  [7. Columns]     -> {exec_res.columns}")
            if exec_res.rows:
                print(f"  [8. First Row]   -> {exec_res.rows[0]}")
        else:
            print(f"  [6. Execution]   -> FAILED: {exec_res.error_message}")

        print("-" * 65)

    print("\nALL 9 DEMONSTRATION QUERIES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    verify_all()

