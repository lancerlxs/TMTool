"""
黑色圆圈检测与裁剪工具 - 检测并裁剪JPG文件左侧或右侧的黑色不规则圆圈
运行环境：Windows 7
依赖：PyQt5, Pillow (PIL), OpenCV (可选)
"""

import sys
import os
import re
import math
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QTextEdit, QSpinBox,
                             QFormLayout, QGroupBox, QMessageBox, QCheckBox,
                             QProgressBar, QGraphicsView, QGraphicsScene,
                             QScrollArea, QDoubleSpinBox, QSplitter, QSizePolicy,
                             QFrame, QTabWidget, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal as Signal, QRectF, QSize
from PyQt5.QtGui import QFont, QImage, QPixmap, QPainter, QPen, QColor, QWheelEvent


def _projection_skew(pil_img, max_angle=8.0):
    """
    投影方差法估计偏斜角(度)。返回 (最佳旋转角, 置信比)。
    旋转角 = 让内容水平所需的旋转角(PIL 语义：正值=逆时针)。精度约 0.02°。
    置信比 = 最佳角处水平投影方差 / 0°处方差；>1 真实偏斜，≈1 无偏斜/信号弱。
    预处理：Otsu 二值化 → 去过大连通域(黑斑/边框) → 水平闭运算增强行信号。
    需要 cv2；无 cv2 返回 (0, 1)。
    """
    try:
        import cv2
    except ImportError:
        return 0.0, 1.0

    gray = pil_img.convert('L')
    W, H = gray.size
    sc = 1500.0 / max(W, H)  # 降采样加速
    sw, sh = max(1, int(W * sc)), max(1, int(H * sc))
    small = np.array(gray.resize((sw, sh)))

    # Otsu 自适应二值化（内容为前景）
    _, otsu = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mask = (otsu > 0).astype(np.uint8)

    # 去掉过大的连通域(黑斑/装订孔块/边框等干扰)，保留文字笔画
    n_cc, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    max_area = int(0.0015 * sw * sh)
    keep = np.ones(mask.shape, dtype=bool)
    for i in range(1, n_cc):
        if stats[i, cv2.CC_STAT_AREA] > max_area:
            keep[labels == i] = False
    mask = ((mask > 0) & keep).astype(np.uint8)

    # 水平闭运算：把同一行文字连成横向条带，增强行投影信号
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (41, 1))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    center = (sw / 2.0, sh / 2.0)

    def var_at(ang):
        M = cv2.getRotationMatrix2D(center, ang, 1.0)
        rot = cv2.warpAffine(mask, M, (sw, sh), flags=cv2.INTER_NEAREST)
        return int(rot.sum(axis=1).var())

    v0 = var_at(0.0)
    coarse = max(np.arange(-max_angle, max_angle + 1e-6, 0.1), key=var_at)        # 粗搜 0.1°
    fine = max(np.arange(coarse - 0.1, coarse + 0.1 + 1e-6, 0.02), key=var_at)    # 细搜 0.02°
    ratio = (var_at(fine) / v0) if v0 > 0 else 1.0
    return round(float(fine), 2), round(ratio, 2)


