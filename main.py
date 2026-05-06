import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from gps_reader import GPSReader
from bot_handler import BotHandler
from logger import system_logger

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUDRATE = int(os.getenv("BAUDRATE", "9600"))

def main():
    if not TELEGRAM_TOKEN:
        system_logger.error("TELEGRAM_TOKEN tidak ditemukan di file .env")
        return

    # Inisialisasi Modul GPS
    system_logger.info("Inisialisasi GPS Reader...")
    gps = GPSReader(port=SERIAL_PORT, baudrate=BAUDRATE)
    gps.start()

    # Inisialisasi Bot Telegram
    system_logger.info("Inisialisasi Bot Telegram...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    bot_handler = BotHandler(gps)
    
    # Daftarkan handlers
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("lokasi", bot_handler.get_location))
    application.add_handler(CommandHandler("status", bot_handler.status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_text))
    
    # Jalankan bot
    system_logger.info("Bot mulai berjalan (Polling)... Tekan Ctrl+C untuk berhenti.")
    try:
        application.run_polling()
    except KeyboardInterrupt:
        system_logger.info("Dihentikan oleh pengguna.")
    finally:
        gps.stop()
        system_logger.info("Sistem dimatikan.")

if __name__ == '__main__':
    main()
