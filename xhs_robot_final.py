import re
import os
import random
import json
import subprocess
import requests
import shutil
import concurrent.futures
from datetime import datetime, timedelta
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
    "省吃俭用热衷免费薅羊毛特性的打工人",
    "追求极致效率的极简主义达人",
    "爱抬杠但总能说到点子上的数码老炮",
    "主打‘陪伴式’自用的数码博主",
    "毒舌但真实的硬件测评人"
]

EMOTION_POOL = [
    "开篇必须要吐槽一个痛点",
    "开篇要表现得非常激动，觉得大家不知道太可惜了",
    "开头要表现出对某些反人类交互设计感到非常无语",
    "充满分享欲，像老朋友聊天一样自然引入",
    "开篇先自嘲一下自己之前的蠢操作",
    "带着一种‘发现新大陆’的神秘感切入",
    "非常淡定地甩出一个冷知识"
]
# ---------------------------------------------

# 4. 路径配置
TEMP_IMG_DIR = PROJECT_ROOT / "temp_downloads"
HISTORY_FILE = PROJECT_ROOT / "published_ids.txt"
IMG_CROP_PIXELS = 2
USE_HEADLESS = False             # 是否使用无头模式运行浏览器

# 5. 智能调度配置
DATA_DIR = PROJECT_ROOT / "data"
PERFORMANCE_LOG_FILE = DATA_DIR / "performance_log.json"
GOLDEN_HOURS = [8, 12, 18, 20, 21]   # 小红书流量高峰时段
ENABLE_SMART_SCHEDULE = True          # 是否启用黄金时段定时发布
SMART_TOPIC_EXPLORE_RATIO = 0.2      # 20% 概率探索新品类
# ==========================================

def get_history_ids() -> set[str]:
    if not HISTORY_FILE.exists(): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_history_id(f_id: str) -> None:
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{f_id}\n")

