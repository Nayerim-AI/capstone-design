import logging
import os
import csv
from datetime import datetime

# Setup logging ke console dan file
def setup_logger():
    os.makedirs('data', exist_ok=True)
    
    logger = logging.getLogger('GPSBotLogger')
    logger.setLevel(logging.INFO)
    
    # Formatter untuk log sistem
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Handler file
    file_handler = logging.FileHandler('data/system.log')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

system_logger = setup_logger()

# Fungsi khusus untuk mencatat log data GPS ke CSV
def log_gps_data(latitude, longitude, altitude, speed):
    try:
        file_exists = os.path.isfile('data/gps_log.csv')
        
        with open('data/gps_log.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Timestamp', 'Latitude', 'Longitude', 'Altitude', 'Speed'])
            
            writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), latitude, longitude, altitude, speed])
    except Exception as e:
        system_logger.error(f"Gagal menulis ke CSV: {e}")
