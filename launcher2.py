import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import os
import json
import signal

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "coffee_launcher_config.json")

# 默认路径设置
DEFAULT_PATHS = {
    "venv_path": "D:/pycharm/.venv/flask",
    "venv_python": "D:/pycharm/.venv/Scripts/python.exe",
    "scripts_dir": "D:/pycharm/.venv/flask"
}

# # 修改这里的默认路径
# DEFAULT_PATHS = {
#     "venv_path": "你的/新/路径",
#     "venv_python": "新/python/解释器路径",
#     "scripts_dir": "新/脚本/目录"
# }

# 加载配置
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except:
        config = DEFAULT_PATHS
else:
    config = DEFAULT_PATHS

# 确保路径可用
VENV_PYTHON = config["venv_python"] if os.path.exists(config["venv_python"]) else config.get("system_python", "python")
SCRIPTS_DIR = config["scripts_dir"]

# 存储正在运行的进程
running_processes = []


# 启动脚本并记录进程
def run_script(script_name):
    """启动脚本并记录进程"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)

    if not os.path.exists(script_path):
        log_message(f"❌ 错误: 找不到脚本 '{script_path}'")
        return

    try:
        # 启动进程
        process = subprocess.Popen(
            [VENV_PYTHON, script_path],
            cwd=SCRIPTS_DIR
        )

        running_processes.append(process)
        log_message(f"✅ 已启动: {script_name} (PID: {process.pid})")
    except Exception as e:
        log_message(f"❌ 启动失败: {e}")



# 日志输出
def log_message(message):
    """日志输出"""
    log_text.config(state='normal')
    log_text.insert(tk.END, message + "\n")
    log_text.config(state='disabled')
    log_text.see(tk.END)


# 安全退出所有程序
def exit_all():
    """安全退出所有程序"""
    if not running_processes:
        log_message("⚠️ 没有正在运行的程序")
        return

    if not messagebox.askyesno("确认", "确定要退出所有程序吗？"):
        return

    log_message("⏳ 正在停止所有程序...")

    # 终止所有进程
    for process in running_processes:
        try:
            process.terminate()
            log_message(f"⚠️ 已终止 PID {process.pid}")
        except Exception as e:
            log_message(f"❌ 终止失败: {e}")

    running_processes.clear()
    log_message("✅ 所有程序已安全退出")


# 关闭启动器
def close_app():
    """关闭启动器"""
    if running_processes and messagebox.askyesno("警告", "仍有程序在运行！确定强制退出吗？"):
        exit_all()
    root.destroy()


# 创建主窗口
root = tk.Tk()
root.title("咖啡生产启动器")
root.geometry("400x500")
root.protocol("WM_DELETE_WINDOW", close_app)

# 配置信息显示
config_frame = tk.LabelFrame(root, text="当前配置")
config_frame.pack(fill='x', padx=10, pady=10)

tk.Label(config_frame, text=f"Python路径: {VENV_PYTHON}", anchor='w', justify=tk.LEFT).pack(fill='x', padx=5, pady=2)
tk.Label(config_frame, text=f"脚本目录: {SCRIPTS_DIR}", anchor='w', justify=tk.LEFT).pack(fill='x', padx=5, pady=2)

# 按钮样式
btn_style = {'font': ('Arial', 12), 'height': 2, 'width': 15, 'pady': 5}

# 按钮容器
btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

# 功能按钮
tk.Button(btn_frame, text="🔌 启动电源", command=lambda: run_script("start_work.py"), bg="#f0f0ff", **btn_style).pack()
tk.Button(btn_frame, text="⚙️ 运行主程序", command=lambda: run_script("mainio_IN11_monitor.py"), bg="#f0fff0",
          **btn_style).pack()
tk.Button(btn_frame, text="🖥️ 启动界面", command=lambda: run_script("app.py"), bg="#fff0f0", **btn_style).pack()

# 控制按钮
ctrl_frame = tk.Frame(root)
ctrl_frame.pack(pady=10, padx=10)

tk.Button(ctrl_frame, text="🛑 退出所有程序", command=exit_all, bg="#ffe0e0", width=15).pack(side=tk.LEFT, padx=5)
tk.Button(ctrl_frame, text="✕ 关闭启动器", command=close_app, bg="#efefef", width=15).pack(side=tk.LEFT, padx=5)

# 日志区域
log_frame = tk.LabelFrame(root, text="日志输出")
log_frame.pack(fill='both', expand=True, padx=10, pady=10)

log_text = tk.Text(log_frame, height=8)
log_text.pack(fill='both', expand=True, padx=5, pady=5)
log_scroll = tk.Scrollbar(log_text, command=log_text.yview)
log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
log_text.config(yscrollcommand=log_scroll.set, state='disabled')

# 初始日志
log_message("🚀 启动器已就绪")
log_message(f"Python路径: {VENV_PYTHON}")
log_message(f"脚本目录: {SCRIPTS_DIR}")
log_message("请选择要启动的组件...")

root.mainloop()
