import os
import subprocess
import csv
import os
import time
import threading

#font
RED="\033[0;31m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
RESET="\033[0m"

def load_authorized_macs(file_path):
    try:
        with open(file_path, 'r') as f:
            macs = {line.strip().upper() for line in f if line.strip()}
        print(f"{GREEN}[*] Loaded {len(macs)} authorized MAC addresses.{RESET}")
        return macs
    except FileNotFoundError:
        print(f"{RED}[!] MAC list file not found: {file_path} {RESET}")
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
                            print(f"{GREEN}[/ Authorized]{RESET} SSID: {essid:20} BSSID: {bssid}")
                        else:
                            print(f"{RED}[X Rogue Detected]{RESET} SSID: {essid:20} BSSID: {bssid}")
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

def start_kismet(interface="wlan0mon",filename="rogue"):
	return subprocess.Popen(["kismet","-c",interface,"-t",filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def kill_kismet():
	os.system("kill $(ps aux | grep -i kismet | awk '{print $2}')")

def main():
	interface=input("Enter the monitor interface (Default wlan0mon): ")
	filename=input("Enter the filename as kismet title: ")
	if interface == "":
		interface="wlan0mon"
	start_kismet(interface,filename)
	mac_list_file = "authorized_macs.txt"
	authorized_macs = load_authorized_macs(mac_list_file)
	if not authorized_macs:
		print(f"{RED}[!] No authorized MACs loaded. Exiting. {RESET}")
		return

	output_base = "scan_output"
	csv_file = output_base + "-01.csv"
	seen_bssids = set()
	cleanup_files(output_base)
	proc = run_airodump(interface, output_base)
	try:
		monitor_csv(csv_file, authorized_macs, seen_bssids)
	except KeyboardInterrupt:
		print(f"{RED}\n[-] Stopping the detection ...{RESET}")
		proc.terminate()
		kill_kismet()
		cleanup_files(output_base)
		analyst=input("Do you want further narrow down rogue detection analysis? : ")
		if analyst.lower() == "yes" or analyst.lower() == "y":
			print(f"{BLUE}Checking file with name {filename} {RESET}")
			result = subprocess.check_output(f'find . -type f -name "{filename}*"', shell=True, text=True)
			print(f"{GREEN}File found: {result}{RESET}")
			file_paths = result.strip()
			print(f"{BLUE}Stripping the packet ... {RESET}")
			os.system(f"kismetdb_strip_packets -i {file_paths} -o strip_{filename}.kismet")
			print(f"{BLUE}Converting the kismet to JSON ...{RESET}")
			os.system(f"kismetdb_dump_devices  -i strip_{filename}.kismet -o {filename}.json -e")
			print(f"{BLUE}Extrating the jq with attribute SSID,BSSID and encryption type ... {RESET}")
			os.system(f"""cat {filename}.json | jq 'select(.["kismet_device_base_type"] == "Wi-Fi AP") | {Type: .["kismet_device_base_type"], Name: .kismet_device_base_commonname, BSSID: .["kismet_device_base_macaddr"], Encryption: .["kismet_device_base_crypt"]}' > potential_rogue_{filename}.json""")
			print(f"{GREEN}[*]DONE ... {RESET}")

if __name__ == "__main__":
    main()
