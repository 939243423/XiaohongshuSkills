# 小红书自动化脚本执行指南

本仓库提供了两套核心自动化脚本，用于实现小红书内容的智能选题、素材采集、AI创作及自动发布工作流。

## 1. 核心脚本概览

### 🚀 `xhs_robot_final.py` (单次任务执行器)
这是整个自动化的核心逻辑脚本。它会执行以下完整闭环：
- **智能选题**: 从预设的苹果技巧矩阵中随机抽取热点专题。
- **素材采集**: 自动在小红书搜索相关热门笔记，并抓取前 5 条详情供参考。
- **AI 创作**:
    - 使用 **ChatAnywhere** 或 **SiliconFlow (DeepSeek-V3)** 强力洗稿并重塑爆款文案。
    - 使用 **SiliconFlow (Kolors)** 生成高质感系列化首图背景。
- **人机交互**: 
    - 弹出 GUI 界面供用户从 5 条参考素材中选定核心对标对象。
    - 弹出预览确认框，用户可审核 AI 生成的首图质感及文案，支持一键降级使用原图。
- **自动发布**: 调用 `publish_pipeline.py` 完成真实的 CDP 自动化发布。

### ⏰ `run_scheduler.py` (定时任务调度器)
该脚本是 `xhs_robot_final.py` 的守护进程：
- **执行逻辑**: 启动后立即运行一次 `xhs_robot_final.py`。
- **循环机制**: 每隔 **6 小时** 自动唤起一次任务，实现全天候稳定产出。
- **终止方式**: 随时在控制台通过 `Ctrl + C` 停止调度。

---

## 2. 环境准备与配置

### 依赖安装
确保已安装 `requirements.txt` 中的所有依赖，并配置好 Python 虚拟环境：
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 关键配置项
打开 `xhs_robot_final.py` 检查以下配置：
- **API 密钥**:
    - `CA_KEY`: ChatAnywhere 密钥。
    - `SILICON_KEY`: SiliconFlow 密钥（用于 DeepSeek 文案和 Kolors 生图）。
- **字体文件**:
    - 本地需存放 `AlibabaPuHuiTi-3-65-Medium.ttf` 字体文件，用于首图文字合成。

---

## 3. 执行方法

### 方案 A：手动执行单次任务 (含交互)
如果您希望手动触发并参与选题确认：
```powershell
python xhs_robot_final.py
```
*执行期间会弹出 TKinter 窗口，请注意关注桌面弹出的交互框。*

### 方案 B：后台挂机自动循环 (每日 4 篇)
如果您希望完全自动化运行：
```powershell
python run_scheduler.py
```
*调度器会始终保持运行，并按照预设的时间间隔（6小时）自动循环。*

---

## 4. 注意事项
1. **浏览器环境**: 本脚本依赖底层 `cdp_publish.py` 驱动的 Chrome 环境，请确保 Chrome Profile 已登录小红书账号且路径配置正确（参考 `config/accounts.json`）。
2. **临时文件**: 脚本运行过程中产生的临时素材会存放在 `temp_downloads/` 目录，并在单次任务结束后自动清理。
3. **交互超时**: 为防止无人值守时卡死，重要的弹窗均设有 **20秒** 超时机制，超时后将应用默认选项（通常为“是”或“首条素材”）继续流程。
