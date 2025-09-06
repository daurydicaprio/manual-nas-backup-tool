#!/usr/bin/env python3
# Manual NAS Backup Tool by Daury DiCaprio - v0.001
# A dual-purpose backup tool using Restic for secure, versioned backups
# and Rclone for simple, incremental file copies, with enhanced user controls.

import os
import subprocess
import sys
import time
import shutil
import signal
import re
import random
import string
import unicodedata
from datetime import datetime
import threading

# ====== COLORS & ICONS ======
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

OK = f"{GREEN}✅{RESET}"
WARN = f"{YELLOW}⚠️{RESET}"
ERR = f"{RED}❌{RESET}"
INFO = f"{BLUE}ℹ️{RESET}"
PROG = f"{CYAN}📦{RESET}"

# ====== GLOBALS ======
current_operation = ""
start_time = None
backup_passwords = {}
SCRIPT_PATH = os.path.realpath(__file__)
COMMAND_NAME = "manual-nas-tool"
INSTALL_PATH = os.path.expanduser(f"~/.local/bin/{COMMAND_NAME}")

# ====== GENERAL HELPERS ======

def cleanup(sig=None, frame=None):
    """Clean up any temporary resources on exit."""
    if sig:
        print(f"\n{WARN} Operation cancelled by user.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def normalize_name(name):
    """Normalize a string to be used as a safe directory name."""
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    name = re.sub(r'[\s_-]+', '_', name)
    return name

def run_cmd(cmd, env_vars=None):
    """Execute a shell command, returning (success, output)."""
    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
        return result.returncode == 0, result.stdout.strip()
    except Exception:
        return False, "Failed to execute command."

def run_cmd_with_progress(cmd, operation, log_file, env_vars=None):
    """Execute a long-running command and show a progress spinner."""
    print(f"\n{INFO} Starting {operation}...")
    show_progress(operation)
    
    with open(log_file, 'a') as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Executing: {cmd}\n")

    output_lines = []
    success = False
    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, env=env
        )
        for line in iter(process.stdout.readline, ''):
            output_lines.append(line.strip())
        process.wait()
        success = process.returncode == 0
    except Exception as e:
        success = False
        output_lines.append(str(e))

    stop_progress()
    
    with open(log_file, 'a') as f:
        status = "SUCCESS" if success else "ERROR"
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {operation} - {status}\n")
        f.write("Full Output:\n" + "\n".join(f"  {line}" for line in output_lines) + "\n")

    if success:
        print(f"{OK} {operation} completed successfully!")
    else:
        print(f"{ERR} {operation} failed!")
        print("Error details (last 5 lines):")
        for line in output_lines[-5:]:
            print(f"  {line}")
            
    return success, output_lines

# ====== UI & INPUT HELPERS ======

def confirm(prompt):
    """Get user confirmation (Y/N)."""
    while True:
        choice = input(f"{YELLOW}{prompt} (y/N): {RESET}").strip().lower()
        if choice in ['y', 'yes']: return True
        elif choice in ['n', 'no', '']: return False

def get_input(prompt, default=""):
    """Get user input."""
    result = input(f"{CYAN}{prompt}: {RESET}").strip()
    if result.lower() in ['q', 'quit']: cleanup(signal.SIGINT, None)
    return result if result else default

def get_password(prompt, salt):
    """Get password or generate a random one."""
    pwd = input(f"{CYAN}{prompt} [Press Enter to auto-generate]: {RESET}").strip()
    if pwd == "":
        chars = string.ascii_letters + string.digits
        pwd = f"{salt}_{''.join(random.choice(chars) for _ in range(12))}"
        print(f"{INFO} Generated password.") # Password shown in final summary
    return pwd

def get_custom_destination_path(default_path):
    """Asks user for a custom destination path with validation."""
    prompt = (f"Enter custom destination path (max 2 levels). "
              f"Default: '{default_path}'\n"
              f"Example: my_projects/personal_backups\n"
              f"[Press Enter for default]: ")
    while True:
        path = get_input(prompt).strip("/")
        if not path:
            return default_path
        if len(path.split('/')) > 2:
            print(f"{ERR} Path cannot be more than two levels deep. Please try again.")
        else:
            return path

