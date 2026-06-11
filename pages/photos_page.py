import os
import shutil
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                               QLabel, QListWidget, QListWidgetItem, QFileDialog,
                               QMessageBox, QLineEdit, QComboBox, QGridLayout, QScrollArea,
                               QDialog, QFormLayout, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QFont

from database import PhotoManager, PlantManager, PHOTO_DIR


class PhotoDialog(QDialog):
    def __init__(self, photo_path, description='', parent=None):
        super().__init__(parent)
        self.setWindowTitle('照片预览')
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('background: #f5f7fa; border-radius: 6px;')

        pixmap = QPixmap(photo_path)
        if not pixmap.isNull():
            label = QLabel()
            label.setPixmap(pixmap.scaled(560, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.setAlignment(Qt.AlignCenter)
            scroll.setWidget(label)
        else:
            scroll.setWidget(QLabel('无法加载图片'))

        layout.addWidget(scroll, 1)

        if description:
            desc_label = QLabel(f'📝 {description}')
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet('color: #606266; padding: 8px;')
            layout.addWidget(desc_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton('关闭')
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


class PhotosPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('🔍 搜索植株...')
        self.search_input.setFixedWidth(200)
        self.search_input.returnPressed.connect(self.load_photos)
        tb_layout.addWidget(self.search_input)

        self.plant_filter = QComboBox()
        self.plant_filter.addItem('全部植株')
        self.plant_filter.setFixedWidth(160)
        self.plant_filter.currentIndexChanged.connect(self.load_photos)
        tb_layout.addWidget(self.plant_filter)

        btn_search = QPushButton('🔍 筛选')
        btn_search.clicked.connect(self.load_photos)
        tb_layout.addWidget(btn_search)

        tb_layout.addStretch()

        btn_upload = QPushButton('📷 上传照片')
        btn_upload.setProperty('class', 'primary')
        btn_upload.clicked.connect(self.upload_photo)
        tb_layout.addWidget(btn_upload)

        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QFrame()
        left_panel.setStyleSheet('background: white; border-radius: 8px;')
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)

        list_title = QLabel('🌳 按植株归档')
        list_title.setStyleSheet('font-weight: 600; color: #303133; margin-bottom: 8px;')
        left_layout.addWidget(list_title)

        self.plant_list = QListWidget()
        self.plant_list.itemClicked.connect(self.on_plant_select)
        left_layout.addWidget(self.plant_list, 1)

        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setStyleSheet('background: white; border-radius: 8px;')
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)

        self.photo_count_label = QLabel('共 0 张照片')
        self.photo_count_label.setStyleSheet('font-weight: 600; color: #303133; margin-bottom: 8px;')
        right_layout.addWidget(self.photo_count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('border: none;')

        scroll_content = QWidget()
        self.grid_layout = QGridLayout(scroll_content)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(scroll_content)

        right_layout.addWidget(scroll, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([200, 1])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        hint = QLabel('💡 提示：点击左侧植株可筛选对应照片，点击照片可放大查看')
        hint.setStyleSheet('color: #909399; font-size: 12px;')
        layout.addWidget(hint)

    def load_data(self):
        self.load_plant_list()
        self.load_photos()

    def load_plant_list(self):
        plants = PlantManager.get_all()
        self.plants = plants

        self.plant_filter.blockSignals(True)
        self.plant_filter.clear()
        self.plant_filter.addItem('全部植株', None)
        for p in plants:
            self.plant_filter.addItem(p['name'], p['id'])
        self.plant_filter.blockSignals(False)

        self.plant_list.clear()
        all_item = QListWidgetItem('📁 全部照片')
        all_item.setData(Qt.UserRole, None)
        all_item.setSizeHint(QSize(0, 40))
        self.plant_list.addItem(all_item)

        plant_photos = PhotoManager.get_all()
        photo_count = {}
        for ph in plant_photos:
            pid = ph['plant_id']
            if pid:
                photo_count[pid] = photo_count.get(pid, 0) + 1

        for p in plants:
            count = photo_count.get(p['id'], 0)
            item = QListWidgetItem(f'🌿 {p["name"]}  ({count}张)')
            item.setData(Qt.UserRole, p['id'])
            item.setSizeHint(QSize(0, 36))
            self.plant_list.addItem(item)

        if self.plant_list.count() > 0:
            self.plant_list.setCurrentRow(0)

    def on_plant_select(self, item):
        plant_id = item.data(Qt.UserRole)
        if plant_id:
            idx = self.plant_filter.findData(plant_id)
            if idx >= 0:
                self.plant_filter.setCurrentIndex(idx)
        else:
            self.plant_filter.setCurrentIndex(0)

    def load_photos(self):
        plant_id = self.plant_filter.currentData()
        photos = PhotoManager.get_all(plant_id=plant_id)
        self.current_photos = photos

        self.photo_count_label.setText(f'共 {len(photos)} 张照片')

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for i, photo in enumerate(photos):
            card = self._create_photo_card(photo)
            row = i // 4
            col = i % 4
            self.grid_layout.addWidget(card, row, col)

    def _create_photo_card(self, photo):
        card = QFrame()
        card.setStyleSheet('''
            QFrame {
                background: white;
                border: 1px solid #ebeef5;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #409eff;
            }
        ''')
        card.setFixedSize(160, 200)
        card.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        img_label = QLabel()
        img_label.setFixedSize(144, 120)
        img_label.setStyleSheet('background: #f5f7fa; border-radius: 4px;')
        img_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(photo['file_path'])
        if not pixmap.isNull():
            scaled = pixmap.scaled(144, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label.setPixmap(scaled)
        else:
            img_label.setText('🖼️')
            img_label.setStyleSheet('background: #f5f7fa; border-radius: 4px; font-size: 32px;')

        layout.addWidget(img_label)

        name_label = QLabel(photo.get('plant_name', '未知') or '未关联')
        name_label.setStyleSheet('font-size: 12px; font-weight: 600; color: #303133;')
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        date_label = QLabel(photo.get('upload_date', '')[:10])
        date_label.setStyleSheet('font-size: 11px; color: #909399;')
        layout.addWidget(date_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        btn_view = QPushButton('查看')
        btn_view.setFixedHeight(24)
        btn_view.setStyleSheet('font-size: 11px;')
        btn_view.clicked.connect(lambda: self.view_photo(photo))
        btn_layout.addWidget(btn_view)

        btn_del = QPushButton('删除')
        btn_del.setFixedHeight(24)
        btn_del.setStyleSheet('font-size: 11px; color: #f56c6c;')
        btn_del.clicked.connect(lambda: self.delete_photo(photo))
        btn_layout.addWidget(btn_del)

        layout.addLayout(btn_layout)
        layout.addStretch()

        return card

    def upload_photo(self):
        files, _ = QFileDialog.getOpenFileNames(self, '选择照片', '',
                                                 '图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)')
        if not files:
            return

        plant_id = self.plant_filter.currentData()
        if not plant_id:
            if len(self.plants) == 0:
                QMessageBox.warning(self, '提示', '请先添加植株再上传照片')
                return
            QMessageBox.information(self, '提示', '请先选择要关联的植株')
            return

        count = 0
        for f in files:
            try:
                os.makedirs(PHOTO_DIR, exist_ok=True)
                ext = os.path.splitext(f)[1]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_name = f'plant_{plant_id}_{timestamp}_{count}{ext}'
                dest = os.path.join(PHOTO_DIR, new_name)
                shutil.copy2(f, dest)

                PhotoManager.add(plant_id, dest, '')
                count += 1
            except Exception as e:
                QMessageBox.warning(self, '错误', f'上传失败：{str(e)}')

        if count > 0:
            QMessageBox.information(self, '成功', f'成功上传 {count} 张照片')
            self.load_data()

    def view_photo(self, photo):
        dlg = PhotoDialog(photo['file_path'], photo.get('description', ''), self)
        dlg.exec()

    def delete_photo(self, photo):
        reply = QMessageBox.question(self, '确认', '确定要删除这张照片吗？')
        if reply == QMessageBox.Yes:
            PhotoManager.delete(photo['id'])
            self.load_data()

    def refresh(self):
        self.load_data()
