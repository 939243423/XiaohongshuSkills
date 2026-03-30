import re
import os
import time
import random
import json
import subprocess
import requests
import glob
import tkinter as tk
from tkinter import messagebox, ttk # <--- 新增 ttk 用于表格展示
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont # <--- 新增 Pillow 用于写字

# ================= 配置区 =================
# 1. 密钥配置
CA_KEY = "xxx"
SILICON_KEY = "xxx"
SEARCH_LIMIT = 5                # 聚合前5条热门笔记的素材

# 初始化客户端
ca_client = OpenAI(api_key=CA_KEY, base_url="https://api.chatanywhere.tech/v1")
sf_client = OpenAI(api_key=SILICON_KEY, base_url="https://api.siliconflow.cn/v1")

# 2. 模型与生图配置
CA_MODEL = "gpt-3.5-turbo"
SF_TEXT_MODEL = "Pro/deepseek-ai/DeepSeek-V3.2"  
IMAGE_MODEL = "Kwai-Kolors/Kolors" # 使用 Kolors 模型

# --- 核心新增：Pillow 字体配置 ---
# 请确保该字体文件放在脚本同级目录下！
# 例如: "AlibabaPuHuiTi-Medium.ttf" 或 "STXihei.ttf" (华文细黑)
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

# 随机选题
SEARCH_KEYWORD = random.choice(APPLE_TOPICS)

# 4. 路径配置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
TEMP_IMG_DIR = os.path.join(PROJECT_ROOT, "temp_downloads")
HISTORY_FILE = os.path.join(PROJECT_ROOT, "published_ids.txt")
IMG_CROP_PIXELS = 2
# ==========================================

def get_history_ids():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_history_id(f_id):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{f_id}\n")

