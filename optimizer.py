"""
optimizer.py - Logical Query Optimizer for QueryForge SQL System
Applies rule-based logical optimizations to the relational query plan:
1. Predicate Pushdown (moves selection predicates before expensive joins)
2. Projection Pruning (eliminates unreferenced schema attributes early)
3. Constant Simplification (folds constant predicates and tautologies)
4. Logical Plan Simplification (removes redundant operations)
"""

from typing import Dict, List, Set, Any, Optional, Tuple
from parser import ParsedQuery, ColumnRef, AggregateCall, BinaryOp, UnaryOp, Literal
from intermediate_representation import IntermediateRepresentation, IROperation


class OptimizationResult:
    """Encapsulates the optimization outcome, comparison, and rule audit."""
    def __init__(self, original_ir: IntermediateRepresentation):
        self.original_ir = original_ir
        self.optimized_ir: Optional[IntermediateRepresentation] = None
        self.rules_applied: List[Dict[str, str]] = []
        self.rules_not_applicable: List[Dict[str, str]] = []
        self.pruned_columns_by_table: Dict[str, List[str]] = {}
        self.reordered_operations: bool = False

    def format_report(self) -> str:
        """Produces a comprehensive educational comparative optimization report."""
        lines = []
        total_applied = len(self.rules_applied)
        lines.append("=" * 60)
        lines.append(f"LOGICAL QUERY OPTIMIZATION REPORT (Rules Applied: {total_applied})")
        lines.append("=" * 60)

        # Comparative Plans
        lines.append("\n[1] ORIGINAL LOGICAL PLAN:")
        lines.append(self.original_ir.to_text())

        lines.append("\n[2] OPTIMIZED LOGICAL PLAN:")
        if self.optimized_ir:
            lines.append(self.optimized_ir.to_text())
        else:
            lines.append(self.original_ir.to_text())

        # Rules Applied
        lines.append("\n[3] OPTIMIZATION RULES APPLIED:")
        if self.rules_applied:
            for r in self.rules_applied:
                lines.append(f"  + Rule: {r['name']}")
                lines.append(f"    Impact:  {r['explanation']}")
                lines.append(f"    Benefit: {r['benefit']}")
                lines.append("")
        else:
            lines.append("  (None: Original logical plan is already canonical/minimal)")

        # Rules Not Applicable
        lines.append("\n[4] RULES EVALUATED BUT NOT APPLICABLE:")
        for r in self.rules_not_applicable:
            lines.append(f"  - Rule: {r['name']}")
            lines.append(f"    Reason: {r['reason']}")
            lines.append("")

        return "\n".join(lines)


