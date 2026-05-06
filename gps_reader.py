import serial
import pynmea2
import threading
import time
from logger import system_logger, log_gps_data

class GPSReader:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_running = False
        
        # Data terkini
        self.current_lat = None
        self.current_lon = None
        self.current_altitude = None
        self.current_speed = None
        self.last_update = None
        self.lock = threading.Lock()

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            system_logger.info(f"Berhasil terhubung ke GPS di port {self.port}")
            return True
        except serial.SerialException as e:
            system_logger.error(f"Gagal menghubungkan ke {self.port}: {e}")
            return False

    def start(self):
        if not self.serial_conn:
            if not self.connect():
                return
                
        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        system_logger.info("Thread GPS Reader dimulai.")

    def stop(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        system_logger.info("GPS Reader dihentikan.")

    def _read_loop(self):
        while self.is_running:
            try:
                line = self.serial_conn.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
                    msg = pynmea2.parse(line)
                    
                    with self.lock:
                        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude') and msg.latitude != 0.0:
                            self.current_lat = msg.latitude
                            self.current_lon = msg.longitude
                            self.last_update = time.time()
                            
                            if hasattr(msg, 'altitude'):
                                self.current_altitude = msg.altitude
                            if hasattr(msg, 'spd_over_grnd'):
                                self.current_speed = msg.spd_over_grnd
                                
                            # Simpan ke CSV setiap ada update koordinat yang valid
                            log_gps_data(
                                self.current_lat, 
                                self.current_lon, 
                                self.current_altitude, 
                                self.current_speed
                            )
                            system_logger.debug(f"GPS Update: Lat {self.current_lat}, Lon {self.current_lon}")
            except pynmea2.ParseError as e:
                pass # Abaikan data yang tidak valid/belum lengkap (sering terjadi saat cold start)
            except Exception as e:
                system_logger.error(f"Error pada pembacaan GPS: {e}")
                time.sleep(1)

    def get_current_location(self):
        with self.lock:
            return {
                'latitude': self.current_lat,
                'longitude': self.current_lon,
                'altitude': self.current_altitude,
                'speed': self.current_speed,
                'last_update': self.last_update
            }
