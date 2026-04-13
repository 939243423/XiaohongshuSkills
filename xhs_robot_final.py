import re
import os
import random
import json
import subprocess
import requests
import shutil
import concurrent.futures
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# ================= 配置区 =================
PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# 1. 密钥配置 (从环境变量或本地文件获取)
def get_api_keys() -> tuple[str, str, str]:
    ca_key = os.environ.get("CA_KEY", "")
    sf_key = os.environ.get("SILICON_KEY", "")
    dt_webhook = os.environ.get("DINGTALK_WEBHOOK", "")
    
    # 支持降级到从 accounts.json 里的某处读取，或者专门的 config
    config_path = PROJECT_ROOT / "config" / "api_keys.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                ca_key = ca_key or config_data.get("CA_KEY", "")
                sf_key = sf_key or config_data.get("SILICON_KEY", "")
                dt_webhook = dt_webhook or config_data.get("DINGTALK_WEBHOOK", "")
        except Exception as e:
            print(f"⚠️ 读取配置文件 {config_path} 失败: {e}")
            
    if not ca_key: ca_key = "xxx"
    if not sf_key: sf_key = "xxx"
    return ca_key, sf_key, dt_webhook

CA_KEY, SILICON_KEY, DINGTALK_WEBHOOK = get_api_keys()

SEARCH_LIMIT = 5                # 聚合前5条热门笔记的素材

# 初始化客户端
ca_client = OpenAI(api_key=CA_KEY, base_url="https://api.chatanywhere.tech/v1")
sf_client = OpenAI(api_key=SILICON_KEY, base_url="https://api.siliconflow.cn/v1")

# 2. 模型与生图配置
CA_MODEL = "gpt-5"
SF_TEXT_MODEL = "Pro/deepseek-ai/DeepSeek-V3.2"  
# IMAGE_MODEL = "Kwai-Kolors/Kolors" # 使用 Kolors 模型
IMAGE_MODEL = "Qwen/Qwen-Image" # 使用 Qwen/Qwen-Image 模型

# --- 核心新增：Pillow 字体配置 ---
FONT_FILE = "AlibabaPuHuiTi-3-65-Medium.ttf" 
# -------------------------------

# 3. 苹果技巧专题矩阵 (100个)
APPLE_TOPICS_DICT = {
    "基础交互与系统定制": [
        "iPhone长截图保姆级教程", "iPhone控制中心自定义", 
        "iPhone辅助触控悬浮球设置", "iPhone侧边键功能自定义", "iPhone键盘单手模式切换",
        "iOS18主屏幕图标变色", "iOS18锁屏底端图标更换", "Siri语音助手进化版玩法",
        "iPhone实时字幕功能开启", "iPhone辅助功能放大镜用法", "iPhone引导访问防他人乱点",
        "iPhone轻点背面快捷指令", "iPhone锁屏组件花式玩法","iPhone隐藏截屏技巧",
    ],
    "影像摄影与相册管理": [
        "iOS自带录屏高级玩法", "iPhone实况照片变视频", "iPhone镜像前置镜头设置",
        "iPhone隐藏相册加密方法", "iPhone人像模式虚化调整", "iPhone电影模式分级调色",
        "iPhone微距模式创意玩法", "iPhone延时摄影参数分享", "iPhone夜间模式拍星空技巧",
        "iPhone照片批量重命名", "iPhone连拍照片筛选技巧", "iPhone制作动图GIF教程",
        "iPhone视频提取背景音乐", "iPhone录制ProRes格式科普", "iPhone录制空间视频教学",
        "iPhone拍照滤镜风格自定义", "iPhone自带相册修图参数", "iPhone快门音关闭小技巧",
        "iPhone本地AI消除路人", "iPhone网格线构图入门", "iPhone曝光锁定对焦技巧"
    ],
    "性能安全与防坑指南": [
        "iPhone电池健康长寿秘籍", "iPhone信号增强玄学设置", "iPhone充电上限80%有必要吗",
        "iPhone系统内存深度清理", "iPhone发烫降温5个绝招", "iPhone定位服务省电方案",
        "iPhone后台刷新哪些该关", "iPhone隐私安全设置检查", "iPhone垃圾短信自动拦截",
        "iPhone关机也能找回技巧", "iPhone密码管理App用法", "iOS系统更新降级防坑指南",
        "iPhone空间音频体验优化", "iPhone镜头擦拭防刮指南", "iPhone工程模式查看信号"
    ],
    "高效办公与生产力": [
        "iPhone原况文本提取实操", "iPhone备忘录扫描全能王", "iPhone科学备忘录公式输入",
        "iPhone数学笔记实时演算", "iPhone文件App远程连接NAS", "iPhone智能汇总长文摘要",
        "iPhone自带翻译实时同传", "iPhone提醒事项自律神器", "iPhone快捷指令自动化实战",
        "iPhone邮件App高级过滤", "iPhone Safari浏览器隐藏功能", "iPhone浏览器干扰控制功能",
        "iPhone分屏画中画开启技巧", "iPhone科学计算器隐藏模式"
    ],
    "生活健康与小工具": [
        "iPhone自带测量仪用法", "iPhone语音隔离通话更清晰", "iPhone屏幕使用时间控制",
        "iPhone专注模式深度定制", "iPhone健康App经期追踪", "iPhone体能训练数据分析",
        "iPhone自带天气预报深度解读", "iPhone股市App高级用法", "iPhone通话录音法律合规点",
        "iPhone白噪音背景音设置", "iPhone辅助功能护眼模式", "iPhone夜间模式自动切换",
        "iPhone低电量模式自动触发", "iPhone动态壁纸空间效果"
    ],
    "全家桶生态联动": [
        "iPad分屏协同办公技巧", "iPad随航Mac变副屏教程", "iPad搭配Pencil绘图入门",
        "iPad学习笔记APP大比拼", "Apple Watch洗手检测开启", "Apple Watch手势控制技巧",
        "AppleWatch查找手机黑科技", "AirPods降噪模式切换逻辑", "AirPods自动切换设备设置",
        "iCloud云端备份空间优化", "AirDrop投送失败解决办法", "Mac与iPhone镜像操控",
        "AppleTV遥控器隐藏用法", "苹果全家桶接力续写功能", "苹果共享相簿邀请技巧",
        "iPhone跨设备剪贴板联动"
    ],
    "极客进阶与海外相关": [
        "iPhone恢复模式保命指南", "iPhone DFU模式进阶操作", "iPhone海外账号注册流程",
        "iPhone更换地区后的新功能", "iPhone连接外置硬盘剪辑视频"
    ]
}

