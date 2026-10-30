"""
semantic_analyzer.py - Semantic Analyzer for QueryForge SQL System
Validates parsed SQL queries against the active database schema catalog.
Detects nonexistent tables, missing columns, ambiguous column references,
invalid aliases, and type or aggregate inconsistencies.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from parser import ParsedQuery, ColumnRef, AggregateCall, SelectItem, BinaryOp, UnaryOp, Literal


class SemanticResult:
    """Encapsulates the result of semantic analysis."""
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # alias or table_name -> real table name
        self.table_bindings: Dict[str, str] = {}
        # List of dicts describing resolved projected columns
        self.resolved_projections: List[Dict[str, Any]] = []
        # Schema snapshot consulted during validation
        self.schema_snapshot: Dict[str, Dict[str, str]] = {}

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(f"Semantic Error: {message}")

    def add_warning(self, message: str) -> None:
        self.warnings.append(f"Semantic Warning: {message}")

    def format_report(self) -> str:
        """Generates a comprehensive report for the GUI."""
        lines = []
        status_str = "VALID (Passed all schema checks)" if self.is_valid else f"FAILED ({len(self.errors)} error(s))"
        lines.append(f"Status: {status_str}")
        lines.append("-" * 55)

        if self.errors:
            lines.append("ERRORS ENCOUNTERED:")
            for err in self.errors:
                lines.append(f"  * {err}")
            lines.append("")

        if self.warnings:
            lines.append("WARNINGS:")
            for w in self.warnings:
                lines.append(f"  ! {w}")
            lines.append("")

        lines.append("RESOLVED TABLE BINDINGS:")
        for alias, table in self.table_bindings.items():
            if alias == table:
                lines.append(f"  * Table '{table}'")
            else:
                lines.append(f"  * Alias '{alias}' -> Table '{table}'")

        lines.append("\nRESOLVED COLUMN PROJECTIONS:")
        for p in self.resolved_projections:
            col_desc = p.get('name', '')
            t_orig = p.get('source_table', 'Computed/Aggregate')
            dt = p.get('data_type', 'UNKNOWN')
            alias = p.get('alias')
            alias_str = f" AS '{alias}'" if alias else ""
            lines.append(f"  * {col_desc}{alias_str}  [Source: {t_orig}, Type: {dt}]")

        lines.append("\nSCHEMA CONTEXT CONSULTED:")
        for t, cols in self.schema_snapshot.items():
            col_list = ", ".join(f"{c}: {dtype}" for c, dtype in cols.items())
            lines.append(f"  * {t}: ({col_list})")

        return "\n".join(lines)


class SemanticAnalyzer:
    """
    Performs semantic verification on a ParsedQuery AST against a schema catalog.
    """

    def __init__(self, catalog: Dict[str, Dict[str, str]]):
        """
        catalog: Dict mapping table_name -> {col_name: data_type}
        """
        self.catalog = catalog

    def analyze(self, query: ParsedQuery) -> SemanticResult:
        result = SemanticResult()
        result.schema_snapshot = self.catalog

        # Step 1: Validate FROM table and bind aliases
        if not query.from_table:
            result.add_error("Missing FROM table reference.")
            return result

        from_tbl = query.from_table.name
        if from_tbl not in self.catalog:
            result.add_error(f"Table '{from_tbl}' does not exist in database schema.")
            return result

        # Register primary table
        result.table_bindings[from_tbl] = from_tbl
        if query.from_table.alias:
            alias = query.from_table.alias
            if alias in result.table_bindings:
                result.add_error(f"Duplicate table alias '{alias}'.")
            result.table_bindings[alias] = from_tbl

        # Step 2: Validate JOIN tables and aliases
        for join in query.joins:
            j_table = join.table.name
            if j_table not in self.catalog:
                result.add_error(f"Joined table '{j_table}' does not exist in database schema.")
                continue

            result.table_bindings[j_table] = j_table
            if join.table.alias:
                j_alias = join.table.alias
                if j_alias in result.table_bindings and j_alias != j_table:
                    result.add_error(f"Duplicate table alias '{j_alias}'.")
                result.table_bindings[j_alias] = j_table

        # If any base table checks failed, abort further column resolution
        if not result.is_valid:
            return result

        # Step 3: Validate JOIN ON conditions
        for join in query.joins:
            self._validate_expression_columns(join.on_condition, result)

        # Step 4: Validate WHERE clause expressions
        if query.where_clause:
            self._validate_expression_columns(query.where_clause, result)

        # Step 5: Validate SELECT list items
        is_wildcard = (len(query.select_items) == 1 and query.select_items[0].expression == "*")

        if is_wildcard:
            # Expand wildcard projections from all participating tables
            for tbl_ref, actual_tbl in result.table_bindings.items():
                if tbl_ref == actual_tbl:  # Avoid duplicate entries for aliases
                    for c_name, c_type in self.catalog[actual_tbl].items():
                        result.resolved_projections.append({
                            "name": f"{actual_tbl}.{c_name}" if len(query.joins) > 0 else c_name,
                            "source_table": actual_tbl,
                            "data_type": c_type,
                            "alias": None
                        })
        else:
            for item in query.select_items:
                expr = item.expression
                if isinstance(expr, AggregateCall):
                    # Validate aggregate function
                    func = expr.func_name.upper()
                    if func not in {"COUNT", "SUM", "AVG", "MIN", "MAX"}:
                        result.add_error(f"Unsupported aggregate function '{func}'.")
                    if expr.argument == "*":
                        if func != "COUNT":
                            result.add_error(f"Aggregate function '{func}' does not accept '*' argument.")
                        result.resolved_projections.append({
                            "name": f"{func}(*)",
                            "source_table": "Aggregated",
                            "data_type": "INTEGER",
                            "alias": item.alias
                        })
                    elif isinstance(expr.argument, ColumnRef):
                        res_col = self._resolve_column(expr.argument, result)
                        if res_col:
                            tbl, col_name, dtype = res_col
                            result.resolved_projections.append({
                                "name": f"{func}({expr.argument})",
                                "source_table": tbl,
                                "data_type": "REAL" if func == "AVG" else dtype,
                                "alias": item.alias
                            })
                elif isinstance(expr, ColumnRef):
                    res_col = self._resolve_column(expr, result)
                    if res_col:
                        tbl, col_name, dtype = res_col
                        result.resolved_projections.append({
                            "name": col_name,
                            "source_table": tbl,
                            "data_type": dtype,
                            "alias": item.alias
                        })
                elif isinstance(expr, str) and expr == "*":
                    result.add_error("Wildcard '*' cannot be combined with explicit column projections.")
                else:
                    result.resolved_projections.append({
                        "name": str(expr),
                        "source_table": "Constant",
                        "data_type": "UNKNOWN",
                        "alias": item.alias
                    })

        # Step 6: Validate GROUP BY columns
        for col_ref in query.group_by:
            self._resolve_column(col_ref, result)

        # Step 7: Validate ORDER BY columns
        for order_item in query.order_by:
            self._resolve_column(order_item.expression, result)

        return result

    def _resolve_column(self, col: ColumnRef, result: SemanticResult) -> Optional[Tuple[str, str, str]]:
        """
        Resolves a ColumnRef against available tables.
        Returns (table_name, column_name, data_type) or None if error.
        """
        col_name = col.column
        prefix = col.table_prefix

        if prefix:
            # Table or alias prefix provided (e.g., s.name or students.name)
            if prefix not in result.table_bindings:
                result.add_error(f"Unknown table or alias prefix '{prefix}' in '{col}'.")
                return None
            real_table = result.table_bindings[prefix]
            table_schema = self.catalog.get(real_table, {})
            if col_name not in table_schema:
                result.add_error(f"Column '{col_name}' does not exist in table '{real_table}' (referenced via '{prefix}').")
                return None
            return (real_table, col_name, table_schema[col_name])
        else:
            # Unqualified column name: search across all active unique tables
            candidate_tables = []
            active_real_tables = set(result.table_bindings.values())

            for tbl in active_real_tables:
                if col_name in self.catalog.get(tbl, {}):
                    candidate_tables.append(tbl)

            if len(candidate_tables) == 0:
                # Find available tables for helpful error message
                table_list = ", ".join(f"'{t}'" for t in active_real_tables)
                result.add_error(f"Column '{col_name}' does not exist in referenced table(s): {table_list}.")
                return None
            elif len(candidate_tables) > 1:
                tables_str = ", ".join(f"'{t}'" for t in candidate_tables)
                result.add_error(f"Ambiguous column reference '{col_name}'. It exists in multiple tables: {tables_str}. Please qualify with table prefix.")
                return None
            else:
                real_table = candidate_tables[0]
                return (real_table, col_name, self.catalog[real_table][col_name])

    def _validate_expression_columns(self, expr: Any, result: SemanticResult) -> None:
        """Recursively checks that all columns referenced in an expression exist."""
        if expr is None:
            return
        if isinstance(expr, BinaryOp):
            self._validate_expression_columns(expr.left, result)
            self._validate_expression_columns(expr.right, result)
        elif isinstance(expr, UnaryOp):
            self._validate_expression_columns(expr.operand, result)
        elif isinstance(expr, ColumnRef):
            self._resolve_column(expr, result)
        elif isinstance(expr, AggregateCall):
            if isinstance(expr.argument, ColumnRef):
                self._resolve_column(expr.argument, result)


if __name__ == "__main__":
    from database import DatabaseManager
    from parser import parse_sql

    db = DatabaseManager()
    catalog = db.get_schema_catalog()
    analyzer = SemanticAnalyzer(catalog)

    print("Testing Valid Query:")
    q_valid = parse_sql("SELECT name, marks FROM students WHERE marks > 80;")
    res_valid = analyzer.analyze(q_valid)
    print(res_valid.format_report())

    print("\n" + "=" * 60 + "\nTesting Unknown Column Query:")
    q_invalid = parse_sql("SELECT unknown_column FROM students;")
    res_invalid = analyzer.analyze(q_invalid)
    print(res_invalid.format_report())

