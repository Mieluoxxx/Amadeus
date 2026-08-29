# macOS 部署

Amadeus 的官方基线是 Windows 11 + CUDA 12.4。macOS 处于社区支持状态：
对话内核（T1）与远程语音（T2a）可用；本地 CUDA 语音（T2b）与壁纸模式（T3）
为 Windows 专属。

## 快速开始

```bash
git clone <repo> && cd amadeus
python3 tools/setup.py --tier voice   # 纯文字用默认 --tier core 即可
# 编辑 .env：至少填 DEEPSEEK_API_KEY；远程 TTS 见 .env 内 MiMo/OpenAI 段
./run_electron_macos.sh
```

环境体检：`python3 tools/setup.py --check`

## 梯级与依赖

| 梯级 | 能力 | 安装 |
|---|---|---|
| T1 core | Chat / Work / Provider / AUIP / 角色渲染 | `tools/setup.py`（默认）|
| T2a voice | 远程 TTS/ASR、播放、口型、barge-in | `tools/setup.py --tier voice`（macOS 需 brew portaudio）|
| T2b local-cu124 | 本地 GPT-SoVITS / Qwen3-ASR | 仅 CUDA 平台 |
| T3 wallpaper | 桌面壁纸模式 | 仅 Windows |

## 已知边界

- 无 CUDA 本地语音（Apple Silicon 无 CUDA；T2b 不适用）
- 壁纸模式按钮在非 Windows 置灰；后端对 `wallpaper.start` 返回
  `wallpaper_unsupported_platform`
- VN Player / VTS 未经 macOS 验证

## 排障表（实测踩坑记录）

| 症状 | 原因 | 解法 |
|---|---|---|
| `npm ci` 在 postinstall 失败 | Electron 二进制下载被墙 | 脚本已自动用 npmmirror 重试；手工：`ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ npm ci` |
| `port 17777 is owned by another backend instance` | 残留后端进程 | `lsof -nP -iTCP:17777 -sTCP:LISTEN` 查 PID 杀掉 |
| Electron 加载了错误的页面 | 5173 被其他 vite 项目占用 | 同上查 5173；`run_electron_macos.sh` 启动前会自动检测 |
| 语音 401 | `.env` 的 key 带引号/空白 | 已自动容错（secret 读取去引号）；仍失败则检查 key 本身 |
| 角色说话时「interrupted by user」 | AEC 未校准，自己的声音触发 barge-in | `.env` 设 `AEC_REALTIME_BARGE_IN=false` |
| `pip install` 卡在 pyaudio 编译 | 缺 portaudio | `brew install portaudio`（voice 梯级脚本会自动处理）|