APPLE_TOPICS = [topic for sublist in APPLE_TOPICS_DICT.values() for topic in sublist]

# --- 进阶反洗稿：防同质化的人设与情绪池 ---
PERSONA_POOL = [
    "被苹果 Bug 折磨的暴躁极客", 
    "专给长辈写教程的耐心外甥", 
    "只会用大白话解释的数码小白救星",
    "十年果粉带一点小高冷的老玩家",
    "省吃俭用热衷免费薅羊毛特性的打工人"
]

EMOTION_POOL = [
    "开篇必须要吐槽一个痛点",
    "开篇要表现得非常激动，觉得大家不知道太可惜了",
    "开头要表现出对某些反人类交互设计感到非常无语",
    "充满分享欲，像老朋友聊天一样自然引入"
]
# ---------------------------------------------

# 4. 路径配置
TEMP_IMG_DIR = PROJECT_ROOT / "temp_downloads"
HISTORY_FILE = PROJECT_ROOT / "published_ids.txt"
IMG_CROP_PIXELS = 2
# ==========================================

def get_history_ids() -> set[str]:
    if not HISTORY_FILE.exists(): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_history_id(f_id: str) -> None:
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{f_id}\n")

def run_cmd(cmd: str, timeout: int = 60) -> dict | None:
    """正则解析命令行输出的 JSON，包含超时机制"""
    try:
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(SCRIPTS_DIR), universal_newlines=False
        )
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate()
            print(f"❌ [run_cmd] 执行超时 ({timeout}s): {cmd}")
            return None
        
        output = stdout_bytes.decode('utf-8', errors='ignore').strip()
        match = re.search(r'(\{.*\})', output, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except Exception as e: print(f"⚠️ [run_cmd] JSON解析失败: {e}")
        return None
    except Exception as e: 
        print(f"❌ [run_cmd] 执行异常: {e}")
        return None

def show_confirm_box(title: str, content: str, timeout: int = 0, default: bool = True) -> bool:
    """弹出 Yes/No 确认框, 支持超时默认"""
    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    
    window_width = 400
    window_height = 150
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
    
    result = [default]
    
    def on_yes():
        result[0] = True
        root.destroy()
        
    def on_no():
        result[0] = False
        root.destroy()
        
    lbl = tk.Label(root, text=content, pady=20, padx=20)
    lbl.pack()
    
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    
    btn_yes = tk.Button(btn_frame, text="是 (Yes)", width=15, command=on_yes)
    btn_yes.pack(side="left", padx=10)
    
    btn_no = tk.Button(btn_frame, text="否 (No)", width=15, command=on_no)
    btn_no.pack(side="right", padx=10)

    if timeout > 0:
        def update_timer(left):
            if left <= 0:
                print(f"[{title}] 计时结束，使用默认选择: {'是' if default else '否'}")
                root.destroy()
            else:
                if default:
                    btn_yes.config(text=f"是 (Yes) ({left}s)")
                else:
                    btn_no.config(text=f"否 (No) ({left}s)")
                root.after(1000, update_timer, left - 1)
        root.after(1000, update_timer, timeout)

    def on_closing():
        result[0] = False
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()
    return result[0]

def show_publish_review_box(title: str, content: str, timeout: int = 0, default_choice: str = 'yes') -> str:
    """弹出发送/还原/取消三选一框，专门用于最终发布确认"""
    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    
    window_width = 500
    window_height = 180
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
    
    result = [default_choice]
    
    def on_yes():
        result[0] = 'yes'
        root.destroy()
        
    def on_no():
        result[0] = 'no'
        root.destroy()
        
    def on_cancel():
        result[0] = 'cancel'
        root.destroy()
        
    lbl = tk.Label(root, text=content, pady=20, padx=20)
    lbl.pack()
    
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    
    btn_yes = tk.Button(btn_frame, text="✅ 直接发布", width=15, bg="#4CAF50", fg="white", command=on_yes)
    btn_yes.pack(side="left", padx=10)
    
    btn_no = tk.Button(btn_frame, text="🔄 改用原图发稿", width=15, bg="#FF9800", fg="white", command=on_no)
    btn_no.pack(side="left", padx=10)
    
    btn_cancel = tk.Button(btn_frame, text="❌ 终止并清空垃圾", width=15, bg="#F44336", fg="white", command=on_cancel)
    btn_cancel.pack(side="right", padx=10)

    if timeout > 0:
        def update_timer(left):
            if left <= 0:
                print(f"[{title}] 计时结束，使用默认选择: {default_choice}")
                root.destroy()
            else:
                if default_choice == 'yes':
                    btn_yes.config(text=f"✅ 直接发布 ({left}s)")
                elif default_choice == 'no':
                    btn_no.config(text=f"🔄 改用原图发稿 ({left}s)")
                else:
                    btn_cancel.config(text=f"❌ 终止并清空垃圾 ({left}s)")
                root.after(1000, update_timer, left - 1)
        root.after(1000, update_timer, timeout)

    def on_closing():
        result[0] = 'cancel' # 点X关闭窗口默认当作截断操作
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()
    return result[0]

def show_selection_dialog(valid_feeds: list[dict], search_keyword: str, timeout: int = 0, default_index: int = 0) -> int:
    """展示带有真实标题和正文预览的选择框"""
    root = tk.Tk()
    root.title("请选择核心对标笔记")
    root.attributes("-topmost", True)
    root.geometry("800x500")

    selected_data = {"index": 0}

    label = tk.Label(root, text=f"专题：{search_keyword}\n请选择主素材来源（已获取详情内容）：", pady=10)
    label.pack()

    columns = ("序号", "真实标题/内容预览", "笔记ID")
    tree = ttk.Treeview(root, columns=columns, show="headings")
    tree.heading("序号", text="序号")
    tree.heading("真实标题/内容预览", text="真实标题/内容预览")
    tree.heading("笔记ID", text="笔记ID")
    tree.column("序号", width=50, anchor="center")
    tree.column("真实标题/内容预览", width=550)
    tree.column("笔记ID", width=150)

    for i, item in enumerate(valid_feeds):
        tree.insert("", "end", values=(i, item['display_text'], item['id']))

    tree.pack(fill="both", expand=True, padx=10, pady=10)

    def on_confirm():
        selection = tree.selection()
        if selection:
            item = tree.item(selection[0], "values")
            selected_data["index"] = int(item[0])
        root.destroy()

    btn = tk.Button(root, text="确定选择 (默认首条)", command=on_confirm, width=30, height=2, bg="#f39c12", fg="white")
    btn.pack(pady=15)

    if timeout > 0:
        def update_timer(left):
            if left <= 0:
                print(f"[选择对标笔记] 计时结束，默认选择第 {default_index+1} 条")
                selected_data["index"] = default_index
                root.destroy()
            else:
                btn.config(text=f"确定选择 (默认首条 {left}s)")
                root.after(1000, update_timer, left - 1)
        root.after(1000, update_timer, timeout)

    root.mainloop()
    return selected_data["index"]

def clean_temp_files() -> None:
    """清理临时文件夹"""
    print("🧹 正在清理临时文件...")
    try:
        if TEMP_IMG_DIR.exists():
            shutil.rmtree(TEMP_IMG_DIR)
        TEMP_IMG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"⚠️ 清理临时文件异常: {e}")

