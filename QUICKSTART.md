# Quick Start

## 1) Cai dat

```bash
cd fire-detection-system
python -m venv .venv
source .venv/bin/activate
pip install ultralytics torch "numpy<2" opencv-python python-dotenv requests
```

## 2) Chinh .env

```env
MODEL_PATH=models/best_v3.pt
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
VIDEO_SOURCE=data/videos/warehouse.mp4
```

## 3) Smoke-test nhanh

```bash
python scripts/smoke_test.py
```

Tuy chon:

```bash
python scripts/smoke_test.py --source 0
python scripts/smoke_test.py --model models/best_v3.pt --source data/videos/warehouse.mp4
```

## 4) Chay

```bash
python src/main.py
```

## 5) Phim tat

- `q`: thoat
- `d`: bat/tat hien thi
- `f`: bat/tat FPS

## 6) Loi thuong gap

- Khong load duoc model: kiem tra duong dan `models/best_v3.pt`.
- Khong gui duoc Telegram: kiem tra token/chat id va ket noi mang.
- Khong mo duoc video: kiem tra `VIDEO_SOURCE` hop le.
