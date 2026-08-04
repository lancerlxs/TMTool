"""
JPG DPI 扫描工具 - 扫描目录及子目录下DPI不足指定值的JPG文件
集成到 TMToolMan.py 主程序中
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QTextEdit, QSpinBox, QFormLayout,
                             QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal as Signal
from PyQt5.QtGui import QFont


class DpiScanWorker(QThread):
    """DPI扫描后台工作线程"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    result_signal = Signal(list)  # 发送低DPI文件列表
    finished_signal = Signal(bool, str)

    def __init__(self, base_dir, min_dpi=300, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.min_dpi = min_dpi
        self.is_stopped = False

    def run(self):
        try:
            # 收集所有JPG文件
            jpg_files = []
            for root, dirs, files in os.walk(self.base_dir):
                if self.is_stopped:
                    break
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg')):
                        jpg_files.append(os.path.join(root, filename))

            total = len(jpg_files)
            if total == 0:
                self.finished_signal.emit(False, "未找到任何JPG/JPEG文件")
                return

            self.log_signal.emit(f"找到 {total} 个JPG文件，开始扫描DPI...")

            low_dpi_files = []
            processed = 0

            for jpg_path in jpg_files:
                if self.is_stopped:
                    break

                try:
                    dpi_value = self.get_image_dpi(jpg_path)

                    # 如果DPI低于阈值或无法获取DPI
                    if dpi_value is None or (isinstance(dpi_value, tuple) and dpi_value[0] < self.min_dpi):
                        file_info = {
                            'path': jpg_path,
                            'filename': os.path.basename(jpg_path),
                            'directory': os.path.basename(os.path.dirname(jpg_path)),
                            'dpi': f"{dpi_value[0]}x{dpi_value[1]}" if isinstance(dpi_value, tuple) else str(dpi_value),
                            'dpi_x': dpi_value[0] if isinstance(dpi_value, tuple) else 0,
                            'size': os.path.getsize(jpg_path)
                        }
                        low_dpi_files.append(file_info)
                        self.log_signal.emit(
                            f"发现低DPI文件: {file_info['directory']}/{file_info['filename']} - DPI: {file_info['dpi']}")

                except Exception as e:
                    self.log_signal.emit(f"处理文件失败 {os.path.basename(jpg_path)}: {str(e)}")

                processed += 1
                self.progress_signal.emit(processed, total)

            if not self.is_stopped:
                self.result_signal.emit(low_dpi_files)
                msg = f"扫描完成！共检查 {processed} 个文件，发现 {len(low_dpi_files)} 个DPI低于{self.min_dpi}的文件"
                self.finished_signal.emit(True, msg)
            else:
                self.finished_signal.emit(False, "扫描已停止")

        except Exception as e:
            self.finished_signal.emit(False, f"扫描出错: {str(e)}")

    def stop(self):
        self.is_stopped = True

    def get_image_dpi(self, image_path):
        """获取图片的DPI值，返回元组(x, y)或None"""
        try:
            with Image.open(image_path) as img:
                # 尝试从info中获取DPI
                dpi = img.info.get('dpi')
                if dpi is not None:
                    return dpi if isinstance(dpi, tuple) else (dpi, dpi)

                # 尝试从EXIF获取
                try:
                    exif = img.getexif()
                    if exif:
                        x_res = exif.get(282)  # XResolution
                        y_res = exif.get(283)  # YResolution
                        res_unit = exif.get(296, 2)  # ResolutionUnit (2=英寸, 3=厘米)

                        if x_res and y_res:
                            # 如果单位是厘米，转换为英寸
                            if res_unit == 3:
                                x_res = x_res * 2.54
                                y_res = y_res * 2.54

                            return (int(round(x_res)), int(round(y_res)))
                except:
                    pass

                return None
        except Exception:
            return None


class DpiScannerPage(QWidget):
    """DPI扫描页面"""

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        # 标题
        lbl_title = QLabel("JPG DPI 扫描仪")
        lbl_title.setStyleSheet("color: #00F0FF; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(lbl_title)

        # 设置组
        group = QGroupBox("扫描设置")
        form = QFormLayout()

        # 目录选择
        self.dir_path = QLineEdit()
        btn_browse = QPushButton("选择文件夹")
        btn_browse.setObjectName("BrowseBtn")
        btn_browse.clicked.connect(self.browse_dir)
        h1 = QHBoxLayout()
        h1.addWidget(self.dir_path)
        h1.addWidget(btn_browse)
        form.addRow("扫描目录:", h1)

        # 最小DPI设置
        self.min_dpi_spin = QSpinBox()
        self.min_dpi_spin.setRange(1, 1200)
        self.min_dpi_spin.setValue(300)
        form.addRow("最小DPI阈值:", self.min_dpi_spin)

        # 异常文件输出目录
        self.output_dir = QLineEdit()
        btn_browse_out = QPushButton("选择文件夹")
        btn_browse_out.setObjectName("BrowseBtn")
        btn_browse_out.clicked.connect(self.browse_output_dir)
        h2 = QHBoxLayout()
        h2.addWidget(self.output_dir)
        h2.addWidget(btn_browse_out)
        form.addRow("异常记录目录:", h2)

        # 自动创建异常目录选项
        self.auto_create_dir = QCheckBox("自动在源目录下创建'异常文件'目录")
        self.auto_create_dir.setChecked(True)
        form.addRow("", self.auto_create_dir)

        group.setLayout(form)
        self.layout.addWidget(group)

        # 说明文本
        info_label = QLabel(
            "功能说明：\n"
            "• 递归扫描指定目录及子目录下的所有JPG文件\n"
            "• 检测DPI值低于阈值的文件（默认300）\n"
            "• 将低DPI文件信息记录到指定目录\n"
            "• 生成详细的扫描报告"
        )
        info_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        self.layout.addWidget(info_label)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.scan_btn = QPushButton("开始扫描")
        self.scan_btn.setObjectName("ActionBtn")
        self.scan_btn.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("停止扫描")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton("导出结果")
        self.export_btn.setObjectName("ActionBtn")
        self.export_btn.setStyleSheet("background-color: #2196F3;")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)

        self.layout.addLayout(btn_layout)

        # 进度条
        from PyQt5.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("待开始")
        self.layout.addWidget(self.progress_bar)

        # 结果显示表格
        table_group = QGroupBox("扫描结果")
        table_layout = QVBoxLayout()

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["文件名", "所在目录", "DPI值", "文件大小", "完整路径"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.result_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.result_table)

        table_group.setLayout(table_layout)
        self.layout.addWidget(table_group)

        # 日志框
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(150)
        self.layout.addWidget(self.log_box)

        # 存储扫描结果
        self.scan_results = []
        self.worker = None

    def browse_dir(self):
        """选择扫描目录"""
        d = QFileDialog.getExistingDirectory(self, "选择扫描目录")
        if d:
            self.dir_path.setText(d)
            # 如果未设置输出目录，自动设置为源目录
            if not self.output_dir.text():
                self.output_dir.setText(d)

    def browse_output_dir(self):
        """选择输出目录"""
        d = QFileDialog.getExistingDirectory(self, "选择异常记录目录")
        if d:
            self.output_dir.setText(d)

    def start_scan(self):
        """开始扫描"""
        scan_dir = self.dir_path.text().strip()
        if not scan_dir:
            QMessageBox.warning(self, "提示", "请先选择扫描目录")
            return

        if not os.path.exists(scan_dir):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return

        # 清空之前的结果
        self.scan_results = []
        self.result_table.setRowCount(0)
        self.log_box.clear()

        min_dpi = self.min_dpi_spin.value()

        self.log("=" * 60)
        self.log(f"开始扫描目录: {scan_dir}")
        self.log(f"DPI阈值: {min_dpi}")
        self.log("=" * 60)

        # 创建工作线程
        self.worker = DpiScanWorker(scan_dir, min_dpi)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.display_results)
        self.worker.finished_signal.connect(self.on_finished)

        self.worker.start()

        # 更新按钮状态
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(False)

    def stop_scan(self):
        """停止扫描"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("正在停止扫描...")
            self.stop_btn.setEnabled(False)

    def update_progress(self, current, total):
        """更新进度"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.progress_bar.setValue(int(percentage))
        self.progress_bar.setFormat(f"{current} / {total} ({percentage:.1f}%)")

    def display_results(self, low_dpi_files):
        """显示扫描结果到表格"""
        self.scan_results = low_dpi_files

        if not low_dpi_files:
            self.log("\n✓ 未发现DPI低于阈值的文件")
            return

        self.log(f"\n发现 {len(low_dpi_files)} 个低DPI文件：")

        # 填充表格
        self.result_table.setRowCount(len(low_dpi_files))

        for row, file_info in enumerate(low_dpi_files):
            # 文件名
            item_name = QTableWidgetItem(file_info['filename'])
            self.result_table.setItem(row, 0, item_name)

            # 所在目录
            item_dir = QTableWidgetItem(file_info['directory'])
            self.result_table.setItem(row, 1, item_dir)

            # DPI值
            item_dpi = QTableWidgetItem(file_info['dpi'])
            item_dpi.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(row, 2, item_dpi)

            # 文件大小
            size_str = self.format_file_size(file_info['size'])
            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(row, 3, item_size)

            # 完整路径
            item_path = QTableWidgetItem(file_info['path'])
            item_path.setToolTip(file_info['path'])
            self.result_table.setItem(row, 4, item_path)

        self.log(f"✓ 已在下方表格显示所有低DPI文件")

    def on_finished(self, success, message):
        """扫描完成回调"""
        self.log(message)
        self.progress_bar.setFormat("已完成" if success else "已停止")

        # 恢复按钮状态
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if self.scan_results:
            self.export_btn.setEnabled(True)
            # 保存结果到文件
            self.save_results_to_file()

        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.warning(self, "结束", message)

    def save_results_to_file(self):
        """将扫描结果保存到文件"""
        if not self.scan_results:
            return

        # 确定输出目录
        output_dir = self.output_dir.text().strip()

        # 如果选择了自动创建异常目录
        if self.auto_create_dir.isChecked():
            scan_dir = self.dir_path.text().strip()
            output_dir = os.path.join(scan_dir, "异常文件")
            os.makedirs(output_dir, exist_ok=True)
            self.output_dir.setText(output_dir)
            self.log(f"✓ 已创建异常文件目录: {output_dir}")
        elif not output_dir:
            output_dir = os.path.dirname(self.dir_path.text().strip())

        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"低DPI文件清单_{timestamp}.txt"
        log_path = os.path.join(output_dir, log_filename)

        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"低DPI文件扫描报告\n")
                f.write("=" * 100 + "\n")
                f.write(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"扫描目录: {self.dir_path.text()}\n")
                f.write(f"DPI阈值: {self.min_dpi_spin.value()}\n")
                f.write(f"异常文件数: {len(self.scan_results)}\n")
                f.write("=" * 100 + "\n\n")

                f.write(f"{'序号':<6} {'文件名':<30} {'所在目录':<20} {'DPI值':<12} {'文件大小':<15} {'完整路径'}\n")
                f.write("-" * 100 + "\n")

                for idx, file_info in enumerate(self.scan_results, 1):
                    size_str = self.format_file_size(file_info['size'])
                    f.write(f"{idx:<6} {file_info['filename']:<30} {file_info['directory']:<20} "
                            f"{file_info['dpi']:<12} {size_str:<15} {file_info['path']}\n")

                f.write("-" * 100 + "\n")
                f.write(f"\n报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            self.log(f"✓ 扫描结果已保存到: {log_path}")

        except Exception as e:
            self.log(f"✗ 保存结果文件失败: {str(e)}")

    def export_results(self):
        """手动导出结果"""
        if not self.scan_results:
            QMessageBox.warning(self, "提示", "没有可导出的结果")
            return

        # 重新保存
        self.save_results_to_file()
        QMessageBox.information(self, "完成", "结果已导出到指定目录")

    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    def log(self, msg):
        """添加日志"""
        self.log_box.append(f">> {msg}")


# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置Windows 7兼容性
    try:
        from PyQt5.QtCore import Qt
        # 启用高DPI支持（如果需要）
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except:
        pass
    
    window = DpiScannerPage()
    window.setWindowTitle("JPG DPI 扫描仪")
    window.setGeometry(100, 100, 1200, 800)
    window.show()
    window.raise_()  # 确保窗口显示在最前面
    window.activateWindow()  # 激活窗口
    
    sys.exit(app.exec_())
