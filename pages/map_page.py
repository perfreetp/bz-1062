from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                               QPushButton, QLineEdit, QComboBox, QSpinBox,
                               QDoubleSpinBox, QDateEdit, QTextEdit, QFormLayout,
                               QListWidget, QListWidgetItem, QSplitter, QMessageBox,
                               QInputDialog, QFileDialog, QDialog)
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QFont, QMouseEvent

from database import PlantManager, SettingsManager
import os
import shutil
from datetime import datetime

MAP_IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'maps')


class MapCanvas(QWidget):
    plant_selected = Signal(int)
    plant_moved = Signal(int, float, float)
    plants_selected = Signal(list)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 500)
        self.setStyleSheet('background: #e8f5e9; border: 2px dashed #81c784; border-radius: 8px;')
        self.plants = []
        self.selected_id = None
        self.dragging = False
        self.drag_offset = QPoint()
        self.scale = 1.0
        self.background_pixmap = None
        self.show_areas = True
        self.selection_mode = False
        self.selected_plants = []
        self.selecting = False
        self.selection_start = QPoint()
        self.selection_end = QPoint()
        self.area_colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#9b59b6', '#1abc9c']
        self.load_background()

    def load_background(self):
        bg_path = SettingsManager.get('map_background', '')
        if bg_path and os.path.exists(bg_path):
            self.background_pixmap = QPixmap(bg_path)
            if self.background_pixmap.isNull():
                self.background_pixmap = None
        else:
            self.background_pixmap = None
        self.update()

    def set_background(self, file_path):
        os.makedirs(MAP_IMAGE_DIR, exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest = os.path.join(MAP_IMAGE_DIR, f'map_background{ext}')
        shutil.copy2(file_path, dest)
        SettingsManager.set('map_background', dest)
        self.background_pixmap = QPixmap(dest)
        self.update()

    def clear_background(self):
        SettingsManager.delete('map_background')
        self.background_pixmap = None
        self.update()

    def set_plants(self, plants):
        self.plants = plants
        self.update()

    def set_selected(self, plant_id):
        self.selected_id = plant_id
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        if self.background_pixmap and not self.background_pixmap.isNull():
            scaled_pixmap = self.background_pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x_offset = (w - scaled_pixmap.width()) / 2
            y_offset = (h - scaled_pixmap.height()) / 2
            painter.drawPixmap(int(x_offset), int(y_offset), scaled_pixmap)
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255, 30))
        else:
            pen = QPen(QColor('#c8e6c9'))
            pen.setWidth(1)
            painter.setPen(pen)
            grid_size = 40
            for x in range(0, w, grid_size):
                painter.drawLine(x, 0, x, h)
            for y in range(0, h, grid_size):
                painter.drawLine(0, y, w, y)

        if self.show_areas:
            area_groups = {}
            for plant in self.plants:
                an = plant.get('area_name') or ''
                if an:
                    if an not in area_groups:
                        area_groups[an] = []
                    area_groups[an].append(plant)
            color_idx = 0
            for area_name, group in area_groups.items():
                if not group:
                    continue
                min_x = min(int(p['position_x'] * w) for p in group)
                min_y = min(int(p['position_y'] * h) for p in group)
                max_x = max(int(p['position_x'] * w) for p in group)
                max_y = max(int(p['position_y'] * h) for p in group)
                rect = QRect(min_x - 20, min_y - 20, max_x - min_x + 40, max_y - min_y + 40)
                base_color = QColor(self.area_colors[color_idx % len(self.area_colors)])
                fill_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 77)
                painter.setPen(QPen(base_color, 2))
                painter.setBrush(QBrush(fill_color))
                painter.drawRoundedRect(rect, 8, 8)
                label_rect = QRect(rect.x(), rect.y(), len(area_name) * 14 + 16, 24)
                painter.setPen(QPen(base_color, 1))
                painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
                painter.drawRoundedRect(label_rect, 4, 4)
                painter.setPen(base_color)
                painter.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
                painter.drawText(label_rect, Qt.AlignCenter, area_name)
                color_idx += 1

        for plant in self.plants:
            x = int(plant['position_x'] * w)
            y = int(plant['position_y'] * h)
            x = max(20, min(w - 20, x))
            y = max(20, min(h - 20, y))

            status_colors = {
                '正常': '#67c23a',
                '需关注': '#e6a23c',
                '病虫害': '#f56c6c',
                '枯死': '#909399',
            }
            color = status_colors.get(plant['status'], '#409eff')

            is_selected = plant['id'] in self.selected_plants

            if plant['id'] == self.selected_id:
                painter.setPen(QPen(QColor(color), 3))
                painter.setBrush(QBrush(QColor(color)))
                painter.drawEllipse(x - 16, y - 16, 32, 32)
                painter.setPen(QPen(QColor(color), 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(x - 24, y - 24, 48, 48)
            else:
                painter.setPen(QPen(QColor('#ffffff'), 2))
                painter.setBrush(QBrush(QColor(color)))
                painter.drawEllipse(x - 14, y - 14, 28, 28)

            if is_selected:
                painter.setPen(QPen(QColor('#409eff'), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(x - 20, y - 20, 40, 40)

            painter.setPen(QColor('#ffffff'))
            painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
            painter.drawText(QRect(x - 20, y - 10, 40, 20), Qt.AlignCenter, plant['name'][:2])

        if self.selecting:
            sel_rect = QRect(self.selection_start, self.selection_end).normalized()
            painter.setPen(QPen(QColor('#409eff'), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(64, 158, 255, 50)))
            painter.drawRect(sel_rect)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.selection_mode and event.modifiers() & Qt.ShiftModifier:
                self.selecting = True
                self.selection_start = QPoint(int(event.position().x()), int(event.position().y()))
                self.selection_end = QPoint(self.selection_start)
                self.selected_plants = []
                self.update()
                return
            w = self.width()
            h = self.height()
            for plant in reversed(self.plants):
                px = int(plant['position_x'] * w)
                py = int(plant['position_y'] * h)
                if (event.position().x() - px) ** 2 + (event.position().y() - py) ** 2 <= 225:
                    self.selected_id = plant['id']
                    self.dragging = True
                    self.drag_offset = QPoint(int(event.position().x()) - px, int(event.position().y()) - py)
                    self.plant_selected.emit(plant['id'])
                    self.update()
                    return
            self.selected_id = None
            self.plant_selected.emit(None)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.selecting:
            self.selection_end = QPoint(int(event.position().x()), int(event.position().y()))
            self.update()
            return
        if self.dragging and self.selected_id is not None:
            w = self.width()
            h = self.height()
            new_x = (event.position().x() - self.drag_offset.x()) / w
            new_y = (event.position().y() - self.drag_offset.y()) / h
            new_x = max(0, min(1, new_x))
            new_y = max(0, min(1, new_y))

            for plant in self.plants:
                if plant['id'] == self.selected_id:
                    plant['position_x'] = new_x
                    plant['position_y'] = new_y
                    break
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.selecting:
            self.selecting = False
            sel_rect = QRect(self.selection_start, self.selection_end).normalized()
            w = self.width()
            h = self.height()
            self.selected_plants = []
            for plant in self.plants:
                px = int(plant['position_x'] * w)
                py = int(plant['position_y'] * h)
                if sel_rect.contains(px, py):
                    self.selected_plants.append(plant['id'])
            self.update()
            if self.selected_plants:
                self.plants_selected.emit(self.selected_plants)
            return
        if self.dragging and self.selected_id is not None:
            w = self.width()
            h = self.height()
            new_x = (event.position().x() - self.drag_offset.x()) / w
            new_y = (event.position().y() - self.drag_offset.y()) / h
            new_x = max(0, min(1, new_x))
            new_y = max(0, min(1, new_y))
            self.plant_moved.emit(self.selected_id, new_x, new_y)
        self.dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            w = self.width()
            h = self.height()
            for plant in self.plants:
                px = int(plant['position_x'] * w)
                py = int(plant['position_y'] * h)
                if (event.position().x() - px) ** 2 + (event.position().y() - py) ** 2 <= 225:
                    return
            x_ratio = event.position().x() / w
            y_ratio = event.position().y() / h
            self.parent().add_plant_at(x_ratio, y_ratio)

    def clear_selection(self):
        self.selected_plants = []
        self.update()


class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_plants()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QFrame()
        toolbar.setStyleSheet('background: white; border-radius: 8px; padding: 8px;')
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 8, 12, 8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('🔍 搜索植株名称/品种...')
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.filter_plants)
        tb_layout.addWidget(self.search_input)

        self.area_combo = QComboBox()
        self.area_combo.addItem('全部区域')
        self.area_combo.setFixedWidth(140)
        self.area_combo.currentTextChanged.connect(self.filter_plants)
        tb_layout.addWidget(self.area_combo)

        tb_layout.addStretch()

        self.btn_area_layer = QPushButton('🗺️ 区域图层')
        self.btn_area_layer.setCheckable(True)
        self.btn_area_layer.setChecked(True)
        self.btn_area_layer.clicked.connect(self.toggle_area_layer)
        tb_layout.addWidget(self.btn_area_layer)

        self.btn_batch_select = QPushButton('🔲 批量选择')
        self.btn_batch_select.setCheckable(True)
        self.btn_batch_select.clicked.connect(self.toggle_selection_mode)
        tb_layout.addWidget(self.btn_batch_select)

        btn_bg = QPushButton('🗺️ 导入底图')
        btn_bg.clicked.connect(self.import_background)
        tb_layout.addWidget(btn_bg)

        btn_clear_bg = QPushButton('❌ 清除底图')
        btn_clear_bg.clicked.connect(self.clear_background)
        tb_layout.addWidget(btn_clear_bg)

        btn_add = QPushButton('➕ 添加植株')
        btn_add.setProperty('class', 'primary')
        btn_add.clicked.connect(self.add_plant_dialog)
        tb_layout.addWidget(btn_add)

        btn_refresh = QPushButton('🔄 刷新')
        btn_refresh.clicked.connect(self.refresh)
        tb_layout.addWidget(btn_refresh)

        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QFrame()
        left_panel.setStyleSheet('background: white; border-radius: 8px;')
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)

        list_title = QLabel('📍 植株列表')
        list_title.setStyleSheet('font-weight: 600; color: #303133; margin-bottom: 8px;')
        left_layout.addWidget(list_title)

        self.plant_list = QListWidget()
        self.plant_list.itemClicked.connect(self.on_list_select)
        left_layout.addWidget(self.plant_list, 1)

        self.canvas = MapCanvas()
        self.canvas.plant_selected.connect(self.on_canvas_select)
        self.canvas.plant_moved.connect(self.on_plant_moved)
        self.canvas.plants_selected.connect(self.on_plants_selected)

        right_panel = QFrame()
        right_panel.setStyleSheet('background: white; border-radius: 8px;')
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 14, 16, 14)

        detail_title = QLabel('📝 植株详情')
        detail_title.setStyleSheet('font-weight: 600; color: #303133; margin-bottom: 12px;')
        right_layout.addWidget(detail_title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_input = QLineEdit()
        form.addRow('名称：', self.name_input)

        self.species_input = QLineEdit()
        form.addRow('品种：', self.species_input)

        self.spec_input = QLineEdit()
        form.addRow('规格：', self.spec_input)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 99999)
        form.addRow('数量(株)：', self.quantity_input)

        self.area_input = QDoubleSpinBox()
        self.area_input.setRange(0, 99999)
        self.area_input.setSuffix(' ㎡')
        self.area_input.setDecimals(2)
        form.addRow('绿化面积：', self.area_input)

        self.area_name_input = QLineEdit()
        form.addRow('所在区域：', self.area_name_input)

        self.responsible_input = QLineEdit()
        form.addRow('责任人：', self.responsible_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems(['正常', '需关注', '病虫害', '枯死'])
        form.addRow('状态：', self.status_combo)

        self.plant_date_input = QDateEdit()
        self.plant_date_input.setDisplayFormat('yyyy-MM-dd')
        self.plant_date_input.setCalendarPopup(True)
        form.addRow('种植日期：', self.plant_date_input)

        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        form.addRow('备注：', self.notes_input)

        right_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton('💾 保存')
        btn_save.setProperty('class', 'primary')
        btn_save.clicked.connect(self.save_plant)
        btn_layout.addWidget(btn_save)

        btn_delete = QPushButton('🗑️ 删除')
        btn_delete.setProperty('class', 'danger')
        btn_delete.clicked.connect(self.delete_plant)
        btn_layout.addWidget(btn_delete)

        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        splitter.addWidget(left_panel)
        splitter.addWidget(self.canvas)
        splitter.addWidget(right_panel)
        splitter.setSizes([180, 1, 280])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        layout.addWidget(splitter, 1)

        hint = QLabel('💡 提示：双击地图空白处添加植株，拖拽点位可调整位置 | 批量选择模式下 Shift+拖拽框选')
        hint.setStyleSheet('color: #909399; font-size: 12px; padding: 4px 8px;')
        layout.addWidget(hint)

        self.current_plant_id = None
        self.set_detail_enabled(False)

    def set_detail_enabled(self, enabled):
        for w in [self.name_input, self.species_input, self.spec_input,
                  self.quantity_input, self.area_input, self.area_name_input,
                  self.responsible_input, self.status_combo, self.plant_date_input,
                  self.notes_input]:
            w.setEnabled(enabled)

    def load_plants(self):
        self.all_plants = PlantManager.get_all()
        self.canvas.set_plants(self.all_plants)
        self.refresh_list(self.all_plants)

        areas = PlantManager.get_areas()
        self.area_combo.blockSignals(True)
        self.area_combo.clear()
        self.area_combo.addItem('全部区域')
        for a in areas:
            self.area_combo.addItem(a)
        self.area_combo.blockSignals(False)

    def refresh_list(self, plants):
        self.plant_list.clear()
        status_icons = {'正常': '🟢', '需关注': '🟡', '病虫害': '🔴', '枯死': '⚫'}
        for p in plants:
            icon = status_icons.get(p['status'], '🟢')
            item = QListWidgetItem(f"{icon} {p['name']}")
            item.setData(Qt.UserRole, p['id'])
            self.plant_list.addItem(item)

    def filter_plants(self):
        keyword = self.search_input.text().strip()
        area = self.area_combo.currentText()
        if area == '全部区域':
            area = None

        filtered = []
        for p in self.all_plants:
            match = True
            if keyword:
                kw = keyword.lower()
                if kw not in p['name'].lower() and kw not in (p['species'] or '').lower():
                    match = False
            if area and p['area_name'] != area:
                match = False
            if match:
                filtered.append(p)

        self.canvas.set_plants(filtered)
        self.refresh_list(filtered)

    def on_list_select(self, item):
        plant_id = item.data(Qt.UserRole)
        self.current_plant_id = plant_id
        self.canvas.set_selected(plant_id)
        self.load_detail(plant_id)

    def on_canvas_select(self, plant_id):
        self.current_plant_id = plant_id
        if plant_id:
            self.load_detail(plant_id)
            for i in range(self.plant_list.count()):
                if self.plant_list.item(i).data(Qt.UserRole) == plant_id:
                    self.plant_list.setCurrentRow(i)
                    break
        else:
            self.clear_detail()

    def on_plant_moved(self, plant_id, x, y):
        PlantManager.update(plant_id, {'position_x': x, 'position_y': y})
        for i, p in enumerate(self.all_plants):
            if p['id'] == plant_id:
                self.all_plants[i]['position_x'] = x
                self.all_plants[i]['position_y'] = y
                break

    def toggle_area_layer(self):
        self.canvas.show_areas = self.btn_area_layer.isChecked()
        self.canvas.update()

    def toggle_selection_mode(self):
        self.canvas.selection_mode = self.btn_batch_select.isChecked()
        if not self.canvas.selection_mode:
            self.canvas.clear_selection()

    def on_plants_selected(self, plant_ids):
        self.show_batch_dialog(plant_ids)

    def show_batch_dialog(self, plant_ids):
        if not plant_ids:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f'批量操作（已选 {len(plant_ids)} 个植株）')
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)

        form = QFormLayout()
        form.setSpacing(12)

        responsible_input = QLineEdit()
        form.addRow('责任人：', responsible_input)

        status_combo = QComboBox()
        status_combo.addItems(['', '正常', '需关注', '病虫害', '枯死'])
        form.addRow('状态：', status_combo)

        area_name_input = QLineEdit()
        form.addRow('区域：', area_name_input)

        layout.addLayout(form)

        hint = QLabel('留空的字段将不会被修改')
        hint.setStyleSheet('color: #909399; font-size: 12px;')
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton('确认修改')
        btn_ok.setProperty('class', 'primary')
        btn_ok.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QPushButton('取消')
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            responsible = responsible_input.text().strip()
            status = status_combo.currentText()
            area_name = area_name_input.text().strip()
            if responsible:
                PlantManager.batch_update(plant_ids, 'responsible', responsible)
            if status:
                PlantManager.batch_update(plant_ids, 'status', status)
            if area_name:
                PlantManager.batch_update(plant_ids, 'area_name', area_name)
            self.canvas.clear_selection()
            self.refresh()
            QMessageBox.information(self, '成功', f'已批量更新 {len(plant_ids)} 个植株')

    def load_detail(self, plant_id):
        plant = PlantManager.get_by_id(plant_id)
        if not plant:
            return

        self.name_input.setText(plant['name'])
        self.species_input.setText(plant['species'] or '')
        self.spec_input.setText(plant['spec'] or '')
        self.quantity_input.setValue(plant['quantity'] or 1)
        self.area_input.setValue(plant['area'] or 0)
        self.area_name_input.setText(plant['area_name'] or '')
        self.responsible_input.setText(plant['responsible'] or '')
        self.status_combo.setCurrentText(plant['status'] or '正常')
        if plant['plant_date']:
            from PySide6.QtCore import QDate
            date = QDate.fromString(plant['plant_date'], 'yyyy-MM-dd')
            if date.isValid():
                self.plant_date_input.setDate(date)
        self.notes_input.setPlainText(plant['notes'] or '')
        self.set_detail_enabled(True)

    def clear_detail(self):
        self.name_input.clear()
        self.species_input.clear()
        self.spec_input.clear()
        self.quantity_input.setValue(1)
        self.area_input.setValue(0)
        self.area_name_input.clear()
        self.responsible_input.clear()
        self.status_combo.setCurrentIndex(0)
        self.notes_input.clear()
        self.set_detail_enabled(False)

    def add_plant_dialog(self):
        self.current_plant_id = None
        self.canvas.set_selected(None)
        self.clear_detail()
        self.name_input.setFocus()
        self.set_detail_enabled(True)

    def add_plant_at(self, x, y):
        name, ok = QInputDialog.getText(self, '添加植株', '请输入植株名称：')
        if ok and name.strip():
            data = {
                'name': name.strip(),
                'position_x': x,
                'position_y': y,
            }
            plant_id = PlantManager.add(data)
            self.refresh()
            self.current_plant_id = plant_id
            self.canvas.set_selected(plant_id)
            self.load_detail(plant_id)

    def save_plant(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, '提示', '请输入植株名称')
            return

        from PySide6.QtCore import QDate
        data = {
            'name': name,
            'species': self.species_input.text().strip(),
            'spec': self.spec_input.text().strip(),
            'quantity': self.quantity_input.value(),
            'area': self.area_input.value(),
            'area_name': self.area_name_input.text().strip(),
            'responsible': self.responsible_input.text().strip(),
            'status': self.status_combo.currentText(),
            'plant_date': self.plant_date_input.date().toString('yyyy-MM-dd'),
            'notes': self.notes_input.toPlainText().strip(),
        }

        if self.current_plant_id:
            PlantManager.update(self.current_plant_id, data)
            QMessageBox.information(self, '成功', '保存成功')
        else:
            self.current_plant_id = PlantManager.add(data)
            QMessageBox.information(self, '成功', '添加成功')

        self.refresh()
        self.canvas.set_selected(self.current_plant_id)

    def delete_plant(self):
        if not self.current_plant_id:
            return
        reply = QMessageBox.question(self, '确认', '确定要删除这株植物吗？（可在报表中心回收站恢复）')
        if reply == QMessageBox.Yes:
            PlantManager.delete(self.current_plant_id)
            self.current_plant_id = None
            self.canvas.set_selected(None)
            self.clear_detail()
            self.refresh()

    def import_background(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '选择园区平面图', '',
                                                   '图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)')
        if file_path:
            try:
                self.canvas.set_background(file_path)
                QMessageBox.information(self, '成功', '园区平面图已设置为底图')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入失败：{str(e)}')

    def clear_background(self):
        reply = QMessageBox.question(self, '确认', '确定要清除底图吗？')
        if reply == QMessageBox.Yes:
            self.canvas.clear_background()

    def refresh(self):
        self.load_plants()
        self.canvas.load_background()
