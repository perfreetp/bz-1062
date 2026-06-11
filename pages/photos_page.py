import os
import shutil
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
                               QLabel, QListWidget, QListWidgetItem, QFileDialog,
                               QMessageBox, QLineEdit, QComboBox, QGridLayout, QScrollArea,
                               QDialog, QDialogButtonBox, QFormLayout, QTextEdit, QSplitter, QDateEdit,
                               QTabWidget, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QPixmap, QIcon, QFont

from database import PhotoManager, PlantManager, PHOTO_DIR


class PhotoDialog(QDialog):
    def __init__(self, photo_path, description='', shot_date='', abnormal_status='', parent=None):
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

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        if shot_date:
            date_label = QLabel(f'📅 拍摄日期：{shot_date}')
            date_label.setStyleSheet('color: #606266; padding: 4px 8px;')
            info_layout.addWidget(date_label)

        if description:
            desc_label = QLabel(f'📝 {description}')
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet('color: #606266; padding: 4px 8px;')
            info_layout.addWidget(desc_label)

        if abnormal_status and abnormal_status != '无异常':
            abnormal_colors = {'需关注': '#e6a23c', '病虫害': '#f56c6c', '枯死': '#909399'}
            abnormal_color = abnormal_colors.get(abnormal_status, '#909399')
            abnormal_label = QLabel(f'⚠ 异常情况：{abnormal_status}')
            abnormal_label.setStyleSheet(f'color: {abnormal_color}; padding: 4px 8px; font-weight: 600;')
            info_layout.addWidget(abnormal_label)

        layout.addLayout(info_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton('关闭')
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


class UploadPhotoDialog(QDialog):
    def __init__(self, plants, selected_plant_id=None, parent=None):
        super().__init__(parent)
        self.photo_path = None
        self.setWindowTitle('上传巡检照片')
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.plant_combo = QComboBox()
        for p in plants:
            label = f"{p['name']} ({p['species'] or '未知品种'})"
            self.plant_combo.addItem(label, p['id'])
        if selected_plant_id is not None:
            idx = self.plant_combo.findData(selected_plant_id)
            if idx >= 0:
                self.plant_combo.setCurrentIndex(idx)
        form.addRow('植株：', self.plant_combo)

        btn_select = QPushButton('📷 选择照片')
        btn_select.clicked.connect(self.select_photo)
        self.photo_label = QLabel('未选择照片')
        self.photo_label.setStyleSheet('color: #909399;')
        photo_layout = QHBoxLayout()
        photo_layout.addWidget(btn_select)
        photo_layout.addWidget(self.photo_label, 1)
        photo_frame = QFrame()
        photo_frame.setLayout(photo_layout)
        form.addRow('照片：', photo_frame)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 90)
        self.thumbnail_label.setStyleSheet('background: #f5f7fa; border-radius: 4px;')
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.hide()
        form.addRow('预览：', self.thumbnail_label)

        self.shot_date = QDateEdit()
        self.shot_date.setDisplayFormat('yyyy-MM-dd')
        self.shot_date.setCalendarPopup(True)
        self.shot_date.setDate(QDate.currentDate())
        form.addRow('拍摄日期：', self.shot_date)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(80)
        self.description_input.setPlaceholderText('请填写巡检说明，如：生长状态良好、发现病虫害等...')
        form.addRow('说明：', self.description_input)

        self.abnormal_combo = QComboBox()
        self.abnormal_combo.addItems(['无异常', '需关注', '病虫害', '枯死'])
        form.addRow('异常情况：', self.abnormal_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_photo(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, '选择照片', '',
                                                        '图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)')
            if file_path:
                self.photo_path = file_path
                self.photo_label.setText(os.path.basename(file_path))
                self.photo_label.setStyleSheet('color: #67c23a;')
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.thumbnail_label.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.thumbnail_label.show()
                else:
                    self.thumbnail_label.hide()
                    QMessageBox.warning(self, '提示', '无法加载该图片文件')
        except Exception as e:
            QMessageBox.warning(self, '错误', f'选择图片失败：{str(e)}')

    def get_data(self):
        return {
            'plant_id': self.plant_combo.currentData(),
            'photo_path': self.photo_path,
            'shot_date': self.shot_date.date().toString('yyyy-MM-dd'),
            'description': self.description_input.toPlainText().strip(),
            'abnormal_status': self.abnormal_combo.currentText()
        }

    def accept(self):
        try:
            if not self.photo_path:
                QMessageBox.warning(self, '提示', '请先选择照片')
                return
            if self.plant_combo.currentIndex() < 0:
                QMessageBox.warning(self, '提示', '请先选择植株')
                return
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'操作失败：{str(e)}')


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
        self.search_input.returnPressed.connect(self.on_filter_changed)
        tb_layout.addWidget(self.search_input)

        self.month_filter = QComboBox()
        self.month_filter.addItem('全部月份')
        self.month_filter.setFixedWidth(120)
        self.month_filter.currentIndexChanged.connect(self.on_filter_changed)
        tb_layout.addWidget(self.month_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem('全部状态')
        self.status_filter.addItems(['正常', '需关注', '病虫害', '枯死'])
        self.status_filter.setFixedWidth(120)
        self.status_filter.currentIndexChanged.connect(self.on_filter_changed)
        tb_layout.addWidget(self.status_filter)

        self.plant_filter = QComboBox()
        self.plant_filter.addItem('全部植株')
        self.plant_filter.setFixedWidth(160)
        self.plant_filter.currentIndexChanged.connect(self.on_filter_changed)
        tb_layout.addWidget(self.plant_filter)

        btn_search = QPushButton('🔍 筛选')
        btn_search.clicked.connect(self.on_filter_changed)
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

        self.tabs = QTabWidget()

        grid_tab = QWidget()
        grid_layout = QVBoxLayout(grid_tab)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('border: none;')

        scroll_content = QWidget()
        self.grid_layout = QGridLayout(scroll_content)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(scroll_content)

        grid_layout.addWidget(scroll)
        self.tabs.addTab(grid_tab, '📁 网格视图')

        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        timeline_layout.setContentsMargins(0, 0, 0, 0)

        self.timeline_tree = QTreeWidget()
        self.timeline_tree.setHeaderLabels(['巡检时间线'])
        self.timeline_tree.setHeaderHidden(True)
        self.timeline_tree.itemDoubleClicked.connect(self.on_timeline_item_doubleclick)
        timeline_layout.addWidget(self.timeline_tree)

        self.tabs.addTab(timeline_tab, '📅 巡检时间线')
        self.tabs.currentChanged.connect(self.on_tab_changed)

        right_layout.addWidget(self.tabs, 1)

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
        self.load_month_filter()
        self.load_photos()
        self.load_timeline()

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

    def load_month_filter(self):
        current_month = self.month_filter.currentData()
        months = PhotoManager.get_available_months()

        self.month_filter.blockSignals(True)
        self.month_filter.clear()
        self.month_filter.addItem('全部月份', None)
        for m in months:
            year, month = m.split('-')
            self.month_filter.addItem(f'{year}年{int(month)}月', m)
        self.month_filter.blockSignals(False)

        if current_month:
            idx = self.month_filter.findData(current_month)
            if idx >= 0:
                self.month_filter.setCurrentIndex(idx)

    def on_filter_changed(self):
        self.load_photos()
        self.load_timeline()

    def load_photos(self):
        plant_id = self.plant_filter.currentData()
        month = self.month_filter.currentData()
        status = self.status_filter.currentText()

        keyword = self.search_input.text().strip()
        search_plant_ids = None
        if keyword:
            search_plant_ids = [p['id'] for p in self.plants
                                if keyword.lower() in (p.get('name', '') or '').lower()
                                or keyword.lower() in (p.get('species', '') or '').lower()]
            if not search_plant_ids:
                photos = []
            else:
                photos = PhotoManager.get_all(plant_id=plant_id, month=month, plant_status=status)
                photos = [p for p in photos if p.get('plant_id') in search_plant_ids]
        else:
            photos = PhotoManager.get_all(plant_id=plant_id, month=month, plant_status=status)

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

        date_label = QLabel(photo.get('shot_date', photo.get('upload_date', '')[:10]))
        date_label.setStyleSheet('font-size: 11px; color: #909399;')
        layout.addWidget(date_label)

        status = photo.get('plant_status', '')
        if status and status != '正常':
            status_labels = {'需关注': '#e6a23c', '病虫害': '#f56c6c', '枯死': '#909399'}
            status_color = status_labels.get(status, '#909399')
            status_label = QLabel(status)
            status_label.setStyleSheet(f'''
                font-size: 10px;
                color: {status_color};
                background: {status_color}20;
                padding: 2px 6px;
                border-radius: 2px;
            ''')
            status_label.setAlignment(Qt.AlignCenter)
            layout.insertWidget(2, status_label)

        abnormal = photo.get('abnormal_status', '')
        if abnormal and abnormal != '无异常':
            abnormal_colors = {'需关注': '#e6a23c', '病虫害': '#f56c6c', '枯死': '#909399'}
            abnormal_color = abnormal_colors.get(abnormal, '#909399')
            abnormal_label = QLabel(f'⚠ {abnormal}')
            abnormal_label.setStyleSheet(f'''
                font-size: 10px;
                color: {abnormal_color};
                background: {abnormal_color}20;
                padding: 2px 6px;
                border-radius: 2px;
            ''')
            abnormal_label.setAlignment(Qt.AlignCenter)
            layout.insertWidget(2, abnormal_label)

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
        if len(self.plants) == 0:
            QMessageBox.warning(self, '提示', '请先添加植株再上传照片')
            return

        selected_plant_id = None
        current_item = self.plant_list.currentItem()
        if current_item:
            item_text = current_item.text()
            if '全部照片' not in item_text:
                selected_plant_id = current_item.data(Qt.UserRole)

        dlg = UploadPhotoDialog(self.plants, selected_plant_id, self)
        if dlg.exec() != QDialog.Accepted:
            return

        data = dlg.get_data()
        if not data['photo_path']:
            return

        try:
            os.makedirs(PHOTO_DIR, exist_ok=True)
            ext = os.path.splitext(data['photo_path'])[1]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_name = f'plant_{data["plant_id"]}_{timestamp}{ext}'
            dest = os.path.join(PHOTO_DIR, new_name)
            shutil.copy2(data['photo_path'], dest)

            PhotoManager.add(data['plant_id'], dest, data['shot_date'], data['description'], data['abnormal_status'])
            QMessageBox.information(self, '成功', '照片上传成功')

            current_plant_filter = self.plant_filter.currentData()
            current_month_filter = self.month_filter.currentData()
            current_status_filter = self.status_filter.currentText()

            self.load_plant_list()
            self.load_month_filter()

            if current_plant_filter is not None:
                idx = self.plant_filter.findData(current_plant_filter)
                if idx >= 0:
                    self.plant_filter.setCurrentIndex(idx)
                if current_month_filter:
                    idx = self.month_filter.findData(current_month_filter)
                    if idx >= 0:
                        self.month_filter.setCurrentIndex(idx)
                idx = self.status_filter.findText(current_status_filter)
                if idx >= 0:
                    self.status_filter.setCurrentIndex(idx)
                self.load_photos()
                self.load_timeline()
            else:
                self.load_photos()
                self.load_timeline()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'上传失败：{str(e)}')

    def view_photo(self, photo):
        dlg = PhotoDialog(
            photo['file_path'],
            description=photo.get('description', ''),
            shot_date=photo.get('shot_date', ''),
            abnormal_status=photo.get('abnormal_status', ''),
            parent=self
        )
        dlg.exec()

    def delete_photo(self, photo):
        reply = QMessageBox.question(self, '确认', '确定要删除这张照片吗？')
        if reply == QMessageBox.Yes:
            PhotoManager.delete(photo['id'])
            self.load_data()

    def on_tab_changed(self, index):
        if index == 1:
            self.load_timeline()

    def load_timeline(self):
        self.timeline_tree.clear()

        plant_id = self.plant_filter.currentData()
        month = self.month_filter.currentData()
        status = self.status_filter.currentText()

        if plant_id:
            plant = PlantManager.get_by_id(plant_id)
            if plant:
                photos_by_month = PhotoManager.get_photos_with_timeline(plant_id, month=month, plant_status=status)
                self._build_timeline_for_plant(plant, photos_by_month)
        else:
            plants_with_photos = set()
            all_photos = PhotoManager.get_all(
                month=month,
                plant_status=status
            )
            for p in all_photos:
                if p.get('plant_id'):
                    plants_with_photos.add(p['plant_id'])

            for pid in sorted(plants_with_photos):
                plant = PlantManager.get_by_id(pid)
                if plant:
                    photos_by_month = PhotoManager.get_photos_with_timeline(pid, month=month, plant_status=status)
                    self._build_timeline_for_plant(plant, photos_by_month)

    def _build_timeline_for_plant(self, plant, photos_by_month):
        type_icons = {'正常': '🌿', '需关注': '⚠️', '病虫害': '🐛', '枯死': '💀'}
        status_icon = type_icons.get(plant.get('status', '正常'), '🌿')
        plant_item = QTreeWidgetItem([f'{status_icon} {plant["name"]}（{plant.get("species", "未知品种")}）'])
        plant_item.setExpanded(True)
        self.timeline_tree.addTopLevelItem(plant_item)

        for month in sorted(photos_by_month.keys(), reverse=True):
            year, mon = month.split('-')
            month_item = QTreeWidgetItem([f'📅 {year}年{int(mon)}月（{len(photos_by_month[month])}张）'])
            month_item.setExpanded(True)
            plant_item.addChild(month_item)

            for photo in photos_by_month[month]:
                date_str = photo.get('shot_date', photo.get('upload_date', ''))[:10]
                desc = photo.get('description', '')
                title = f'📷 {date_str}'
                if desc:
                    if len(desc) > 30:
                        desc = desc[:30] + '...'
                    title += f' - {desc}'
                photo_item = QTreeWidgetItem([title])
                photo_item.setData(0, Qt.UserRole, photo)
                month_item.addChild(photo_item)

    def on_timeline_item_doubleclick(self, item, column):
        photo = item.data(0, Qt.UserRole)
        if photo:
            self.view_photo(photo)

    def refresh(self):
        self.load_data()
