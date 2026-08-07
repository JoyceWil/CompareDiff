import sys
import os
import cv2
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QSplitter, QListWidget, QMainWindow,
    QComboBox, QStackedWidget, QSizePolicy, QButtonGroup, QFrame, QStyle
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QPoint


IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')
IMAGE_FILE_FILTER = '图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;所有文件 (*)'

APP_STYLE = """
QMainWindow, QWidget#mainSurface {
    background: #151a1f;
    color: #d9e1e7;
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
}
QLabel {
    color: #d9e1e7;
}
QWidget#toolbar {
    background: #1d252c;
    border: 1px solid #2d3942;
    border-radius: 6px;
}
QLabel#appName {
    color: #f4f7f9;
    font-size: 19px;
    font-weight: 600;
}
QLabel#appSection {
    color: #7f909c;
    font-size: 10px;
    font-weight: 600;
}
QLabel#fieldLabel, QLabel#listTitle {
    color: #8fa2af;
    font-size: 11px;
    font-weight: 600;
}
QLabel#pathValue {
    color: #d7e1e7;
    background: #141a1f;
    border: 1px solid #303d46;
    border-radius: 4px;
    padding: 5px 8px;
}
QLabel#selectedFile {
    color: #b7f2dc;
    background: #18342f;
    border: 1px solid #2b5c51;
    border-radius: 4px;
    padding: 5px 8px;
}
QLabel#summary {
    color: #98aab5;
    padding: 2px 1px;
    font-size: 12px;
}
QLabel#pixelInfo {
    color: #8bf0bf;
    background: #11171b;
    border: 1px solid #27343c;
    border-radius: 5px;
    padding: 5px 9px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 11px;
}
QPushButton {
    color: #dbe5eb;
    background: #26323a;
    border: 1px solid #3a4a55;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 18px;
}
QPushButton:hover {
    background: #31414c;
    border-color: #55717f;
}
QPushButton:pressed {
    background: #1d2a31;
}
QPushButton:checked {
    color: #e5fff5;
    background: #146b5a;
    border-color: #36a68b;
}
QPushButton:disabled {
    color: #60717c;
    background: #20282e;
    border-color: #2b353d;
}
QPushButton#primaryButton {
    color: #f4fffb;
    background: #16735f;
    border-color: #34a789;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background: #1b896f;
    border-color: #5fd0ac;
}
QPushButton[ready="true"] {
    color: #ddfff3;
    background: #1c5145;
    border-color: #3f8e7c;
}
QComboBox {
    color: #e0e9ee;
    background: #141a1f;
    border: 1px solid #3a4a55;
    border-radius: 4px;
    padding: 5px 28px 5px 8px;
    min-height: 18px;
}
QComboBox:hover, QComboBox:focus {
    border-color: #5d7b87;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    color: #e0e9ee;
    background: #202a31;
    border: 1px solid #3a4a55;
    selection-background-color: #16735f;
}
QListWidget {
    color: #cfdbe1;
    background: #11171b;
    border: 1px solid #303d46;
    border-radius: 5px;
    outline: none;
    padding: 3px;
}
QListWidget::item {
    border-radius: 3px;
    padding: 5px 6px;
}
QListWidget::item:hover {
    background: #26353d;
}
QListWidget::item:selected {
    color: #f1fff9;
    background: #176c5a;
}
QScrollBar:vertical {
    background: #11171b;
    width: 10px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: #40515c;
    min-height: 26px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover { background: #58707d; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle {
    background: #2a353d;
}
QSplitter::handle:hover {
    background: #3f8e7c;
}
QToolTip {
    color: #e6f0f3;
    background: #202b32;
    border: 1px solid #4a606a;
    padding: 5px;
}
QFrame#divider {
    color: #34434d;
    background: #34434d;
    max-width: 1px;
}
"""


