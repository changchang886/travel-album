# AI Travel Album Generator

🎒 扔进来一堆旅行照片 → 自动排版 → 输出可打印的相册 PDF

## Features

- **AI Smart Selection** — 自动筛选：去糊、去重、挑最佳照片
- **Auto Layout** — 优雅的双图/单图排版，带标题和日期
- **Customizable** — 自定义相册标题、照片数量
- **Printable** — 输出标准 A4 PDF，直接送去印刷

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (or it reads from ~/ai-chat-loop/config.yaml)
export DEEPSEEK_API_KEY="sk-..."

# Generate album
python main.py ~/Pictures/tokyo-trip --title "东京之旅"

# Skip AI selection (faster, for testing)
python main.py ~/Pictures/tokyo-trip --title "Tokyo" --no-ai
```

## How It Works

1. 📸 Read all photos from folder
2. 🤖 AI analyzes and selects best shots
3. 📖 Auto-layout into photo album pages
4. 📤 Output printable PDF

## Tech Stack

Python · fpdf2 · OpenAI API · DeepSeek · Pillow