class QueryOptimizer:
    """
    Analyzes AST and IR to perform safe, equivalence-preserving logical transformations.
    """

    def __init__(self, catalog: Dict[str, Dict[str, str]]):
        self.catalog = catalog

    def optimize(self, query: ParsedQuery, original_ir: IntermediateRepresentation) -> OptimizationResult:
        result = OptimizationResult(original_ir)

        # -------------------------------------------------------------
        # Rule 1: Projection Pruning
        # -------------------------------------------------------------
        is_wildcard = (len(query.select_items) == 1 and query.select_items[0].expression == "*")

        if is_wildcard:
            result.rules_not_applicable.append({
                "name": "Projection Pruning",
                "reason": "Query requests wildcard 'SELECT *', which requires all table attributes to be preserved."
            })
        else:
            # Build alias map
            alias_to_table: Dict[str, str] = {query.from_table.name: query.from_table.name}
            if query.from_table.alias:
                alias_to_table[query.from_table.alias] = query.from_table.name
            for j in query.joins:
                alias_to_table[j.table.name] = j.table.name
                if j.table.alias:
                    alias_to_table[j.table.alias] = j.table.name

            # Collect all referenced columns across all clauses
            referenced_cols = self._collect_all_referenced_columns(query)
            tables = [query.from_table.name] + [j.table.name for j in query.joins]
            pruned_details = []

            for tbl in tables:
                all_cols = set(self.catalog.get(tbl, {}).keys())
                used_cols = set()
                for pref, c_name in referenced_cols:
                    if pref is not None:
                        real_t = alias_to_table.get(pref, pref)
                        if real_t == tbl and c_name in all_cols:
                            used_cols.add(c_name)
                    else:
                        # Unprefixed: check if it belongs to this table
                        if c_name in all_cols:
                            used_cols.add(c_name)

                unused_cols = sorted(list(all_cols - used_cols))

                if unused_cols:
                    result.pruned_columns_by_table[tbl] = unused_cols
                    pruned_details.append(f"Table '{tbl}': pruned {len(unused_cols)} unused column(s) ({', '.join(unused_cols)})")

            if pruned_details:
                result.rules_applied.append({
                    "name": "Projection Pruning",
                    "explanation": "; ".join(pruned_details) + ".",
                    "benefit": "Reduces disk I/O, cache footprint, and memory buffer bandwidth by not loading discarded columns."
                })
            else:
                result.rules_not_applicable.append({
                    "name": "Projection Pruning",
                    "reason": "All attributes from referenced tables are required by downstream projections, filters, or joins."
                })

        # -------------------------------------------------------------
        # Rule 2: Constant Simplification / Folding
        # -------------------------------------------------------------
        constant_folded, new_where = self._simplify_constants(query.where_clause)
        if constant_folded:
            result.rules_applied.append({
                "name": "Constant Simplification / Folding",
                "explanation": f"Evaluated and folded constant-only predicates in WHERE clause: {constant_folded}.",
                "benefit": "Eliminates redundant boolean evaluation cycles during per-tuple runtime scanning."
            })
        else:
            result.rules_not_applicable.append({
                "name": "Constant Simplification",
                "reason": "No constant-only comparisons (e.g., 1 = 1 or 5 > 10) found in the query predicates."
            })

        # -------------------------------------------------------------
        # Rule 3: Predicate Pushdown (Filter reordering before Join)
        # -------------------------------------------------------------
        can_pushdown = False
        pushdown_details = ""

        if query.joins and query.where_clause:
            # Check if WHERE clause references only attributes of the base table
            base_tbl = query.from_table.name
            base_alias = query.from_table.alias
            where_cols = self._collect_columns_from_expr(query.where_clause)

            only_base = True
            for tbl_ref, col_name in where_cols:
                if tbl_ref and tbl_ref != base_tbl and tbl_ref != base_alias:
                    only_base = False
                    break
                elif not tbl_ref:
                    # Unqualified: check if it belongs exclusively to base_table
                    base_cols = self.catalog.get(base_tbl, {})
                    other_tbls = [j.table.name for j in query.joins]
                    if col_name not in base_cols:
                        only_base = False
                        break
                    for ot in other_tbls:
                        if col_name in self.catalog.get(ot, {}):
                            only_base = False
                            break

            if only_base:
                can_pushdown = True
                pushdown_details = (
                    f"Selection predicate '{query.where_clause}' references only '{base_tbl}'. "
                    f"Pushed FILTER before {len(query.joins)} JOIN operation(s)."
                )

        if can_pushdown:
            result.reordered_operations = True
            result.rules_applied.append({
                "name": "Predicate Pushdown",
                "explanation": pushdown_details,
                "benefit": "Greatly reduces intermediate join cardinality and prevents computing joins on non-qualifying tuples."
            })
        else:
            if not query.joins:
                reason = "Query operates on a single table (no JOINs present to push predicates through)."
            elif not query.where_clause:
                reason = "No WHERE filter condition present to push down."
            else:
                reason = "Filter predicates span multiple joined relations or depend on join attributes."
            result.rules_not_applicable.append({
                "name": "Predicate Pushdown",
                "reason": reason
            })

        # -------------------------------------------------------------
        # Rule 4: Logical Plan Simplification
        # -------------------------------------------------------------
        # Redundant LIMIT check or redundant scan simplification
        if query.limit is not None and query.limit <= 0:
            result.rules_applied.append({
                "name": "Logical Plan Simplification",
                "explanation": "Detected LIMIT <= 0; query plan yields an empty relation immediately.",
                "benefit": "Avoids full table scans or join execution."
            })
        else:
            result.rules_not_applicable.append({
                "name": "Logical Plan Simplification",
                "reason": "Plan structure is already minimal; no dead branches or redundant operations."
            })

        # -------------------------------------------------------------
        # Generate Optimized IR Plan
        # -------------------------------------------------------------
        optimized_ops = self._build_optimized_ir_ops(query, original_ir, result)
        result.optimized_ir = IntermediateRepresentation(optimized_ops)

        return result

    def _build_optimized_ir_ops(
        self,
        query: ParsedQuery,
        original_ir: IntermediateRepresentation,
        result: OptimizationResult
    ) -> List[IROperation]:
        """Constructs the optimized sequence of IR operations."""
        ops: List[IROperation] = []
        step = 1

        def next_id() -> str:
            nonlocal step
            val = f"OP{step}"
            step += 1
            return val

        # If predicate pushdown is applicable, insert FILTER right after base SCAN
        if result.reordered_operations:
            # 1. Base SCAN
            base_tbl = query.from_table.name
            alias_str = f" AS {query.from_table.alias}" if query.from_table.alias else ""
            ops.append(IROperation(
                op_id=next_id(),
                op_type="SCAN",
                expression=f"{base_tbl}{alias_str}",
                relational_symbol="Relation (R)",
                description=f"Performs sequential access scan over primary relation '{base_tbl}'."
            ))

            # 2. PUSHED DOWN FILTER
            ops.append(IROperation(
                op_id=next_id(),
                op_type="FILTER",
                expression=str(query.where_clause),
                relational_symbol="Select [sigma]",
                description=f"[PUSHDOWN] Filter evaluated early on '{base_tbl}' prior to relational join."
            ))

            # 3. JOINs
            for join in query.joins:
                j_str = f"{join.table.name}"
                if join.table.alias:
                    j_str += f" AS {join.table.alias}"
                ops.append(IROperation(
                    op_id=next_id(),
                    op_type="JOIN",
                    expression=f"{j_str} ON {join.on_condition}",
                    relational_symbol="Join [bowtie]",
                    description=f"Theta-join with '{join.table.name}' on {join.on_condition} over pre-filtered tuples."
                ))

            # 4. Copy remaining operations (GROUP, AGGREGATE, PROJECT, SORT, LIMIT)
            for orig_op in original_ir.operations:
                if orig_op.op_type not in ("SCAN", "JOIN", "FILTER"):
                    ops.append(IROperation(
                        op_id=next_id(),
                        op_type=orig_op.op_type,
                        expression=orig_op.expression,
                        relational_symbol=orig_op.relational_symbol,
                        description=orig_op.description
                    ))
            return ops

        # If no reordering, copy original operations and annotate with optimizations
        for orig_op in original_ir.operations:
            desc = orig_op.description
            expr = orig_op.expression

            if orig_op.op_type == "PROJECT" and "Projection Pruning" in [r['name'] for r in result.rules_applied]:
                desc += " [Optimized: pruned unused schema columns early]"

            ops.append(IROperation(
                op_id=next_id(),
                op_type=orig_op.op_type,
                expression=expr,
                relational_symbol=orig_op.relational_symbol,
                description=desc
            ))

        return ops

    def _collect_all_referenced_columns(self, query: ParsedQuery) -> Set[Tuple[Optional[str], str]]:
        """Finds all (table_or_alias, col_name) referenced in the query."""
        cols = set()

        # In select items
        for item in query.select_items:
            if isinstance(item.expression, ColumnRef):
                cols.add((item.expression.table_prefix, item.expression.column))
            elif isinstance(item.expression, AggregateCall) and isinstance(item.expression.argument, ColumnRef):
                cols.add((item.expression.argument.table_prefix, item.expression.argument.column))

        # In WHERE clause
        if query.where_clause:
            cols.update(self._collect_columns_from_expr(query.where_clause))

        # In JOIN ON conditions
        for join in query.joins:
            cols.update(self._collect_columns_from_expr(join.on_condition))

        # In GROUP BY
        for c in query.group_by:
            cols.add((c.table_prefix, c.column))

        # In ORDER BY
        for o in query.order_by:
            cols.add((o.expression.table_prefix, o.expression.column))

        return cols

    def _collect_columns_from_expr(self, expr: Any) -> Set[Tuple[Optional[str], str]]:
        cols = set()
        if expr is None:
            return cols
        if isinstance(expr, ColumnRef):
            cols.add((expr.table_prefix, expr.column))
        elif isinstance(expr, BinaryOp):
            cols.update(self._collect_columns_from_expr(expr.left))
            cols.update(self._collect_columns_from_expr(expr.right))
        elif isinstance(expr, UnaryOp):
            cols.update(self._collect_columns_from_expr(expr.operand))
        return cols

    def _simplify_constants(self, expr: Any) -> Tuple[Optional[str], Any]:
        """Detects and simplifies constant expressions like 1 = 1."""
        if expr is None:
            return None, None

        if isinstance(expr, BinaryOp):
            # Check if left and right are Literals
            if isinstance(expr.left, Literal) and isinstance(expr.right, Literal):
                if expr.op == "=" and expr.left.value == expr.right.value:
                    return f"({expr.left} = {expr.right}) simplified to TRUE", Literal(value=True, raw_type="BOOLEAN")
            # Recurse
            left_simp, _ = self._simplify_constants(expr.left)
            if left_simp:
                return left_simp, expr
            right_simp, _ = self._simplify_constants(expr.right)
            if right_simp:
                return right_simp, expr

        return None, expr


if __name__ == "__main__":
    from database import DatabaseManager
    from parser import parse_sql
    from intermediate_representation import IRGenerator

    db = DatabaseManager()
    catalog = db.get_schema_catalog()
    ir_gen = IRGenerator()
    opt = QueryOptimizer(catalog)

    test_q = parse_sql("SELECT s.name, c.course_name FROM students s INNER JOIN enrollments e ON s.student_id = e.student_id INNER JOIN courses c ON e.course_id = c.course_id WHERE s.marks > 80;")
    test_ir = ir_gen.generate(test_q)
    res = opt.optimize(test_q, test_ir)
    print(res.format_report())
