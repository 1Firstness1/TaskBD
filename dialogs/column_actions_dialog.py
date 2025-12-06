from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton
)

from .sort_dialog import SortDialog
from .filter_dialog import FilterDialog
from .group_dialog import GroupDialog
from .subquery_dialog import SubqueryDialog
from .case_expression_dialog import CaseExpressionDialog

class ColumnActionsDialog(QDialog):
    """Окно действий над столбцом."""
    def __init__(self, controller, table_name, columns_info, selected_column, prefill_value="", parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.prefill_value = prefill_value
        self.task_dialog = parent  # TaskDialog

        self.setWindowTitle(f"Действия над столбцом: {self.selected_column}")
        self.setMinimumWidth(420)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h3>Столбец: {self.selected_column}</h3>"))

        sort_btn = QPushButton("Сортировка")
        sort_btn.setMinimumHeight(36)
        sort_btn.clicked.connect(self.open_sort)
        layout.addWidget(sort_btn)

        filter_btn = QPushButton("Фильтрация (WHERE)")
        filter_btn.setMinimumHeight(36)
        filter_btn.clicked.connect(self.open_filter)
        layout.addWidget(filter_btn)

        group_btn = QPushButton("Группировка (GROUP BY, агрегаты, HAVING)")
        group_btn.setMinimumHeight(36)
        group_btn.clicked.connect(self.open_group)
        layout.addWidget(group_btn)

        subquery_btn = QPushButton("Подзапросы (ANY/ALL/EXISTS)")
        subquery_btn.setMinimumHeight(36)
        subquery_btn.clicked.connect(self.open_subquery_builder)
        layout.addWidget(subquery_btn)

        case_btn = QPushButton("Выражения CASE / COALESCE / NULLIF")
        case_btn.setMinimumHeight(36)
        case_btn.clicked.connect(self.open_case_builder)
        layout.addWidget(case_btn)

        layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _check_join_for_advanced(self) -> bool:
        if getattr(self.task_dialog, "is_join_mode", False):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Недоступно",
                "Эта операция недоступна при активных соединениях (JOIN).\n"
                "В режиме JOIN разрешены только сортировка и фильтрация."
            )
            return True
        return False

    def open_sort(self):
        dlg = SortDialog(self.selected_column, self)
        if dlg.exec_():
            direction = dlg.direction
            if hasattr(self.task_dialog, "add_sort_clause"):
                self.task_dialog.add_sort_clause(self.selected_column, direction)

    def open_filter(self):
        dlg = FilterDialog(self.selected_column, self.prefill_value, self)
        if dlg.exec_():
            where_clause = dlg.where_clause
            if hasattr(self.task_dialog, "add_where_clause"):
                self.task_dialog.add_where_clause(where_clause)

    def open_group(self):
        if self._check_join_for_advanced():
            return
        dlg = GroupDialog(self.selected_column, self.columns_info, self)
        if dlg.exec_():
            if dlg.group_by_selected and hasattr(self.task_dialog, "add_group_by_column"):
                self.task_dialog.add_group_by_column(dlg.group_by_column)
            if dlg.aggregate_expression and hasattr(self.task_dialog, "add_select_aggregate"):
                self.task_dialog.add_select_aggregate(dlg.aggregate_expression)
            if dlg.having_clause and hasattr(self.task_dialog, "add_having_clause"):
                self.task_dialog.add_having_clause(dlg.having_clause)

    def open_subquery_builder(self):
        if self._check_join_for_advanced():
            return
        dlg = SubqueryDialog(self.controller, self.table_name, self)
        if dlg.exec_():
            clause = dlg.get_clause()
            if clause:
                self.task_dialog.add_where_clause(clause)

    def open_case_builder(self):
        if self._check_join_for_advanced():
            return
        dlg = CaseExpressionDialog(self.controller, self.table_name, self)
        if dlg.exec_():
            expr = dlg.get_case_expression()
            if expr:
                self.task_dialog.add_select_expression(expr)
                self.task_dialog.refresh_with_current_clauses()