def generate_silicon_pure_background(theme: str) -> str | None:
    """调用大模型动态构思生图Prompt，并调用硅基流动生成首图底版"""
    print(f"🎨 硅基动力：正在通过 AI 引擎动态构思【无限创意的首图底版】...")
    url = "https://api.siliconflow.cn/v1/images/generations"
    
    # 使用大模型脑爆一个千变万化的 prompt，让每次生成都完全不一样
    prompt_brainstorm = f"""
    你需要为一篇关于苹果数码技巧（核心主题：【{theme}】）的小红书图文笔记，设计一张极具视觉冲击力的封面底图。
    该底图将用于中央或上方排版白色/黑色大字，因此画面必须满足【大量留白或干净的背景层】，严禁出现杂乱元素干扰文字阅读。

    我们要突破想象力，但【核心视觉元素或氛围必须与苹果（Apple/iOS）及主题“{theme}”紧密相关】。
    你可以从以下风格中随机汲取灵感（可以融合）：
    - 苹果官方极简风（丝滑的磨砂铝合金材质、精细的边缘倒角、镜头玻璃的折射感）
    - 创意UI隐喻（将“{theme}”中的操作逻辑转化为唯美的悬浮毛玻璃卡片、发光的控制轴或丝滑的动画定格）
    - 治愈系数码生活（晨光下的干净桌面、一杯咖啡配上精致的iPad/iPhone局部、光影在墙面形成的苹果Logo轮廓）
    - 抽象材质流体（采用苹果品牌色如太空灰、星光色、深夜色，展现极具呼吸感的流动金属或丝绒感光影）
    - 赛博光束（极细的激光勾勒出智能设备的轮廓，光线流转暗示数据计算）

    严格要求：
    1. 画面主体必须让观众一眼能联想到“高端数码、Apple、智能生活”。
    2. 只输出一段极度具体、画面感极强的中文图像描述（作为 Midjourney 即时生图的 Prompt），不要超过 150 个字。严禁包含任何“好的”、“为你提供”等废话。
    3. 必须包含画面主体、材质、光影效果（如影棚级光线、丁达尔光等）。
    """
    
    try:
        res = sf_client.chat.completions.create(
            model=SF_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt_brainstorm}],
            temperature=0.9
        )
        ai_generated_prompt = res.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ 动态 prompt 生成失败，降级为经典手机特写底图: {e}")
        ai_generated_prompt = "极简高质感底图。正中央完全对称放置一部新款智能手机的正面高清大特写，手机主体极大，精确占据整个画面高度的75%，宽高比为9:19.5，为上下方留出完美的留白排版空间。手机屏幕的最顶部有标志性的极窄黑色药丸形状灵动岛。手机屏幕内全屏展示着色彩明艳可爱的卡通萌物壁纸。影棚级明亮柔和的光线，画面极度干净、纯粹、几何对称感极强。"

    refined_prompt = f"竖向构图。{ai_generated_prompt}。8K分辨率，杰作，极简高级质感，纯净无杂物，绝对完美的留白排版空间。"
    print(f"✨ 本次抽签生成的盲盒底图 Prompt: {refined_prompt}")
    
    
    payload = {
        "model": IMAGE_MODEL,
        "prompt": refined_prompt,
        "size": "768x1024",
        "num_inference_steps": 25 # Kolors建议步数，确保细节
    }
    headers = {"Authorization": f"Bearer {SILICON_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=90)
        if response.status_code == 200:
            return response.json()['data'][0]['url']
        else:
            print(f"❌ 绘图失败 HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ 绘图异常: {e}")
    return None

def pillow_add_text_to_image(image_path: str, title: str) -> bool:
    """使用 Pillow 库提升排版风格：加入阴影与主副标拆分"""
    print(f"✍️ Pillow 进阶版：正在首图刻制高级版式...")
    
    try:
        img = Image.open(image_path)
        if img.mode != 'RGB': img = img.convert('RGB')
        draw = ImageDraw.Draw(img)
        width, height = img.size

        font_path = str(PROJECT_ROOT / FONT_FILE)
        if not os.path.exists(font_path):
            print(f"⚠️ 未找到字体文件 {FONT_FILE}，将使用系统默认字体")
            font_main = ImageFont.load_default()
            font_sub = ImageFont.load_default()
        else:
            font_main = ImageFont.truetype(font_path, int(width / 12))
            font_sub = ImageFont.truetype(font_path, int(width / 25))

        # 严格清洗掉 Emoji 等字体不支持的特殊拓展符号，防止出现 []
        clean_text_full = re.sub(r'[^\w\s\u4e00-\u9fa5，。！？、：；（）【】《》“”‘’+\-*\/\!]', '', title).strip()
        if not clean_text_full:
            clean_text_full = "苹果实用技巧分享"
            
        # 移除原有的 18 字硬性截断，改成宽松容量，交由下方的自适应缩放算法保证不溢出
        clean_text_full = clean_text_full[:36] 

        def smart_split(text):
            if len(text) <= 7: return [text]
            # 优先按照标点折行
            for p in ['？', '！', '，', '。', '、', '：', ' ', '?', '!']:
                if p in text and 3 <= text.index(p) <= len(text) - 2:
                    idx = text.index(p)
                    # 保留标点在第一行
                    return [text[:idx+1].strip(), text[idx+1:].strip()]
            # 其次查找中英文边界折行 (防止 iPhone信 被强行劈开)
            mid_range = range(max(1, len(text)//2 - 3), min(len(text)-1, len(text)//2 + 3))
            for i in mid_range:
                if (ord(text[i]) < 128 and ord(text[i+1]) >= 128) or (ord(text[i]) >= 128 and ord(text[i+1]) < 128):
                    return [text[:i+1].strip(), text[i+1:].strip()]
            # 兜底强制中分
            mid = len(text) // 2
            return [text[:mid].strip(), text[mid:].strip()]

        lines = smart_split(clean_text_full)

        # 动态估算每一行的物理显示占比（汉字占1个单位，英文占0.55个单位）
        def get_display_width(text):
            return sum(1 if '\u4e00' <= char <= '\u9fa5' else 0.55 for char in text)
        
        max_display_width = max(max([get_display_width(line) for line in lines]), 1)
        # 根据该行最多字符动态打回字号：最高不越过图片宽度 85%，防过密防截断
        font_size = max(20, min(int(width / 5.0), int((width * 0.85) / max_display_width)))

        try:
            font_main = ImageFont.truetype(font_path, font_size)
        except Exception:
            font_main = ImageFont.load_default()

        line_heights = []
        line_widths = []
        for line in lines:
            try:
                left, top, right, bottom = draw.textbbox((0, 0), line, font=font_main)
                line_widths.append(right - left)
                line_heights.append(bottom - top)
            except:
                w, h = draw.textsize(line, font=font_main)
                line_widths.append(w)
                line_heights.append(h)
                
        # 稍微拉开行距，避免两行文字的厚描边互相打架糊成一团
        line_spacing = int(font_size * 0.25)
        total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
        
        # 【排版进阶】：根据视觉反馈微调距离顶部距离，下移至 17% 左右，避免顶边过满
        # 目的：确保文字呼吸感的同时，依然将最引人注目的中间大片区域让位给手机
        start_y = height * 0.2 
        
        # 进一步调细描边厚度，还原图二清爽的视觉感 (描边比例降至 1/14)
        stroke_width = max(2, int(font_size / 14))
        current_y = start_y
        
        # 纯白大字，黑色描边，高度还原参考图且防止文字粘连
        for i, line in enumerate(lines):
            x = (width - line_widths[i]) / 2
            try:
                draw.text((x, current_y), line, font=font_main, fill=(255, 255, 255), 
                          stroke_width=stroke_width, stroke_fill=(0, 0, 0))
            except TypeError:
                # 降级模拟法
                for dx in range(-stroke_width, stroke_width + 1):
                    for dy in range(-stroke_width, stroke_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, current_y + dy), line, font=font_main, fill=(0, 0, 0))
                draw.text((x, current_y), line, font=font_main, fill=(255, 255, 255))
            current_y += line_heights[i] + line_spacing

        # 底部精致小水印：包含官方矢量苹果黑标与黑色水印文字，添加白色细微发光底防杂色
        try:
            # 字体调小
            font_sub = ImageFont.truetype(font_path, int(width / 35))
        except:
            font_sub = ImageFont.load_default()
            
        watermark = "IOS 技巧分享"
        try:
            w_left, w_top, w_right, w_bottom = draw.textbbox((0, 0), watermark, font=font_sub)
            w_w = w_right - w_left
            w_h = w_bottom - w_top
        except:
            w_w, w_h = draw.textsize(watermark, font_sub)
            w_top = 0
            
        icon_size = int(w_h * 1.3)
        total_w = w_w + icon_size + 12
        start_x = (width - total_w) / 2
        w_y = height - w_h - (height * 0.04) # 逼近底边

        # 加载苹果Logo图
        logo_path = PROJECT_ROOT / "apple_logo.png"
        if not logo_path.exists():
            try:
                r = requests.get("https://img.icons8.com/ios-filled/100/000000/mac-os.png", timeout=5)
                if r.status_code == 200:
                    with open(logo_path, "wb") as f: f.write(r.content)
            except: pass
            
        if logo_path.exists():
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                logo_img = logo_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                # 计算精确绝对垂直居中，消除字体排版框本身的内部偏置造成的错位
                center_y = w_y + w_top + (w_h / 2)
                icon_y = int(center_y - (icon_size / 2))
                img.paste(logo_img, (int(start_x), icon_y), mask=logo_img)
            except Exception as e:
                print("水印Logo绘制失败:", e)
                
        # 黑色水印，白底描边增强对比可读性
        try:
            draw.text((start_x + icon_size + 12, w_y), watermark, font=font_sub, fill=(0, 0, 0), stroke_width=2, stroke_fill=(255, 255, 255))
        except TypeError:
            draw.text((start_x + icon_size + 12, w_y), watermark, font=font_sub, fill=(0, 0, 0))

        img.save(image_path, quality=95)
        return True
    except Exception as e:
        print(f"❌ Pillow 进阶版排版失败: {e}")
        return False

def download_and_process_image(url: str, index: int, is_ai: bool = False) -> str | None:
    TEMP_IMG_DIR.mkdir(parents=True, exist_ok=True)
    path = TEMP_IMG_DIR / f"img_{index}.jpg"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        with open(path, 'wb') as f: f.write(r.content)
        with Image.open(path) as img:
            if img.mode != 'RGB': img = img.convert('RGB')
            if not is_ai: # 原图裁剪去指纹
                w, h = img.size
                img = img.crop((IMG_CROP_PIXELS, IMG_CROP_PIXELS, w-IMG_CROP_PIXELS, h-IMG_CROP_PIXELS))
            img.save(path, quality=95)
        return str(path.resolve())
    except Exception as e: 
        print(f"⚠️ 下载图片 {index} 失败: {e}")
        return None

def send_dingtalk_msg(title: str, content: str, img_url: str = None) -> None:
    """推送到钉钉机器人，实现远程无人值守的进度播报"""
    if not DINGTALK_WEBHOOK:
        return
    headers = {'Content-Type': 'application/json'}
    preview_content = content[:150] + "..." if len(content) > 150 else content
    
    markdown_text = f"### 🤖 小红书自动化：待发布审核\n\n**📝 文案标题**：\n{title}\n\n**📄 内容预览**：\n{preview_content}\n\n"
    if img_url:
        markdown_text += f"**🖼️ 首图底板预览**：\n![]({img_url})\n\n"
        
    markdown_text += "> 💡 **提示**：系统已进入 15 分钟等候期。如您不打断，系统将在超时后『自动默许发布全网』！如需重做请立刻关停脚本。"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "小红书待发布审核通知", # 这里面带有"审核"和"通知"等词，可以在群机器人设置安全关键词时使用
            "text": markdown_text
        }
    }
    try:
        requests.post(DINGTALK_WEBHOOK, json=payload, headers=headers, timeout=10)
        print("📨 已成功投递钉钉机器人通知！")
    except Exception as e:
        print(f"⚠️ 钉钉群推送异常: {e}")

