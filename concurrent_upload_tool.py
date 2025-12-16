import concurrent.futures
import requests
import time
import threading
import os

# =============================================================
# --- 配置信息：请在这里修改您的 MoviePilot 实例信息 ---
# =============================================================
API_BASE_URL = "http://YOUR_MOVIEPILOT_IP:PORT" # 例如: "http://192.168.1.100:3000"
AUTH_TOKEN = "YOUR_ACTUAL_API_TOKEN_HERE" 
STORAGE_NAME = "115" # 确保与 MoviePilot 中 115 的配置名称一致
MAX_CONCURRENT_UPLOADS = 5  # 设置最大同时上传的文件数（建议 3-5 个）
# =============================================================

AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}

# -------------------------------------------------------------
# 1. 获取待处理文件列表
# -------------------------------------------------------------
def get_pending_files():
    """从 MoviePilot API 获取需要整理/上传的文件列表。"""
    print(f"--- 1. 正在从 {API_BASE_URL}/library/files 获取待处理文件... ---")
    try:
        url = f"{API_BASE_URL}/library/files"
        response = requests.get(url, headers=AUTH_HEADERS)
        response.raise_for_status()
        
        pending_files = response.json().get("data", [])
        
        # 过滤处于等待整理状态的文件（根据实际 API 状态调整）
        pending_list = [f for f in pending_files if f.get("status") in ["pending", "wait_for_organize"]]
        
        return pending_list

    except requests.exceptions.RequestException as e:
        print(f"🚨 错误：无法获取文件列表。请检查 API_BASE_URL 和 AUTH_TOKEN。错误详情: {e}")
        return []

# -------------------------------------------------------------
# 2. 并发上传单个文件
# -------------------------------------------------------------
def upload_single_file_task(file_info):
    """
    单个线程执行的任务：直接调用 MoviePilot 的上传 API。
    """
    thread_name = threading.current_thread().name
    file_path = file_info.get("path", "未知文件路径")
    file_name = os.path.basename(file_path)
    
    print(f"[{thread_name}] ⚙️ 任务开始：准备上传文件: {file_name}")
    
    payload = {
        "file_path": file_path,
        "storage_name": STORAGE_NAME 
    }
    
    try:
        upload_url = f"{API_BASE_URL}/storage/upload"
        start_time = time.time()
        
        # 上传超时设置长一些 (30 分钟)
        response = requests.post(upload_url, json=payload, headers=AUTH_HEADERS, timeout=1800) 
        response.raise_for_status() 
        
        duration = time.time() - start_time
        print(f"[{thread_name}] ✅ 上传成功: {file_name} (耗时: {duration:.2f} 秒)")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[{thread_name}] 🚨 上传失败 {file_name}。错误: {e}")
        return False

# -------------------------------------------------------------
# 3. 主控制函数：启动并发
# -------------------------------------------------------------
def run_concurrent_upload():
    """主函数：获取列表，启动线程池。"""
    
    # 检查配置是否已修改
    if "YOUR_ACTUAL_API_TOKEN_HERE" in AUTH_TOKEN or "YOUR_MOVIEPILOT_IP:PORT" in API_BASE_URL:
        print("!!! 🚨 严重错误：请先修改脚本顶部的配置信息（AUTH_TOKEN, API_BASE_URL）!!!")
        return
    
    pending_files = get_pending_files()
    
    if not pending_files:
        print("没有找到待处理文件，程序结束。")
        return

    print(f"\n--- 2. 找到 {len(pending_files)} 个文件，启动 {MAX_CONCURRENT_UPLOADS} 个并发上传线程 ---")
    
    # 创建线程池执行器
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_UPLOADS) as executor:
        
        future_to_file = {
            executor.submit(upload_single_file_task, file_info): file_info.get("path")
            for file_info in pending_files
        }
        
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                # 检查任务的返回值
                if future.result():
                    print(f"🌟 最终报告：文件 {os.path.basename(file_path)} 已成功完成上传。")
                else:
                    print(f"⚠️ 最终报告：文件 {os.path.basename(file_path)} 上传过程中出现错误。")
            except Exception as e:
                print(f"❌ 最终报告：文件 {os.path.basename(file_path)} 任务执行时发生异常: {e}")

if __name__ == '__main__':
    run_concurrent_upload()