from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QMessageBox, QLabel
)

class SearchDialog(QDialog):
    """Диалог поиска по таблице с защитой от SQL Injection и переключателем LIKE/SIMILAR TO."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info

        self.search_condition = None
        self.search_params = None

        self.setWindowTitle(f"Поиск: {self.table_name}")
        self.setMinimumWidth(560)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        # Столбец
        self.col_combo = QComboBox()
        self.col_combo.setMinimumWidth(200)
        self.col_combo.view().setMinimumWidth(240)
        self.col_combo.addItems([c['name'] for c in self.columns_info])
        form.addRow("Столбец:", self.col_combo)

        # Оператор
        self.op_combo = QComboBox()
        self.op_combo.setMinimumWidth(200)
        self.op_combo.view().setMinimumWidth(240)
        # Переключатель между LIKE и SIMILAR TO + отрицания
        self.op_combo.addItems([
            "LIKE",
            "NOT LIKE",
            "SIMILAR TO",
            "NOT SIMILAR TO",
            # Дополнительно оставим классические:
            "=", "!=", "<", "<=", ">", ">="
        ])
        form.addRow("Оператор:", self.op_combo)

        # Значение
        self.value_edit = QLineEdit()
        form.addRow("Значение:", self.value_edit)

        # Хинт по шаблонам
        self.pattern_hint = QLabel("")
        self.pattern_hint.setStyleSheet("color: #666666;")
        form.addRow("Подсказка:", self.pattern_hint)

        # Реакция на смену оператора — обновляем хинт
        self.op_combo.currentTextChanged.connect(self._update_hint)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Инициализация подсказки
        self._update_hint(self.op_combo.currentText())

    def _update_hint(self, op_text):
        """
        Обновляет подсказку по синтаксису шаблонов в зависимости от оператора.
        """
        if op_text in ("LIKE", "NOT LIKE"):
            # Примеры LIKE шаблонов
            self.pattern_hint.setText("Пример для LIKE: '%00%' (содержит '00'), 'A-%' (начинается с 'A-').")
        elif op_text in ("SIMILAR TO", "NOT SIMILAR TO"):
            # Примеры SIMILAR TO шаблонов в синтаксисе PostgreSQL
            # SIMILAR TO использует «шаблоны» SQL (похожие на regexp, но с синтаксисом SQL)
            # В простых случаях можно использовать '%00%' аналогично LIKE.
            # Также доступны группировки: '(A|B)%', символы классов '[0-9]%' — требуется дубль экранирования в Python при необходимости.
            self.pattern_hint.setText("Пример для SIMILAR TO: '%00%' (содержит '00'), '(A|B)%' (начинается с A или B).")
        else:
            self.pattern_hint.setText("Для операторов сравнения введите число или точное значение.")

    def accept_dialog(self):
        col = self.col_combo.currentText()
        op = self.op_combo.currentText()
        raw_val = self.value_edit.text().strip()

        # Операторы без параметра
        if op in ("IS NULL", "IS NOT NULL"):
            self.search_condition = f"{col} {op}"
            self.search_params = None
            self.accept()
            return

        # Валидация вводимого значения
        if raw_val == "":
            QMessageBox.warning(self, "Ошибка", "Введите значение для поиска")
            return

        # Для LIKE/SIMILAR TO обязателен параметр для безопасного выполнения
        if op in ("LIKE", "NOT LIKE", "SIMILAR TO", "NOT SIMILAR TO"):
            # В PostgreSQL SIMILAR TO умеет принимать те же простые шаблоны как и LIKE, например '%00%'.
            # Поэтому тест с pattern '%00%' должен работать и тут.
            # Формируем параметризованное условие:
            self.search_condition = f"{col} {op} %s"
            self.search_params = [raw_val]
            self.accept()
            return

        # Классические сравнения — пытаемся определить число
        if self._is_number(raw_val):
            self.search_condition = f"{col} {op} %s"
            self.search_params = [float(raw_val)]
        else:
            # Строка — сравнение с параметром
            self.search_condition = f"{col} {op} %s"
            self.search_params = [raw_val]

        self.accept()

    @staticmethod
    def _is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False