def ai_create_content(materials: list[str], search_keyword: str) -> dict | None:
    """文案创作：多源缝合+人设情绪注入"""
    combined_raw = "\n---\n".join(materials)
    persona = random.choice(PERSONA_POOL)
    emotion = random.choice(EMOTION_POOL)
    
    # --- 核心改进：加强洗稿约束 ---
    prompt = f"""
    你现在是小红书百万粉丝的【苹果数码博主】。
    你的人设是：【{persona}】
    你的开场情绪基调：【{emotion}】
    
    请结合下面提供的多篇不同视角的参考资料以及真实用户评论反馈，针对专题【{search_keyword}】进行原创内容缝合创作。
    
    【强制要求】：
    1. 必须完全符合分配给你的人设和基调。结合基调表达你的情绪，严禁生硬。严禁使用过度的烂大街口癖如“家人们”、“绝绝子”。
    2. 结构缝合：融合各篇干货。如果有给出“评论区的痛点反馈”，你【必须】在文中以自问自答或避坑提示的形式解答出来！
    3. 视觉引导：正文分点必须带Emoji数字（1️⃣, 2️⃣...），每段话最多不超过100字，保持呼吸感。
    4. 标题要求：爆款标题党！总字数算上表情符号一定要在20字内。
    5. 封面短标题：根据标题进一步凝练出一个用于图片封面的极简短语（必须控制在10个字以内，最能一击即中痛点，不带任何表情符号，要有强烈的视觉冲击力）。
    6. 结尾【极其重要】：正文的最后间隔一行再另起一行，至少带5个相关热门标签，格式为 #标签1 #标签2 #标签3。

    【海量参考资料及评论反馈池】：
    {combined_raw}

    请严格返回符合 JSON 格式：{{"title": "...", "cover_title": "...", "content": "..."}}
    """
    # ---------------------------
    
    # 尝试 CA
    try:
        print(f"🤖 文案创作：优先尝试 ChatAnywhere ({CA_MODEL})...")
        response = ca_client.chat.completions.create(
            model=CA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        print(f"⚠️ CA 调用失败，正在启动硅基流动 ({SF_TEXT_MODEL}) 托底...")
        try:
            response = sf_client.chat.completions.create(
                model=SF_TEXT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ 文案双线全部失败: {e}")
            return None

def main_workflow() -> None:
    # 每次运行前强行清空历史残留的临时物料
    clean_temp_files()
    
    # --- 核心改进：大模型动态延伸选题 ---
    print("🧠 正在通过大模型脑爆无限新选题...")
    try:
        sample_topics = random.sample(APPLE_TOPICS, 10)
        topic_prompt = f"""
        你是一个资深的苹果数码博主。请你想出一个【绝佳的、极具痛点和吸引力】的小红书苹果/iOS使用技巧选题。
        你可以参考以下已有的选题框架提取灵感，但【必须输出一个全新、独特、高度垂直】的新鲜选题：
        参考框架：{sample_topics}
        
        严格要求：
        1. 只输出选题的核心短语（控制在12个字以内，例如：iPhone快捷视频提取、iPad分屏效率神器等）。
        2. 严禁包含任何标点符号、解释性语句或废话。
        """
        topic_res = sf_client.chat.completions.create(
            model=SF_TEXT_MODEL,
            messages=[{"role": "user", "content": topic_prompt}],
            temperature=0.8
        )
        search_keyword = topic_res.choices[0].message.content.strip()
        search_keyword = re.sub(r'[^\w\u4e00-\u9fa5]', '', search_keyword)
        if not search_keyword:
            raise ValueError("生成选题为空")
        print(f"🌟 AI无尽选题引擎生成了全新选题: {search_keyword}")
    except Exception as e:
        print(f"⚠️ AI选题生成失败，降级使用本地经典题库 ({e})")
        search_keyword = random.choice(APPLE_TOPICS)
    # ----------------------------------------
    
    print(f"🚀 === 任务启动 | 今日选题：{search_keyword} ===")
    history_ids = get_history_ids()

    # 1. 搜索
    results = run_cmd(f'python cdp_publish.py --reuse-existing-tab search-feeds --keyword "{search_keyword}" --sort-by 最多点赞 --note-type 图文')
    if not results or 'feeds' not in results:
        print("❌ 搜索失败。"); return

    # 2. 批量抓取详情以供选择
    print(f"🔍 正在预抓取前 {SEARCH_LIMIT} 条笔记详情以供选择...")
    valid_feeds = []
    unposted_raw = [f for f in results['feeds'] if f.get('id') not in history_ids]
    
    for f in unposted_raw[:SEARCH_LIMIT]:
        f_id = f.get('id')
        # 加上 --load-all-comments 抓取评论痛点
        res = run_cmd(f'python cdp_publish.py --reuse-existing-tab get-feed-detail --feed-id "{f_id}" --xsec-token "{f.get("xsecToken")}" --load-all-comments')
        if res and 'detail' in res and 'note' in res['detail']:
            note = res['detail']['note']
            
            # 兼容处理 comments 可能为 dict 的情况
            comments_data = res['detail'].get('comments', [])
            if isinstance(comments_data, dict):
                comments_list = comments_data.get('comments', []) or comments_data.get('list', [])
            elif isinstance(comments_data, list):
                comments_list = comments_data
            else:
                comments_list = []
                
            title = note.get('title', '').strip()
            desc = note.get('desc', '').strip()
            display_text = title if title else desc.replace('\n', ' ')[:60]
            
            # 提取前 5 条有效评论作为用户痛点反馈
            top_comments = [c.get('content', '').replace('\n', ' ') for c in comments_list[:5] if isinstance(c, dict) and c.get('content')]
            
            valid_feeds.append({
                'id': f_id,
                'note': note,
                'display_text': display_text,
                'top_comments': top_comments
            })

    if not valid_feeds:
        print("⚠️ 专题已发过或无素材。"); return
    
    # --- 核心交互：展示抓取后的真实内容进行选择 ---
    selected_idx = show_selection_dialog(valid_feeds, search_keyword, timeout=20, default_index=0)
    target_data = valid_feeds[selected_idx]
    main_id = target_data['id']
    main_note = target_data['note']
    print(f"🎯 选定目标: {main_id} | {target_data['display_text']}")

    # 3. 整理多源缝合素材
    materials = []
    # 主核心
    materials.append(f"【核心图文对标】\n标题: {main_note.get('title')}\n正文: {main_note.get('desc')}")
    if target_data.get('top_comments'):
         materials.append(f"【核心痛点反馈】该条笔记评论区的真实疑问或吐槽: {', '.join(target_data['top_comments'])}")
    
    # 补充素材视角（缝合剩余几条好的笔记和它们的评论）
    for i, feed in enumerate(valid_feeds[:3]):
        if i != selected_idx:
            materials.append(f"【补充视角参考 {i}】标题: {feed['note'].get('title')} | 摘要: {feed['note'].get('desc')[:100]}...\n【该话题其他评论反馈】: {', '.join(feed.get('top_comments', [])[:3])}")
    
    # 4. 文案合成
    new_post = ai_create_content(materials, search_keyword)
    if not new_post: return

    # 5. 提取图片
    original_images = []
    for img_obj in main_note.get('imageList', []):
        info = img_obj.get('infoList', [])
        if info: original_images.append(info[-1].get('url'))

    # 6. 处理图片组合
    processed_imgs = []
    ai_cover_success = False

    # --- 步骤 A：AI 生成纯净首图背景 (已根据系列化需求替换 Prompt) ---
    cover_title = new_post.get('cover_title', new_post['title'])
    pure_bg_url = generate_silicon_pure_background(theme=cover_title)
    if pure_bg_url:
        p_path = download_and_process_image(pure_bg_url, 0, is_ai=True)
        if p_path:
            # 重新启用并升级了 Pillow 高级排版印字
            if pillow_add_text_to_image(p_path, cover_title):
                processed_imgs.append(p_path)
                ai_cover_success = True
            else:
                # 即使加字失败也用纯背景图托底
                processed_imgs.append(p_path)
                ai_cover_success = True

    # --- 步骤 B：后续步骤直接下载原图图集 (除第一张外，且采用多线程并发下载) ---
    if original_images and len(original_images) > 1:
        print(f"📸 正在并发下载原笔记步骤图集 (第2-{len(original_images)}张)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(download_and_process_image, url, idx + 1, False)
                for idx, url in enumerate(original_images[1:])
            ]
            for future in concurrent.futures.as_completed(futures):
                p = future.result()
                if p: processed_imgs.append(p)

    # 7. 人机审核
    if not ai_cover_success:
        print("🛑 AI 生成纯净首图失败，等待决策...")
        if not show_confirm_box("⚠️ 首图生图失败", "AI无法生成首图背景。\n是否改用【原笔记图集】全套发布？", timeout=20, default=True):
            clean_temp_files() # <--- 保留：点否则清理
            print("❌ 用户中止发布。"); return
        
        # 降级：如果用户同意，把被跳过的第一张原图下载下来补上
        if original_images:
            print("📸 下载原笔记第一张图补上海报...")
            p = download_and_process_image(original_images[0], 0, is_ai=False)
            if p: processed_imgs.insert(0, p) # 插入到最前面
    else:
        print("🔍 首图海报合成成功，等待远程或本机的最终防干扰审核...")
        
        # 核心：触发钉钉远程投递（展示标题、大纲摘要和公网上的AI底图图床）
        send_dingtalk_msg(new_post['title'], new_post['content'], pure_bg_url)
        
        # 本机审核：弹出 3选1 发车确认框，超时15分钟后默认自动发车
        user_choice = show_publish_review_box(
            "🖼️ 最终发车确认", 
            f"专题：{search_keyword}\nAI 图文已生成并推送到您的钉钉。\n若 15 分钟内无任何操作打断，系统将按照您的预设自动起盘发表。\n\n如对稿件内容极度不满意，可点击【红键】强行终止并清场。", 
            timeout=900, 
            default_choice='yes'
        )
        
        if user_choice == 'cancel':
            print("🛑 用户手动打断，中止本次发布流程，深度清理临时物料池...")
            clean_temp_files()
            return
            
        elif user_choice == 'no':
            print("⚠️ 审核由于海报打回：舍弃所生成的封面，正文保留并使用原作者第一图直接发版...")
            if original_images:
                p = download_and_process_image(original_images[0], 0, is_ai=False)
                if p and processed_imgs:
                    processed_imgs[0] = p # 替换掉生成的第一张图
        # ------------------------------------------------
    # 8. 发布
    if not processed_imgs: return
    print(f"📝 准备发布原创作品: {new_post['title']}")
    content_file = TEMP_IMG_DIR / "post.txt"
    with open(content_file, "w", encoding="utf-8") as f: f.write(new_post["content"])
    
    # 重新排序确保顺序正确 img_0, img_1...
    sorted_imgs = sorted(processed_imgs, key=lambda x: int(re.search(r'img_(\d+)', x).group(1)))
    
    imgs_arg = " ".join([f'"{p}"' for p in sorted_imgs])
    publish_cmd = (
        f'python publish_pipeline.py --reuse-existing-tab --auto-publish '
        f'--title "{new_post["title"]}" --content-file "{str(content_file.resolve())}" --images {imgs_arg}'
    )
    run_cmd(publish_cmd)

    # 9. 善后
    save_history_id(main_id)
    print(f"✅ 【{search_keyword}】发布完成！")
    # 清理临时文件
    clean_temp_files()

if __name__ == "__main__":
    main_workflow()