def format_time(seconds):
    """Format seconds into HH:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def show_progress(operation):
    """Show a CLI progress spinner."""
    global current_operation
    current_operation = operation
    
    def animate():
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while current_operation:
            elapsed = time.time() - start_time if start_time else 0
            print(f"\r{PROG} {chars[i % len(chars)]} {current_operation} - {format_time(elapsed)}", end="", flush=True)
            time.sleep(0.1)
            i += 1
    
    threading.Thread(target=animate, daemon=True).start()

def stop_progress():
    """Stop the progress spinner."""
    global current_operation
    current_operation = ""
    print()

# ====== PRE-FLIGHT CHECKS & INSTALLATION ======

def check_tools():
    """Check if required tools are installed."""
    print(f"{INFO} Checking for required tools...")
    tools = {"restic": "https://restic.readthedocs.io", "rclone": "https://rclone.org/install/"}
    if all(shutil.which(tool) for tool in tools):
        print(f"{OK} All tools are installed.")
        return True
    for tool, url in tools.items():
        if not shutil.which(tool):
            print(f"{ERR} Tool not found: {tool}. See: {url}")
    sys.exit(1)

def check_rclone_config():
    """Check if rclone has configured remotes."""
    print(f"{INFO} Checking rclone configuration...")
    success, remotes = run_cmd("rclone listremotes")
    if not success or not remotes:
        print(f"\n{WARN} Rclone has no configured cloud remotes.")
        return []
    print(f"{OK} Rclone is configured.")
    return [r.rstrip(':') for r in remotes.split('\n') if r.strip()]

def handle_installation():
    """Handles the optional installation/update of the script as a command."""
    is_installed = os.path.exists(INSTALL_PATH)
    
    def do_install():
        try:
            bin_dir = os.path.dirname(INSTALL_PATH)
            os.makedirs(bin_dir, exist_ok=True)
            shutil.copy(SCRIPT_PATH, INSTALL_PATH)
            os.chmod(INSTALL_PATH, 0o755)
            status = "updated" if is_installed else "installed"
            print(f"{OK} Command '{COMMAND_NAME}' has been {status} successfully!")
            
            if bin_dir not in os.environ.get("PATH", "").split(os.pathsep):
                print(f"{WARN} Your PATH does not seem to include {bin_dir}.")
                print(f"    Please add it to your shell profile (e.g., .bashrc, .zshrc) and restart your terminal:")
                print(f"    {BOLD}export PATH=\"$HOME/.local/bin:$PATH\"{RESET}")
        except Exception as e:
            print(f"{ERR} Installation failed: {e}")

    print("-" * 50)
    if is_installed:
        print(f"{INFO} Command '{COMMAND_NAME}' is already installed.")
        print(f"    You can run this tool anytime by just typing: {BOLD}{COMMAND_NAME}{RESET}")
        if confirm("Do you want to update it to this script's version?"):
            do_install()
    else:
        if confirm(f"Would you like to install this script as the '{COMMAND_NAME}' command?"):
            do_install()
        else:
            print(f"{INFO} To install later, run: {BOLD}cp '{SCRIPT_PATH}' '{INSTALL_PATH}' && chmod +x '{INSTALL_PATH}'{RESET}")

# ====== CORE LOGIC FUNCTIONS ======

def handle_secure_backup(src_path, normalized_name, password, dest_type, dest_value, log_file):
    """Handles the secure backup workflow using Restic."""
    custom_path = get_custom_destination_path("manual_nas_encrypted")
    repo_name = f"{normalized_name}_encrypted"
    
    if dest_type == "cloud":
        repo_path = f"rclone:{dest_value}:{custom_path}/{repo_name}"
    else:
        disk_base_path = os.path.join(f"/run/media/{os.getenv('USER')}", dest_value)
        repo_path = os.path.join(disk_base_path, custom_path, repo_name)

    print(f"\n{INFO} Secure Backup Repository: {repo_path}")
    backup_passwords[repo_path] = password
    env_vars = {"RESTIC_PASSWORD": password}
    
    repo_exists, _ = run_cmd(f"restic --repo '{repo_path}' snapshots --last 1", env_vars=env_vars)
    backup_type = "Incremental" if repo_exists else "Initial"
    
    if not confirm(f"Proceed with {backup_type} backup to {dest_value}?"):
        return False, None
    
    if not repo_exists:
        init_cmd = f"restic --repo '{repo_path}' init"
        success, _ = run_cmd_with_progress(init_cmd, f"Initializing repo on {dest_value}", log_file, env_vars)
        if not success: return False, None
    
    backup_cmd = f"restic backup '{src_path}' --repo '{repo_path}' --verbose"
    success, output = run_cmd_with_progress(backup_cmd, f"{backup_type} backup to {dest_value}", log_file, env_vars)
    summary = [line for line in output[-10:] if any(k in line.lower() for k in ['files', 'dirs', 'added', 'processed', 'snapshot'])]
    
    return success, {"destination": repo_path, "summary": summary}

def handle_simple_copy(src_path, normalized_name, dest_type, dest_value, log_file):
    """Handles the simple, non-encrypted, incremental copy workflow using Rclone."""
    custom_path = get_custom_destination_path("manual_nas_backup")
    backup_name = f"{normalized_name}_backup"
    
    if dest_type == "cloud":
        project_path = f"{dest_value}:{custom_path}/{backup_name}"
    else:
        disk_base_path = os.path.join(f"/run/media/{os.getenv('USER')}", dest_value)
        project_path = os.path.join(disk_base_path, custom_path, backup_name)

    if run_cmd(f"rclone lsd '{project_path}'")[0]:
        print(f"{WARN} A folder for '{backup_name}' already exists at the destination.")
        if not confirm("Do you want to merge/update files into it? (N creates a duplicated folder)"):
            project_path = f"{project_path}_duplicated_{datetime.now().strftime('%Y%m%d')}"
            print(f"{INFO} A new folder will be used: {os.path.basename(project_path)}")
    
    if not confirm(f"Proceed with simple copy to {dest_value}?"):
        return False, None

    copy_cmd = f"rclone copy '{src_path}' '{project_path}' --progress --update --create-empty-src-dirs"
    success, output = run_cmd_with_progress(copy_cmd, f"Simple copy to {dest_value}", log_file)
    summary_lines = [line for line in output if "Transferred" in line or "Errors" in line or "Checks" in line]
    summary = summary_lines[-3:] if summary_lines else ["No summary available."]
    
    return success, {"destination": project_path, "summary": summary}

# ====== MAIN FUNCTION ======
def main():
    global start_time
    
    os.system("clear")
    print(f"{BOLD}{CYAN}✨ Manual NAS Backup Tool by Daury DiCaprio - v0.001 ✨{RESET}")
    print(f"\n{INFO} This tool helps you create two types of backups:")
    print(f"  1. {BOLD}Secure Backups:{RESET} Ideal for safety. Encrypted, versioned, and space-efficient.")
    print(f"  2. {BOLD}Simple Copies:{RESET} Ideal for archiving files to free up space while keeping them accessible.")

    check_tools()
    configured_remotes = check_rclone_config()
    
    print(f"\n{BOLD}Choose an action:{RESET}")
    print(f"{CYAN}1) Secure Backup{RESET} (Encrypted, version history - Recommended for safety)")
    print(f"{CYAN}2) Simple Incremental Copy{RESET} (Non-encrypted, direct file access - Ideal for archiving)")
    
    choice = get_input("Select an option (1/2)")
    if choice not in ['1', '2']:
        print(f"{ERR} Invalid option. Exiting."); sys.exit(1)
    
    print(f"\n{BOLD}📂 Select source folder:{RESET}")
    home = os.path.expanduser("~")
    folders = sorted([f for f in os.listdir(home) if os.path.isdir(os.path.join(home, f))])
    
    print(f"{YELLOW}0) Enter a custom path{RESET}")
    for i, folder in enumerate(folders, 1): print(f"{i}) {folder}")
    
    folder_choice = get_input("Select a folder")
    
    try:
        src_path = os.path.join(home, get_input(f"Enter path relative to Home ('{home}')")) if folder_choice == "0" else os.path.join(home, folders[int(folder_choice) - 1])
    except (ValueError, IndexError):
        print(f"{ERR} Invalid selection."); sys.exit(1)

    if not os.path.exists(src_path):
        print(f"{ERR} Source folder does not exist: {src_path}"); sys.exit(1)
    
    normalized_name = normalize_name(os.path.basename(src_path))
    
    if not confirm(f"\n{INFO} Source: {src_path}\nContinue with this folder?"): sys.exit(0)

    print(f"\n{BOLD}💾 Select PRIMARY destination:{RESET}")
    print(f"{INFO} To add more cloud options, first run: {BOLD}rclone config{RESET}")
    
    media_path = f"/run/media/{os.getenv('USER')}"
    disks = [d for d in os.listdir(media_path) if os.path.isdir(os.path.join(media_path, d))] if os.path.exists(media_path) else []
    
    options = {}
    idx = 1
    for disk in disks: options[str(idx)] = ("disk", disk); print(f"{GREEN}{idx}) External Disk: {disk}{RESET}"); idx += 1
    for remote in configured_remotes: options[str(idx)] = ("cloud", remote); print(f"{BLUE}{idx}) Cloud Remote: {remote}{RESET}"); idx += 1

    if not options: print(f"{ERR} No destinations found."); sys.exit(1)
    
    dest_choice = get_input("Select a destination")
    if dest_choice not in options: print(f"{ERR} Invalid selection."); sys.exit(1)
    
    destinations = [options[dest_choice]]
    
    primary_type, _ = destinations[0]
    if primary_type == 'disk' and configured_remotes and confirm("Also back up to a cloud remote?"):
        print(f"\n{BOLD}☁️ Select SECONDARY cloud destination:{RESET}")
        for i, remote in enumerate(configured_remotes, 1): print(f"{i}) {remote}")
        remote_choice = get_input("Select a cloud remote")
        try: destinations.append(("cloud", configured_remotes[int(remote_choice) - 1]))
        except (ValueError, IndexError): print(f"{WARN} Invalid selection. Skipping.")
    elif primary_type == 'cloud' and disks and confirm("Also back up to an external disk?"):
        print(f"\n{BOLD}💽 Select SECONDARY disk destination:{RESET}")
        for i, disk in enumerate(disks, 1): print(f"{i}) {disk}")
        disk_choice = get_input("Select a disk")
        try: destinations.append(("disk", disks[int(disk_choice) - 1]))
        except (ValueError, IndexError): print(f"{WARN} Invalid selection. Skipping.")

    destinations.sort(key=lambda x: x[0] == 'cloud')
        
    log_dir = os.path.join(home, "manual_nas_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    start_time = time.time()
    
    password = None
    if choice == '1':
        password = get_password("Enter password for secure repository", normalized_name)

    results = []
    for dest_type, dest_value in destinations:
        handler = handle_secure_backup if choice == '1' else handle_simple_copy
        args = (src_path, normalized_name, password, dest_type, dest_value, log_file) if choice == '1' else (src_path, normalized_name, dest_type, dest_value, log_file)
        
        success, result_data = handler(*args)
        if success:
            results.append(result_data)
        else:
            print(f"{ERR} Backup to {dest_value} failed. Halting subsequent backups.")
            break

    if not results:
        print(f"\n{ERR} No backups were completed. Check the log: {log_file}"); sys.exit(1)
        
    print(f"\n{OK} Operation finished in {format_time(time.time() - start_time)}!")
    print(f"📂 Source:      {src_path}")
    
    for i, result in enumerate(results, 1):
        print(f"\n{INFO}--- Summary for Backup #{i} ---{RESET}")
        print(f"  💾 Destination: {result.get('destination')}")
        for line in result.get('summary', []): print(f"    {line}")
        
    if choice == '1' and password:
        # --- NEW: Enhanced Password Display Box ---
        box_width = 60
        print(f"\n{WARN}┌{'─' * box_width}┐{RESET}")
        print(f"{WARN}│{' ' * box_width}│{RESET}")
        
        title = "--- IMPORTANT RECOVERY PASSWORD ---"
        print(f"{WARN}│{title.center(box_width)}│{RESET}")
        print(f"{WARN}│{' ' * box_width}│{RESET}")

        pwd_line = f"{BOLD}{YELLOW}{password}{RESET}"
        # This part is a bit tricky to center with color codes, so we'll left-align with padding
        print(f"{WARN}│   Password: {pwd_line}{' ' * (box_width - 15 - len(password))}│{RESET}")
        print(f"{WARN}│{' ' * box_width}│{RESET}")

        warning_line = "Save this in a secure password manager!"
        print(f"{WARN}│{warning_line.center(box_width)}│{RESET}")
        print(f"{WARN}│{' ' * box_width}│{RESET}")
        print(f"{WARN}└{'─' * box_width}┘{RESET}")

    print(f"\n📄 Detailed log saved to: {log_file}")
    
    handle_installation()
    print(f"\n{GREEN}All done!{RESET}")

if __name__ == "__main__":
    main()
