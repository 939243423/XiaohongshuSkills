import time
import subprocess
import os
import datetime

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
    print("⚙️  规则：立刻执行第一次，之后每 6 小时执行一次")
    print("========================================")
    
    interval_seconds = 6 * 60 * 60  # 6小时的秒数
    
    while True:
        run_job()
        
        # 计算下一次执行时间
        next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval_seconds)
        print(f"⏳ 等待 6 小时，下一次执行时间预计: {next_run.strftime('%Y-%m-%d %H:%M:%S')} ... (随时可Ctrl+C终止)")
        
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n⏹️ 收到停止信号，已退出定时任务。")
            break

if __name__ == "__main__":
    main()
