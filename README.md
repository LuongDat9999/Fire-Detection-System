# Fire Detection System

Hệ thống AI giám sát và cảnh báo cháy theo thời gian thực, kết hợp:
- Computer Vision (YOLOv26) để phát hiện nguy cơ cháy trên video stream và camera webcam.
- Quản lý trạng thái Runtime (state management) để tránh spam cảnh báo và theo dõi xu hướng.
- Telegram Bot + LLM để tương tác bằng ngôn ngữ tự nhiên (tạm dừng, kiểm tra trạng thái, xem camera, theo dõi sát).

## 1) Giới thiệu

Trong các khu vực nhà kho, xưởng, bếp công nghiệp hoặc điểm có nguy cơ cháy cao:
- Con người không thể theo dõi camera liên tục 24/7.
- Cảnh báo thủ công thường chậm và dễ bỏ sót.
- Tín hiệu cảnh báo quá nhiều gây "mệt mỏi cảnh báo" (alert fatigue).

Mục tiêu của dự án:
- Phát hiện nhanh nguy cơ cháy từ camera/video.
- Gửi cảnh báo có bằng chứng hình ảnh đến Telegram.
- Cho phép người trực thao tác ngay trên tin nhắn: tạm dừng cảnh báo, yêu cầu theo dõi sát hơn, kiểm tra trạng thái.

## 2) Phạm vi và Trường hợp sử dụng
Trong phạm vi hiện tại:
- Nhận diện nguy cơ cháy trên khung hình video bằng mô hình YOLOv26 được train từ 2 tập dữ liệu gồm hơn 15k hình ảnh được lấy trên roboflow với 2 class là: ["fire", "smoke"] với độ chính xác 89%.
- Cơ chế xác nhận cháy theo thời gian không báo ngay khi có khung hình nhiễu
- Gửi cảnh báo Telegram kèm ảnh và nút hành động trên khung chat.
- LLM phân loại ý định người dùng trong chat Telegram được dùng là mô hình llama-3.1-8b-instant.

Ngoài phạm vi (chưa triển khai đầy đủ trong repo này):
- Tích hợp trực tiếp tổng đài 114/911.
- Lưu trữ lịch sử cảnh báo vào database/BI dashboard.
- Cơ chế đa camera quản trị tập trung.

## 3) Giá trị nghiệp vụ kỳ vọng
- Giảm thời gian phát hiện sự cố sớm hơn so với giám sát thủ công.
- Tăng phạm vi giám sát bằng cách sử dụng camera thay vì các thiết bị sensor truyền thống
- Tăng tốc độ phản ứng của đội trực (nhận cảnh báo + có ảnh chứng minh).
- Giảm cảnh báo giả nhờ cơ chế xác nhận (confirmation) và quản lý trạng thái.
- Tăng khả năng vận hành nhờ giao tiếp bằng ngôn ngữ tự nhiên qua Telegram.

## 4) Kiến trúc tổng quan
Khối xử lý chính:
1. Nguồn Video (Video Source)
2. Bộ phát hiện (Detector - YOLO)
3. Quản lý trạng thái (State Manager: NORMAL, SILENCED, MONITORING_INTENSELY)
4. Cảnh báo (Alerting: Telegram notifier/callback)
5. Não bộ LLM + Bot handlers

Luồng chính:
1. Nhận khung hình từ camera/file.
2. Chạy suy luận (inference) và lấy kết quả phát hiện.
3. Xác nhận "cháy thực sự" (confirmed fire) theo cửa sổ thời gian.
4. Nếu đủ điều kiện + đến chu kỳ báo cáo thì gửi cảnh báo Telegram.
5. Người dùng tương tác (nút bấm/chat), hệ thống cập nhật trạng thái runtime.

## 5) Trạng thái hệ thống và Quy tắc cảnh báo

Trạng thái (State):
- NORMAL: vận hành mặc định.
- SILENCED: tạm dừng cảnh báo trong N phút.
- MONITORING_INTENSELY: báo cáo theo chu kỳ theo dõi sát hơn, kèm xu hướng diện tích lửa.

