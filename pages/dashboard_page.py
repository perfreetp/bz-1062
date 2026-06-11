from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QTableWidget, QTableWidgetItem,
                               QHeaderView, QProgressBar)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from database import PlantManager, MaintenanceManager, ExpenseManager


class StatCard(QFrame):
    def __init__(self, title, value, subtitle='', icon='', color='#409eff'):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f'''
            StatCard {{
                background: white;
                border-radius: 10px;
                border: none;
            }}
        ''')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f'font-size: 36px;')
        icon_label.setFixedWidth(60)
        icon_label.setAlignment(Qt.AlignCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet('color: #909399; font-size: 13px;')

        value_label = QLabel(str(value))
        value_label.setStyleSheet(f'color: {color}; font-size: 28px; font-weight: 700;')
        value_label.setFont(QFont('Microsoft YaHei', 22, QFont.Bold))

        info_layout.addWidget(title_label)
        info_layout.addWidget(value_label)
        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet('color: #c0c4cc; font-size: 12px;')
            info_layout.addWidget(sub_label)

        layout.addWidget(icon_label)
        layout.addLayout(info_layout, 1)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        stats_layout = QGridLayout()
        stats_layout.setSpacing(12)

        self.card_area = StatCard('绿化面积', '0 ㎡', '园区总绿化覆盖面积', '🌿', '#67c23a')
        self.card_plants = StatCard('植株数量', '0 株', '登记在册的植物总数', '🌳', '#409eff')
        self.card_normal = StatCard('正常植株', '0 株', '生长状态良好', '✅', '#67c23a')
        self.card_warn = StatCard('需关注', '0 株', '需要重点养护', '⚠️', '#e6a23c')

        stats_layout.addWidget(self.card_area, 0, 0)
        stats_layout.addWidget(self.card_plants, 0, 1)
        stats_layout.addWidget(self.card_normal, 0, 2)
        stats_layout.addWidget(self.card_warn, 0, 3)

        layout.addLayout(stats_layout)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(16)

        left_frame = QFrame()
        left_frame.setStyleSheet('background: white; border-radius: 10px;')
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(16, 14, 16, 14)

        title1 = QLabel('📅 今日待办养护')
        title1.setStyleSheet('font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 8px;')
        left_layout.addWidget(title1)

        self.today_table = QTableWidget(0, 4)
        self.today_table.setHorizontalHeaderLabels(['类型', '植株', '区域', '责任人'])
        self.today_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.today_table.verticalHeader().setVisible(False)
        self.today_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.today_table.setSelectionBehavior(QTableWidget.SelectRows)
        left_layout.addWidget(self.today_table, 1)

        right_frame = QFrame()
        right_frame.setStyleSheet('background: white; border-radius: 10px;')
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(16, 14, 16, 14)

        title2 = QLabel('📊 植株状态分布')
        title2.setStyleSheet('font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 8px;')
        right_layout.addWidget(title2)

        self.status_table = QTableWidget(0, 3)
        self.status_table.setHorizontalHeaderLabels(['状态', '数量', '占比'])
        self.status_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.status_table.verticalHeader().setVisible(False)
        self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.status_table, 1)

        mid_layout.addWidget(left_frame, 1)
        mid_layout.addWidget(right_frame, 1)

        layout.addLayout(mid_layout, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)

        area_frame = QFrame()
        area_frame.setStyleSheet('background: white; border-radius: 10px;')
        area_layout = QVBoxLayout(area_frame)
        area_layout.setContentsMargins(16, 14, 16, 14)
        title3 = QLabel('📍 各区域植株分布')
        title3.setStyleSheet('font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 8px;')
        area_layout.addWidget(title3)
        self.area_table = QTableWidget(0, 3)
        self.area_table.setHorizontalHeaderLabels(['区域', '品种数', '植株数'])
        self.area_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.area_table.verticalHeader().setVisible(False)
        self.area_table.setEditTriggers(QTableWidget.NoEditTriggers)
        area_layout.addWidget(self.area_table, 1)

        expense_frame = QFrame()
        expense_frame.setStyleSheet('background: white; border-radius: 10px;')
        exp_layout = QVBoxLayout(expense_frame)
        exp_layout.setContentsMargins(16, 14, 16, 14)
        title4 = QLabel('💰 费用概览')
        title4.setStyleSheet('font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 8px;')
        exp_layout.addWidget(title4)

        self.total_exp_label = QLabel('累计费用：¥ 0.00')
        self.total_exp_label.setStyleSheet('font-size: 20px; font-weight: 700; color: #e6a23c; padding: 12px 0;')
        exp_layout.addWidget(self.total_exp_label)

        contract_title = QLabel('🔔 即将到期合同')
        contract_title.setStyleSheet('font-size: 13px; font-weight: 600; color: #f56c6c; margin-top: 8px;')
        exp_layout.addWidget(contract_title)

        self.contract_table = QTableWidget(0, 3)
        self.contract_table.setHorizontalHeaderLabels(['供应商', '金额', '到期日'])
        self.contract_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.contract_table.verticalHeader().setVisible(False)
        self.contract_table.setEditTriggers(QTableWidget.NoEditTriggers)
        exp_layout.addWidget(self.contract_table, 1)

        bottom_layout.addWidget(area_frame, 1)
        bottom_layout.addWidget(expense_frame, 1)

        layout.addLayout(bottom_layout, 1)

        self.refresh()

    def refresh(self):
        stats = PlantManager.get_statistics()

        self.card_area.findChild(QLabel, '', Qt.FindDirectChildrenOnly)
        self._update_card_value(self.card_area, f'{stats["total_area"]} ㎡')
        self._update_card_value(self.card_plants, f'{stats["total_quantity"]} 株')
        self._update_card_value(self.card_normal, f'{stats["normal_count"]} 株')
        self._update_card_value(self.card_warn, f'{stats["warn_count"] + stats["sick_count"]} 株')

        self._load_status_table(stats)
        self._load_area_table(stats)
        self._load_today_tasks()
        self._load_expense_info()

    def _update_card_value(self, card, value):
        labels = card.findChildren(QLabel)
        if len(labels) >= 3:
            labels[2].setText(value)

    def _load_status_table(self, stats):
        total = stats['total_plants'] if stats['total_plants'] > 0 else 1
        statuses = [
            ('正常', stats['normal_count'], '#67c23a'),
            ('需关注', stats['warn_count'], '#e6a23c'),
            ('病虫害', stats['sick_count'], '#f56c6c'),
            ('枯死', stats['dead_count'], '#909399'),
        ]
        self.status_table.setRowCount(0)
        for name, count, color in statuses:
            row = self.status_table.rowCount()
            self.status_table.insertRow(row)
            item_name = QTableWidgetItem(name)
            item_name.setForeground(QColor(color))
            self.status_table.setItem(row, 0, item_name)
            self.status_table.setItem(row, 1, QTableWidgetItem(str(count)))
            pct = round(count / total * 100, 1)
            self.status_table.setItem(row, 2, QTableWidgetItem(f'{pct}%'))

    def _load_area_table(self, stats):
        self.area_table.setRowCount(0)
        for area in stats['by_area']:
            row = self.area_table.rowCount()
            self.area_table.insertRow(row)
            name = area['area_name'] if area['area_name'] else '未分类'
            self.area_table.setItem(row, 0, QTableWidgetItem(name))
            self.area_table.setItem(row, 1, QTableWidgetItem(str(area['cnt'])))
            self.area_table.setItem(row, 2, QTableWidgetItem(str(area['qty'])))

    def _load_today_tasks(self):
        tasks = MaintenanceManager.get_today_tasks()
        self.today_table.setRowCount(0)
        type_icons = {'浇水': '💧', '施肥': '🌾', '修剪': '✂️', '打药': '🧴', '其他': '📝'}
        for task in tasks:
            row = self.today_table.rowCount()
            self.today_table.insertRow(row)
            icon = type_icons.get(task['plan_type'], '📝')
            self.today_table.setItem(row, 0, QTableWidgetItem(f"{icon} {task['plan_type']}"))
            self.today_table.setItem(row, 1, QTableWidgetItem(task['plant_name'] or ''))
            self.today_table.setItem(row, 2, QTableWidgetItem(task['area_name'] or ''))
            self.today_table.setItem(row, 3, QTableWidgetItem(task['responsible'] or ''))

    def _load_expense_info(self):
        total = ExpenseManager.get_total_expense()
        self.total_exp_label.setText(f'累计费用：¥ {total:,.2f}')

        contracts = ExpenseManager.get_contracts_soon(30)
        self.contract_table.setRowCount(0)
        for c in contracts:
            row = self.contract_table.rowCount()
            self.contract_table.insertRow(row)
            self.contract_table.setItem(row, 0, QTableWidgetItem(c['vendor'] or ''))
            self.contract_table.setItem(row, 1, QTableWidgetItem(f"¥ {c['amount']:,.2f}"))
            item_date = QTableWidgetItem(c['contract_end_date'] or '')
            item_date.setForeground(QColor('#f56c6c'))
            self.contract_table.setItem(row, 2, item_date)
