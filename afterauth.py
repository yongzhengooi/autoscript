from rich import print
from rich.console import Console
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
# Refresh Token (Optional)
# ===============================================
def refresh(jwt):
    response = requests.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        data={
            "client_id": "00b41c95-dab0-4487-9791-b9d2c32c80f2",
            "scope": "0000000c-0000-0000-c000-000000000000/.default",
            "refresh_token": jwt,
            "grant_type": "refresh_token",
        },
    )
    if response.status_code == 200:
        data = response.json()
        # Extract the new access token
        auth_token = data.get("access_token")
        return auth_token
    else:
        print(f"Token refresh failed ({response.status_code}): {response.text}")
        return None


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
# Recursive Listing + Download
# ===============================================
def list_children(auth_token, item_ref, base_path, level=0, download=False):
    # handle both item_id and full pagination URL
    if item_ref.startswith("https://"):
        url = item_ref
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_ref}/children"

    response = safe_request("GET", url, headers=auth_token)
    data = response.json()

    for item in data.get("value", []):
        indent = "  " * level
        name = item["name"]
        type_ = "Folder" if "folder" in item else "File"
        console.print(f"{indent}{type_}: [bold]{name}[/bold]")

        if "folder" in item:
            # Recursive call for subfolder
            new_path = os.path.join(base_path, name)
            os.makedirs(new_path, exist_ok=True)
            list_children(auth_token, item["id"], new_path, level + 1, download)
        else:
            # Download file if requested
            if download:
                download_url = item.get("@microsoft.graph.downloadUrl")
                if download_url:
                    download_file(name, download_url, base_path)
                else:
                    console.print(f"{indent}[yellow]⚠️ No download URL for {name}[/yellow]")

    # Handle pagination properly (preserve download flag)
    if "@odata.nextLink" in data:
        next_url = data["@odata.nextLink"]
        list_children(auth_token, next_url, base_path, level, download)


# ===============================================
# File Downloader
# ===============================================
def download_file(name, url, save_path):
    console.print(f"[blue]📥 Downloading:[/blue] {name}")
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, name)

    # Skip existing
    if os.path.exists(file_path):
        console.print(f"[dim]Skipping existing file {name}[/dim]")
        return

    response = safe_request("GET", url, headers={})
    with open(file_path, "wb") as f:
        f.write(response.content)
    console.print(f"[green]✅ Saved to {file_path}[/green]\n")
    time.sleep(random.uniform(0.3, 1.0))


# ===============================================
# List top-level OneDrive items
# ===============================================
def get_onedrive(auth_token, download=False):
    response = safe_request("GET", "https://graph.microsoft.com/v1.0/me/drive/root/children", headers=auth_token)
    data = response.json()

    console.print("\n================== [bold cyan]Listing OneDrive Folders[/bold cyan] ==================\n")

    for item in data.get("value", []):
        name = item["name"]
        id_ = item["id"]
        webUrl = item["webUrl"]
        type_ = "Folder" if "folder" in item else "File"
        console.print(f"{type_}: [bold]{name}[/bold] ({id_}) -> {webUrl}")

        if "folder" in item:
            console.print(f"\n[dim]Listing child items for {name}...[/dim]\n")
            list_children(auth_token, id_, os.path.join(OUTPUT_DIR, name), download)

    # Handle pagination for root
    if "@odata.nextLink" in data:
        next_url = data["@odata.nextLink"]
        list_children(auth_token, next_url, OUTPUT_DIR, 0, download)


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
                get_onedrive(auth_header)
            elif choice == "2":
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                get_onedrive(auth_header, download=True)
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
                refresh_token=input("Maybe try generate new token using refresh token? \n")
                rf_jwt=refresh(refresh_token)
		auth_header = {"Authorization": f"Bearer {rf_jwt}", "Content-Type": "application/json"}


if __name__ == "__main__":
    main()