# ================= 数据持久化层 =================
def _ensure_data_dir() -> None:
    """确保 data 目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_performance_log() -> list[dict]:
    """读取发布效果日志"""
    if not PERFORMANCE_LOG_FILE.exists():
        return []
    try:
        with open(PERFORMANCE_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ 读取发布日志失败: {e}")
        return []

def save_performance_log(log: list[dict]) -> None:
    """保存发布效果日志"""
    _ensure_data_dir()
    with open(PERFORMANCE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def append_performance_record(record: dict) -> None:
    """追加一条发布记录"""
    log = load_performance_log()
    log.append(record)
    save_performance_log(log)

def _get_interaction_score(metrics: dict | None) -> float:
    """根据互动数据计算综合得分（点赞×1 + 收藏×2 + 评论×3）"""
    if not metrics or not isinstance(metrics, dict):
        return 0.0
    # 兼容后端返回的中文/英文 Key
    like = metrics.get("like", metrics.get("点赞", 0)) or 0
    fav = metrics.get("fav", metrics.get("收藏", 0)) or 0
    comment = metrics.get("comment", metrics.get("评论", 0)) or 0
    return float(like + fav * 2 + comment * 3)

def _classify_topic_category(topic: str) -> str:
    """将一个选题短语映射到 APPLE_TOPICS_DICT 的品类 key"""
    for category, topics in APPLE_TOPICS_DICT.items():
        for t in topics:
            # 模糊匹配：选题包含品类中某个条目的关键词
            if t in topic or topic in t:
                return category
    # 未匹配到的归到通用品类
    return "其他"

# ================= 智能选题策略 =================
def smart_pick_topic() -> tuple[str, str]:
    """
    数据驱动的智能选题。
    返回 (品类名, 选题关键词)。
    80% 概率选历史表现最佳品类，20% 随机探索。
    """
    log = load_performance_log()
    scored_records = [r for r in log if r.get("metrics") and _get_interaction_score(r.get("metrics")) > 0]
    
    if len(scored_records) < 3:
        # 数据不足，降级为纯随机
        print("📊 [智能选题] 历史数据不足（<3条），使用随机品类")
        category = random.choice(list(APPLE_TOPICS_DICT.keys()))
        return category, _ai_generate_topic_from_category(category)
    
    # 统计每个品类的平均互动得分
    category_scores: dict[str, list[float]] = {}
    for r in scored_records:
        cat = r.get("category", "其他")
        score = _get_interaction_score(r.get("metrics"))
        category_scores.setdefault(cat, []).append(score)
    
    category_avg = {cat: sum(scores) / len(scores) for cat, scores in category_scores.items()}
    
    # 补充从未发布过的品类（给予基础分数以便探索）
    all_categories = list(APPLE_TOPICS_DICT.keys())
    base_score = max(category_avg.values()) * 0.3 if category_avg else 1.0
    for cat in all_categories:
        if cat not in category_avg:
            category_avg[cat] = base_score
    
    # 80/20 策略
    if random.random() < SMART_TOPIC_EXPLORE_RATIO:
        # 探索：随机选择
        category = random.choice(all_categories)
        print(f"🔬 [智能选题] 探索模式 → 随机品类：{category}")
    else:
        # 开发：按得分加权随机
        cats = list(category_avg.keys())
        weights = [max(0.1, category_avg[c]) for c in cats]
        category = random.choices(cats, weights=weights, k=1)[0]
        print(f"📈 [智能选题] 开发模式 → 高权重品类：{category} (avg={category_avg[category]:.1f})")
    
    return category, _ai_generate_topic_from_category(category)

def _ai_generate_topic_from_category(category: str) -> str:
    """在指定品类下用 AI 生成一个新鲜选题"""
    category_topics = APPLE_TOPICS_DICT.get(category, APPLE_TOPICS)
    sample = random.sample(category_topics, min(5, len(category_topics)))
    try:
        topic_prompt = f"""
        你是一个资深的苹果数码博主。请你在【{category}】这个品类下，想出一个【绝佳的、极具痛点和吸引力】的小红书苹果/iOS使用技巧选题。
        你可以参考以下已有的选题框架提取灵感，但【必须输出一个全新、独特、高度垂直】的新鲜选题：
        参考框架：{sample}
        
        严格要求：
        1. 只输出选题的核心短语（控制在12个字以内）。
        2. 严禁包含任何标点符号、解释性语句或废话。
        """
        topic_res = sf_client.chat.completions.create(
            model=SF_TEXT_MODEL,
            messages=[{"role": "user", "content": topic_prompt}],
            temperature=0.85
        )
        keyword = topic_res.choices[0].message.content.strip()
        keyword = re.sub(r'[^\w\u4e00-\u9fa5]', '', keyword)
        if keyword:
            return keyword
    except Exception as e:
        print(f"⚠️ AI品类选题失败: {e}")
    return random.choice(category_topics)

# ================= 文案风格动态进化 =================
def smart_pick_style() -> tuple[str, str]:
    """
    根据历史数据选择最优的 (人设, 情绪) 组合。
    表现好的组合权重更高，但保留探索性。
    """
    log = load_performance_log()
    scored_records = [r for r in log if r.get("metrics") and _get_interaction_score(r.get("metrics")) > 0]
    
    if len(scored_records) < 3:
        print("🎭 [风格进化] 历史数据不足，使用随机风格")
        return random.choice(PERSONA_POOL), random.choice(EMOTION_POOL)
    
    # 统计每个 (persona, emotion) 组合的平均得分
    combo_scores: dict[tuple[str, str], list[float]] = {}
    for r in scored_records:
        key = (r.get("persona", ""), r.get("emotion", ""))
        if key[0] and key[1]:
            score = _get_interaction_score(r.get("metrics"))
            combo_scores.setdefault(key, []).append(score)
    
    if not combo_scores:
        return random.choice(PERSONA_POOL), random.choice(EMOTION_POOL)
    
    # 构建全量组合池（含未使用过的）
    all_combos = [(p, e) for p in PERSONA_POOL for e in EMOTION_POOL]
    combo_avg = {k: sum(v) / len(v) for k, v in combo_scores.items()}
    base_score = max(combo_avg.values()) * 0.4 if combo_avg else 1.0
    
    weights = []
    for combo in all_combos:
        weights.append(max(0.1, combo_avg.get(combo, base_score)))
    
    chosen = random.choices(all_combos, weights=weights, k=1)[0]
    avg_display = combo_avg.get(chosen, base_score)
    print(f"🎭 [风格进化] 选择组合：人设='{chosen[0][:6]}...' 情绪='{chosen[1][:6]}...' (avg={avg_display:.1f})")
    return chosen

# ================= 发布时间优化 =================
def get_optimal_publish_time(offset_index: int = 0) -> str | None:
    """
    计算最优发布时间。
    offset_index: 如果要批量发布，可以指定偏移量（如 0 为最近的，1 为再下一个）。
    如果 offset_index 为 0 且当前在黄金窗口(±30min)内，返回 None（立即发布）。
    否则返回对应的第 (offset_index + 1) 个黄金时段的 'yyyy-MM-dd HH:mm' 字符串。
    """
    if not ENABLE_SMART_SCHEDULE:
        return None
    
    now = datetime.now()
    
    # 查找未来的黄金时段
    future_slots = []
    # 检查今天
    for gh in sorted(GOLDEN_HOURS):
        target = now.replace(hour=gh, minute=0, second=0, microsecond=0)
        if target > now:
            # 如果是最近一个且在 30min 窗口内，标记为“立即”
            diff_minutes = (target - now).total_seconds() / 60
            if offset_index == 0 and diff_minutes <= 30:
                # 注意：已经过了 30min 的话已经在上面 target > now 过滤掉了
                # 这里 diff_minutes 其实是正值且 <= 30
                pass 
            future_slots.append(target)
            
    # 如果未来时段不够，补充明天的、后天的
    days_offset = 1
    while len(future_slots) <= offset_index + 1:
        for gh in sorted(GOLDEN_HOURS):
            target = (now + timedelta(days=days_offset)).replace(hour=gh, minute=0, second=0, microsecond=0)
            future_slots.append(target)
        days_offset += 1
        if days_offset > 7: break # 安全边界

    # 特殊情况：如果是第一个且在窗口内
    if offset_index == 0:
        for gh in GOLDEN_HOURS:
            target = now.replace(hour=gh, minute=0, second=0, microsecond=0)
            if abs((now - target).total_seconds()) / 60 <= 30:
                print(f"⏰ [智能调度] 当前处于黄金窗口 {gh}:00，立即发布第 1 篇")
                return None

    target_slot = future_slots[offset_index]
    post_time = target_slot.strftime("%Y-%m-%d %H:%M")
    print(f"⏰ [智能调度] 第 {offset_index + 1} 篇定时到：{post_time}")
    return post_time

# ================= 效果回查闭环 =================
def backfill_performance_metrics() -> None:
    """
    扫描 performance_log 中 metrics=null 且发布超过 24h 的记录，
    通过 content-data API 回填真实互动数据。
    """
    log = load_performance_log()
    pending = [
        (i, r) for i, r in enumerate(log)
        if r.get("metrics") is None and r.get("published_at")
    ]
    
    if not pending:
        return
    
    # 筛选超过 24h 的记录
    now = datetime.now()
    stale = []
    for i, r in pending:
        try:
            pub_time = datetime.strptime(r["published_at"], "%Y-%m-%d %H:%M")
            if (now - pub_time).total_seconds() > 24 * 3600:
                stale.append((i, r))
        except ValueError:
            continue
    
    if not stale:
        print(f"📊 [效果回查] {len(pending)} 条待回查记录均未满 24h，跳过")
        return
    
    print(f"📊 [效果回查] 正在回查 {len(stale)} 条超过 24h 的笔记数据...")
    
    headless_arg = "--headless" if USE_HEADLESS else ""
    # 拉取最新的内容数据（一次拉最多 50 条以覆盖近期发布）
    result = run_cmd(
        f'python cdp_publish.py {headless_arg} --reuse-existing-tab content-data --page-size 50',
        timeout=120
    )
    
    if not result or 'rows' not in result:
        print("⚠️ [效果回查] content-data 拉取失败，跳过本次回查")
        return
    
    rows = result['rows']
    updated_count = 0
    
    for idx, record in stale:
        title = record.get("title", "")
        if not title:
            continue
        
        # 按标题模糊匹配
        matched_row = None
        for row in rows:
            row_title = row.get("标题", "")
            if row_title and (title in row_title or row_title in title):
                matched_row = row
                break
        
        if matched_row:
            metrics = {
                "impression": matched_row.get("曝光", 0),
                "like": matched_row.get("点赞", 0),
                "fav": matched_row.get("收藏", 0),
                "comment": matched_row.get("评论", 0),
                "share": matched_row.get("分享", 0),
            }
            log[idx]["metrics"] = metrics
            score = _get_interaction_score(metrics)
            print(f"  ✅ 回填成功：{title[:15]}... → 得分={score:.0f}")
            updated_count += 1
    
    if updated_count > 0:
        save_performance_log(log)
        print(f"📊 [效果回查] 本次共回填 {updated_count} 条记录")

def run_cmd(cmd: str, timeout: int = 120, retries: int = 1) -> dict | None:
    """正则解析命令行输出的 JSON，包含超时机制与自动重试逻辑"""
    for attempt in range(retries + 1):
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
                if attempt < retries:
                    print(f"🔄 [run_cmd] 正在进行第 {attempt + 1} 次重试...")
                    continue
                return None
            
            output = stdout_bytes.decode('utf-8', errors='ignore').strip()
            match = re.search(r'(\{.*\})', output, re.DOTALL)
            if match:
                try: 
                    return json.loads(match.group(1))
                except Exception as e: 
                    print(f"⚠️ [run_cmd] JSON解析失败: {e}")
            
            # 如果没匹配到 JSON 或解析失败，视情况重试
            if attempt < retries:
                print(f"🔄 [run_cmd] 未获取有效结果，正在进行第 {attempt + 1} 次重试...")
                continue
            return None
        except Exception as e: 
            print(f"❌ [run_cmd] 执行异常: {e}")
            if attempt < retries:
                continue
            return None
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

    我们要突破想象力，但【核心视觉元素必须与“{theme}”紧密相关】。
    
    任务逻辑：
    1. 识别主题【{theme}】中的核心实体（如：iPhone, Apple Watch, AirPods, MacBook, iPad, 或特定的软件功能界面）。
    2. 如果主题涉及特定硬件（如手表、耳机），画面主角必须是该硬件，严禁千篇一律地使用手机。
    3. 如果主题涉及特定操作（如洗手、听歌、拍照、充电），请在画面中加入具象的、高质感的环境暗示（如：晶莹的水滴、跳动的声波、柔和的光晕、编织质感的充电线）。
    
    推荐风格示例（随机选择或融合）：
    - 【写实产品艺术】：极致细节的硬件特写（镜头玻璃的反射、拉丝金属的质感），配合丁达尔光影，营造高端商业摄影感。
    - 【C4D 场景模拟】：将硬件置于超现实的纯净空间，周围点缀着与主题相关的 3D 抽象元素（如悬浮的海带状波纹、极简的几何发光体）。
    - 【治愈数码生活】：极简、高亮度的干净桌面桌面局部，光线透过窗帘撒在设备上，画面纯净有呼吸感。
    - 【未来主义光效】：用细微的荧光线条勾勒出设备的轮廓，光流代表数据或能量的传递。

    严格要求：
    1. 画面主体必须让观众一眼能联感到“高端苹果生态、智能、精致”。
    2. 只输出一段极度具体、画面感极强的图像描述（MJ/Prompt 风格），不要超过 200 个字。严禁废话。
    3. 必须包含：画面主体、材质细节、环境光影、背景干净度（强调为排版留放文字空间）。
    """
    
    try:
        res = sf_client.chat.completions.create(
            model=SF_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt_brainstorm}],
            temperature=0.9
        )
        ai_generated_prompt = res.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ 动态 prompt 生成失败，降级为经典底图: {e}")
        ai_generated_prompt = "极简高质感底图。正中央放置高科技数码设备的质感局部特写，比如新款手机或手表的精致材质边缘。柔和且纯净的影棚光，画面有极大的干净留白区域用于文字排版，色调温润如星光色或太空灰。"

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