def run_cmd(cmd):
    """正则解析命令行输出的 JSON"""
    try:
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=SCRIPTS_DIR, universal_newlines=False
        )
        stdout_bytes, _ = process.communicate()
        output = stdout_bytes.decode('utf-8', errors='ignore').strip()
        match = re.search(r'(\{.*\})', output, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        return None
    except: return None

def show_confirm_box(title, content, timeout=0, default=True):
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

def show_selection_dialog(valid_feeds, timeout=0, default_index=0):
    """展示带有真实标题和正文预览的选择框"""
    root = tk.Tk()
    root.title("请选择核心对标笔记")
    root.attributes("-topmost", True)
    root.geometry("800x500")

    selected_data = {"index": 0}

    label = tk.Label(root, text=f"专题：{SEARCH_KEYWORD}\n请选择主素材来源（已获取详情内容）：", pady=10)
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

def clean_temp_files():
    """清理临时文件夹"""
    print("🧹 正在清理临时文件...")
    files = glob.glob(os.path.join(TEMP_IMG_DIR, "*"))
    for f in files:
        try:
            os.remove(f)
        except:
            pass

def generate_silicon_pure_background():
    """调用硅基流动生成具有系列化一致性的纯净、带Logo首图背景图"""
    print(f"🎨 硅基动力：正在生成系列化【首图背景】...")
    url = "https://api.siliconflow.cn/v1/images/generations"
    
    # 数码生活桌面特写
    refined_prompt = (
        "竖版构图，9:16 比例。一张干净极简橡木桌子的中景特写。一台 iPhone 16 Pro 和一副 AirPods 整齐地摆放在中心。阳光透过窗户洒下，在桌面和设备上形成错综美观的斑驳叶影。高端生活方式摄影，浅景深，背景优美模糊。温馨、宁静、治愈的氛围。中性色调，8k 分辨率，照片级真实，电影级光影，无文字，画面极其干净且有呼吸感，留有大量留白。"
    )
    # ----------------------------------------
    
    payload = {
        "model": IMAGE_MODEL,
        "prompt": refined_prompt,
        "size": "1024x1024",
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

def pillow_add_text_to_image(image_path, text_content):
    """使用 Pillow 库将标题精准印在图片正中央"""
    print(f"✍️ Pillow 增强：正在首图合成标题【{text_content}】...")
    
    try:
        # 1. 打开图片
        img = Image.open(image_path)
        if img.mode != 'RGB': img = img.convert('RGB')
        draw = ImageDraw.Draw(img)
        width, height = img.size

        # 2. 加载字体 (如果加载失败，降级使用默认字体)
        font_path = os.path.join(PROJECT_ROOT, FONT_FILE)
        if not os.path.exists(font_path):
            print(f"⚠️ 未找到字体文件 {FONT_FILE}，将使用系统默认字体（可能不好看）")
            font = ImageFont.load_default()
            font_size = 40
        else:
            # 根据图片宽度动态计算字体大小 (取图片宽度的 1/15)
            font_size = int(width / 15)
            # 限制标题字数，防止过长超出
            clean_text = text_content[:15] 
            font = ImageFont.truetype(font_path, font_size)

        # 3. 计算文字位置使其居中
        # Pillow 10+ 建议使用 getbbox
        try:
            left, top, right, bottom = draw.textbbox((0, 0), clean_text, font=font)
            text_width = right - left
            text_height = bottom - top
        except:
            # 兼容老版本 Pillow
            text_width, text_height = draw.textsize(clean_text, font=font)

        x = (width - text_width) / 2
        y = (height - text_height) / 2 - (height / 10) # 稍微往上偏一点点，视觉更好

        # 4. 绘制文字 (黑色)
        draw.text((x, y), clean_text, font=font, fill=(0, 0, 0)) # 黑字

        # 5. 保存覆盖
        img.save(image_path, quality=95)
        return True
    except Exception as e:
        print(f"❌ Pillow 合成失败: {e}")
        return False

def download_and_process_image(url, index, is_ai=False):
    if not os.path.exists(TEMP_IMG_DIR): os.makedirs(TEMP_IMG_DIR)
    path = os.path.join(TEMP_IMG_DIR, f"img_{index}.jpg")
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            with open(path, 'wb') as f: f.write(r.content)
            with Image.open(path) as img:
                if img.mode != 'RGB': img = img.convert('RGB')
                if not is_ai: # 原图裁剪去指纹
                    w, h = img.size
                    img = img.crop((IMG_CROP_PIXELS, IMG_CROP_PIXELS, w-IMG_CROP_PIXELS, h-IMG_CROP_PIXELS))
                img.save(path, quality=95)
            return os.path.abspath(path)
    except: pass
    return None

def ai_create_content(materials):
    """文案创作：强力洗稿+爆款重塑"""
    combined_raw = "\n---\n".join([f"参考素材: {m}" for m in materials])
    
    # --- 核心改进：加强洗稿约束 ---
    prompt = f"""
    你现在是小红书百万粉丝的【苹果数码博主】。请针对专题【{SEARCH_KEYWORD}】进行二次创作。
    
    【强制要求】：
    1. 严禁原样照抄素材内容！必须用你专业且略带幽默的口吻重新组织语言。
    2. 结构重塑：提取素材中的干货核心，转化为更易读的保姆级教程。
    3. 视觉引导：正文分点必须带Emoji数字（1️⃣, 2️⃣...），每段话最多不超过100字，保持呼吸感。
    4. 标题要求：必须是标题党！标题总字数算上表情符号一定要在19字内。
    5. 结尾【极其重要】：正文的最后一行至少带5个相关热门标签，格式为 #标签1 #标签2 #标签3。


    【参考素材背景】：
    {combined_raw}

    请输出严格的 JSON 格式：{{"title": "...", "content": "..."}}
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
        except:
            print("❌ 文案双线全部失败。")
            return None

def main_workflow():
    print(f"🚀 === 任务启动 | 今日选题：{SEARCH_KEYWORD} ===")
    history_ids = get_history_ids()

    # 1. 搜索
    results = run_cmd(f'python cdp_publish.py --reuse-existing-tab search-feeds --keyword "{SEARCH_KEYWORD}" --sort-by 最多点赞 --note-type 图文')
    if not results or 'feeds' not in results:
        print("❌ 搜索失败。"); return

    # 2. 批量抓取详情以供选择
    print(f"🔍 正在预抓取前 {SEARCH_LIMIT} 条笔记详情以供选择...")
    valid_feeds = []
    unposted_raw = [f for f in results['feeds'] if f.get('id') not in history_ids]
    
    for f in unposted_raw[:SEARCH_LIMIT]:
        f_id = f.get('id')
        res = run_cmd(f'python cdp_publish.py --reuse-existing-tab get-feed-detail --feed-id "{f_id}" --xsec-token "{f.get("xsecToken")}"')
        if res and 'detail' in res and 'note' in res['detail']:
            note = res['detail']['note']
            title = note.get('title', '').strip()
            desc = note.get('desc', '').strip()
            # 清洗预览文字
            display_text = title if title else desc.replace('\n', ' ')[:60]
            valid_feeds.append({
                'id': f_id,
                'note': note,
                'display_text': display_text
            })

    if not valid_feeds:
        print("⚠️ 专题已发过或无素材。"); return
    
    # --- 核心交互：展示抓取后的真实内容进行选择 ---
    selected_idx = show_selection_dialog(valid_feeds, timeout=20, default_index=0)
    target_data = valid_feeds[selected_idx]
    main_id = target_data['id']
    main_note = target_data['note']
    print(f"🎯 选定目标: {main_id} | {target_data['display_text']}")

    # 3. 整理素材
    materials = [f"标题: {main_note.get('title')}\n内容: {main_note.get('desc')}"]
    
    # 4. 文案合成
    new_post = ai_create_content(materials)
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
    pure_bg_url = generate_silicon_pure_background()
    if pure_bg_url:
        p_path = download_and_process_image(pure_bg_url, 0, is_ai=True)
        if p_path:
            # --- 修改：暂时不用 Pillow 在首图印字 ---
            # if pillow_add_text_to_image(p_path, new_post['title']):
            #     processed_imgs.append(p_path)
            #     ai_cover_success = True
            
            # 直接使用纯净 AI 背景图作为首图
            processed_imgs.append(p_path)
            ai_cover_success = True

    # --- 步骤 B：后续步骤直接下载原图图集 (除第一张外) ---
    if original_images and len(original_images) > 1:
        print(f"📸 正在下载原笔记步骤图集 (第2-{len(original_images)}张)...")
        for idx, url in enumerate(original_images[1:]): 
            p = download_and_process_image(url, idx + 1, is_ai=False)
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
        print("🔍 首图海报合成成功，等待用户审核...")
        print(f"📝 标题预览: {new_post['title']}")
        # --- 修改：审核提示词更新，仅审核背景和 Logo 质量 ---
        if not show_confirm_box("🖼️ 审核首图系列感", f"专题：{SEARCH_KEYWORD}\nAI已生成系列化画册风背景（不带字）。\n满意质感并发布吗（不满意将改用原笔记第一张图）？", timeout=20, default=False):
            print("⚠️ 用户对首图质感不满意，改用原笔记第一张图...")
            if original_images:
                p = download_and_process_image(original_images[0], 0, is_ai=False)
                if p and processed_imgs:
                    processed_imgs[0] = p # 替换掉生成的第一张图
        # ------------------------------------------------
    # 8. 发布
    if not processed_imgs: return
    print(f"📝 准备发布原创作品: {new_post['title']}")
    content_file = os.path.join(TEMP_IMG_DIR, "post.txt")
    with open(content_file, "w", encoding="utf-8") as f: f.write(new_post["content"])
    
    # 重新排序确保顺序正确 img_0, img_1...
    sorted_imgs = sorted(processed_imgs, key=lambda x: int(re.search(r'img_(\d+)', x).group(1)))
    
    imgs_arg = " ".join([f'"{p}"' for p in sorted_imgs])
    publish_cmd = (
        f'python publish_pipeline.py --reuse-existing-tab --auto-publish '
        f'--title "{new_post["title"]}" --content-file "{os.path.abspath(content_file)}" --images {imgs_arg}'
    )
    run_cmd(publish_cmd)

    # 9. 善后
    save_history_id(main_id)
    print(f"✅ 【{SEARCH_KEYWORD}】发布完成！")
    # 清理临时文件
    clean_temp_files()

if __name__ == "__main__":
    main_workflow()