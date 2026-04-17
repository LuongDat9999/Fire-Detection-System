# Fire Detection System

He thong phat hien lua toi gian su dung YOLO PyTorch model `models/best_v3.pt`.

## Tinh nang hien co

- Phat hien lua theo tung frame video
- Ve bounding box va hien thi trang thai co/khong co lua
- Gui canh bao Telegram kem anh frame hien tai
- Ho tro nguon camera hoac file video

## Cau truc du an



## Cai dat nhanh

```bash
cd fire-detection-system
python -m venv .venv
source .venv/bin/activate
pip install ultralytics torch "numpy<2" opencv-python python-dotenv requests
```

## Cau hinh moi truong

```env
MODEL_PATH=models/best_v3.pt
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Chay he thong

Smoke-test truoc khi chay chinh:

```bash
python scripts/smoke_test.py
```

Tuy chon:

```bash
python scripts/smoke_test.py --source 0
python scripts/smoke_test.py --model models/best_v3.pt --source data/videos/warehouse.mp4
```

Chay he thong chinh:

```bash
python src/main.py
```

Tuy chon:

```bash
python src/main.py --source 0
python src/main.py --source data/videos/warehouse.mp4 --no-display
```

## Dieu khien

- `q`: thoat
- `d`: bat/tat man hinh hien thi
- `f`: bat/tat FPS
