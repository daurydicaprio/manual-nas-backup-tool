# Manual NAS Backup Tool

**Author:** [Daury DiCaprio](https://daurydicaprio.com)  
**License:** MIT  
**Motto:** #VERyGoodforlife

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful interactive Python script for creating two types of backups: secure, encrypted, versioned backups using **Restic**, and simple, incremental, direct-access file copies using **Rclone**.

---

### Creator's Journey & Purpose

This tool was born out of a real-world need: managing project files on a laptop (a Dell XPS) with limited storage. The goal was to create a reliable system to:
1.  **Archive** completed projects to an external drive and cloud storage to free up local space.
2.  **Secure** critical, in-progress work with versioned, encrypted backups.

Currently, I use it weekly to keep my main machine clean and my data safe across a local HDD and Google Drive. The future plan is to deploy this tool on a dedicated home server (a Beelink NAS with Proxmox) and a Raspberry Pi to create a fully automated, robust, on-site and off-site backup system.

### ✅ Key Features

-   **Dual Backup Modes:** Choose between ultra-secure, encrypted backups or simple, accessible file copies.
-   **Dual Destination:** Back up to a local drive and the cloud in a single, reliable operation (local first, then cloud).
-   **Interactive & Safe:** Guides you through every step with clear prompts and warnings to prevent accidental data loss.
-   **Flexible:** Works with any external drive and any cloud storage service configured with Rclone (Google Drive, Dropbox, etc.).
-   **Customizable:** Allows you to specify custom destination paths for better organization.

### 🛠️ Requirements

Before you start, make sure you have these three tools installed:

1.  **Restic:** The engine for secure, encrypted backups.
2.  **Rclone:** The "swiss army knife" for cloud storage, used as a backend for both backup types.
3.  **FUSE:** Required to mount and explore your encrypted backups as a virtual drive (`fuse3` on Arch, `fuse` on Debian/Ubuntu).

### 🚀 Step-by-Step Usage

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/manual-nas-backup-tool.git
    cd manual-nas-backup-tool
    ```

2.  **Install Dependencies:**
    -   On Arch Linux: `sudo pacman -S restic rclone fuse3`
    -   On Debian/Ubuntu/Raspberry Pi OS: `sudo apt update && sudo apt install restic rclone fuse -y`

3.  **Configure Rclone:** If you want to back up to the cloud, you must configure Rclone first. It's a one-time setup.
    ```bash
    rclone config
    ```
    Follow the prompts to add your cloud storage provider (e.g., Google Drive).

4.  **Make the Script Executable:**
    ```bash
    chmod +x manual-nas-tool.py
    ```

5.  **Run the Tool:**
    ```bash
    ./manual-nas-tool.py
    ```
    The script will guide you through the rest! At the end of the first successful run, it will offer to install itself as a system command (`manual-nas-tool`) for easy access.

---

### 🔑 Accessing Your Encrypted Backups

Your secure backups are encrypted databases. You cannot see the files directly. To access them, you use `restic` to mount the backup as a virtual, read-only drive.

1.  **Create a mount point (an empty folder):**
    ```bash
    mkdir ~/my_decrypted_backup
    ```

2.  **Mount the repository (example for Google Drive):**
    ```bash
    # For a cloud backup:
    restic --repo rclone:<your_remote_name>:manual_nas_encrypted/<project_name>_encrypted/ mount ~/my_decrypted_backup

    # For a local disk backup:
    restic --repo /path/to/your/disk/manual_nas_encrypted/<project_name>_encrypted/ mount ~/my_decrypted_backup
    ```

3.  **Enter your password** when prompted.

4.  **Explore your files!** You can now browse the `~/my_decrypted_backup` folder with your file manager. Look inside the `snapshots/latest/` directory.

5.  **Unmount when finished:** Go back to the terminal and press `Ctrl + C`.

> ⚠️ **THE GOLDEN RULE: SAVE YOUR PASSWORD!**
> The password you use for a secure backup is your **only key** to your data. If you lose it, your data is gone forever. There is no recovery. **Save it in a trusted password manager immediately.**

---

### 🤖 Automation (Optional)

#### Simple Automation with Cron

You can run a backup automatically at a set time. Run `crontab -e` and add a line like this to run a backup every day at 3:00 AM. *Note: This works best if your script is modified to be non-interactive.*

```bash
0 3 * * * /path/to/your/manual-nas-tool.py --non-interactive --source /home/user/projects --dest gdrive --secure
```

#### Advanced Automation with Systemd

For better reliability and logging on a dedicated server (like a Raspberry Pi or NAS), using a `systemd timer` is the modern, professional standard. It's more complex to set up (requiring a `.service` and a `.timer` file) but offers huge benefits:
-   **Superior Logging:** Every run is logged in the system journal (`journalctl`).
-   **Increased Reliability:** It can run a missed backup as soon as the system boots up.

---

**MIT License** © 2025 Daury DiCaprio
