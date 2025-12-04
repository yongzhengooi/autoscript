import subprocess
import csv
import os
import time
import threading

def load_authorized_macs(file_path):
    try:
        with open(file_path, 'r') as f:
            macs = {line.strip().upper() for line in f if line.strip()}
        print(f"[*] Loaded {len(macs)} authorized MAC addresses.")
        return macs
    except FileNotFoundError:
        print(f"[!] MAC list file not found: {file_path}")
        return set()

def run_airodump(interface, output_file):
    print("[*] Starting airodump-ng (press Ctrl+C to stop)...")
    return subprocess.Popen([
        "airodump-ng",
        "--write", output_file,
        "--write-interval", "1",
        "--output-format", "csv",
        interface
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def monitor_csv(csv_file, authorized_macs, seen_bssids):
    while True:
        if not os.path.exists(csv_file):
            time.sleep(1)
            continue

        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 2 or row[0].strip() in ["BSSID", "Station MAC"]:
                        continue

                    bssid = row[0].strip().upper()
                    essid = row[13].strip() if len(row) > 13 else "<Hidden>"

                    if bssid and bssid not in seen_bssids:
                        seen_bssids.add(bssid)
                        if bssid in authorized_macs:
                            print(f"[✅ Authorized] SSID: {essid:20} BSSID: {bssid}")
                        else:
                            print(f"[🚨 Rogue Detected] SSID: {essid:20} BSSID: {bssid}")
                            with open("rogue_list.txt", "a") as f:
                                 f.write(f"SSID: {essid} BSSID: {bssid}\n")
        except Exception as e:
            print(f"[!] Error reading CSV: {e}")
        time.sleep(1)

def cleanup_files(base_name):
    for suffix in ["-01.csv", "-01.kismet.csv", "-01.kismet.netxml", "-01.cap"]:
        path = base_name + suffix
        if os.path.exists(path):
            os.remove(path)

def main():
    iface = input("Enter monitor-mode interface (e.g., wlan0mon): ")
    mac_list_file = "authorized_macs.txt"
    authorized_macs = load_authorized_macs(mac_list_file)
    if not authorized_macs:
        print("[!] No authorized MACs loaded. Exiting.")
        return

    output_base = "scan_output"
    csv_file = output_base + "-01.csv"
    seen_bssids = set()

    cleanup_files(output_base)
    proc = run_airodump(iface, output_base)

    try:
        monitor_csv(csv_file, authorized_macs, seen_bssids)
    except KeyboardInterrupt:
        print("\n[✋] Stopping...")
        proc.terminate()
        cleanup_files(output_base)

if __name__ == "__main__":
    main()
