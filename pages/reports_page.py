import os
import csv
from datetime import datetime, timedelta

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QLineEdit, QTabWidget, QMessageBox,
                               QFileDialog, QListWidget, QListWidgetItem, QSpinBox,
                               QProgressBar, QGroupBox, QTextEdit, QDialog, QFormLayout,
                               QDateEdit, QCheckBox, QInputDialog)
from PySide6.QtCore import Qt, QDate, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QPen, QBrush, QIcon
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from database import PlantManager, MaintenanceManager, BackupManager, ExpenseManager


class LabelPrintDialog(QDialog):
    def __init__(self, plants, parent=None):
        super().__init__(parent)
        self.plants = plants
        self.setWindowTitle('打印标签')
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        settings = QGroupBox('标签设置')
        set_layout = QHBoxLayout(settings)

        set_layout.addWidget(QLabel('每行数量：'))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 6)
        self.cols_spin.setValue(3)
        set_layout.addWidget(self.cols_spin)

        set_layout.addWidget(QLabel('标签大小：'))
        self.size_combo = QComboBox()
        self.size_combo.addItems(['小', '中', '大'])
        self.size_combo.setCurrentIndex(1)
        set_layout.addWidget(self.size_combo)

        set_layout.addStretch()
        layout.addWidget(settings)

        preview_group = QGroupBox('预览')
        preview_layout = QVBoxLayout(preview_group)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(300)
        self.preview.setStyleSheet('background: white; border: 1px solid #ebeef5; border-radius: 6px;')
        preview_layout.addWidget(self.preview)
        layout.addWidget(preview_group, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_export = QPushButton('导出图片')
        btn_export.clicked.connect(self.export_labels)
        btn_layout.addWidget(btn_export)

        btn_print = QPushButton('🖨️ 打印')
        btn_print.setProperty('class', 'primary')
        btn_print.clicked.connect(self.print_labels)
        btn_layout.addWidget(btn_print)

        btn_close = QPushButton('关闭')
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        self.cols_spin.valueChanged.connect(self.update_preview)
        self.size_combo.currentIndexChanged.connect(self.update_preview)
        self.label_pixmap = None

    def showEvent(self, event):
        super().showEvent(event)
        self.update_preview()

    def update_preview(self):
        cols = self.cols_spin.value()
        size_map = {'小': (120, 60), '中': (160, 80), '大': (200, 100)}
        label_w, label_h = size_map[self.size_combo.currentText()]

        rows = (len(self.plants) + cols - 1) // cols
        spacing = 10
        margin = 20

        total_w = cols * label_w + (cols - 1) * spacing + margin * 2
        total_h = rows * label_h + (rows - 1) * spacing + margin * 2

        pixmap = QPixmap(max(total_w, 500), max(total_h, 300))
        pixmap.fill(QColor('#ffffff'))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        for i, plant in enumerate(self.plants):
            row = i // cols
            col = i % cols
            x = margin + col * (label_w + spacing)
            y = margin + row * (label_h + spacing)

            painter.setPen(QPen(QColor('#dcdfe6'), 1))
            painter.setBrush(QBrush(QColor('#f5f7fa')))
            painter.drawRoundedRect(x, y, label_w, label_h, 6, 6)

            painter.setPen(QColor('#303133'))
            painter.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
            painter.drawText(x + 8, y + 22, plant['name'])

            painter.setPen(QColor('#606266'))
            painter.setFont(QFont('Microsoft YaHei', 9))
            painter.drawText(x + 8, y + 38, plant.get('species', '') or '')

            painter.setPen(QColor('#909399'))
            painter.setFont(QFont('Microsoft YaHei', 8))
            painter.drawText(x + 8, y + 52, f"编号：{plant['id']:04d}")

            if label_h > 70:
                painter.drawText(x + 8, y + 66, f"区域：{plant.get('area_name', '') or ''}")

        painter.end()
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.label_pixmap = pixmap

    def export_labels(self):
        file_path, _ = QFileDialog.getSaveFileName(self, '导出标签图片', '植株标签.png', 'PNG图片 (*.png)')
        if file_path:
            self.label_pixmap.save(file_path)
            QMessageBox.information(self, '成功', '标签图片已导出')

    def print_labels(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            rect = painter.viewport()
            scaled = self.label_pixmap.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (rect.width() - scaled.width()) / 2
            y = (rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled)
            painter.end()
            QMessageBox.information(self, '成功', '打印已发送')


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        tabs = QTabWidget()

        stat_tab = QWidget()
        stat_layout = QVBoxLayout(stat_tab)
        stat_layout.setContentsMargins(0, 0, 0, 0)
        self._init_stat_tab(stat_layout)
        tabs.addTab(stat_tab, '📊 数据统计')

        biz_tab = QWidget()
        biz_layout = QVBoxLayout(biz_tab)
        biz_layout.setContentsMargins(0, 0, 0, 0)
        self._init_business_tab(biz_layout)
        tabs.addTab(biz_tab, '📈 经营分析')

        abnormal_tab = QWidget()
        abn_layout = QVBoxLayout(abnormal_tab)
        abn_layout.setContentsMargins(0, 0, 0, 0)
        self._init_abnormal_tab(abn_layout)
        tabs.addTab(abnormal_tab, '⚠️ 异常筛选')

        label_tab = QWidget()
        label_layout = QVBoxLayout(label_tab)
        label_layout.setContentsMargins(0, 0, 0, 0)
        self._init_label_tab(label_layout)
        tabs.addTab(label_tab, '🏷️ 标签打印')

        accept_tab = QWidget()
        accept_layout = QVBoxLayout(accept_tab)
        accept_layout.setContentsMargins(0, 0, 0, 0)
        self._init_accept_tab(accept_layout)
        tabs.addTab(accept_tab, '📋 验收表')

        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)
        backup_layout.setContentsMargins(0, 0, 0, 0)
        self._init_backup_tab(backup_layout)
        tabs.addTab(backup_tab, '💾 备份恢复')

        recycle_tab = QWidget()
        recycle_layout = QVBoxLayout(recycle_tab)
        recycle_layout.setContentsMargins(0, 0, 0, 0)
        self._init_recycle_tab(recycle_layout)
        tabs.addTab(recycle_tab, '🗑️ 回收站')

        layout.addWidget(tabs)

    def _init_stat_tab(self, layout):
        filter_bar = QFrame()
        filter_bar.setStyleSheet('background: white; border-radius: 8px;')
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(12, 10, 12, 10)
        fb_layout.setSpacing(10)

        fb_layout.addWidget(QLabel('筛选区域：'))
        self.survival_area_combo = QComboBox()
        self.survival_area_combo.addItem('全部区域', None)
        self.survival_area_combo.setFixedWidth(160)
        self.survival_area_combo.currentIndexChanged.connect(self.load_statistics)
        fb_layout.addWidget(self.survival_area_combo)

        fb_layout.addStretch()

        btn_export_survival = QPushButton('📤 导出成活率明细报表')
        btn_export_survival.setProperty('class', 'warning')
        btn_export_survival.clicked.connect(self.export_survival_report)
        fb_layout.addWidget(btn_export_survival)

        btn_export_report = QPushButton('📤 导出完整报表')
        btn_export_report.setProperty('class', 'primary')
        btn_export_report.clicked.connect(self.export_full_report)
        fb_layout.addWidget(btn_export_report)

        layout.addWidget(filter_bar)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.survival_card = QFrame()
        self.survival_card.setStyleSheet('background: white; border-radius: 10px;')
        sc_layout = QVBoxLayout(self.survival_card)
        sc_layout.setContentsMargins(16, 14, 16, 14)
        sc_title = QLabel('🌱 月度植株状态与成活率')
        sc_title.setStyleSheet('font-weight: 600; color: #303133;')
        sc_layout.addWidget(sc_title)
        self.survival_table = QTableWidget(0, 8)
        self.survival_table.setHorizontalHeaderLabels(['月份', '期末在养', '异常', '枯死', '补植', '期末总数', '成活率', '趋势'])
        self.survival_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.survival_table.verticalHeader().setVisible(False)
        self.survival_table.setEditTriggers(QTableWidget.NoEditTriggers)
        sc_layout.addWidget(self.survival_table, 1)
        cards_layout.addWidget(self.survival_card, 3)

        self.expense_card = QFrame()
        self.expense_card.setStyleSheet('background: white; border-radius: 10px;')
        ec_layout = QVBoxLayout(self.expense_card)
        ec_layout.setContentsMargins(16, 14, 16, 14)
        ec_title = QLabel('💰 月度费用统计')
        ec_title.setStyleSheet('font-weight: 600; color: #303133;')
        ec_layout.addWidget(ec_title)
        self.expense_table = QTableWidget(0, 3)
        self.expense_table.setHorizontalHeaderLabels(['月份', '类型', '金额'])
        self.expense_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.expense_table.verticalHeader().setVisible(False)
        self.expense_table.setEditTriggers(QTableWidget.NoEditTriggers)
        ec_layout.addWidget(self.expense_table, 1)
        cards_layout.addWidget(self.expense_card, 2)

        layout.addLayout(cards_layout, 1)

        summary_bar = QFrame()
        summary_bar.setStyleSheet('background: white; border-radius: 8px;')
        sb_layout = QHBoxLayout(summary_bar)
        sb_layout.setContentsMargins(16, 12, 16, 12)
        sb_layout.setSpacing(32)

        self.sum_plants = QLabel('植株总数：0')
        self.sum_plants.setStyleSheet('font-size: 14px; color: #606266;')
        sb_layout.addWidget(self.sum_plants)

        self.sum_area = QLabel('绿化面积：0 ㎡')
        self.sum_area.setStyleSheet('font-size: 14px; color: #606266;')
        sb_layout.addWidget(self.sum_area)

        self.sum_amount = QLabel('累计费用：¥ 0')
        self.sum_amount.setStyleSheet('font-size: 14px; color: #e6a23c;')
        sb_layout.addWidget(self.sum_amount)

        self.sum_normal = QLabel('正常：0')
        self.sum_normal.setStyleSheet('font-size: 14px; color: #67c23a;')
        sb_layout.addWidget(self.sum_normal)

        self.sum_abnormal = QLabel('异常：0')
        self.sum_abnormal.setStyleSheet('font-size: 14px; color: #f56c6c;')
        sb_layout.addWidget(self.sum_abnormal)

        sb_layout.addStretch()

        layout.addWidget(summary_bar)

    def _init_abnormal_tab(self, layout):
        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel('异常类型：'))
        self.abn_type_combo = QComboBox()
        self.abn_type_combo.addItems(['全部异常', '需关注', '病虫害', '枯死', '无养护计划', '超期未养护'])
        self.abn_type_combo.setFixedWidth(140)
        self.abn_type_combo.currentTextChanged.connect(self.load_abnormal_data)
        tb_layout.addWidget(self.abn_type_combo)

        tb_layout.addStretch()

        btn_export = QPushButton('📤 导出异常清单')
        btn_export.clicked.connect(self.export_abnormal)
        tb_layout.addWidget(btn_export)

        layout.addWidget(toolbar)

        self.abn_table = QTableWidget(0, 7)
        self.abn_table.setHorizontalHeaderLabels(['ID', '名称', '品种', '区域', '责任人', '状态', '备注'])
        self.abn_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.abn_table.verticalHeader().setVisible(False)
        self.abn_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.abn_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.abn_table, 1)

    def _init_business_tab(self, layout):
        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel('筛选区域：'))
        self.biz_area_combo = QComboBox()
        self.biz_area_combo.addItem('全部区域', None)
        self.biz_area_combo.setFixedWidth(160)
        self.biz_area_combo.currentIndexChanged.connect(self.load_business_analysis)
        tb_layout.addWidget(self.biz_area_combo)

        tb_layout.addStretch()

        btn_export = QPushButton('📤 导出经营分析报表')
        btn_export.setProperty('class', 'primary')
        btn_export.clicked.connect(self.export_business_report)
        tb_layout.addWidget(btn_export)

        layout.addWidget(toolbar)

        self.biz_table = QTableWidget(0, 10)
        self.biz_table.setHorizontalHeaderLabels(
            ['月份', '养护费用', '补植费用', '采购费用', '其他费用', '费用合计', '在养数', '异常数', '枯死数', '成活率'])
        self.biz_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.biz_table.verticalHeader().setVisible(False)
        self.biz_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.biz_table, 1)

    def _init_label_tab(self, layout):
        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel('选择植株：'))
        self.label_area_combo = QComboBox()
        self.label_area_combo.addItem('全部区域')
        self.label_area_combo.setFixedWidth(140)
        tb_layout.addWidget(self.label_area_combo)

        tb_layout.addStretch()

        btn_select_all = QPushButton('全选')
        btn_select_all.clicked.connect(self.select_all_labels)
        tb_layout.addWidget(btn_select_all)

        btn_print = QPushButton('🏷️ 打印标签')
        btn_print.setProperty('class', 'primary')
        btn_print.clicked.connect(self.print_labels)
        tb_layout.addWidget(btn_print)

        layout.addWidget(toolbar)

        self.label_table = QTableWidget(0, 6)
        self.label_table.setHorizontalHeaderLabels(['选择', 'ID', '名称', '品种', '区域', '责任人'])
        self.label_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.label_table.setColumnWidth(0, 50)
        self.label_table.verticalHeader().setVisible(False)
        self.label_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.label_table, 1)

    def _init_accept_tab(self, layout):
        form_bar = QFrame()
        form_bar.setStyleSheet('background: white; border-radius: 8px;')
        fb_layout = QHBoxLayout(form_bar)
        fb_layout.setContentsMargins(12, 10, 12, 10)
        fb_layout.setSpacing(16)

        fb_layout.addWidget(QLabel('验收日期：'))
        self.accept_date = QDateEdit()
        self.accept_date.setDisplayFormat('yyyy-MM-dd')
        self.accept_date.setCalendarPopup(True)
        self.accept_date.setDate(QDate.currentDate())
        fb_layout.addWidget(self.accept_date)

        fb_layout.addWidget(QLabel('验收人：'))
        self.accept_person = QLineEdit()
        self.accept_person.setFixedWidth(120)
        self.accept_person.setPlaceholderText('请输入')
        fb_layout.addWidget(self.accept_person)

        fb_layout.addStretch()

        btn_generate = QPushButton('📝 生成验收表')
        btn_generate.setProperty('class', 'primary')
        btn_generate.clicked.connect(self.generate_acceptance)
        fb_layout.addWidget(btn_generate)

        btn_export = QPushButton('📤 导出CSV')
        btn_export.clicked.connect(self.export_acceptance)
        fb_layout.addWidget(btn_export)

        layout.addWidget(form_bar)

        self.accept_table = QTableWidget(0, 8)
        self.accept_table.setHorizontalHeaderLabels(['序号', '名称', '品种', '规格', '数量', '区域', '状态', '验收结果'])
        self.accept_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.accept_table.verticalHeader().setVisible(False)
        layout.addWidget(self.accept_table, 1)

    def _init_backup_tab(self, layout):
        action_bar = QFrame()
        action_bar.setStyleSheet('background: white; border-radius: 8px;')
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(12, 10, 12, 10)
        ab_layout.setSpacing(10)

        btn_create = QPushButton('➕ 新建备份')
        btn_create.setProperty('class', 'primary')
        btn_create.clicked.connect(self.create_backup)
        ab_layout.addWidget(btn_create)

        ab_layout.addStretch()

        btn_restore_file = QPushButton('📥 从文件恢复')
        btn_restore_file.clicked.connect(self.restore_from_file)
        ab_layout.addWidget(btn_restore_file)

        layout.addWidget(action_bar)

        self.backup_table = QTableWidget(0, 5)
        self.backup_table.setHorizontalHeaderLabels(['ID', '备份时间', '记录数', '备注', '操作'])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backup_table.verticalHeader().setVisible(False)
        self.backup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.backup_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.backup_table, 1)

        hint = QLabel('💡 提示：备份文件保存在 data/backups 目录下，建议定期复制到安全位置')
        hint.setStyleSheet('color: #909399; font-size: 12px;')
        layout.addWidget(hint)

    def _init_recycle_tab(self, layout):
        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel('回收站中的植株记录，可恢复或永久删除'))
        tb_layout.addStretch()

        btn_refresh = QPushButton('🔄 刷新')
        btn_refresh.clicked.connect(self.load_recycle_bin)
        tb_layout.addWidget(btn_refresh)

        layout.addWidget(toolbar)

        self.recycle_table = QTableWidget(0, 7)
        self.recycle_table.setHorizontalHeaderLabels(['ID', '名称', '品种', '区域', '删除时间', '操作', ''])
        self.recycle_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recycle_table.verticalHeader().setVisible(False)
        self.recycle_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recycle_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.recycle_table, 1)

    def refresh(self):
        self.load_statistics()
        self.load_business_analysis()
        self.load_abnormal_data()
        self.load_label_list()
        self.load_backup_list()
        self.load_recycle_bin()
        self.generate_acceptance()

    def load_statistics(self):
        area_filter = self.survival_area_combo.currentData()

        all_plants = PlantManager.get_all()
        if area_filter:
            all_plants = [p for p in all_plants if p.get('area_name') == area_filter]

        total_plants = len(all_plants)
        total_area = sum(p.get('area', 0) for p in all_plants)
        normal_count = sum(1 for p in all_plants if p.get('status') == '正常')
        abnormal_count = total_plants - normal_count

        self.sum_plants.setText(f'植株总数：{total_plants} 个品种')
        self.sum_area.setText(f'绿化面积：{total_area:.2f} ㎡')
        self.sum_normal.setText(f'正常：{normal_count}')
        self.sum_abnormal.setText(f'异常：{abnormal_count}')

        total_exp = ExpenseManager.get_total_expense()
        self.sum_amount.setText(f'累计费用：¥ {total_exp:,.2f}')

        areas = PlantManager.get_areas()
        current_area = self.survival_area_combo.currentData()
        self.survival_area_combo.blockSignals(True)
        self.survival_area_combo.clear()
        self.survival_area_combo.addItem('全部区域', None)
        for a in sorted(areas):
            self.survival_area_combo.addItem(a, a)
        if current_area:
            idx = self.survival_area_combo.findData(current_area)
            if idx >= 0:
                self.survival_area_combo.setCurrentIndex(idx)
        self.survival_area_combo.blockSignals(False)

        monthly_data = self._get_monthly_status(all_plants)
        self.survival_table.setRowCount(0)

        prev_rate = None
        for month, counts in sorted(monthly_data.items()):
            row = self.survival_table.rowCount()
            self.survival_table.insertRow(row)

            total = counts['total']
            survival_rate = round(counts['normal'] / total * 100, 1) if total > 0 else 100

            self.survival_table.setItem(row, 0, QTableWidgetItem(month))

            normal_item = QTableWidgetItem(str(counts['normal']))
            normal_item.setForeground(QColor('#67c23a'))
            self.survival_table.setItem(row, 1, normal_item)

            abnormal_item = QTableWidgetItem(str(counts['abnormal']))
            abnormal_item.setForeground(QColor('#e6a23c'))
            self.survival_table.setItem(row, 2, abnormal_item)

            dead_item = QTableWidgetItem(str(counts['dead']))
            dead_item.setForeground(QColor('#909399'))
            self.survival_table.setItem(row, 3, dead_item)

            replanted_item = QTableWidgetItem(str(counts['replanted']))
            replanted_item.setForeground(QColor('#409eff'))
            self.survival_table.setItem(row, 4, replanted_item)

            self.survival_table.setItem(row, 5, QTableWidgetItem(str(total)))

            rate_item = QTableWidgetItem(f'{survival_rate}%')
            if survival_rate >= 90:
                rate_item.setForeground(QColor('#67c23a'))
            elif survival_rate >= 70:
                rate_item.setForeground(QColor('#e6a23c'))
            else:
                rate_item.setForeground(QColor('#f56c6c'))
            self.survival_table.setItem(row, 6, rate_item)

            if prev_rate is not None:
                if survival_rate > prev_rate:
                    trend_text = '↑'
                    trend_color = QColor('#67c23a')
                elif survival_rate < prev_rate:
                    trend_text = '↓'
                    trend_color = QColor('#f56c6c')
                else:
                    trend_text = '→'
                    trend_color = QColor('#909399')
            else:
                trend_text = '-'
                trend_color = QColor('#909399')

            trend_item = QTableWidgetItem(trend_text)
            trend_item.setForeground(trend_color)
            trend_item.setTextAlignment(Qt.AlignCenter)
            self.survival_table.setItem(row, 7, trend_item)

            prev_rate = survival_rate

        self.current_survival_data = monthly_data
        self.current_survival_plants = all_plants

        expenses = ExpenseManager.get_monthly_expenses()
        self.expense_table.setRowCount(0)
        for e in expenses:
            row = self.expense_table.rowCount()
            self.expense_table.insertRow(row)
            self.expense_table.setItem(row, 0, QTableWidgetItem(e['month']))
            self.expense_table.setItem(row, 1, QTableWidgetItem(e['expense_type']))
            amount_item = QTableWidgetItem(f"¥ {e['total']:,.2f}")
            amount_item.setForeground(QColor('#e6a23c'))
            self.expense_table.setItem(row, 2, amount_item)

    def _get_monthly_status(self, plants):
        monthly = {}
        now = datetime.now()

        months = []
        for i in range(11, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            months.append((year, month))

        for year, month in months:
            month_key = f'{year:04d}-{month:02d}'
            if month == 12:
                next_month_start = f'{year + 1:04d}-01-01'
            else:
                next_month_start = f'{year:04d}-{month + 1:02d}-01'

            existing = []
            replanted = 0
            for p in plants:
                created_str = p.get('created_at', '') or p.get('updated_at', '')
                if not created_str:
                    continue
                if created_str[:10] < next_month_start:
                    existing.append(p)
                if created_str[:7] == month_key:
                    replanted += 1

            normal = sum(1 for p in existing if p.get('status') == '正常')
            abnormal = sum(1 for p in existing if p.get('status') in ('需关注', '病虫害'))
            dead = sum(1 for p in existing if p.get('status') == '枯死')
            total = len(existing)

            monthly[month_key] = {
                'normal': normal,
                'abnormal': abnormal,
                'dead': dead,
                'replanted': replanted,
                'total': total,
            }

        return monthly

    def export_survival_report(self):
        area_filter = self.survival_area_combo.currentText()
        file_path, _ = QFileDialog.getSaveFileName(self, '导出成活率明细报表',
                                                    f'成活率报表_{area_filter}_{datetime.now().strftime("%Y%m%d")}.csv',
                                                    'CSV文件 (*.csv)')
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['月度植株状态与成活率报表'])
                writer.writerow([f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow([f'筛选区域：{area_filter}'])
                writer.writerow([])

                writer.writerow(['一、月度汇总'])
                writer.writerow(['月份', '期末在养', '异常', '枯死', '补植', '期末总数', '成活率', '趋势'])

                prev_rate = None
                for month, counts in sorted(self.current_survival_data.items()):
                    total = counts['total']
                    rate = round(counts['normal'] / total * 100, 1) if total > 0 else 100

                    if prev_rate is not None:
                        if rate > prev_rate:
                            trend = '↑'
                        elif rate < prev_rate:
                            trend = '↓'
                        else:
                            trend = '→'
                    else:
                        trend = '-'

                    writer.writerow([
                        month, counts['normal'], counts['abnormal'],
                        counts['dead'], counts['replanted'], total, f'{rate}%', trend
                    ])
                    prev_rate = rate
                writer.writerow([])

                writer.writerow(['二、植株明细'])
                writer.writerow(['ID', '名称', '品种', '规格', '数量', '区域', '责任人', '状态', '种植日期', '更新时间', '备注'])

                for p in self.current_survival_plants:
                    writer.writerow([
                        p['id'], p['name'], p.get('species', ''), p.get('spec', ''),
                        p.get('quantity', 1), p.get('area_name', ''),
                        p.get('responsible', ''), p.get('status', ''),
                        p.get('plant_date', ''), p.get('updated_at', ''),
                        p.get('notes', '')
                    ])

            QMessageBox.information(self, '成功', '成活率明细报表已导出')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败：{str(e)}')

    def load_business_analysis(self):
        area_filter = self.biz_area_combo.currentData()

        areas = PlantManager.get_areas()
        current_area = self.biz_area_combo.currentData()
        self.biz_area_combo.blockSignals(True)
        self.biz_area_combo.clear()
        self.biz_area_combo.addItem('全部区域', None)
        for a in sorted(areas):
            self.biz_area_combo.addItem(a, a)
        if current_area:
            idx = self.biz_area_combo.findData(current_area)
            if idx >= 0:
                self.biz_area_combo.setCurrentIndex(idx)
        self.biz_area_combo.blockSignals(False)

        all_plants = PlantManager.get_all()
        if area_filter:
            filtered_plants = [p for p in all_plants if p.get('area_name') == area_filter]
        else:
            filtered_plants = all_plants

        monthly_survival = self._get_monthly_status(filtered_plants)

        expenses = ExpenseManager.get_monthly_expenses_by_type(area_name=area_filter)
        expense_by_month = {}
        for e in expenses:
            month = e['month']
            if month not in expense_by_month:
                expense_by_month[month] = {'养护费用': 0, '补植费用': 0, '采购费用': 0, '其他费用': 0}
            etype = e['expense_type']
            amount = e['total']
            if '养护' in etype:
                expense_by_month[month]['养护费用'] += amount
            elif '补植' in etype:
                expense_by_month[month]['补植费用'] += amount
            elif '采购' in etype:
                expense_by_month[month]['采购费用'] += amount
            else:
                expense_by_month[month]['其他费用'] += amount

        self.biz_table.setRowCount(0)

        for month in sorted(monthly_survival.keys()):
            counts = monthly_survival[month]
            row = self.biz_table.rowCount()
            self.biz_table.insertRow(row)

            self.biz_table.setItem(row, 0, QTableWidgetItem(month))

            exp = expense_by_month.get(month, {'养护费用': 0, '补植费用': 0, '采购费用': 0, '其他费用': 0})

            for col, key in enumerate(['养护费用', '补植费用', '采购费用', '其他费用'], 1):
                item = QTableWidgetItem(f"¥ {exp[key]:,.2f}")
                item.setForeground(QColor('#e6a23c'))
                self.biz_table.setItem(row, col, item)

            total_exp = exp['养护费用'] + exp['补植费用'] + exp['采购费用'] + exp['其他费用']
            total_item = QTableWidgetItem(f"¥ {total_exp:,.2f}")
            total_item.setForeground(QColor('#f56c6c'))
            self.biz_table.setItem(row, 5, total_item)

            normal_item = QTableWidgetItem(str(counts['normal']))
            normal_item.setForeground(QColor('#67c23a'))
            self.biz_table.setItem(row, 6, normal_item)

            abnormal_item = QTableWidgetItem(str(counts['abnormal']))
            abnormal_item.setForeground(QColor('#e6a23c'))
            self.biz_table.setItem(row, 7, abnormal_item)

            dead_item = QTableWidgetItem(str(counts['dead']))
            dead_item.setForeground(QColor('#909399'))
            self.biz_table.setItem(row, 8, dead_item)

            rate = round(counts['normal'] / counts['total'] * 100, 1) if counts['total'] > 0 else 100
            rate_item = QTableWidgetItem(f'{rate}%')
            if rate >= 90:
                rate_item.setForeground(QColor('#67c23a'))
            elif rate >= 70:
                rate_item.setForeground(QColor('#e6a23c'))
            else:
                rate_item.setForeground(QColor('#f56c6c'))
            self.biz_table.setItem(row, 9, rate_item)

        self.current_biz_data = {
            'monthly_survival': monthly_survival,
            'expense_by_month': expense_by_month,
            'plants': filtered_plants,
        }

    def export_business_report(self):
        area_filter = self.biz_area_combo.currentText()
        file_path, _ = QFileDialog.getSaveFileName(self, '导出经营分析报表',
                                                    f'经营分析报表_{area_filter}_{datetime.now().strftime("%Y%m%d")}.csv',
                                                    'CSV文件 (*.csv)')
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['经营分析报表'])
                writer.writerow([f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow([f'筛选区域：{area_filter}'])
                writer.writerow([])

                writer.writerow(['一、月度汇总'])
                writer.writerow(['月份', '养护费用', '补植费用', '采购费用', '其他费用', '费用合计', '在养数', '异常数', '枯死数', '成活率'])

                biz_data = self.current_biz_data
                for month in sorted(biz_data['monthly_survival'].keys()):
                    counts = biz_data['monthly_survival'][month]
                    exp = biz_data['expense_by_month'].get(month, {'养护费用': 0, '补植费用': 0, '采购费用': 0, '其他费用': 0})
                    total_exp = exp['养护费用'] + exp['补植费用'] + exp['采购费用'] + exp['其他费用']
                    rate = round(counts['normal'] / counts['total'] * 100, 1) if counts['total'] > 0 else 100
                    writer.writerow([
                        month,
                        f"{exp['养护费用']:.2f}",
                        f"{exp['补植费用']:.2f}",
                        f"{exp['采购费用']:.2f}",
                        f"{exp['其他费用']:.2f}",
                        f"{total_exp:.2f}",
                        counts['normal'],
                        counts['abnormal'],
                        counts['dead'],
                        f'{rate}%'
                    ])

                writer.writerow([])
                writer.writerow(['二、植株明细'])
                writer.writerow(['ID', '名称', '品种', '区域', '责任人', '状态', '种植日期', '备注'])

                for p in biz_data['plants']:
                    writer.writerow([
                        p['id'], p['name'], p.get('species', ''),
                        p.get('area_name', ''), p.get('responsible', ''),
                        p.get('status', ''), p.get('plant_date', ''),
                        p.get('notes', '')
                    ])

            QMessageBox.information(self, '成功', '经营分析报表已导出')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败：{str(e)}')

    def load_abnormal_data(self):
        abn_type = self.abn_type_combo.currentText()
        plants = PlantManager.get_all()

        abnormal = []
        if abn_type == '全部异常':
            abnormal = [p for p in plants if p['status'] != '正常']
        elif abn_type in ['需关注', '病虫害', '枯死']:
            abnormal = [p for p in plants if p['status'] == abn_type]
        elif abn_type == '无养护计划':
            plans = MaintenanceManager.get_plans()
            plan_plant_ids = set(p['plant_id'] for p in plans if p['plant_id'])
            abnormal = [p for p in plants if p['id'] not in plan_plant_ids]
        elif abn_type == '超期未养护':
            tasks = MaintenanceManager.get_today_tasks()
            for task in tasks:
                for p in plants:
                    if p['id'] == task['plant_id']:
                        abnormal.append(p)
                        break

        status_colors = {
            '正常': QColor('#67c23a'),
            '需关注': QColor('#e6a23c'),
            '病虫害': QColor('#f56c6c'),
            '枯死': QColor('#909399'),
        }

        self.abn_table.setRowCount(0)
        for p in abnormal:
            row = self.abn_table.rowCount()
            self.abn_table.insertRow(row)
            self.abn_table.setItem(row, 0, QTableWidgetItem(str(p['id'])))
            self.abn_table.setItem(row, 1, QTableWidgetItem(p['name']))
            self.abn_table.setItem(row, 2, QTableWidgetItem(p.get('species', '') or ''))
            self.abn_table.setItem(row, 3, QTableWidgetItem(p.get('area_name', '') or ''))
            self.abn_table.setItem(row, 4, QTableWidgetItem(p.get('responsible', '') or ''))

            status_item = QTableWidgetItem(p.get('status', ''))
            color = status_colors.get(p.get('status', ''), QColor('#606266'))
            status_item.setForeground(color)
            self.abn_table.setItem(row, 5, status_item)

            self.abn_table.setItem(row, 6, QTableWidgetItem(p.get('notes', '') or ''))

    def load_label_list(self):
        plants = PlantManager.get_all()
        self.label_table.setRowCount(0)

        areas = set()
        for p in plants:
            if p.get('area_name'):
                areas.add(p['area_name'])

        current = self.label_area_combo.currentText()
        self.label_area_combo.blockSignals(True)
        self.label_area_combo.clear()
        self.label_area_combo.addItem('全部区域')
        for a in sorted(areas):
            self.label_area_combo.addItem(a)
        if current:
            idx = self.label_area_combo.findText(current)
            if idx >= 0:
                self.label_area_combo.setCurrentIndex(idx)
        self.label_area_combo.blockSignals(False)

        area_filter = self.label_area_combo.currentText()
        if area_filter != '全部区域':
            plants = [p for p in plants if p.get('area_name') == area_filter]

        for p in plants:
            row = self.label_table.rowCount()
            self.label_table.insertRow(row)

            cb_item = QTableWidgetItem()
            cb_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            cb_item.setCheckState(Qt.Checked)
            cb_item.setData(Qt.UserRole, p['id'])
            self.label_table.setItem(row, 0, cb_item)

            self.label_table.setItem(row, 1, QTableWidgetItem(str(p['id'])))
            self.label_table.setItem(row, 2, QTableWidgetItem(p['name']))
            self.label_table.setItem(row, 3, QTableWidgetItem(p.get('species', '') or ''))
            self.label_table.setItem(row, 4, QTableWidgetItem(p.get('area_name', '') or ''))
            self.label_table.setItem(row, 5, QTableWidgetItem(p.get('responsible', '') or ''))

    def select_all_labels(self):
        all_checked = True
        for row in range(self.label_table.rowCount()):
            item = self.label_table.item(row, 0)
            if item and item.checkState() != Qt.Checked:
                all_checked = False
                break

        state = Qt.Unchecked if all_checked else Qt.Checked
        for row in range(self.label_table.rowCount()):
            item = self.label_table.item(row, 0)
            if item:
                item.setCheckState(state)

    def print_labels(self):
        selected = []
        for row in range(self.label_table.rowCount()):
            item = self.label_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                plant_id = item.data(Qt.UserRole)
                plant = PlantManager.get_by_id(plant_id)
                if plant:
                    selected.append(plant)

        if not selected:
            QMessageBox.warning(self, '提示', '请选择要打印标签的植株')
            return

        dlg = LabelPrintDialog(selected, self)
        dlg.exec()

    def generate_acceptance(self):
        plants = PlantManager.get_all()
        self.accept_table.setRowCount(0)

        for i, p in enumerate(plants):
            row = self.accept_table.rowCount()
            self.accept_table.insertRow(row)
            self.accept_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.accept_table.setItem(row, 1, QTableWidgetItem(p['name']))
            self.accept_table.setItem(row, 2, QTableWidgetItem(p.get('species', '') or ''))
            self.accept_table.setItem(row, 3, QTableWidgetItem(p.get('spec', '') or ''))
            self.accept_table.setItem(row, 4, QTableWidgetItem(str(p.get('quantity', 1))))
            self.accept_table.setItem(row, 5, QTableWidgetItem(p.get('area_name', '') or ''))
            self.accept_table.setItem(row, 6, QTableWidgetItem(p.get('status', '')))

            result = '合格' if p.get('status') == '正常' else '待整改'
            result_item = QTableWidgetItem(result)
            result_item.setForeground(QColor('#67c23a') if result == '合格' else QColor('#e6a23c'))
            self.accept_table.setItem(row, 7, result_item)

    def export_acceptance(self):
        file_path, _ = QFileDialog.getSaveFileName(self, '导出验收表',
                                                    f'绿植验收表_{datetime.now().strftime("%Y%m%d")}.csv',
                                                    'CSV文件 (*.csv)')
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([f'绿植验收表 - {self.accept_date.date().toString("yyyy-MM-dd")}'])
                writer.writerow([f'验收人：{self.accept_person.text() or "未填写"}'])
                writer.writerow([])
                writer.writerow(['序号', '名称', '品种', '规格', '数量', '区域', '状态', '验收结果'])

                for row in range(self.accept_table.rowCount()):
                    row_data = []
                    for col in range(self.accept_table.columnCount()):
                        item = self.accept_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    writer.writerow(row_data)

            QMessageBox.information(self, '成功', '验收表已导出')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败：{str(e)}')

    def export_abnormal(self):
        file_path, _ = QFileDialog.getSaveFileName(self, '导出异常清单',
                                                    f'异常植株清单_{datetime.now().strftime("%Y%m%d")}.csv',
                                                    'CSV文件 (*.csv)')
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', '名称', '品种', '区域', '责任人', '状态', '备注'])
                for row in range(self.abn_table.rowCount()):
                    row_data = []
                    for col in range(self.abn_table.columnCount()):
                        item = self.abn_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    writer.writerow(row_data)
            QMessageBox.information(self, '成功', '异常清单已导出')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败：{str(e)}')

    def export_full_report(self):
        file_path, _ = QFileDialog.getSaveFileName(self, '导出完整报表',
                                                    f'绿植管理报表_{datetime.now().strftime("%Y%m%d")}.csv',
                                                    'CSV文件 (*.csv)')
        if not file_path:
            return

        try:
            stats = PlantManager.get_statistics()
            expenses = ExpenseManager.get_total_expense()

            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['园区绿植管理报表'])
                writer.writerow([f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow([])

                writer.writerow(['一、概览数据'])
                writer.writerow(['指标', '数值'])
                writer.writerow(['植株品种数', stats['total_plants']])
                writer.writerow(['植株总数量', stats['total_quantity']])
                writer.writerow(['绿化面积(㎡)', stats['total_area']])
                writer.writerow(['正常植株', stats['normal_count']])
                writer.writerow(['需关注', stats['warn_count']])
                writer.writerow(['病虫害', stats['sick_count']])
                writer.writerow(['枯死', stats['dead_count']])
                writer.writerow(['累计费用(元)', expenses])
                writer.writerow([])

                writer.writerow(['二、各区域分布'])
                writer.writerow(['区域', '品种数', '植株数'])
                for a in stats['by_area']:
                    writer.writerow([a['area_name'] or '未分类', a['cnt'], a['qty']])
                writer.writerow([])

                writer.writerow(['三、植株明细'])
                writer.writerow(['ID', '名称', '品种', '规格', '数量', '面积', '区域', '责任人', '状态', '种植日期', '备注'])
                plants = PlantManager.get_all()
                for p in plants:
                    writer.writerow([
                        p['id'], p['name'], p.get('species', ''), p.get('spec', ''),
                        p.get('quantity', 1), p.get('area', 0),
                        p.get('area_name', ''), p.get('responsible', ''),
                        p.get('status', ''), p.get('plant_date', ''), p.get('notes', '')
                    ])

            QMessageBox.information(self, '成功', '完整报表已导出')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败：{str(e)}')

    def create_backup(self):
        desc, ok = QInputDialog.getText(self, '新建备份', '请输入备份备注（可选）：')
        if ok:
            try:
                backup_file = BackupManager.create_backup(desc.strip())
                QMessageBox.information(self, '成功', f'备份创建成功\n文件：{backup_file}')
                self.load_backup_list()
            except Exception as e:
                QMessageBox.critical(self, '错误', f'备份失败：{str(e)}')

    def load_backup_list(self):
        backups = BackupManager.get_backups()
        self.backup_table.setRowCount(0)

        for b in backups:
            row = self.backup_table.rowCount()
            self.backup_table.insertRow(row)
            self.backup_table.setItem(row, 0, QTableWidgetItem(str(b['id'])))
            self.backup_table.setItem(row, 1, QTableWidgetItem(b['backup_date'] or ''))
            self.backup_table.setItem(row, 2, QTableWidgetItem(str(b.get('record_count', 0))))
            self.backup_table.setItem(row, 3, QTableWidgetItem(b.get('description', '') or ''))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            btn_restore = QPushButton('恢复')
            btn_restore.setFixedHeight(26)
            btn_restore.setStyleSheet('color: #e6a23c;')
            btn_restore.clicked.connect(lambda checked, bid=b['id'], fpath=b['file_path']: self.restore_backup(bid, fpath))
            btn_layout.addWidget(btn_restore)

            btn_delete = QPushButton('删除')
            btn_delete.setFixedHeight(26)
            btn_delete.setStyleSheet('color: #f56c6c;')
            btn_delete.clicked.connect(lambda checked, bid=b['id']: self.delete_backup(bid))
            btn_layout.addWidget(btn_delete)

            self.backup_table.setCellWidget(row, 4, btn_widget)

    def restore_backup(self, backup_id, file_path):
        reply = QMessageBox.question(self, '确认恢复',
                                     '确定要恢复到此备份吗？\n恢复前将自动创建当前数据的备份。')
        if reply == QMessageBox.Yes:
            try:
                BackupManager.restore_backup(file_path)
                QMessageBox.information(self, '成功', '恢复成功，请重新启动程序')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'恢复失败：{str(e)}')

    def restore_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '选择备份文件', '', '数据库文件 (*.db)')
        if file_path:
            reply = QMessageBox.question(self, '确认恢复',
                                         '确定要从该文件恢复吗？\n恢复前将自动创建当前数据的备份。')
            if reply == QMessageBox.Yes:
                try:
                    BackupManager.restore_backup(file_path)
                    QMessageBox.information(self, '成功', '恢复成功，请重新启动程序')
                    self.load_backup_list()
                except Exception as e:
                    QMessageBox.critical(self, '错误', f'恢复失败：{str(e)}')

    def delete_backup(self, backup_id):
        reply = QMessageBox.question(self, '确认', '确定要删除这个备份吗？此操作不可恢复。')
        if reply == QMessageBox.Yes:
            BackupManager.delete_backup(backup_id)
            self.load_backup_list()

    def load_recycle_bin(self):
        deleted = PlantManager.get_deleted()
        self.recycle_table.setRowCount(0)

        for p in deleted:
            row = self.recycle_table.rowCount()
            self.recycle_table.insertRow(row)
            self.recycle_table.setItem(row, 0, QTableWidgetItem(str(p['id'])))
            self.recycle_table.setItem(row, 1, QTableWidgetItem(p['name']))
            self.recycle_table.setItem(row, 2, QTableWidgetItem(p.get('species', '') or ''))
            self.recycle_table.setItem(row, 3, QTableWidgetItem(p.get('area_name', '') or ''))
            self.recycle_table.setItem(row, 4, QTableWidgetItem(p.get('updated_at', '') or ''))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            btn_restore = QPushButton('恢复')
            btn_restore.setFixedHeight(26)
            btn_restore.setProperty('class', 'success')
            btn_restore.setStyleSheet('color: #67c23a;')
            btn_restore.clicked.connect(lambda checked, pid=p['id']: self.restore_plant(pid))
            btn_layout.addWidget(btn_restore)

            self.recycle_table.setCellWidget(row, 5, btn_widget)

    def restore_plant(self, plant_id):
        PlantManager.restore(plant_id)
        QMessageBox.information(self, '成功', '植株已恢复')
        self.load_recycle_bin()

    def refresh(self):
        self.load_statistics()
        self.load_business_analysis()
        self.load_abnormal_data()
        self.load_label_list()
        self.load_backup_list()
        self.load_recycle_bin()
        self.generate_acceptance()
