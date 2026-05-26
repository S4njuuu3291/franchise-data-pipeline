from datetime import datetime, timedelta
import subprocess

start_date = datetime(2026, 5, 16)
end_date = datetime(2026, 5, 25)

current_date = start_date
overall_start = datetime.now()
print(f"=== MEMULAI RUNNER SIMULASI 3 BULAN FULL ===")
print(f"🕐 Mulai: {overall_start.strftime('%Y-%m-%d %H:%M:%S')}")
print()

while current_date <= end_date:
    date_str = current_date.strftime("%Y-%m-%d")
    day_start = datetime.now()
    print(f"[EXEC] Menjalankan generator untuk tanggal: {date_str}")
    
    # Memanggil skrip generate_transactions.py via terminal secara otomatis
    cmd = ["python3","data-generator/generate_transactions.py", "--date", date_str]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Cetak output dari skrip utama agar kita bisa memantau prosesnya
    print(result.stdout)
    if result.stderr:
        print(f"WARNING/ERROR: {result.stderr}")
    
    day_end = datetime.now()
    day_duration = (day_end - day_start).total_seconds()
    print(f"✅ Selesai ({date_str}) — ⏱ {day_duration:.2f} detik")
    print()
        
    # Maju ke hari berikutnya
    current_date += timedelta(days=1)

overall_end = datetime.now()
total_duration = (overall_end - overall_start).total_seconds()
print("=== SEMUA DATA TRANSAKSI 3 BULAN BERHASIL DIMASUKKAN ===")
print(f"🕐 Selesai: {overall_end.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"⏱ Total waktu eksekusi: {total_duration:.2f} detik ({(total_duration/60):.2f} menit)")