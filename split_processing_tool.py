"""
说明：此功能为法院一张网系统下案卷分件的工具 - 分件处理工具
根据用户设定的页码范围，将JPG文件按项目分件并生成PDF
时间：2026-06-19
修改记录：
 1. 2026-06-19 增加固定项目列表、文件名去零匹配等功能
 2.未增加OCR处理功能，仅生成PDF文件，因为一张网中的自己需要OCR
 3.2026-07-01 增加了tab，实现读个类型的列表并实现了自定义分件，增加了pdf文件名是否需要序号前缀的选择功能
 4.2026-07-09 增加了鼠标右键进行新增和删除一行的功能，
"""
import os
import sys
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import shutil

# 解除PIL像素限制
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

# 固定的29个民事案件项目列表
FIXED_PROJECTS = [
    "案件审判流程管理信息表、案件登记表",
    "诉讼材料收取清单",
    "案件移送函等表明案件来源的材料",
    "起诉状及相关材料",
    "反诉状及相关材料",
    "答辩状及相关材料",
    "交纳诉讼费用相关材料",
    "受理案件通知书、应诉通知书及相关材料",
    "诉讼参与人主体资格材料",
    "诉讼参与人提交的申请书及相关材料",
    "诉讼参与人举证材料",
    "法院调查取证材料",
    "多元纠纷化解相关材料",
    "保全相关材料",
    "开庭通知书、公告、传票等相关材料",
    "庭前会议笔录、法庭笔录及相关材料",
    "公益诉讼起诉人意见、代理词等材料",
    "调解协议、公益诉讼调解公告",
    "延长审理期限、扣除审理期限材料",
    "撤诉申请书、撤诉笔录",
    "本院法律文书正本",
    "宣判及委托送达类材料",
    "送达地址确认书、送达回证或其他送达凭证",
    "上诉案件相关材料",
    "其他与诉讼活动相关的材料"
]

# 固定的46个刑事卷项目列表
CRIMINAL_CASE_PROJECTS = [
    "案件审判流程管理信息表、案件登记表",
    "诉讼材料收取清单",
    "案件移送函等表明案件来源的材料",
    "起诉书及相关材料",
    "附带民事公益诉讼公告等材料",
    "送达起诉书副本记录",
    "量刑建议书",
    "适用简易程序建议书",
    "程序转换决定书",
    "认罪认罚具结书",
    "附带民事（公益）诉讼答辩状",
    "案件通知等相关告知材料",
    "诉讼参与人主体资格材料",
    "委托、指定辩护人材料",
    "诉讼参与人提交的申请书及相关材料",
    "搜查证、搜查勘验笔录及扣押物品清单",
    "查封令及查封物品清单",
    "取保候审、监视居住、逮捕决定书及相关材料",
    "退回补充侦查函及补充侦查材料",
    "证据材料",
    "法院调查取证材料",
    "法院调查、询问、讯问等笔录",
    "赔偿协议、附带民事诉讼谅解书",
    "开庭通知书、公告、传票、提押票、换押证等材料",
    "庭前会议笔录、证据展示材料",
    "法庭笔录",
    "公诉词、被告人的供述和辩解、辩护词、附带民事（公益）诉讼代理词",
    "附带民事（公益）诉讼调解协议、调解公告及多元纠纷化解相关材料",
    "延长审理期限、扣除审理期限材料",
    "撤诉申请书",
    "本院法律文书正本",
    "宣判公告、委托宣判函、宣判笔录",
    "妨碍诉讼的强制措施材料",
    "送达地址确认书、送达回证或其他送达凭证",
    "报请核准死刑案件报告及上诉移送函",
    "最高人民法院或高级人民法院判决书、裁定书",
    "执行死刑相关材料",
    "上诉案件相关材料",
    "执行通知书存根和回执、移送执行函",
    "赃证物移送清单及处理手续",
    "涉案资金处理的相关材料",
    "罚没款票据等材料",
    "未成年人犯罪记录封存相关材料",
    "其他与诉讼活动相关的材料"
]

# 固定的31个执行案件项目列表
CRIMINAL_PROJECTS = [
    "案件执行流程管理信息表、案件登记表",
    "申请执行材料收取清单",
    "申请执行书",
    "移送执行函（公益诉讼裁判生效后移送执行部门用）",
    "委托执行函等表明案件来源的材料",
    "执行依据",
    "受理案件通知书、提供被执行人财产状况告知书、申请执行人举报财产责任书",
    "执行通知书、财产申报表、报告财产令、被执行人报告财产责任书",
    "执行案件参与人主体资格材料",
    "申请执行人、被执行人、案外人举证材料",
    "法院询问笔录、调查笔录、听证笔录、执行笔录、谈话笔录、终本约谈笔录及取证材料",
    "财产查询材料",
    "财产处置材料",
    "行为执行材料",
    "强制措施材料",
    "解除、撤销强制执行措施材料",
    "追加、变更执行主体申请书及相关证明材料",
    "追加、变更执行主体裁定书正本",
    "强制执行裁定书正本",
    "执行和解协议、执行和解笔录",
    "执行和解协议履行情况的证明材料",
    "中止执行、终结执行、终结本次执行、不予执行、驳回申请等执行裁定书及执行凭证",
    "执行款物收取、交付凭证及有关审批材料",
    "执行异议、复议申请及相关材料",
    "撤回执行申请书",
    "延长执行期限材料",
    "委托执行函、受托执行复函",
    "结案相关材料",
    "交纳执行费用相关材料",
    "送达地址确认书、送达回证或其他送达凭证",
    "其他与执行工作相关的材料"
]

# 固定的12个执保案件项目列表
PRESERVATION_PROJECTS = [
    "案件执行流程管理信息表、案件登记表",
    "财产保全申请书",
    "裁定书",
    "财产保全执行申请人主体资格材料",
    "财产保全执行申请人提供的证明材料",
    "法院询问笔录、调查笔录、听证笔录、执行笔录、谈话笔录及取证材料",
    "财产查询材料",
    "财产处置材料",
    "财产保全清单",
    "结案相关材料",
    "送达地址确认书、送达回证或其他送达凭证",
    "其他与执行工作相关的材料"
]

# 固定的29个执恢案件项目列表
RESTORATION_PROJECTS = [
    "案件执行流程管理信息表、案件登记表",
    "申请执行材料收取清单",
    "恢复执行申请书",
    "执行依据",
    "受理案件通知书、提供被执行人财产状况告知书、申请执行人举报财产责任书",
    "执行通知书、财产申报表、报告财产令、被执行人报告财产责任书",
    "恢复执行案件参与人主体资格材料",
    "申请执行人、被执行人、案外人举证材料",
    "法院询问笔录、调查笔录、听证笔录、执行笔录、谈话笔录、终本约谈笔录及取证材料",
    "财产保全材料",
    "财产查询材料",
    "财产处置材料",
    "行为执行材料",
    "强制措施材料",
    "解除、撤销强制措施材料",
    "追加、变更执行主体申请书及相关证明材料",
    "追加、变更执行主体裁定书",
    "强制执行裁定书正本",
    "执行和解协议、执行和解笔录",
    "执行和解协议履行情况的证明材料",
    "中止执行、终结执行、终结本次执行、不予执行、驳回申请等执行裁定书及执行凭证",
    "执行款物收取、交付凭证及有关审批材料",
    "执行异议、复议申请及相关材料",
    "撤回执行申请书",
    "延长执行期限材料",
    "委托执行函、受托执行复函",
    "结案相关材料",
    "交纳执行费用相关材料",
    "送达地址确认书、送达回证或其他送达凭证",
    "其他与执行工作相关的材料"
]

# 固定的4个副卷项目列表
SUPPLEMENTARY_PROJECTS = [
    "合议庭评议笔录、汇报笔录",
    "审（签）批材料",
    "本院法律文书签发稿",
    "结案相关材料"
]

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# from pdf_ocr_processor import UmiOCRProcessor


def init_log_file(log_path, start_time):
    """
    初始化日志文件
    :param log_path: 日志文件路径
    :param start_time: 开始时间
    """
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"分件处理工具日志\n")
            f.write(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 120 + "\n")
            f.write(f"{'项目名称':<25} {'起始页':<10} {'终止页':<10} {'文件数量':<10} {'处理结果':<15} {'耗时(秒)':<12} {'执行时间':<20}\n")
            f.write("-" * 120 + "\n")
        print(f"日志文件已创建: {log_path}")
    except Exception as e:
        print(f"创建日志文件失败: {str(e)}")


def append_to_log(log_path, result):
    """
    追加单条记录到日志文件
    :param log_path: 日志文件路径
    :param result: 处理结果字典
    """
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            process_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 如果有详细错误信息，添加到日志中
            error_info = result.get('error_detail', '')
            status_display = f"{result['status']} - {error_info}" if error_info else result['status']
            f.write(f"{result['project']:<25} {result['start_page']:<10} {result['end_page']:<10} "
                   f"{result['file_count']:<10} {status_display:<15} "
                   f"{result['duration']:<12} {process_time:<20}\n")
    except Exception as e:
        print(f"追加日志记录失败: {str(e)}")