class ElidedLabel(QLabel):
    """在有限宽度内显示关键名称，完整内容保留在悬停提示中。"""
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self._full_text = ''
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumWidth(110)
        self.set_full_text(text)

    def set_full_text(self, text, tooltip=None):
        self._full_text = text
        self.setToolTip(tooltip or text)
        self._refresh_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_text()

    def _refresh_text(self):
        if self.width() <= 0:
            super().setText(self._full_text)
            return
        elided = self.fontMetrics().elidedText(self._full_text, Qt.ElideRight, self.width())
        super().setText(elided)


def make_section_label(text):
    label = QLabel(text)
    label.setObjectName('appSection')
    return label


def make_field_label(text):
    label = QLabel(text)
    label.setObjectName('fieldLabel')
    return label


def make_list_title(text):
    label = QLabel(text)
    label.setObjectName('listTitle')
    return label


def make_divider():
    divider = QFrame()
    divider.setObjectName('divider')
    divider.setFrameShape(QFrame.VLine)
    divider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    return divider


def compact_relative_path(relative_path, max_parent_length=24):
    """优先展示文件名；父目录过长时用 ..\\..\\ 代替。"""
    normalized_path = os.path.normpath(relative_path)
    parent_path, filename = os.path.split(normalized_path)
    if not parent_path or len(parent_path) <= max_parent_length:
        return normalized_path
    return f'..{os.sep}..{os.sep}{filename}'


# --- 辅助函数 ---
def cv2qt(img):
    """转换 OpenCV 图片 -> Qt 图片"""
    if img is None: return QPixmap()
    if len(img.shape) == 2:
        h, w = img.shape
        bytes_per_line = img.strides[0]
        return QImage(img.data, w, h, bytes_per_line, QImage.Format_Grayscale8).copy()
    else:
        h, w, c = img.shape
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        bytes_per_line = rgb.strides[0]
        return QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()


def read_image(path):
    """读取图片，处理中文路径和透明通道"""
    arr = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)

    if img is None: return None

    # 处理 4通道 BGRA -> 3通道 BGR
    if len(img.shape) == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def collect_images(root_dir):
    """递归收集目录中的图像，并保留相对于根目录的路径。"""
    images = []
    for root, dirs, files in os.walk(root_dir):
        dirs.sort()
        for filename in sorted(files):
            if filename.lower().endswith(IMAGE_EXTENSIONS):
                absolute_path = os.path.join(root, filename)
                relative_path = os.path.relpath(absolute_path, root_dir)
                images.append((relative_path, absolute_path))
    return images


