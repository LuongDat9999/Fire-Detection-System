# Fire Detection System

Hệ thống AI giám sát và cảnh báo cháy theo thời gian thực, kết hợp:
- Computer Vision (YOLO) để phát hiện nguy cơ cháy trên video stream.
- Quản lý trạng thái Runtime (state management) để tránh spam cảnh báo và theo dõi xu hướng.
- Telegram Bot + LLM để tương tác bằng ngôn ngữ tự nhiên (tạm dừng, kiểm tra trạng thái, xem camera, theo dõi sát).

README này được viết theo góc nhìn BA để đội vận hành, dev và các bên liên quan (stakeholder) dễ dàng hiểu nhanh:
- Hệ thống giải quyết bài toán gì.
- Luồng nghiệp vụ và luồng kỹ thuật ra sao.
- Cách cài đặt, chạy, và vận hành an toàn.


## Cấu trúc thư mục
```text
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
```

## Định hướng nâng cấp 

Trong phạm vi hiện tại:
- Nhận diện nguy cơ cháy trên khung hình video bằng mô hình YOLO (.pt).
- Cơ chế xác nhận cháy theo thời gian (không báo ngay khi chỉ có 1 khung hình nhiễu).
- Gửi cảnh báo Telegram kèm ảnh và nút hành động.
- LLM phân loại ý định người dùng trong chat Telegram.

Ngoài phạm vi (chưa triển khai đầy đủ trong repo này):
- Nâng cấp độ chính xác của model
- Đa camera + bảng điều khiển (dashboard) tập trung.
- Lưu trữ lịch sử cảnh báo vào database/BI dashboard.
- Tích hợp thêm chức năng
- Tích hợp thêm kênh cảnh báo: SMS, Zalo, email, webhook.
- Tích hợp trực tiếp tổng đài 114/911.
- Cơ chế đa camera quản trị tập trung.