def finalize_log_file(log_path, results, start_time):
    """
    完成日志文件，添加统计信息
    :param log_path: 日志文件路径
    :param results: 处理结果列表
    :param start_time: 开始时间
    """
    try:
        success_count = sum(1 for r in results if r['status'] == '成功')
        fail_count = len(results) - success_count
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() / 60
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write("-" * 120 + "\n")
            f.write(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总耗时: {total_duration:.2f}分钟\n")
            f.write(f"总计处理: {len(results)} 个项目\n")
            f.write(f"成功: {success_count} 个\n")
            f.write(f"失败: {fail_count} 个\n")
            f.write("=" * 120 + "\n")
        print(f"日志文件已完成: {log_path}")
    except Exception as e:
        print(f"完成日志文件失败: {str(e)}")


def get_sorted_jpg_files(directory):
    """
    获取目录下排序后的JPG文件列表（只处理jpg文件）
    :param directory: 目录路径
    :return: 排序后的JPG文件路径列表
    """
    jpg_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.jpg', '.jpeg')):
            jpg_files.append(os.path.join(directory, filename))
    
    # 按文件名排序
    jpg_files.sort()
    return jpg_files


def normalize_filename(filename):
    """
    去除文件名前面的零，用于页码匹配
    例如：'00001.jpg' -> '1.jpg'
    :param filename: 原始文件名
    :return: 去除前导零后的文件名
    """
    name, ext = os.path.splitext(filename)
    # 去除前导零
    normalized_name = name.lstrip('0') or '0'  # 如果全是0，保留一个0
    return normalized_name + ext


def get_page_number_from_filename(filename):
    """
    从文件名中提取页码（去除前导零后的数字）
    支持带"-"分隔符的文件名，以分隔符后的部分为主
    例如：'00001.jpg' -> 1, '00010.jpg' -> 10
          '001-00005.jpg' -> 5, 'cover-00010.jpg' -> 10
    :param filename: 文件名
    :return: 页码数字
    """
    name, ext = os.path.splitext(os.path.basename(filename))
    
    # 如果文件名包含"-"分隔符，使用分隔符后的部分
    if '-' in name:
        # 取最后一个"-"之后的部分
        name = name.split('-')[-1]
    
    # 去除前导零
    normalized_name = name.lstrip('0') or '0'
    try:
        return int(normalized_name)
    except ValueError:
        return None


def validate_page_ranges(source_dir, projects_list):
    """
    验证所有项目的页码范围是否都能找到对应的文件
    :param source_dir: 源目录
    :param projects_list: 项目列表
    :return: (是否有效, 错误信息列表)
    """
    if not os.path.isdir(source_dir):
        return False, [f"源目录不存在: {source_dir}"]
    
    # 获取所有JPG文件并创建页码映射
    all_files = get_sorted_jpg_files(source_dir)
    if not all_files:
        return False, [f"在目录 {source_dir} 中未找到JPG文件"]
    
    page_to_file = {}
    for file_path in all_files:
        page_num = get_page_number_from_filename(file_path)
        if page_num is not None:
            page_to_file[page_num] = file_path
    
    max_page = max(page_to_file.keys()) if page_to_file else 0
    if max_page == 0:
        return False, [f"在目录 {source_dir} 中未找到有效的页码文件（文件名应为数字.jpg格式）"]
    
    # 验证每个项目的页码范围
    errors = []
    for project_info in projects_list:
        project_name = project_info['project']
        start_page = int(project_info['start_page'])
        end_page = int(project_info['end_page'])
        index = project_info.get('index', '')
        
        # 显示名称（自建目录用序号，民事案件用项目名称）
        display_name = f"{index}_{project_name}" if index else project_name
        
        # 检查起始页和终止页是否在范围内
        if start_page < 1:
            errors.append(f"'{display_name}': 起始页({start_page})必须为正整数")
            continue
        
        if end_page > max_page:
            errors.append(f"'{display_name}': 终止页({end_page})超出最大页码({max_page})")
            continue
        
        if start_page > end_page:
            errors.append(f"'{display_name}': 起始页({start_page})大于终止页({end_page})")
            continue
        
        # 检查该范围内是否所有页码都有对应文件
        missing_pages = []
        for page_num in range(start_page, end_page + 1):
            if page_num not in page_to_file:
                missing_pages.append(str(page_num))
        
        if missing_pages:
            if len(missing_pages) <= 5:
                # 如果缺失的页码不多，列出具体页码
                errors.append(f"'{display_name}': 页码范围[{start_page}-{end_page}]中缺少文件: {', '.join(missing_pages)}")
            else:
                # 如果缺失的页码较多，只显示数量
                errors.append(f"'{display_name}': 页码范围[{start_page}-{end_page}]中缺少{len(missing_pages)}个文件")
    
    return len(errors) == 0, errors


def copy_files_by_range(source_dir, target_dir, start_page, end_page):
    """
    根据页码范围复制文件（支持文件名前导零）
    :param source_dir: 源目录
    :param target_dir: 目标目录
    :param start_page: 起始页（从1开始）
    :param end_page: 终止页
    :return: 复制的文件数量
    """
    # 获取所有JPG文件并排序
    all_files = get_sorted_jpg_files(source_dir)
    
    if not all_files:
        raise ValueError(f"在目录 {source_dir} 中未找到JPG文件")
    
    # 创建页码到文件路径的映射（使用去零后的页码作为键）
    page_to_file = {}
    for file_path in all_files:
        page_num = get_page_number_from_filename(file_path)
        if page_num is not None:
            page_to_file[page_num] = file_path
    
    # 验证页码范围
    if start_page < 1:
        raise ValueError(f"起始页必须大于等于1，当前值: {start_page}")
    
    # 检查是否有足够的文件
    max_page = max(page_to_file.keys()) if page_to_file else 0
    if max_page == 0:
        raise ValueError(f"在目录 {source_dir} 中未找到有效的页码文件（文件名应为数字.jpg格式）")
    
    if end_page > max_page:
        raise ValueError(f"终止页({end_page})超出最大页码({max_page})，目录中共有{len(all_files)}个JPG文件")
    
    if start_page > end_page:
        raise ValueError(f"起始页({start_page})不能大于终止页({end_page})")
    
    # 创建目标目录
    os.makedirs(target_dir, exist_ok=True)
    
    # 复制指定范围的文件（保留原文件名）
    copied_count = 0
    for page_num in range(start_page, end_page + 1):
        if page_num in page_to_file:
            src_file = page_to_file[page_num]
            filename = os.path.basename(src_file)  # 保留原文件名（包含前导零）
            dst_file = os.path.join(target_dir, filename)
            shutil.copy2(src_file, dst_file)  # 保留元数据
            copied_count += 1
        else:
            print(f"警告: 页码 {page_num} 对应的文件不存在，已跳过")
    
    if copied_count == 0:
        raise ValueError(f"在页码范围 [{start_page}-{end_page}] 内未找到任何文件")
    
    return copied_count


def generate_pdf_from_jpgs(jpg_dir, output_dir, project_name, resolution=100.0, index='', add_index_prefix=True):
    """
    将JPG文件生成为PDF
    :param jpg_dir: JPG文件目录
    :param output_dir: PDF输出目录
    :param project_name: 项目名称（用作PDF文件名）
    :param resolution: PDF显示DPI值
    :param index: 序号（可选，添加到PDF文件名前缀）
    :param add_index_prefix: 是否在PDF文件名前添加序号前缀
    :return: PDF文件路径和状态
    """
    # 获取JPG文件
    jpg_files = get_sorted_jpg_files(jpg_dir)
    
    if not jpg_files:
        raise ValueError(f"在目录 {jpg_dir} 中未找到JPG文件")
    
    # 构建PDF文件名
    # 如果add_index_prefix为True且index存在且非空，则使用 "{index}_{project_name}"；否则只使用 project_name
    if add_index_prefix and index and str(index).strip():
        pdf_filename = f"{index}_{project_name}"
    else:
        pdf_filename = project_name
    pdf_path = os.path.join(output_dir, pdf_filename + ".pdf")
    
    try:
        # 使用PIL将多个图像合并为一个PDF
        images = []
        for jpg_path in jpg_files:
            image = Image.open(jpg_path)
            # 转换为RGB模式（如果需要）
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            images.append(image)
        
        # 保存为PDF
        if images:
            first_image = images[0]
            if len(images) == 1:
                first_image.save(pdf_path, "PDF", resolution=resolution)
            else:
                first_image.save(pdf_path, "PDF", resolution=resolution, save_all=True, append_images=images[1:])
        
        print(f"已将{len(jpg_files)}个JPG文件合并为PDF: {pdf_path} (DPI: {resolution})")
        return pdf_path, "PDF生成成功"
    
    except Exception as e:
        print(f"PDF生成出错: {str(e)}")
        raise e


def process_single_project(source_dir, output_base_dir, project_info, resolution=100.0, use_index_only=False, add_index_to_pdf=True):
    """
    处理单个项目
    :param source_dir: 源目录
    :param output_base_dir: 输出基础目录（分件完成目录）
    :param project_info: 项目信息字典 {'project': 项目名, 'start_page': 起始页, 'end_page': 终止页, 'index': 序号}
    :param resolution: PDF DPI
    :param use_index_only: 是否只使用序号作为文件名（自建目录模式）
    :param add_index_to_pdf: 是否在PDF文件名前添加序号前缀
    :return: 处理结果字典
    """
    project_name = project_info['project']
    start_page = int(project_info['start_page'])
    end_page = int(project_info['end_page'])
    index = project_info.get('index', '')
    
    start_time = time.time()
    result = {
        'project': project_name,
        'start_page': start_page,
        'end_page': end_page,
        'file_count': 0,
        'status': '失败',
        'duration': 0,
        'error_detail': ''  # 新增：详细错误信息
    }
    
    try:
        # 创建项目文件夹（序号作为前缀）
        if index:
            folder_name = f"{index}_{project_name}"
        else:
            folder_name = project_name
        project_dir = os.path.join(output_base_dir, folder_name)
        
        # 复制文件
        copied_count = copy_files_by_range(source_dir, project_dir, start_page, end_page)
        result['file_count'] = copied_count
        
        # 生成PDF（根据模式决定是否使用序号前缀）
        if use_index_only:
            # 自建目录模式：文件名只用序号
            pdf_path, ocr_status = generate_pdf_from_jpgs(project_dir, output_base_dir, index, resolution, '', False)
        else:
            # 民事案件目录模式：根据用户选择决定是否添加序号前缀
            pdf_path, ocr_status = generate_pdf_from_jpgs(project_dir, output_base_dir, project_name, resolution, index, add_index_to_pdf)
        
        result['status'] = '成功'
        result['duration'] = round(time.time() - start_time, 2)
        
        print(f"项目 '{project_name}' 处理成功: 复制了{copied_count}个文件，生成PDF: {pdf_path}")
        
    except Exception as e:
        error_msg = str(e)
        result['status'] = f"失败"
        result['error_detail'] = error_msg  # 记录详细错误信息
        result['duration'] = round(time.time() - start_time, 2)
        print(f"项目 '{project_name}' 处理失败: {error_msg}")
    
    return result


def process_all_projects(source_dir, projects_list, output_base_dir=None, resolution=100.0, progress_callback=None, result_callback=None, use_index_only=False, add_index_to_pdf=True):
    """
    处理所有项目
    :param source_dir: 源目录
    :param projects_list: 项目列表 [{'project': 项目名, 'start_page': 起始页, 'end_page': 终止页}, ...]
    :param output_base_dir: 输出基础目录，默认为源目录下的“分件完成”
    :param resolution: PDF DPI
    :param progress_callback: 进度回调函数
    :param result_callback: 结果回调函数
    :param use_index_only: 是否只使用序号作为文件名（自建目录模式）
    :param add_index_to_pdf: 是否在PDF文件名前添加序号前缀
    """
    if not os.path.isdir(source_dir):
        error_msg = f"错误：{source_dir} 不是一个有效的目录"
        if result_callback:
            result_callback(error_msg)
        else:
            print(error_msg)
        return
    
    if not projects_list:
        error_msg = "错误：项目列表为空"
        if result_callback:
            result_callback(error_msg)
        else:
            print(error_msg)
        return
    
    # 设置输出目录
    if output_base_dir is None:
        output_base_dir = os.path.join(source_dir, "分件完成")
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    msg = f"找到 {len(projects_list)} 个项目，开始处理..."
    if result_callback:
        result_callback(msg)
    else:
        print(msg)
    
    # 记录开始时间
    start_time = datetime.now()
    
    # 创建日志文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"split_processing_log_{timestamp}.txt"
    log_path = os.path.join(output_base_dir, log_filename)
    init_log_file(log_path, start_time)
    
    # 处理结果列表
    results_list = []
    
    # 逐个处理项目
    total_count = len(projects_list)
    completed = 0
    
    for project_info in projects_list:
        completed += 1
        project_name = project_info['project']
        
        # 更新进度
        if progress_callback:
            progress_callback(completed, total_count, f"正在处理: {project_name} ({completed}/{total_count})")
        
        # 处理单个项目
        result = process_single_project(source_dir, output_base_dir, project_info, resolution, use_index_only, add_index_to_pdf)
        results_list.append(result)
        
        # 实时记录日志
        append_to_log(log_path, result)
        
        # 显示结果
        if result_callback:
            # 如果有错误详情，显示详细信息
            error_info = result.get('error_detail', '')
            if error_info:
                status_msg = f"{project_name}: {result['status']} - PDF转换失败: {error_info} ({result['duration']}秒)"
            else:
                status_msg = f"{project_name}: {result['status']} - {result['file_count']}个文件 ({result['duration']}秒)"
            result_callback(status_msg)
        else:
            error_info = result.get('error_detail', '')
            if error_info:
                print(f"{project_name}: {result['status']} - PDF转换失败: {error_info} ({result['duration']}秒)")
            else:
                print(f"{project_name}: {result['status']} - {result['file_count']}个文件 ({result['duration']}秒)")
    
    # 完成日志文件
    finalize_log_file(log_path, results_list, start_time)
    
    # 计算成功率
    success_count = sum(1 for r in results_list if r['status'] == '成功')
    fail_count = len(results_list) - success_count
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    
    rate_msg = f"处理完成！共处理 {total_count} 个项目，成功 {success_count} 个，失败 {fail_count} 个，成功率 {success_rate:.1f}%。"
    
    # 如果有失败的项目，单独列出
    if fail_count > 0:
        failed_projects = [r for r in results_list if r['status'] != '成功']
        fail_summary = f"\n\n以下 {fail_count} 个项目PDF转换失败:\n"
        fail_summary += "-" * 80 + "\n"
        for idx, fail_result in enumerate(failed_projects, 1):
            error_info = fail_result.get('error_detail', '未知错误')
            fail_summary += f"{idx}. {fail_result['project']} (页码:{fail_result['start_page']}-{fail_result['end_page']})\n"
            fail_summary += f"   错误原因: {error_info}\n\n"
        rate_msg += fail_summary
    
    if result_callback:
        result_callback(rate_msg)
        result_callback(results_list)
        result_callback(f"日志文件已保存至: {log_path}")
        result_callback(f"输出目录: {output_base_dir}")
    else:
        print(rate_msg)
        print(f"日志文件已保存至: {log_path}")
        print(f"输出目录: {output_base_dir}")


class SplitProcessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("分件处理工具")
        self.root.geometry("1000x800")
        
        # 存储路径和配置
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.pdf_dpi = tk.IntVar(value=300)  # 默认 300 DPI
        self.add_index_prefix = tk.BooleanVar(value=True)  # 默认选中：在PDF文件名前增加序号
        
        # 设置GUI
        self.setup_gui()
        
    def setup_gui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 配置Treeview样式 - 显示网格线
        style = ttk.Style()
        style.configure('Custom.Treeview', background='white', fieldbackground='white', rowheight=25)
        style.configure('Civil.Treeview', background='white', fieldbackground='white', rowheight=25)
        style.map('Custom.Treeview', background=[('selected', '#0078d7')], foreground=[('selected', 'white')])
        style.map('Civil.Treeview', background=[('selected', '#0078d7')], foreground=[('selected', 'white')])
        
        # 标题
        title_label = ttk.Label(main_frame, text="分件处理工具", font=("微软雅黑", 16))
        title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20))
        
        # 说明标签（动态更新）
        self.note_label = ttk.Label(main_frame, 
                              text="说明：项目列表为固定项，只需填写起始页和终止页即可。留空则跳过该项目。",
                              foreground="blue", font=("微软雅黑", 9))
        self.note_label.grid(row=1, column=0, columnspan=4, pady=(0, 10), sticky=tk.W)
        
        # 源目录选择
        ttk.Label(main_frame, text="源目录:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Entry(main_frame, textvariable=self.source_dir, width=50).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, columnspan=2)
        ttk.Button(main_frame, text="浏览", command=self.browse_source_dir).grid(row=2, column=3, padx=(10, 0), pady=5)
        
        # 输出目录选择
        ttk.Label(main_frame, text="输出目录:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, columnspan=2)
        ttk.Button(main_frame, text="浏览", command=self.browse_output_dir).grid(row=3, column=3, padx=(10, 0), pady=5)
        
        # PDF DPI 设置
        ttk.Label(main_frame, text="PDF DPI:").grid(row=4, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        dpi_spinbox = ttk.Spinbox(main_frame, from_=72, to=1200, textvariable=self.pdf_dpi, width=15)
        dpi_spinbox.grid(row=4, column=1, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="(默认 300)").grid(row=4, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # PDF文件名前增加序号单选框
        index_checkbox = ttk.Checkbutton(main_frame, text="PDF文件名前增加序号", variable=self.add_index_prefix)
        index_checkbox.grid(row=4, column=3, sticky=tk.E, padx=(20, 0), pady=5)
        
        # 创建Tab控件
        tab_control = ttk.Notebook(main_frame)
        tab_control.grid(row=5, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 第一个Tab：自建目录
        self.custom_tab = ttk.Frame(tab_control)
        tab_control.add(self.custom_tab, text='自建目录')
        
        # 第二个Tab：民事案件目录
        self.civil_tab = ttk.Frame(tab_control)
        tab_control.add(self.civil_tab, text='民事案件目录')
        
        # 第三个Tab：执行案件目录
        self.criminal_tab = ttk.Frame(tab_control)
        tab_control.add(self.criminal_tab, text='执行案件目录')
        
        # 第四个Tab：执保案件目录
        self.preservation_tab = ttk.Frame(tab_control)
        tab_control.add(self.preservation_tab, text='执保案件目录')
        
        # 第五个Tab：执恢案件目录
        self.restoration_tab = ttk.Frame(tab_control)
        tab_control.add(self.restoration_tab, text='执恢案件目录')
        
        # 第六个Tab：刑事卷目录
        self.criminal_case_tab = ttk.Frame(tab_control)
        tab_control.add(self.criminal_case_tab, text='刑事卷目录')
        
        # 第七个Tab：副卷目录
        self.supplementary_tab = ttk.Frame(tab_control)
        tab_control.add(self.supplementary_tab, text='副卷目录')
        
        # 初始化七个Tab的内容
        self.setup_custom_tab()
        self.setup_civil_tab()
        self.setup_criminal_tab()
        self.setup_preservation_tab()
        self.setup_restoration_tab()
        self.setup_criminal_case_tab()
        self.setup_supplementary_tab()
        
        # 绑定Tab切换事件
        tab_control.bind('<<NotebookTabChanged>>', self.on_tab_changed)
        
        # 处理按钮
        self.process_button = ttk.Button(main_frame, text="开始处理", command=self.start_processing)
        self.process_button.grid(row=6, column=0, columnspan=4, pady=20)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=600, mode='determinate')
        self.progress.grid(row=7, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E))
        
        # 进度标签
        self.progress_label = ttk.Label(main_frame, text="")
        self.progress_label.grid(row=8, column=0, columnspan=4, pady=5)
        
        # 结果显示文本框
        self.result_text = tk.Text(main_frame, height=10, width=80)
        result_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_text.grid(row=9, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_scrollbar.grid(row=9, column=4, pady=10, sticky=(tk.N, tk.S))
        
        # 配置行权重以便于拉伸
        main_frame.rowconfigure(9, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # 当前激活的Tab（默认为民事案件目录）
        self.current_tab = 'civil'
    
    def setup_preservation_tab(self):
        """设置执保案件目录Tab"""
        # 创建框架
        preservation_frame = ttk.Frame(self.preservation_tab, padding="10")
        preservation_frame.pack(fill=tk.BOTH, expand=True)
        preservation_frame.columnconfigure(0, weight=1)
        preservation_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview表格（隐藏序号列）
        columns = ('index', 'project', 'start_page', 'end_page')
        self.preservation_tree = ttk.Treeview(preservation_frame, columns=columns, show='headings', height=15)
        
        # 定义列标题
        self.preservation_tree.heading('index', text='序号')
        self.preservation_tree.heading('project', text='项目名称')
        self.preservation_tree.heading('start_page', text='起始页')
        self.preservation_tree.heading('end_page', text='终止页')
        
        # 定义列宽度（序号列宽度为0，隐藏显示）
        self.preservation_tree.column('index', width=0, minwidth=0)  # 隐藏序号列
        self.preservation_tree.column('project', width=450)
        self.preservation_tree.column('start_page', width=100)
        self.preservation_tree.column('end_page', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(preservation_frame, orient=tk.VERTICAL, command=self.preservation_tree.yview)
        self.preservation_tree.configure(yscrollcommand=scrollbar.set)
        
        self.preservation_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始化固定项目列表
        self.init_preservation_projects()
        
        # 提示标签
        hint_label = ttk.Label(preservation_frame, 
                              text="提示：双击单元格可编辑起始页和终止页，留空表示跳过该项目",
                              foreground="gray", font=("微软雅黑", 8))
        hint_label.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 配置样式 - 显示网格线（通过背景色和边框实现）
        self.preservation_tree.configure(style='Civil.Treeview')
        # 为Treeview添加边框以模拟网格效果
        self.preservation_tree.tag_configure('odd', background='#f0f0f0')
        self.preservation_tree.tag_configure('even', background='white')
        # 为每行交替设置tag
        for i, item in enumerate(self.preservation_tree.get_children()):
            tag = 'odd' if i % 2 == 0 else 'even'
            self.preservation_tree.item(item, tags=(tag,))
        
        # 绑定右键菜单
        self.preservation_tree.bind('<Button-3>', self.on_preservation_right_click)
        self.preservation_tree.bind('<Button-2>', self.on_preservation_right_click)  # Mac系统
    
    def setup_restoration_tab(self):
        """设置执恢案件目录Tab"""
        # 创建框架
        restoration_frame = ttk.Frame(self.restoration_tab, padding="10")
        restoration_frame.pack(fill=tk.BOTH, expand=True)
        restoration_frame.columnconfigure(0, weight=1)
        restoration_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview表格（隐藏序号列）
        columns = ('index', 'project', 'start_page', 'end_page')
        self.restoration_tree = ttk.Treeview(restoration_frame, columns=columns, show='headings', height=15)
        
        # 定义列标题
        self.restoration_tree.heading('index', text='序号')
        self.restoration_tree.heading('project', text='项目名称')
        self.restoration_tree.heading('start_page', text='起始页')
        self.restoration_tree.heading('end_page', text='终止页')
        
        # 定义列宽度（序号列宽度为0，隐藏显示）
        self.restoration_tree.column('index', width=0, minwidth=0)  # 隐藏序号列
        self.restoration_tree.column('project', width=450)
        self.restoration_tree.column('start_page', width=100)
        self.restoration_tree.column('end_page', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(restoration_frame, orient=tk.VERTICAL, command=self.restoration_tree.yview)
        self.restoration_tree.configure(yscrollcommand=scrollbar.set)
        
        self.restoration_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始化固定项目列表
        self.init_restoration_projects()
        
        # 提示标签
        hint_label = ttk.Label(restoration_frame, 
                              text="提示：双击单元格可编辑起始页和终止页，留空表示跳过该项目",
                              foreground="gray", font=("微软雅黑", 8))
        hint_label.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 配置样式 - 显示网格线（通过背景色和边框实现）
        self.restoration_tree.configure(style='Civil.Treeview')
        # 为Treeview添加边框以模拟网格效果
        self.restoration_tree.tag_configure('odd', background='#f0f0f0')
        self.restoration_tree.tag_configure('even', background='white')
        # 为每行交替设置tag
        for i, item in enumerate(self.restoration_tree.get_children()):
            tag = 'odd' if i % 2 == 0 else 'even'
            self.restoration_tree.item(item, tags=(tag,))
        
        # 绑定右键菜单
        self.restoration_tree.bind('<Button-3>', self.on_restoration_right_click)
        self.restoration_tree.bind('<Button-2>', self.on_restoration_right_click)  # Mac系统
    
    def setup_criminal_case_tab(self):
        """设置刑事卷目录Tab"""
        # 创建框架
        criminal_case_frame = ttk.Frame(self.criminal_case_tab, padding="10")
        criminal_case_frame.pack(fill=tk.BOTH, expand=True)
        criminal_case_frame.columnconfigure(0, weight=1)
        criminal_case_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview表格（隐藏序号列）
        columns = ('index', 'project', 'start_page', 'end_page')
        self.criminal_case_tree = ttk.Treeview(criminal_case_frame, columns=columns, show='headings', height=15)
        
        # 定义列标题
        self.criminal_case_tree.heading('index', text='序号')
        self.criminal_case_tree.heading('project', text='项目名称')
        self.criminal_case_tree.heading('start_page', text='起始页')
        self.criminal_case_tree.heading('end_page', text='终止页')
        
        # 定义列宽度（序号列宽度为0，隐藏显示）
        self.criminal_case_tree.column('index', width=0, minwidth=0)  # 隐藏序号列
        self.criminal_case_tree.column('project', width=450)
        self.criminal_case_tree.column('start_page', width=100)
        self.criminal_case_tree.column('end_page', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(criminal_case_frame, orient=tk.VERTICAL, command=self.criminal_case_tree.yview)
        self.criminal_case_tree.configure(yscrollcommand=scrollbar.set)
        
        self.criminal_case_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始化固定项目列表
        self.init_criminal_case_projects()
        
        # 提示标签
        hint_label = ttk.Label(criminal_case_frame, 
                              text="提示：双击单元格可编辑起始页和终止页，留空表示跳过该项目",
                              foreground="gray", font=("微软雅黑", 8))
        hint_label.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 配置样式 - 显示网格线（通过背景色和边框实现）
        self.criminal_case_tree.configure(style='Civil.Treeview')
        # 为Treeview添加边框以模拟网格效果
        self.criminal_case_tree.tag_configure('odd', background='#f0f0f0')
        self.criminal_case_tree.tag_configure('even', background='white')
        # 为每行交替设置tag
        for i, item in enumerate(self.criminal_case_tree.get_children()):
            tag = 'odd' if i % 2 == 0 else 'even'
            self.criminal_case_tree.item(item, tags=(tag,))
        
        # 绑定右键菜单
        self.criminal_case_tree.bind('<Button-3>', self.on_criminal_case_right_click)
        self.criminal_case_tree.bind('<Button-2>', self.on_criminal_case_right_click)  # Mac系统
    
    def init_criminal_case_projects(self):
        """初始化刑事卷目录（固定项目列表）"""
        for idx, project_name in enumerate(CRIMINAL_CASE_PROJECTS, start=1):
            # 存储格式：(序号, 项目名称, 起始页, 终止页)
            self.criminal_case_tree.insert('', 'end', values=(str(idx), project_name, '', ''))
        
        # 启用就地编辑功能
        self.criminal_case_tree.bind('<Double-1>', self.on_criminal_case_double_click)
    
    def on_criminal_case_double_click(self, event):
        """处理刑事卷目录Tab的双击事件"""
        region = self.criminal_case_tree.identify_region(event.x, event.y)
        
        if region != "cell":
            return
        
        column = self.criminal_case_tree.identify_column(event.x)
        item = self.criminal_case_tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # 获取当前行的序号
        current_values = self.criminal_case_tree.item(item)['values']
        index = str(current_values[0]) if len(current_values) > 0 and current_values[0] else ''
        
        # 判断是否为新增行（包含"-"）
        is_new_row = '-' in index
        
        col_index = int(column.replace('#', '')) - 1
        
        # 如果是新增行，允许编辑第2列（项目名）、第3列（起始页）和第4列（终止页）
        # 如果是初始行，只允许编辑第3列（起始页）和第4列（终止页）
        if is_new_row:
            if col_index not in [1, 2, 3]:  # 1=项目名, 2=起始页, 3=终止页
                return
        else:
            if col_index not in [2, 3]:  # 2=起始页, 3=终止页
                return
        
        current_value = str(current_values[col_index]) if current_values[col_index] else ''
        
        x, y, width, height = self.criminal_case_tree.bbox(item, column)
        
        entry = ttk.Entry(self.criminal_case_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        def save_edit(event=None):
            new_value = entry.get().strip()
            
            # 如果编辑的是起始页或终止页，需要验证为整数
            if col_index in [2, 3] and new_value:
                try:
                    page_num = int(new_value)
                    if page_num < 1:
                        messagebox.showerror("错误", "页码必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "页码必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            values = list(self.criminal_case_tree.item(item)['values'])
            values[col_index] = new_value if new_value else ''
            self.criminal_case_tree.item(item, values=values)
            entry.destroy()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', lambda e: self.root.after(100, save_edit))
    
    def setup_supplementary_tab(self):
        """设置副卷目录Tab"""
        # 创建框架
        supplementary_frame = ttk.Frame(self.supplementary_tab, padding="10")
        supplementary_frame.pack(fill=tk.BOTH, expand=True)
        supplementary_frame.columnconfigure(0, weight=1)
        supplementary_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview表格（隐藏序号列）
        columns = ('index', 'project', 'start_page', 'end_page')
        self.supplementary_tree = ttk.Treeview(supplementary_frame, columns=columns, show='headings', height=15)
        
        # 定义列标题
        self.supplementary_tree.heading('index', text='序号')
        self.supplementary_tree.heading('project', text='项目名称')
        self.supplementary_tree.heading('start_page', text='起始页')
        self.supplementary_tree.heading('end_page', text='终止页')
        
        # 定义列宽度（序号列宽度为0，隐藏显示）
        self.supplementary_tree.column('index', width=0, minwidth=0)  # 隐藏序号列
        self.supplementary_tree.column('project', width=450)
        self.supplementary_tree.column('start_page', width=100)
        self.supplementary_tree.column('end_page', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(supplementary_frame, orient=tk.VERTICAL, command=self.supplementary_tree.yview)
        self.supplementary_tree.configure(yscrollcommand=scrollbar.set)
        
        self.supplementary_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始化固定项目列表
        self.init_supplementary_projects()
        
        # 提示标签
        hint_label = ttk.Label(supplementary_frame, 
                              text="提示：双击单元格可编辑起始页和终止页，留空表示跳过该项目",
                              foreground="gray", font=("微软雅黑", 8))
        hint_label.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 配置样式 - 显示网格线（通过背景色和边框实现）
        self.supplementary_tree.configure(style='Civil.Treeview')
        # 为Treeview添加边框以模拟网格效果
        self.supplementary_tree.tag_configure('odd', background='#f0f0f0')
        self.supplementary_tree.tag_configure('even', background='white')
        # 为每行交替设置tag
        for i, item in enumerate(self.supplementary_tree.get_children()):
            tag = 'odd' if i % 2 == 0 else 'even'
            self.supplementary_tree.item(item, tags=(tag,))
        
        # 绑定右键菜单
        self.supplementary_tree.bind('<Button-3>', self.on_supplementary_right_click)
        self.supplementary_tree.bind('<Button-2>', self.on_supplementary_right_click)  # Mac系统
    
    def init_supplementary_projects(self):
        """初始化副卷目录（固定项目列表）"""
        for idx, project_name in enumerate(SUPPLEMENTARY_PROJECTS, start=1):
            # 存储格式：(序号, 项目名称, 起始页, 终止页)
            self.supplementary_tree.insert('', 'end', values=(str(idx), project_name, '', ''))
        
        # 启用就地编辑功能
        self.supplementary_tree.bind('<Double-1>', self.on_supplementary_double_click)
    
    def on_supplementary_double_click(self, event):
        """处理副卷目录Tab的双击事件"""
        region = self.supplementary_tree.identify_region(event.x, event.y)
        
        if region != "cell":
            return
        
        column = self.supplementary_tree.identify_column(event.x)
        item = self.supplementary_tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # 获取当前行的序号
        current_values = self.supplementary_tree.item(item)['values']
        index = str(current_values[0]) if len(current_values) > 0 and current_values[0] else ''
        
        # 判断是否为新增行（包含"-"）
        is_new_row = '-' in index
        
        col_index = int(column.replace('#', '')) - 1
        
        # 如果是新增行，允许编辑第2列（项目名）、第3列（起始页）和第4列（终止页）
        # 如果是初始行，只允许编辑第3列（起始页）和第4列（终止页）
        if is_new_row:
            if col_index not in [1, 2, 3]:  # 1=项目名, 2=起始页, 3=终止页
                return
        else:
            if col_index not in [2, 3]:  # 2=起始页, 3=终止页
                return
        
        current_value = str(current_values[col_index]) if current_values[col_index] else ''
        
        x, y, width, height = self.supplementary_tree.bbox(item, column)
        
        entry = ttk.Entry(self.supplementary_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        def save_edit(event=None):
            new_value = entry.get().strip()
            
            # 如果编辑的是起始页或终止页，需要验证为整数
            if col_index in [2, 3] and new_value:
                try:
                    page_num = int(new_value)
                    if page_num < 1:
                        messagebox.showerror("错误", "页码必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "页码必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            values = list(self.supplementary_tree.item(item)['values'])
            values[col_index] = new_value if new_value else ''
            self.supplementary_tree.item(item, values=values)
            entry.destroy()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', lambda e: self.root.after(100, save_edit))
    
    def on_tab_changed(self, event):
        """Tab切换事件处理"""
        selected_tab = event.widget.select()
        tab_text = event.widget.tab(selected_tab, "text")
        
        if tab_text == '自建目录':
            self.current_tab = 'custom'
            self.note_label.config(text="说明：请填写起始页和终止页，留空则跳过该行。文件名仅使用序号。")
        elif tab_text == '民事案件目录':
            self.current_tab = 'civil'
            self.note_label.config(text="说明：项目列表为固定项，只需填写起始页和终止页即可。留空则跳过该项目。")
        elif tab_text == '执行案件目录':
            self.current_tab = 'criminal'
            self.note_label.config(text="说明：项目列表为固定项，只需填写起始页和终止页即可。留空则跳过该项目。")
        elif tab_text == '执保案件目录':
            self.current_tab = 'preservation'
            self.note_label.config(text="说明：项目列表为固定项，只需填写起始页和终止页即可。留空则跳过该项目。")
        elif tab_text == '执恢案件目录':
            self.current_tab = 'restoration'
            self.note_label.config(text="说明：项目列表为固定项，只需填写起始页和终止页即可。留空则跳过该项目。")
        elif tab_text == '刑事卷目录':
            self.current_tab = 'criminal_case'
            self.note_label.config(text="说明：项目列表为固定项，只需填写起始页和终止页即可。留空则跳过该项目。")
        elif tab_text == '副卷目录':
            self.current_tab = 'supplementary'
            self.note_label.config(text="说明：项目列表为固定项，只需填写起始页和终止页即可。留空则跳过该项目。")
    
    def setup_custom_tab(self):
        """设置自建目录Tab"""
        # 创建框架
        custom_frame = ttk.Frame(self.custom_tab, padding="10")
        custom_frame.pack(fill=tk.BOTH, expand=True)
        custom_frame.columnconfigure(0, weight=1)
        custom_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview表格（3列：序号、起始页、终止页）
        columns = ('index', 'start_page', 'end_page')
        self.custom_tree = ttk.Treeview(custom_frame, columns=columns, show='headings', height=30)
        
        # 定义列标题
        self.custom_tree.heading('index', text='序号')
        self.custom_tree.heading('start_page', text='起始页')
        self.custom_tree.heading('end_page', text='终止页')
        
        # 定义列宽度
        self.custom_tree.column('index', width=100, anchor=tk.CENTER)
        self.custom_tree.column('start_page', width=150, anchor=tk.CENTER)
        self.custom_tree.column('end_page', width=150, anchor=tk.CENTER)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(custom_frame, orient=tk.VERTICAL, command=self.custom_tree.yview)
        self.custom_tree.configure(yscrollcommand=scrollbar.set)
        
        self.custom_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始化30行数据
        for i in range(1, 31):
            self.custom_tree.insert('', 'end', values=(str(i), '', ''))
        
        # 启用就地编辑功能
        self.custom_tree.bind('<Double-1>', self.on_custom_double_click)
        
        # 绑定右键菜单
        self.custom_tree.bind('<Button-3>', self.on_custom_right_click)
        self.custom_tree.bind('<Button-2>', self.on_custom_right_click)  # Mac系统
        
        # 提示标签
        hint_label = ttk.Label(custom_frame, 
                              text="提示：双击单元格可编辑起始页和终止页，留空表示跳过该行；右键点击可增加/删除行",
                              foreground="gray", font=("微软雅黑", 8))
        hint_label.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 配置样式 - 显示网格线（通过背景色和边框实现）
        self.custom_tree.configure(style='Custom.Treeview')
        # 为Treeview添加边框以模拟网格效果
        self.custom_tree.tag_configure('odd', background='#f0f0f0')
        self.custom_tree.tag_configure('even', background='white')
        # 为每行交替设置tag
        for i, item in enumerate(self.custom_tree.get_children()):
            tag = 'odd' if i % 2 == 0 else 'even'
            self.custom_tree.item(item, tags=(tag,))
    
    def setup_civil_tab(self):
        """设置民事案件目录Tab"""
        # 创建框架
        civil_frame = ttk.Frame(self.civil_tab, padding="10")
        civil_frame.pack(fill=tk.BOTH, expand=True)
        civil_frame.columnconfigure(0, weight=1)
        civil_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview表格（隐藏序号列）
        columns = ('index', 'project', 'start_page', 'end_page')
        self.civil_tree = ttk.Treeview(civil_frame, columns=columns, show='headings', height=15)
        
        # 定义列标题
        self.civil_tree.heading('index', text='序号')
        self.civil_tree.heading('project', text='项目名称')
        self.civil_tree.heading('start_page', text='起始页')
        self.civil_tree.heading('end_page', text='终止页')
        
        # 定义列宽度（序号列宽度为0，隐藏显示）
        self.civil_tree.column('index', width=0, minwidth=0)  # 隐藏序号列
        self.civil_tree.column('project', width=450)
        self.civil_tree.column('start_page', width=100)
        self.civil_tree.column('end_page', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(civil_frame, orient=tk.VERTICAL, command=self.civil_tree.yview)
        self.civil_tree.configure(yscrollcommand=scrollbar.set)
        
        self.civil_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始化固定项目列表
        self.init_civil_projects()
        
        # 提示标签
        hint_label = ttk.Label(civil_frame, 
                              text="提示：双击单元格可编辑起始页和终止页，留空表示跳过该项目",
                              foreground="gray", font=("微软雅黑", 8))
        hint_label.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 配置样式 - 显示网格线（通过背景色和边框实现）
        self.civil_tree.configure(style='Civil.Treeview')
        # 为Treeview添加边框以模拟网格效果
        self.civil_tree.tag_configure('odd', background='#f0f0f0')
        self.civil_tree.tag_configure('even', background='white')
        # 为每行交替设置tag
        for i, item in enumerate(self.civil_tree.get_children()):
            tag = 'odd' if i % 2 == 0 else 'even'
            self.civil_tree.item(item, tags=(tag,))
        
        # 绑定右键菜单
        self.civil_tree.bind('<Button-3>', self.on_civil_right_click)
        self.civil_tree.bind('<Button-2>', self.on_civil_right_click)  # Mac系统
    
    def setup_criminal_tab(self):
        """设置刑事案件目录Tab"""
        # 创建框架
        criminal_frame = ttk.Frame(self.criminal_tab, padding="10")
        criminal_frame.pack(fill=tk.BOTH, expand=True)
        criminal_frame.columnconfigure(0, weight=1)
        criminal_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview表格（隐藏序号列）
        columns = ('index', 'project', 'start_page', 'end_page')
        self.criminal_tree = ttk.Treeview(criminal_frame, columns=columns, show='headings', height=15)
        
        # 定义列标题
        self.criminal_tree.heading('index', text='序号')
        self.criminal_tree.heading('project', text='项目名称')
        self.criminal_tree.heading('start_page', text='起始页')
        self.criminal_tree.heading('end_page', text='终止页')
        
        # 定义列宽度（序号列宽度为0，隐藏显示）
        self.criminal_tree.column('index', width=0, minwidth=0)  # 隐藏序号列
        self.criminal_tree.column('project', width=450)
        self.criminal_tree.column('start_page', width=100)
        self.criminal_tree.column('end_page', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(criminal_frame, orient=tk.VERTICAL, command=self.criminal_tree.yview)
        self.criminal_tree.configure(yscrollcommand=scrollbar.set)
        
        self.criminal_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 初始化固定项目列表
        self.init_criminal_projects()
        
        # 提示标签
        hint_label = ttk.Label(criminal_frame, 
                              text="提示：双击单元格可编辑起始页和终止页，留空表示跳过该项目",
                              foreground="gray", font=("微软雅黑", 8))
        hint_label.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 配置样式 - 显示网格线（通过背景色和边框实现）
        self.criminal_tree.configure(style='Civil.Treeview')
        # 为Treeview添加边框以模拟网格效果
        self.criminal_tree.tag_configure('odd', background='#f0f0f0')
        self.criminal_tree.tag_configure('even', background='white')
        # 为每行交替设置tag
        for i, item in enumerate(self.criminal_tree.get_children()):
            tag = 'odd' if i % 2 == 0 else 'even'
            self.criminal_tree.item(item, tags=(tag,))
        
        # 绑定右键菜单
        self.criminal_tree.bind('<Button-3>', self.on_criminal_right_click)
        self.criminal_tree.bind('<Button-2>', self.on_criminal_right_click)  # Mac系统
        
    def init_civil_projects(self):
        """初始化民事案件目录（固定项目列表）"""
        for idx, project_name in enumerate(FIXED_PROJECTS, start=1):
            # 存储格式：(序号, 项目名称, 起始页, 终止页)
            self.civil_tree.insert('', 'end', values=(str(idx), project_name, '', ''))
        
        # 启用就地编辑功能
        self.civil_tree.bind('<Double-1>', self.on_civil_double_click)
    
    def init_criminal_projects(self):
        """初始化刑事案件目录（固定项目列表）"""
        for idx, project_name in enumerate(CRIMINAL_PROJECTS, start=1):
            # 存储格式：(序号, 项目名称, 起始页, 终止页)
            self.criminal_tree.insert('', 'end', values=(str(idx), project_name, '', ''))
        
        # 启用就地编辑功能
        self.criminal_tree.bind('<Double-1>', self.on_criminal_double_click)
    
    def init_preservation_projects(self):
        """初始化执保案件目录（固定项目列表）"""
        for idx, project_name in enumerate(PRESERVATION_PROJECTS, start=1):
            # 存储格式：(序号, 项目名称, 起始页, 终止页)
            self.preservation_tree.insert('', 'end', values=(str(idx), project_name, '', ''))
        
        # 启用就地编辑功能
        self.preservation_tree.bind('<Double-1>', self.on_preservation_double_click)
    
    def init_restoration_projects(self):
        """初始化执恢案件目录（固定项目列表）"""
        for idx, project_name in enumerate(RESTORATION_PROJECTS, start=1):
            # 存储格式：(序号, 项目名称, 起始页, 终止页)
            self.restoration_tree.insert('', 'end', values=(str(idx), project_name, '', ''))
        
        # 启用就地编辑功能
        self.restoration_tree.bind('<Double-1>', self.on_restoration_double_click)
    
    def on_custom_double_click(self, event):
        """处理自建目录Tab的双击事件"""
        region = self.custom_tree.identify_region(event.x, event.y)
        
        if region != "cell":
            return
        
        column = self.custom_tree.identify_column(event.x)
        item = self.custom_tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # 允许编辑所有3列：序号、起始页、终止页
        col_index = int(column.replace('#', '')) - 1
        if col_index not in [0, 1, 2]:  # 0=序号, 1=起始页, 2=终止页
            return
        
        current_values = self.custom_tree.item(item)['values']
        current_value = str(current_values[col_index]) if current_values[col_index] else ''
        
        x, y, width, height = self.custom_tree.bbox(item, column)
        
        entry = ttk.Entry(self.custom_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        def save_edit(event=None):
            new_value = entry.get().strip()
            
            # 如果编辑的是序号列，需要验证为正整数
            if col_index == 0 and new_value:
                try:
                    index_num = int(new_value)
                    if index_num < 1:
                        messagebox.showerror("错误", "序号必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "序号必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            # 如果编辑的是起始页或终止页，需要验证为整数
            if col_index in [1, 2] and new_value:
                try:
                    page_num = int(new_value)
                    if page_num < 1:
                        messagebox.showerror("错误", "页码必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "页码必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            values = list(self.custom_tree.item(item)['values'])
            values[col_index] = new_value if new_value else ''
            self.custom_tree.item(item, values=values)
            entry.destroy()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', lambda e: self.root.after(100, save_edit))
    
    def on_civil_double_click(self, event):
        """处理民事案件目录Tab的双击事件"""
        region = self.civil_tree.identify_region(event.x, event.y)
        
        if region != "cell":
            return
        
        column = self.civil_tree.identify_column(event.x)
        item = self.civil_tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # 获取当前行的序号
        current_values = self.civil_tree.item(item)['values']
        index = str(current_values[0]) if len(current_values) > 0 and current_values[0] else ''
        
        # 判断是否为新增行（包含"-"）
        is_new_row = '-' in index
        
        col_index = int(column.replace('#', '')) - 1
        
        # 如果是新增行，允许编辑第2列（项目名）、第3列（起始页）和第4列（终止页）
        # 如果是初始行，只允许编辑第3列（起始页）和第4列（终止页）
        if is_new_row:
            if col_index not in [1, 2, 3]:  # 1=项目名, 2=起始页, 3=终止页
                return
        else:
            if col_index not in [2, 3]:  # 2=起始页, 3=终止页
                return
        
        current_value = str(current_values[col_index]) if current_values[col_index] else ''
        
        x, y, width, height = self.civil_tree.bbox(item, column)
        
        entry = ttk.Entry(self.civil_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        def save_edit(event=None):
            new_value = entry.get().strip()
            
            # 如果编辑的是起始页或终止页，需要验证为整数
            if col_index in [2, 3] and new_value:
                try:
                    page_num = int(new_value)
                    if page_num < 1:
                        messagebox.showerror("错误", "页码必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "页码必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            values = list(self.civil_tree.item(item)['values'])
            values[col_index] = new_value if new_value else ''
            self.civil_tree.item(item, values=values)
            entry.destroy()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', lambda e: self.root.after(100, save_edit))
    
    def on_criminal_double_click(self, event):
        """处理刑事案件目录Tab的双击事件"""
        region = self.criminal_tree.identify_region(event.x, event.y)
        
        if region != "cell":
            return
        
        column = self.criminal_tree.identify_column(event.x)
        item = self.criminal_tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # 获取当前行的序号
        current_values = self.criminal_tree.item(item)['values']
        index = str(current_values[0]) if len(current_values) > 0 and current_values[0] else ''
        
        # 判断是否为新增行（包含"-"）
        is_new_row = '-' in index
        
        col_index = int(column.replace('#', '')) - 1
        
        # 如果是新增行，允许编辑第2列（项目名）、第3列（起始页）和第4列（终止页）
        # 如果是初始行，只允许编辑第3列（起始页）和第4列（终止页）
        if is_new_row:
            if col_index not in [1, 2, 3]:  # 1=项目名, 2=起始页, 3=终止页
                return
        else:
            if col_index not in [2, 3]:  # 2=起始页, 3=终止页
                return
        
        current_value = str(current_values[col_index]) if current_values[col_index] else ''
        
        x, y, width, height = self.criminal_tree.bbox(item, column)
        
        entry = ttk.Entry(self.criminal_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        def save_edit(event=None):
            new_value = entry.get().strip()
            
            # 如果编辑的是起始页或终止页，需要验证为整数
            if col_index in [2, 3] and new_value:
                try:
                    page_num = int(new_value)
                    if page_num < 1:
                        messagebox.showerror("错误", "页码必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "页码必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            values = list(self.criminal_tree.item(item)['values'])
            values[col_index] = new_value if new_value else ''
            self.criminal_tree.item(item, values=values)
            entry.destroy()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', lambda e: self.root.after(100, save_edit))
    
    def on_preservation_double_click(self, event):
        """处理执保案件目录Tab的双击事件"""
        region = self.preservation_tree.identify_region(event.x, event.y)
        
        if region != "cell":
            return
        
        column = self.preservation_tree.identify_column(event.x)
        item = self.preservation_tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # 获取当前行的序号
        current_values = self.preservation_tree.item(item)['values']
        index = str(current_values[0]) if len(current_values) > 0 and current_values[0] else ''
        
        # 判断是否为新增行（包含"-"）
        is_new_row = '-' in index
        
        col_index = int(column.replace('#', '')) - 1
        
        # 如果是新增行，允许编辑第2列（项目名）、第3列（起始页）和第4列（终止页）
        # 如果是初始行，只允许编辑第3列（起始页）和第4列（终止页）
        if is_new_row:
            if col_index not in [1, 2, 3]:  # 1=项目名, 2=起始页, 3=终止页
                return
        else:
            if col_index not in [2, 3]:  # 2=起始页, 3=终止页
                return
        
        current_value = str(current_values[col_index]) if current_values[col_index] else ''
        
        x, y, width, height = self.preservation_tree.bbox(item, column)
        
        entry = ttk.Entry(self.preservation_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        def save_edit(event=None):
            new_value = entry.get().strip()
            
            # 如果编辑的是起始页或终止页，需要验证为整数
            if col_index in [2, 3] and new_value:
                try:
                    page_num = int(new_value)
                    if page_num < 1:
                        messagebox.showerror("错误", "页码必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "页码必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            values = list(self.preservation_tree.item(item)['values'])
            values[col_index] = new_value if new_value else ''
            self.preservation_tree.item(item, values=values)
            entry.destroy()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', lambda e: self.root.after(100, save_edit))
    
    def on_restoration_double_click(self, event):
        """处理执恢案件目录Tab的双击事件"""
        region = self.restoration_tree.identify_region(event.x, event.y)
        
        if region != "cell":
            return
        
        column = self.restoration_tree.identify_column(event.x)
        item = self.restoration_tree.identify_row(event.y)
        
        if not item or not column:
            return
        
        # 获取当前行的序号
        current_values = self.restoration_tree.item(item)['values']
        index = str(current_values[0]) if len(current_values) > 0 and current_values[0] else ''
        
        # 判断是否为新增行（包含"-"）
        is_new_row = '-' in index
        
        col_index = int(column.replace('#', '')) - 1
        
        # 如果是新增行，允许编辑第2列（项目名）、第3列（起始页）和第4列（终止页）
        # 如果是初始行，只允许编辑第3列（起始页）和第4列（终止页）
        if is_new_row:
            if col_index not in [1, 2, 3]:  # 1=项目名, 2=起始页, 3=终止页
                return
        else:
            if col_index not in [2, 3]:  # 2=起始页, 3=终止页
                return
        
        current_value = str(current_values[col_index]) if current_values[col_index] else ''
        
        x, y, width, height = self.restoration_tree.bbox(item, column)
        
        entry = ttk.Entry(self.restoration_tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        def save_edit(event=None):
            new_value = entry.get().strip()
            
            # 如果编辑的是起始页或终止页，需要验证为整数
            if col_index in [2, 3] and new_value:
                try:
                    page_num = int(new_value)
                    if page_num < 1:
                        messagebox.showerror("错误", "页码必须为正整数", parent=self.root)
                        entry.destroy()
                        return
                except ValueError:
                    messagebox.showerror("错误", "页码必须为整数", parent=self.root)
                    entry.destroy()
                    return
            
            values = list(self.restoration_tree.item(item)['values'])
            values[col_index] = new_value if new_value else ''
            self.restoration_tree.item(item, values=values)
            entry.destroy()
        
        def cancel_edit(event=None):
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', lambda e: self.root.after(100, save_edit))
    
    # ==================== 右键菜单功能 ====================
    
    def _generate_new_index(self, tree, selected_item, is_initial_row_func):
        """
        生成新行的序号
        :param tree: Treeview对象
        :param selected_item: 选中的行项
        :param is_initial_row_func: 判断是否为初始行的函数
        :return: 新生成的序号字符串
        """
        # 获取选中行的序号
        selected_values = tree.item(selected_item)['values']
        selected_index = str(selected_values[0]) if len(selected_values) > 0 and selected_values[0] else ''
        
        # 确定基础序号（如果是初始行，就是它自己；如果是新增行，提取第一个"-"之前的部分）
        if is_initial_row_func(selected_index):
            base_index = selected_index
        else:
            base_index = selected_index.split('-')[0]
        
        # 找到所有以该基础序号开头的新增行，找出最大后缀
        all_items = tree.get_children()
        max_suffix = 0
        
        for item in all_items:
            values = tree.item(item)['values']
            idx = str(values[0]) if len(values) > 0 and values[0] else ''
            
            # 检查是否是以相同基础序号开头的新增行
            if idx.startswith(f"{base_index}-"):
                # 提取后缀数字（最后一个"-"之后的部分）
                parts = idx.split('-')
                if len(parts) >= 2:
                    try:
                        suffix = int(parts[-1])
                        if suffix > max_suffix:
                            max_suffix = suffix
                    except ValueError:
                        pass
        
        # 新增行的序号为基础序号-(最大后缀+1)
        new_index = f"{base_index}-{max_suffix + 1}"
        
        return new_index
    
    def _is_initial_row_custom(self, index):
        """判断自建目录的行是否为初始行（不包含"-"）"""
        return '-' not in index
    
    def _is_initial_row_fixed(self, index):
        """判断固定项目列表的行是否为初始行（纯数字）"""
        try:
            int(index)
            return True
        except (ValueError, TypeError):
            return False
    
    def _add_row_after_selected(self, tree, selected_item, is_initial_row_func, has_project_column=True):
        """
        在选中行后添加新行
        :param tree: Treeview对象
        :param selected_item: 选中的行项
        :param is_initial_row_func: 判断是否为初始行的函数
        :param has_project_column: 是否有项目名称列
        """
        # 生成新序号
        new_index = self._generate_new_index(tree, selected_item, is_initial_row_func)
        
        # 获取所有行
        all_items = list(tree.get_children())
        selected_position = all_items.index(selected_item) if selected_item in all_items else len(all_items)
        
        # 获取选中行的序号
        selected_values = tree.item(selected_item)['values']
        selected_index = str(selected_values[0]) if len(selected_values) > 0 and selected_values[0] else ''
        
        # 确定基础序号
        if is_initial_row_func(selected_index):
            base_index = selected_index
        else:
            base_index = selected_index.split('-')[0]
        
        # 查找该基础序号组的所有行，找到最后一行的位置
        last_group_position = selected_position
        for i, item in enumerate(all_items):
            values = tree.item(item)['values']
            idx = str(values[0]) if len(values) > 0 and values[0] else ''
            
            # 如果是以相同基础序号开头的新增行
            if idx.startswith(f"{base_index}-"):
                last_group_position = i  # 更新为该组最后一行的位置
        
        # 在该组最后一行后插入
        insert_position = last_group_position + 1
        
        # 在计算出的位置插入新行
        if has_project_column:
            # 有项目名称列的Tab（民事、刑事、执保、执恢、刑事卷、副卷）
            tree.insert('', insert_position, values=(new_index, '', '', ''))
        else:
            # 自建目录Tab（无项目名称列）
            tree.insert('', insert_position, values=(new_index, '', ''))
    
    def _delete_selected_row(self, tree, selected_item, is_initial_row_func):
        """
        删除选中的行（带初始行保护）
        :param tree: Treeview对象
        :param selected_item: 选中的行项
        :param is_initial_row_func: 判断是否为初始行的函数
        """
        if not selected_item:
            return
        
        # 获取选中行的序号
        selected_values = tree.item(selected_item)['values']
        selected_index = str(selected_values[0]) if len(selected_values) > 0 and selected_values[0] else ''
        
        # 检查是否为初始行
        if is_initial_row_func(selected_index):
            messagebox.showwarning("警告", f"序号为 '{selected_index}' 的是初始数据行，不能删除！\n\n只能删除用户新增的行。", parent=self.root)
            return
        
        # 删除该行
        tree.delete(selected_item)
    
    def _show_context_menu(self, event, tree, is_initial_row_func, has_project_column=True):
        """
        显示右键菜单
        :param event: 鼠标事件
        :param tree: Treeview对象
        :param is_initial_row_func: 判断是否为初始行的函数
        :param has_project_column: 是否有项目名称列
        """
        # 识别点击的行
        item = tree.identify_row(event.y)
        if not item:
            return
        
        # 选中该行
        tree.selection_set(item)
        tree.focus(item)
        
        # 创建右键菜单
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="增加一行", command=lambda: self._add_row_after_selected(tree, item, is_initial_row_func, has_project_column))
        menu.add_command(label="删除一行", command=lambda: self._delete_selected_row(tree, item, is_initial_row_func))
        
        # 显示菜单
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def on_custom_right_click(self, event):
        """自建目录Tab的右键菜单"""
        self._show_context_menu(event, self.custom_tree, self._is_initial_row_custom, has_project_column=False)
    
    def on_civil_right_click(self, event):
        """民事案件目录Tab的右键菜单"""
        self._show_context_menu(event, self.civil_tree, self._is_initial_row_fixed, has_project_column=True)
    
    def on_criminal_right_click(self, event):
        """刑事案件目录Tab的右键菜单"""
        self._show_context_menu(event, self.criminal_tree, self._is_initial_row_fixed, has_project_column=True)
    
    def on_preservation_right_click(self, event):
        """执保案件目录Tab的右键菜单"""
        self._show_context_menu(event, self.preservation_tree, self._is_initial_row_fixed, has_project_column=True)
    
    def on_restoration_right_click(self, event):
        """执恢案件目录Tab的右键菜单"""
        self._show_context_menu(event, self.restoration_tree, self._is_initial_row_fixed, has_project_column=True)
    
    def on_criminal_case_right_click(self, event):
        """刑事卷目录Tab的右键菜单"""
        self._show_context_menu(event, self.criminal_case_tree, self._is_initial_row_fixed, has_project_column=True)
    
    def on_supplementary_right_click(self, event):
        """副卷目录Tab的右键菜单"""
        self._show_context_menu(event, self.supplementary_tree, self._is_initial_row_fixed, has_project_column=True)
    
    def browse_source_dir(self):
        directory = filedialog.askdirectory(title="选择源目录")
        if directory:
            self.source_dir.set(directory)
            # 自动更新输出目录为源目录下的"分件完成"
            self.output_dir.set(os.path.join(directory, "分件完成"))
            # 清空两个Tab列表中的数据
            self.clear_all_tables_data()
    
    def clear_all_tables_data(self):
        """清空所有表格中的起始页和终止页数据"""
        # 清空自建目录Tab的数据（保留序号）
        for item in self.custom_tree.get_children():
            values = self.custom_tree.item(item)['values']
            # 只保留序号，清空起始页和终止页
            self.custom_tree.item(item, values=(values[0], '', ''))
        
        # 清空民事案件目录Tab的数据（保留序号和项目名称）
        for item in self.civil_tree.get_children():
            values = self.civil_tree.item(item)['values']
            # 只保留序号和项目名称，清空起始页和终止页
            self.civil_tree.item(item, values=(values[0], values[1], '', ''))
        
        # 清空刑事案件目录Tab的数据（保留序号和项目名称）
        for item in self.criminal_tree.get_children():
            values = self.criminal_tree.item(item)['values']
            # 只保留序号和项目名称，清空起始页和终止页
            self.criminal_tree.item(item, values=(values[0], values[1], '', ''))
        
        # 清空执保案件目录Tab的数据（保留序号和项目名称）
        for item in self.preservation_tree.get_children():
            values = self.preservation_tree.item(item)['values']
            # 只保留序号和项目名称，清空起始页和终止页
            self.preservation_tree.item(item, values=(values[0], values[1], '', ''))
        
        # 清空执恢案件目录Tab的数据（保留序号和项目名称）
        for item in self.restoration_tree.get_children():
            values = self.restoration_tree.item(item)['values']
            # 只保留序号和项目名称，清空起始页和终止页
            self.restoration_tree.item(item, values=(values[0], values[1], '', ''))
        
        # 清空刑事卷目录Tab的数据（保留序号和项目名称）
        for item in self.criminal_case_tree.get_children():
            values = self.criminal_case_tree.item(item)['values']
            # 只保留序号和项目名称，清空起始页和终止页
            self.criminal_case_tree.item(item, values=(values[0], values[1], '', ''))
        
        # 清空副卷目录Tab的数据（保留序号和项目名称）
        for item in self.supplementary_tree.get_children():
            values = self.supplementary_tree.item(item)['values']
            # 只保留序号和项目名称，清空起始页和终止页
            self.supplementary_tree.item(item, values=(values[0], values[1], '', ''))
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
    
    def start_processing(self):
        # 在开始处理前，强制保存所有正在编辑的内容
        # 通过转移焦点来触发所有Entry的FocusOut事件
        self.root.focus_force()
        # 等待一小段时间让FocusOut事件处理完成
        self.root.update_idletasks()
        
        source = self.source_dir.get()
        output = self.output_dir.get()
        dpi = self.pdf_dpi.get()
        add_index = self.add_index_prefix.get()  # 获取单选框状态
        
        if not source:
            messagebox.showerror("错误", "请选择源目录")
            return
        
        if not os.path.isdir(source):
            messagebox.showerror("错误", "源目录不存在")
            return
        
        # 根据当前Tab获取项目列表
        if self.current_tab == 'custom':
            # 自建目录模式
            projects, skipped_count, validation_errors = self.get_custom_projects()
            use_index_only = True  # 自建目录始终使用序号作为文件名
        else:
            # 其他Tab模式（民事、刑事、执保、执恢、刑事卷、副卷）
            if self.current_tab == 'civil':
                projects, skipped_projects, validation_errors = self.get_civil_projects()
            elif self.current_tab == 'criminal':
                projects, skipped_projects, validation_errors = self.get_criminal_projects()
            elif self.current_tab == 'preservation':
                projects, skipped_projects, validation_errors = self.get_preservation_projects()
            elif self.current_tab == 'criminal_case':
                projects, skipped_projects, validation_errors = self.get_criminal_case_projects()
            elif self.current_tab == 'supplementary':
                projects, skipped_projects, validation_errors = self.get_supplementary_projects()
            else:
                # 执恢案件目录模式
                projects, skipped_projects, validation_errors = self.get_restoration_projects()
            use_index_only = False  # 其他Tab不使用序号-only模式
        
        # 显示验证错误
        if validation_errors:
            error_msg = "以下项目存在错误:\n\n" + "\n".join(validation_errors)
            messagebox.showerror("验证错误", error_msg, parent=self.root)
            return
        
        if not projects:
            messagebox.showwarning("警告", "没有要处理的项目（所有项目都被跳过或存在错误）", parent=self.root)
            return
        
        # 执行前验证：检查所有页码范围是否都能找到对应的文件
        is_valid, validation_errors = validate_page_ranges(source, projects)
        if not is_valid:
            error_msg = "以下项目存在页码问题，请修改后再执行:\n\n" + "\n".join(validation_errors)
            messagebox.showerror("页码验证失败", error_msg, parent=self.root)
            return
        
        # 禁用处理按钮
        self.process_button.config(state=tk.DISABLED)
        
        # 清空之前的结果
        self.result_text.delete(1.0, tk.END)
        
        # 在新线程中运行处理任务
        thread = threading.Thread(
            target=process_all_projects,
            args=(source, projects, output, dpi, self.update_progress, self.display_result),
            kwargs={'use_index_only': use_index_only, 'add_index_to_pdf': add_index},
            daemon=True
        )
        thread.start()
    
    def get_custom_projects(self):
        """获取自建目录的项目列表"""
        projects = []
        skipped_count = 0
        validation_errors = []
        
        for item in self.custom_tree.get_children():
            values = self.custom_tree.item(item)['values']
            index = str(values[0]).strip() if len(values) > 0 and values[0] else ''
            start_page_str = str(values[1]).strip() if len(values) > 1 and values[1] else ''
            end_page_str = str(values[2]).strip() if len(values) > 2 and values[2] else ''
            
            # 如果起始页为空，跳过该行
            if not start_page_str:
                skipped_count += 1
                continue
            
            # 验证起始页和终止页
            try:
                start_page = int(start_page_str)
                if start_page < 1:
                    validation_errors.append(f"序号'{index}': 起始页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"序号'{index}': 起始页必须为整数")
                continue
            
            if not end_page_str:
                validation_errors.append(f"序号'{index}': 终止页不能为空")
                continue
            
            try:
                end_page = int(end_page_str)
                if end_page < 1:
                    validation_errors.append(f"序号'{index}': 终止页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"序号'{index}': 终止页必须为整数")
                continue
            
            # 验证起始页小于等于终止页
            if start_page > end_page:
                validation_errors.append(f"序号'{index}': 起始页({start_page})必须小于或等于终止页({end_page})")
                continue
            
            # 自建目录：项目名称就是序号
            projects.append({
                'project': index,
                'start_page': start_page,
                'end_page': end_page,
                'index': index
            })
        
        return projects, skipped_count, validation_errors
    
    def get_civil_projects(self):
        """获取民事案件目录的项目列表"""
        projects = []
        skipped_projects = []
        validation_errors = []
        
        for item in self.civil_tree.get_children():
            values = self.civil_tree.item(item)['values']
            index = str(values[0]).strip() if len(values) > 0 and values[0] else ''
            project_name = values[1]
            start_page_str = str(values[2]).strip() if len(values) > 2 and values[2] else ''
            end_page_str = str(values[3]).strip() if len(values) > 3 and values[3] else ''
            
            # 如果起始页为空，跳过该项目
            if not start_page_str:
                skipped_projects.append(project_name)
                continue
            
            # 验证新增行的项目名称
            is_new_row = '-' in index
            if is_new_row and (not project_name or not str(project_name).strip()):
                validation_errors.append(f"序号'{index}'的行没有项目名称")
                continue
            
            # 验证起始页和终止页
            try:
                start_page = int(start_page_str)
                if start_page < 1:
                    validation_errors.append(f"'{project_name}': 起始页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 起始页必须为整数")
                continue
            
            if not end_page_str:
                validation_errors.append(f"'{project_name}': 终止页不能为空")
                continue
            
            try:
                end_page = int(end_page_str)
                if end_page < 1:
                    validation_errors.append(f"'{project_name}': 终止页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 终止页必须为整数")
                continue
            
            # 验证起始页小于等于终止页
            if start_page > end_page:
                validation_errors.append(f"'{project_name}': 起始页({start_page})必须小于或等于终止页({end_page})")
                continue
            
            projects.append({
                'project': project_name,
                'start_page': start_page,
                'end_page': end_page,
                'index': index
            })
        
        return projects, skipped_projects, validation_errors
    
    def get_criminal_projects(self):
        """获取刑事案件目录的项目列表"""
        projects = []
        skipped_projects = []
        validation_errors = []
        
        for item in self.criminal_tree.get_children():
            values = self.criminal_tree.item(item)['values']
            index = str(values[0]).strip() if len(values) > 0 and values[0] else ''
            project_name = values[1]
            start_page_str = str(values[2]).strip() if len(values) > 2 and values[2] else ''
            end_page_str = str(values[3]).strip() if len(values) > 3 and values[3] else ''
            
            # 如果起始页为空，跳过该项目
            if not start_page_str:
                skipped_projects.append(project_name)
                continue
            
            # 验证新增行的项目名称
            is_new_row = '-' in index
            if is_new_row and (not project_name or not str(project_name).strip()):
                validation_errors.append(f"序号'{index}'的行没有项目名称")
                continue
            
            # 验证起始页和终止页
            try:
                start_page = int(start_page_str)
                if start_page < 1:
                    validation_errors.append(f"'{project_name}': 起始页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 起始页必须为整数")
                continue
            
            if not end_page_str:
                validation_errors.append(f"'{project_name}': 终止页不能为空")
                continue
            
            try:
                end_page = int(end_page_str)
                if end_page < 1:
                    validation_errors.append(f"'{project_name}': 终止页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 终止页必须为整数")
                continue
            
            # 验证起始页小于等于终止页
            if start_page > end_page:
                validation_errors.append(f"'{project_name}': 起始页({start_page})必须小于或等于终止页({end_page})")
                continue
            
            projects.append({
                'project': project_name,
                'start_page': start_page,
                'end_page': end_page,
                'index': index
            })
        
        return projects, skipped_projects, validation_errors
    
    def get_preservation_projects(self):
        """获取执保案件目录的项目列表"""
        projects = []
        skipped_projects = []
        validation_errors = []
        
        for item in self.preservation_tree.get_children():
            values = self.preservation_tree.item(item)['values']
            index = str(values[0]).strip() if len(values) > 0 and values[0] else ''
            project_name = values[1]
            start_page_str = str(values[2]).strip() if len(values) > 2 and values[2] else ''
            end_page_str = str(values[3]).strip() if len(values) > 3 and values[3] else ''
            
            # 如果起始页为空，跳过该项目
            if not start_page_str:
                skipped_projects.append(project_name)
                continue
            
            # 验证新增行的项目名称
            is_new_row = '-' in index
            if is_new_row and (not project_name or not str(project_name).strip()):
                validation_errors.append(f"序号'{index}'的行没有项目名称")
                continue
            
            # 验证起始页和终止页
            try:
                start_page = int(start_page_str)
                if start_page < 1:
                    validation_errors.append(f"'{project_name}': 起始页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 起始页必须为整数")
                continue
            
            if not end_page_str:
                validation_errors.append(f"'{project_name}': 终止页不能为空")
                continue
            
            try:
                end_page = int(end_page_str)
                if end_page < 1:
                    validation_errors.append(f"'{project_name}': 终止页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 终止页必须为整数")
                continue
            
            # 验证起始页小于等于终止页
            if start_page > end_page:
                validation_errors.append(f"'{project_name}': 起始页({start_page})必须小于或等于终止页({end_page})")
                continue
            
            projects.append({
                'project': project_name,
                'start_page': start_page,
                'end_page': end_page,
                'index': index
            })
        
        return projects, skipped_projects, validation_errors
    
    def get_restoration_projects(self):
        """获取执恢案件目录的项目列表"""
        projects = []
        skipped_projects = []
        validation_errors = []
        
        for item in self.restoration_tree.get_children():
            values = self.restoration_tree.item(item)['values']
            index = str(values[0]).strip() if len(values) > 0 and values[0] else ''
            project_name = values[1]
            start_page_str = str(values[2]).strip() if len(values) > 2 and values[2] else ''
            end_page_str = str(values[3]).strip() if len(values) > 3 and values[3] else ''
            
            # 如果起始页为空，跳过该项目
            if not start_page_str:
                skipped_projects.append(project_name)
                continue
            
            # 验证新增行的项目名称
            is_new_row = '-' in index
            if is_new_row and (not project_name or not str(project_name).strip()):
                validation_errors.append(f"序号'{index}'的行没有项目名称")
                continue
            
            # 验证起始页和终止页
            try:
                start_page = int(start_page_str)
                if start_page < 1:
                    validation_errors.append(f"'{project_name}': 起始页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 起始页必须为整数")
                continue
            
            if not end_page_str:
                validation_errors.append(f"'{project_name}': 终止页不能为空")
                continue
            
            try:
                end_page = int(end_page_str)
                if end_page < 1:
                    validation_errors.append(f"'{project_name}': 终止页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 终止页必须为整数")
                continue
            
            # 验证起始页小于等于终止页
            if start_page > end_page:
                validation_errors.append(f"'{project_name}': 起始页({start_page})必须小于或等于终止页({end_page})")
                continue
            
            projects.append({
                'project': project_name,
                'start_page': start_page,
                'end_page': end_page,
                'index': index
            })
        
        return projects, skipped_projects, validation_errors
    
    def get_criminal_case_projects(self):
        """获取刑事卷目录的项目列表"""
        projects = []
        skipped_projects = []
        validation_errors = []
        
        for item in self.criminal_case_tree.get_children():
            values = self.criminal_case_tree.item(item)['values']
            index = str(values[0]).strip() if len(values) > 0 and values[0] else ''
            project_name = values[1]
            start_page_str = str(values[2]).strip() if len(values) > 2 and values[2] else ''
            end_page_str = str(values[3]).strip() if len(values) > 3 and values[3] else ''
            
            # 如果起始页为空，跳过该项目
            if not start_page_str:
                skipped_projects.append(project_name)
                continue
            
            # 验证新增行的项目名称
            is_new_row = '-' in index
            if is_new_row and (not project_name or not str(project_name).strip()):
                validation_errors.append(f"序号'{index}'的行没有项目名称")
                continue
            
            # 验证起始页和终止页
            try:
                start_page = int(start_page_str)
                if start_page < 1:
                    validation_errors.append(f"'{project_name}': 起始页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 起始页必须为整数")
                continue
            
            if not end_page_str:
                validation_errors.append(f"'{project_name}': 终止页不能为空")
                continue
            
            try:
                end_page = int(end_page_str)
                if end_page < 1:
                    validation_errors.append(f"'{project_name}': 终止页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 终止页必须为整数")
                continue
            
            # 验证起始页小于等于终止页
            if start_page > end_page:
                validation_errors.append(f"'{project_name}': 起始页({start_page})必须小于或等于终止页({end_page})")
                continue
            
            projects.append({
                'project': project_name,
                'start_page': start_page,
                'end_page': end_page,
                'index': index
            })
        
        return projects, skipped_projects, validation_errors
    
    def get_supplementary_projects(self):
        """获取副卷目录的项目列表"""
        projects = []
        skipped_projects = []
        validation_errors = []
        
        for item in self.supplementary_tree.get_children():
            values = self.supplementary_tree.item(item)['values']
            index = str(values[0]).strip() if len(values) > 0 and values[0] else ''
            project_name = values[1]
            start_page_str = str(values[2]).strip() if len(values) > 2 and values[2] else ''
            end_page_str = str(values[3]).strip() if len(values) > 3 and values[3] else ''
            
            # 如果起始页为空，跳过该项目
            if not start_page_str:
                skipped_projects.append(project_name)
                continue
            
            # 验证新增行的项目名称
            is_new_row = '-' in index
            if is_new_row and (not project_name or not str(project_name).strip()):
                validation_errors.append(f"序号'{index}'的行没有项目名称")
                continue
            
            # 验证起始页和终止页
            try:
                start_page = int(start_page_str)
                if start_page < 1:
                    validation_errors.append(f"'{project_name}': 起始页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 起始页必须为整数")
                continue
            
            if not end_page_str:
                validation_errors.append(f"'{project_name}': 终止页不能为空")
                continue
            
            try:
                end_page = int(end_page_str)
                if end_page < 1:
                    validation_errors.append(f"'{project_name}': 终止页必须为正整数")
                    continue
            except ValueError:
                validation_errors.append(f"'{project_name}': 终止页必须为整数")
                continue
            
            # 验证起始页小于等于终止页
            if start_page > end_page:
                validation_errors.append(f"'{project_name}': 起始页({start_page})必须小于或等于终止页({end_page})")
                continue
            
            projects.append({
                'project': project_name,
                'start_page': start_page,
                'end_page': end_page,
                'index': index
            })
        
        return projects, skipped_projects, validation_errors
    
    def update_progress(self, current, total, message):
        # 更新进度条
        percentage = (current / total) * 100
        self.progress['value'] = percentage
        
        # 更新进度标签
        self.progress_label.config(text=f"{message} - {percentage:.1f}%")
        
        # 更新GUI
        self.root.update_idletasks()
    
    def display_result(self, result):
        # 在主线程中更新GUI
        self.root.after(0, self._update_result_display, result)
    
    def _update_result_display(self, result):
        if isinstance(result, str):
            # 这是一条消息
            self.result_text.insert(tk.END, result + "\n")
            self.result_text.see(tk.END)
            
            # 如果是完成消息，弹出提示对话框
            if "处理完成！" in str(result) or "共处理" in str(result):
                self.root.after(100, lambda: messagebox.showinfo("处理完成", result, parent=self.root))
        elif isinstance(result, list):
            # 这是结果列表，展示处理结果
            self.result_text.insert(tk.END, "\n" + "="*80 + "\n")
            self.result_text.insert(tk.END, "处理结果详情:\n")
            self.result_text.insert(tk.END, f"{'项目名称':<20} {'起始页':<8} {'终止页':<8} {'文件数':<8} {'状态':<15} {'耗时(秒)':<8}\n")
            self.result_text.insert(tk.END, "-"*80 + "\n")
            
            for item in result:
                # 如果有错误详情，显示在状态中
                error_info = item.get('error_detail', '')
                status_display = f"{item['status']} - {error_info}" if error_info else item['status']
                self.result_text.insert(
                    tk.END,
                    f"{item['project']:<20} {item['start_page']:<8} {item['end_page']:<8} "
                    f"{item['file_count']:<8} {status_display:<15} {item['duration']:<8}\n"
                )
            
            self.result_text.insert(tk.END, "="*80 + "\n")
            self.result_text.see(tk.END)
        else:
            self.result_text.insert(tk.END, str(result) + "\n")
            self.result_text.see(tk.END)
        
        # 如果是完成消息，启用按钮
        if "处理完成！" in str(result) or "共处理" in str(result):
            self.process_button.config(state=tk.NORMAL)
            self.progress['value'] = 0
            self.progress_label.config(text="")


def main():
    root = tk.Tk()
    app = SplitProcessingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
