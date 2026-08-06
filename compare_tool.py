import sys
import os
import cv2
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QSplitter, QListWidget, QMainWindow
)
from PyQt5.QtGui import QImage, QPixmap, QCursor
from PyQt5.QtCore import Qt, QPoint


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
        self.label = QLabel("请在左侧选择文件")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: #202020; color: #888;")
        self.label.setMouseTracking(True)
        self.label.installEventFilter(self)

        self.info_label = QLabel("坐标: -, 像素值: -")
        self.info_label.setStyleSheet("font-weight: bold; color: #00FF00;")

        # 布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.info_label)
        layout.addWidget(self.label, stretch=1)
        self.setLayout(layout)

    def set_images(self, imgA, imgB):
        """外部调用此方法更新图片"""
        if imgA is None or imgB is None: return

        # 格式统一
        if len(imgA.shape) != len(imgB.shape):
            if len(imgA.shape) == 2: imgA = cv2.cvtColor(imgA, cv2.COLOR_GRAY2BGR)
            if len(imgB.shape) == 2: imgB = cv2.cvtColor(imgB, cv2.COLOR_GRAY2BGR)

        self.imgA = imgA
        self.imgB = imgB
        self.h, self.w = imgA.shape[:2]

        self.split_x = self.w // 2

        # --- 核心修改：每次加载新图，强制执行“适应窗口”逻辑 ---
        self.fit_in_view()

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
        self.setWindowTitle("Batch Image Compare Tool (Auto-Fit)")
        self.resize(1200, 800)

        self.dirA = ""
        self.dirB = ""
        self.file_pairs = []

        # --- UI 组件 ---
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 1. 顶部控制栏
        top_bar = QHBoxLayout()
        self.btn_sel_A = QPushButton("1. 选择目录 Result (A)")
        self.btn_sel_A.clicked.connect(lambda: self.select_dir('A'))
        self.lbl_dir_A = QLabel("未选择")
        self.lbl_dir_A.setStyleSheet("color: gray;")

        self.btn_sel_B = QPushButton("2. 选择目录 GT (B)")
        self.btn_sel_B.clicked.connect(lambda: self.select_dir('B'))
        self.lbl_dir_B = QLabel("未选择")
        self.lbl_dir_B.setStyleSheet("color: gray;")

        self.btn_diff = QPushButton("切换 Diff 模式")
        self.btn_diff.setCheckable(True)
        self.btn_diff.clicked.connect(self.toggle_diff_mode)

        # 增加一个显式的“适配窗口”按钮，万一用户缩放跑偏了可以点
        self.btn_fit = QPushButton("适配窗口 (Fit)")
        self.btn_fit.clicked.connect(self.trigger_fit)

        top_bar.addWidget(self.btn_sel_A)
        top_bar.addWidget(self.lbl_dir_A)
        top_bar.addSpacing(20)
        top_bar.addWidget(self.btn_sel_B)
        top_bar.addWidget(self.lbl_dir_B)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_fit)
        top_bar.addWidget(self.btn_diff)

        # 2. 中间分割布局
        splitter = QSplitter(Qt.Horizontal)

        self.file_list = QListWidget()
        self.file_list.setFixedWidth(250)
        self.file_list.itemClicked.connect(self.on_file_selected)

        self.compare_view = CompareWidget()

        splitter.addWidget(self.file_list)
        splitter.addWidget(self.compare_view)
        splitter.setStretchFactor(1, 1)

        main_layout.addLayout(top_bar)
        main_layout.addWidget(splitter)

    def select_dir(self, type_):
        d = QFileDialog.getExistingDirectory(self, f"选择目录 {type_}")
        if not d: return

        if type_ == 'A':
            self.dirA = d
            self.lbl_dir_A.setText(os.path.basename(d))
            self.btn_sel_A.setStyleSheet("background-color: #d4f0d4;")
        else:
            self.dirB = d
            self.lbl_dir_B.setText(os.path.basename(d))
            self.btn_sel_B.setStyleSheet("background-color: #d4f0d4;")

        if self.dirA and self.dirB:
            self.scan_files()

    def scan_files(self):
        self.file_pairs = []
        self.file_list.clear()

        valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')

        for root, dirs, files in os.walk(self.dirA):
            for file in files:
                if file.lower().endswith(valid_exts):
                    abs_path_A = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path_A, self.dirA)
                    abs_path_B = os.path.join(self.dirB, rel_path)

                    if os.path.exists(abs_path_B):
                        self.file_pairs.append((rel_path, abs_path_A, abs_path_B))
                        self.file_list.addItem(rel_path)

        count = len(self.file_pairs)
        QMessageBox.information(self, "扫描完成", f"共找到 {count} 对匹配图片。")

        if count > 0:
            self.file_list.setCurrentRow(0)
            self.load_pair(0)

    def on_file_selected(self, item):
        idx = self.file_list.row(item)
        self.load_pair(idx)

    def load_pair(self, idx):
        if idx < 0 or idx >= len(self.file_pairs): return
        rel, pathA, pathB = self.file_pairs[idx]

        imgA = read_image(pathA)
        imgB = read_image(pathB)

        if imgA is None or imgB is None: return

        self.compare_view.set_images(imgA, imgB)

    def toggle_diff_mode(self):
        self.compare_view.toggle_diff()

    def trigger_fit(self):
        self.compare_view.fit_in_view()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = BatchCompareWindow()
    win.show()
    sys.exit(app.exec_())