import os

import cv2


class FireTools:
	def __init__(self, detector, state_manager, bot):
		self.detector = detector
		self.state = state_manager
		self.bot = bot

	async def show_camera(self, chat_id):
		"""Capture latest frame from detector and send it to Telegram."""
		frame = getattr(self.detector, "current_frame", None)
		if frame is None:
			await self.bot.app.bot.send_message(
				chat_id=chat_id,
				text="Khong the truy cap camera luc nay.",
			)
			return

		snapshot_path = "data/snapshot.jpg"
		os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
		ok = cv2.imwrite(snapshot_path, frame)
		if not ok:
			await self.bot.app.bot.send_message(
				chat_id=chat_id,
				text="Khong the tao anh snapshot tu camera.",
			)
			return

		with open(snapshot_path, "rb") as photo:
			await self.bot.app.bot.send_photo(
				chat_id=chat_id,
				photo=photo,
				caption="Anh thuc te tu camera hien tai.",
			)

	def mute_alerts(self, minutes=10):
		"""Silence outbound alerts for N minutes."""
		self.state.set_mute(minutes)
		return f"Da tat thong bao trong {minutes} phut."

	def start_intense_monitoring(self):
		"""Enable intensified monitoring mode."""
		self.state.set_monitor()
		return "Da chuyen sang che do giam sat chat che dien tich lua."

	def get_status(self):
		snapshot = self.state.snapshot()
		if snapshot.state.value == "SILENCED" and snapshot.ignore_until is not None:
			return (
				f"Trang thai: {snapshot.state.value}. "
				f"Mute den: {snapshot.ignore_until.isoformat()}. "
				f"Dien tich lua gan nhat: {snapshot.last_fire_area:.0f}px2"
			)

		return (
			f"Trang thai: {snapshot.state.value}. "
			f"Dien tich lua gan nhat: {snapshot.last_fire_area:.0f}px2"
		)
