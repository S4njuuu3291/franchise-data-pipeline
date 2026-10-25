from datetime import datetime, timedelta
import logging
import subprocess
import yaml
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Load konfigurasi dari file YAML
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(SCRIPT_DIR, "simulation_config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

sim = config["simulation"]
start_date = datetime.strptime(sim["start_date"], "%Y-%m-%d")
end_date = datetime.strptime(sim["end_date"], "%Y-%m-%d")

current_date = start_date
overall_start = datetime.now()
logger.info("=== MEMULAI RUNNER SIMULASI 3 BULAN FULL ===")
logger.info("Mulai: %s", overall_start.strftime('%Y-%m-%d %H:%M:%S'))

while current_date <= end_date:
    date_str = current_date.strftime("%Y-%m-%d")
    day_start = datetime.now()
    logger.info("Menjalankan generator untuk tanggal: %s", date_str)
    
    # Memanggil skrip generate_transactions.py via terminal secara otomatis
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "generate_transactions.py"), "--date", date_str]
    # Warisi stream agar log generator tampil langsung dengan level aslinya.
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        logger.error("Generator gagal untuk tanggal %s dengan exit code %d", date_str, result.returncode)
        raise RuntimeError(f"Generator gagal untuk tanggal {date_str} dengan exit code {result.returncode}")
    
    day_end = datetime.now()
    day_duration = (day_end - day_start).total_seconds()
    logger.info("Selesai (%s) — %.2f detik", date_str, day_duration)
        
    # Maju ke hari berikutnya
    current_date += timedelta(days=1)

overall_end = datetime.now()
total_duration = (overall_end - overall_start).total_seconds()
logger.info("=== SEMUA DATA TRANSAKSI 3 BULAN BERHASIL DIMASUKKAN ===")
logger.info("Selesai: %s", overall_end.strftime('%Y-%m-%d %H:%M:%S'))
logger.info("Total waktu eksekusi: %.2f detik (%.2f menit)", total_duration, total_duration / 60)
