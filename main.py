import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget,
                               QLabel, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPalette, QColor

from database import init_db

PAGES = [
    ('总览仪表盘', 'dashboard', '📊'),
    ('地图台账', 'map', '🗺️'),
    ('批量编辑', 'batch', '📋'),
    ('养护排班', 'maintenance', '🌱'),
    ('照片库', 'photos', '📷'),
    ('费用记录', 'expenses', '💰'),
    ('报表中心', 'reports', '📈'),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('园区绿植管理系统')
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        self.init_ui()
        self.apply_style()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setIconSize(QSize(24, 24))

        for name, page_id, icon in PAGES:
            item = QListWidgetItem(f'  {icon}  {name}')
            item.setData(Qt.UserRole, page_id)
            item.setSizeHint(QSize(0, 56))
            self.sidebar.addItem(item)

        self.sidebar.currentRowChanged.connect(self.switch_page)

        content_frame = QFrame()
        content_frame.setObjectName('contentFrame')
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 16, 20, 20)

        self.title_label = QLabel('总览仪表盘')
        self.title_label.setObjectName('pageTitle')
        content_layout.addWidget(self.title_label)

        self.stacked = QStackedWidget()
        content_layout.addWidget(self.stacked)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content_frame, 1)

        self.load_pages()
        self.sidebar.setCurrentRow(0)

    def load_pages(self):
        from pages.dashboard_page import DashboardPage
        from pages.map_page import MapPage
        from pages.batch_page import BatchPage
        from pages.maintenance_page import MaintenancePage
        from pages.photos_page import PhotosPage
        from pages.expenses_page import ExpensesPage
        from pages.reports_page import ReportsPage

        self.pages = {
            'dashboard': DashboardPage(),
            'map': MapPage(),
            'batch': BatchPage(),
            'maintenance': MaintenancePage(),
            'photos': PhotosPage(),
            'expenses': ExpensesPage(),
            'reports': ReportsPage(),
        }

        for page_id, page in self.pages.items():
            self.stacked.addWidget(page)

    def switch_page(self, index):
        page_id = PAGES[index][1]
        page_name = PAGES[index][0]
        self.title_label.setText(page_name)
        self.stacked.setCurrentIndex(index)

        if hasattr(self.pages[page_id], 'refresh'):
            self.pages[page_id].refresh()

    def apply_style(self):
        self.setStyleSheet('''
            QMainWindow, QWidget {
                background-color: #f5f7fa;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QListWidget {
                background-color: #2c3e50;
                border: none;
                outline: none;
            }
            QListWidget::item {
                color: #bdc3c7;
                padding: 8px 12px;
                border-left: 4px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #34495e;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: #ffffff;
                border-left: 4px solid #1abc9c;
            }
            #contentFrame {
                background-color: #f5f7fa;
            }
            #pageTitle {
                font-size: 20px;
                font-weight: 600;
                color: #2c3e50;
                padding: 8px 4px 16px 4px;
            }
            QFrame[frameShape="4"] {
                background: white;
                border-radius: 8px;
            }
            QPushButton {
                padding: 8px 18px;
                border-radius: 4px;
                border: 1px solid #dcdfe6;
                background-color: white;
                color: #606266;
            }
            QPushButton:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background-color: #ecf5ff;
            }
            QPushButton:pressed {
                background-color: #d9ecff;
            }
            QPushButton[class="primary"] {
                background-color: #409eff;
                color: white;
                border: none;
            }
            QPushButton[class="primary"]:hover {
                background-color: #66b1ff;
            }
            QPushButton[class="success"] {
                background-color: #67c23a;
                color: white;
                border: none;
            }
            QPushButton[class="success"]:hover {
                background-color: #85ce61;
            }
            QPushButton[class="danger"] {
                background-color: #f56c6c;
                color: white;
                border: none;
            }
            QPushButton[class="danger"]:hover {
                background-color: #f78989;
            }
            QPushButton[class="warning"] {
                background-color: #e6a23c;
                color: white;
                border: none;
            }
            QPushButton[class="warning"]:hover {
                background-color: #ebb563;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {
                padding: 6px 10px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #409eff;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #409eff;
                outline: none;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ebeef5;
                border-radius: 6px;
                gridline-color: #ebeef5;
                selection-background-color: #ecf5ff;
                selection-color: #409eff;
            }
            QHeaderView::section {
                background-color: #f5f7fa;
                color: #606266;
                padding: 10px 8px;
                border: none;
                border-right: 1px solid #ebeef5;
                border-bottom: 1px solid #ebeef5;
                font-weight: 600;
            }
            QTabWidget::pane {
                border: 1px solid #ebeef5;
                border-radius: 6px;
                background: white;
                top: -1px;
            }
            QTabBar::tab {
                background: #f5f7fa;
                color: #606266;
                padding: 10px 24px;
                border: 1px solid #ebeef5;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #409eff;
                border-bottom: 2px solid #409eff;
            }
            QGroupBox {
                border: 1px solid #ebeef5;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #303133;
                font-weight: 600;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #f5f7fa;
            }
            QScrollBar::handle:vertical {
                background: #c0c4cc;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #909399;
            }
        ''')


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
