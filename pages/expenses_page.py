from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QDateEdit, QTextEdit,
                               QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
                               QTabWidget, QGroupBox, QProgressBar)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from database import ExpenseManager, PlantManager


class BudgetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('设置预算')
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2099)
        self.year_spin.setValue(datetime.now().year)
        form.addRow('年份：', self.year_spin)

        self.category_combo = QComboBox()
        self.category_combo.addItems(['采购', '补植', '养护', '农药', '肥料', '设备', '其他'])
        form.addRow('费用类型：', self.category_combo)

        self.area_combo = QComboBox()
        self.area_combo.addItem('全局', '')
        areas = PlantManager.get_areas()
        for a in areas:
            self.area_combo.addItem(a, a)
        form.addRow('区域：', self.area_combo)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 999999999)
        self.amount_spin.setPrefix('¥ ')
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(0)
        form.addRow('预算金额：', self.amount_spin)

        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(60)
        form.addRow('备注：', self.notes_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            'year': self.year_spin.value(),
            'category': self.category_combo.currentText(),
            'area_name': self.area_combo.currentData(),
            'amount': self.amount_spin.value(),
            'notes': self.notes_input.toPlainText().strip(),
        }


class ExpenseDialog(QDialog):
    def __init__(self, parent=None, expense=None):
        super().__init__(parent)
        self.expense = expense
        self.setWindowTitle('费用记录')
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.type_combo = QComboBox()
        self.type_combo.addItems(['采购', '补植', '养护', '农药', '肥料', '设备', '其他'])
        form.addRow('费用类型：', self.type_combo)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 9999999)
        self.amount_spin.setPrefix('¥ ')
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(0)
        form.addRow('金额：', self.amount_spin)

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow('日期：', self.date_edit)

        self.vendor_input = QLineEdit()
        form.addRow('供应商：', self.vendor_input)

        self.contract_check = QDateEdit()
        self.contract_check.setDisplayFormat('yyyy-MM-dd')
        self.contract_check.setCalendarPopup(True)
        self.contract_check.setDate(QDate.currentDate().addYears(1))
        form.addRow('合同到期日：', self.contract_check)

        self.plant_combo = QComboBox()
        self.plant_combo.addItem('无关联', None)
        plants = PlantManager.get_all()
        for p in plants:
            self.plant_combo.addItem(p['name'], p['id'])
        form.addRow('关联植株：', self.plant_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        form.addRow('备注：', self.notes_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if expense:
            self.load_data(expense)

    def load_data(self, expense):
        idx = self.type_combo.findText(expense.get('expense_type', ''))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.amount_spin.setValue(expense.get('amount', 0))
        if expense.get('expense_date'):
            d = QDate.fromString(expense['expense_date'], 'yyyy-MM-dd')
            if d.isValid():
                self.date_edit.setDate(d)
        self.vendor_input.setText(expense.get('vendor', ''))
        if expense.get('contract_end_date'):
            d = QDate.fromString(expense['contract_end_date'], 'yyyy-MM-dd')
            if d.isValid():
                self.contract_check.setDate(d)
        if expense.get('related_plant_id'):
            idx = self.plant_combo.findData(expense['related_plant_id'])
            if idx >= 0:
                self.plant_combo.setCurrentIndex(idx)
        self.notes_input.setPlainText(expense.get('notes', ''))

    def get_data(self):
        return {
            'expense_type': self.type_combo.currentText(),
            'amount': self.amount_spin.value(),
            'expense_date': self.date_edit.date().toString('yyyy-MM-dd'),
            'vendor': self.vendor_input.text().strip(),
            'contract_end_date': self.contract_check.date().toString('yyyy-MM-dd'),
            'related_plant_id': self.plant_combo.currentData(),
            'notes': self.notes_input.toPlainText().strip(),
        }


class ExpensesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        summary_bar = QFrame()
        summary_bar.setStyleSheet('background: white; border-radius: 8px;')
        sb_layout = QHBoxLayout(summary_bar)
        sb_layout.setContentsMargins(16, 12, 16, 12)
        sb_layout.setSpacing(24)

        self.total_label = QLabel('💰 累计费用：¥ 0.00')
        self.total_label.setStyleSheet('font-size: 18px; font-weight: 700; color: #e6a23c;')
        sb_layout.addWidget(self.total_label)

        self.year_label = QLabel('📅 本年度：¥ 0.00')
        self.year_label.setStyleSheet('font-size: 15px; color: #606266;')
        sb_layout.addWidget(self.year_label)

        self.contract_alert_label = QLabel('🔔 即将到期合同：0 份')
        self.contract_alert_label.setStyleSheet('font-size: 14px; color: #f56c6c; font-weight: 600;')
        sb_layout.addWidget(self.contract_alert_label)

        self.budget_alert_label = QLabel('')
        self.budget_alert_label.setStyleSheet('font-size: 14px; color: #f56c6c; font-weight: 600;')
        self.budget_alert_label.setVisible(False)
        sb_layout.addWidget(self.budget_alert_label)

        sb_layout.addStretch()

        layout.addWidget(summary_bar)

        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        self.type_filter = QComboBox()
        self.type_filter.addItem('全部类型')
        self.type_filter.addItems(['采购', '补植', '养护', '农药', '肥料', '设备', '其他'])
        self.type_filter.setFixedWidth(120)
        self.type_filter.currentTextChanged.connect(self.refresh)
        tb_layout.addWidget(self.type_filter)

        self.year_filter = QComboBox()
        self.year_filter.addItem('全部年份')
        current_year = datetime.now().year
        for y in range(current_year, current_year - 5, -1):
            self.year_filter.addItem(str(y), y)
        self.year_filter.setFixedWidth(120)
        self.year_filter.currentIndexChanged.connect(self.refresh)
        tb_layout.addWidget(self.year_filter)

        tb_layout.addStretch()

        btn_add = QPushButton('➕ 添加记录')
        btn_add.setProperty('class', 'primary')
        btn_add.clicked.connect(self.add_expense)
        tb_layout.addWidget(btn_add)

        layout.addWidget(toolbar)

        tabs = QTabWidget()

        all_tab = QWidget()
        all_layout = QVBoxLayout(all_tab)
        all_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(['ID', '类型', '金额', '日期', '供应商', '合同到期', '关联植株', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self.edit_from_table)
        all_layout.addWidget(self.table)

        tabs.addTab(all_tab, '全部记录')

        contract_tab = QWidget()
        contract_layout = QVBoxLayout(contract_tab)
        contract_layout.setContentsMargins(0, 0, 0, 0)

        contract_header = QFrame()
        contract_header.setStyleSheet('background: #fef0f0; border-radius: 6px; padding: 10px;')
        ch_layout = QHBoxLayout(contract_header)
        ch_layout.setContentsMargins(12, 8, 12, 8)
        ch_label = QLabel('🔔 合同到期提醒（30天内）')
        ch_label.setStyleSheet('font-weight: 600; color: #f56c6c;')
        ch_layout.addWidget(ch_label)
        ch_layout.addStretch()
        contract_layout.addWidget(contract_header)

        self.contract_table = QTableWidget(0, 6)
        self.contract_table.setHorizontalHeaderLabels(['供应商', '类型', '金额', '到期日期', '剩余天数', '操作'])
        self.contract_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.contract_table.verticalHeader().setVisible(False)
        self.contract_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.contract_table.setSelectionBehavior(QTableWidget.SelectRows)
        contract_layout.addWidget(self.contract_table, 1)

        tabs.addTab(contract_tab, '合同到期提醒')

        budget_tab = QWidget()
        budget_layout = QVBoxLayout(budget_tab)
        budget_layout.setContentsMargins(0, 0, 0, 0)
        budget_layout.setSpacing(8)

        budget_toolbar = QFrame()
        budget_toolbar.setStyleSheet('background: white; border-radius: 8px;')
        bt_layout = QHBoxLayout(budget_toolbar)
        bt_layout.setContentsMargins(12, 10, 12, 10)
        bt_layout.setSpacing(10)

        bt_layout.addWidget(QLabel('年份：'))
        self.budget_year_combo = QComboBox()
        current_year = datetime.now().year
        for y in range(current_year + 1, current_year - 5, -1):
            self.budget_year_combo.addItem(str(y), y)
        self.budget_year_combo.setCurrentText(str(current_year))
        self.budget_year_combo.setFixedWidth(100)
        self.budget_year_combo.currentIndexChanged.connect(self.load_budget_progress)
        bt_layout.addWidget(self.budget_year_combo)

        bt_layout.addWidget(QLabel('区域：'))
        self.budget_area_filter = QComboBox()
        self.budget_area_filter.addItem('全部区域', '')
        areas = PlantManager.get_areas()
        for a in areas:
            self.budget_area_filter.addItem(a, a)
        self.budget_area_filter.setFixedWidth(120)
        self.budget_area_filter.currentIndexChanged.connect(self.load_budget_progress)
        bt_layout.addWidget(self.budget_area_filter)

        bt_layout.addStretch()

        btn_set_budget = QPushButton('💰 设置预算')
        btn_set_budget.setProperty('class', 'primary')
        btn_set_budget.clicked.connect(self.open_budget_dialog)
        bt_layout.addWidget(btn_set_budget)

        budget_layout.addWidget(budget_toolbar)

        self.budget_table = QTableWidget(0, 7)
        self.budget_table.setHorizontalHeaderLabels(['费用类型', '区域', '预算金额', '已使用', '剩余', '进度', '状态'])
        self.budget_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.budget_table.verticalHeader().setVisible(False)
        self.budget_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.budget_table.setSelectionBehavior(QTableWidget.SelectRows)
        budget_layout.addWidget(self.budget_table, 1)

        tabs.addTab(budget_tab, '📊 预算管理')

        layout.addWidget(tabs, 1)

    def refresh(self):
        self.load_expenses()
        self.load_contract_alerts()
        self.load_budget_progress()
        self.update_summary()

    def update_summary(self):
        total = ExpenseManager.get_total_expense()
        self.total_label.setText(f'💰 累计费用：¥ {total:,.2f}')

        year = self.year_filter.currentData()
        if year:
            year_expenses = ExpenseManager.get_all(year=year)
            year_total = sum(e['amount'] for e in year_expenses)
            self.year_label.setText(f'📅 {year}年：¥ {year_total:,.2f}')

        contracts = ExpenseManager.get_contracts_soon(30)
        self.contract_alert_label.setText(f'🔔 即将到期合同：{len(contracts)} 份')

        current_year = datetime.now().year
        progress_list = ExpenseManager.get_budget_progress(current_year)
        overspent = [p for p in progress_list if p['progress_pct'] > 100]
        if overspent:
            self.budget_alert_label.setVisible(True)
            self.budget_alert_label.setText(f'⚠️ 预算超支：{len(overspent)} 项')
        else:
            self.budget_alert_label.setVisible(False)

    def load_expenses(self):
        expense_type = self.type_filter.currentText()
        if expense_type == '全部类型':
            expense_type = None

        year = self.year_filter.currentData()
        if isinstance(year, int):
            pass
        else:
            year = None

        expenses = ExpenseManager.get_all(expense_type=expense_type, year=year)

        type_icons = {
            '采购': '🛒', '补植': '🌱', '养护': '🧹',
            '农药': '🧴', '肥料': '🌾', '设备': '🔧', '其他': '📦'
        }

        self.table.setRowCount(0)
        for e in expenses:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(e['id'])))
            icon = type_icons.get(e['expense_type'], '📦')
            self.table.setItem(row, 1, QTableWidgetItem(f"{icon} {e['expense_type']}"))

            amount_item = QTableWidgetItem(f"¥ {e['amount']:,.2f}")
            amount_item.setForeground(QColor('#e6a23c'))
            self.table.setItem(row, 2, amount_item)

            self.table.setItem(row, 3, QTableWidgetItem(e['expense_date'] or ''))
            self.table.setItem(row, 4, QTableWidgetItem(e['vendor'] or ''))
            self.table.setItem(row, 5, QTableWidgetItem(e['contract_end_date'] or '-'))
            self.table.setItem(row, 6, QTableWidgetItem(e.get('plant_name', '') or ''))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            btn_edit = QPushButton('编辑')
            btn_edit.setFixedHeight(26)
            btn_edit.clicked.connect(lambda checked, eid=e['id']: self.edit_expense(eid))
            btn_layout.addWidget(btn_edit)

            btn_delete = QPushButton('删除')
            btn_delete.setFixedHeight(26)
            btn_delete.setStyleSheet('color: #f56c6c;')
            btn_delete.clicked.connect(lambda checked, eid=e['id']: self.delete_expense(eid))
            btn_layout.addWidget(btn_delete)

            self.table.setCellWidget(row, 7, btn_widget)

    def load_contract_alerts(self):
        contracts = ExpenseManager.get_contracts_soon(30)
        self.contract_table.setRowCount(0)

        today = datetime.now().date()

        for c in contracts:
            row = self.contract_table.rowCount()
            self.contract_table.insertRow(row)

            self.contract_table.setItem(row, 0, QTableWidgetItem(c['vendor'] or ''))
            self.contract_table.setItem(row, 1, QTableWidgetItem(c['expense_type'] or ''))
            amount_item = QTableWidgetItem(f"¥ {c['amount']:,.2f}")
            amount_item.setForeground(QColor('#e6a23c'))
            self.contract_table.setItem(row, 2, amount_item)

            date_item = QTableWidgetItem(c['contract_end_date'] or '')
            date_item.setForeground(QColor('#f56c6c'))
            self.contract_table.setItem(row, 3, date_item)

            try:
                end_date = datetime.strptime(c['contract_end_date'], '%Y-%m-%d').date()
                days = (end_date - today).days
                days_text = f'{days} 天'
                if days <= 7:
                    days_text += ' ⚠️'
            except:
                days_text = '-'
            days_item = QTableWidgetItem(days_text)
            days_item.setForeground(QColor('#f56c6c'))
            self.contract_table.setItem(row, 4, days_item)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_edit = QPushButton('续签')
            btn_edit.setFixedHeight(26)
            btn_edit.setStyleSheet('color: #67c23a;')
            btn_edit.clicked.connect(lambda checked, eid=c['id']: self.renew_contract(eid))
            btn_layout.addWidget(btn_edit)
            self.contract_table.setCellWidget(row, 5, btn_widget)

    def add_expense(self):
        dlg = ExpenseDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            ExpenseManager.add(data)
            QMessageBox.information(self, '成功', '添加成功')
            self.refresh()

    def edit_expense(self, expense_id):
        expenses = ExpenseManager.get_all()
        expense = None
        for e in expenses:
            if e['id'] == expense_id:
                expense = e
                break
        if not expense:
            return

        dlg = ExpenseDialog(self, expense)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            ExpenseManager.update(expense_id, data)
            QMessageBox.information(self, '成功', '保存成功')
            self.refresh()

    def edit_from_table(self, index):
        row = index.row()
        expense_id = int(self.table.item(row, 0).text())
        self.edit_expense(expense_id)

    def delete_expense(self, expense_id):
        reply = QMessageBox.question(self, '确认', '确定要删除这条记录吗？')
        if reply == QMessageBox.Yes:
            ExpenseManager.delete(expense_id)
            self.refresh()

    def renew_contract(self, expense_id):
        expenses = ExpenseManager.get_all()
        expense = None
        for e in expenses:
            if e['id'] == expense_id:
                expense = e
                break
        if not expense:
            return

        dlg = ExpenseDialog(self, expense)
        dlg.setWindowTitle('续签合同')
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            ExpenseManager.update(expense_id, data)
            QMessageBox.information(self, '成功', '合同已续签')
            self.refresh()

    def load_budget_progress(self):
        year = self.budget_year_combo.currentData()
        if not year:
            return
        area_name = self.budget_area_filter.currentData()
        area_name = area_name if area_name else None
        progress_list = ExpenseManager.get_budget_progress(year, area_name=area_name)

        self.budget_table.setRowCount(0)
        for p in progress_list:
            row = self.budget_table.rowCount()
            self.budget_table.insertRow(row)

            self.budget_table.setItem(row, 0, QTableWidgetItem(p['category']))
            self.budget_table.setItem(row, 1, QTableWidgetItem(p['area_name'] or '全局'))

            budget_item = QTableWidgetItem(f"¥ {p['budget_amount']:,.2f}")
            budget_item.setForeground(QColor('#409eff'))
            self.budget_table.setItem(row, 2, budget_item)

            spent_item = QTableWidgetItem(f"¥ {p['spent_amount']:,.2f}")
            spent_item.setForeground(QColor('#e6a23c'))
            self.budget_table.setItem(row, 3, spent_item)

            remaining = p['budget_amount'] - p['spent_amount']
            remaining_item = QTableWidgetItem(f"¥ {remaining:,.2f}")
            if remaining < 0:
                remaining_item.setForeground(QColor('#f56c6c'))
            else:
                remaining_item.setForeground(QColor('#67c23a'))
            self.budget_table.setItem(row, 4, remaining_item)

            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            pct = int(min(p['progress_pct'], 100))
            progress_bar.setValue(pct)
            if p['progress_pct'] < 80:
                progress_bar.setStyleSheet(
                    'QProgressBar::chunk{background:#67c23a;border-radius:4px;}'
                    'QProgressBar{border:1px solid #dcdfe6;border-radius:4px;text-align:center;}')
            elif p['progress_pct'] <= 100:
                progress_bar.setStyleSheet(
                    'QProgressBar::chunk{background:#e6a23c;border-radius:4px;}'
                    'QProgressBar{border:1px solid #dcdfe6;border-radius:4px;text-align:center;}')
            else:
                progress_bar.setStyleSheet(
                    'QProgressBar::chunk{background:#f56c6c;border-radius:4px;}'
                    'QProgressBar{border:1px solid #dcdfe6;border-radius:4px;text-align:center;}')
            self.budget_table.setCellWidget(row, 5, progress_bar)

            if p['progress_pct'] < 80:
                status_item = QTableWidgetItem('正常')
                status_item.setForeground(QColor('#67c23a'))
            elif p['progress_pct'] <= 100:
                status_item = QTableWidgetItem('接近预算')
                status_item.setForeground(QColor('#e6a23c'))
            else:
                status_item = QTableWidgetItem('⚠️ 超支')
                status_item.setForeground(QColor('#f56c6c'))
            self.budget_table.setItem(row, 6, status_item)

    def open_budget_dialog(self):
        dlg = BudgetDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            ExpenseManager.set_budget(
                data['year'], data['category'],
                data['area_name'], data['amount'], data['notes']
            )
            QMessageBox.information(self, '成功', '预算设置成功')
            self.load_budget_progress()
            self.update_summary()