def ai_create_content(materials: list[str], search_keyword: str, persona: str | None = None, emotion: str | None = None) -> dict | None:
    """文案创作：多源缝合+人设情绪注入（支持外部传入智能选择的风格）"""
    combined_raw = "\n---\n".join(materials)
    persona = persona or random.choice(PERSONA_POOL)
    emotion = emotion or random.choice(EMOTION_POOL)
    
    # --- 核心改进：加强洗稿约束 ---
    prompt = f"""
    你现在是小红书百万粉丝的【苹果数码博主】。
    你的人设是：【{persona}】
    你的开场情绪基调：【{emotion}】
    
    请结合下面提供的多篇不同视角的参考资料以及真实用户评论反馈，针对专题【{search_keyword}】进行原创内容缝合创作。
    
    【强制要求】：
    1. 必须完全符合分配给你的人设和基调。结合基调表达你的情绪，严禁生硬。严禁使用过度的烂大街口癖如“家人们”、“绝绝子”。
    2. 结构缝合：融合各篇干货。如果有给出“评论区的痛点反馈”，你应以自然融入的方式解答（比如：‘看到有人说...其实...’），不要总是用死板的问答格式。
    3. 视觉引导：**严禁每一段都使用 1️⃣2️⃣3️⃣ 等固定数字开头**。请灵活混合使用：
       - 加粗小标题
       - 符号点（如 ✅, ✨, 💡, 📌 等）
       - 或者直接分段，让文章看起来有呼吸感且不像说明书。
    4. 句式多样化：每段话的长短要错落有致，避免整齐划一的排比句。严禁使用“总之”、“综上所述”等AI感明显的总结词。
    5. 标题要求：爆款标题党！总字数算上表情符号一定要在20字内。
    6. 封面短标题：根据标题进一步凝练出一个用于图片封面的极简短语（必须控制在10个字以内，最能一击即中痛点，不带任何表情符号，要有强烈的视觉冲击力）。
    7. 结尾【极其重要】：正文的最后间隔一行再另起一行，至少带5个相关热门标签，格式为 #标签1 #标签2 #标签3。

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

def main_workflow(count: int = 1) -> None:
    """
    主工作流。
    count: 连续生成并发布的篇数。
    """
    for i in range(count):
        if i > 0:
            # 批量发布时，每篇之间休息 5-15 分钟模拟真人
            rest_minutes = random.randint(5, 15)
            print(f"\n🛌 [批量模式] 已完成第 {i} 篇，休息 {rest_minutes} 分钟后开始下一篇...")
            time.sleep(rest_minutes * 60)

        print(f"\n🎬 === 开始执行第 {i+1}/{count} 篇发布任务 ===")
        _single_note_workflow(index_in_batch=i)

def _single_note_workflow(index_in_batch: int = 0) -> None:
    # 每次运行前强行清空历史残留的临时物料
    clean_temp_files()
    
    # --- 效果回查闭环：回填历史笔记的真实互动数据 ---
    print("📊 === 效果回查：扫描待回填的历史笔记 ===")
    backfill_performance_metrics()
    
    # --- 智能选题：数据驱动的品类选择 + AI 生成新鲜选题 ---
    print("🧠 === 智能选题引擎启动 ===")
    topic_category, search_keyword = smart_pick_topic()
    print(f"🌟 选题结果：品类=[{topic_category}] 关键词=[{search_keyword}]")
    
    # --- 风格进化：选择最优人设+情绪组合 ---
    chosen_persona, chosen_emotion = smart_pick_style()
    
    print(f"🚀 === 任务启动 | 今日选题：{search_keyword} ===")
    history_ids = get_history_ids()

    # 1. 搜索
    headless_arg = "--headless" if USE_HEADLESS else ""
    results = run_cmd(
        f'python cdp_publish.py {headless_arg} --reuse-existing-tab search-feeds --keyword "{search_keyword}" --sort-by 最多点赞 --note-type 图文',
        timeout=180, retries=2
    )
    if not results or 'feeds' not in results:
        print("❌ 搜索失败。"); return

    # 2. 批量抓取详情以供选择
    print(f"🔍 正在预抓取前 {SEARCH_LIMIT} 条笔记详情以供选择...")
    valid_feeds = []
    unposted_raw = [f for f in results['feeds'] if f.get('id') not in history_ids]
    
    for f in unposted_raw[:SEARCH_LIMIT]:
        f_id = f.get('id')
        # 加上 --load-all-comments 抓取评论痛点，且给 180s 宽裕时间
        res = run_cmd(
            f'python cdp_publish.py {headless_arg} --reuse-existing-tab get-feed-detail --feed-id "{f_id}" --xsec-token "{f.get("xsecToken")}" --load-all-comments',
            timeout=180
        )
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
    new_post = ai_create_content(materials, search_keyword, persona=chosen_persona, emotion=chosen_emotion)
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
    # 8. 发布（含智能时间调度）
    if not processed_imgs: return
    print(f"📝 准备发布原创作品: {new_post['title']}")
    content_file = TEMP_IMG_DIR / "post.txt"
    with open(content_file, "w", encoding="utf-8") as f: f.write(new_post["content"])
    
    # 重新排序确保顺序正确 img_0, img_1...
    sorted_imgs = sorted(processed_imgs, key=lambda x: int(re.search(r'img_(\d+)', x).group(1)))
    
    # 智能发布时间调度
    optimal_time = get_optimal_publish_time(offset_index=index_in_batch)
    post_time_arg = f'--post-time "{optimal_time}"' if optimal_time else ""
    
    imgs_arg = " ".join([f'"{p}"' for p in sorted_imgs])
    publish_cmd = (
        f'python publish_pipeline.py {headless_arg} --reuse-existing-tab --auto-publish '
        f'{post_time_arg} '
        f'--title "{new_post["title"]}" --content-file "{str(content_file.resolve())}" --images {imgs_arg}'
    )
    run_cmd(publish_cmd)

    # 9. 善后：保存发布记录到性能日志（用于智能选题和风格进化）
    published_at = optimal_time or datetime.now().strftime("%Y-%m-%d %H:%M")
    append_performance_record({
        "id": main_id,
        "title": new_post.get("title", ""),
        "topic": search_keyword,
        "category": topic_category,
        "persona": chosen_persona,
        "emotion": chosen_emotion,
        "published_at": published_at,
        "metrics": None  # 将由 backfill_performance_metrics() 在 24h 后回填
    })
    
    save_history_id(main_id)
    print(f"✅ 【{search_keyword}】发布完成！策略数据已记录。")
    # 清理临时文件
    clean_temp_files()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Xiaohongshu AI Robot")
    parser.add_argument("--count", type=int, default=1, help="一次运行生成的篇数 (默认: 1)")
    args = parser.parse_args()
    
    main_workflow(count=args.count)