def _hough_skew(pil_img, min_count=30):
    """
    Hough直线法估计偏斜角(度)。返回 (角度, 近水平线根数=置信度)。
    对投影法不敏感的小角度(约1°)文字/表单图更灵敏。
    角度已与 PIL rotate 对齐(正值=逆时针，直接用于纠偏)。需要 cv2；无 cv2 返回 (0, 0)。
    """
    try:
        import cv2
    except ImportError:
        return 0.0, 0

    gray = pil_img.convert('L')
    W, H = gray.size
    sc = 1500.0 / max(W, H)
    sw, sh = max(1, int(W * sc)), max(1, int(H * sc))
    small = np.array(gray.resize((sw, sh)))
    edges = cv2.Canny(small, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                            minLineLength=max(20, sw // 8), maxLineGap=20)
    angs = []
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if ang > 90:
                ang -= 180
            elif ang <= -90:
                ang += 180
            if -8 < ang < 8:  # 近水平线(文字行方向)；真实偏斜<8°，更大角度是斜线/图形
                angs.append(ang)
    if len(angs) >= min_count:
        return round(float(np.median(angs)), 2), len(angs)
    return 0.0, len(angs)


def _estimate_skew(pil_img, max_angle=8.0):
    """
    估计图像内容偏斜角(度)。返回 (旋转角, 置信比)。
    优先用投影方差法；若其信号弱(置信比<1.2)，回退到 Hough 直线法
    (对小角度约1°的文字/表单图更灵敏)。两种方法的角度都已与 PIL rotate 对齐。
    """
    ang, ratio = _projection_skew(pil_img, max_angle)
    if ratio >= 1.2 and abs(ang) >= 0.1:
        return ang, ratio
    # 投影法信号不足：回退 Hough 直线法
    ang_h, conf = _hough_skew(pil_img)
    if conf >= 30 and abs(ang_h) >= 0.1:
        return ang_h, 2.0  # Hough 高置信，合成 ratio 让 _deskew_image 放行
    return 0.0, 1.0


def _deskew_image(pil_img, fillcolor=(255, 255, 255), min_angle=0.1, min_ratio=1.2):
    """
    对图像做纯旋转纠偏(自动检测)。返回 (结果Image, 应用的角度；未纠偏时为 0.0)。
    仅当 |偏斜角|>=min_angle(0.1°) 且 置信比>=min_ratio(1.2) 时才纠偏。
    真实偏斜经预处理后置信比通常>=1.3，平整页≈1.0；1.2 兼顾灵敏与抗误报。
    纯旋转(无缩放/剪切)→ 内容不变形；expand=False 保持原尺寸，
    旋出的边角用 fillcolor 填充(默认白)。
    """
    ang, ratio = _estimate_skew(pil_img)
    if abs(ang) < min_angle or ratio < min_ratio:
        return pil_img, 0.0
    out = pil_img.rotate(ang, resample=Image.BICUBIC, expand=False, fillcolor=fillcolor)
    return out, ang


class CircleDetectionWorker(QThread):
    """黑色圆圈检测后台工作线程（多线程处理）"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    result_signal = Signal(list)  # 发送处理结果列表
    finished_signal = Signal(bool, str)
    file_done_signal = Signal(str)  # 单个文件处理完成后发射其输出路径

    def __init__(self, input_dir, output_dir, max_diameter_mm=25, margin_mm=40, deskew=False, remove_border=True, thread_count=4, edge_cover=False, edge_margin_mm=2.0, dpi=300, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.max_diameter_mm = max_diameter_mm
        self.margin_mm = margin_mm
        self.deskew = deskew
        self.remove_border = remove_border
        self.thread_count = thread_count
        self.edge_cover = edge_cover
        self.edge_margin_mm = edge_margin_mm
        self.is_stopped = False
        self.dpi_assumption = dpi
        self.max_diameter_pixels = int(self.max_diameter_mm * self.dpi_assumption / 25.4)
        self.margin_pixels = int(self.margin_mm * self.dpi_assumption / 25.4)
        self.edge_margin_pixels = int(self.edge_margin_mm * self.dpi_assumption / 25.4) if self.edge_cover else 0

    def run(self):
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading

            jpg_files = []
            for root, dirs, files in os.walk(self.input_dir):
                if self.is_stopped:
                    break
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg')):
                        jpg_files.append(os.path.join(root, filename))

            def _natural_key(path):
                return [int(t) if t.isdigit() else t.lower()
                        for t in re.split(r'(\d+)', path)]
            jpg_files.sort(key=_natural_key)

            total = len(jpg_files)
            if total == 0:
                self.finished_signal.emit(False, "未找到任何JPG/JPEG文件")
                return

            self.log_signal.emit(f"找到 {total} 个JPG文件，{self.thread_count}线程并行处理...")

            results = []
            processed = [0]
            deskew_count = [0]
            holed_file_count = [0]
            hole_count_total = [0]
            lock = threading.Lock()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(self.output_dir, f"处理日志_{timestamp}.txt")
            os.makedirs(self.output_dir, exist_ok=True)
            logf = open(log_path, 'w', encoding='utf-8')
            log_lock = threading.Lock()

            def wlog(s):
                with log_lock:
                    logf.write(s + "\n")
                    logf.flush()

            wlog("黑色圆洞（装订孔）检测与裁剪 - 处理日志")
            wlog(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            wlog(f"输入目录: {self.input_dir}")
            wlog(f"输出目录: {self.output_dir}")
            wlog(f"圆圈最大直径: {self.max_diameter_mm}mm；纠偏: {'开启' if self.deskew else '关闭'}；线程数: {self.thread_count}")
            wlog("=" * 70)

            def process_one(jpg_path, idx):
                if self.is_stopped:
                    return
                self.log_signal.emit(f"处理中: {os.path.basename(jpg_path)}")
                wlog(f"[{idx}/{total}] 正在处理: {jpg_path}")
                try:
                    result = self.process_image(jpg_path)
                except Exception as e:
                    result = {'path': jpg_path, 'filename': os.path.basename(jpg_path),
                              'success': False, 'error_msg': str(e),
                              'circles_found': 0, 'deskew_angle': 0.0}
                with lock:
                    results.append(result)
                    holes = result.get('circles_found', 0)
                    hole_count_total[0] += holes
                    if holes > 0:
                        holed_file_count[0] += 1
                    da = result.get('deskew_angle', 0.0) or 0.0
                    if da:
                        deskew_count[0] += 1
                    processed[0] += 1
                    if result['success']:
                        parts = [f"✓ {os.path.basename(jpg_path)}"]
                        if self.deskew:
                            parts.append(f"纠偏{da}°" if da else "无需纠偏")
                        parts.append(f"装订孔{holes}个" if holes else "无装订孔")
                        self.log_signal.emit("  ".join(parts))
                    else:
                        self.log_signal.emit(f"✗ {os.path.basename(jpg_path)} - 失败 {result.get('error_msg', '')}")
                    wlog(f"  装订孔: {'检测并填充 %d 个' % holes if holes else '未检测到'}")
                    if self.deskew:
                        wlog(f"  纠偏: {'已纠正 %.2f°' % da if da else '无明显偏斜，未纠偏'}")
                    wlog(f"  结果: {'成功' if result['success'] else '失败: ' + str(result.get('error_msg', ''))}")
                    wlog(f"  输出: {result.get('output_path', '')}")
                    if result['success'] and result.get('output_path'):
                        self.file_done_signal.emit(result['output_path'])
                    self.progress_signal.emit(processed[0], total)

            with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
                futures = {}
                for idx, jpg_path in enumerate(jpg_files, 1):
                    if self.is_stopped:
                        break
                    future = executor.submit(process_one, jpg_path, idx)
                    futures[future] = jpg_path
                for future in as_completed(futures):
                    if self.is_stopped:
                        for f in futures:
                            f.cancel()
                        break
                    future.result()

            wlog("=" * 70)
            wlog(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            success_count = sum(1 for r in results if r['success'])
            wlog(f"总计文件: {processed[0]}（成功 {success_count}，失败 {processed[0] - success_count}）")
            wlog(f"去装订孔: {holed_file_count[0]} 个文件，共 {hole_count_total[0]} 个孔")
            wlog(f"纠偏: {deskew_count[0]} 个文件")
            if self.is_stopped:
                wlog("注意：处理被用户中途停止")
            logf.close()
            self.log_signal.emit(f"已生成处理日志: {os.path.basename(log_path)}")

            if not self.is_stopped:
                self.result_signal.emit(results)
                msg = (f"处理完成！共 {processed[0]} 个文件，成功 {success_count}；"
                       f"去孔 {holed_file_count[0]} 文件/{hole_count_total[0]} 个；"
                       f"纠偏 {deskew_count[0]} 个文件。日志: {os.path.basename(log_path)}")
                self.finished_signal.emit(True, msg)
            else:
                self.finished_signal.emit(False, f"处理已停止。日志: {os.path.basename(log_path)}")

        except Exception as e:
            self.finished_signal.emit(False, f"处理出错: {str(e)}")

    def stop(self):
        self.is_stopped = True

    def process_image(self, image_path):
        """
        处理单个图像：检测打孔洞并用白色填充。返回处理结果字典。
        """
        try:
            # 档案扫描图通常较大：解除 PIL 默认大图限制，容错截断图
            Image.MAX_IMAGE_PIXELS = None
            Image.LOAD_TRUNCATED_IMAGES = True
            img = Image.open(image_path)
            img.load()  # 立即解码，及时暴露损坏文件
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            # 可选：纠偏(去倾斜)——纯旋转，内容不变形；之后再做圆洞检测
            deskew_applied = 0.0
            if self.deskew:
                img, deskew_applied = _deskew_image(img)
            orig_w, orig_h = img.size

            # --- 先检测+填充装订孔（在去黑边之前！）---
            # 去黑边用更宽的灰度阈值(page_bg-60)，会把孔和附近的暗块连成大块一并填掉，
            # 导致后续检测不到孔。先在 <50 严格阈值上检测孔，填充后再去黑边。
            arr = np.array(img)
            gray_full = (np.mean(arr, axis=2).astype(np.uint8) if arr.ndim == 3 else arr.copy())
            mask_full = gray_full < 50  # 装订孔检测阈值(灰度<50=足够暗)
            circles_info = self.detect_edge_holes(mask_full, orig_w, orig_h)
            del arr, gray_full, mask_full
            circles_info = self._dedup_circles(circles_info)

            if circles_info:
                img = self.crop_circles(img, circles_info)

            # --- 再去黑边/阴影（孔已填充为底色，不会被误连）---
            if self.remove_border:
                img, _br = self.remove_black_border(img)

            # --- 边缘底色覆盖：将四周边缘区域用底色覆盖 ---
            if self.edge_cover and self.edge_margin_pixels > 0:
                img = self.cover_edge_with_bg(img, self.edge_margin_pixels)

            # 输出路径（保持原目录结构），确保每个文件都写入目标目录
            rel_path = os.path.relpath(image_path, self.input_dir)
            output_path = os.path.join(self.output_dir, rel_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if circles_info:
                img.save(output_path, quality=95)
            else:
                # 未检测到圆洞：检查去黑边是否改了图
                img.save(output_path, quality=95)

            return {
                'path': image_path,
                'filename': os.path.basename(image_path),
                'success': True,
                'circles_found': len(circles_info),
                'deskew_angle': deskew_applied,
                'output_path': output_path,
                'preview_before': image_path,
                'preview_after': output_path
            }

        except Exception as e:
            return {
                'path': image_path,
                'filename': os.path.basename(image_path),
                'success': False,
                'error_msg': str(e),
                'circles_found': 0,
                'deskew_angle': 0.0
            }

    def detect_detection_boundaries(self, black_mask, img_width, img_height):
        """
        智能检测左右边界：
        1. 检测最左和最右的文字位置
        2. 检测长竖线位置
        3. 根据检测结果确定检测区域
        
        返回: (left_boundary, right_boundary)
        """
        # 计算每列的黑色像素数量（垂直投影）
        column_sums = np.sum(black_mask, axis=0)
        
        # 检测长竖线：连续多列都有较多黑色像素
        vertical_line_threshold = img_height * 0.3  # 竖线至少覆盖30%高度
        min_vertical_line_cols = 2  # 至少2列连续
        
        left_vertical_line_x = None
        right_vertical_line_x = None
        
        # 查找左侧最近的竖线
        consecutive_cols = 0
        for x in range(img_width):
            if column_sums[x] >= vertical_line_threshold:
                consecutive_cols += 1
                if consecutive_cols >= min_vertical_line_cols and left_vertical_line_x is None:
                    left_vertical_line_x = x
            else:
                consecutive_cols = 0
        
        # 查找右侧最近的竖线
        consecutive_cols = 0
        for x in range(img_width - 1, -1, -1):
            if column_sums[x] >= vertical_line_threshold:
                consecutive_cols += 1
                if consecutive_cols >= min_vertical_line_cols and right_vertical_line_x is None:
                    right_vertical_line_x = x
            else:
                consecutive_cols = 0
        
        # 检测文字边界：使用连通分量分析区分文字和圆圈
        # 优先用 cv2（C 实现，极快）；无 cv2 时回退到纯 Python 实现
        num_fg, stats = self._connected_components_with_stats(black_mask)

        # 找出所有连通区域的边界框，并分类
        text_leftmost = img_width
        text_rightmost = 0
        has_text_or_lines = False

        for min_row, min_col, max_row, max_col, pixel_count in self._iter_components(num_fg, stats):
            if pixel_count < 10:  # 忽略太小的区域（可能是噪点或小圆圈）
                continue

            height = max_row - min_row
            width = max_col - min_col
            area = height * width

            # 圆形候选（尺寸<=最大直径且接近方形）不当作“文字/线”。
            # 否则实心黑圆洞会因密度高被归为内容，把检测边界推到圆洞之外导致漏检。
            diameter = max(height, width)
            aspect = diameter / max(min(height, width), 1)
            if diameter <= self.max_diameter_pixels and aspect <= 3:
                continue

            # 判断是否为文字或竖线（而非圆圈）
            # 文字/竖线特征：
            # 1. 高度较大（超过图像高度5%）
            # 2. 或者宽高比异常（细长形状）
            # 3. 或者像素密度较高（实心区域）
            pixel_density = pixel_count / area if area > 0 else 0

            is_text_or_line = (
                (height > img_height * 0.05) or  # 高度超过5%
                (width > height * 2) or           # 宽远大于高（横线）
                (height > width * 2) or           # 高远大于宽（竖线）
                (pixel_density > 0.3 and pixel_count > 100)  # 高密度大区域
            )

            if is_text_or_line:
                has_text_or_lines = True
                text_leftmost = min(text_leftmost, min_col)
                text_rightmost = max(text_rightmost, max_col)
        
        # 情况3：没有文字和竖线，使用全图检测
        if not has_text_or_lines:
            return 0, img_width
        
        # 确定最终检测边界
        # 左侧：取竖线和文字中更靠外的
        if left_vertical_line_x is not None:
            left_boundary = min(left_vertical_line_x, text_leftmost)
        else:
            left_boundary = text_leftmost
        
        # 右侧：取竖线和文字中更靠外的
        if right_vertical_line_x is not None:
            right_boundary = max(right_vertical_line_x, text_rightmost)
        else:
            right_boundary = text_rightmost
        
        # 添加边距容差（15像素），确保能覆盖边缘的圆圈
        margin_tolerance = 15
        left_boundary = max(0, left_boundary - margin_tolerance)
        right_boundary = min(img_width, right_boundary + margin_tolerance)
        
        # 确保检测区域有效
        if left_boundary <= 0:
            left_boundary = 0
        if right_boundary >= img_width:
            right_boundary = img_width
        
        return left_boundary, right_boundary

    def find_black_circles_smart(self, black_mask, img_width, img_height, left_boundary, right_boundary):
        """
        在智能确定的检测区域内查找黑色圆圈
        返回圆圈信息列表：[(center_x, center_y, radius), ...]
        """
        circles = []
        searched = False

        # 提取左侧检测区域（从左边界到图像左边缘）
        if 0 < left_boundary < img_width:
            left_region = black_mask[:, :left_boundary]
            circles.extend(self.detect_circle_region(left_region, 0, img_height))
            searched = True

        # 提取右侧检测区域（从右边界到图像右边缘）
        if 0 < right_boundary < img_width:
            right_region = black_mask[:, right_boundary:]
            circles.extend(self.detect_circle_region(right_region, right_boundary, img_height))
            searched = True

        # 无边距区可搜（纯圆洞图、无文字内容，或内容占满全图）→ 全图检测，避免漏检
        if not searched:
            circles.extend(self.detect_circle_region(black_mask, 0, img_height))

        return circles

    def detect_edge_holes(self, mask, img_w, img_h):
        """Edge band hole detection (single pass, default solidity)."""
        mp = self.margin_pixels
        candidates = []
        if 0 < mp < img_w // 2:
            for cx, cy, r in self.detect_circle_region(mask[:, :mp], 0, img_h):
                candidates.append((cx, cy, r, 'L'))
            for cx, cy, r in self.detect_circle_region(mask[:, img_w - mp:], img_w - mp, img_h):
                candidates.append((cx, cy, r, 'R'))
        if 0 < mp < img_h // 2:
            for cx, cy, r in self.detect_circle_region(mask[:mp, :], 0, mp):
                candidates.append((cx, cy, r, 'T'))
            for cx, cy, r in self.detect_circle_region(mask[img_h - mp:, :], 0, mp):
                candidates.append((cx, cy + (img_h - mp), r, 'B'))
        return self._filter_punch_holes(candidates, img_w, img_h)

    def _filter_punch_holes(self, candidates, img_w, img_h):
        """Filter punch holes from edge candidates."""
        if not candidates:
            return []
        band = self.margin_pixels * 0.5
        tol = max(self.max_diameter_pixels / 4, 1)
        floor = self.max_diameter_pixels * 0.03

        from collections import defaultdict
        by_edge = defaultdict(list)
        for cx, cy, r, edge in candidates:
            # 距最近纸边的距离（四条边取最小）
            if min(cx, img_w - 1 - cx, cy, img_h - 1 - cy) <= band:
                by_edge[edge].append((cx, cy, r))

        kept = []
        for edge, comps in by_edge.items():
            vertical = edge in ('L', 'R')
            key_idx = 0 if vertical else 1   # 竖向边按 x 聚列，横向边按 y 聚排
            cols = []
            for c in sorted(comps, key=lambda c: c[key_idx]):
                placed = False
                for col in cols:
                    if abs(col[0][key_idx] - c[key_idx]) <= tol:
                        col.append(c)
                        placed = True
                        break
                if not placed:
                    cols.append([c])
            min_iso = self.max_diameter_pixels * 0.045
            for col in cols:
                if len(col) >= 2:
                    thresh = max(floor, max(c[2] for c in col) * 0.5)
                    for cx, cy, r in col:
                        if r >= thresh:
                            kept.append((cx, cy, r))
                else:
                    cx, cy, r = col[0]
                    if r >= min_iso:
                        kept.append((cx, cy, r))
        return kept

    @staticmethod
    def _dedup_circles(circles):
        """按中心距离去重(中心距 < 较小半径视为同一圆)。"""
        unique = []
        for cx, cy, r in circles:
            r = int(r)
            is_dup = False
            for ux, uy, ur in unique:
                if (cx - ux) ** 2 + (cy - uy) ** 2 < min(r, int(ur)) ** 2:
                    is_dup = True
                    break
            if not is_dup:
                unique.append((int(cx), int(cy), r))
        return unique

    def find_black_circles(self, black_mask, img_width, img_height):
        """
        在黑色掩码中查找圆形区域（仅在两侧边距范围内检测）
        返回圆圈信息列表：[(center_x, center_y, radius), ...]
        """
        circles = []
        
        # 计算左右两侧的边界（仅检测距离边缘margin_pixels范围内的区域）
        left_boundary = self.margin_pixels  # 左侧检测区域的右边界
        right_boundary = img_width - self.margin_pixels  # 右侧检测区域的左边界
        
        # 确保边界有效
        if left_boundary <= 0 or right_boundary >= img_width or left_boundary >= right_boundary:
            # 如果图像宽度太小，无法划分边距区域，则不检测
            return circles
        
        # 提取左侧边距区域（从左边到left_boundary）
        left_region = black_mask[:, :left_boundary]
        # 提取右侧边距区域（从right_boundary到右边）
        right_region = black_mask[:, right_boundary:]

        # 检测左侧圆圈（offset_x为0，因为是从x=0开始）
        left_circles = self.detect_circle_region(left_region, 0, img_height)
        circles.extend(left_circles)

        # 检测右侧圆圈（offset_x为right_boundary，因为是从right_boundary开始）
        right_circles = self.detect_circle_region(right_region, right_boundary, img_height)
        circles.extend(right_circles)

        return circles

    def detect_circle_region(self, region_mask, offset_x, img_height):
        """
        在指定区域检测黑色圆圈
        """
        circles = []
        height, width = region_mask.shape
        
        # 查找黑色像素的行和列
        black_rows, black_cols = np.where(region_mask)
        
        if len(black_rows) == 0:
            return circles

        # 简单的聚类方法：将接近的黑色像素归为一组
        min_distance = self.max_diameter_pixels // 2
        
        # 使用连通分量标记（优先 cv2，极快）
        num_fg, stats = self._connected_components_with_stats(region_mask)

        for min_row, min_col, max_row, max_col, pixel_count in self._iter_components(num_fg, stats):
            # 降低最小像素数要求，以检测小圆圈（从10降到5）
            if pixel_count < 5:  # 忽略太小的噪点
                continue

            # 计算直径
            diameter = max(max_row - min_row, max_col - min_col)

            # 检查是否符合圆圈尺寸要求
            if diameter > self.max_diameter_pixels:
                continue
            # 实际装订孔半径通常 15-40px；超过 max_diameter*0.2(~59px=10mm半径) 的大块
            # 不是装订孔而是印章/图形/表格区
            if diameter > self.max_diameter_pixels * 0.4:
                continue

            # 额外检查：确保是近似圆形的（不是细长的线）
            # 宽高比 = 长边 / 短边（短边至少为1，避免除零）。圆≈1.0，细线条会很大。
            aspect_ratio = max(max_row - min_row, max_col - min_col) / max(min(max_row - min_row, max_col - min_col), 1)
            if aspect_ratio > 3:  # 如果宽高比超过3，可能是线条而非圆圈
                continue

            # 实心度(solidity)：真圆洞(实心圆盘)密度高(≈0.78)；手写笔画/线条密度低
            bw, bh = max_col - min_col, max_row - min_row
            solidity = pixel_count / (bh * bw) if bh * bw > 0 else 0
            min_big_diam = self.max_diameter_pixels * 0.09
            if not (solidity >= 0.5 or (solidity >= 0.40 and diameter >= min_big_diam)):
                continue

            # 计算中心点和半径
            center_y = (min_row + max_row) // 2
            center_x = (min_col + max_col) // 2 + offset_x
            radius = diameter // 2

            circles.append((center_x, center_y, radius))

        return circles

    def label_connected_components(self, binary_mask):
        """
        简单的连通分量标记算法（4连通）- 不使用scipy
        返回标记后的数组和特征数量
        """
        height, width = binary_mask.shape
        labeled = np.zeros((height, width), dtype=int)
        current_label = 0
        
        # 简化的洪水填充算法
        visited = np.zeros((height, width), dtype=bool)
        
        for y in range(height):
            for x in range(width):
                if binary_mask[y, x] and not visited[y, x]:
                    current_label += 1
                    # BFS洪水填充
                    queue = [(y, x)]
                    visited[y, x] = True
                    labeled[y, x] = current_label
                    
                    while queue:
                        cy, cx = queue.pop(0)
                        # 检查4个方向的邻居
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < height and 0 <= nx < width:
                                if binary_mask[ny, nx] and not visited[ny, nx]:
                                    visited[ny, nx] = True
                                    labeled[ny, nx] = current_label
                                    queue.append((ny, nx))
        
        return labeled, current_label

    def _connected_components_with_stats(self, binary_mask):
        """
        连通域分析，返回 (num_fg, stats)。
        - num_fg: 前景连通域数量
        - stats: (num_fg+1, 5) 数组，每行 [left, top, width, height, area]；
                 第 0 行为背景/占位，前景连通域为 1..num_fg。
        优先用 cv2（C 实现，比纯 Python 洪水填充快上百倍，且直接给出 bbox/面积，
        无需逐域 np.where 扫描）；cv2 不可用时回退到 label_connected_components +
        逐域统计（与原实现等价，仅较慢）。
        """
        mask_u8 = binary_mask.astype(np.uint8)
        try:
            import cv2
            # connectivity=4，与原 label_connected_components 的 4 连通保持一致
            # 注意：必须用关键字传参，位置参数 4 会被当作 ltype 而非 connectivity
            num, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask_u8, connectivity=4)
            # cv2 的 num 含背景(label 0)，前景数 = num-1；stats[0] 为背景
            return num - 1, stats
        except Exception:
            labels, num_fg = self.label_connected_components(binary_mask)
            stats = self._build_stats_from_labels(labels, num_fg)
            return num_fg, stats

    @staticmethod
    def _build_stats_from_labels(labels, num_fg):
        """由标记图构建 stats 数组（cv2 不可用时的回退路径，语义对齐 cv2）。"""
        stats = np.zeros((num_fg + 1, 5), dtype=np.int64)
        for lab in range(1, num_fg + 1):
            ys, xs = np.where(labels == lab)
            if ys.size == 0:
                continue
            xmin, xmax = int(xs.min()), int(xs.max())
            ymin, ymax = int(ys.min()), int(ys.max())
            stats[lab, 0] = xmin                       # left
            stats[lab, 1] = ymin                       # top
            stats[lab, 2] = xmax - xmin + 1           # width
            stats[lab, 3] = ymax - ymin + 1           # height
            stats[lab, 4] = ys.size                    # area(pixel count)
        return stats

    @staticmethod
    def _iter_components(num_fg, stats):
        """
        生成每个前景连通域的 (min_row, min_col, max_row, max_col, pixel_count)。
        语义与原 np.where(labeled==label) 计算的边界框完全一致，供检测逻辑直接复用。
        """
        for i in range(1, num_fg + 1):
            left = int(stats[i, 0])
            top = int(stats[i, 1])
            w = int(stats[i, 2])
            h = int(stats[i, 3])
            area = int(stats[i, 4])
            yield top, left, top + h - 1, left + w - 1, area

    def crop_circles(self, img, circles_info):
        """
        用与底色一致的颜色填充圆洞区域：在每个圆洞外围采样局部背景色再填充。
        白底图填白、彩底图填对应底色，避免彩色底图上出现刺眼白斑。
        """
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)
        arr = np.array(img)  # 原始未绘制状态，用于采样背景色
        H, W = arr.shape[:2]
        rgb = arr.ndim == 3

        for center_x, center_y, radius in circles_info:
            padding = max(5, radius // 10)
            adjusted_radius = radius + padding

            x1 = max(0, int(center_x - adjusted_radius))
            y1 = max(0, int(center_y - adjusted_radius))
            x2 = min(W, int(center_x + adjusted_radius))
            y2 = min(H, int(center_y + adjusted_radius))

            # 在填充框外围采样背景色：取亮度较高的像素(排除暗的圆洞/文字)，中位数作为底色
            s = max(4, adjusted_radius // 3)
            sx1, sy1 = max(0, x1 - s), max(0, y1 - s)
            sx2, sy2 = min(W, x2 + s), min(H, y2 + s)
            sample = arr[sy1:sy2, sx1:sx2]
            if rgb:
                bright = sample[sample.mean(axis=2) > 80]
                color = tuple(int(v) for v in np.median(bright, axis=0)) if len(bright) else (255, 255, 255)
            else:
                bright = sample[sample > 80]
                color = int(np.median(bright)) if bright.size else 255

            draw.ellipse([x1, y1, x2, y2], fill=color)

        return img_copy

    def remove_black_border(self, img):
        """
        去除扫描黑边/阴影：检测靠近纸边、明显比页面底色暗的大块连通域
        (深色长条、灰色阴影三角等)，用页面底色填充。
        只处理“靠近边缘且足够大”的暗块，不动正文与远处内容。返回 (结果Image, 被填充像素数)。
        """
        try:
            import cv2
        except ImportError:
            return img, 0

        arr = np.array(img)
        H, W = arr.shape[:2]
        rgb = arr.ndim == 3
        gray = (arr.mean(axis=2).astype(np.uint8) if rgb else arr.copy())

        # 页面底色亮度(取偏亮的 75 分位，避免被暗块/文字拉低)
        page_bg = float(np.percentile(gray, 75))
        thr = page_bg - 60           # 比底色暗 60 以上视为边/阴影
        darkish = (gray < thr).astype(np.uint8)

        # 填充用底色(取接近底色亮度的像素中位 RGB)
        bgmask = gray >= (page_bg - 20)
        if rgb:
            bgpx = arr[bgmask]
            bg = tuple(int(v) for v in np.median(bgpx.reshape(-1, 3), axis=0)) if len(bgpx) else (255, 255, 255)
        else:
            bg = int(np.median(arr[bgmask])) if bgmask.any() else 255

        n, labels, stats, _ = cv2.connectedComponentsWithStats(darkish, 8)

        # 局部纹理(15x15 窗标准差)：二维码/条码等高频内容纹理高，真实黑边/阴影平滑(低)
        gf = gray.astype(np.float32)
        gmean = cv2.blur(gf, (15, 15))
        gsq = cv2.blur(gf * gf, (15, 15))
        local_std = np.sqrt(np.maximum(gsq - gmean * gmean, 0))

        min_area = int(0.0015 * W * H)  # 只处理大块，避免误删靠边文字(文字纹理高会被上面跳过)
        fill = np.zeros((H, W), dtype=bool)
        for i in range(1, n):
            a = stats[i, cv2.CC_STAT_AREA]
            if a < min_area:
                continue
            l = stats[i, cv2.CC_STAT_LEFT]; t = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]; h = stats[i, cv2.CC_STAT_HEIGHT]
            r = l + w; b = t + h
            # 靠近某条纸边(各自按该方向尺寸的10%)
            if not ((l < 0.1 * W) or (r > 0.9 * W) or (t < 0.1 * H) or (b > 0.9 * H)):
                continue
            # 面积过大(>12%)的不是边框，是大面积内容/底色
            if a > 0.12 * W * H:
                continue
            # 深度检查：至少有一条边，组件向内延伸不超过该方向30%
            # (否则是大面积浅灰底/内容区，不是边框/阴影)
            depth_ok = ((l < 0.1 * W and r < 0.3 * W) or
                        (r > 0.9 * W and (W - l) < 0.3 * W) or
                        (t < 0.1 * H and b < 0.3 * H) or
                        (b > 0.9 * H and (H - t) < 0.3 * H))
            if not depth_ok:
                continue
            comp = labels == i
            # 纹理检查：横贯全幅(>75%宽)的顶部/底部条，或纵贯全幅(>75%高)的左/右条，
            # 不论纹理都去除(它们是整幅黑条，纹理来自边缘过渡而非文字)。
            # 其余局部暗块：实心黑(均值<60)直接去；灰色阴影若>10%含高纹理(文字)则跳过
            spans_full = (w > 0.75 * W and (t < 0.1 * H or b > 0.9 * H)) or \
                         (h > 0.75 * H and (l < 0.1 * W or r > 0.9 * W))
            if not spans_full:
                comp_mean_gray = float(gray[comp].mean())
                if comp_mean_gray >= 60 and (local_std[comp] > 50).mean() > 0.10:
                    continue
            fill |= comp

        # ---- 额外：边缘细长扫描线(细灰线) —— 仅当其周边无文字时填充 ----
        for i in range(1, n):
            a = stats[i, cv2.CC_STAT_AREA]
            if a < 40:
                continue
            l = stats[i, cv2.CC_STAT_LEFT]; t = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]; h = stats[i, cv2.CC_STAT_HEIGHT]
            r = l + w; b = t + h
            # 靠近某条纸边(6%内)
            if not ((l < 0.06 * W) or (r > 0.94 * W) or (t < 0.06 * H) or (b > 0.94 * H)):
                continue
            longe = max(w, h); short = min(w, h)
            if longe < 40 or short > 25 or longe / max(short, 1) < 4:
                continue  # 不是细长线
            # 检查"内侧"(朝图像中心一侧)邻域是否有文字：暗像素占比>10%视为有文字
            gap = 15
            vertical = h > w
            if vertical:
                y0, y1 = max(0, t - gap), min(H, b + gap)
                band = darkish[y0:y1, max(0, l - gap):l] if r > 0.94 * W else darkish[y0:y1, r:min(W, r + gap)]
            else:
                x0, x1 = max(0, l - gap), min(W, r + gap)
                band = darkish[max(0, t - gap):t, x0:x1] if b > 0.94 * H else darkish[b:min(H, b + gap), x0:x1]
            if band.size == 0 or band.mean() > 0.10:
                continue  # 内侧有文字，不处理
            fill |= (labels == i)

        if not fill.any():
            return img, 0
        out_arr = arr.copy()
        out_arr[fill] = bg
        return Image.fromarray(out_arr), int(fill.sum())

    def cover_edge_with_bg(self, img, margin_px):
        """
        将图像四周边缘 margin_px 像素宽度的区域用底色覆盖。
        底色通过采样四角区域的中位数获得。
        """
        arr = np.array(img)
        H, W = arr.shape[:2]
        rgb = arr.ndim == 3

        # 采样四角区域获取底色
        corner = max(10, margin_px // 2)
        corners = [
            arr[0:corner, 0:corner],
            arr[0:corner, W - corner:W],
            arr[H - corner:H, 0:corner],
            arr[H - corner:H, W - corner:W],
        ]
        samples = np.concatenate([c.reshape(-1, c.shape[-1]) if rgb else c.reshape(-1) for c in corners])
        if rgb:
            bright = samples[samples.mean(axis=1) > 80]
            bg_color = tuple(int(v) for v in np.median(bright, axis=0)) if len(bright) else (255, 255, 255)
        else:
            bright = samples[samples > 80]
            bg_color = int(np.median(bright)) if bright.size else 255

        out = arr.copy()
        # 上边
        out[:margin_px, :] = bg_color
        # 下边
        out[H - margin_px:, :] = bg_color
        # 左边（排除已处理的上下角）
        out[margin_px:H - margin_px, :margin_px] = bg_color
        # 右边
        out[margin_px:H - margin_px, W - margin_px:] = bg_color

        return Image.fromarray(out)


class ZoomableImageView(QGraphicsView):
    """支持缩放和边距红框叠加的图像预览视图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = None
        self._margin_rect_item = None
        self._scale_factor = 1.0
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setStyleSheet("background-color: #1a1a2e; border: 1px solid #30363D; border-radius: 3px;")
        self._img_width = 0
        self._img_height = 0

    def set_image(self, pil_image, margin_mm=0, dpi=300):
        """设置显示的PIL图像，可选绘制边距红框"""
        if pil_image is None:
            return
        rgb = pil_image.convert('RGB')
        data = rgb.tobytes('raw', 'RGB')
        qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self._img_width = rgb.width
        self._img_height = rgb.height

        self._scene.clear()
        self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self._pixmap_item = self._scene.addPixmap(pixmap)

        if margin_mm > 0:
            px = int(margin_mm * dpi / 25.4)
            pen = QPen(QColor(255, 0, 0), max(2, int(max(rgb.width, rgb.height) / 500)))
            self._margin_rect_item = self._scene.addRect(
                QRectF(px, px, max(0, rgb.width - 2 * px), max(0, rgb.height - 2 * px)), pen)
        else:
            self._margin_rect_item = None

        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._scale_factor = 1.0

    def clear_image(self):
        self._scene.clear()
        self._pixmap_item = None
        self._margin_rect_item = None
        self._img_width = 0
        self._img_height = 0

    def zoom_in(self):
        self._scale_factor *= 1.25
        self.scale(1.25, 1.25)

    def zoom_out(self):
        self._scale_factor /= 1.25
        self.scale(1 / 1.25, 1 / 1.25)

    def fit_to_view(self):
        if self._pixmap_item:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._scale_factor = 1.0

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()


class PreviewPanel(QWidget):
    """单个预览面板：包含导航、缩放、图像视图和路径显示"""
    nav_changed = Signal()  # 当用户切换页面时发出

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题栏
        header = QLabel(title)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #00F0FF; font-size: 14px; font-weight: bold; padding: 2px;")
        layout.addWidget(header)

        # 导航栏
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("◀ 上一页")
        self.prev_btn.setObjectName("BrowseBtn")
        self.prev_btn.setFixedWidth(90)
        self.next_btn = QPushButton("下一页 ▶")
        self.next_btn.setObjectName("BrowseBtn")
        self.next_btn.setFixedWidth(90)
        self.page_label = QLabel("0 / 0")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("color: #E0E0E0; font-size: 12px;")
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.page_label, 1)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        # 图像视图
        self.image_view = ZoomableImageView()
        self.image_view.setMinimumHeight(300)
        layout.addWidget(self.image_view, 1)

        # 缩放按钮栏
        zoom_bar = QHBoxLayout()
        self.zoom_in_btn = QPushButton("放大 +")
        self.zoom_in_btn.setObjectName("BrowseBtn")
        self.zoom_in_btn.setFixedWidth(70)
        self.zoom_out_btn = QPushButton("缩小 −")
        self.zoom_out_btn.setObjectName("BrowseBtn")
        self.zoom_out_btn.setFixedWidth(70)
        self.fit_btn = QPushButton("适应窗口")
        self.fit_btn.setObjectName("BrowseBtn")
        self.fit_btn.setFixedWidth(80)
        zoom_bar.addWidget(self.zoom_in_btn)
        zoom_bar.addWidget(self.zoom_out_btn)
        zoom_bar.addWidget(self.fit_btn)
        zoom_bar.addStretch()
        layout.addLayout(zoom_bar)

        # 文件路径
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #8B949E; font-size: 14px; padding: 3px;")
        layout.addWidget(self.path_label)

        # 连接缩放按钮
        self.zoom_in_btn.clicked.connect(self.image_view.zoom_in)
        self.zoom_out_btn.clicked.connect(self.image_view.zoom_out)
        self.fit_btn.clicked.connect(self.image_view.fit_to_view)

        self._files = []
        self._current_index = -1

    def set_files(self, files):
        self._files = list(files)
        self._current_index = 0 if files else -1
        self._update_nav_state()

    def get_current_index(self):
        return self._current_index

    def set_current_index(self, idx):
        if 0 <= idx < len(self._files):
            self._current_index = idx
            self._update_nav_state()
            self.nav_changed.emit()

    def current_file(self):
        if 0 <= self._current_index < len(self._files):
            return self._files[self._current_index]
        return None

    def file_count(self):
        return len(self._files)

    def _update_nav_state(self):
        total = len(self._files)
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(self._current_index < total - 1)
        if total > 0:
            self.page_label.setText(f"{self._current_index + 1} / {total}")
        else:
            self.page_label.setText("0 / 0")

    def show_pil_image(self, pil_image, margin_mm=0, dpi=300):
        self.image_view.set_image(pil_image, margin_mm, dpi)
        f = self.current_file()
        self.path_label.setText(f if f else "")

    def clear(self):
        self.image_view.clear_image()
        self.path_label.setText("")
        self.page_label.setText("0 / 0")
        self._files = []
        self._current_index = -1


class BlackCircleRemoverPage(QWidget):
    """黑色圆圈移除主页面"""

    DARK_QSS = """
    QWidget { background-color: #0B0F19; color: #E0E0E0; font-family: 'Microsoft YaHei', Arial; }
    QGroupBox {
        border: 1px solid #30363D; border-radius: 5px; margin-top: 15px; padding: 15px;
        font-weight: bold; color: #00F0FF;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
    QLineEdit, QSpinBox, QComboBox {
        background-color: #0D1117; border: 1px solid #30363D; border-radius: 3px;
        padding: 5px; color: #E0E0E0;
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #00F0FF; }
    QSpinBox::up-button, QSpinBox::down-button { background-color: #21262D; border: none; width: 18px; }
    QSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; border-left: 1px solid #30363D; }
    QSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; border-left: 1px solid #30363D; border-top: 1px solid #30363D; }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #30363D; }
    QSpinBox::up-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #E0E0E0; width: 0px; height: 0px; }
    QSpinBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #E0E0E0; width: 0px; height: 0px; }
    QPushButton#ActionBtn { background-color: #238636; color: white; border: none; padding: 8px 16px; border-radius: 3px; font-weight: bold; }
    QPushButton#ActionBtn:hover { background-color: #2EA043; }
    QPushButton#ActionBtn:disabled { background-color: #1a3a25; color: #5a7a65; }
    QPushButton#BrowseBtn { background-color: #30363D; color: white; border: none; padding: 5px 10px; border-radius: 3px; }
    QPushButton#BrowseBtn:hover { background-color: #3C434D; }
    QTextEdit { background-color: #0D1117; border: 1px solid #30363D; border-radius: 3px; color: #FFFFFF; font-size: 13px; }
    QProgressBar { background-color: #0D1117; border: 1px solid #30363D; border-radius: 3px; text-align: center; color: #FFFFFF; font-weight: bold; }
    QProgressBar::chunk { background-color: #2EA043; border-radius: 2px; }
    QCheckBox { color: #E0E0E0; }
    QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #30363D; border-radius: 3px; background-color: #0D1117; }
    QCheckBox::indicator:checked { background-color: #00F0FF; border: 1px solid #00F0FF; }
    """

    def __init__(self):
        super().__init__()
        self.setStyleSheet(self.DARK_QSS)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 12)
        self.layout.setSpacing(8)

        # === 左侧面板：设置区 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 标题
        lbl_title = QLabel("图像质检工具")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(
            "color: #00F0FF; font-size: 26px; font-weight: bold;"
            "font-family: 'SimHei','黑体','Microsoft YaHei'; padding: 2px 0 6px 0;")
        left_layout.addWidget(lbl_title)

        # 设置组
        group = QGroupBox("处理设置")
        form = QFormLayout()

        # 输入目录选择
        self.input_dir = QLineEdit()
        btn_browse_input = QPushButton("选择文件夹")
        btn_browse_input.setObjectName("BrowseBtn")
        btn_browse_input.clicked.connect(self.browse_input_dir)
        h1 = QHBoxLayout()
        h1.addWidget(self.input_dir)
        h1.addWidget(btn_browse_input)
        form.addRow("输入目录:", h1)

        # 输出目录选择
        self.output_dir = QLineEdit()
        btn_browse_output = QPushButton("选择文件夹")
        btn_browse_output.setObjectName("BrowseBtn")
        btn_browse_output.clicked.connect(self.browse_output_dir)
        h2 = QHBoxLayout()
        h2.addWidget(self.output_dir)
        h2.addWidget(btn_browse_output)
        form.addRow("输出目录:", h2)

        # 自动设置输出目录选项
        self.auto_output_dir = QCheckBox("自动在源目录下创建'图像处理结果'目录")
        self.auto_output_dir.setChecked(True)
        self.auto_output_dir.stateChanged.connect(self.on_auto_output_changed)
        form.addRow("", self.auto_output_dir)

        # 最大直径设置（毫米）
        self.max_diameter_spin = QSpinBox()
        self.max_diameter_spin.setRange(5, 50)
        self.max_diameter_spin.setValue(25)  # 2.5cm = 25mm
        self.max_diameter_spin.setSuffix(" mm")
        form.addRow("圆圈最大直径:", self.max_diameter_spin)

        # 纠偏(去倾斜)选项
        self.deskew_check = QCheckBox("纠偏（将内容旋转到水平，纯旋转不变形）")
        self.deskew_check.setChecked(True)
        form.addRow("纠偏:", self.deskew_check)

        # 去黑边选项(默认选中)
        self.border_check = QCheckBox("去黑边（去除扫描产生的边缘黑条/阴影，保留正文）")
        self.border_check.setChecked(True)
        form.addRow("去黑边:", self.border_check)

        # DPI 设置
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.setToolTip("用于将毫米转换为像素的DPI假设值")
        form.addRow("图像DPI:", self.dpi_spin)

        # 边缘覆盖边距设置
        self.edge_margin_spin = QDoubleSpinBox()
        self.edge_margin_spin.setRange(0.0, 50.0)
        self.edge_margin_spin.setValue(2.0)
        self.edge_margin_spin.setSingleStep(0.5)
        self.edge_margin_spin.setSuffix(" mm")
        self.edge_margin_spin.setToolTip("距离文件边缘的边距宽度，该区域内的内容将被底色覆盖")
        form.addRow("边缘覆盖边距:", self.edge_margin_spin)

        # 边缘覆盖选项
        self.edge_cover_check = QCheckBox("边缘底色覆盖（将四周边缘区域用底色覆盖）")
        self.edge_cover_check.setChecked(False)
        self.edge_cover_check.setToolTip("启用后，处理时会将文件四周边缘设定边距宽度的区域用底色覆盖")
        # 勾选/改值时实时刷新预览红框
        self.edge_cover_check.stateChanged.connect(self._refresh_edge_preview)
        self.edge_margin_spin.valueChanged.connect(self._refresh_edge_preview)
        form.addRow("边缘覆盖:", self.edge_cover_check)

        # 线程数设置
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 8)
        self.thread_spin.setValue(4)
        self.thread_spin.setSuffix(" 线程")
        form.addRow("并行线程数:", self.thread_spin)

        group.setLayout(form)
        left_layout.addWidget(group)

        # 说明文本
        info_label = QLabel(
            "功能说明：\n"
            "• 递归扫描指定目录及子目录下的所有JPG文件\n"
            "• 智能检测文字和竖线边界，自动确定检测区域\n"
            "• 仅在文字/竖线外侧区域检测黑色圆圈\n"
            "• 圆圈最大直径可配置（默认25mm/2.5cm）\n"
            "• 用与底色一致的颜色填充检测到的圆洞\n"
            "• 边缘覆盖：将文件四周边缘用底色覆盖\n"
            "• 右侧预览区可预览原图和处理后的效果\n"
            "• 支持鼠标滚轮缩放、拖拽查看"
        )
        info_label.setStyleSheet("color: #8B949E; font-size: 14px;")
        left_layout.addWidget(info_label)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.process_btn = QPushButton("开始处理")
        self.process_btn.setObjectName("ActionBtn")
        self.process_btn.clicked.connect(self.start_processing)
        btn_layout.addWidget(self.process_btn)

        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633; color: white;")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        left_layout.addLayout(btn_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("待开始")
        left_layout.addWidget(self.progress_bar)

        # 日志框
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(180)
        left_layout.addWidget(self.log_box, 1)

        # === 右侧：预览区（原图和处理后并排显示） ===
        self.preview_splitter = QSplitter(Qt.Vertical)

        self.before_panel = PreviewPanel("原图预览")
        self.after_panel = PreviewPanel("处理后预览")
        self.preview_splitter.addWidget(self.before_panel)
        self.preview_splitter.addWidget(self.after_panel)
        self.preview_splitter.setStretchFactor(0, 1)
        self.preview_splitter.setStretchFactor(1, 1)

        # === 中间：文件树浏览器 ===
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(2, 2, 2, 2)
        tree_label = QLabel("文件浏览器")
        tree_label.setStyleSheet("color: #00F0FF; font-weight: bold; padding: 2px;")
        tree_layout.addWidget(tree_label)
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setStyleSheet("""
            QTreeWidget { background-color: #0D1117; border: 1px solid #30363D; border-radius: 3px; font-size: 13px; color: #E0E0E0; }
            QTreeWidget::item { padding: 3px; }
            QTreeWidget::item:selected { background-color: #1F6FEB; color: white; }
        """)
        self.file_tree.itemClicked.connect(self.on_tree_item_clicked)
        tree_layout.addWidget(self.file_tree)

        # 分割器（三栏：设置 | 文件树 | 预览）
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(tree_container)
        self.main_splitter.addWidget(self.preview_splitter)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 3)
        self.main_splitter.setSizes([300, 200, 500])
        self.layout.addWidget(self.main_splitter, 1)

        # 存储处理结果
        self.process_results = []
        self.worker = None
        self.source_files = []  # 源目录下的所有JPG文件列表

        # 连接预览导航按钮
        self.before_panel.prev_btn.clicked.connect(lambda: self._tree_navigate(-1))
        self.before_panel.next_btn.clicked.connect(lambda: self._tree_navigate(1))
        self.after_panel.prev_btn.clicked.connect(lambda: self._navigate_preview(self.after_panel, -1))
        self.after_panel.next_btn.clicked.connect(lambda: self._navigate_preview(self.after_panel, 1))

    def browse_input_dir(self):
        """选择输入目录"""
        d = QFileDialog.getExistingDirectory(self, "选择输入目录")
        if d:
            self.input_dir.setText(d)
            if self.auto_output_dir.isChecked():
                output_path = os.path.join(d, "图像处理结果")
                self.output_dir.setText(output_path)
            self._scan_source_files(d)
            self.build_file_tree(d)

    def browse_output_dir(self):
        """选择输出目录"""
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.output_dir.setText(d)
            # 取消自动输出目录选项
            self.auto_output_dir.setChecked(False)

    def on_auto_output_changed(self, state):
        """自动输出目录选项改变"""
        if state == Qt.Checked and self.input_dir.text():
            output_path = os.path.join(self.input_dir.text(), "图像处理结果")
            self.output_dir.setText(output_path)

    def build_file_tree(self, root_dir):
        """构建文件浏览器树：一级=子目录(默认折叠)+根目录下的JPG文件。"""
        self.file_tree.clear()
        self._tree_files = []
        self._tree_current_idx = -1
        if not root_dir or not os.path.isdir(root_dir):
            return
        self._tree_root_dir = root_dir
        try:
            entries = sorted(os.listdir(root_dir))
            for sub in entries:
                sub_path = os.path.join(root_dir, sub)
                if not os.path.isdir(sub_path):
                    continue
                count = 0
                sub_files = []
                for r, d, files in os.walk(sub_path):
                    for f in sorted(files):
                        if f.lower().endswith(('.jpg', '.jpeg')):
                            sub_files.append(os.path.join(r, f))
                            count += 1
                if count == 0:
                    continue
                dir_item = QTreeWidgetItem(self.file_tree)
                dir_item.setText(0, f"📁 {sub} ({count})")
                dir_item.setForeground(0, QColor("#00F0FF"))
                dir_item.setData(0, Qt.UserRole, ("dir", sub_path))
                for fp in sub_files:
                    file_item = QTreeWidgetItem(dir_item)
                    file_item.setText(0, os.path.basename(fp))
                    file_item.setData(0, Qt.UserRole, ("file", fp))
                    self._tree_files.append(fp)
            root_jpgs = []
            for f in entries:
                fp = os.path.join(root_dir, f)
                if os.path.isfile(fp) and f.lower().endswith(('.jpg', '.jpeg')):
                    root_jpgs.append(fp)
            if root_jpgs:
                root_item = QTreeWidgetItem(self.file_tree)
                root_item.setText(0, f"📁 根目录 ({len(root_jpgs)})")
                root_item.setForeground(0, QColor("#00F0FF"))
                root_item.setData(0, Qt.UserRole, ("dir", root_dir))
                for fp in root_jpgs:
                    file_item = QTreeWidgetItem(root_item)
                    file_item.setText(0, os.path.basename(fp))
                    file_item.setData(0, Qt.UserRole, ("file", fp))
                    self._tree_files.append(fp)
        except Exception as e:
            self.log(f"构建文件树出错: {e}")

    def on_tree_item_clicked(self, item, column):
        """点击文件树节点：文件则预览，目录则展开/折叠"""
        data = item.data(0, Qt.UserRole)
        if data and data[0] == "file":
            filepath = data[1]
            # 更新当前索引
            if filepath in self._tree_files:
                self._tree_current_idx = self._tree_files.index(filepath)
                self._update_nav_buttons()
            self.preview_file_by_path(filepath)

    def preview_file_by_path(self, filepath):
        """按文件路径预览：原图+处理后对比。
        严格按"相对目录路径+文件名"匹配，确保不会错位。"""
        if not filepath or not os.path.isfile(filepath):
            return
        # 原图（如果勾选了边缘覆盖，传入margin参数以显示红框）
        edge_mm = self.edge_margin_spin.value() if self.edge_cover_check.isChecked() else 0
        dpi_val = 300
        try:
            img = Image.open(filepath)
            img.load()
            self.before_panel.show_pil_image(img, margin_mm=edge_mm, dpi=dpi_val)
            self.before_panel._filepath = filepath
        except Exception:
            pass
        # 处理后结果：严格按相对路径匹配
        self.after_panel.clear()
        output_dir = self.output_dir.text().strip()
        root_dir = getattr(self, '_tree_root_dir', '') or self.input_dir.text().strip()
        if output_dir and os.path.isdir(output_dir) and root_dir:
            # 计算输入文件相对于输入根目录的相对路径
            rel = os.path.relpath(filepath, root_dir)
            after_path = os.path.join(output_dir, rel)
            if os.path.isfile(after_path):
                try:
                    img2 = Image.open(after_path)
                    img2.load()
                    self.after_panel.show_pil_image(img2)
                    self.after_panel._filepath = after_path
                except Exception:
                    pass

    def _tree_navigate(self, direction):
        """通过文件树列表导航：-1上一页，+1下一页，原图和处理后联动"""
        files = getattr(self, '_tree_files', [])
        idx = getattr(self, '_tree_current_idx', -1)
        new_idx = idx + direction
        if 0 <= new_idx < len(files):
            self._tree_current_idx = new_idx
            self._update_nav_buttons()
            self.preview_file_by_path(files[new_idx])

    def _update_nav_buttons(self):
        """更新原图面板的上一页/下一页按钮状态和页码"""
        files = getattr(self, '_tree_files', [])
        idx = getattr(self, '_tree_current_idx', -1)
        total = len(files)
        self.before_panel.prev_btn.setEnabled(idx > 0)
        self.before_panel.next_btn.setEnabled(idx < total - 1)
        if 0 <= idx < total:
            self.before_panel.page_label.setText(f"{idx + 1} / {total}")

    def _refresh_edge_preview(self):
        """边缘覆盖勾选/改值时，实时刷新原图预览的红框"""
        files = getattr(self, '_tree_files', [])
        idx = getattr(self, '_tree_current_idx', -1)
        if 0 <= idx < len(files):
            self.preview_file_by_path(files[idx])

    def start_processing(self):
        """开始处理"""
        input_dir = self.input_dir.text().strip()
        if not input_dir:
            QMessageBox.warning(self, "提示", "请先选择输入目录")
            return

        if not os.path.exists(input_dir):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return

        # 确定输出目录
        output_dir = self.output_dir.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "提示", "请指定输出目录")
            return

        # 如果启用了自动创建输出目录
        if self.auto_output_dir.isChecked():
            output_dir = os.path.join(input_dir, "图像处理结果")
            os.makedirs(output_dir, exist_ok=True)
            self.output_dir.setText(output_dir)
            self.log(f"✓ 已创建输出目录: {output_dir}")

        # 清空之前的结果
        self.process_results = []
        self.log_box.clear()

        max_diameter = self.max_diameter_spin.value()
        deskew = self.deskew_check.isChecked()
        remove_border = self.border_check.isChecked()
        dpi = self.dpi_spin.value()
        edge_cover = self.edge_cover_check.isChecked()
        edge_margin = self.edge_margin_spin.value()

        self.log("=" * 60)
        self.log(f"开始处理目录: {input_dir}")
        self.log(f"输出目录: {output_dir}")
        self.log(f"圆圈最大直径: {max_diameter}mm")
        self.log(f"纠偏: {'开启（自动检测，纯旋转不变形）' if deskew else '关闭'}")
        self.log(f"去黑边: {'开启' if remove_border else '关闭'}")
        self.log(f"边缘覆盖: {'开启' if edge_cover else '关闭'}")
        if edge_cover:
            self.log(f"边缘覆盖边距: {edge_margin}mm")
        self.log(f"DPI: {dpi}")
        thread_count = self.thread_spin.value()
        self.log(f"并行线程: {thread_count}")
        self.log("=" * 60)

        # 创建工作线程
        self.worker = CircleDetectionWorker(input_dir, output_dir, max_diameter,
                                            deskew=deskew, remove_border=remove_border,
                                            thread_count=thread_count,
                                            edge_cover=edge_cover, edge_margin_mm=edge_margin,
                                            dpi=dpi)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.display_results)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.file_done_signal.connect(self._on_file_done)

        # 清空处理后预览
        self.after_panel.clear()

        self.worker.start()

        # 更新按钮状态
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_processing(self):
        """停止处理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("正在停止处理...")
            self.stop_btn.setEnabled(False)

    def update_progress(self, current, total):
        """更新进度"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.progress_bar.setValue(int(percentage))
        self.progress_bar.setFormat(f"{current} / {total} ({percentage:.1f}%)")

    def display_results(self, results):
        """显示处理结果"""
        self.process_results = results

        if not results:
            self.log("\n✓ 未处理任何文件")
            return

        success_count = sum(1 for r in results if r['success'])
        circles_total = sum(r['circles_found'] for r in results)

        self.log(f"\n处理统计：")
        self.log(f"  总文件数: {len(results)}")
        self.log(f"  成功处理: {success_count}")
        self.log(f"  失败: {len(results) - success_count}")
        self.log(f"  检测到的圆圈总数: {circles_total}")

        # 设置处理后预览文件列表
        processed_files = [r['output_path'] for r in results if r['success'] and r.get('output_path')]
        if processed_files:
            self.after_panel.set_files(processed_files)
            self.after_panel.set_current_index(0)
            self._show_after_preview(0)

    def on_finished(self, success, message):
        """处理完成回调"""
        self.log(message)
        self.progress_bar.setFormat("已完成" if success else "已停止")

        # 恢复按钮状态
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.warning(self, "结束", message)

    def log(self, msg):
        """添加日志"""
        self.log_box.append(f">> {msg}")

    # === 预览相关方法 ===

    def _on_file_done(self, output_path):
        """单个文件处理完成，实时更新处理后预览"""
        if not os.path.exists(output_path):
            return
        # 添加到处理后预览文件列表
        current_files = list(self.after_panel._files)
        if output_path not in current_files:
            current_files.append(output_path)
            self.after_panel._files = current_files
            # 如果是第一个文件，显示它
            if len(current_files) == 1:
                self.after_panel._current_index = 0
                self.after_panel._update_nav_state()
                self._show_after_preview(0)

    def _scan_source_files(self, source_dir):
        """扫描源目录下的所有JPG文件，更新预览"""
        jpg_files = []
        for root, dirs, files in os.walk(source_dir):
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    jpg_files.append(os.path.join(root, filename))

        def _natural_key(path):
            return [int(t) if t.isdigit() else t.lower()
                    for t in re.split(r'(\d+)', path)]
        jpg_files.sort(key=_natural_key)

        self.source_files = jpg_files
        if jpg_files:
            self.before_panel.set_files(jpg_files)
            self.before_panel.set_current_index(0)
            self._show_before_preview(0)
        else:
            self.before_panel.clear()

    def _show_before_preview(self, index):
        """显示原图预览"""
        if 0 <= index < len(self.source_files):
            try:
                img = Image.open(self.source_files[index])
                img.load()
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                dpi = self.dpi_spin.value()
                margin_mm = self.edge_margin_spin.value() if self.edge_cover_check.isChecked() else 0
                self.before_panel.show_pil_image(img, margin_mm, dpi)
            except Exception as e:
                self.before_panel.image_view.clear_image()
                self.before_panel.path_label.setText(f"加载失败: {e}")

    def _show_after_preview(self, index):
        """显示处理后预览"""
        files = self.after_panel._files
        if 0 <= index < len(files):
            try:
                img = Image.open(files[index])
                img.load()
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                self.after_panel.show_pil_image(img, 0, 0)
            except Exception as e:
                self.after_panel.image_view.clear_image()
                self.after_panel.path_label.setText(f"加载失败: {e}")

    def _navigate_preview(self, panel, direction):
        """导航预览：direction=-1上一页，+1下一页"""
        current = panel.get_current_index()
        new_idx = current + direction
        if 0 <= new_idx < panel.file_count():
            panel.set_current_index(new_idx)
            if panel is self.before_panel:
                self._show_before_preview(new_idx)
                if new_idx < self.after_panel.file_count():
                    self.after_panel.set_current_index(new_idx)
                    self._show_after_preview(new_idx)
            elif panel is self.after_panel:
                self._show_after_preview(new_idx)
                if new_idx < self.before_panel.file_count():
                    self.before_panel.set_current_index(new_idx)
                    self._show_before_preview(new_idx)


# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置Windows 7兼容性
    try:
        # 启用高DPI支持
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except:
        pass
    
    window = BlackCircleRemoverPage()
    window.setWindowTitle("同美图像质检工具")
    window.setGeometry(100, 100, 1400, 900)
    window.show()
    window.raise_()  # 确保窗口显示在最前面
    window.activateWindow()  # 激活窗口
    
    sys.exit(app.exec_())
