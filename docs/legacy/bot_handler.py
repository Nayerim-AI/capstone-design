from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
import datetime

# Kita akan menerima instance gps_reader dari main.py
class BotHandler:
    def __init__(self, gps_reader):
        self.gps_reader = gps_reader

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /start"""
        user_name = update.effective_user.first_name
        
        # Buat keyboard untuk mempermudah penggunaan
        keyboard = [
            [KeyboardButton("📍 Cek Lokasi"), KeyboardButton("📊 Status Sistem")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_message = (
            f"Halo {user_name}! 👋\n\n"
            f"Saya adalah Bot Tracker Capstone Design.\n"
            f"Saya terhubung dengan modul GPS PL2303 untuk melacak posisi secara realtime.\n\n"
            f"Gunakan menu di bawah atau ketik perintah:\n"
            f"/lokasi - Dapatkan koordinat dan peta\n"
            f"/status - Cek status pembacaan GPS\n"
            f"/bantuan - Menampilkan pesan ini"
        )
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

    async def get_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mengirimkan lokasi dari GPS"""
        loc_data = self.gps_reader.get_current_location()
        
        if loc_data['latitude'] is None or loc_data['longitude'] is None:
            await update.message.reply_text("⏳ *Menunggu sinyal GPS...*\nModul GPS belum mendapatkan fix lokasi yang valid. Pastikan antena berada di area terbuka (outdoor).", parse_mode='Markdown')
            return

        lat = loc_data['latitude']
        lon = loc_data['longitude']
        alt = loc_data['altitude'] if loc_data['altitude'] else "Tidak tersedia"
        speed = loc_data['speed'] if loc_data['speed'] else "0.0"
        
        # Jika last_update ada, hitung waktu yang berlalu
        time_str = "Baru saja"
        if loc_data['last_update']:
            dt = datetime.datetime.fromtimestamp(loc_data['last_update'])
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')

        # Kirim Location (Peta bawaan Telegram)
        await context.bot.send_location(
            chat_id=update.effective_chat.id,
            latitude=lat,
            longitude=lon
        )
        
        # Kirim detail text
        report_msg = (
            f"🌍 *Laporan Lokasi Terkini*\n\n"
            f"📍 *Latitude*: `{lat}`\n"
            f"📍 *Longitude*: `{lon}`\n"
            f"⛰️ *Altitude*: {alt} mdpl\n"
            f"🚀 *Kecepatan*: {speed} knots\n"
            f"⏱️ *Update Terakhir*: {time_str}\n\n"
            f"🔗 *Google Maps*:\n"
            f"https://www.google.com/maps?q={lat},{lon}"
        )
        await update.message.reply_text(report_msg, parse_mode='Markdown')

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cek status dari hardware/sistem"""
        loc_data = self.gps_reader.get_current_location()
        is_gps_connected = self.gps_reader.serial_conn and self.gps_reader.serial_conn.is_open
        
        status_msg = f"📊 *Status Sistem*\n\n"
        status_msg += f"🔌 *Koneksi GPS*: {'✅ Terhubung' if is_gps_connected else '❌ Terputus'}\n"
        status_msg += f"🛰️ *Status Sinyal*: {'✅ Lock' if loc_data['latitude'] else '⏳ Mencari satelit...'}\n"
        
        if loc_data['last_update']:
            dt = datetime.datetime.fromtimestamp(loc_data['last_update'])
            status_msg += f"⏱️ *Data Terakhir*: {dt.strftime('%H:%M:%S')}\n"
            
        await update.message.reply_text(status_msg, parse_mode='Markdown')

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk pesan text (termasuk tombol keyboard)"""
        text = update.message.text
        if text == "📍 Cek Lokasi":
            await self.get_location(update, context)
        elif text == "📊 Status Sistem":
            await self.status(update, context)
        else:
            await update.message.reply_text("Perintah tidak dikenali. Silakan gunakan tombol menu yang tersedia.")
