from rich import print
from rich.console import Console
from rich.progress import Progress, BarColumn, DownloadColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn
import json
import requests
import os
import time
import random

console = Console()
counter = 5
OUTPUT_DIR = "./OneDrive_Download"

# ===============================================
# Helper: Safe request with retry/backoff
# ===============================================
def safe_request(method, url, headers, **kwargs):
    for attempt in range(5):
        response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", random.randint(20, 40)))
            console.print(f"[yellow]⚠️ Rate limited (429). Retrying in {wait}s...[/yellow]")
            time.sleep(wait)
            continue
        elif response.status_code >= 500:
            wait = 5 * (attempt + 1)
            console.print(f"[red]⚠️ Server error {response.status_code}. Retry in {wait}s...[/red]")
            time.sleep(wait)
            continue
        return response
    raise Exception("❌ Too many retries — giving up.")


# ===============================================
# User Info
# ===============================================
def get_info(auth_token):
    global counter
    response = safe_request("GET", "https://graph.microsoft.com/v1.0/me", headers=auth_token)
    j_response = response.json()

    console.print("[cyan]\n=============== Authenticated as ===============[/cyan]")
    console.print(f"[green]Display Name:[/green] {j_response.get('displayName', 'N/A')}")
    console.print(f"[green]Job Title:[/green] {j_response.get('jobTitle', 'N/A')}")
    console.print(f"[green]Phone Number:[/green] {j_response.get('mobilePhone', 'N/A')}")
    console.print(f"[green]Principal Name:[/green] {j_response.get('userPrincipalName', 'N/A')}")
    counter = 5


# ===============================================
# Recursive folder listing (no downloads)
# ===============================================
def list_items(auth_token, item_ref, level=0):
    if item_ref.startswith("https://"):
        url = item_ref
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_ref}/children"

    response = safe_request("GET", url, headers=auth_token)
    data = response.json()

    for item in data.get("value", []):
        indent = "  " * level
        name = item["name"]
        type_ = "📁 Folder" if "folder" in item else "📄 File"
        console.print(f"{indent}{type_}: [bold]{name}[/bold]")

        if "folder" in item:
            list_items(auth_token, item["id"], level + 1)

    if "@odata.nextLink" in data:
        list_items(auth_token, data["@odata.nextLink"], level)


# ===============================================
# Recursive download (files only)
# ===============================================
def download_items(auth_token, item_ref, base_path):
    if item_ref.startswith("https://"):
        url = item_ref
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_ref}/children"

    response = safe_request("GET", url, headers=auth_token)
    data = response.json()

    for item in data.get("value", []):
        name = item["name"]
        if "folder" in item:
            new_path = os.path.join(base_path, name)
            os.makedirs(new_path, exist_ok=True)
            download_items(auth_token, item["id"], new_path)
        else:
            download_url = item.get("@microsoft.graph.downloadUrl")
            if download_url:
                download_file(name, download_url, base_path)

    if "@odata.nextLink" in data:
        download_items(auth_token, data["@odata.nextLink"], base_path)


# ===============================================
# File Downloader with Progress Bar
# ===============================================
def download_file(name, url, save_path):
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, name)

    if os.path.exists(file_path):
        console.print(f"[dim]Skipping existing file {name}[/dim]")
        return

    console.print(f"[blue]📥 Downloading:[/blue] {name}")

    with safe_request("GET", url, headers={}, stream=True) as r:
        total = int(r.headers.get("Content-Length", 0))
        chunk_size = 1024 * 64  # 64KB

        with Progress(
            TextColumn("[bold blue]{task.fields[filename]}[/bold blue]"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("download", total=total, filename=name)
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

    console.print(f"[green]✅ Saved to {file_path}[/green]\n")
    time.sleep(random.uniform(0.3, 1.0))


# ===============================================
# Top-level list / download
# ===============================================
def list_onedrive(auth_token):
    console.print("\n================== [bold cyan]Listing OneDrive[/bold cyan] ==================\n")
    response = safe_request("GET", "https://graph.microsoft.com/v1.0/me/drive/root/children", headers=auth_token)
    data = response.json()
    for item in data.get("value", []):
        name = item["name"]
        console.print(f"[bold]{name}[/bold]")
        if "folder" in item:
            list_items(auth_token, item["id"], 1)
    if "@odata.nextLink" in data:
        list_items(auth_token, data["@odata.nextLink"], 0)


def download_onedrive(auth_token):
    console.print("\n================== [bold cyan]Downloading OneDrive[/bold cyan] ==================\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    response = safe_request("GET", "https://graph.microsoft.com/v1.0/me/drive/root/children", headers=auth_token)
    data = response.json()
    for item in data.get("value", []):
        name = item["name"]
        if "folder" in item:
            new_path = os.path.join(OUTPUT_DIR, name)
            os.makedirs(new_path, exist_ok=True)
            download_items(auth_token, item["id"], new_path)
        else:
            download_url = item.get("@microsoft.graph.downloadUrl")
            if download_url:
                download_file(name, download_url, OUTPUT_DIR)
    if "@odata.nextLink" in data:
        download_items(auth_token, data["@odata.nextLink"], OUTPUT_DIR)


# ===============================================
# Create Folder
# ===============================================
def create_folder(auth_token, folder_name):
    info = {"name": folder_name, "folder": {}}
    response = safe_request(
        "POST",
        "https://graph.microsoft.com/v1.0/me/drive/root/children",
        headers=auth_token,
        data=json.dumps(info),
    )
    if response.status_code in [200, 201]:
        console.print(f"[green]✅ Successfully created folder '{folder_name}'[/green]")
    else:
        console.print(f"[red]❌ Failed to create folder: {response.text}[/red]")


# ===============================================
# Main Menu
# ===============================================
def main():
    jwt = input("Enter the JWT auth token: ").strip()
    console.clear()

    global counter
    auth_header = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    get_info(auth_header)
    while True:
        try:
            print("\n[bold cyan]=========== MENU ===========[/bold cyan]")
            print("1) List all files in OneDrive")
            print("2) Download all files in OneDrive")
            print("3) Create a folder")
            print("4) Whoami")
            print("5) Exit")

            choice = input("\nEnter an option: ").strip()
            if choice == "1":
                list_onedrive(auth_header)
            elif choice == "2":
                download_onedrive(auth_header)
            elif choice == "3":
                name = input("Enter the folder name: ").strip()
                create_folder(auth_header, name)
            elif choice == "4":
                get_info(auth_header)
            elif choice == "5":
                break
            else:
                console.print("[yellow]Invalid option, try again.[/yellow]")
        except Exception as e:
            print(f"Attempted to auth: {counter} | Error: {e}")
            counter -= 1
            time.sleep(3)
            if counter == 0:
                print("[red]Probably JWT expired[/red]")
                break


if __name__ == "__main__":
    main()
