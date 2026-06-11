from datetime import datetime, timedelta
import calendar

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QLineEdit, QSpinBox, QDateEdit, QTextEdit,
                               QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
                               QTabWidget, QListWidget, QListWidgetItem, QSplitter,
                               QScrollArea, QSizePolicy, QInputDialog)
from PySide6.QtCore import Qt, QDate, QMimeData, Signal
from PySide6.QtGui import QColor, QDrag, QPixmap, QPainter
from PySide6.QtWidgets import QApplication

from database import MaintenanceManager, PlantManager


class DraggableTaskLabel(QLabel):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        type_icons = {'浇水': '💧', '施肥': '🌾', '修剪': '✂️', '打药': '🧴', '除草': '🌿', '其他': '📝'}
        icon = type_icons.get(task['plan_type'], '📝')
        self.setText(f"{icon} {task['plant_name'] or '未知'}")
        self.setStyleSheet('''
            QLabel {
                background: #ecf5ff;
                border: 1px solid #b3d8ff;
                border-radius: 4px;
                padding: 4px 8px;
                margin: 2px;
                font-size: 12px;
            }
            QLabel:hover {
                background: #d9ecff;
            }
        ''')
        self.setCursor(Qt.PointingHandCursor)
        self.setWordWrap(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.position() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.task['id']))
        drag.setMimeData(mime_data)

        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)

        drag.exec(Qt.MoveAction)


class CalendarCell(QFrame):
    task_dropped = Signal(int, str)

    def __init__(self, date_str, parent=None):
        super().__init__(parent)
        self.date_str = date_str
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setStyleSheet('''
            CalendarCell {
                background: white;
                border: 1px solid #ebeef5;
            }
            CalendarCell:hover {
                background: #f5f7fa;
            }
        ''')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.date_label = QLabel(date_str.split('-')[2] if len(date_str) > 0 else '')
        self.date_label.setStyleSheet('font-weight: 600; color: #606266; font-size: 13px;')
        layout.addWidget(self.date_label)

        self.tasks_container = QVBoxLayout()
        self.tasks_container.setSpacing(2)
        layout.addLayout(self.tasks_container, 1)

        today = datetime.now().strftime('%Y-%m-%d')
        if date_str == today:
            self.setStyleSheet('''
                CalendarCell {
                    background: #f0f9eb;
                    border: 2px solid #67c23a;
                }
            ''')
            self.date_label.setStyleSheet('font-weight: 700; color: #67c23a; font-size: 14px;')
        elif date_str < today:
            self.date_label.setStyleSheet('font-weight: 600; color: #c0c4cc; font-size: 13px;')

    def add_task(self, task):
        task_label = DraggableTaskLabel(task)
        task_label.mouseDoubleClickEvent = lambda e, pid=task['id']: self.edit_task(pid)
        self.tasks_container.addWidget(task_label)

    def clear_tasks(self):
        while self.tasks_container.count():
            child = self.tasks_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def edit_task(self, plan_id):
        parent = self.window()
        if hasattr(parent, 'edit_plan'):
            parent.edit_plan(plan_id)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet('''
                CalendarCell {
                    background: #ecf5ff;
                    border: 2px solid #409eff;
                }
            ''')

    def dragLeaveEvent(self, event):
        today = datetime.now().strftime('%Y-%m-%d')
        if self.date_str == today:
            self.setStyleSheet('''
                CalendarCell {
                    background: #f0f9eb;
                    border: 2px solid #67c23a;
                }
            ''')
        else:
            self.setStyleSheet('''
                CalendarCell {
                    background: white;
                    border: 1px solid #ebeef5;
                }
            ''')

    def dropEvent(self, event):
        if event.mimeData().hasText():
            plan_id = int(event.mimeData().text())
            self.task_dropped.emit(plan_id, self.date_str)
            event.acceptProposedAction()
        self.dragLeaveEvent(None)


