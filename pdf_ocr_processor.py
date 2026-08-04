import os
import requests
import json
import time
from pathlib import Path
import zipfile
# ===================================================
# 使用Umi-OCR接口来实现pdf文件的ocr识别,需要启动umi-ocr程序，其不是服务，是以单独程序的状态被启动的。
# lancer 2025-08-25
# ===================================================


class UmiOCRProcessor:
    def __init__(self, base_url="http://127.0.0.1:1224"):
        """
        初始化Umi-OCR处理器
        :param base_url: Umi-OCR的基础API地址
        """
        self.base_url = base_url
        self.upload_url = f"{base_url}/api/doc/upload"
        self.result_url = f"{base_url}/api/doc/result"
        self.download_url = f"{base_url}/api/doc/download"
        self.clear_url_template = f"{base_url}/api/doc/clear/{{}}"

    def ocr_pdf(self, pdf_path):
        """
        对PDF文件进行OCR识别
        :param pdf_path: PDF文件路径
        :return: OCR识别结果
        """
        try:
            # 1. 上传文件，获取任务ID
            print(f"正在上传文件: {pdf_path}")
            task_id = self._upload_file(pdf_path)
            if not task_id:
                return None
            
            # 2. 轮询任务状态直到OCR任务结束
            print(f"任务ID: {task_id}，正在OCR处理中...")
            ocr_result = self._poll_task_status(task_id)
            
            # 3. 生成目标文件，获取下载链接
            print("正在生成下载文件...")
            download_info = self._generate_download_file(task_id)
            
            # 4. 下载目标文件
            if download_info:
                print("正在下载结果文件...")
                download_path = self._download_file(download_info)
                
            # 5. 清理任务
            print("正在清理任务...")
            self._clear_task(task_id)
            
            return ocr_result, download_path  # 同时返回OCR结果和下载路径
                
        except Exception as e:
            print(f"OCR处理出错: {str(e)}")
            return None, None

    def _upload_file(self, pdf_path):
        """
        上传文件并获取任务ID
        :param pdf_path: PDF文件路径
        :return: 任务ID
        """
        # 任务参数
        options_json = json.dumps({
            "doc.extractionMode": "mixed",
        })
        
        with open(pdf_path, "rb") as file:
            response = requests.post(
                self.upload_url, 
                files={"file": file}, 
                data={"json": options_json}
            )
        
        response.raise_for_status()
        res_data = response.json()
        
        if res_data["code"] == 101:
            # 如果code == 101，表示服务器未接收到上传的文件
            # 在某些Linux系统上，如果file_name包含非ASCII字符，可能会出现此错误
            # 此时可以指定一个只包含ASCII字符的temp_name来构建上传请求
            file_name = os.path.basename(pdf_path)
            file_prefix, file_suffix = os.path.splitext(file_name)
            temp_name = "temp" + file_suffix
            print(f"[Warning] 检测到文件上传失败: code == 101")
            print(f"尝试使用temp_name {temp_name} 代替原始文件名 {file_name}")
            
            with open(pdf_path, "rb") as file:
                response = requests.post(
                    self.upload_url,
                    # 使用temp_name构建上传请求
                    files={"file": (temp_name, file)},
                    data={"json": options_json},
                )
            response.raise_for_status()
            res_data = response.json()
            
        if res_data["code"] != 100:
            print(f"任务提交失败: {res_data}")
            return None
            
        task_id = res_data["data"]
        print(f"任务ID: {task_id}")
        return task_id

    def _poll_task_status(self, task_id):
        """
        轮询任务状态直到OCR任务结束
        :param task_id: 任务ID
        :return: OCR结果
        """
        headers = {"Content-Type": "application/json"}
        data_str = json.dumps({
            "id": task_id,
            "is_data": True,
            "format": "text",
            "is_unread": True,
        })
        
        while True:
            time.sleep(1)
            response = requests.post(self.result_url, data=data_str, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            
            if res_data["code"] != 100:
                print(f"获取任务状态失败: {res_data}")
                return None

            print(f"    进度: {res_data['processed_count']}/{res_data['pages_count']}")
            
            if res_data["is_done"]:
                state = res_data["state"]
                if state != "success":
                    print(f"任务执行失败: {res_data['message']}")
                    return None
                print("OCR任务完成。")
                # 修改: 收集所有页面的OCR结果，而不是只返回最后一页
                all_text = ""
                if isinstance(res_data["data"], list):
                    # 如果数据是列表格式，连接所有页面的结果
                    for page_data in res_data["data"]:
                        if isinstance(page_data, str):
                            all_text += page_data
                        elif isinstance(page_data, dict) and "text" in page_data:
                            all_text += page_data["text"]
                        else:
                            all_text += str(page_data)
                else:
                    # 如果数据是字符串或其他格式，直接使用
                    all_text = str(res_data["data"])
                return all_text

    def _generate_download_file(self, task_id):
        """
        生成目标文件，获取下载链接
        :param task_id: 任务ID
        :return: 下载信息
        """
        headers = {"Content-Type": "application/json"}
        # 下载文件参数
        download_options = {
            "file_types": [
                "txt",
                "txtPlain",
                "jsonl",
                "csv",
                "pdfLayered",
                "pdfOneLayer",
            ],
            # ingore_blank 是一个拼写错误。如果使用Umi-OCR 2.1.4或更早版本，请使用这个错误拼写。
            # 如果使用最新代码构建的Umi-OCR，请使用正确的拼写 ignore_blank。
            "ingore_blank": False,  # 不忽略空白页
            "id": task_id
        }
        data_str = json.dumps(download_options)
        response = requests.post(self.download_url, data=data_str, headers=headers)
        response.raise_for_status()
        res_data = response.json()
        
        if res_data["code"] != 100:
            print(f"获取下载URL失败: {res_data}")
            return None
            
        return {
            "url": res_data["data"],
            "name": res_data["name"]
        }

    def _download_file(self, download_info):
        """
        下载目标文件
        :param download_info: 下载信息
        :return: 下载文件路径
        """
        url = download_info["url"]
        name = download_info["name"]
        
        # 下载文件保存位置
        download_dir = "./download"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        download_path = os.path.join(download_dir, name)
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 下载文件大小
        total_size = int(response.headers.get("content-length", 0))
        downloaded_size = 0
        log_size = 10485760  # 每10MB打印一次进度

        with open(download_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    if downloaded_size >= log_size:
                        log_size = downloaded_size + 10485760
                        progress = (downloaded_size / total_size) * 100
                        print(
                            f"    下载文件: {int(downloaded_size / 1048576)}MB | 进度: {progress:.2f}%"
                        )
        print(f"目标文件下载成功: {download_path}")
        return download_path

    def _clear_task(self, task_id):
        """
        清理任务
        :param task_id: 任务ID
        """
        clear_url = self.clear_url_template.format(task_id)
        response = requests.get(clear_url)
        response.raise_for_status()
        res_data = response.json()
        
        if res_data["code"] != 100:
            print(f"任务清理失败: {res_data}")
            return False
            
        print("任务清理成功。")
        return True

    def extract_text_from_result(self, ocr_result):
        """
        从OCR结果中提取文本
        :param ocr_result: OCR识别结果
        :return: 提取的文本内容
        """
        # 由于新的API直接返回文本结果，直接返回即可
        if not ocr_result:
            return ""
        return ocr_result

    def process_pdf_folder(self, input_folder, output_folder):
        """
        处理指定文件夹下的所有PDF文件
        :param input_folder: 输入文件夹路径
        :param output_folder: 输出文件夹路径
        """
        # 确保输出文件夹存在
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # 获取所有PDF文件
        pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"在 {input_folder} 中未找到PDF文件")
            return
        
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        # 处理每个PDF文件
        for pdf_file in pdf_files:
            pdf_path = os.path.join(input_folder, pdf_file)
            print(f"正在处理: {pdf_file}")
            
            # 进行OCR识别
            ocr_result, download_path = self.ocr_pdf(pdf_path)
            
            # 解压下载的zip文件并将.p.txt文件复制到output_folder
            if download_path and os.path.exists(download_path):
                try:
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        # 遍历zip文件中的所有文件
                        for file_info in zip_ref.infolist():
                            # 如果是.p.txt文件，则解压到output_folder
                            if file_info.filename.endswith('.p.txt'):
                                # 构造目标文件路径
                                target_path = os.path.join(output_folder, os.path.basename(file_info.filename))
                                # 解压单个文件
                                with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                                    target.write(source.read())
                                print(f"已复制.p.txt文件到: {target_path}")
                except Exception as e:
                    print(f"解压或复制文件时出错: {str(e)}")
            
            # 添加延时，避免请求过于频繁
            time.sleep(1)

def main():
    # 配置输入和输出文件夹
    input_folder = "D:\\temp\\pdf"  # 修改为你的PDF文件夹路径
    output_folder = "D:\\temp\\txt"  # 修改为你的输出文件夹路径
    
    # 创建OCR处理器实例
    ocr_processor = UmiOCRProcessor()
    
    # 处理PDF文件
    ocr_processor.process_pdf_folder(input_folder, output_folder)
    
    print("所有PDF文件处理完成！")

if __name__ == "__main__":
    main()