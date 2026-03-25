import re
import os
import time
import random
import json
import subprocess
import requests
import glob
from openai import OpenAI
from PIL import Image

# ================= 配置区 =================
SEARCH_KEYWORD = "苹果数码技巧"  # 搜索关键词
SEARCH_LIMIT = 5                # 聚合前5条热门笔记的素材

# 2. AI 配置 (ChatAnywhere)
CA_KEY = "xxx"  # <--- 填入你的 Key
client = OpenAI(api_key=CA_KEY, base_url="https://api.chatanywhere.tech/v1")

# 3. 路径配置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
SCRIPTS_DIR = r"{}".format(os.path.join(PROJECT_ROOT, "scripts"))
TEMP_IMG_DIR = r"{}".format(os.path.join(PROJECT_ROOT, "temp_downloads"))

# 【新增】已发布笔记的 ID 记录文件，放在项目根目录
HISTORY_FILE = os.path.join(PROJECT_ROOT, "published_ids.txt")

# 4. 防搬运检测 (Pillow)
IMG_CROP_PIXELS = 2  # 每边裁剪2像素，改变MD5
# ==========================================

def get_history_ids():
    """读取已经发布过的笔记 ID"""
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_history_id(f_id):
    """记录本次发布的 ID，防止下次重复"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{f_id}\n")

def run_cmd(cmd):
    """使用正则表达式从杂乱的日志中精准钓出 JSON 字符串"""
    print(f"正在执行: {cmd}")
    try:
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=SCRIPTS_DIR, universal_newlines=False
        )
        stdout_bytes, stderr_bytes = process.communicate()
        output = stdout_bytes.decode('utf-8', errors='ignore').strip()
        
        match = re.search(r'(\{.*\})', output, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        return None
    except Exception as e:
        print(f"⚠️ 运行异常: {e}")
        return None

def download_and_process_image(url, index):
    """下载图片并修改MD5指纹，返回绝对路径"""
    if not os.path.exists(TEMP_IMG_DIR): os.makedirs(TEMP_IMG_DIR)
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.xiaohongshu.com/"}
    raw_path = os.path.join(TEMP_IMG_DIR, f"raw_{index}.jpg")
    processed_path = os.path.join(TEMP_IMG_DIR, f"proc_{index}.jpg")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            with open(raw_path, 'wb') as f: f.write(response.content)
            with Image.open(raw_path) as img:
                if img.mode != 'RGB': img = img.convert('RGB')
                w, h = img.size
                img_cropped = img.crop((IMG_CROP_PIXELS, IMG_CROP_PIXELS, w - IMG_CROP_PIXELS, h - IMG_CROP_PIXELS))
                img_cropped.save(processed_path, quality=95)
            os.remove(raw_path)
            return os.path.abspath(processed_path)
    except Exception as e:
        print(f"📸 图片处理异常 {index}: {e}")
    return None

def ai_aggregate_and_creative(materials):
    """AI 多素材聚合创作，增加标题字数限制"""
    print("🤖 AI 正在聚合素材并生成原创文案...")
    combined_raw = "\n---\n".join([f"素材{i+1}: {m}" for i, m in enumerate(materials)])
    
    prompt = f"""
    你是一个资深苹果数码博主，擅长分享iPhone/Mac的隐藏技巧。
    请将以下素材，二次创作出一篇全新的【深度合集】笔记。
    
    【硬性约束】：
    1. 标题：必须非常有吸引力，且总长度（含Emoji）严格控制在 20 个汉字以内！
    2. 正文：分点叙述、多用Emoji、末尾加5-8个热门话题标签。
    
    素材集：{combined_raw}
    请直接输出 JSON 格式：{{"title": "...", "content": "..."}}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ AI 生成失败: {e}")
        return None

def main_workflow():
    print(f"🚀 === 任务启动: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 1. 加载发布历史
    history_ids = get_history_ids()

    # 2. 搜索
    search_cmd = f'python cdp_publish.py --reuse-existing-tab search-feeds --keyword "{SEARCH_KEYWORD}" --sort-by 最多点赞 --note-type 图文'
    results = run_cmd(search_cmd)
    
    if not results or 'feeds' not in results:
        print("❌ 搜索失败。")
        return

    # 3. 筛选出没发过的“潜在目标”
    unposted_feeds = [f for f in results['feeds'] if f.get('id') not in history_ids]
    if not unposted_feeds:
        print("⚠️ 搜索结果中的笔记全都发布过了，任务终止。")
        return

    # 确定本次发布的主笔记（提供整套图片的那篇）
    target_main_feed = unposted_feeds[0]
    main_id = target_main_feed.get('id')
    print(f"🎯 本次任务图片来源 ID: {main_id}")

    # 4. 获取详情
    materials = []
    selected_images = []
    
    # 文案参考前5篇（哪怕发过也可以参考文案），但图片必须用 main_id 这一篇
    for i, feed in enumerate(results['feeds'][:SEARCH_LIMIT]):
        f_id = feed.get('id')
        x_token = feed.get('xsecToken')
        
        print(f"🔍 正在提取第 {i+1} 篇素材...")
        detail_cmd = f'python cdp_publish.py --reuse-existing-tab get-feed-detail --feed-id "{f_id}" --xsec-token "{x_token}"'
        res = run_cmd(detail_cmd)
        
        if res and 'detail' in res and 'note' in res['detail']:
            note_data = res['detail']['note']
            materials.append(f"标题: {note_data.get('title')}\n正文: {note_data.get('desc')}")
            
            # 关键：只在匹配到 main_id 时下载全套图集
            if f_id == main_id:
                img_list = note_data.get('imageList', [])
                for img_obj in img_list:
                    info_list = img_obj.get('infoList', [])
                    if info_list:
                        selected_images.append(info_list[-1].get('url'))
                print(f"📸 已锁定目标图集：{len(selected_images)} 张图片")

    if not materials or not selected_images:
        print("❌ 素材或图集提取失败")
        return

    # 5. AI 合成
    new_post = ai_aggregate_and_creative(materials)
    if not new_post: return

    # 6. 下载处理图片
    processed_imgs = []
    for idx, url in enumerate(selected_images[:9]):
        p = download_and_process_image(url, idx)
        if p: processed_imgs.append(p)

    if not processed_imgs: return

    # 7. 发布
    print(f"📝 准备发布原创作品: {new_post['title']}")
    content_file_path = os.path.join(TEMP_IMG_DIR, "post_content.txt")
    with open(content_file_path, "w", encoding="utf-8") as f:
        f.write(new_post["content"])
    
    imgs_arg = " ".join([f'"{p}"' for p in processed_imgs])
    publish_cmd = (
        f'python publish_pipeline.py --reuse-existing-tab --auto-publish '
        f'--title "{new_post["title"]}" --content-file "{os.path.abspath(content_file_path)}" --images {imgs_arg}'
    )
    
    run_cmd(publish_cmd)
    
    # 8. 记录历史并清理
    save_history_id(main_id)
    print(f"✅ 已记录 ID {main_id} 到已发布列表。")

    print("🧹 清理临时文件...")
    files = glob.glob(os.path.join(TEMP_IMG_DIR, "*"))
    for f in files: 
        try: os.remove(f)
        except: pass
    print("✅ === 全部流程结束 ===")

if __name__ == "__main__":
    time.sleep(random.randint(2, 5))
    main_workflow()