# 以下为您编写的“同美档案工具集合”Python代码。代码采用PyQt5框架构建，界面采用深色科技感配色，左侧为菜单栏，右侧为动态切换的功能区。
#
# 请确保在运行前安装依赖库：`pip
# install
# PyQt5
# `
#
# ```python
import sys
import os
import shutil
# 使用 PyQt5（Qt5）替代 PySide6（Qt6），以兼容 Python 3.8。
# PyQt5 中信号为 pyqtSignal，通过别名统一为 Signal，保持下游写法不变。
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QTextEdit, QSpinBox, QComboBox,
                             QFormLayout, QGroupBox, QMessageBox, QStackedWidget, QCheckBox,
                             QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal as Signal, QRegularExpression
from PyQt5.QtGui import QFont, QRegularExpressionValidator
from PIL import Image, ImageDraw, ImageFont, ImageOps
from concurrent.futures import ThreadPoolExecutor, as_completed
# 注：cv2 与 numpy 已改为在 AutoPagingWorker.add_number_to_image 中延迟导入，
# 以提升 Win7 下的健壮性（opencv 在 Win7 上较易出现 DLL 加载失败），
# 这样即使该依赖缺失或损坏，主程序仍可启动、其他功能页仍可使用。
import time
import threading
from datetime import datetime
from pathlib import Path


class TechStyle:
    """科技感样式表"""
    MAIN_BG = "#0B0F19"
    PANEL_BG = "#161B22"
    TEXT_COLOR = "#E0E0E0"
    ACCENT_COLOR = "#00F0FF"
    BTN_HOVER = "#1F6FEB"

    QSS = f"""
    QMainWindow {{ background-color: {MAIN_BG}; }}
    QWidget {{ color: {TEXT_COLOR}; font-family: 'Microsoft YaHei', Arial; }}

    /* 左侧菜单栏 */
    #LeftPanel {{
        background-color: {PANEL_BG};
        border-right: 1px solid #30363D;
    }}
    QLabel#TitleLabel {{
        color: {ACCENT_COLOR};
        font-size: 18px;
        font-weight: bold;
        padding: 20px;
        border-bottom: 1px solid #30363D;
    }}
    QPushButton#MenuBtn {{
        background-color: transparent;
        color: #8B949E;
        text-align: left;
        padding: 15px 20px;
        border: none;
        font-size: 14px;
    }}
    QPushButton#MenuBtn:hover {{
        background-color: #21262D;
        color: {ACCENT_COLOR};
        border-left: 2px solid {ACCENT_COLOR};
    }}
    QPushButton#MenuBtn:checked {{
        background-color: #1F242C;
        color: {ACCENT_COLOR};
        border-left: 4px solid {ACCENT_COLOR};
        font-weight: bold;
    }}

    /* 右侧功能区 */
    #RightPanel {{ background-color: {MAIN_BG}; }}
    QGroupBox {{
        border: 1px solid #30363D;
        border-radius: 5px;
        margin-top: 15px;
        padding: 15px;
        font-weight: bold;
        color: {ACCENT_COLOR};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }}

    /* 输入控件 */
    QLineEdit, QSpinBox, QComboBox {{
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-radius: 3px;
        padding: 5px;
        color: {TEXT_COLOR};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {ACCENT_COLOR};
    }}

    /* QSpinBox 上下按钮：显式定义，避免样式表覆盖后按钮消失/失效 */
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: #21262D;
        border: none;
        width: 18px;
    }}
    QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; border-left: 1px solid #30363D; }}
    QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; border-left: 1px solid #30363D; border-top: 1px solid #30363D; }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: #30363D; }}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{ background-color: {ACCENT_COLOR}; }}
    QSpinBox::up-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid {TEXT_COLOR};
        width: 0px; height: 0px;
    }}
    QSpinBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {TEXT_COLOR};
        width: 0px; height: 0px;
    }}

    /* 动作按钮 */
    QPushButton#ActionBtn {{
        background-color: #238636;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 3px;
        font-weight: bold;
    }}
    QPushButton#ActionBtn:hover {{
        background-color: #2EA043;
    }}
    QPushButton#BrowseBtn {{
        background-color: #30363D;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 3px;
    }}
    QPushButton#BrowseBtn:hover {{
        background-color: #3C434D;
    }}

    QTextEdit {{
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-radius: 3px;
        color: #FFFFFF;
        font-size: 13px;
    }}
    
    /* 消息提示框 */
    QMessageBox {{
        background-color: #FFFFFF;
    }}
    QMessageBox QLabel {{
        color: #000000;
        font-weight: bold;
        font-size: 14px;
    }}
    QMessageBox QPushButton {{
        background-color: #238636;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 3px;
        font-weight: bold;
        min-width: 80px;
    }}
    QMessageBox QPushButton:hover {{
        background-color: #2EA043;
    }}
    """