# --- 核心对比组件 ---
class CompareWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.imgA = None
        self.imgB = None
        self.h = 0
        self.w = 0

        # 视图状态
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self.mode = 'NONE'
        self.last_mouse = QPoint()
        self.split_x = 0
        self.show_diff = False

        # UI 初始化
        self.label = QLabel("选择文件夹或单对图片以开始对比")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(
            "background-color: #0a0e11; color: #60717c; "
            "border: 1px solid #27343c; border-radius: 5px;"
        )
        self.label.setMouseTracking(True)
        self.label.installEventFilter(self)

        self.info_label = QLabel("坐标: -, 像素值: -")
        self.info_label.setObjectName('pixelInfo')

        # 布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.info_label)
        layout.addWidget(self.label, stretch=1)
        self.setLayout(layout)

    def set_images(self, imgA, imgB):
        """外部调用此方法更新图片"""
        if imgA is None or imgB is None:
            return False, '图片读取失败。'

        if imgA.shape[:2] != imgB.shape[:2]:
            return False, (
                f'图像尺寸不一致：左图为 {imgA.shape[1]} x {imgA.shape[0]}，'
                f'右图为 {imgB.shape[1]} x {imgB.shape[0]}。'
            )

        # 格式统一
        if len(imgA.shape) != len(imgB.shape):
            if len(imgA.shape) == 2: imgA = cv2.cvtColor(imgA, cv2.COLOR_GRAY2BGR)
            if len(imgB.shape) == 2: imgB = cv2.cvtColor(imgB, cv2.COLOR_GRAY2BGR)

        if imgA.shape != imgB.shape:
            return False, '图像通道格式不兼容，无法进行像素级对比。'

        self.imgA = imgA
        self.imgB = imgB
        self.h, self.w = imgA.shape[:2]

        self.split_x = self.w // 2

        # --- 核心修改：每次加载新图，强制执行“适应窗口”逻辑 ---
        self.fit_in_view()
        return True, ''

    def fit_in_view(self):
        """计算最佳缩放比例和偏移量，使图片居中并铺满窗口"""
        if self.w == 0 or self.h == 0: return

        # 获取当前窗口的显示区域大小
        view_w = self.label.width()
        view_h = self.label.height()

        # 防止窗口还没显示导致尺寸为0
        if view_w <= 1: view_w = 800
        if view_h <= 1: view_h = 600

        # 1. 计算缩放比例 (保留 5% 的边距，看起来舒服点)
        scale_w = view_w / self.w
        scale_h = view_h / self.h
        self.scale = min(scale_w, scale_h) * 0.95

        # 2. 计算居中偏移量
        new_w = self.w * self.scale
        new_h = self.h * self.scale

        ox = (view_w - new_w) / 2
        oy = (view_h - new_h) / 2

        self.offset = QPoint(int(ox), int(oy))
        self.update_view()

    def toggle_diff(self):
        self.show_diff = not self.show_diff
        self.update_view()

    def update_view(self):
        if self.imgA is None: return

        # 1. 合成
        if self.show_diff:
            diff = cv2.absdiff(self.imgA, self.imgB)
            base = np.clip(diff.astype(np.float32) * 3, 0, 255).astype(np.uint8)
        else:
            base = self.imgB.copy()
            sx = max(0, min(self.split_x, self.w))

            if len(base.shape) == 2:
                base[:, :sx] = self.imgA[:, :sx]
            else:
                base[:, :sx, :] = self.imgA[:, :sx, :]

        # 2. 变换
        view_img = self.apply_transform(base)

        # 3. 绘图
        if len(view_img.shape) == 2:
            view_img = cv2.cvtColor(view_img, cv2.COLOR_GRAY2BGR)

        if not self.show_diff:
            view_img = self.draw_split_line(view_img)

        # 4. 显示
        qt_img = cv2qt(view_img)
        self.label.setPixmap(QPixmap.fromImage(qt_img))

    def apply_transform(self, img):
        if img is None: return np.zeros((400, 400, 3), dtype=np.uint8)
        h, w = img.shape[:2]
        new_w, new_h = int(w * self.scale), int(h * self.scale)
        # 自动选择插值方式：放得很大时用最近邻（看像素），缩小时用线性（平滑）
        method = cv2.INTER_NEAREST if self.scale > 4.0 else cv2.INTER_LINEAR
        scaled = cv2.resize(img, (new_w, new_h), interpolation=method)

        canvas_h = self.label.height()
        canvas_w = self.label.width()
        # 容错处理
        if canvas_w <= 1: canvas_w, canvas_h = 800, 600

        canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

        # 这里的 offset 是图片的左上角相对于画布左上角的坐标
        ox, oy = self.offset.x(), self.offset.y()

        # 计算图片与画布的重叠区域
        x1 = max(0, ox)
        y1 = max(0, oy)
        x2 = min(canvas_w, ox + new_w)
        y2 = min(canvas_h, oy + new_h)

        # 计算对应在 resize 后图片中的坐标
        img_x1 = x1 - ox
        img_y1 = y1 - oy
        img_x2 = img_x1 + (x2 - x1)
        img_y2 = img_y1 + (y2 - y1)

        # 赋值 (只要有重叠区域)
        if x1 < x2 and y1 < y2:
            canvas[y1:y2, x1:x2] = scaled[img_y1:img_y2, img_x1:img_x2]
        return canvas

    def draw_split_line(self, view_img):
        H, W = view_img.shape[:2]
        screen_split_x = int(self.split_x * self.scale + self.offset.x())
        if 0 <= screen_split_x <= W:
            cv2.line(view_img, (screen_split_x, 0), (screen_split_x, H), (0, 255, 255), 2)
            cy = H // 2
            cv2.circle(view_img, (screen_split_x, cy), 8, (0, 165, 255), -1)
            cv2.circle(view_img, (screen_split_x, cy), 8, (255, 255, 255), 1)
        return view_img

    # 事件处理
    def eventFilter(self, obj, event):
        if obj == self.label and self.imgA is not None:
            if event.type() == event.MouseMove:
                self.on_mouse_move(event)
            elif event.type() == event.MouseButtonPress:
                self.on_mouse_press(event)
            elif event.type() == event.MouseButtonRelease:
                self.on_mouse_release(event)
            elif event.type() == event.Wheel:
                self.on_wheel(event); return True
            # 可选：监听窗口大小变化事件，如果需要拖动窗口实时居中，可取消注释下面两行
            # elif event.type() == event.Resize:
            #     self.fit_in_view()
        return False

    def on_mouse_move(self, event):
        pos = event.pos()
        sx = int(self.split_x * self.scale + self.offset.x())

        is_hover = abs(pos.x() - sx) < 10 and not self.show_diff

        if self.mode == 'DRAG_SPLIT' or is_hover:
            self.setCursor(Qt.SizeHorCursor)
        elif self.mode == 'DRAG_IMAGE':
            self.setCursor(Qt.ClosedHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        if self.mode == 'DRAG_SPLIT':
            self.split_x = max(0, min(int((pos.x() - self.offset.x()) / self.scale), self.w))
            self.update_view()
        elif self.mode == 'DRAG_IMAGE':
            self.offset += pos - self.last_mouse
            self.last_mouse = pos
            self.update_view()
        else:
            # 取值逻辑
            ix = int((pos.x() - self.offset.x()) / self.scale)
            iy = int((pos.y() - self.offset.y()) / self.scale)
            if 0 <= ix < self.w and 0 <= iy < self.h:
                va = self.imgA[iy, ix]
                vb = self.imgB[iy, ix]
                curr = va if ix < self.split_x else vb
                src = "Result" if ix < self.split_x else "GT"

                # 数值显示 (兼容灰度/彩色)
                if hasattr(va, "__len__"):
                    diff = np.sum(np.abs(va.astype(int) - vb.astype(int)))
                    self.info_label.setText(f"[{ix},{iy}] | {src}: {curr.tolist()} | Diff(Sum): {diff}")
                else:
                    diff = abs(int(va) - int(vb))
                    self.info_label.setText(f"[{ix},{iy}] | {src}: {curr} | Diff: {diff}")

    def on_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            sx = int(self.split_x * self.scale + self.offset.x())
            if abs(event.pos().x() - sx) < 10 and not self.show_diff:
                self.mode = 'DRAG_SPLIT'
            else:
                self.mode = 'DRAG_IMAGE'
            self.last_mouse = event.pos()

    def on_mouse_release(self, event):
        self.mode = 'NONE'

    def on_wheel(self, event):
        # 滚轮缩放时，保留当前的偏移，不做自动居中，允许用户放大查看细节
        if event.angleDelta().y() > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.scale = max(0.01, min(50.0, self.scale))  # 扩大允许的缩放范围
        self.update_view()


# --- 主窗口 ---
class BatchCompareWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CompareDiff")
        self.resize(1200, 800)
        self.setMinimumSize(1024, 680)

        self.dirA = ""
        self.dirB = ""
        self.file_pairs = []
        self.folder_files_a = []
        self.folder_files_b = []
        self.single_path_a = ""
        self.single_path_b = ""
        self.manual_path_a = ""
        self.manual_path_b = ""

        # --- UI 组件 ---
        main_widget = QWidget()
        main_widget.setObjectName('mainSurface')
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. 顶部控制栏
        toolbar = QWidget()
        toolbar.setObjectName('toolbar')
        toolbar.setFixedHeight(72)
        top_bar = QHBoxLayout(toolbar)
        top_bar.setContentsMargins(12, 8, 12, 8)
        top_bar.setSpacing(8)

        title_group = QVBoxLayout()
        title_group.setSpacing(0)
        app_name = QLabel("CompareDiff")
        app_name.setObjectName('appName')
        title_group.addWidget(app_name)
        title_group.addWidget(make_section_label("RESEARCH IMAGE REVIEW"))
        top_bar.addLayout(title_group)
        top_bar.addWidget(make_divider())

        mode_group = QVBoxLayout()
        mode_group.setSpacing(2)
        mode_group.addWidget(make_section_label("对比模式"))
        self.mode_selector = QComboBox()
        self.mode_selector.addItem("文件夹对比", 'folder')
        self.mode_selector.addItem("单对图片", 'single')
        self.mode_selector.currentIndexChanged.connect(self.switch_compare_mode)
        mode_group.addWidget(self.mode_selector)
        top_bar.addLayout(mode_group)
        top_bar.addWidget(make_divider())

        self.folder_controls = QWidget()
        folder_layout = QHBoxLayout(self.folder_controls)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(6)
        folder_layout.addWidget(make_section_label("数据源"))
        self.btn_sel_dir_a = QPushButton("选择 Result")
        self.btn_sel_dir_a.clicked.connect(lambda: self.select_dir('A'))
        self.lbl_dir_A = QLabel("未选择")
        self.lbl_dir_A.setObjectName('pathValue')
        self.lbl_dir_A.setMinimumWidth(92)
        self.lbl_dir_A.setMaximumWidth(120)

        self.btn_sel_dir_b = QPushButton("选择 GT")
        self.btn_sel_dir_b.clicked.connect(lambda: self.select_dir('B'))
        self.lbl_dir_B = QLabel("未选择")
        self.lbl_dir_B.setObjectName('pathValue')
        self.lbl_dir_B.setMinimumWidth(92)
        self.lbl_dir_B.setMaximumWidth(120)

        self.lbl_selected_file_a = ElidedLabel("左图：未选择")
        self.lbl_selected_file_b = ElidedLabel("右图：未选择")
        self.lbl_selected_file_a.setObjectName('selectedFile')
        self.lbl_selected_file_b.setObjectName('selectedFile')
        self.lbl_selected_file_a.setMaximumWidth(170)
        self.lbl_selected_file_b.setMaximumWidth(170)

        folder_layout.addWidget(self.btn_sel_dir_a)
        folder_layout.addWidget(self.lbl_dir_A)
        folder_layout.addWidget(self.btn_sel_dir_b)
        folder_layout.addWidget(self.lbl_dir_B)
        folder_layout.addWidget(make_divider())
        folder_layout.addWidget(self.lbl_selected_file_a)
        folder_layout.addWidget(self.lbl_selected_file_b)

        self.single_controls = QWidget()
        single_layout = QHBoxLayout(self.single_controls)
        single_layout.setContentsMargins(0, 0, 0, 0)
        single_layout.setSpacing(6)
        single_layout.addWidget(make_section_label("数据源"))
        self.btn_sel_file_a = QPushButton("选择左图")
        self.btn_sel_file_a.clicked.connect(lambda: self.select_single_image('A'))
        self.lbl_file_a = QLabel("未选择")
        self.lbl_file_a.setObjectName('pathValue')
        self.lbl_file_a.setMinimumWidth(120)
        self.lbl_file_a.setMaximumWidth(180)

        self.btn_sel_file_b = QPushButton("选择右图")
        self.btn_sel_file_b.clicked.connect(lambda: self.select_single_image('B'))
        self.lbl_file_b = QLabel("未选择")
        self.lbl_file_b.setObjectName('pathValue')
        self.lbl_file_b.setMinimumWidth(120)
        self.lbl_file_b.setMaximumWidth(180)

        single_layout.addWidget(self.btn_sel_file_a)
        single_layout.addWidget(self.lbl_file_a)
        single_layout.addWidget(self.btn_sel_file_b)
        single_layout.addWidget(self.lbl_file_b)

        top_bar.addWidget(self.folder_controls, 1)
        top_bar.addWidget(self.single_controls, 1)
        top_bar.addWidget(make_divider())

        view_group = QVBoxLayout()
        view_group.setSpacing(2)
        view_group.addWidget(make_section_label("视图"))
        view_controls = QHBoxLayout()
        view_controls.setSpacing(6)
        self.btn_fit = QPushButton("适配")
        self.btn_fit.setToolTip("适配窗口")
        self.btn_fit.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_fit.clicked.connect(self.trigger_fit)

        self.btn_diff = QPushButton("差分")
        self.btn_diff.setToolTip("切换 Diff 模式")
        self.btn_diff.setCheckable(True)
        self.btn_diff.clicked.connect(self.toggle_diff_mode)
        view_controls.addWidget(self.btn_fit)
        view_controls.addWidget(self.btn_diff)
        view_group.addLayout(view_controls)
        top_bar.addLayout(view_group)

        # 2. 左侧文件浏览区与图像视图
        splitter = QSplitter(Qt.Horizontal)

        self.browser_stack = QStackedWidget()
        self.single_browser = self.create_single_browser()
        self.folder_browser = self.create_folder_browser()
        self.browser_stack.addWidget(self.folder_browser)
        self.browser_stack.addWidget(self.single_browser)
        self.browser_stack.setMinimumWidth(460)
        self.browser_stack.setMaximumWidth(560)

        self.compare_view = CompareWidget()

        splitter.addWidget(self.browser_stack)
        splitter.addWidget(self.compare_view)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([480, 720])

        main_layout.addWidget(toolbar)
        main_layout.addWidget(splitter)
        self.switch_compare_mode()

    def create_single_browser(self):
        browser = QWidget()
        layout = QVBoxLayout(browser)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(make_list_title("单对图片"))
        status = QLabel("从顶部选择左图和右图后，将自动载入对比视图。")
        status.setWordWrap(True)
        status.setObjectName('summary')
        layout.addWidget(status)
        layout.addStretch()
        return browser

    def create_folder_browser(self):
        browser = QWidget()
        layout = QVBoxLayout(browser)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(make_list_title("图像对"))
        header.addStretch()
        self.folder_summary = QLabel("请选择两个目录以开始自动匹配。")
        self.folder_summary.setObjectName('summary')
        self.folder_summary.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        header.addWidget(self.folder_summary)
        layout.addLayout(header)

        self.mode_button_group = QButtonGroup(browser)
        view_controls = QHBoxLayout()
        view_controls.setSpacing(6)
        self.btn_show_auto = QPushButton("自动匹配")
        self.btn_show_auto.setCheckable(True)
        self.btn_show_auto.clicked.connect(lambda: self.show_folder_view(0))
        self.btn_show_manual = QPushButton("手动配对")
        self.btn_show_manual.setCheckable(True)
        self.btn_show_manual.clicked.connect(lambda: self.show_folder_view(1))
        self.mode_button_group.addButton(self.btn_show_auto)
        self.mode_button_group.addButton(self.btn_show_manual)
        view_controls.addWidget(self.btn_show_auto)
        view_controls.addWidget(self.btn_show_manual)
        view_controls.addStretch()
        layout.addLayout(view_controls)

        self.folder_views = QStackedWidget()
        self.file_list = QListWidget()
        self.file_list.setTextElideMode(Qt.ElideRight)
        self.file_list.itemClicked.connect(self.on_auto_pair_selected)
        self.folder_views.addWidget(self.file_list)
        self.folder_views.addWidget(self.create_manual_browser())
        layout.addWidget(self.folder_views, 1)
        self.show_folder_view(0)
        return browser

    def create_manual_browser(self):
        browser = QWidget()
        layout = QVBoxLayout(browser)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_compare_selected = QPushButton("对比所选图片")
        self.btn_compare_selected.setObjectName('primaryButton')
        self.btn_compare_selected.setToolTip("载入当前选择的左图与右图")
        self.btn_compare_selected.setEnabled(False)
        self.btn_compare_selected.clicked.connect(self.compare_manual_selection)
        layout.addWidget(self.btn_compare_selected)

        lists = QSplitter(Qt.Horizontal)
        panel_a, self.manual_list_a = self.create_manual_list('Result (A)', 'A')
        panel_b, self.manual_list_b = self.create_manual_list('GT (B)', 'B')
        lists.addWidget(panel_a)
        lists.addWidget(panel_b)
        lists.setStretchFactor(0, 1)
        lists.setStretchFactor(1, 1)
        lists.setSizes([230, 230])
        layout.addWidget(lists, 1)
        return browser

    def create_manual_list(self, title, side):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(make_list_title(title))
        image_list = QListWidget()
        image_list.setTextElideMode(Qt.ElideRight)
        if side == 'A':
            image_list.itemClicked.connect(self.on_manual_a_selected)
        else:
            image_list.itemClicked.connect(self.on_manual_b_selected)
        layout.addWidget(image_list)
        return panel, image_list

    def switch_compare_mode(self):
        is_folder_mode = self.mode_selector.currentData() == 'folder'
        self.folder_controls.setVisible(is_folder_mode)
        self.single_controls.setVisible(not is_folder_mode)
        self.browser_stack.setCurrentIndex(0 if is_folder_mode else 1)

    def show_folder_view(self, index):
        if index == 0 and not self.file_pairs:
            index = 1
        self.folder_views.setCurrentIndex(index)
        self.btn_show_auto.setChecked(index == 0)
        self.btn_show_manual.setChecked(index == 1)

    @staticmethod
    def set_path_label(label, path):
        label.setText(os.path.basename(path) or path)
        label.setToolTip(path)

    @staticmethod
    def set_selected_file_label(label, title, path):
        if path:
            label.set_full_text(f'{title}：{os.path.basename(path)}', path)
        else:
            label.set_full_text(f'{title}：未选择')

    def select_dir(self, type_):
        d = QFileDialog.getExistingDirectory(self, f"选择目录 {type_}")
        if not d: return

        if type_ == 'A':
            self.dirA = d
            self.set_path_label(self.lbl_dir_A, d)
            self.btn_sel_dir_a.setProperty('ready', True)
            self.btn_sel_dir_a.style().unpolish(self.btn_sel_dir_a)
            self.btn_sel_dir_a.style().polish(self.btn_sel_dir_a)
        else:
            self.dirB = d
            self.set_path_label(self.lbl_dir_B, d)
            self.btn_sel_dir_b.setProperty('ready', True)
            self.btn_sel_dir_b.style().unpolish(self.btn_sel_dir_b)
            self.btn_sel_dir_b.style().polish(self.btn_sel_dir_b)

        if self.dirA and self.dirB:
            self.scan_files()

    def select_single_image(self, side):
        path, _ = QFileDialog.getOpenFileName(
            self, f"选择{'左' if side == 'A' else '右'}图", '', IMAGE_FILE_FILTER
        )
        if not path:
            return

        if side == 'A':
            self.single_path_a = path
            self.set_path_label(self.lbl_file_a, path)
        else:
            self.single_path_b = path
            self.set_path_label(self.lbl_file_b, path)

        if self.single_path_a and self.single_path_b:
            self.load_image_pair(self.single_path_a, self.single_path_b)

    def scan_files(self):
        self.file_pairs = []
        self.file_list.clear()

        self.folder_files_a = collect_images(self.dirA)
        self.folder_files_b = collect_images(self.dirB)
        files_b_by_relative_path = dict(self.folder_files_b)

        for relative_path, path_a in self.folder_files_a:
            path_b = files_b_by_relative_path.get(relative_path)
            if path_b:
                self.file_pairs.append((relative_path, path_a, path_b))
                self.add_path_item(self.file_list, relative_path, path_a)

        self.populate_manual_lists()

        count = len(self.file_pairs)
        self.folder_summary.setText(
            f"自动匹配：{count} 对 | Result：{len(self.folder_files_a)} 张 | "
            f"GT：{len(self.folder_files_b)} 张"
        )
        self.btn_show_auto.setEnabled(count > 0)

        if count > 0:
            self.show_folder_view(0)
            self.file_list.setCurrentRow(0)
            self.load_auto_pair(0)
            QMessageBox.information(self, "扫描完成", f"共找到 {count} 对自动匹配图片。")
        else:
            self.show_folder_view(1)
            QMessageBox.information(
                self,
                "未找到自动匹配",
                "两个目录中没有同相对路径的图片，已切换到手动配对。"
            )

    def populate_manual_lists(self):
        self.manual_list_a.clear()
        self.manual_list_b.clear()
        self.manual_path_a = ''
        self.manual_path_b = ''
        self.btn_compare_selected.setEnabled(False)
        self.set_selected_file_label(self.lbl_selected_file_a, '左图', '')
        self.set_selected_file_label(self.lbl_selected_file_b, '右图', '')

        for relative_path, absolute_path in self.folder_files_a:
            self.add_path_item(self.manual_list_a, relative_path, absolute_path)
        for relative_path, absolute_path in self.folder_files_b:
            self.add_path_item(self.manual_list_b, relative_path, absolute_path)

    @staticmethod
    def add_path_item(image_list, relative_path, absolute_path):
        image_list.addItem(compact_relative_path(relative_path))
        item = image_list.item(image_list.count() - 1)
        item.setData(Qt.UserRole, absolute_path)
        item.setToolTip(relative_path)

    def on_auto_pair_selected(self, item):
        idx = self.file_list.row(item)
        self.load_auto_pair(idx)

    def load_auto_pair(self, idx):
        if idx < 0 or idx >= len(self.file_pairs): return
        relative_path, path_a, path_b = self.file_pairs[idx]
        self.set_selected_file_label(self.lbl_selected_file_a, '左图', path_a)
        self.set_selected_file_label(self.lbl_selected_file_b, '右图', path_b)
        self.load_image_pair(path_a, path_b)

    def on_manual_a_selected(self, item):
        self.manual_path_a = item.data(Qt.UserRole)
        self.set_selected_file_label(self.lbl_selected_file_a, '左图', self.manual_path_a)
        self.btn_compare_selected.setEnabled(bool(self.manual_path_a and self.manual_path_b))

    def on_manual_b_selected(self, item):
        self.manual_path_b = item.data(Qt.UserRole)
        self.set_selected_file_label(self.lbl_selected_file_b, '右图', self.manual_path_b)
        self.btn_compare_selected.setEnabled(bool(self.manual_path_a and self.manual_path_b))

    def compare_manual_selection(self):
        if not self.manual_path_a or not self.manual_path_b:
            return
        self.load_image_pair(self.manual_path_a, self.manual_path_b)

    def load_image_pair(self, path_a, path_b):
        try:
            img_a = read_image(path_a)
            img_b = read_image(path_b)
        except (OSError, ValueError, cv2.error) as error:
            QMessageBox.warning(self, '无法读取图片', f'{error}')
            return False

        if img_a is None or img_b is None:
            QMessageBox.warning(self, '无法读取图片', '至少有一张图片无法读取。')
            return False

        success, message = self.compare_view.set_images(img_a, img_b)
        if not success:
            QMessageBox.warning(self, '无法进行对比', message)
            return False

        return True

    def toggle_diff_mode(self):
        self.compare_view.toggle_diff()

    def trigger_fit(self):
        self.compare_view.fit_in_view()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = BatchCompareWindow()
    win.show()
    sys.exit(app.exec_())