Quy tắc quan trọng:
- Xác nhận cháy (Fire confirmation): chỉ xác nhận khi lửa tồn tại đủ lâu trong khoảng thời gian cấu hình.
- Khôi phục khi mất lửa (Fire absence reset): cho phép mất kết quả phát hiện ngắn hạn để tránh hiện tượng nhấp nháy (flicker).
- Khoảng cách cảnh báo (Alert interval): cách nhau theo chế độ để tránh spam.

## 6) Yêu cầu hệ thống

- macOS/Linux (Windows có thể chạy, nhưng chưa tối ưu hướng dẫn tại đây)
- Python 3.10+
- File mô hình: models/best_v3.pt
- Telegram Bot token và chat id (nếu dùng cảnh báo Telegram)
- Groq API key (nếu dùng LLM chat intent)

## 7) Cài đặt

\`\`\`bash
cd fire-detection-system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
\`\`\`

## 8) Cấu hình .env

Tạo file .env trong thư mục fire-detection-system:

\`\`\`env
# Core
MODEL_PATH=models/best_v3.pt
VIDEO_SOURCE=data/videos/warehouse.mp4

# Detector tuning
CONFIDENCE_THRESHOLD=0.5
IOU_THRESHOLD=0.45

# Runtime logic
FIRE_CONFIRMATION_SECONDS=3.5
FIRE_ABSENCE_RESET_SECONDS=1
ALERT_INTERVAL_NORMAL_SECONDS=3
ALERT_INTERVAL_MONITORING_SECONDS=10
TREND_THRESHOLD_RATIO=0.15

# Telegram
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# LLM (Groq)
GROQ_API_KEY=your_groq_api_key
MODEL_NAME=llama-3.1-8b-instant
\`\`\`

## 9) Cách chạy

### 9.1 Chỉ chạy Vision

\`\`\`bash
python src/main.py
\`\`\`

### 9.2 Vision + Telegram LLM bot

\`\`\`bash
python src/main.py --with-telegram-llm
\`\`\`

### 9.3 Chế độ debug LLM (không mở camera)

\`\`\`bash
python src/main.py --llm-debug
\`\`\`

## 10) Tương tác Telegram

Bot có thể hiểu ý định qua chat nhắn tin bằng ngôn ngữ bình thường, ví dụ:
- "tắt báo động 10 phút" -> MUTE
- "gửi tôi ảnh camera hiện tại" -> SHOW_CAMERA
- "trạng thái hệ thống" -> STATUS
- "theo dõi sát hơn" -> MONITORING_INTENSELY
- "báo khẩn cấp" -> EMERGENCY

Khi có cảnh báo, bot gửi ảnh kèm các nút bấm nhanh (inline buttons):
- Tạm dừng 10 phút
- Theo dõi thêm
- Báo động khẩn cấp

## 11) Phím tắt khi chạy giao diện video

- q: thoát
- d: bật/tắt hiển thị
- f: bật/tắt FPS

## 12) Cấu trúc thư mục

\`\`\`text
fire-detection-system/
├── src/
│   ├── main.py                 # Điểm khởi đầu (Entry point)
│   ├── agents/
│   │   ├── brain.py            # Phân loại ý định LLM (Groq)
│   │   └── tools.py            # Các hành động công cụ cho Telegram bot
│   ├── chat/
│   │   └── telegram_bot.py     # Xử lý Telegram, nút bấm, tin nhắn
│   ├── core/
│   │   ├── detector.py         # Suy luận YOLO
│   │   ├── state_manager.py    # Chuyển đổi trạng thái Runtime
│   │   └── system.py           # Điều phối luồng xử lý (Pipeline coordinator)
│   └── utils/
│       ├── config.py           # Cấu hình môi trường
│       ├── drawer.py           # Vẽ bbox/trạng thái/FPS
│       └── notifier.py         # Gửi cảnh báo Telegram
├── data/videos/                # Video mẫu
├── models/                     # Các mô hình YOLO
└── requirements.txt
\`\`\`