class PlanDialog(QDialog):
    def __init__(self, parent=None, plan=None):
        super().__init__(parent)
        self.plan = plan
        self.setWindowTitle('养护计划')
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.plant_combo = QComboBox()
        plants = PlantManager.get_all()
        self.plant_map = {}
        for p in plants:
            label = f"{p['name']} ({p['species'] or '未知品种'})"
            self.plant_combo.addItem(label, p['id'])
            self.plant_map[p['id']] = p
        form.addRow('植株：', self.plant_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(['浇水', '施肥', '修剪', '打药', '除草', '其他'])
        form.addRow('类型：', self.type_combo)

        self.frequency_spin = QSpinBox()
        self.frequency_spin.setRange(1, 365)
        self.frequency_spin.setSuffix(' 天/次')
        self.frequency_spin.setValue(7)
        form.addRow('频率：', self.frequency_spin)

        self.last_date = QDateEdit()
        self.last_date.setDisplayFormat('yyyy-MM-dd')
        self.last_date.setCalendarPopup(True)
        self.last_date.setDate(QDate.currentDate())
        form.addRow('上次完成：', self.last_date)

        self.next_date = QDateEdit()
        self.next_date.setDisplayFormat('yyyy-MM-dd')
        self.next_date.setCalendarPopup(True)
        self.next_date.setDate(QDate.currentDate().addDays(7))
        form.addRow('下次计划：', self.next_date)

        self.responsible_input = QLineEdit()
        form.addRow('责任人：', self.responsible_input)

        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        form.addRow('备注：', self.notes_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if plan:
            self.load_data(plan)

        self.frequency_spin.valueChanged.connect(self.update_next_date)
        self.last_date.dateChanged.connect(self.update_next_date)

    def update_next_date(self):
        days = self.frequency_spin.value()
        next_d = self.last_date.date().addDays(days)
        self.next_date.setDate(next_d)

    def load_data(self, plan):
        if plan.get('plant_id'):
            idx = self.plant_combo.findData(plan['plant_id'])
            if idx >= 0:
                self.plant_combo.setCurrentIndex(idx)
        idx = self.type_combo.findText(plan.get('plan_type', ''))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        if plan.get('frequency_days'):
            self.frequency_spin.setValue(plan['frequency_days'])
        if plan.get('last_date'):
            d = QDate.fromString(plan['last_date'], 'yyyy-MM-dd')
            if d.isValid():
                self.last_date.setDate(d)
        if plan.get('next_date'):
            d = QDate.fromString(plan['next_date'], 'yyyy-MM-dd')
            if d.isValid():
                self.next_date.setDate(d)
        self.responsible_input.setText(plan.get('responsible', ''))
        self.notes_input.setPlainText(plan.get('notes', ''))

    def get_data(self):
        return {
            'plant_id': self.plant_combo.currentData(),
            'plan_type': self.type_combo.currentText(),
            'frequency_days': self.frequency_spin.value(),
            'last_date': self.last_date.date().toString('yyyy-MM-dd'),
            'next_date': self.next_date.date().toString('yyyy-MM-dd'),
            'responsible': self.responsible_input.text().strip(),
            'notes': self.notes_input.toPlainText().strip(),
        }


class MaintenancePage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        self.type_filter = QComboBox()
        self.type_filter.addItem('全部类型')
        self.type_filter.addItems(['浇水', '施肥', '修剪', '打药', '除草', '其他'])
        self.type_filter.setFixedWidth(120)
        self.type_filter.currentTextChanged.connect(self.refresh)
        tb_layout.addWidget(self.type_filter)

        tb_layout.addStretch()

        btn_add = QPushButton('➕ 新建计划')
        btn_add.setProperty('class', 'primary')
        btn_add.clicked.connect(self.add_plan)
        tb_layout.addWidget(btn_add)

        btn_dispatch = QPushButton('📋 生成今日派工单')
        btn_dispatch.setProperty('class', 'success')
        btn_dispatch.clicked.connect(self.generate_dispatch)
        tb_layout.addWidget(btn_dispatch)

        layout.addWidget(toolbar)

        tabs = QTabWidget()

        today_tab = QWidget()
        today_layout = QVBoxLayout(today_tab)
        today_layout.setContentsMargins(0, 0, 0, 0)

        today_header = QFrame()
        today_header.setStyleSheet('background: #f0f9eb; border-radius: 6px; padding: 10px;')
        th_layout = QHBoxLayout(today_header)
        th_layout.setContentsMargins(12, 8, 12, 8)
        today_date = datetime.now().strftime('%Y年%m月%d日')
        self.today_count_label = QLabel(f'📅 今日待办（{today_date}）：0 项')
        self.today_count_label.setStyleSheet('font-weight: 600; color: #67c23a;')
        th_layout.addWidget(self.today_count_label)
        th_layout.addStretch()

        btn_complete_all = QPushButton('✅ 全部完成')
        btn_complete_all.setProperty('class', 'success')
        btn_complete_all.clicked.connect(self.complete_all_today)
        th_layout.addWidget(btn_complete_all)

        today_layout.addWidget(today_header)

        self.today_table = QTableWidget(0, 6)
        self.today_table.setHorizontalHeaderLabels(['类型', '植株', '区域', '责任人', '计划日期', '操作'])
        self.today_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.today_table.verticalHeader().setVisible(False)
        self.today_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.today_table.setSelectionBehavior(QTableWidget.SelectRows)
        today_layout.addWidget(self.today_table, 1)

        tabs.addTab(today_tab, '今日待办')

        plans_tab = QWidget()
        plans_layout = QVBoxLayout(plans_tab)
        plans_layout.setContentsMargins(0, 0, 0, 0)

        self.plans_table = QTableWidget(0, 8)
        self.plans_table.setHorizontalHeaderLabels(['ID', '类型', '植株', '频率(天)', '上次完成', '下次计划', '责任人', '操作'])
        self.plans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.plans_table.verticalHeader().setVisible(False)
        self.plans_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.plans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plans_table.doubleClicked.connect(self.edit_plan_from_table)
        plans_layout.addWidget(self.plans_table)

        tabs.addTab(plans_tab, '养护计划')

        week_tab = QWidget()
        week_layout = QVBoxLayout(week_tab)
        week_layout.setContentsMargins(0, 0, 0, 0)

        week_header = QFrame()
        week_header.setStyleSheet('background: #ecf5ff; border-radius: 6px; padding: 10px;')
        wh_layout = QHBoxLayout(week_header)
        wh_layout.setContentsMargins(12, 8, 12, 8)
        self.week_count_label = QLabel('📆 本周待办：0 项')
        self.week_count_label.setStyleSheet('font-weight: 600; color: #409eff;')
        wh_layout.addWidget(self.week_count_label)
        wh_layout.addStretch()
        week_layout.addWidget(week_header)

        self.week_table = QTableWidget(0, 6)
        self.week_table.setHorizontalHeaderLabels(['计划日期', '类型', '植株', '区域', '责任人', '操作'])
        self.week_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.week_table.verticalHeader().setVisible(False)
        self.week_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.week_table.setSelectionBehavior(QTableWidget.SelectRows)
        week_layout.addWidget(self.week_table, 1)

        tabs.addTab(week_tab, '本周安排')

        month_tab = QWidget()
        month_layout = QVBoxLayout(month_tab)
        month_layout.setContentsMargins(0, 0, 0, 0)

        month_header = QFrame()
        month_header.setStyleSheet('background: #fdf6ec; border-radius: 6px; padding: 10px;')
        mh_layout = QHBoxLayout(month_header)
        mh_layout.setContentsMargins(12, 8, 12, 8)

        btn_prev_month = QPushButton('◀ 上月')
        btn_prev_month.clicked.connect(self.prev_month)
        mh_layout.addWidget(btn_prev_month)

        self.month_label = QLabel()
        self.month_label.setStyleSheet('font-weight: 700; color: #e6a23c; font-size: 16px;')
        self.month_label.setAlignment(Qt.AlignCenter)
        mh_layout.addWidget(self.month_label, 1)

        btn_next_month = QPushButton('下月 ▶')
        btn_next_month.clicked.connect(self.next_month)
        mh_layout.addWidget(btn_next_month)

        btn_today = QPushButton('今天')
        btn_today.setProperty('class', 'primary')
        btn_today.clicked.connect(self.go_to_today)
        mh_layout.addWidget(btn_today)

        month_layout.addWidget(month_header)

        weekday_header = QFrame()
        weekday_layout = QHBoxLayout(weekday_header)
        weekday_layout.setContentsMargins(0, 0, 0, 0)
        weekday_layout.setSpacing(1)
        weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
        for wd in weekdays:
            lbl = QLabel(wd)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet('font-weight: 600; color: #909399; padding: 8px; background: #f5f7fa;')
            weekday_layout.addWidget(lbl)
        month_layout.addWidget(weekday_header)

        self.calendar_grid = QVBoxLayout()
        self.calendar_grid.setSpacing(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.calendar_container = QWidget()
        self.calendar_container.setLayout(self.calendar_grid)
        scroll.setWidget(self.calendar_container)
        month_layout.addWidget(scroll, 1)

        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.month_cells = {}

        tabs.addTab(month_tab, '月历视图')

        records_tab = QWidget()
        records_layout = QVBoxLayout(records_tab)
        records_layout.setContentsMargins(0, 0, 0, 0)

        self.records_table = QTableWidget(0, 6)
        self.records_table.setHorizontalHeaderLabels(['日期', '类型', '植株', '操作人', '结果', '备注'])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.verticalHeader().setVisible(False)
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        records_layout.addWidget(self.records_table)

        tabs.addTab(records_tab, '养护记录')

        layout.addWidget(tabs, 1)

    def refresh(self):
        self.load_today_tasks()
        self.load_plans()
        self.load_week_tasks()
        self.load_records()
        self.load_month_calendar()

    def prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.load_month_calendar()

    def next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.load_month_calendar()

    def go_to_today(self):
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.load_month_calendar()

    def load_month_calendar(self):
        if not hasattr(self, 'calendar_grid') or self.calendar_grid is None:
            return

        self.month_label.setText(f'{self.current_year}年{self.current_month}月')

        while self.calendar_grid.count():
            item = self.calendar_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        self.month_cells = {}

        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdatescalendar(self.current_year, self.current_month)

        end_day = calendar.monthrange(self.current_year, self.current_month)[1]
        all_tasks = MaintenanceManager.get_all_tasks_within_range(
            f'{self.current_year}-{self.current_month:02d}-01',
            f'{self.current_year}-{self.current_month:02d}-{end_day}'
        )

        tasks_by_date = {}
        for task in all_tasks:
            date_key = task['next_date']
            if date_key not in tasks_by_date:
                tasks_by_date[date_key] = []
            tasks_by_date[date_key].append(task)

        for week in weeks:
            week_frame = QFrame()
            week_layout = QHBoxLayout(week_frame)
            week_layout.setContentsMargins(0, 0, 0, 0)
            week_layout.setSpacing(1)

            for day in week:
                date_str = day.strftime('%Y-%m-%d')
                if day.month == self.current_month:
                    cell = CalendarCell(date_str)
                else:
                    cell = CalendarCell(date_str)
                    cell.setStyleSheet('''
                        CalendarCell {
                            background: #fafafa;
                            border: 1px solid #ebeef5;
                        }
                    ''')
                    cell.date_label.setStyleSheet('font-weight: 600; color: #c0c4cc; font-size: 13px;')

                cell.task_dropped.connect(self.on_task_dropped)
                self.month_cells[date_str] = cell

                if date_str in tasks_by_date:
                    for task in tasks_by_date[date_str]:
                        cell.add_task(task)

                week_layout.addWidget(cell)

            self.calendar_grid.addWidget(week_frame)

    def on_task_dropped(self, plan_id, new_date):
        plan = MaintenanceManager.get_plan(plan_id)
        if not plan:
            return

        reply = QMessageBox.question(self, '确认改期',
                                     f'确定要将任务改期到 {new_date} 吗？')
        if reply != QMessageBox.Yes:
            return

        try:
            MaintenanceManager.update_plan_date(plan_id, new_date)
            QMessageBox.information(self, '成功', '任务已改期')
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'改期失败：{str(e)}')

    def load_today_tasks(self):
        tasks = MaintenanceManager.get_today_tasks()
        type_icons = {'浇水': '💧', '施肥': '🌾', '修剪': '✂️', '打药': '🧴', '除草': '🌿', '其他': '📝'}

        self.today_count_label.setText(
            f'📅 今日待办（{datetime.now().strftime("%Y年%m月%d日")}）：{len(tasks)} 项'
        )

        self.today_table.setRowCount(0)
        for task in tasks:
            row = self.today_table.rowCount()
            self.today_table.insertRow(row)

            icon = type_icons.get(task['plan_type'], '📝')
            self.today_table.setItem(row, 0, QTableWidgetItem(f"{icon} {task['plan_type']}"))
            self.today_table.setItem(row, 1, QTableWidgetItem(task['plant_name'] or ''))
            self.today_table.setItem(row, 2, QTableWidgetItem(task['area_name'] or ''))
            self.today_table.setItem(row, 3, QTableWidgetItem(task['responsible'] or ''))
            self.today_table.setItem(row, 4, QTableWidgetItem(task['next_date'] or ''))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_complete = QPushButton('完成')
            btn_complete.setProperty('class', 'success')
            btn_complete.setFixedHeight(28)
            btn_complete.clicked.connect(lambda checked, pid=task['id']: self.complete_task(pid))
            btn_layout.addWidget(btn_complete)
            self.today_table.setCellWidget(row, 5, btn_widget)

    def load_plans(self):
        plan_type = self.type_filter.currentText()
        if plan_type == '全部类型':
            plan_type = None

        plans = MaintenanceManager.get_plans(plan_type=plan_type)
        type_icons = {'浇水': '💧', '施肥': '🌾', '修剪': '✂️', '打药': '🧴', '除草': '🌿', '其他': '📝'}

        self.plans_table.setRowCount(0)
        for plan in plans:
            row = self.plans_table.rowCount()
            self.plans_table.insertRow(row)

            self.plans_table.setItem(row, 0, QTableWidgetItem(str(plan['id'])))
            icon = type_icons.get(plan['plan_type'], '📝')
            self.plans_table.setItem(row, 1, QTableWidgetItem(f"{icon} {plan['plan_type']}"))
            self.plans_table.setItem(row, 2, QTableWidgetItem(plan['plant_name'] or ''))
            self.plans_table.setItem(row, 3, QTableWidgetItem(str(plan['frequency_days'])))
            self.plans_table.setItem(row, 4, QTableWidgetItem(plan['last_date'] or '-'))
            next_item = QTableWidgetItem(plan['next_date'] or '')
            if plan['next_date']:
                try:
                    next_d = datetime.strptime(plan['next_date'], '%Y-%m-%d')
                    if next_d < datetime.now():
                        next_item.setForeground(QColor('#f56c6c'))
                except:
                    pass
            self.plans_table.setItem(row, 5, next_item)
            self.plans_table.setItem(row, 6, QTableWidgetItem(plan['responsible'] or ''))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            btn_edit = QPushButton('编辑')
            btn_edit.setFixedHeight(26)
            btn_edit.clicked.connect(lambda checked, pid=plan['id']: self.edit_plan(pid))
            btn_layout.addWidget(btn_edit)

            btn_delete = QPushButton('删除')
            btn_delete.setFixedHeight(26)
            btn_delete.setStyleSheet('color: #f56c6c;')
            btn_delete.clicked.connect(lambda checked, pid=plan['id']: self.delete_plan(pid))
            btn_layout.addWidget(btn_delete)

            self.plans_table.setCellWidget(row, 7, btn_widget)

    def load_week_tasks(self):
        tasks = MaintenanceManager.get_week_tasks()
        type_icons = {'浇水': '💧', '施肥': '🌾', '修剪': '✂️', '打药': '🧴', '除草': '🌿', '其他': '📝'}

        self.week_count_label.setText(f'📆 本周待办：{len(tasks)} 项')

        self.week_table.setRowCount(0)
        for task in tasks:
            row = self.week_table.rowCount()
            self.week_table.insertRow(row)

            date_item = QTableWidgetItem(task['next_date'] or '')
            try:
                task_date = datetime.strptime(task['next_date'], '%Y-%m-%d')
                if task_date.date() == datetime.now().date():
                    date_item.setForeground(QColor('#f56c6c'))
            except:
                pass
            self.week_table.setItem(row, 0, date_item)

            icon = type_icons.get(task['plan_type'], '📝')
            self.week_table.setItem(row, 1, QTableWidgetItem(f"{icon} {task['plan_type']}"))
            self.week_table.setItem(row, 2, QTableWidgetItem(task['plant_name'] or ''))
            self.week_table.setItem(row, 3, QTableWidgetItem(task['area_name'] or ''))
            self.week_table.setItem(row, 4, QTableWidgetItem(task['responsible'] or ''))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_complete = QPushButton('完成')
            btn_complete.setProperty('class', 'success')
            btn_complete.setFixedHeight(26)
            btn_complete.clicked.connect(lambda checked, pid=task['id']: self.complete_task(pid))
            btn_layout.addWidget(btn_complete)
            self.week_table.setCellWidget(row, 5, btn_widget)

    def load_records(self):
        records = MaintenanceManager.get_records(limit=100)
        self.records_table.setRowCount(0)
        for r in records:
            row = self.records_table.rowCount()
            self.records_table.insertRow(row)
            self.records_table.setItem(row, 0, QTableWidgetItem(r['record_date'] or ''))
            self.records_table.setItem(row, 1, QTableWidgetItem(r['record_type'] or ''))
            self.records_table.setItem(row, 2, QTableWidgetItem(r['plant_name'] or ''))
            self.records_table.setItem(row, 3, QTableWidgetItem(r['operator'] or ''))

            result_item = QTableWidgetItem(r['result'] or '')
            if r['result'] == '已完成':
                result_item.setForeground(QColor('#67c23a'))
            self.records_table.setItem(row, 4, result_item)

            self.records_table.setItem(row, 5, QTableWidgetItem(r['notes'] or ''))

    def add_plan(self):
        dlg = PlanDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            MaintenanceManager.add_plan(data)
            QMessageBox.information(self, '成功', '计划创建成功')
            self.refresh()

    def edit_plan(self, plan_id):
        plans = MaintenanceManager.get_plans()
        plan = None
        for p in plans:
            if p['id'] == plan_id:
                plan = p
                break
        if not plan:
            return

        dlg = PlanDialog(self, plan)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            MaintenanceManager.update_plan(plan_id, data)
            QMessageBox.information(self, '成功', '保存成功')
            self.refresh()

    def edit_plan_from_table(self, index):
        row = index.row()
        plan_id = int(self.plans_table.item(row, 0).text())
        self.edit_plan(plan_id)

    def delete_plan(self, plan_id):
        reply = QMessageBox.question(self, '确认', '确定要删除这个养护计划吗？')
        if reply == QMessageBox.Yes:
            MaintenanceManager.delete_plan(plan_id)
            self.refresh()

    def complete_task(self, plan_id):
        MaintenanceManager.complete_task(plan_id)
        QMessageBox.information(self, '成功', '已完成，已更新下次计划日期')
        self.refresh()

    def complete_all_today(self):
        tasks = MaintenanceManager.get_today_tasks()
        if not tasks:
            QMessageBox.information(self, '提示', '今日没有待办任务')
            return

        reply = QMessageBox.question(self, '确认', f'确定要将今日 {len(tasks)} 项任务全部标记为完成吗？')
        if reply == QMessageBox.Yes:
            for task in tasks:
                MaintenanceManager.complete_task(task['id'])
            QMessageBox.information(self, '成功', f'已完成 {len(tasks)} 项任务')
            self.refresh()

    def generate_dispatch(self):
        tasks = MaintenanceManager.get_today_tasks()
        if not tasks:
            QMessageBox.information(self, '提示', '今日没有待办任务，无需生成派工单')
            return

        group_by, ok = QInputDialog.getItem(
            self, '选择分组方式', '请选择派工单分组方式：',
            ['按责任人', '按任务类型'], 0, False
        )
        if not ok:
            return

        msg = f'===== 今日养护派工单 =====\n'
        msg += f'日期：{datetime.now().strftime("%Y年%m月%d日")}\n'
        msg += f'共 {len(tasks)} 项任务\n'
        msg += f'分组方式：{group_by}\n\n'

        if group_by == '按责任人':
            by_responsible = {}
            unassigned = []
            for task in tasks:
                resp = task.get('responsible', '').strip() or '未指定'
                if resp == '未指定':
                    unassigned.append(task)
                else:
                    if resp not in by_responsible:
                        by_responsible[resp] = []
                    by_responsible[resp].append(task)

            for resp, items in sorted(by_responsible.items()):
                msg += f'━━━ {resp} ({len(items)}项) ━━━\n'
                for item in items:
                    msg += f'  □ {item["plan_type"]} - {item["plant_name"] or "未知"}（{item["area_name"] or "未分区"}）\n'
                msg += '\n'

            if unassigned:
                msg += f'━━━ 未指定责任人 ({len(unassigned)}项) ━━━\n'
                for item in unassigned:
                    msg += f'  □ {item["plan_type"]} - {item["plant_name"] or "未知"}（{item["area_name"] or "未分区"}）\n'
                msg += '\n'
        else:
            by_type = {}
            for task in tasks:
                t = task['plan_type']
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(task)

            for t, items in by_type.items():
                msg += f'【{t}】{len(items)}项\n'
                for item in items:
                    msg += f'  • {item["plant_name"] or "未知"}（{item["area_name"] or "未分区"}）'
                    if item['responsible']:
                        msg += f' - {item["responsible"]}'
                    msg += '\n'
                msg += '\n'

        msg += '=========================='

        dlg = QDialog(self)
        dlg.setWindowTitle('今日派工单')
        dlg.setMinimumSize(500, 450)
        layout = QVBoxLayout(dlg)

        text_edit = QTextEdit()
        text_edit.setPlainText(msg)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_copy = QPushButton('📋 复制')
        btn_copy.clicked.connect(lambda: self.copy_dispatch(msg))
        btn_layout.addWidget(btn_copy)

        btn_print = QPushButton('🖨️ 打印')
        btn_print.clicked.connect(lambda: self.print_dispatch(msg))
        btn_layout.addWidget(btn_print)

        btn_close = QPushButton('关闭')
        btn_close.clicked.connect(dlg.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)
        dlg.exec()

    def copy_dispatch(self, content):
        clipboard = QApplication.clipboard()
        clipboard.setText(content)
        QMessageBox.information(self, '成功', '派工单已复制到剪贴板')

    def print_dispatch(self, content):
        QMessageBox.information(self, '提示', '打印功能已触发\n\n' + content[:100] + '...')
