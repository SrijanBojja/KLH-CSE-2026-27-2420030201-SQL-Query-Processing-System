"""
main.py - Main Application GUI for QueryForge: SQL Query Processing System
A professional, modern Compiler Design desktop application built with Python Tkinter and ttk.
Demonstrates the full SQL query compilation pipeline:
Lexical -> Syntax -> Semantic -> IR -> Optimization -> Execution -> Results
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
import time
from typing import List, Optional, Dict, Any

from database import DatabaseManager
from lexer import SQLLexer, Token, TOKEN_TYPE_DESCRIPTIONS, LexerError
from parser import SQLParser, ParsedQuery, ParserError, parse_sql
from semantic_analyzer import SemanticAnalyzer, SemanticResult
from intermediate_representation import IRGenerator, IntermediateRepresentation
from optimizer import QueryOptimizer, OptimizationResult
from query_executor import QueryExecutor, ExecutionResult


# =====================================================================
# Modern Dark Color Palette & Typography
# =====================================================================
THEME = {
    "bg_dark": "#181825",        # Deep background
    "bg_panel": "#1e1e2e",       # Panel/Card background
    "bg_subpanel": "#252538",    # Secondary sub-panel background
    "bg_input": "#11111b",       # Text editor / input background
    "fg_text": "#cdd6f4",        # Main text
    "fg_muted": "#a6adc8",       # Muted / subtle text
    "fg_heading": "#ffffff",     # Section headings
    "accent_blue": "#89b4fa",    # Primary accent / active
    "accent_teal": "#94e2d5",    # Secondary accent
    "accent_green": "#a6e3a1",   # Success indicator
    "accent_amber": "#f9e2af",   # Warning indicator
    "accent_red": "#f38ba8",     # Error indicator
    "border": "#313244",         # Border outlines
    "btn_bg": "#313244",         # Button background
    "btn_active": "#45475a",     # Button hover/active
    "font_main": ("Segoe UI", 10),
    "font_heading": ("Segoe UI", 12, "bold"),
    "font_title": ("Segoe UI", 16, "bold"),
    "font_mono": ("Consolas", 10),
    "font_mono_bold": ("Consolas", 10, "bold"),
    "font_mono_lg": ("Consolas", 11)
}

SAMPLE_QUERIES = [
    {
        "title": "Query 1: Basic SELECT (Full Table Scan)",
        "sql": "SELECT * FROM students;"
    },
    {
        "title": "Query 2: Filtering (WHERE Selection Predicate)",
        "sql": "SELECT name, marks\nFROM students\nWHERE marks > 80;"
    },
    {
        "title": "Query 3: Sorting & Cardinality Limit (ORDER BY & LIMIT)",
        "sql": "SELECT name, marks\nFROM students\nORDER BY marks DESC\nLIMIT 5;"
    },
    {
        "title": "Query 4: Aggregation & Grouping (GROUP BY & AVG)",
        "sql": "SELECT department, AVG(marks) AS average_marks\nFROM students\nGROUP BY department;"
    },
    {
        "title": "Query 5: Multi-Table Relational JOIN (Theta-Join)",
        "sql": "SELECT s.name, c.course_name, e.grade\nFROM students s\nINNER JOIN enrollments e ON s.student_id = e.student_id\nINNER JOIN courses c ON e.course_id = c.course_id;"
    },
    {
        "title": "Query 6: Semantic Error (Referencing Non-Existent Column)",
        "sql": "SELECT unknown_column FROM students;"
    },
    {
        "title": "Query 7: Syntax Error (Missing Comma / Dangling WHERE)",
        "sql": "SELECT name marks FROM students WHERE;"
    },
    {
        "title": "Query 8: JOIN with Filter (Demonstrates Predicate Pushdown)",
        "sql": "SELECT s.name, c.course_name\nFROM students s\nINNER JOIN enrollments e ON s.student_id = e.student_id\nINNER JOIN courses c ON e.course_id = c.course_id\nWHERE s.marks > 85;"
    },
    {
        "title": "Query 9: Constant Tautology (Demonstrates Constant Folding)",
        "sql": "SELECT name, department, marks\nFROM students\nWHERE 1 = 1 AND marks >= 90;"
    }
]


class QueryForgeApp:
    """Main application window and compiler pipeline controller."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QueryForge – SQL Query Processing System")
        self.root.geometry("1280x820")
        self.root.minsize(1050, 700)
        self.root.configure(bg=THEME["bg_dark"])

        # Core subsystems
        self.db = DatabaseManager()
        self.ir_generator = IRGenerator()
        self.optimizer = QueryOptimizer(self.db.get_schema_catalog())
        self.executor = QueryExecutor(self.db)

        # Pipeline runtime state
        self.current_tokens: List[Token] = []
        self.current_ast: Optional[ParsedQuery] = None
        self.current_semantic_res: Optional[SemanticResult] = None
        self.current_ir: Optional[IntermediateRepresentation] = None
        self.current_opt_res: Optional[OptimizationResult] = None
        self.current_exec_res: Optional[ExecutionResult] = None

        # Step-by-Step execution state
        self.step_mode_active = False
        self.current_step_index = 0
        self.pipeline_stages = ["INPUT", "LEXICAL", "SYNTAX", "SEMANTIC", "IR", "OPTIMIZATION", "EXECUTION", "OUTPUT"]

        self._configure_ttk_styles()
        self._build_ui()
        self._load_initial_sample()
        self.refresh_db_explorer()

    def _configure_ttk_styles(self):
        """Configure ttk widgets for a dark, high-contrast look."""
        style = ttk.Style()
        style.theme_use("clam")

        # General style overrides
        style.configure(".", background=THEME["bg_panel"], foreground=THEME["fg_text"], font=THEME["font_main"])
        style.configure("TFrame", background=THEME["bg_panel"])
        style.configure("TLabel", background=THEME["bg_panel"], foreground=THEME["fg_text"])
        style.configure("TLabelframe", background=THEME["bg_panel"], foreground=THEME["fg_heading"], bordercolor=THEME["border"])
        style.configure("TLabelframe.Label", background=THEME["bg_panel"], foreground=THEME["accent_blue"], font=THEME["font_heading"])

        # Notebook tabs
        style.configure("TNotebook", background=THEME["bg_dark"], borderwidth=0)
        style.configure("TNotebook.Tab", background=THEME["bg_subpanel"], foreground=THEME["fg_muted"],
                        padding=[12, 6], font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", THEME["bg_panel"])],
                  foreground=[("selected", THEME["accent_blue"])])

        # Buttons
        style.configure("TButton", background=THEME["btn_bg"], foreground=THEME["fg_text"],
                        font=("Segoe UI", 9, "bold"), borderwidth=1, padding=[8, 5])
        style.map("TButton",
                  background=[("active", THEME["btn_active"]), ("pressed", THEME["accent_blue"])],
                  foreground=[("pressed", THEME["bg_dark"])])

        style.configure("Primary.TButton", background="#1e3a5f", foreground="#ffffff",
                        font=("Segoe UI", 9, "bold"), padding=[10, 6])
        style.map("Primary.TButton",
                  background=[("active", "#254e80"), ("pressed", THEME["accent_blue"])])

        style.configure("Success.TButton", background="#1b4d3e", foreground="#ffffff",
                        font=("Segoe UI", 9, "bold"), padding=[10, 6])

        # Treeview (for token tables and database data)
        style.configure("Treeview",
                        background=THEME["bg_input"],
                        foreground=THEME["fg_text"],
                        fieldbackground=THEME["bg_input"],
                        font=THEME["font_mono"],
                        rowheight=24,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=THEME["bg_subpanel"],
                        foreground=THEME["accent_blue"],
                        font=("Segoe UI", 9, "bold"),
                        borderwidth=1,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", "#2a3b5c")],
                  foreground=[("selected", "#ffffff")])

        # Scrollbars
        style.configure("Vertical.TScrollbar", background=THEME["bg_subpanel"], troughcolor=THEME["bg_input"], borderwidth=0)
        style.configure("Horizontal.TScrollbar", background=THEME["bg_subpanel"], troughcolor=THEME["bg_input"], borderwidth=0)

        # Combobox
        style.configure("TCombobox", fieldbackground=THEME["bg_input"], background=THEME["bg_subpanel"],
                        foreground=THEME["fg_text"], arrowcolor=THEME["accent_blue"])

    # =====================================================================
    # UI Layout Construction
    # =====================================================================

    def _build_ui(self):
        """Constructs the application layout."""
        # Main vertical container
        main_container = tk.Frame(self.root, bg=THEME["bg_dark"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # 1. Top Header Banner & Pipeline Stage Indicator
        self._build_header(main_container)

        # 2. Middle Content Area (Split: Left Editor & Controls | Right Notebook Views)
        content_paned = tk.PanedWindow(main_container, orient=tk.HORIZONTAL, bg=THEME["bg_dark"],
                                       sashwidth=4, sashrelief=tk.FLAT)
        content_paned.pack(fill=tk.BOTH, expand=True, pady=(8, 8))

        # Left Column: SQL Editor, Sample Selector, Action Buttons
        left_frame = tk.Frame(content_paned, bg=THEME["bg_panel"], padx=10, pady=10, relief=tk.RIDGE, bd=1)
        content_paned.add(left_frame, minsize=420, stretch="never")
        self._build_editor_panel(left_frame)

        # Right Column: Multi-tab Pipeline Stages & Results
        right_frame = tk.Frame(content_paned, bg=THEME["bg_panel"], padx=6, pady=6, relief=tk.RIDGE, bd=1)
        content_paned.add(right_frame, minsize=600, stretch="always")
        self._build_pipeline_notebook(right_frame)

        # 3. Bottom Summary & Metrics Status Bar
        self._build_status_bar(main_container)

    def _build_header(self, parent: tk.Frame):
        """Builds top header with title and visual pipeline stage indicators."""
        header_frame = tk.Frame(parent, bg=THEME["bg_panel"], padx=12, pady=8, relief=tk.RIDGE, bd=1)
        header_frame.pack(fill=tk.X)

        # Top row: Title and Subtitle
        title_row = tk.Frame(header_frame, bg=THEME["bg_panel"])
        title_row.pack(fill=tk.X)

        title_lbl = tk.Label(title_row, text="QueryForge", font=THEME["font_title"],
                             fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        title_lbl.pack(side=tk.LEFT)

        sub_lbl = tk.Label(title_row, text="  SQL Query Processing System | Compiler Design Project",
                           font=("Segoe UI", 10), fg=THEME["fg_muted"], bg=THEME["bg_panel"])
        sub_lbl.pack(side=tk.LEFT, pady=(4, 0))

        # Right side info tag
        engine_tag = tk.Label(title_row, text="Engine: Educational RDBMS Compiler + SQLite VDB",
                              font=("Segoe UI", 9, "italic"), fg=THEME["accent_teal"], bg=THEME["bg_panel"])
        engine_tag.pack(side=tk.RIGHT)

        # Visual Pipeline Indicator Banner
        # INPUT -> LEXICAL -> SYNTAX -> SEMANTIC -> IR -> OPTIMIZATION -> EXECUTION -> OUTPUT
        sep = tk.Frame(header_frame, height=1, bg=THEME["border"])
        sep.pack(fill=tk.X, pady=(6, 8))

        pipe_container = tk.Frame(header_frame, bg=THEME["bg_panel"])
        pipe_container.pack(fill=tk.X)

        self.stage_badges: Dict[str, tk.Label] = {}
        for i, stage in enumerate(self.pipeline_stages):
            # Badge
            badge = tk.Label(
                pipe_container,
                text=f"{i+1}. {stage}",
                font=("Segoe UI", 8, "bold"),
                bg=THEME["bg_subpanel"],
                fg=THEME["fg_muted"],
                padx=8,
                pady=3,
                relief=tk.FLAT,
                bd=0
            )
            badge.pack(side=tk.LEFT, padx=(0, 2))
            self.stage_badges[stage] = badge

            # Arrow between stages
            if i < len(self.pipeline_stages) - 1:
                arrow = tk.Label(pipe_container, text="->", font=("Segoe UI", 8, "bold"),
                                 fg=THEME["fg_muted"], bg=THEME["bg_panel"])
                arrow.pack(side=tk.LEFT, padx=3)

    def _set_pipeline_badge_state(self, stage: str, state: str):
        """
        Updates pipeline badge color:
        state: 'idle', 'active', 'success', 'error', 'skipped'
        """
        badge = self.stage_badges.get(stage)
        if not badge:
            return

        if state == "active":
            badge.configure(bg=THEME["accent_blue"], fg=THEME["bg_dark"])
        elif state == "success":
            badge.configure(bg=THEME["accent_green"], fg=THEME["bg_dark"])
        elif state == "error":
            badge.configure(bg=THEME["accent_red"], fg="#ffffff")
        elif state == "skipped":
            badge.configure(bg=THEME["border"], fg=THEME["fg_muted"])
        else:  # idle
            badge.configure(bg=THEME["bg_subpanel"], fg=THEME["fg_muted"])

    def _reset_pipeline_badges(self):
        for stage in self.pipeline_stages:
            self._set_pipeline_badge_state(stage, "idle")

    def _build_editor_panel(self, parent: tk.Frame):
        """Builds left column: sample queries, SQL editor, and control buttons."""
        # 1. Sample Query Selector
        sample_lbl = tk.Label(parent, text="SELECT SAMPLE DEMONSTRATION QUERY:",
                              font=("Segoe UI", 9, "bold"), fg=THEME["accent_teal"], bg=THEME["bg_panel"])
        sample_lbl.pack(anchor=tk.W, pady=(0, 4))

        self.sample_combo = ttk.Combobox(parent, state="readonly", font=("Segoe UI", 9))
        self.sample_combo["values"] = [s["title"] for s in SAMPLE_QUERIES]
        self.sample_combo.current(0)
        self.sample_combo.pack(fill=tk.X, pady=(0, 8))
        self.sample_combo.bind("<<ComboboxSelected>>", lambda e: self._on_sample_selected())

        # 2. SQL Query Editor Label
        editor_lbl_frame = tk.Frame(parent, bg=THEME["bg_panel"])
        editor_lbl_frame.pack(fill=tk.X, pady=(0, 4))

        editor_lbl = tk.Label(editor_lbl_frame, text="SQL QUERY INPUT:",
                              font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        editor_lbl.pack(side=tk.LEFT)

        clear_btn = tk.Button(editor_lbl_frame, text="Clear", font=("Segoe UI", 8),
                              bg=THEME["bg_subpanel"], fg=THEME["fg_muted"], activebackground=THEME["btn_active"],
                              relief=tk.FLAT, bd=1, padx=6, pady=1, command=self.clear_editor)
        clear_btn.pack(side=tk.RIGHT)

        # 3. Text Editor with Scrollbar
        editor_frame = tk.Frame(parent, bg=THEME["border"], bd=1)
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.sql_editor = tk.Text(
            editor_frame,
            wrap=tk.WORD,
            bg=THEME["bg_input"],
            fg="#e0def4",
            insertbackground=THEME["accent_blue"],
            selectbackground="#3b4261",
            font=THEME["font_mono_lg"],
            padx=8,
            pady=8,
            bd=0,
            undo=True
        )
        self.sql_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        editor_scroll = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.sql_editor.yview)
        editor_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sql_editor.configure(yscrollcommand=editor_scroll.set)

        # 4. Action Buttons Grid
        btn_grid = tk.Frame(parent, bg=THEME["bg_panel"])
        btn_grid.pack(fill=tk.X, pady=(0, 8))

        # Full Process Button
        self.btn_process_all = tk.Button(
            btn_grid,
            text="▶ Process All (Full Pipeline)",
            font=("Segoe UI", 9, "bold"),
            bg="#204a87",
            fg="#ffffff",
            activebackground=THEME["accent_blue"],
            activeforeground=THEME["bg_dark"],
            relief=tk.RAISED,
            bd=1,
            pady=6,
            command=self.process_all_stages
        )
        self.btn_process_all.pack(fill=tk.X, pady=(0, 4))

        # Secondary row: Step by step controls
        step_row = tk.Frame(btn_grid, bg=THEME["bg_panel"])
        step_row.pack(fill=tk.X, pady=(0, 4))

        self.btn_step_by_step = tk.Button(
            step_row,
            text="⏭ Step-by-Step",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_subpanel"],
            fg=THEME["fg_text"],
            activebackground=THEME["btn_active"],
            relief=tk.RAISED,
            bd=1,
            pady=4,
            command=self.start_step_mode
        )
        self.btn_step_by_step.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        self.btn_next_step = tk.Button(
            step_row,
            text="Next Step ⏩",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_subpanel"],
            fg=THEME["fg_muted"],
            activebackground=THEME["btn_active"],
            state=tk.DISABLED,
            relief=tk.RAISED,
            bd=1,
            pady=4,
            command=self.execute_next_step
        )
        self.btn_next_step.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # Third row: Load Sample and Reset Database
        action_row = tk.Frame(btn_grid, bg=THEME["bg_panel"])
        action_row.pack(fill=tk.X)

        btn_load_sample = tk.Button(
            action_row,
            text="Load Sample",
            font=("Segoe UI", 8),
            bg=THEME["bg_subpanel"],
            fg=THEME["fg_text"],
            activebackground=THEME["btn_active"],
            relief=tk.RAISED,
            bd=1,
            pady=3,
            command=self._on_sample_selected
        )
        btn_load_sample.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_reset_db = tk.Button(
            action_row,
            text="🔄 Reset Database",
            font=("Segoe UI", 8),
            bg=THEME["bg_subpanel"],
            fg=THEME["accent_amber"],
            activebackground=THEME["btn_active"],
            relief=tk.RAISED,
            bd=1,
            pady=3,
            command=self.reset_database
        )
        btn_reset_db.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # 5. Database Quick Status Box
        db_box = tk.LabelFrame(parent, text="Catalog Environment", font=("Segoe UI", 8, "bold"),
                               bg=THEME["bg_panel"], fg=THEME["fg_muted"], bd=1, padx=8, pady=6)
        db_box.pack(fill=tk.X, pady=(4, 0))

        self.lbl_db_info = tk.Label(
            db_box,
            text="RDBMS: SQLite In-Memory (:memory:)\nTables: students (10), courses (6), enrollments (15)",
            font=("Segoe UI", 8),
            fg=THEME["fg_muted"],
            bg=THEME["bg_panel"],
            justify=tk.LEFT
        )
        self.lbl_db_info.pack(anchor=tk.W)

    def _build_pipeline_notebook(self, parent: tk.Frame):
        """Constructs the tabbed viewer for pipeline stages and query results."""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Lexical Analysis
        self.tab_lexer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_lexer, text="1. Lexical Analysis")
        self._build_tab_lexer(self.tab_lexer)

        # Tab 2: Syntax Analysis
        self.tab_syntax = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_syntax, text="2. Syntax Analysis")
        self._build_tab_syntax(self.tab_syntax)

        # Tab 3: Semantic Analysis
        self.tab_semantic = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_semantic, text="3. Semantic Analysis")
        self._build_tab_semantic(self.tab_semantic)

        # Tab 4: Intermediate Representation (IR)
        self.tab_ir = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ir, text="4. Intermediate Representation (IR)")
        self._build_tab_ir(self.tab_ir)

        # Tab 5: Query Optimization
        self.tab_optimizer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_optimizer, text="5. Query Optimization")
        self._build_tab_optimizer(self.tab_optimizer)

        # Tab 6: Query Execution & Plan
        self.tab_executor = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_executor, text="6. Query Execution")
        self._build_tab_executor(self.tab_executor)

        # Tab 7: Query Results (Table View)
        self.tab_results = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_results, text="7. Output Results")
        self._build_tab_results(self.tab_results)

        # Tab 8: Database Explorer
        self.tab_db_explorer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_db_explorer, text="Database Explorer")
        self._build_tab_db_explorer(self.tab_db_explorer)

    # -----------------------------------------------------------------
    # Tab 1: Lexical Analysis
    # -----------------------------------------------------------------
    def _build_tab_lexer(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        self.lbl_lexer_status = tk.Label(top_bar, text="Status: Ready | Total Tokens: 0",
                                         font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        self.lbl_lexer_status.pack(side=tk.LEFT)

        # Split pane: Token Treeview (left/top) and Token Description Glossary (right/bottom)
        paned = tk.PanedWindow(parent, orient=tk.VERTICAL, bg=THEME["bg_dark"], sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tokens Table
        table_frame = tk.Frame(paned, bg=THEME["bg_input"])
        paned.add(table_frame, minsize=240, stretch="always")

        cols = ("Position", "Token Type", "Lexeme", "Coordinates")
        self.tree_tokens = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        self.tree_tokens.heading("Position", text="Position")
        self.tree_tokens.heading("Token Type", text="Token Type")
        self.tree_tokens.heading("Lexeme", text="Lexeme (Source Slice)")
        self.tree_tokens.heading("Coordinates", text="Line : Column")

        self.tree_tokens.column("Position", width=70, anchor=tk.CENTER)
        self.tree_tokens.column("Token Type", width=140, anchor=tk.W)
        self.tree_tokens.column("Lexeme", width=220, anchor=tk.W)
        self.tree_tokens.column("Coordinates", width=110, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree_tokens.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree_tokens.xview)
        self.tree_tokens.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree_tokens.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Token explanation glossary
        glossary_frame = tk.LabelFrame(paned, text="Token Classification Reference",
                                       font=("Segoe UI", 8, "bold"), bg=THEME["bg_panel"],
                                       fg=THEME["accent_teal"], bd=1, padx=6, pady=4)
        paned.add(glossary_frame, minsize=140, stretch="never")

        self.txt_lexer_glossary = tk.Text(
            glossary_frame,
            wrap=tk.WORD,
            bg=THEME["bg_subpanel"],
            fg=THEME["fg_text"],
            font=THEME["font_mono"],
            bd=0,
            padx=6,
            pady=4,
            height=6
        )
        self.txt_lexer_glossary.pack(fill=tk.BOTH, expand=True)

        glossary_text = "\n".join(f"[{k:<11}] {v}" for k, v in TOKEN_TYPE_DESCRIPTIONS.items() if k != "EOF")
        self.txt_lexer_glossary.insert(tk.END, glossary_text)
        self.txt_lexer_glossary.configure(state=tk.DISABLED)

    # -----------------------------------------------------------------
    # Tab 2: Syntax Analysis
    # -----------------------------------------------------------------
    def _build_tab_syntax(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        self.lbl_syntax_status = tk.Label(top_bar, text="Syntax Status: Ready",
                                          font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        self.lbl_syntax_status.pack(side=tk.LEFT)

        self.txt_syntax_tree = tk.Text(
            parent,
            wrap=tk.NONE,
            bg=THEME["bg_input"],
            fg=THEME["fg_text"],
            font=THEME["font_mono_lg"],
            padx=10,
            pady=10,
            bd=0
        )
        scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.txt_syntax_tree.yview)
        scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.txt_syntax_tree.xview)
        self.txt_syntax_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.txt_syntax_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # -----------------------------------------------------------------
    # Tab 3: Semantic Analysis
    # -----------------------------------------------------------------
    def _build_tab_semantic(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        self.lbl_semantic_status = tk.Label(top_bar, text="Semantic Status: Ready",
                                            font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        self.lbl_semantic_status.pack(side=tk.LEFT)

        self.txt_semantic_report = tk.Text(
            parent,
            wrap=tk.NONE,
            bg=THEME["bg_input"],
            fg=THEME["fg_text"],
            font=THEME["font_mono_lg"],
            padx=10,
            pady=10,
            bd=0
        )
        scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.txt_semantic_report.yview)
        scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.txt_semantic_report.xview)
        self.txt_semantic_report.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.txt_semantic_report.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # -----------------------------------------------------------------
    # Tab 4: Intermediate Representation (IR)
    # -----------------------------------------------------------------
    def _build_tab_ir(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        self.lbl_ir_status = tk.Label(top_bar, text="IR Pipeline: Linear Relational Algebra Operations",
                                      font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        self.lbl_ir_status.pack(side=tk.LEFT)

        self.txt_ir_output = tk.Text(
            parent,
            wrap=tk.NONE,
            bg=THEME["bg_input"],
            fg=THEME["fg_text"],
            font=THEME["font_mono_lg"],
            padx=10,
            pady=10,
            bd=0
        )
        scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.txt_ir_output.yview)
        scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.txt_ir_output.xview)
        self.txt_ir_output.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.txt_ir_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # -----------------------------------------------------------------
    # Tab 5: Query Optimization
    # -----------------------------------------------------------------
    def _build_tab_optimizer(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        self.lbl_optimizer_status = tk.Label(top_bar, text="Optimizer: Rule-Based Logical Transformation",
                                             font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        self.lbl_optimizer_status.pack(side=tk.LEFT)

        self.txt_optimizer_report = tk.Text(
            parent,
            wrap=tk.NONE,
            bg=THEME["bg_input"],
            fg=THEME["fg_text"],
            font=THEME["font_mono_lg"],
            padx=10,
            pady=10,
            bd=0
        )
        scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.txt_optimizer_report.yview)
        scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.txt_optimizer_report.xview)
        self.txt_optimizer_report.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.txt_optimizer_report.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # -----------------------------------------------------------------
    # Tab 6: Query Execution & Physical Plan
    # -----------------------------------------------------------------
    def _build_tab_executor(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        self.lbl_executor_status = tk.Label(top_bar, text="Execution Engine: SQLite Read-Only Authorizer",
                                            font=("Segoe UI", 9, "bold"), fg=THEME["accent_blue"], bg=THEME["bg_panel"])
        self.lbl_executor_status.pack(side=tk.LEFT)

        self.txt_executor_report = tk.Text(
            parent,
            wrap=tk.NONE,
            bg=THEME["bg_input"],
            fg=THEME["fg_text"],
            font=THEME["font_mono_lg"],
            padx=10,
            pady=10,
            bd=0
        )
        scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.txt_executor_report.yview)
        scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.txt_executor_report.xview)
        self.txt_executor_report.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.txt_executor_report.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # -----------------------------------------------------------------
    # Tab 7: Output Results Table
    # -----------------------------------------------------------------
    def _build_tab_results(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        self.lbl_results_status = tk.Label(top_bar, text="Returned Records: 0 rows | Duration: 0.00 ms",
                                           font=("Segoe UI", 9, "bold"), fg=THEME["accent_green"], bg=THEME["bg_panel"])
        self.lbl_results_status.pack(side=tk.LEFT)

        results_frame = tk.Frame(parent, bg=THEME["bg_input"])
        results_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.tree_results = ttk.Treeview(results_frame, show="headings", selectmode="browse")
        scroll_y = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree_results.yview)
        scroll_x = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.tree_results.xview)
        self.tree_results.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree_results.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    # -----------------------------------------------------------------
    # Tab 8: Database Explorer
    # -----------------------------------------------------------------
    def _build_tab_db_explorer(self, parent: ttk.Frame):
        top_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=6, pady=4)
        top_bar.pack(fill=tk.X)

        lbl = tk.Label(top_bar, text="Sample Database Schema & Live Table Inspector",
                       font=("Segoe UI", 9, "bold"), fg=THEME["accent_teal"], bg=THEME["bg_panel"])
        lbl.pack(side=tk.LEFT)

        refresh_btn = tk.Button(top_bar, text="Refresh Tables", font=("Segoe UI", 8),
                                bg=THEME["bg_subpanel"], fg=THEME["fg_text"],
                                relief=tk.FLAT, bd=1, padx=6, pady=1, command=self.refresh_db_explorer)
        refresh_btn.pack(side=tk.RIGHT)

        paned = tk.PanedWindow(parent, orient=tk.HORIZONTAL, bg=THEME["bg_dark"], sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left subpane: Tables list
        left_sub = tk.LabelFrame(paned, text="Tables", font=("Segoe UI", 9, "bold"),
                                 bg=THEME["bg_panel"], fg=THEME["accent_blue"], bd=1, padx=6, pady=6)
        paned.add(left_sub, minsize=180, stretch="never")

        self.listbox_tables = tk.Listbox(
            left_sub,
            bg=THEME["bg_input"],
            fg=THEME["fg_text"],
            selectbackground="#2a3b5c",
            selectforeground="#ffffff",
            font=THEME["font_mono_bold"],
            bd=0
        )
        self.listbox_tables.pack(fill=tk.BOTH, expand=True)
        self.listbox_tables.bind("<<ListboxSelect>>", lambda e: self._on_table_selected())

        # Right subpane: Split into Column Schema (top) and Live Records (bottom)
        right_sub = tk.PanedWindow(paned, orient=tk.VERTICAL, bg=THEME["bg_dark"], sashwidth=4)
        paned.add(right_sub, minsize=400, stretch="always")

        # Upper: Column Schema
        schema_frame = tk.LabelFrame(right_sub, text="Table Schema & Constraints",
                                     font=("Segoe UI", 9, "bold"), bg=THEME["bg_panel"],
                                     fg=THEME["accent_blue"], bd=1, padx=4, pady=4)
        right_sub.add(schema_frame, minsize=150, stretch="never")

        cols_schema = ("Column Name", "Data Type", "Not Null", "Primary Key")
        self.tree_schema = ttk.Treeview(schema_frame, columns=cols_schema, show="headings", height=5)
        for c in cols_schema:
            self.tree_schema.heading(c, text=c)
            self.tree_schema.column(c, width=110, anchor=tk.CENTER if "Key" in c or "Null" in c else tk.W)
        self.tree_schema.pack(fill=tk.BOTH, expand=True)

        # Lower: Records Preview
        records_frame = tk.LabelFrame(right_sub, text="Live Table Data Preview",
                                      font=("Segoe UI", 9, "bold"), bg=THEME["bg_panel"],
                                      fg=THEME["accent_blue"], bd=1, padx=4, pady=4)
        right_sub.add(records_frame, minsize=200, stretch="always")

        self.tree_records = ttk.Treeview(records_frame, show="headings")
        scroll_rec_y = ttk.Scrollbar(records_frame, orient=tk.VERTICAL, command=self.tree_records.yview)
        scroll_rec_x = ttk.Scrollbar(records_frame, orient=tk.HORIZONTAL, command=self.tree_records.xview)
        self.tree_records.configure(yscrollcommand=scroll_rec_y.set, xscrollcommand=scroll_rec_x.set)

        self.tree_records.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_rec_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_rec_x.pack(side=tk.BOTTOM, fill=tk.X)

    # -----------------------------------------------------------------
    # Status Bar Construction
    # -----------------------------------------------------------------
    def _build_status_bar(self, parent: tk.Frame):
        status_bar = tk.Frame(parent, bg=THEME["bg_panel"], padx=10, pady=4, relief=tk.RIDGE, bd=1)
        status_bar.pack(fill=tk.X)

        self.status_token_lbl = tk.Label(status_bar, text="Tokens: --", font=("Segoe UI", 8),
                                         fg=THEME["fg_muted"], bg=THEME["bg_panel"])
        self.status_token_lbl.pack(side=tk.LEFT, padx=(0, 15))

        self.status_syntax_lbl = tk.Label(status_bar, text="Syntax: --", font=("Segoe UI", 8),
                                          fg=THEME["fg_muted"], bg=THEME["bg_panel"])
        self.status_syntax_lbl.pack(side=tk.LEFT, padx=(0, 15))

        self.status_semantic_lbl = tk.Label(status_bar, text="Semantic: --", font=("Segoe UI", 8),
                                            fg=THEME["fg_muted"], bg=THEME["bg_panel"])
        self.status_semantic_lbl.pack(side=tk.LEFT, padx=(0, 15))

        self.status_opt_lbl = tk.Label(status_bar, text="Optimization: --", font=("Segoe UI", 8),
                                       fg=THEME["fg_muted"], bg=THEME["bg_panel"])
        self.status_opt_lbl.pack(side=tk.LEFT, padx=(0, 15))

        self.status_exec_lbl = tk.Label(status_bar, text="Execution: Ready", font=("Segoe UI", 8, "bold"),
                                        fg=THEME["accent_green"], bg=THEME["bg_panel"])
        self.status_exec_lbl.pack(side=tk.RIGHT)

    # =====================================================================
    # Editor & Database Explorer Interaction Handlers
    # =====================================================================

    def _load_initial_sample(self):
        """Loads default sample query into the editor."""
        self._on_sample_selected()

    def _on_sample_selected(self):
        idx = self.sample_combo.current()
        if 0 <= idx < len(SAMPLE_QUERIES):
            self.sql_editor.delete("1.0", tk.END)
            self.sql_editor.insert(tk.END, SAMPLE_QUERIES[idx]["sql"])

    def clear_editor(self):
        self.sql_editor.delete("1.0", tk.END)
        self._reset_pipeline_badges()
        self._set_pipeline_badge_state("INPUT", "active")

    def reset_database(self):
        """Re-initializes in-memory database and restores catalog."""
        self.db.initialize_database()
        self.optimizer = QueryOptimizer(self.db.get_schema_catalog())
        self.refresh_db_explorer()
        messagebox.showinfo(
            "Database Reset",
            "In-memory SQLite database has been restored to default state with original sample records!"
        )

    def refresh_db_explorer(self):
        """Refreshes table list and schema information."""
        self.listbox_tables.delete(0, tk.END)
        tables = self.db.get_table_names()
        for t in tables:
            cnt = self.db.get_table_row_count(t)
            self.listbox_tables.insert(tk.END, f"{t} ({cnt})")

        if tables:
            self.listbox_tables.selection_set(0)
            self._on_table_selected()

        # Update editor quick tag
        summary_text = f"RDBMS: SQLite In-Memory (:memory:)\nTables: " + ", ".join(
            f"{t} ({self.db.get_table_row_count(t)})" for t in tables
        )
        self.lbl_db_info.configure(text=summary_text)

    def _on_table_selected(self):
        sel = self.listbox_tables.curselection()
        if not sel:
            return
        tbl_text = self.listbox_tables.get(sel[0])
        tbl_name = tbl_text.split(" ")[0]

        # 1. Fill Schema
        for item in self.tree_schema.get_children():
            self.tree_schema.delete(item)

        col_infos = self.db.get_table_columns_info(tbl_name)
        for col_name, ctype, notnull, is_pk in col_infos:
            self.tree_schema.insert("", tk.END, values=(
                col_name,
                ctype,
                "YES" if notnull else "NO",
                "PRIMARY KEY" if is_pk else ""
            ))

        # 2. Fill Records Preview
        for item in self.tree_records.get_children():
            self.tree_records.delete(item)

        col_names, rows = self.db.get_table_data(tbl_name)
        self.tree_records["columns"] = col_names
        for c in col_names:
            self.tree_records.heading(c, text=c)
            self.tree_records.column(c, width=120, anchor=tk.W)

        for row in rows:
            self.tree_records.insert("", tk.END, values=row)

    # =====================================================================
    # Compiler Pipeline Execution Engine
    # =====================================================================

    def process_all_stages(self):
        """Executes all 8 pipeline stages sequentially in a single pass."""
        self.step_mode_active = False
        self.btn_next_step.configure(state=tk.DISABLED)
        self._reset_pipeline_badges()

        sql_input = self.sql_editor.get("1.0", tk.END).strip()
        if not sql_input:
            messagebox.showwarning("Empty Query", "Please enter an SQL query to process.")
            self._set_pipeline_badge_state("INPUT", "error")
            return

        self._set_pipeline_badge_state("INPUT", "success")

        # 1. Lexical Analysis
        ok = self._run_stage_lexical(sql_input)
        if not ok:
            return

        # 2. Syntax Analysis
        ok = self._run_stage_syntax(sql_input)
        if not ok:
            return

        # 3. Semantic Analysis
        ok = self._run_stage_semantic()
        if not ok:
            return

        # 4. Intermediate Representation
        ok = self._run_stage_ir()
        if not ok:
            return

        # 5. Query Optimization
        ok = self._run_stage_optimizer()
        if not ok:
            return

        # 6. Query Execution & Results
        ok = self._run_stage_executor(sql_input)
        if not ok:
            return

        # Switch to Results tab automatically on full success
        self.notebook.select(self.tab_results)

    # -----------------------------------------------------------------
    # Step-by-Step Mode Controller
    # -----------------------------------------------------------------
    def start_step_mode(self):
        """Initiates step-by-step pipeline execution mode."""
        sql_input = self.sql_editor.get("1.0", tk.END).strip()
        if not sql_input:
            messagebox.showwarning("Empty Query", "Please enter an SQL query to process.")
            return

        self.step_mode_active = True
        self.current_step_index = 1
        self._reset_pipeline_badges()
        self._set_pipeline_badge_state("INPUT", "success")
        self.btn_next_step.configure(state=tk.NORMAL)

        # Prompt user about step mode
        self.execute_next_step()

    def execute_next_step(self):
        """Advances pipeline to the next individual stage."""
        if not self.step_mode_active:
            return

        sql_input = self.sql_editor.get("1.0", tk.END).strip()

        if self.current_step_index == 1:
            # Stage: Lexical
            ok = self._run_stage_lexical(sql_input)
            self.notebook.select(self.tab_lexer)
            if not ok:
                self._stop_step_mode()
                return
            self.current_step_index += 1

        elif self.current_step_index == 2:
            # Stage: Syntax
            ok = self._run_stage_syntax(sql_input)
            self.notebook.select(self.tab_syntax)
            if not ok:
                self._stop_step_mode()
                return
            self.current_step_index += 1

        elif self.current_step_index == 3:
            # Stage: Semantic
            ok = self._run_stage_semantic()
            self.notebook.select(self.tab_semantic)
            if not ok:
                self._stop_step_mode()
                return
            self.current_step_index += 1

        elif self.current_step_index == 4:
            # Stage: IR
            ok = self._run_stage_ir()
            self.notebook.select(self.tab_ir)
            if not ok:
                self._stop_step_mode()
                return
            self.current_step_index += 1

        elif self.current_step_index == 5:
            # Stage: Optimization
            ok = self._run_stage_optimizer()
            self.notebook.select(self.tab_optimizer)
            if not ok:
                self._stop_step_mode()
                return
            self.current_step_index += 1

        elif self.current_step_index == 6:
            # Stage: Execution & Results
            ok = self._run_stage_executor(sql_input)
            self.notebook.select(self.tab_results)
            self._stop_step_mode()

    def _stop_step_mode(self):
        self.step_mode_active = False
        self.btn_next_step.configure(state=tk.DISABLED)

    # -----------------------------------------------------------------
    # Individual Pipeline Stage Implementations
    # -----------------------------------------------------------------

    def _run_stage_lexical(self, sql: str) -> bool:
        """Executes Stage 1: Lexical Analysis."""
        self._set_pipeline_badge_state("LEXICAL", "active")
        for item in self.tree_tokens.get_children():
            self.tree_tokens.delete(item)

        try:
            lexer = SQLLexer(sql)
            self.current_tokens = lexer.tokenize()

            # Populate Treeview
            for tok in self.current_tokens:
                coords = f"Line {tok.line} : Col {tok.column}"
                self.tree_tokens.insert("", tk.END, values=(tok.position, tok.token_type, tok.lexeme, coords))

            self.lbl_lexer_status.configure(
                text=f"Status: SUCCESS | Tokens Identified: {len(self.current_tokens)}",
                fg=THEME["accent_green"]
            )
            self.status_token_lbl.configure(
                text=f"Tokens: {len(self.current_tokens)}",
                fg=THEME["fg_text"]
            )
            self._set_pipeline_badge_state("LEXICAL", "success")
            return True

        except LexerError as lex_err:
            self._set_pipeline_badge_state("LEXICAL", "error")
            self._mark_subsequent_stages_skipped(["SYNTAX", "SEMANTIC", "IR", "OPTIMIZATION", "EXECUTION", "OUTPUT"])
            self.lbl_lexer_status.configure(text=f"Status: ERROR | {str(lex_err)}", fg=THEME["accent_red"])
            self.status_token_lbl.configure(text="Tokens: ERROR", fg=THEME["accent_red"])
            self.notebook.select(self.tab_lexer)
            messagebox.showerror("Lexical Error", str(lex_err))
            return False

    def _run_stage_syntax(self, sql: str) -> bool:
        """Executes Stage 2: Syntax Analysis."""
        self._set_pipeline_badge_state("SYNTAX", "active")
        self.txt_syntax_tree.delete("1.0", tk.END)

        try:
            parser = SQLParser(self.current_tokens, raw_query=sql)
            self.current_ast = parser.parse()

            # Render Formatted AST
            ast_text = self.current_ast.pretty_tree()
            clause_summary = [
                f"\nCLAUSE BREAKDOWN:",
                f"  * Distinct:      {self.current_ast.distinct}",
                f"  * Select Items:  {len(self.current_ast.select_items)} item(s)",
                f"  * Primary Table: {self.current_ast.from_table}",
                f"  * JOIN Count:    {len(self.current_ast.joins)} join(s)",
                f"  * WHERE Filter:  {self.current_ast.where_clause or 'None'}",
                f"  * GROUP BY:      {', '.join(str(c) for c in self.current_ast.group_by) or 'None'}",
                f"  * ORDER BY:      {', '.join(str(o) for o in self.current_ast.order_by) or 'None'}",
                f"  * LIMIT:         {self.current_ast.limit if self.current_ast.limit is not None else 'None'}"
            ]
            full_syntax_view = ast_text + "\n" + "\n".join(clause_summary)
            self.txt_syntax_tree.insert(tk.END, full_syntax_view)

            self.lbl_syntax_status.configure(text="Syntax Status: VALID (Grammar verified)", fg=THEME["accent_green"])
            self.status_syntax_lbl.configure(text="Syntax: VALID", fg=THEME["accent_green"])
            self._set_pipeline_badge_state("SYNTAX", "success")
            return True

        except ParserError as parse_err:
            self._set_pipeline_badge_state("SYNTAX", "error")
            self._mark_subsequent_stages_skipped(["SEMANTIC", "IR", "OPTIMIZATION", "EXECUTION", "OUTPUT"])
            self.lbl_syntax_status.configure(text=f"Syntax Status: INVALID", fg=THEME["accent_red"])
            self.txt_syntax_tree.insert(tk.END, f">>> SYNTAX ANALYSIS FAILURE:\n\n{str(parse_err)}")
            self.status_syntax_lbl.configure(text="Syntax: INVALID", fg=THEME["accent_red"])
            self.notebook.select(self.tab_syntax)
            messagebox.showerror("Syntax Error", str(parse_err))
            return False

    def _run_stage_semantic(self) -> bool:
        """Executes Stage 3: Semantic Analysis."""
        self._set_pipeline_badge_state("SEMANTIC", "active")
        self.txt_semantic_report.delete("1.0", tk.END)

        catalog = self.db.get_schema_catalog()
        analyzer = SemanticAnalyzer(catalog)
        self.current_semantic_res = analyzer.analyze(self.current_ast)

        report = self.current_semantic_res.format_report()
        self.txt_semantic_report.insert(tk.END, report)

        if self.current_semantic_res.is_valid:
            self.lbl_semantic_status.configure(text="Semantic Status: VALID (Schema bindings verified)", fg=THEME["accent_green"])
            self.status_semantic_lbl.configure(text="Semantic: VALID", fg=THEME["accent_green"])
            self._set_pipeline_badge_state("SEMANTIC", "success")
            return True
        else:
            self._set_pipeline_badge_state("SEMANTIC", "error")
            self._mark_subsequent_stages_skipped(["IR", "OPTIMIZATION", "EXECUTION", "OUTPUT"])
            self.lbl_semantic_status.configure(text="Semantic Status: INVALID (Schema check failed)", fg=THEME["accent_red"])
            self.status_semantic_lbl.configure(text="Semantic: INVALID", fg=THEME["accent_red"])
            self.notebook.select(self.tab_semantic)
            err_msg = "\n".join(self.current_semantic_res.errors)
            messagebox.showerror("Semantic Error", f"Semantic validation failed:\n\n{err_msg}")
            return False

    def _run_stage_ir(self) -> bool:
        """Executes Stage 4: Intermediate Representation Generation."""
        self._set_pipeline_badge_state("IR", "active")
        self.txt_ir_output.delete("1.0", tk.END)

        try:
            self.current_ir = self.ir_generator.generate(self.current_ast)

            ir_display = [
                "=" * 70,
                "LINEAR RELATIONAL ALGEBRA INTERMEDIATE REPRESENTATION (IR)",
                "=" * 70,
                self.current_ir.to_text(),
                "\n" + "=" * 70,
                "OPERATIONAL DECOMPOSITION TABLE",
                "=" * 70,
                self.current_ir.format_detailed_table()
            ]

            self.txt_ir_output.insert(tk.END, "\n".join(ir_display))
            self.lbl_ir_status.configure(
                text=f"IR Pipeline: Generated {len(self.current_ir.operations)} Relational Operations",
                fg=THEME["accent_green"]
            )
            self._set_pipeline_badge_state("IR", "success")
            return True

        except Exception as ex:
            self._set_pipeline_badge_state("IR", "error")
            self._mark_subsequent_stages_skipped(["OPTIMIZATION", "EXECUTION", "OUTPUT"])
            self.lbl_ir_status.configure(text=f"IR Error: {str(ex)}", fg=THEME["accent_red"])
            self.notebook.select(self.tab_ir)
            messagebox.showerror("IR Generation Error", str(ex))
            return False

    def _run_stage_optimizer(self) -> bool:
        """Executes Stage 5: Query Optimization."""
        self._set_pipeline_badge_state("OPTIMIZATION", "active")
        self.txt_optimizer_report.delete("1.0", tk.END)

        try:
            self.current_opt_res = self.optimizer.optimize(self.current_ast, self.current_ir)
            report = self.current_opt_res.format_report()
            self.txt_optimizer_report.insert(tk.END, report)

            applied_count = len(self.current_opt_res.rules_applied)
            self.lbl_optimizer_status.configure(
                text=f"Optimizer: Applied {applied_count} Rule(s) | Logical Transformations Complete",
                fg=THEME["accent_green"] if applied_count > 0 else THEME["accent_teal"]
            )
            self.status_opt_lbl.configure(
                text=f"Optimization: {applied_count} Applied",
                fg=THEME["accent_green"] if applied_count > 0 else THEME["fg_text"]
            )
            self._set_pipeline_badge_state("OPTIMIZATION", "success")
            return True

        except Exception as ex:
            self._set_pipeline_badge_state("OPTIMIZATION", "error")
            self._mark_subsequent_stages_skipped(["EXECUTION", "OUTPUT"])
            self.lbl_optimizer_status.configure(text=f"Optimization Error: {str(ex)}", fg=THEME["accent_red"])
            self.notebook.select(self.tab_optimizer)
            messagebox.showerror("Optimization Error", str(ex))
            return False

    def _run_stage_executor(self, sql: str) -> bool:
        """Executes Stage 6: Query Execution & Results Rendering."""
        self._set_pipeline_badge_state("EXECUTION", "active")
        self.txt_executor_report.delete("1.0", tk.END)

        for item in self.tree_results.get_children():
            self.tree_results.delete(item)

        self.current_exec_res = self.executor.execute(sql)

        # 1. Populate Execution Report Tab
        exec_lines = [
            "=" * 60,
            "DATABASE QUERY EXECUTION METRICS",
            "=" * 60,
            f"Executed Query:   {self.current_exec_res.sql_executed}",
            f"Execution Status: {'SUCCESS' if self.current_exec_res.success else 'FAILED'}",
            f"Latency:          {self.current_exec_res.execution_time_ms:.4f} ms",
            f"Rows Returned:    {self.current_exec_res.row_count}",
            f"Columns:          {', '.join(self.current_exec_res.columns) if self.current_exec_res.columns else 'None'}",
            "\n" + "=" * 60,
            "SQLITE PHYSICAL QUERY PLAN (EXPLAIN QUERY PLAN)",
            "=" * 60
        ]

        if self.current_exec_res.physical_plan:
            for node in self.current_exec_res.physical_plan:
                exec_lines.append(f"  [ID {node['id']:<2} | Parent {node['parent']:<2}] -> {node['detail']}")
        else:
            exec_lines.append("  (Physical execution plan unavailable)")

        exec_lines.append("\nNote: The physical execution plan shows SQLite's low-level B-Tree and storage engine traversal,")
        exec_lines.append("complementing the compiler's logical intermediate representation (IR).")

        self.txt_executor_report.insert(tk.END, "\n".join(exec_lines))

        if not self.current_exec_res.success:
            self._set_pipeline_badge_state("EXECUTION", "error")
            self._set_pipeline_badge_state("OUTPUT", "skipped")
            self.lbl_executor_status.configure(text=f"Execution Failed: {self.current_exec_res.error_message}", fg=THEME["accent_red"])
            self.status_exec_lbl.configure(text="Execution: FAILED", fg=THEME["accent_red"])
            self.notebook.select(self.tab_executor)
            messagebox.showerror("Execution Error", self.current_exec_res.error_message)
            return False

        # 2. Populate Results Table Tab
        self._set_pipeline_badge_state("EXECUTION", "success")
        self._set_pipeline_badge_state("OUTPUT", "success")

        cols = self.current_exec_res.columns
        self.tree_results["columns"] = cols
        for c in cols:
            self.tree_results.heading(c, text=c)
            self.tree_results.column(c, width=130, anchor=tk.W)

        for row in self.current_exec_res.rows:
            self.tree_results.insert("", tk.END, values=row)

        summary_msg = f"Returned Records: {self.current_exec_res.row_count} row(s) | Latency: {self.current_exec_res.execution_time_ms:.3f} ms"
        self.lbl_results_status.configure(text=summary_msg, fg=THEME["accent_green"])
        self.status_exec_lbl.configure(
            text=f"SUCCESS: {self.current_exec_res.row_count} rows in {self.current_exec_res.execution_time_ms:.2f}ms",
            fg=THEME["accent_green"]
        )
        return True

    def _mark_subsequent_stages_skipped(self, stages: List[str]):
        """Marks downstream stages as skipped upon upstream error."""
        for s in stages:
            self._set_pipeline_badge_state(s, "skipped")


def main():
    """Application entry point."""
    root = tk.Tk()
    app = QueryForgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