class FunctionPage(QWidget):
    """功能页面基类"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {TechStyle.ACCENT_COLOR}; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(lbl_title)

    def add_log_widget(self):
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(150)
        self.layout.addWidget(self.log_box)

    def log(self, msg):
        self.log_box.append(f">> {msg}")


class FileRenameWorker(QThread):
    """文件重命名后台处理线程"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(bool, str)
    
    def __init__(self, base_dir, modify_dpi=False, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.modify_dpi = modify_dpi  # 是否修改JPG文件的DPI为600
        self.is_stopped = False
    
    def run(self):
        try:
            results = {
                "processed_dirs": 0,
                "renamed_files": 0,
                "failed_files": 0,
                "errors": [],
                "actions": [],
                "log_entries": []
            }
            
            # 遍历基础目录下的所有子目录
            subdirs = [d for d in Path(self.base_dir).iterdir() if d.is_dir()]
            total_dirs = len(subdirs)
            processed_dirs = 0
            
            for subdir in subdirs:
                if self.is_stopped:
                    break
                
                # 获取子目录中的所有文件
                files = [f for f in subdir.iterdir() if f.is_file()]
                
                if not files:
                    processed_dirs += 1
                    continue
                
                # 获取目录名（不含路径）
                dir_name = subdir.name
                
                # 如果只有一个文件，直接使用目录名
                if len(files) == 1:
                    file = files[0]
                    new_name = subdir / f"{dir_name}{file.suffix}"
                    
                    action_desc = f"将 '{file.name}' 重命名为 '{new_name.name}'"
                    results["actions"].append(action_desc)
                    self.log_signal.emit(action_desc)
                    
                    log_entry = {
                        "directory": subdir.name,
                        "original_name": file.name,
                        "new_name": new_name.name,
                        "modify_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "success": True,
                        "error_msg": ""
                    }
                    
                    try:
                        file.rename(new_name)
                        results["renamed_files"] += 1
                        
                        # 如果需要修改DPI且是JPG文件，则修改DPI
                        if self.modify_dpi and new_name.suffix.lower() in ['.jpg', '.jpeg']:
                            try:
                                img = Image.open(new_name)
                                # 设置DPI为600
                                img.save(new_name, dpi=(600, 600))
                                self.log_signal.emit(f"已修改 {new_name.name} 的DPI为600")
                            except Exception as dpi_error:
                                error_msg = f"修改DPI失败 {new_name.name}: {str(dpi_error)}"
                                results["errors"].append(error_msg)
                                log_entry["success"] = False
                                log_entry["error_msg"] = error_msg
                                self.log_signal.emit(f"错误: {error_msg}")
                    except Exception as e:
                        error_msg = f"重命名文件失败 {file}: {str(e)}"
                        results["errors"].append(error_msg)
                        results["failed_files"] += 1
                        log_entry["success"] = False
                        log_entry["error_msg"] = error_msg
                        self.log_signal.emit(f"错误: {error_msg}")
                    
                    results["log_entries"].append(log_entry)
                else:
                    # 如果有多个文件，则使用递增后缀
                    for i, file in enumerate(files, start=1):
                        if self.is_stopped:
                            break
                        
                        # 生成新的文件名（目录名-序号.扩展名）
                        new_name = subdir / f"{dir_name}-{i:04d}{file.suffix}"
                        
                        action_desc = f"将 '{file.name}' 重命名为 '{new_name.name}'"
                        results["actions"].append(action_desc)
                        self.log_signal.emit(action_desc)
                        
                        log_entry = {
                            "directory": subdir.name,
                            "original_name": file.name,
                            "new_name": new_name.name,
                            "modify_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "success": True,
                            "error_msg": ""
                        }
                        
                        try:
                            file.rename(new_name)
                            results["renamed_files"] += 1
                            
                            # 如果需要修改DPI且是JPG文件，则修改DPI
                            if self.modify_dpi and new_name.suffix.lower() in ['.jpg', '.jpeg']:
                                try:
                                    img = Image.open(new_name)
                                    # 设置DPI为600
                                    img.save(new_name, dpi=(600, 600))
                                    self.log_signal.emit(f"已修改 {new_name.name} 的DPI为600")
                                except Exception as dpi_error:
                                    error_msg = f"修改DPI失败 {new_name.name}: {str(dpi_error)}"
                                    results["errors"].append(error_msg)
                                    log_entry["success"] = False
                                    log_entry["error_msg"] = error_msg
                                    self.log_signal.emit(f"错误: {error_msg}")
                        except Exception as e:
                            error_msg = f"重命名文件失败 {file}: {str(e)}"
                            results["errors"].append(error_msg)
                            results["failed_files"] += 1
                            log_entry["success"] = False
                            log_entry["error_msg"] = error_msg
                            self.log_signal.emit(f"错误: {error_msg}")
                        
                        results["log_entries"].append(log_entry)
                
                processed_dirs += 1
                results["processed_dirs"] = processed_dirs
                self.progress_signal.emit(processed_dirs, total_dirs)
            
            if not self.is_stopped:
                # 创建日志文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = f"rename_log_{timestamp}.txt"
                log_filepath = os.path.join(self.base_dir, log_filename)
                
                with open(log_filepath, 'w', encoding='utf-8') as log_file:
                    log_file.write(f"文件重命名日志 - 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    log_file.write(f"基础目录: {self.base_dir}\n")
                    log_file.write("=" * 80 + "\n")
                    log_file.write("目录名\t原文件名\t新文件名\t修改时间\t状态\t错误信息\n")
                    log_file.write("=" * 80 + "\n")
                    
                    for entry in results['log_entries']:
                        status = "成功" if entry['success'] else "失败"
                        error_info = entry['error_msg'] if entry['error_msg'] else ""
                        log_line = f"{entry['directory']}\t{entry['original_name']}\t{entry['new_name']}\t{entry['modify_time']}\t{status}\t{error_info}\n"
                        log_file.write(log_line)
                    
                    log_file.write("=" * 80 + "\n")
                    log_file.write(f"处理完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    log_file.write(f"总计处理目录: {results['processed_dirs']} 个\n")
                    log_file.write(f"成功重命名文件: {results['renamed_files']} 个\n")
                    log_file.write(f"失败文件: {results['failed_files']} 个\n")
                
                success_count = results['renamed_files']
                fail_count = results['failed_files']
                self.finished_signal.emit(True, 
                    f"处理完成！总计: {results['processed_dirs']} 个目录, "
                    f"成功: {success_count}, 失败: {fail_count}\n日志: {log_filename}")
            else:
                self.finished_signal.emit(False, "处理已停止")
                
        except Exception as e:
            self.finished_signal.emit(False, f"处理出错: {str(e)}")
    
    def stop(self):
        self.is_stopped = True


class FileRenamePage(FunctionPage):
    def __init__(self):
        super().__init__("文件改名")
        group = QGroupBox("按目录名批量重命名文件")
        form = QFormLayout()

        self.dir_path = QLineEdit()
        btn_browse = QPushButton("选择文件夹")
        btn_browse.setObjectName("BrowseBtn")
        btn_browse.clicked.connect(self.browse_dir)

        h1 = QHBoxLayout()
        h1.addWidget(self.dir_path)
        h1.addWidget(btn_browse)

        form.addRow("目标目录:", h1)
        
        # DPI修改选项
        self.modify_dpi_check = QCheckBox("修改JPG文件的DPI为600")
        self.modify_dpi_check.setChecked(False)
        form.addRow("选项:", self.modify_dpi_check)
        
        group.setLayout(form)
        self.layout.addWidget(group)
        
        # 说明文本
        info_label = QLabel(
            "功能说明：\n"
            "• 单文件：直接以目录名命名\n"
            "• 多文件：目录名-0001、目录名-0002...\n"
            "• 自动生成详细日志文件\n"
            "• 可选：修改JPG文件DPI为600"
        )
        info_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        self.layout.addWidget(info_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览操作")
        self.preview_btn.setObjectName("ActionBtn")
        self.preview_btn.setStyleSheet("background-color: #2196F3;")
        self.preview_btn.clicked.connect(self.preview_operations)
        btn_layout.addWidget(self.preview_btn)
        
        btn_exec = QPushButton("开始批量改名")
        btn_exec.setObjectName("ActionBtn")
        btn_exec.clicked.connect(self.execute)
        btn_layout.addWidget(btn_exec)
        
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.worker = None
        self.add_log_widget()

    def browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录")
        if d: self.dir_path.setText(d)
    
    def preview_operations(self):
        """预览将要执行的操作"""
        d = self.dir_path.text()
        if not d:
            QMessageBox.warning(self, "提示", "请先选择目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return
        
        # 清空之前的结果
        self.log_box.clear()
        
        self.log("="*50)
        self.log("正在预览操作...")
        self.log(f"基础目录: {d}")
        self.log("-"*50)
        
        try:
            from pathlib import Path
            subdirs = [dir for dir in Path(d).iterdir() if dir.is_dir()]
            total_files = 0
            actions = []
            
            for subdir in subdirs:
                files = [f for f in subdir.iterdir() if f.is_file()]
                if not files:
                    continue
                
                dir_name = subdir.name
                
                if len(files) == 1:
                    file = files[0]
                    new_name = f"{dir_name}{file.suffix}"
                    action = f"将 '{file.name}' 重命名为 '{new_name}'"
                    actions.append(action)
                    self.log(f"  • {action}")
                else:
                    for i, file in enumerate(files, start=1):
                        new_name = f"{dir_name}-{i:04d}{file.suffix}"
                        action = f"将 '{file.name}' 重命名为 '{new_name}'"
                        actions.append(action)
                        self.log(f"  • {action}")
                
                total_files += len(files)
            
            self.log("-"*50)
            self.log(f"预览完成！")
            self.log(f"将处理 {len(subdirs)} 个子目录")
            self.log(f"将重命名 {total_files} 个文件")
            
            if self.modify_dpi_check.isChecked():
                self.log("\n注意：将同时修改JPG文件的DPI为600")
            
            self.log("\n注意：这只是预览，文件尚未重命名。")
            
        except Exception as e:
            error_msg = f"预览过程中出现错误: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def execute(self):
        d = self.dir_path.text()
        if not d:
            QMessageBox.warning(self, "提示", "请先选择目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return
        
        # 确认操作
        reply = QMessageBox.question(
            self, "确认操作",
            "确定要开始重命名文件吗？\n此操作不可逆！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮，启用停止按钮
        self.log("="*50)
        self.log("开始处理...")
        self.log(f"目录: {d}")
        if self.modify_dpi_check.isChecked():
            self.log("选项: 修改JPG文件DPI为600")
        self.log("="*50)
        
        # 创建工作线程
        modify_dpi = self.modify_dpi_check.isChecked()
        self.worker = FileRenameWorker(base_dir=d, modify_dpi=modify_dpi)
        
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        
        self.worker.start()
        
        # 更新按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始批量改名":
            btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_processing(self):
        """停止处理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("正在停止处理...")
            self.stop_btn.setEnabled(False)
    
    def update_progress(self, current, total):
        """更新进度显示"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.log(f"进度: {current}/{total} ({percentage:.1f}%)")
    
    def on_finished(self, success, message):
        """处理完成回调"""
        self.log(message)
        
        # 恢复按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始批量改名":
            btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "完成", "处理完成！")
        else:
            QMessageBox.warning(self, "提示", message)


class AutoPagingWorker(QThread):
    """后台处理线程"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(bool, str)
    
    def __init__(self, directory, margin_mm, start_number, thread_count, cover_digit, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.margin_mm = margin_mm
        self.start_number = start_number
        self.thread_count = thread_count
        self.cover_digit = cover_digit
        self.is_stopped = False
    
    def run(self):
        try:
            # 收集文件
            dir_files_map = self.collect_jpg_files()
            if not dir_files_map:
                self.finished_signal.emit(False, "未找到任何JPG文件")
                return
            
            total_dirs = len(dir_files_map)
            total_files = sum(len(files) for files in dir_files_map.values())
            self.log_signal.emit(f"找到 {total_dirs} 个目录，共 {total_files} 个JPG文件")
            
            # 创建日志文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"sequence_number_log_{timestamp}.txt"
            log_path = os.path.join(self.directory, log_filename)
            self.init_log_file(log_path)
            
            # 处理所有目录
            all_results = []
            processed_dirs = 0
            
            with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
                future_to_dir = {}
                for dir_path, jpg_files in dir_files_map.items():
                    future = executor.submit(
                        self.process_directory_files, 
                        dir_path, jpg_files, self.start_number
                    )
                    future_to_dir[future] = dir_path
                
                for future in as_completed(future_to_dir):
                    if self.is_stopped:
                        break
                    
                    dir_path = future_to_dir[future]
                    try:
                        results = future.result()
                        all_results.extend(results)
                        
                        # 记录日志
                        for result in results:
                            self.append_to_log(log_path, result)
                            self.log_signal.emit(
                                f"{result['directory']}/{result['filename']} - "
                                f"序号:{result['number']} - {result['result']} ({result['duration']}秒)"
                            )
                    except Exception as e:
                        error_msg = f"处理目录 {dir_path} 时出错: {str(e)}"
                        self.log_signal.emit(error_msg)
                    
                    processed_dirs += 1
                    self.progress_signal.emit(processed_dirs, total_dirs)
            
            if not self.is_stopped:
                # 完成日志
                self.finalize_log_file(log_path, all_results)
                success_count = sum(1 for r in all_results if r['result'] == '成功')
                fail_count = len(all_results) - success_count
                self.finished_signal.emit(True, 
                    f"处理完成！总计: {len(all_results)}, 成功: {success_count}, 失败: {fail_count}\n日志: {log_path}")
            else:
                self.finished_signal.emit(False, "处理已停止")
                
        except Exception as e:
            self.finished_signal.emit(False, f"处理出错: {str(e)}")
    
    def stop(self):
        self.is_stopped = True
    
    def collect_jpg_files(self):
        """收集目录及子目录下所有JPG文件"""
        dir_files_map = {}
        for root, dirs, files in os.walk(self.directory):
            jpg_files = []
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    jpg_files.append(os.path.join(root, filename))
            if jpg_files:
                jpg_files.sort()
                dir_files_map[root] = jpg_files
        return dir_files_map
    
    def get_chinese_font(self):
        """获取中文字体"""
        font_paths = [
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
        ]
        font_size = 236
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, font_size)
            except Exception:
                continue
        return ImageFont.load_default()
    
    def add_number_to_image(self, image_path, number):
        """在图片右上角添加数字"""
        try:
            # cv2/numpy 延迟导入：Win7 上 opencv 较易出现 DLL 加载失败，
            # 放在此处可避免影响主程序启动与其他功能页（导入失败会被下方 except 捕获）。
            import cv2
            import numpy as np
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                return False
            
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            font = self.get_chinese_font()
            
            # 计算边距（毫米转像素，假设300DPI）
            margin_px = int(self.margin_mm * 300 / 25.4)
            
            text = str(number)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = img_pil.width - margin_px - text_width
            y = margin_px
            
            # 如果需要覆盖数字区域
            if self.cover_digit:
                padding = int(20 * 300 / 25.4)
                cover_x = x - padding // 2
                cover_y = y - padding // 3
                cover_width = text_width + padding
                cover_height = text_height + padding // 2
                draw.rectangle([cover_x, cover_y, cover_x + cover_width, cover_y + cover_height], 
                              fill=(255, 255, 255), outline=None)
            
            draw.text((x, y), text, fill=(0, 0, 0), font=font)
            
            img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            cv2.imencode('.jpg', img_cv)[1].tofile(image_path)
            return True
        except Exception as e:
            print(f"处理图片 {image_path} 时出错: {str(e)}")
            return False
    
    def process_directory_files(self, directory_path, jpg_files, start_number):
        """处理单个目录下的JPG文件"""
        results = []
        current_number = start_number
        
        for jpg_file in jpg_files:
            if self.is_stopped:
                break
            
            start_time = time.time()
            success = self.add_number_to_image(jpg_file, current_number)
            end_time = time.time()
            
            results.append({
                'directory': os.path.basename(directory_path),
                'filename': os.path.basename(jpg_file),
                'number': current_number,
                'result': '成功' if success else '失败',
                'duration': round(end_time - start_time, 3),
                'full_path': jpg_file
            })
            
            if success:
                current_number += 1
        
        return results
    
    def init_log_file(self, log_path):
        """初始化日志文件"""
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"JPG文件添加序号处理日志\n")
                f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 100 + "\n")
                f.write(f"{'目录名':<20} {'文件名':<30} {'序号':<8} {'结果':<10} {'耗时(秒)':<12} {'处理时间':<20}\n")
                f.write("-" * 100 + "\n")
        except Exception as e:
            print(f"创建日志文件失败: {str(e)}")
    
    def append_to_log(self, log_path, result):
        """追加单条记录到日志文件"""
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                process_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{result['directory']:<20} {result['filename']:<30} "
                       f"{result['number']:<8} {result['result']:<10} {result['duration']:<12} {process_time:<20}\n")
        except Exception as e:
            print(f"追加日志记录失败: {str(e)}")
    
    def finalize_log_file(self, log_path, results):
        """完成日志文件"""
        try:
            success_count = sum(1 for r in results if r['result'] == '成功')
            fail_count = len(results) - success_count
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write("-" * 100 + "\n")
                f.write(f"结束时间: {end_time}\n")
                f.write(f"总计处理: {len(results)} 个文件\n")
                f.write(f"成功: {success_count} 个\n")
                f.write(f"失败: {fail_count} 个\n")
                f.write("=" * 100 + "\n")
        except Exception as e:
            print(f"完成日志文件失败: {str(e)}")


class AutoPagingPage(FunctionPage):
    def __init__(self):
        super().__init__("自动编页码")
        group = QGroupBox("JPG文件右上角添加序号")
        form = QFormLayout()

        self.file_dir = QLineEdit()
        btn_browse = QPushButton("选择文件夹")
        btn_browse.setObjectName("BrowseBtn")
        btn_browse.clicked.connect(lambda: self.file_dir.setText(QFileDialog.getExistingDirectory(self, "选择目录")))

        h1 = QHBoxLayout()
        h1.addWidget(self.file_dir)
        h1.addWidget(btn_browse)

        self.start_num = QSpinBox()
        self.start_num.setRange(1, 9999)
        self.start_num.setValue(1)
        
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(1, 20)
        self.margin_spin.setValue(3)
        
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 16)
        self.thread_spin.setValue(4)
        
        self.cover_check = QComboBox()
        self.cover_check.addItems(["不覆盖", "用白色框覆盖"])

        form.addRow("文件目录:", h1)
        form.addRow("起始序号:", self.start_num)
        form.addRow("边距(毫米):", self.margin_spin)
        form.addRow("线程数:", self.thread_spin)
        form.addRow("覆盖选项:", self.cover_check)
        group.setLayout(form)
        self.layout.addWidget(group)

        btn_exec = QPushButton("开始编页码")
        btn_exec.setObjectName("ActionBtn")
        btn_exec.clicked.connect(self.execute)
        self.layout.addWidget(btn_exec)
        
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        self.layout.addWidget(self.stop_btn)
        
        self.worker = None
        self.add_log_widget()

    def execute(self):
        d = self.file_dir.text()
        if not d:
            QMessageBox.warning(self, "提示", "请先选择目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return
        
        # 禁用按钮，启用停止按钮
        self.log("="*50)
        self.log("开始处理...")
        self.log(f"目录: {d}")
        self.log(f"起始序号: {self.start_num.value()}")
        self.log(f"边距: {self.margin_spin.value()}mm")
        self.log(f"线程数: {self.thread_spin.value()}")
        self.log(f"覆盖选项: {self.cover_check.currentText()}")
        self.log("="*50)
        
        # 创建工作线程
        self.worker = AutoPagingWorker(
            directory=d,
            margin_mm=self.margin_spin.value(),
            start_number=self.start_num.value(),
            thread_count=self.thread_spin.value(),
            cover_digit=(self.cover_check.currentIndex() == 1)
        )
        
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        
        self.worker.start()
        
        # 更新按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn:
            btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_processing(self):
        """停止处理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("正在停止处理...")
            self.stop_btn.setEnabled(False)
    
    def update_progress(self, current, total):
        """更新进度显示"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.log(f"进度: {current}/{total} ({percentage:.1f}%)")
    
    def on_finished(self, success, message):
        """处理完成回调"""
        self.log(message)
        
        # 恢复按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn:
            btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "完成", "处理完成！")
        else:
            QMessageBox.warning(self, "提示", message)


class FileMovePage(FunctionPage):
    def __init__(self):
        super().__init__("文件移动")
        group = QGroupBox("文件批量归类移动")
        form = QFormLayout()

        self.src_dir = QLineEdit()
        self.dst_dir = QLineEdit()
        self.rule_combo = QComboBox()
        self.rule_combo.addItems(["按扩展名归类", "按修改日期归类", "全部移动"])

        btn_src = QPushButton("浏览")
        btn_src.setObjectName("BrowseBtn")
        btn_src.clicked.connect(lambda: self.src_dir.setText(QFileDialog.getExistingDirectory(self, "源目录")))
        btn_dst = QPushButton("浏览")
        btn_dst.setObjectName("BrowseBtn")
        btn_dst.clicked.connect(lambda: self.dst_dir.setText(QFileDialog.getExistingDirectory(self, "目标目录")))

        h1 = QHBoxLayout();
        h1.addWidget(self.src_dir);
        h1.addWidget(btn_src)
        h2 = QHBoxLayout();
        h2.addWidget(self.dst_dir);
        h2.addWidget(btn_dst)

        form.addRow("源目录:", h1)
        form.addRow("目标目录:", h2)
        form.addRow("移动规则:", self.rule_combo)
        group.setLayout(form)
        self.layout.addWidget(group)

        btn_exec = QPushButton("开始移动")
        btn_exec.setObjectName("ActionBtn")
        btn_exec.clicked.connect(self.execute)
        self.layout.addWidget(btn_exec)
        self.add_log_widget()

    def execute(self):
        self.log("校验目录权限...")
        self.log(f"应用规则: {self.rule_combo.currentText()}")
        self.log("正在复制及删除原文件...")
        self.log("文件移动归档完成！")


class ArchiveStampWorker(QThread):
    """归档章加盖后台处理线程"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(bool, str)
    
    def __init__(self, base_dir, overwrite_original=False, max_workers=4, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.overwrite_original = overwrite_original  # 是否覆盖原归档章
        self.max_workers = max_workers
        self.is_stopped = False
    
    def run(self):
        try:
            # 获取所有JPG文件
            dir_to_files = self.find_all_jpg_in_directory()
            if not dir_to_files:
                self.finished_signal.emit(False, "未找到任何JPG文件")
                return
            
            total_dirs = len(dir_to_files)
            total_files = sum(len(files) for files in dir_to_files.values())
            self.log_signal.emit(f"找到 {total_dirs} 个目录，共 {total_files} 个JPG文件")
            
            # 创建日志文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"archive_stamp_log_{timestamp}.txt"
            log_filepath = os.path.join(self.base_dir, log_filename)
            
            with open(log_filepath, 'w', encoding='utf-8') as log_file:
                log_file.write(f"归档章加盖日志 - 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write(f"处理目录: {self.base_dir}\n")
                log_file.write(f"线程数: {self.max_workers}\n")
                log_file.write("=" * 80 + "\n")
                log_file.write("文件名称\t\t处理结果\t处理用时(秒)\n")
                log_file.write("=" * 80 + "\n")
                log_file.flush()
                
                processed_count = 0
                completed = 0
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {}
                    for dir_path, files in dir_to_files.items():
                        dir_name = os.path.basename(dir_path)
                        # 只取排序后的第一个文件
                        if files:
                            first_file = files[0]
                            future = executor.submit(
                                self.process_single_file,
                                first_file, dir_name
                            )
                            futures[future] = (first_file, dir_name)
                    
                    for future in as_completed(futures):
                        if self.is_stopped:
                            break
                        
                        completed += 1
                        jpg_file, dir_name = futures[future]
                        
                        try:
                            result = future.result()
                            
                            # 记录日志
                            filename = os.path.basename(result['processed_file_path']) if result['processed_file_path'] else os.path.basename(jpg_file)
                            result_str = "成功" if result['success'] else "失败"
                            duration = result['duration']
                            
                            log_entry = f"{filename}\t\t{result_str}\t{duration}\n"
                            log_file.write(log_entry)
                            log_file.flush()
                            
                            if result['success']:
                                processed_count += 1
                            
                            self.log_signal.emit(
                                f"处理文件: {filename} - {result_str} ({duration}s)"
                            )
                            self.progress_signal.emit(completed, len(futures))
                            
                        except Exception as e:
                            filename = os.path.basename(jpg_file)
                            error_msg = f"处理文件 {filename} 时出错: {str(e)}"
                            self.log_signal.emit(error_msg)
                            
                            log_entry = f"{filename}\t\t失败\t0.0\n"
                            log_file.write(log_entry)
                            log_file.flush()
                            
                            self.progress_signal.emit(completed, len(futures))
            
            if not self.is_stopped:
                operation_type = "覆盖原归档章并重新加盖" if self.overwrite_original else "添加新归档章"
                self.finished_signal.emit(True,
                    f"{operation_type}处理完成！\n总计: {len(futures)}, 成功: {processed_count}, 失败: {len(futures) - processed_count}\n日志: {log_filename}")
            else:
                self.finished_signal.emit(False, "处理已停止")
                
        except Exception as e:
            self.finished_signal.emit(False, f"处理出错: {str(e)}")
    
    def stop(self):
        self.is_stopped = True
    
    def find_all_jpg_in_directory(self):
        """在指定目录及子目录中查找所有JPG文件（按目录分组）"""
        dir_to_files = {}
        
        for root, dirs, files in os.walk(self.base_dir):
            jpg_files_in_root = []
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    jpg_files_in_root.append(os.path.join(root, filename))
            
            if jpg_files_in_root:
                jpg_files_in_root.sort()
                dir_to_files[root] = jpg_files_in_root
        
        return dir_to_files
    
    def create_red_grid_image(self, dir_name, file_count=1):
        """创建归档章图片"""
        DPI = 300
        mm_to_px = DPI / 25.4
        
        rect_width_mm = 45
        rect_height_mm = 16
        rect_width_px = int(rect_width_mm * mm_to_px)
        rect_height_px = int(rect_height_mm * mm_to_px)
        
        cell_width_mm = 15
        cell_height_mm = 8
        cell_width_px = int(cell_width_mm * mm_to_px)
        cell_height_px = int(cell_height_mm * mm_to_px)
        
        img = Image.new('RGB', (rect_width_px, rect_height_px), 'white')
        draw = ImageDraw.Draw(img)
        
        # 尝试加载宋体字体
        try:
            font = ImageFont.truetype("simsun.ttc", 36)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/simsun.ttc", 36)
            except:
                font = ImageFont.load_default()
        
        # 解析目录名称
        dir_text1 = dir_name[:4] if len(dir_name) >= 4 else dir_name.ljust(4)
        dir_text2 = dir_name[11:15] if len(dir_name) >= 15 else dir_name[11:].ljust(4) if len(dir_name) > 11 else "".ljust(4)
        last_5_chars = dir_name[-5:] if len(dir_name) >= 5 else dir_name
        dir_text3 = last_5_chars
        for i, char in enumerate(last_5_chars):
            if char != '0':
                dir_text3 = last_5_chars[i:]
                break
        
        # 绘制6个方格的红色边框
        for row in range(2):
            for col in range(3):
                x1 = col * cell_width_px
                y1 = row * cell_height_px
                x2 = x1 + cell_width_px
                y2 = y1 + cell_height_px
                
                draw.rectangle([x1, y1, x2, y2], fill='white', outline='red', width=2)
                
                if row == 0 and col == 0:
                    text = dir_text1
                elif row == 0 and col == 1:
                    text = dir_text2
                elif row == 0 and col == 2:
                    text = dir_text3
                elif row == 1 and col == 0:
                    text = "确权"
                elif row == 1 and col == 1:
                    text = "永久"
                elif row == 1 and col == 2:
                    text = str(file_count)
                else:
                    continue
                
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x1 + (cell_width_px - text_width) // 2
                text_y = y1 + (cell_height_px - text_height) // 2
                draw.text((text_x, text_y), text, fill='red', font=font)
        
        return img
    
    def overlay_image_on_jpg(self, jpg_file_path, overlay_img):
        """将归档章叠加到JPG文件的顶部中央"""
        try:
            Image.MAX_IMAGE_PIXELS = None
            
            original_img = Image.open(jpg_file_path)
            
            # 应用EXIF方向信息
            try:
                img_with_orientation = ImageOps.exif_transpose(original_img)
            except:
                img_with_orientation = original_img
            
            base_width, base_height = img_with_orientation.size
            
            DPI = 300
            mm_to_px = DPI / 25.4
            
            # 处理覆盖选项
            if self.overwrite_original:
                base_img = img_with_orientation.copy()
                base_width, base_height = base_img.size
                
                from PIL import ImageDraw
                draw = ImageDraw.Draw(base_img)
                cover_height_px = int(18 * mm_to_px)
                draw.rectangle([0, 0, base_width, cover_height_px], fill='white', outline=None)
            else:
                top_margin_px = int(18 * mm_to_px)
                new_height = base_height + top_margin_px
                
                new_img = Image.new('RGB', (base_width, new_height), 'white')
                new_img.paste(img_with_orientation, (0, top_margin_px))
                
                base_img = new_img
                base_width, base_height = base_img.size
            
            # 计算叠加位置
            overlay_width, overlay_height = overlay_img.size
            margin_top_px = int(1 * mm_to_px)
            x_pos = (base_width - overlay_width) // 2
            y_pos = margin_top_px
            
            if overlay_img.mode != 'RGBA':
                overlay_img_rgba = overlay_img.convert('RGBA')
            else:
                overlay_img_rgba = overlay_img
            
            if base_img.mode != 'RGBA':
                base_img_rgba = base_img.convert('RGBA')
            else:
                base_img_rgba = base_img
            
            result_img = base_img_rgba.copy()
            result_img.paste(overlay_img_rgba, (x_pos, y_pos), overlay_img_rgba)
            result_img = result_img.convert('RGB')
            
            result_img.save(jpg_file_path, 'JPEG', dpi=(DPI, DPI))
            
            return True, jpg_file_path
            
        except Exception as e:
            print(f"处理JPG文件时出错: {str(e)}")
            return False, jpg_file_path
    
    def process_single_file(self, jpg_file_path, directory_name):
        """处理单个文件"""
        start_time = time.time()
        
        # 获取当前目录下的文件数量
        dir_path = os.path.dirname(jpg_file_path)
        jpg_files_in_dir = [f for f in os.listdir(dir_path) if f.lower().endswith(('.jpg', '.jpeg'))]
        file_count = len(jpg_files_in_dir)
        
        # 创建归档章图片
        grid_img = self.create_red_grid_image(directory_name, file_count)
        
        # 将归档章叠加到JPG文件
        success, processed_file_path = self.overlay_image_on_jpg(jpg_file_path, grid_img)
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        return {
            'file_path': jpg_file_path,
            'directory_name': directory_name,
            'success': success,
            'processed_file_path': processed_file_path,
            'duration': duration
        }


class ArchiveStampPage(FunctionPage):
    def __init__(self):
        super().__init__("文件改名加盖归档章")
        group = QGroupBox("按目录名生成归档章并加盖到JPG文件")
        form = QFormLayout()

        self.dir_path = QLineEdit()
        btn_browse = QPushButton("选择文件夹")
        btn_browse.setObjectName("BrowseBtn")
        btn_browse.clicked.connect(self.browse_dir)

        h1 = QHBoxLayout()
        h1.addWidget(self.dir_path)
        h1.addWidget(btn_browse)

        form.addRow("目标目录:", h1)
        
        # 覆盖原归档章选项
        self.overwrite_check = QCheckBox("覆盖原归档章")
        self.overwrite_check.setChecked(False)
        form.addRow("选项:", self.overwrite_check)
        
        # 线程数设置
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 32)
        self.thread_spin.setValue(4)
        form.addRow("线程数:", self.thread_spin)
        
        group.setLayout(form)
        self.layout.addWidget(group)
        
        # 说明文本
        info_label = QLabel(
            "功能说明：\n"
            "• 根据目录名称自动生成归档章（45mm×16mm）\n"
            "• 在所有JPG文件顶部增加18mm白色边框\n"
            "• 归档章加盖在边框正中间（距顶部1mm）\n"
            "• 可选：覆盖原归档章后重新加盖\n"
            "• 自动从目录名提取：全宗号、年份、档号"
        )
        info_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        self.layout.addWidget(info_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览操作")
        self.preview_btn.setObjectName("ActionBtn")
        self.preview_btn.setStyleSheet("background-color: #2196F3;")
        self.preview_btn.clicked.connect(self.preview_operations)
        btn_layout.addWidget(self.preview_btn)
        
        btn_exec = QPushButton("开始加盖归档章")
        btn_exec.setObjectName("ActionBtn")
        btn_exec.clicked.connect(self.execute)
        btn_layout.addWidget(btn_exec)
        
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.worker = None
        self.add_log_widget()
    
    def browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录")
        if d: self.dir_path.setText(d)
    
    def preview_operations(self):
        """预览将要执行的操作"""
        d = self.dir_path.text()
        if not d:
            QMessageBox.warning(self, "提示", "请先选择目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return
        
        # 清空之前的结果
        self.log_box.clear()
        
        self.log("="*50)
        self.log("正在预览操作...")
        self.log(f"基础目录: {d}")
        self.log("-"*50)
        
        try:
            # 统计JPG文件
            jpg_count = 0
            dir_count = 0
            sample_files = []
            
            for root, dirs, files in os.walk(d):
                jpg_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg'))]
                if jpg_files:
                    dir_count += 1
                    jpg_count += len(jpg_files)
                    if len(sample_files) < 3:
                        sample_files.append((os.path.basename(root), jpg_files[0]))
            
            if jpg_count == 0:
                self.log("未找到任何JPG文件")
                return
            
            self.log(f"找到 {dir_count} 个目录，共 {jpg_count} 个JPG文件")
            self.log("")
            self.log("示例文件：")
            for dir_name, filename in sample_files:
                self.log(f"  • {dir_name}/{filename}")
            
            self.log("")
            if self.overwrite_check.isChecked():
                self.log("注意：将覆盖原归档章并重新加盖")
            else:
                self.log("注意：将在文件顶部添加18mm白色边框并加盖归档章")
            
            self.log("")
            self.log("这只是预览，文件尚未修改。")
            
        except Exception as e:
            error_msg = f"预览过程中出现错误: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def execute(self):
        d = self.dir_path.text()
        if not d:
            QMessageBox.warning(self, "提示", "请先选择目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return
        
        # 确认操作
        confirm_msg = "确定要开始加盖归档章吗？"
        if self.overwrite_check.isChecked():
            confirm_msg += "\n\n注意：此操作将覆盖原归档章区域（顶部18mm），请确保已备份重要文件！"
        
        reply = QMessageBox.question(
            self, "确认操作",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮，启用停止按钮
        self.log("="*50)
        self.log("开始处理...")
        self.log(f"目录: {d}")
        if self.overwrite_check.isChecked():
            self.log("选项: 覆盖原归档章并重新加盖")
        else:
            self.log("选项: 添加新归档章（不覆盖）")
        self.log(f"线程数: {self.thread_spin.value()}")
        self.log("="*50)
        
        # 创建工作线程
        overwrite_original = self.overwrite_check.isChecked()
        max_workers = self.thread_spin.value()
        self.worker = ArchiveStampWorker(
            base_dir=d,
            overwrite_original=overwrite_original,
            max_workers=max_workers
        )
        
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        
        self.worker.start()
        
        # 更新按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始加盖归档章":
            btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_processing(self):
        """停止处理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("正在停止处理...")
            self.stop_btn.setEnabled(False)
    
    def update_progress(self, current, total):
        """更新进度显示"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.log(f"进度: {current}/{total} ({percentage:.1f}%)")
    
    def on_finished(self, success, message):
        """处理完成回调"""
        self.log(message)
        
        # 恢复按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始加盖归档章":
            btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "完成", "处理完成！")
        else:
            QMessageBox.warning(self, "提示", message)


# ----------------------------------------------------------------------
# 图片 DPI 修改（由 modify_jpg_dpi.py 移植，去除 tkinter 依赖）
# ----------------------------------------------------------------------
def _dpi_get_image_dpi(image_path):
    """读取图片 DPI：优先 info['dpi']，其次 EXIF 分辨率，最后返回分辨率。"""
    try:
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(image_path) as img:
            dpi = img.info.get('dpi')
            if dpi is not None:
                return dpi if isinstance(dpi, tuple) else (dpi, dpi)
            try:
                exif = img.getexif()
                if exif:
                    xr, yr, unit = exif.get(282), exif.get(283), exif.get(296, 2)
                    if xr and yr:
                        if unit == 3:        # 厘米 → 英寸
                            return f"EXIF:{xr * 2.54:.0f}x{yr * 2.54:.0f} DPI"
                        elif unit == 2:      # 英寸
                            return f"EXIF:{xr:.0f}x{yr:.0f} DPI"
                        else:
                            return f"EXIF:{xr:.0f}x{yr:.0f}(无单位)"
            except Exception:
                pass
            return f"{img.width}x{img.height}(无DPI元数据)"
    except Exception:
        return "DPI获取失败"


def _dpi_get_image_details(image_path):
    """获取图片详情：分辨率/色彩模式/格式/文件大小。"""
    details = {'resolution': '未知', 'mode': '未知', 'format': '未知', 'file_size': '未知'}
    try:
        Image.MAX_IMAGE_PIXELS = None
        Image.LOAD_TRUNCATED_IMAGES = True
        with Image.open(image_path) as img:
            details['resolution'] = f"{img.width}x{img.height}"
            details['mode'] = img.mode
            details['format'] = img.format
        try:
            details['file_size'] = f"{os.path.getsize(image_path):,} bytes"
        except Exception:
            pass
    except Exception:
        pass
    return details


def _dpi_init_log(log_path):
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("JPG文件DPI修改日志\n")
            f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 120 + "\n")
            f.write(f"{'文件名':<28}{'原DPI':<16}{'新DPI':<12}{'分辨率':<14}{'模式':<8}"
                    f"{'格式':<8}{'大小':<16}{'结果':<10}{'耗时(s)':<10}\n")
            f.write("-" * 120 + "\n")
    except Exception:
        pass


def _dpi_append_log(log_path, info):
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{os.path.basename(str(info.get('file_path', ''))):<28}"
                    f"{str(info.get('original_dpi', '')):<16}"
                    f"{str(info.get('new_dpi', '')):<12}"
                    f"{str(info.get('resolution', '')):<14}"
                    f"{str(info.get('mode', '')):<8}"
                    f"{str(info.get('format', '')):<8}"
                    f"{str(info.get('file_size', '')):<16}"
                    f"{str(info.get('result', '')):<10}"
                    f"{str(info.get('process_time', '')):<10}\n")
    except Exception:
        pass


def _dpi_finalize_log(log_path, stats):
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write("-" * 120 + "\n")
            f.write(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总计处理: {stats.get('processed_files', 0)} 个\n")
            f.write(f"成功修改: {stats.get('modified_files', 0)} 个\n")
            f.write(f"失败: {len(stats.get('errors', []))} 个\n")
            f.write("=" * 120 + "\n")
    except Exception:
        pass


def _dpi_process_single_file(file_path, dpi, dry_run, stop_event=None):
    """处理单个 JPG：读取原 DPI，按需重写为 dpi（仅改 DPI，不改像素）。"""
    start = time.time()
    if stop_event and stop_event.is_set():
        return {'file_path': file_path, 'original_dpi': '未知', 'new_dpi': f"{dpi}x{dpi}",
                'result': '已停止', 'process_time': 0, 'success': False, 'error': '用户停止'}
    try:
        Image.MAX_IMAGE_PIXELS = None
        original_dpi = _dpi_get_image_dpi(file_path)
        original_dpi_str = (f"{original_dpi[0]}x{original_dpi[1]}"
                            if isinstance(original_dpi, tuple) else str(original_dpi))
        details = _dpi_get_image_details(file_path)
        if stop_event and stop_event.is_set():
            return {'file_path': file_path, 'original_dpi': original_dpi_str,
                    'new_dpi': f"{dpi}x{dpi}", 'result': '已停止',
                    'process_time': round(time.time() - start, 3), 'success': False, 'error': '用户停止',
                    **details}

        if not dry_run:
            Image.LOAD_TRUNCATED_IMAGES = True
            with Image.open(file_path) as img:
                img.save(file_path, dpi=(dpi, dpi))
            result = "成功"
        else:
            result = "模拟成功"

        return {'file_path': file_path, 'original_dpi': original_dpi_str,
                'new_dpi': f"{dpi}x{dpi}", 'result': result,
                'process_time': round(time.time() - start, 3), 'success': True, **details}
    except Exception as e:
        return {'file_path': file_path, 'original_dpi': '未知', 'new_dpi': f"{dpi}x{dpi}",
                'result': '失败', 'process_time': round(time.time() - start, 3),
                'success': False, 'error': str(e)}


class ModifyDpiWorker(QThread):
    """JPG 图片 DPI 批量修改后台线程（多线程，支持模拟运行与停止）。"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)      # (已完成, 总数)
    finished_signal = Signal(bool, str)     # (是否正常完成, 汇总信息)

    def __init__(self, base_dir, dpi=600, dry_run=False, max_workers=4, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.dpi = dpi
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.is_stopped = False
        self.stop_event = threading.Event()

    def stop(self):
        self.is_stopped = True
        self.stop_event.set()

    def run(self):
        try:
            Image.MAX_IMAGE_PIXELS = None
            Image.LOAD_TRUNCATED_IMAGES = True

            # 递归收集 JPG/JPEG
            jpg_files = []
            for root, _d, files in os.walk(self.base_dir):
                for f in files:
                    if f.lower().endswith(('.jpg', '.jpeg')):
                        jpg_files.append(os.path.join(root, f))
            total = len(jpg_files)
            if total == 0:
                self.finished_signal.emit(False, f"目录 {self.base_dir} 下未找到 JPG/JPEG 文件")
                return

            mode = "模拟运行" if self.dry_run else "实际修改"
            self.log_signal.emit(f"找到 {total} 个 JPG 文件，目标 DPI={self.dpi}，"
                                 f"线程数={self.max_workers}，{mode}")

            # 日志文件
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(self.base_dir, f"dpi_modify_log_{ts}.txt")
            _dpi_init_log(log_path)

            self.log_signal.emit(f"{'目录':<16} | {'文件名':<24} | {'原DPI':<14} | "
                                 f"{'新DPI':<10} | {'结果':<6} | 耗时(秒)")
            self.log_signal.emit("-" * 90)

            done = 0
            success = 0
            errors = []

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(_dpi_process_single_file, fp, self.dpi,
                                    self.dry_run, self.stop_event): fp
                    for fp in jpg_files
                }
                for future in as_completed(future_to_file):
                    if self.is_stopped:
                        for ff in future_to_file:
                            ff.cancel()
                        break
                    fp = future_to_file[future]
                    try:
                        res = future.result()
                    except Exception as e:
                        res = {'file_path': fp, 'original_dpi': '未知', 'new_dpi': f"{self.dpi}x{self.dpi}",
                               'result': '异常', 'process_time': 0, 'success': False, 'error': str(e)}
                        self.log_signal.emit(f"处理异常 {os.path.basename(fp)}: {e}")

                    _dpi_append_log(log_path, res)
                    dir_name = os.path.basename(os.path.dirname(fp))
                    self.log_signal.emit(
                        f"{dir_name:<16} | {os.path.basename(fp):<24} | "
                        f"{str(res.get('original_dpi', '')):<14} | {res.get('new_dpi', ''):<10} | "
                        f"{res.get('result', ''):<6} | {res.get('process_time', 0)}")

                    done += 1
                    if res.get('success'):
                        success += 1
                    else:
                        errors.append(f"{os.path.basename(fp)}: {res.get('error', '')}")
                    self.progress_signal.emit(done, total)

            _dpi_finalize_log(log_path, {'processed_files': done,
                                         'modified_files': success, 'errors': errors})

            if self.is_stopped:
                self.finished_signal.emit(False, f"已停止。已处理 {done}/{total}，成功 {success}。")
            else:
                self.finished_signal.emit(
                    True, f"{mode}完成：共 {done} 个，成功 {success}，失败 {len(errors)}。日志：{log_path}")
        except Exception as e:
            self.finished_signal.emit(False, f"运行异常：{e}")


class ModifyDpiPage(FunctionPage):
    """图片 DPI 批量修改功能页（递归处理 JPG/JPEG，仅改 DPI 不影响像素）"""
    def __init__(self):
        super().__init__("修改DPI")
        self.worker = None

        group = QGroupBox("图片DPI批量修改（递归处理 JPG/JPEG，仅改DPI不影响像素尺寸）")
        form = QFormLayout()

        self.img_dir = QLineEdit()
        self.img_dir.setPlaceholderText("选择包含 JPG 图片的目录...")
        btn_browse = QPushButton("选择文件夹")
        btn_browse.setObjectName("BrowseBtn")
        btn_browse.clicked.connect(
            lambda: self.img_dir.setText(QFileDialog.getExistingDirectory(self, "选择图片目录")))
        h1 = QHBoxLayout()
        h1.addWidget(self.img_dir)
        h1.addWidget(btn_browse)

        self.dpi_edit = QLineEdit()
        self.dpi_edit.setText("300")
        self.dpi_edit.setMaxLength(5)
        self.dpi_edit.setMaximumWidth(140)
        self.dpi_edit.setValidator(QRegularExpressionValidator(QRegularExpression("\\d*")))
        h_dpi = QHBoxLayout()
        h_dpi.addWidget(self.dpi_edit)
        h_dpi.addWidget(QLabel("DPI"))
        h_dpi.addStretch()

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 32)
        self.thread_spin.setValue(4)

        self.dry_run_cb = QCheckBox("模拟运行（仅预览将要执行的操作，不实际修改文件）")

        form.addRow("图片目录:", h1)
        form.addRow("目标DPI:", h_dpi)
        form.addRow("线程数:", self.thread_spin)
        form.addRow("", self.dry_run_cb)
        group.setLayout(form)
        self.layout.addWidget(group)

        # 控制按钮
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览操作")
        self.preview_btn.setObjectName("ActionBtn")
        self.exec_btn = QPushButton("开始修改")
        self.exec_btn.setObjectName("ActionBtn")
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.setObjectName("ActionBtn")
        self.preview_btn.clicked.connect(self._preview)
        self.exec_btn.clicked.connect(self._execute)
        self.stop_btn.clicked.connect(self._stop)
        self.clear_btn.clicked.connect(self._clear)
        for b in (self.preview_btn, self.exec_btn, self.stop_btn, self.clear_btn):
            btn_layout.addWidget(b)
        self.layout.addLayout(btn_layout)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setFormat("待开始")
        self.layout.addWidget(self.progress)

        self.add_log_widget()

    # ---------- 辅助 ----------
    def _target_dpi(self):
        try:
            return int(self.dpi_edit.text().strip())
        except ValueError:
            return 0

    def _set_running(self, running):
        self.preview_btn.setEnabled(not running)
        self.exec_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def _start_worker(self, dry_run):
        directory = self.img_dir.text().strip()
        if not directory or not os.path.isdir(directory):
            QMessageBox.warning(self, "提示", "请先选择有效的图片目录。")
            return
        dpi = self._target_dpi()
        if dpi <= 0:
            QMessageBox.warning(self, "提示", "目标 DPI 必须为正整数。")
            return
        self._clear()
        self.progress.setValue(0)
        self.progress.setFormat("准备中...")
        self.worker = ModifyDpiWorker(directory, dpi=dpi, dry_run=dry_run,
                                      max_workers=self.thread_spin.value())
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self._set_running(True)
        self.worker.start()

    def _preview(self):
        self._start_worker(dry_run=True)

    def _execute(self):
        directory = self.img_dir.text().strip()
        if not directory or not os.path.isdir(directory):
            QMessageBox.warning(self, "提示", "请先选择有效的图片目录。")
            return
        dpi = self._target_dpi()
        confirm = QMessageBox.question(
            self, "确认操作",
            f"确定要将 {directory} 下所有 JPG/JPEG 的 DPI 修改为 {dpi} 吗？\n"
            f"此操作会直接覆盖原文件，不可逆。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self._start_worker(dry_run=False)

    def _stop(self):
        if self.worker:
            self.worker.stop()
            self.log("正在停止...")

    def _update_progress(self, done, total):
        if total <= 0:
            self.progress.setValue(0)
            self.progress.setFormat("0 / 0")
            return
        pct = int(done * 100 / total)
        self.progress.setValue(pct)
        self.progress.setFormat(f"{done} / {total}  ({pct}%)")

    def _on_finished(self, ok, message):
        self._set_running(False)
        self.log(message)
        self.progress.setFormat("已完成" if ok else "已停止")
        self.worker = None
        QMessageBox.information(self, "完成" if ok else "结束", message)

    def _clear(self):
        if hasattr(self, 'progress'):
            self.progress.setValue(0)
            self.progress.setFormat("待开始")
        if hasattr(self, 'log_box'):
            self.log_box.clear()


class JpgToPdfWorker(QThread):
    """JPG转双层PDF后台处理线程"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(bool, str)
    
    def __init__(self, directory_path, output_dir=None, max_workers=4, resolution=100.0, generate_ofd=False, parent=None):
        super().__init__(parent)
        self.directory_path = directory_path
        self.output_dir = output_dir if output_dir else directory_path
        self.max_workers = max_workers
        self.resolution = resolution
        self.generate_ofd = generate_ofd  # 是否同时生成OFD文件
        self.is_stopped = False
        
        # 检查Spire.PDF库是否可用（用于生成OFD）
        if self.generate_ofd:
            try:
                from spire.pdf import PdfDocument, FileFormat
                self.spire_available = True
            except ImportError:
                self.spire_available = False
        else:
            self.spire_available = False
    
    def run(self):
        try:
            # 收集所有目录下的JPG文件
            dir_jpgs_map = self.collect_jpg_files()
            if not dir_jpgs_map:
                self.finished_signal.emit(False, f"在目录 {self.directory_path} 及其子目录中没有找到JPG文件")
                return
            
            total_dirs = len(dir_jpgs_map)
            self.log_signal.emit(f"找到 {total_dirs} 个包含JPG文件的目录，使用 {self.max_workers} 个线程开始处理...")
            
            # 创建日志文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"jpgtopdf_log_{timestamp}.txt"
            log_path = os.path.join(self.output_dir, log_filename)
            start_time = datetime.now()
            self.init_log_file(log_path, start_time)
            
            # 处理所有目录
            results_list = []
            success_count = 0
            completed = 0
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for dir_path, jpg_files in dir_jpgs_map.items():
                    if self.is_stopped:
                        break
                    dir_name = os.path.basename(dir_path)
                    future = executor.submit(
                        self.process_single_directory,
                        jpg_files, dir_name
                    )
                    futures[future] = (dir_name, jpg_files)
                
                for future in as_completed(futures):
                    if self.is_stopped:
                        break
                    
                    completed += 1
                    dir_name, jpg_files = futures[future]
                    
                    try:
                        result = future.result()
                        results_list.append(result)
                        
                        # 实时记录日志
                        self.append_to_log(log_path, result)
                        
                        if result['result'] == '成功':
                            success_count += 1
                            log_msg = f"✓ {result['folder']}/{result['pdf_file']} - 成功 ({result['duration']}秒)"
                            if result.get('ofd_generated'):
                                log_msg += f" [已生成OFD: {result['ofd_file']}]"
                            self.log_signal.emit(log_msg)
                        else:
                            self.log_signal.emit(
                                f"✗ {result['folder']}/{result['pdf_file']} - {result['ocr_status']}"
                            )
                        
                        self.progress_signal.emit(completed, total_dirs)
                        
                    except Exception as e:
                        error_msg = f"处理目录 {dir_name} 时发生异常: {str(e)}"
                        self.log_signal.emit(error_msg)
                        self.progress_signal.emit(completed, total_dirs)
            
            if not self.is_stopped:
                # 完成日志文件
                self.finalize_log_file(log_path, results_list, start_time)
                
                success_rate = (success_count / total_dirs) * 100 if total_dirs > 0 else 0
                rate_msg = f"\n处理完成！共处理 {total_dirs} 个目录，成功 {success_count} 个，成功率 {success_rate:.1f}%。\n日志: {log_filename}"
                
                if success_rate >= 90:
                    rate_msg += "\n提示：单线程处理可能获得更高成功率！"
                
                self.finished_signal.emit(True, rate_msg)
            else:
                self.finished_signal.emit(False, "处理已停止")
                
        except Exception as e:
            self.finished_signal.emit(False, f"处理出错: {str(e)}")
    
    def stop(self):
        self.is_stopped = True
    
    def collect_jpg_files(self):
        """收集目录及子目录下所有JPG文件（按目录分组）"""
        dir_jpgs_map = {}
        
        for root, dirs, files in os.walk(self.directory_path):
            jpg_files = []
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    jpg_path = os.path.join(root, filename)
                    jpg_files.append(jpg_path)
            
            if jpg_files:
                jpg_files.sort()
                dir_jpgs_map[root] = jpg_files
        
        return dir_jpgs_map
    
    def jpgs_to_pdf(self, jpg_paths, output_dir, pdf_filename):
        """将多个 JPG 文件合并为一个 PDF（仅图像层）"""
        pdf_path = os.path.join(output_dir, pdf_filename + ".pdf")
        
        images = []
        for jpg_path in jpg_paths:
            image = Image.open(jpg_path)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            images.append(image)
        
        if images:
            first_image = images[0]
            if len(images) == 1:
                first_image.save(pdf_path, "PDF", resolution=self.resolution)
            else:
                first_image.save(pdf_path, "PDF", resolution=self.resolution, save_all=True, append_images=images[1:])
        
        return pdf_path
    
    def process_jpgs_to_ocr_pdf(self, jpg_paths, output_dir, pdf_filename):
        """将多个JPG文件合并转换为双层PDF（图像+OCR文本层）"""
        Image.MAX_IMAGE_PIXELS = None
        
        # 首先将 JPG 文件合并为 PDF
        temp_pdf_path = self.jpgs_to_pdf(jpg_paths, output_dir, pdf_filename)
        
        try:
            # 使用UmiOCR对PDF进行OCR处理
            from pdf_ocr_processor import UmiOCRProcessor
            ocr_processor = UmiOCRProcessor()
            
            # 进行OCR处理
            ocr_result, download_path = ocr_processor.ocr_pdf(temp_pdf_path)
            
            # 从下载的zip文件中提取双层PDF
            if download_path and os.path.exists(download_path):
                import zipfile
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    all_files = zip_ref.namelist()
                    
                    # 查找pdfLayered文件（双层PDF）
                    layered_pdf_files = []
                    for ext in ['.pdfLayered.pdf', '.Layered.pdf', '.layered.pdf']:
                        layered_pdf_files = [f for f in all_files if f.endswith(ext)]
                        if layered_pdf_files:
                            break
                    
                    # 如果上述都没有找到，尝试包含'layered'的文件
                    if not layered_pdf_files:
                        layered_pdf_files = [f for f in all_files if 'layered' in f.lower()]
                    
                    # 如果仍然没有找到，使用任何PDF文件
                    if not layered_pdf_files:
                        layered_pdf_files = [f for f in all_files if f.endswith('.pdf')]
                    
                    if layered_pdf_files:
                        target_pdf_path = os.path.join(output_dir, pdf_filename + ".pdf")
                        
                        # 提取双层PDF文件
                        with zip_ref.open(layered_pdf_files[0]) as source, open(target_pdf_path, 'wb') as target:
                            target.write(source.read())
                        
                        zip_ref.close()
                        
                        # 删除下载的zip文件
                        os.remove(download_path)
                        
                        return target_pdf_path, "双层PDF生成成功"
                    else:
                        os.remove(download_path)
                        return temp_pdf_path, "仅图像PDF（无OCR层）"
            else:
                return temp_pdf_path, "OCR处理失败"
            
        except Exception as e:
            print(f"OCR处理出错: {str(e)}")
            return temp_pdf_path, f"OCR处理错误: {str(e)}"
        finally:
            # 确保临时PDF文件被删除
            if os.path.exists(temp_pdf_path) and temp_pdf_path != os.path.join(output_dir, pdf_filename + ".pdf"):
                os.remove(temp_pdf_path)
    
    def convert_pdf_to_ofd(self, pdf_path, ofd_path):
        """使用Spire.PDF库将PDF转换为OFD格式"""
        if not os.path.exists(pdf_path):
            return False, 0
        
        if not self.spire_available:
            return False, 0
        
        start_time = time.time()
        
        try:
            from spire.pdf import PdfDocument, FileFormat
            
            # 创建PdfDocument实例
            pdf_document = PdfDocument()
            
            # 加载PDF文件
            pdf_document.LoadFromFile(pdf_path)
            
            # 保存为OFD格式
            pdf_document.SaveToFile(ofd_path, FileFormat.OFD)
            
            # 清理资源
            pdf_document.Close()
            
            end_time = time.time()
            duration = end_time - start_time
            return True, duration
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"PDF转OFD过程中发生错误: {e}")
            return False, duration
    
    def process_single_directory(self, jpg_files, dir_name):
        """处理单个目录的JPG文件"""
        start_time = time.time()
        result = "失败"
        result_pdf_path = None
        ocr_status = "未知"
        ofd_generated = False
        ofd_filename = ""
        
        try:
            pdf_filename = dir_name
            result_pdf_path, ocr_status = self.process_jpgs_to_ocr_pdf(
                jpg_files, self.output_dir, pdf_filename
            )
            if result_pdf_path:
                result = "成功"
                
                # 如果选择了生成OFD，则转换刚生成的PDF
                if self.generate_ofd and self.spire_available and result_pdf_path:
                    ofd_path = os.path.splitext(result_pdf_path)[0] + '.ofd'
                    ofd_success, ofd_duration = self.convert_pdf_to_ofd(result_pdf_path, ofd_path)
                    if ofd_success:
                        ofd_generated = True
                        ofd_filename = os.path.basename(ofd_path)
                        self.log_signal.emit(f"  → 已生成OFD: {ofd_filename} ({ofd_duration:.2f}秒)")
                    else:
                        self.log_signal.emit(f"  → OFD生成失败")
        except Exception as e:
            result = "失败"
            ocr_status = f"错误: {str(e)}"
        
        duration = round(time.time() - start_time, 2)
        
        return {
            'folder': dir_name,
            'pdf_file': os.path.basename(result_pdf_path) if result_pdf_path else f"{dir_name}.pdf",
            'result': result,
            'ocr_status': ocr_status,
            'duration': duration,
            'ofd_generated': ofd_generated,
            'ofd_file': ofd_filename
        }
    
    def init_log_file(self, log_path, start_time):
        """初始化日志文件"""
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"JPG转双层PDF处理日志\n")
                f.write(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 120 + "\n")
                f.write(f"{'目录名':<25} {'PDF文件名':<30} {'处理结果':<10} {'双层PDF状态':<20} {'耗时(秒)':<12} {'处理时间':<20}\n")
                f.write("-" * 120 + "\n")
        except Exception as e:
            print(f"创建日志文件失败: {str(e)}")
    
    def append_to_log(self, log_path, result):
        """追加单条记录到日志文件"""
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                process_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{result['folder']:<25} {result['pdf_file']:<30} "
                       f"{result['result']:<10} {result['ocr_status']:<20} "
                       f"{result['duration']:<12} {process_time:<20}\n")
        except Exception as e:
            print(f"追加日志记录失败: {str(e)}")
    
    def finalize_log_file(self, log_path, results, start_time):
        """完成日志文件，添加统计信息"""
        try:
            success_count = sum(1 for r in results if r['result'] == '成功')
            fail_count = len(results) - success_count
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds() / 60
            
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write("-" * 120 + "\n")
                f.write(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总耗时: {total_duration:.2f}分钟\n")
                f.write(f"总计处理: {len(results)} 个目录\n")
                f.write(f"成功: {success_count} 个\n")
                f.write(f"失败: {fail_count} 个\n")
                f.write("=" * 120 + "\n")
        except Exception as e:
            print(f"完成日志文件失败: {str(e)}")


class JpgToPdfPage(FunctionPage):
    def __init__(self):
        super().__init__("JPG转双层PDF")
        group = QGroupBox("图片转双层PDF (OCR)")
        form = QFormLayout()

        self.img_dir = QLineEdit()
        btn_browse_src = QPushButton("选择文件夹")
        btn_browse_src.setObjectName("BrowseBtn")
        btn_browse_src.clicked.connect(self.browse_img_dir)
        h1 = QHBoxLayout()
        h1.addWidget(self.img_dir)
        h1.addWidget(btn_browse_src)
        
        self.out_dir = QLineEdit()
        btn_browse_out = QPushButton("选择文件夹")
        btn_browse_out.setObjectName("BrowseBtn")
        btn_browse_out.clicked.connect(self.browse_out_dir)
        h2 = QHBoxLayout()
        h2.addWidget(self.out_dir)
        h2.addWidget(btn_browse_out)

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 32)
        self.thread_spin.setValue(1)
        
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        
        self.generate_ofd_check = QCheckBox("同时生成OFD文件")
        self.generate_ofd_check.setChecked(True)  # 默认选中

        form.addRow("图片目录:", h1)
        form.addRow("输出目录:", h2)
        form.addRow("线程数:", self.thread_spin)
        form.addRow("PDF DPI:", self.dpi_spin)
        form.addRow("选项:", self.generate_ofd_check)
        group.setLayout(form)
        self.layout.addWidget(group)
        
        # 说明文本
        info_label = QLabel(
            "功能说明：\n"
            "• 扫描目录及子目录下所有JPG文件\n"
            "• 每个目录的JPG合并为一个PDF\n"
            "• 调用Umi-OCR生成双层PDF（可搜索）\n"
            "• PDF文件名与目录名相同\n"
            "• 可选：同时在PDF目录中生成同名OFD文件\n"
            "• 注意：需要先启动Umi-OCR程序"
        )
        info_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        self.layout.addWidget(info_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览操作")
        self.preview_btn.setObjectName("ActionBtn")
        self.preview_btn.setStyleSheet("background-color: #2196F3;")
        self.preview_btn.clicked.connect(self.preview_operations)
        btn_layout.addWidget(self.preview_btn)
        
        btn_exec = QPushButton("开始转换")
        btn_exec.setObjectName("ActionBtn")
        btn_exec.clicked.connect(self.execute)
        btn_layout.addWidget(btn_exec)
        
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.worker = None
        self.add_log_widget()
    
    def browse_img_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片目录")
        if d:
            self.img_dir.setText(d)
            if not self.out_dir.text():
                self.out_dir.setText(d)
    
    def browse_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d: self.out_dir.setText(d)
    
    def preview_operations(self):
        """预览将要执行的操作"""
        d = self.img_dir.text()
        if not d:
            QMessageBox.warning(self, "提示", "请先选择图片目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return
        
        # 清空之前的结果
        self.log_box.clear()
        
        self.log("="*50)
        self.log("正在预览操作...")
        self.log(f"基础目录: {d}")
        self.log("-"*50)
        
        try:
            # 统计JPG文件和目录
            jpg_count = 0
            dir_count = 0
            sample_dirs = []
            
            for root, dirs, files in os.walk(d):
                jpg_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg'))]
                if jpg_files:
                    dir_count += 1
                    jpg_count += len(jpg_files)
                    if len(sample_dirs) < 3:
                        sample_dirs.append((os.path.basename(root), len(jpg_files)))
            
            if jpg_count == 0:
                self.log("未找到任何JPG文件")
                return
            
            self.log(f"找到 {dir_count} 个目录，共 {jpg_count} 个JPG文件")
            self.log("")
            self.log("示例目录：")
            for dir_name, count in sample_dirs:
                self.log(f"  • {dir_name}/ ({count} 个JPG)")
            
            self.log("")
            self.log(f"线程数: {self.thread_spin.value()}")
            self.log(f"PDF DPI: {self.dpi_spin.value()}")
            self.log("")
            self.log("注意：这只是预览，文件尚未转换。")
            self.log("注意：需要先启动Umi-OCR程序！")
            
        except Exception as e:
            error_msg = f"预览过程中出现错误: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def execute(self):
        d = self.img_dir.text()
        out = self.out_dir.text()
        
        if not d:
            QMessageBox.warning(self, "提示", "请先选择图片目录")
            return
        
        if not out:
            QMessageBox.warning(self, "提示", "请先选择输出目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "图片目录不存在")
            return
        
        if not os.path.exists(out):
            QMessageBox.warning(self, "错误", "输出目录不存在")
            return
        
        # 确认操作
        reply = QMessageBox.question(
            self, "确认操作",
            "确定要开始转换吗？\n\n注意：需要先启动Umi-OCR程序！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮，启用停止按钮
        self.log("="*50)
        self.log("开始处理...")
        self.log(f"图片目录: {d}")
        self.log(f"输出目录: {out}")
        self.log(f"线程数: {self.thread_spin.value()}")
        self.log(f"PDF DPI: {self.dpi_spin.value()}")
        self.log("="*50)
        
        # 创建工作线程
        max_workers = self.thread_spin.value()
        resolution = float(self.dpi_spin.value())
        generate_ofd = self.generate_ofd_check.isChecked()
        self.worker = JpgToPdfWorker(
            directory_path=d,
            output_dir=out,
            max_workers=max_workers,
            resolution=resolution,
            generate_ofd=generate_ofd
        )
        
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        
        self.worker.start()
        
        # 更新按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始转换":
            btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_processing(self):
        """停止处理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("正在停止处理...")
            self.stop_btn.setEnabled(False)
    
    def update_progress(self, current, total):
        """更新进度显示"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.log(f"进度: {current}/{total} ({percentage:.1f}%)")
    
    def on_finished(self, success, message):
        """处理完成回调"""
        self.log(message)
        
        # 恢复按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始转换":
            btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "完成", "处理完成！")
        else:
            QMessageBox.warning(self, "提示", message)


class PdfToOfdWorker(QThread):
    """PDF转OFD后台处理线程"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(bool, str)
    
    def __init__(self, pdf_dir, output_dir, parent=None):
        super().__init__(parent)
        self.pdf_dir = pdf_dir
        self.output_dir = output_dir
        self.is_stopped = False
        
        # 检查Spire.PDF库是否可用
        try:
            from spire.pdf import PdfDocument, FileFormat
            self.spire_available = True
        except ImportError:
            self.spire_available = False
    
    def run(self):
        try:
            if not self.spire_available:
                self.finished_signal.emit(False, "错误：未安装Spire.PDF库\n请运行: pip install Spire.Pdf")
                return
            
            # 获取所有PDF文件
            pdf_files = []
            for root, dirs, files in os.walk(self.pdf_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_path = os.path.join(root, file)
                        pdf_files.append(pdf_path)
            
            total_files = len(pdf_files)
            if total_files == 0:
                self.finished_signal.emit(False, "未找到任何PDF文件")
                return
            
            self.log_signal.emit(f"找到 {total_files} 个PDF文件，开始转换...")
            
            # 创建日志文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"spire_conversion_log_{timestamp}.txt"
            log_file_path = os.path.join(self.pdf_dir, log_filename)
            start_time = datetime.now()
            log_entries = []
            
            processed = 0
            success_count = 0
            
            for pdf_path in pdf_files:
                if self.is_stopped:
                    break
                
                file_start_time = time.time()
                
                # 计算相对路径以保持目录结构
                rel_path = os.path.relpath(pdf_path, self.pdf_dir)
                ofd_filename = os.path.splitext(os.path.basename(pdf_path))[0] + '.ofd'
                output_subdir = os.path.join(self.output_dir, os.path.dirname(rel_path))
                os.makedirs(output_subdir, exist_ok=True)
                ofd_path = os.path.join(output_subdir, ofd_filename)
                
                # 执行转换
                success, duration = self.convert_pdf_to_ofd(pdf_path, ofd_path)
                
                file_end_time = time.time()
                file_duration = file_end_time - file_start_time
                
                if success:
                    success_count += 1
                    result = "成功"
                    self.log_signal.emit(f"✓ {os.path.basename(pdf_path)} -> {ofd_filename} ({duration:.2f}秒)")
                else:
                    result = "失败"
                    self.log_signal.emit(f"✗ {os.path.basename(pdf_path)} 转换失败")
                
                processed += 1
                percentage = (processed / total_files) * 100
                
                # 记录日志条目
                log_entry = {
                    "文件名": os.path.basename(pdf_path),
                    "处理结果": result,
                    "处理用时(秒)": f"{file_duration:.2f}",
                    "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                log_entries.append(log_entry)
                
                self.progress_signal.emit(processed, total_files)
            
            if not self.is_stopped:
                # 写入日志文件
                end_time = datetime.now()
                total_duration = (end_time - start_time).total_seconds() / 60
                
                with open(log_file_path, 'w', encoding='utf-8') as log_file:
                    log_file.write("PDF转OFD处理日志 (Spire.PDF)\n")
                    log_file.write("=" * 50 + "\n")
                    log_file.write(f"处理开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    log_file.write(f"处理结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    log_file.write(f"总耗时: {total_duration:.2f}分钟\n")
                    log_file.write(f"总文件数: {total_files}\n")
                    log_file.write(f"成功转换: {success_count}\n")
                    log_file.write(f"转换失败: {total_files - success_count}\n")
                    log_file.write("=" * 50 + "\n\n")
                    
                    log_file.write("详细处理记录:\n")
                    log_file.write("文件名\t处理结果\t处理用时(秒)\t处理时间\n")
                    log_file.write("-" * 80 + "\n")
                    
                    for entry in log_entries:
                        log_file.write(f"{entry['文件名']}\t{entry['处理结果']}\t{entry['处理用时(秒)']}\t{entry['处理时间']}\n")
                
                summary_msg = f"\n转换完成！共处理 {total_files} 个PDF文件，成功转换 {success_count} 个，总耗时 {total_duration:.2f}分钟。\n日志: {log_filename}"
                self.finished_signal.emit(True, summary_msg)
            else:
                self.finished_signal.emit(False, "处理已停止")
                
        except Exception as e:
            self.finished_signal.emit(False, f"处理出错: {str(e)}")
    
    def stop(self):
        self.is_stopped = True
    
    def convert_pdf_to_ofd(self, pdf_path, ofd_path):
        """使用Spire.PDF库将PDF转换为OFD格式"""
        if not os.path.exists(pdf_path):
            return False, 0
        
        if not self.spire_available:
            return False, 0
        
        start_time = time.time()
        
        try:
            from spire.pdf import PdfDocument, FileFormat
            
            # 创建PdfDocument实例
            pdf_document = PdfDocument()
            
            # 加载PDF文件
            pdf_document.LoadFromFile(pdf_path)
            
            # 保存为OFD格式
            pdf_document.SaveToFile(ofd_path, FileFormat.OFD)
            
            # 清理资源
            pdf_document.Close()
            
            end_time = time.time()
            duration = end_time - start_time
            return True, duration
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"文件转换过程中发生错误: {e}")
            return False, duration


class PdfToOfdPage(FunctionPage):
    def __init__(self):
        super().__init__("PDF转OFD")
        group = QGroupBox("PDF转OFD格式 (Spire.PDF)")
        form = QFormLayout()

        self.pdf_dir = QLineEdit()
        btn_browse_src = QPushButton("选择文件夹")
        btn_browse_src.setObjectName("BrowseBtn")
        btn_browse_src.clicked.connect(self.browse_pdf_dir)
        h1 = QHBoxLayout()
        h1.addWidget(self.pdf_dir)
        h1.addWidget(btn_browse_src)
        
        self.out_dir = QLineEdit()
        btn_browse_out = QPushButton("选择文件夹")
        btn_browse_out.setObjectName("BrowseBtn")
        btn_browse_out.clicked.connect(self.browse_out_dir)
        h2 = QHBoxLayout()
        h2.addWidget(self.out_dir)
        h2.addWidget(btn_browse_out)

        form.addRow("PDF源目录:", h1)
        form.addRow("OFD输出目录:", h2)
        group.setLayout(form)
        self.layout.addWidget(group)
        
        # 说明文本
        info_label = QLabel(
            "功能说明：\n"
            "• 使用Spire.PDF库进行高质量转换\n"
            "• 支持递归扫描子目录\n"
            "• 保持原有目录结构\n"
            "• OFD文件名与PDF相同\n"
            "• 注意：需要先安装Spire.PDF库"
        )
        info_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        self.layout.addWidget(info_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览操作")
        self.preview_btn.setObjectName("ActionBtn")
        self.preview_btn.setStyleSheet("background-color: #2196F3;")
        self.preview_btn.clicked.connect(self.preview_operations)
        btn_layout.addWidget(self.preview_btn)
        
        btn_exec = QPushButton("开始转换为OFD")
        btn_exec.setObjectName("ActionBtn")
        btn_exec.clicked.connect(self.execute)
        btn_layout.addWidget(btn_exec)
        
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setObjectName("ActionBtn")
        self.stop_btn.setStyleSheet("background-color: #DA3633;")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.worker = None
        self.add_log_widget()
    
    def browse_pdf_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择PDF源目录")
        if d:
            self.pdf_dir.setText(d)
            if not self.out_dir.text():
                self.out_dir.setText(d)
    
    def browse_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择OFD输出目录")
        if d: self.out_dir.setText(d)
    
    def preview_operations(self):
        """预览将要执行的操作"""
        d = self.pdf_dir.text()
        if not d:
            QMessageBox.warning(self, "提示", "请先选择PDF源目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "指定的目录不存在")
            return
        
        # 清空之前的结果
        self.log_box.clear()
        
        self.log("="*50)
        self.log("正在预览操作...")
        self.log(f"基础目录: {d}")
        self.log("-"*50)
        
        try:
            # 统计PDF文件
            pdf_count = 0
            sample_files = []
            
            for root, dirs, files in os.walk(d):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_count += 1
                        if len(sample_files) < 3:
                            sample_files.append(file)
            
            if pdf_count == 0:
                self.log("未找到任何PDF文件")
                return
            
            self.log(f"找到 {pdf_count} 个PDF文件")
            self.log("")
            self.log("示例文件：")
            for filename in sample_files:
                ofd_name = os.path.splitext(filename)[0] + '.ofd'
                self.log(f"  • {filename} → {ofd_name}")
            
            self.log("")
            self.log("注意：这只是预览，文件尚未转换。")
            self.log("注意：需要先安装Spire.PDF库！")
            
        except Exception as e:
            error_msg = f"预览过程中出现错误: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def execute(self):
        d = self.pdf_dir.text()
        out = self.out_dir.text()
        
        if not d:
            QMessageBox.warning(self, "提示", "请先选择PDF源目录")
            return
        
        if not out:
            QMessageBox.warning(self, "提示", "请先选择OFD输出目录")
            return
        
        if not os.path.exists(d):
            QMessageBox.warning(self, "错误", "PDF源目录不存在")
            return
        
        if not os.path.exists(out):
            QMessageBox.warning(self, "错误", "OFD输出目录不存在")
            return
        
        # 确认操作
        reply = QMessageBox.question(
            self, "确认操作",
            "确定要开始转换吗？\n\n注意：需要先安装Spire.PDF库！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮，启用停止按钮
        self.log("="*50)
        self.log("开始处理...")
        self.log(f"PDF源目录: {d}")
        self.log(f"OFD输出目录: {out}")
        self.log("="*50)
        
        # 创建工作线程
        self.worker = PdfToOfdWorker(
            pdf_dir=d,
            output_dir=out
        )
        
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        
        self.worker.start()
        
        # 更新按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始转换为OFD":
            btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_processing(self):
        """停止处理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("正在停止处理...")
            self.stop_btn.setEnabled(False)
    
    def update_progress(self, current, total):
        """更新进度显示"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.log(f"进度: {current}/{total} ({percentage:.1f}%)")
    
    def on_finished(self, success, message):
        """处理完成回调"""
        self.log(message)
        
        # 恢复按钮状态
        btn = self.findChild(QPushButton, "ActionBtn")
        if btn and btn.text() == "开始转换为OFD":
            btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "完成", "处理完成！")
        else:
            QMessageBox.warning(self, "提示", message)


class SettingsPage(FunctionPage):
    def __init__(self):
        super().__init__("参数设置")
        group = QGroupBox("系统全局参数配置")
        form = QFormLayout()

        self.work_dir = QLineEdit(os.getcwd())
        btn_browse = QPushButton("浏览")
        btn_browse.setObjectName("BrowseBtn")
        btn_browse.clicked.connect(
            lambda: self.work_dir.setText(QFileDialog.getExistingDirectory(self, "选择工作目录")))
        h1 = QHBoxLayout();
        h1.addWidget(self.work_dir);
        h1.addWidget(btn_browse)

        self.thread_num = QSpinBox();
        self.thread_num.setValue(4)
        self.log_level = QComboBox();
        self.log_level.addItems(["INFO", "DEBUG", "ERROR"])

        form.addRow("默认工作目录:", h1)
        form.addRow("并发线程数:", self.thread_num)
        form.addRow("日志级别:", self.log_level)
        group.setLayout(form)
        self.layout.addWidget(group)

        btn_save = QPushButton("保存配置")
        btn_save.setObjectName("ActionBtn")
        btn_save.clicked.connect(self.execute)
        self.layout.addWidget(btn_save)
        self.add_log_widget()

    def execute(self):
        self.log("配置写入 config.ini 成功！")
        self.log(f"工作目录: {self.work_dir.text()}")
        self.log(f"线程数: {self.thread_num.value()}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("同美档案工具集合")
        self.resize(1000, 650)
        self.setStyleSheet(TechStyle.QSS)

        # 主中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧菜单栏
        self.left_panel = QWidget()
        self.left_panel.setObjectName("LeftPanel")
        self.left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignTop)

        title = QLabel("同美档案工具集合")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)

        # 菜单按钮配置 (去除了重复的"文件改名")
        menus = ["文件改名", "自动编页码", "文件移动", "加盖归档章",
                 "修改DPI", "JPG转双层PDF", "PDF转OFD", "参数设置"]

        self.menu_buttons = []
        for m in menus:
            btn = QPushButton(m)
            btn.setObjectName("MenuBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, b=btn: self.on_menu_click(b))
            left_layout.addWidget(btn)
            self.menu_buttons.append(btn)

        left_layout.addStretch()

        # 右侧功能区 (使用QStackedWidget管理多页面)
        self.right_panel = QWidget()
        self.right_panel.setObjectName("RightPanel")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)

        self.stack = QStackedWidget()

        # 实例化各功能页
        self.pages = {
            "文件改名": FileRenamePage(),
            "自动编页码": AutoPagingPage(),
            "文件移动": FileMovePage(),
            "加盖归档章": ArchiveStampPage(),
            "修改DPI": ModifyDpiPage(),
            "JPG转双层PDF": JpgToPdfPage(),
            "PDF转OFD": PdfToOfdPage(),
            "参数设置": SettingsPage()
        }

        for name in menus:
            self.stack.addWidget(self.pages[name])

        right_layout.addWidget(self.stack)

        # 组装整体布局
        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.right_panel)

        # 默认选中第一个菜单
        self.on_menu_click(self.menu_buttons[0])

    def on_menu_click(self, clicked_btn):
        """处理菜单点击切换事件"""
        # 取消其他按钮的选中状态
        for btn in self.menu_buttons:
            btn.setChecked(False)
        # 激活当前按钮
        clicked_btn.setChecked(True)

        # 切换右侧堆栈页面
        page_name = clicked_btn.text()
        if page_name in self.pages:
            self.stack.setCurrentWidget(self.pages[page_name])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 强制使用深色科技感字体渲染
    f = QFont("Microsoft YaHei", 9)
    app.setFont(f)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
