import cv2
import numpy as np
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from agents.brain import Intent, LLMBrain
from agents.tools import FireTools

class FireTelegramBot:
    def __init__(self, token, detector=None, state_manager=None, brain=None):
        self.app = Application.builder().token(token).build()
        self.brain = brain or LLMBrain()
        self.detector = None
        self.state_manager = None
        self.tools = None
        self.attach_runtime(detector, state_manager)
        self._add_handlers()

    def attach_runtime(self, detector, state_manager) -> None:
        self.detector = detector
        self.state_manager = state_manager
        if detector is None or state_manager is None:
            self.tools = None
            return

        self.tools = FireTools(detector, state_manager, self)

    def _add_handlers(self):
        # Lệnh /start
        self.app.add_handler(CommandHandler("start", self.start_command))
        # Xử lý các nút bấm (Inline Keyboard)
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        # Xử lý tin nhắn văn bản (Sử dụng LLM)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Hàm xử lý khi người dùng gõ /start"""
        await update.message.reply_text(
            "🔥 Hệ thống AI Detection đã sẵn sàng!\n"
            "Tôi sẽ thông báo khi có hỏa hoạn. Bạn cũng có thể yêu cầu xem camera bằng lời nói."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dùng LLM để hiểu người dùng muốn gì"""
        user_text = update.message.text
        chat_id = update.message.chat_id
        result = self.brain.classify_intent(user_text)

        if self.tools is None:
            await update.message.reply_text("He thong chua gan detector/state manager.")
            return

        if result.intent == Intent.SHOW_CAMERA:
            await self.tools.show_camera(chat_id)
        elif result.intent == Intent.RESUME_MONITORING:
            msg = self.tools.resume_monitoring()
            await update.message.reply_text(f"{msg}")
        elif result.intent == Intent.MONITORING_INTENSELY:
            msg = self.tools.start_intense_monitoring()
            await update.message.reply_text(f"{msg}")
        elif result.intent == Intent.MUTE:
            msg = self.tools.mute_alerts(minutes=10)
            await update.message.reply_text(f"{msg}")
        elif result.intent == Intent.STATUS:
            await update.message.reply_text(self.tools.get_status())
        elif result.intent == Intent.EMERGENCY:
            await update.message.reply_text("Da nhan lenh khan cap. Hay lien he luc luong cuu hoa ngay.")
        else:
            raw_line = result.raw_output if result.raw_output else "UNKNOWN"
            await update.message.reply_text(f"Khong xac dinh duoc yeu cau. LLM raw: {raw_line}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý các nút bấm"""
        query = update.callback_query
        await query.answer()
        
        # Tùy biến phản hồi dựa trên data của nút
        action_map = {
            'mute_10': "✅ Đã tạm dừng cảnh báo 10 phút.",
            'resume_now': "Đã tiếp tục theo dõi ngay.",
            'monitor_more': "⏳ Đang tăng cường theo dõi biến động diện tích lửa...",
            'emergency': "🚨 ĐÃ GỬI TÍN HIỆU CỨU HỎA KHẨN CẤP!"
        }

        if self.tools is not None:
            if query.data == "mute_10":
                action_map["mute_10"] = self.tools.mute_alerts(10)
            elif query.data == "resume_now":
                action_map["resume_now"] = self.tools.resume_monitoring()
            elif query.data == "monitor_more":
                action_map["monitor_more"] = self.tools.start_intense_monitoring()
        
        result_text = action_map.get(query.data, "Không rõ lệnh")
        await query.edit_message_caption(caption=f"Trạng thái: {result_text}")

    async def send_fire_alert(self, chat_id: str, frame: np.ndarray, details: str) -> None:
        """Gửi ảnh cảnh báo cháy kèm theo các nút bấm tương tác."""
        if not chat_id:
            return

        # 1. Mã hóa ảnh frame sang bytes
        ok, jpeg_frame = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return

        # 2. ĐỊNH NGHĨA CÁC NÚT BẤM (Đây là phần bạn đang thiếu)
        keyboard = [
            [
                InlineKeyboardButton("Phớt lờ (10p)", callback_data='mute_10'),
                InlineKeyboardButton("Theo dõi thêm", callback_data='monitor_more')
            ],
            [InlineKeyboardButton("🚨 BÁO ĐỘNG THẬT", callback_data='emergency')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 3. GỬI PHOTO KÈM REPLY_MARKUP
        try:
            await self.app.bot.send_photo(
                chat_id=chat_id,
                photo=jpeg_frame.tobytes(),
                caption=f"🚨 <b>CẢNH BÁO CHÁY!</b>\n{details}\n\n<i>Chọn hành động bên dưới:</i>",
                parse_mode="HTML",
                reply_markup=reply_markup # Gắn các nút bấm vào đây
            )
        except Exception as e:
            print(f"Lỗi khi gửi cảnh báo Telegram: {e}")