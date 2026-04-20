import time
import subprocess
import os
import datetime
import random

def run_job():
    print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 开始执行自动化发布流程...")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xhs_robot_final.py')
    try:
        # 使用 subprocess 调用
        result = subprocess.run(['python', script_path])
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 流程执行完毕，退出码: {result.returncode}")
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 运行出错: {e}")

def main():
    print("========================================")
    print("⏰ 小红书定时发布任务已启动")
    print("⚙️  规则：立刻执行第一次，之后每 12 小时执行一次")
    print("========================================")
    
    interval_hours = 12
    
    while True:
        run_job()
        
        # 添加随机抖动：在设定间隔的基础上 +/- 30 分钟 (可以根据需要调整)
        jitter_minutes = random.randint(-45, 45)
        current_sleep_seconds = (interval_hours * 60 + jitter_minutes) * 60
        
        # 计算下一次执行时间
        next_run = datetime.datetime.now() + datetime.timedelta(seconds=current_sleep_seconds)
        print(f"⏳ 随机抖动后的等待时间: {current_sleep_seconds / 3600:.2f} 小时 (约 {jitter_minutes:+} 分钟)")
        print(f"⏳ 下一次执行时间预计: {next_run.strftime('%Y-%m-%d %H:%M:%S')} ... (随时可Ctrl+C终止)")
        
        try:
            time.sleep(current_sleep_seconds)
        except KeyboardInterrupt:
            print("\n⏹️ 收到停止信号，已退出定时任务。")
            break

if __name__ == "__main__":
    main()
