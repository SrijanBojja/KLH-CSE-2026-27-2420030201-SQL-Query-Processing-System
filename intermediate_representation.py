"""
intermediate_representation.py - Intermediate Representation (IR) Generator for QueryForge
Converts the parsed and semantically validated AST into a linear Relational Algebra
operator sequence (SCAN, FILTER, JOIN, GROUP, AGGREGATE, PROJECT, SORT, LIMIT).
"""

from dataclasses import dataclass
from typing import List, Optional, Any
from parser import ParsedQuery, SelectItem, AggregateCall, ColumnRef


@dataclass
class IROperation:
    """Represents a single relational algebra step in the logical execution plan."""
    op_id: str               # e.g., 'OP1', 'OP2'
    op_type: str             # SCAN, FILTER, JOIN, AGGREGATE, GROUP_BY, PROJECT, SORT, LIMIT
    expression: str          # Target arguments / expressions
    relational_symbol: str   # Mathematical relational algebra symbol (e.g., sigma, pi, bowtie)
    description: str         # Educational explanation of what this operation performs

    def __str__(self) -> str:
        return f"{self.op_id}: {self.op_type} {self.expression}"


class IntermediateRepresentation:
    """Encapsulates the sequence of IR operations generated from an AST."""
    def __init__(self, operations: List[IROperation]):
        self.operations = operations

    def to_text(self) -> str:
        """Returns the linear representation of the plan."""
        return "\n".join(str(op) for op in self.operations)

    def format_detailed_table(self) -> str:
        """Produces a formatted educational table explaining each step."""
        lines = []
        header = f"{'Step':<6} | {'Operator':<12} | {'Rel. Alg.':<10} | {'Expression / Arguments':<32} | {'Description'}"
        lines.append(header)
        lines.append("-" * len(header) + "-" * 30)

        for op in self.operations:
            lines.append(
                f"{op.op_id:<6} | {op.op_type:<12} | {op.relational_symbol:<10} | {op.expression:<32} | {op.description}"
            )
        return "\n".join(lines)


class IRGenerator:
    """
    Transforms a validated ParsedQuery AST into a structured Intermediate Representation (IR).
    """

    def generate(self, query: ParsedQuery) -> IntermediateRepresentation:
        operations: List[IROperation] = []
        step_num = 1

        def next_id() -> str:
            nonlocal step_num
            val = f"OP{step_num}"
            step_num += 1
            return val

        # 1. Base Table SCAN
        from_tbl_str = query.from_table.name
        if query.from_table.alias:
            from_tbl_str += f" AS {query.from_table.alias}"

        operations.append(IROperation(
            op_id=next_id(),
            op_type="SCAN",
            expression=from_tbl_str,
            relational_symbol="Relation (R)",
            description=f"Performs sequential access scan over primary relation '{query.from_table.name}'."
        ))

        # 2. JOINs (if any)
        for join in query.joins:
            j_str = f"{join.table.name}"
            if join.table.alias:
                j_str += f" AS {join.table.alias}"
            j_expr = f"{j_str} ON {join.on_condition}"

            operations.append(IROperation(
                op_id=next_id(),
                op_type="JOIN",
                expression=j_expr,
                relational_symbol="Join [bowtie]",
                description=f"Computes theta-join with relation '{join.table.name}' matching predicate ({join.on_condition})."
            ))

        # 3. FILTER / SELECTION (WHERE clause)
        if query.where_clause:
            operations.append(IROperation(
                op_id=next_id(),
                op_type="FILTER",
                expression=str(query.where_clause),
                relational_symbol="Select [sigma]",
                description=f"Applies selection predicate sigma({query.where_clause}) to eliminate non-qualifying tuples."
            ))

        # 4. GROUP BY and AGGREGATION
        has_aggregates = any(isinstance(item.expression, AggregateCall) for item in query.select_items)
        if query.group_by:
            grp_cols = ", ".join(str(c) for c in query.group_by)
            operations.append(IROperation(
                op_id=next_id(),
                op_type="GROUP_BY",
                expression=grp_cols,
                relational_symbol="Group [gamma]",
                description=f"Partitions input tuples into equivalence classes sharing identical values of ({grp_cols})."
            ))

        if has_aggregates:
            agg_funcs = [str(item.expression) for item in query.select_items if isinstance(item.expression, AggregateCall)]
            operations.append(IROperation(
                op_id=next_id(),
                op_type="AGGREGATE",
                expression=", ".join(agg_funcs),
                relational_symbol="Aggregate [gamma]",
                description=f"Computes aggregate accumulation functions over grouped partitions: {', '.join(agg_funcs)}."
            ))

        # 5. PROJECTION (SELECT columns)
        proj_items = []
        for item in query.select_items:
            s = str(item.expression)
            if item.alias:
                s += f" AS {item.alias}"
            proj_items.append(s)

        dist_str = " [DISTINCT]" if query.distinct else ""
        proj_expr = ", ".join(proj_items) + dist_str

        operations.append(IROperation(
            op_id=next_id(),
            op_type="PROJECT",
            expression=proj_expr,
            relational_symbol="Project [pi]",
            description=f"Extracts specified attribute projections pi({proj_expr}) while discarding unneeded attributes."
        ))

        # 6. SORT / ORDER BY
        if query.order_by:
            sort_items = ", ".join(str(o) for o in query.order_by)
            operations.append(IROperation(
                op_id=next_id(),
                op_type="SORT",
                expression=sort_items,
                relational_symbol="Sort [tau]",
                description=f"Sorts output tuples according to ordering specification tau({sort_items})."
            ))

        # 7. LIMIT
        if query.limit is not None:
            operations.append(IROperation(
                op_id=next_id(),
                op_type="LIMIT",
                expression=str(query.limit),
                relational_symbol="Limit [lambda]",
                description=f"Restricts cardinality of final relation to at most {query.limit} tuple(s)."
            ))

        return IntermediateRepresentation(operations)


if __name__ == "__main__":
    from parser import parse_sql

    q = parse_sql("SELECT name, marks FROM students WHERE marks > 80 ORDER BY marks DESC LIMIT 5;")
    ir_gen = IRGenerator()
    ir = ir_gen.generate(q)
    print("Linear Plan:")
    print(ir.to_text())
    print("\nDetailed Breakdown Table:")
    print(ir.format_detailed_table())
