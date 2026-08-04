"""
黑色圆圈检测与裁剪工具 - 检测并裁剪JPG文件左侧或右侧的黑色不规则圆圈
运行环境：Windows 7
依赖：PyQt5, Pillow (PIL), OpenCV (可选)
"""

import sys
import os
import math
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QTextEdit, QSpinBox, QFormLayout,
                             QGroupBox, QMessageBox, QCheckBox, QSplitter,
                             QScrollArea, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal as Signal
from PyQt5.QtGui import QFont, QPixmap, QImage


class CircleDetectionWorker(QThread):
    """黑色圆圈检测后台工作线程（单线程处理）"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    result_signal = Signal(list)  # 发送处理结果列表
    finished_signal = Signal(bool, str)

    def __init__(self, input_dir, output_dir, max_diameter_mm=25, margin_mm=40, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.max_diameter_mm = max_diameter_mm  # 最大直径（毫米），默认25mm(2.5cm)
        self.margin_mm = margin_mm  # 两侧边距（毫米），默认40mm(4cm)
        self.is_stopped = False
        # 假设300 DPI进行像素转换
        self.dpi_assumption = 300
        self.max_diameter_pixels = int(self.max_diameter_mm * self.dpi_assumption / 25.4)
        self.margin_pixels = int(self.margin_mm * self.dpi_assumption / 25.4)  # 边距像素值

    def run(self):
        try:
            # 收集所有JPG文件
            jpg_files = []
            for root, dirs, files in os.walk(self.input_dir):
                if self.is_stopped:
                    break
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg')):
                        jpg_files.append(os.path.join(root, filename))

            total = len(jpg_files)
            if total == 0:
                self.finished_signal.emit(False, "未找到任何JPG/JPEG文件")
                return

            self.log_signal.emit(f"找到 {total} 个JPG文件，开始检测黑色圆圈...")

            results = []
            processed = 0
            # 崩溃日志：记录“正在处理”的文件。进程被系统杀死(如内存耗尽)时无 Python
            # 异常信息，此文件可定位元凶；正常结束后自动删除。
            crash_log = os.path.join(self.output_dir, '_processing.log')
            try:
                os.makedirs(self.output_dir, exist_ok=True)
                with open(crash_log, 'w', encoding='utf-8') as cf:
                    cf.write(f"开始处理 {total} 个文件\n")
            except Exception:
                crash_log = None

            for jpg_path in jpg_files:
                if self.is_stopped:
                    break

                # 先记录正在处理的文件（GUI 日志 + 同步写文件），便于崩溃定位
                self.log_signal.emit(f"处理中: {os.path.basename(jpg_path)}")
                if crash_log:
                    try:
                        with open(crash_log, 'a', encoding='utf-8') as cf:
                            cf.write(f">>> {jpg_path}\n")
                            cf.flush()
                    except Exception:
                        pass

                try:
                    result = self.process_image(jpg_path)
                    results.append(result)
                    
                    status = "✓ 已裁剪" if result['success'] else "✗ 失败"
                    circle_info = f"发现{result['circles_found']}个圆圈" if result['success'] else ""
                    self.log_signal.emit(
                        f"{status} {os.path.basename(jpg_path)} - {circle_info} {result.get('error_msg', '')}")

                except Exception as e:
                    error_msg = f"处理文件失败 {os.path.basename(jpg_path)}: {str(e)}"
                    self.log_signal.emit(error_msg)
                    results.append({
                        'path': jpg_path,
                        'filename': os.path.basename(jpg_path),
                        'success': False,
                        'error_msg': str(e),
                        'circles_found': 0
                    })

                processed += 1
                self.progress_signal.emit(processed, total)

            if not self.is_stopped:
                self.result_signal.emit(results)
                success_count = sum(1 for r in results if r['success'])
                msg = f"处理完成！共检查 {processed} 个文件，成功裁剪 {success_count} 个文件"
                # 正常结束，删除崩溃日志
                if crash_log and os.path.exists(crash_log):
                    try:
                        os.remove(crash_log)
                    except Exception:
                        pass
                self.finished_signal.emit(True, msg)
            else:
                self.finished_signal.emit(False, "处理已停止")

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
            orig_w, orig_h = img.size

            # --- 原图分辨率灰度/掩码：用于边距带打孔洞检测 ---
            # 保持原分辨率，避免降采样把小圆洞缩到无法与噪点区分
            arr = np.array(img)
            gray_full = (np.mean(arr, axis=2).astype(np.uint8) if arr.ndim == 3 else arr.copy())
            mask_full = gray_full < 50

            # --- 降采样图：仅用于快速判断“是否存在文字内容” ---
            DET_MAX_EDGE = 1500
            if max(orig_w, orig_h) > DET_MAX_EDGE:
                sc = DET_MAX_EDGE / max(orig_w, orig_h)
                det_w, det_h = int(orig_w * sc), int(orig_h * sc)
                det_img = img.resize((det_w, det_h), Image.BILINEAR)
                darr = np.array(det_img)
                det_img.close()
                dgray = (np.mean(darr, axis=2).astype(np.uint8) if darr.ndim == 3 else darr.copy())
                dmask = dgray < 50
                del darr, dgray
            else:
                sc = 1.0
                det_w, det_h = orig_w, orig_h
                dmask = mask_full

            # 内容边界（降采样，阈值临时缩放）→ 判断是否有文字内容
            orig_max_diam = self.max_diameter_pixels
            self.max_diameter_pixels = max(5, int(orig_max_diam * sc))
            try:
                lb, rb = self.detect_detection_boundaries(dmask, det_w, det_h)
            finally:
                self.max_diameter_pixels = orig_max_diam
            has_content = not (lb <= 0 and rb >= det_w)

            # --- 检测圆洞（原图分辨率，坐标无需缩放）---
            if has_content:
                # 有文字内容：打孔洞紧贴纸边 → 边距带检测 + 过滤
                circles_info = self.detect_edge_holes(mask_full, orig_w, orig_h)
            else:
                # 无文字（纯圆图等）：全图检测（降采样省内存），坐标映射回原图
                raw = self.detect_circle_region(dmask, 0, det_h)
                if sc != 1.0:
                    inv = 1.0 / sc
                    circles_info = [(int(round(cx * inv)), int(round(cy * inv)), int(round(r * inv)))
                                    for cx, cy, r in raw]
                else:
                    circles_info = raw

            del arr, gray_full, mask_full
            if sc != 1.0:
                del dmask
            circles_info = self._dedup_circles(circles_info)

            # 输出路径（保持原目录结构），确保每个文件都写入目标目录
            rel_path = os.path.relpath(image_path, self.input_dir)
            output_path = os.path.join(self.output_dir, rel_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if circles_info:
                # 检测到圆洞：在原图上白色填充后另存（输出保持原分辨率）
                output_img = self.crop_circles(img, circles_info)
                img.close()
                output_img.save(output_path, quality=95)
                output_img.close()
            else:
                # 未检测到圆洞：原样复制到目标目录，保证文件完整不丢失
                img.close()
                shutil.copy2(image_path, output_path)

            return {
                'path': image_path,
                'filename': os.path.basename(image_path),
                'success': True,
                'circles_found': len(circles_info),
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
                'circles_found': 0
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
        """
        在四条边的“边距带”(距纸边 margin_pixels 内)以原图分辨率检测打孔洞。
        打孔洞可能在任意一条纸边上（左/右/上/下），故四条边都搜。
        返回带边标记的候选 (cx, cy, r, edge)。
        """
        mp = self.margin_pixels
        candidates = []
        # 左/右边距带（竖向带，洞沿竖向成列）
        if 0 < mp < img_w // 2:
            for cx, cy, r in self.detect_circle_region(mask[:, :mp], 0, img_h):
                candidates.append((cx, cy, r, 'L'))
            for cx, cy, r in self.detect_circle_region(mask[:, img_w - mp:], img_w - mp, img_h):
                candidates.append((cx, cy, r, 'R'))
        # 上/下边距带（横向带，洞沿横向成排）
        if 0 < mp < img_h // 2:
            for cx, cy, r in self.detect_circle_region(mask[:mp, :], 0, mp):
                candidates.append((cx, cy, r, 'T'))
            for cx, cy, r in self.detect_circle_region(mask[img_h - mp:, :], 0, mp):
                candidates.append((cx, cy + (img_h - mp), r, 'B'))
        return self._filter_punch_holes(candidates, img_w, img_h)

    def _filter_punch_holes(self, candidates, img_w, img_h):
        """
        从边距带候选中保留“打孔洞”，滤除文字/边框等噪点：
        - 按所在边(L/R/T/B)分别聚类；
        - 竖向边(L/R)：按中心 x 聚列、要求沿 y 有足够跨度（多个洞纵向排列）；
          横向边(T/B)：按中心 y 聚排、要求沿 x 有足够跨度；
        - 同列/排内相对尺寸过滤，去掉混入的细小噪点。
        “成列且沿边有跨度”是打孔洞的强特征；同行/同列的零散文字不满足，从而被滤除。
        """
        if len(candidates) < 2:
            return []
        tol = max(self.max_diameter_pixels / 4, 1)       # 同列/排 聚类容差
        spread_min = self.max_diameter_pixels            # 沿边跨度阈值
        floor = self.max_diameter_pixels * 0.03          # 绝对最小半径

        from collections import defaultdict
        by_edge = defaultdict(list)
        for cx, cy, r, edge in candidates:
            by_edge[edge].append((cx, cy, r))

        kept = []
        for edge, comps in by_edge.items():
            vertical = edge in ('L', 'R')
            key_idx = 0 if vertical else 1      # 聚类轴：竖向边按 x，横向边按 y
            spread_idx = 1 if vertical else 0   # 跨度轴：竖向边沿 y，横向边沿 x
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
            for col in cols:
                if len(col) < 2:
                    continue
                spread = max(c[spread_idx] for c in col) - min(c[spread_idx] for c in col)
                if spread < spread_min:
                    continue  # 沿边跨度不足，多为同行/同列零散文字
                thresh = max(floor, max(c[2] for c in col) * 0.5)
                for cx, cy, r in col:
                    if r >= thresh:
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
        使用简化的轮廓检测方法
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

            # 额外检查：确保是近似圆形的（不是细长的线）
            # 宽高比 = 长边 / 短边（短边至少为1，避免除零）。圆≈1.0，细线条会很大。
            aspect_ratio = max(max_row - min_row, max_col - min_col) / max(min(max_row - min_row, max_col - min_col), 1)
            if aspect_ratio > 3:  # 如果宽高比超过3，可能是线条而非圆圈
                continue

            # 实心度(solidity)：真圆洞(实心圆盘)密度高(≈0.78)；手写笔画/线条/不规则噪点
            # 填不满其外接框、密度低。实测：真圆洞 0.45~0.92，手写文字 0.2~0.41，阈值取 0.45。
            bw, bh = max_col - min_col, max_row - min_row
            solidity = pixel_count / (bh * bw) if bh * bw > 0 else 0
            if solidity < 0.45:
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


class BlackCircleRemoverPage(QWidget):
    """黑色圆圈移除主页面"""

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        # 标题
        lbl_title = QLabel("黑色圆圈检测与裁剪工具")
        lbl_title.setStyleSheet("color: #00F0FF; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(lbl_title)

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

        group.setLayout(form)
        self.layout.addWidget(group)

        # 说明文本
        info_label = QLabel(
            "功能说明：\n"
            "• 递归扫描指定目录及子目录下的所有JPG文件\n"
            "• 智能检测文字和竖线边界，自动确定检测区域\n"
            "• 仅在文字/竖线外侧区域检测黑色圆圈\n"
            "• 如无文字和竖线，则全图检测\n"
            "• 圆圈最大直径可配置（默认25mm/2.5cm）\n"
            "• 使用白色填充方式裁剪掉检测到的圆圈\n"
            "• 支持预览处理前后的对比效果\n"
            "• 自动生成详细的处理日志"
        )
        info_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        self.layout.addWidget(info_label)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.preview_btn = QPushButton("预览效果")
        self.preview_btn.setObjectName("ActionBtn")
        self.preview_btn.setStyleSheet("background-color: #2196F3;")
        self.preview_btn.clicked.connect(self.show_preview)
        self.preview_btn.setEnabled(False)
        btn_layout.addWidget(self.preview_btn)

        self.process_btn = QPushButton("开始处理")
        self.process_btn.setObjectName("ActionBtn")
        self.process_btn.clicked.connect(self.start_processing)
        btn_layout.addWidget(self.process_btn)

        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        self.layout.addLayout(btn_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("待开始")
        self.layout.addWidget(self.progress_bar)

        # 预览区域（分割视图）
        preview_group = QGroupBox("预览对比（左：原图 / 右：处理后）")
        preview_layout = QHBoxLayout()

        # 原图预览
        self.before_scroll = QScrollArea()
        self.before_scroll.setWidgetResizable(True)
        self.before_label = QLabel("暂无预览")
        self.before_label.setAlignment(Qt.AlignCenter)
        self.before_label.setStyleSheet("color: #8B949E;")
        self.before_scroll.setWidget(self.before_label)

        # 处理后预览
        self.after_scroll = QScrollArea()
        self.after_scroll.setWidgetResizable(True)
        self.after_label = QLabel("暂无预览")
        self.after_label.setAlignment(Qt.AlignCenter)
        self.after_label.setStyleSheet("color: #8B949E;")
        self.after_scroll.setWidget(self.after_label)

        preview_layout.addWidget(self.before_scroll)
        preview_layout.addWidget(self.after_scroll)
        preview_group.setLayout(preview_layout)
        self.layout.addWidget(preview_group)

        # 日志框
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(150)
        self.layout.addWidget(self.log_box)

        # 存储处理结果
        self.process_results = []
        self.worker = None

    def browse_input_dir(self):
        """选择输入目录"""
        d = QFileDialog.getExistingDirectory(self, "选择输入目录")
        if d:
            self.input_dir.setText(d)
            # 如果启用了自动输出目录，更新输出目录
            if self.auto_output_dir.isChecked():
                output_path = os.path.join(d, "图像处理结果")
                self.output_dir.setText(output_path)

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

    def show_preview(self):
        """显示预览效果"""
        if not self.process_results:
            QMessageBox.warning(self, "提示", "请先处理文件以生成预览")
            return

        # 找到第一个成功处理的文件进行预览
        preview_result = None
        for result in self.process_results:
            if result['success'] and result['circles_found'] > 0:
                preview_result = result
                break

        if not preview_result:
            QMessageBox.information(self, "提示", "未找到包含黑色圆圈的文件进行预览")
            return

        # 加载并显示原图
        try:
            before_pixmap = self.load_image_to_pixmap(preview_result['preview_before'])
            self.before_label.setPixmap(before_pixmap)
            self.before_label.setText("")
            self.log(f"✓ 已加载原图: {os.path.basename(preview_result['preview_before'])}")
        except Exception as e:
            error_msg = f"加载原图失败: {str(e)}"
            self.before_label.setText(error_msg)
            self.log(f"✗ {error_msg}")
            import traceback
            self.log(traceback.format_exc())
            return

        # 加载并显示处理后的图
        try:
            after_pixmap = self.load_image_to_pixmap(preview_result['preview_after'])
            self.after_label.setPixmap(after_pixmap)
            self.after_label.setText("")
            self.log(f"✓ 已加载处理后图片: {os.path.basename(preview_result['preview_after'])}")
        except Exception as e:
            error_msg = f"加载处理后图片失败: {str(e)}"
            self.after_label.setText(error_msg)
            self.log(f"✗ {error_msg}")
            import traceback
            self.log(traceback.format_exc())
            return

        self.log(f"✓ 预览显示成功: {preview_result['filename']} (检测到{preview_result['circles_found']}个圆圈)")

    def load_image_to_pixmap(self, image_path):
        """加载图像并转换为QPixmap，保持适当大小"""
        try:
            # 直接使用Qt的QPixmap加载，更可靠
            pixmap = QPixmap(image_path)
            
            if pixmap.isNull():
                raise ValueError(f"无法加载图片: {image_path}")
            
            # 限制显示尺寸
            max_display_width = 600
            max_display_height = 400
            
            # 缩放图片以适应显示区域
            scaled_pixmap = pixmap.scaled(
                max_display_width, max_display_height,
                Qt.KeepAspectRatio,  # 保持宽高比
                Qt.SmoothTransformation  # 平滑缩放
            )
            
            if scaled_pixmap.isNull():
                raise ValueError(f"缩放图片失败: {image_path}")
            
            return scaled_pixmap
            
        except Exception as e:
            # 如果直接加载失败，尝试使用PIL方法
            img = Image.open(image_path)
            
            # 限制显示尺寸
            max_display_width = 600
            max_display_height = 400
            
            # 计算缩放比例
            ratio_w = max_display_width / img.width
            ratio_h = max_display_height / img.height
            ratio = min(ratio_w, ratio_h, 1.0)  # 不放大
            
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 转换为RGB模式确保兼容性
            if img_resized.mode != 'RGB':
                img_resized = img_resized.convert('RGB')
            
            # 获取图像数据
            data = img_resized.tobytes("raw", "RGB")
            
            # 创建QImage
            qimage = QImage(data, new_width, new_height, QImage.Format_RGB888)
            
            if qimage.isNull():
                raise ValueError(f"无法创建QImage: {image_path}")
            
            # 转换为QPixmap
            pixmap = QPixmap.fromImage(qimage)
            
            if pixmap.isNull():
                raise ValueError(f"无法创建QPixmap: {image_path}")
            
            return pixmap

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
        self.before_label.setText("暂无预览")
        self.after_label.setText("暂无预览")

        max_diameter = self.max_diameter_spin.value()

        self.log("=" * 60)
        self.log(f"开始处理目录: {input_dir}")
        self.log(f"输出目录: {output_dir}")
        self.log(f"圆圈最大直径: {max_diameter}mm")
        self.log(f"检测模式: 智能边界检测（根据文字和竖线自动确定）")
        self.log("=" * 60)

        # 创建工作线程
        self.worker = CircleDetectionWorker(input_dir, output_dir, max_diameter)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.display_results)
        self.worker.finished_signal.connect(self.on_finished)

        self.worker.start()

        # 更新按钮状态
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.preview_btn.setEnabled(False)

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

        # 启用预览按钮
        if any(r['success'] and r['circles_found'] > 0 for r in results):
            self.preview_btn.setEnabled(True)

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
    window.setWindowTitle("黑色圆圈检测与裁剪工具")
    window.setGeometry(100, 100, 1400, 900)
    window.show()
    window.raise_()  # 确保窗口显示在最前面
    window.activateWindow()  # 激活窗口
    
    sys.exit(app.exec_())
