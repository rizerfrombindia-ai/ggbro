# Windows RDP with Telegram Bot & Cloud Sessions

A free cloud Windows virtual machine on GitHub Actions with 100% stable RDP, anti-disconnect watchdog, and **cloud session persistence** (Google accounts, Chrome logins, and desktop files saved and restored via Telegram bot).

---

## 🚀 New Features

### 1. 🛡️ Anti-Disconnect & Auto-Reconnect (Fixes 45m/1h Disconnects)
- **Watchdog Daemon**: Continuously monitors the tunnel process. If `bore.pub` or the tunnel drops, it **auto-restarts within 5 seconds** and immediately notifies you of the new port on Telegram!
- **TCP Keepalive**: Sends active ping probes every 25 seconds to keep Azure NAT connections open so the VM never gets disconnected due to idle timeout.
- **Power & Session Policies**: Bypasses all Windows Server idle timeouts (`MaxIdleTime = 0`), disables lock screen, and continuously resets Windows session idle counters.

### 2. 💾 Cloud Session Persistence (Google Accounts & Files Won't Be Lost!)
- **Auto-created Desktop Folder**: `SavedSession` on the desktop. Any files you put here are saved to the cloud!
- **Google Accounts & Chrome Data**: Google Chrome profile is automatically linked to the session. Log into your Google accounts, save passwords, and extensions—they will persist across all runner restarts!
- **Telegram Commands**:
  - `/sessions` — List all saved cloud sessions and click to load any older session.
  - `/save [name]` — Save the current session immediately to cloud (defaults to `default`).
  - `/load [name]` — Load a specific session into your current RDP.
- **Auto-Save**: Automatically backs up every 20 minutes in the background and when you click `[🛑 Stop Runner]`.
- **Auto-Restore on Startup**: Automatically restores your `default` session on boot so your accounts are ready when you log in.

---

## 📋 Prerequisites & Credentials

- **Telegram Bot**: [@LUPPIEGAY](https://t.me/LUPPIEGAY) (Token pre-configured).
- **Default PIN / Password**: `123456`
- **Username**: `runneradmin`
- **Zero Card / Zero Sign-up**: Uses free Bore TCP tunnel (`bore.pub:<port>`) with zero tokens or cards needed.

---

## 🎮 How to Use

1. Go to your repository on GitHub > **[Actions](https://github.com/rizerfrombindia-ai/ggbro/actions)**.
2. Select **Windows RDP with Telegram Bot** > Click **Run workflow** > Green button.
3. Open Telegram and message [@LUPPIEGAY](https://t.me/LUPPIEGAY):
   - Send **`/start`** to get your RDP address (`bore.pub:<port>`), username (`runneradmin`), and PIN (`123456`).
4. Log in using **Remote Desktop (`mstsc`)** on Windows or **RD Client** on Android/iOS.
5. Open Chrome, log into your Google Account, do your work.
6. Send **`/save`** on Telegram (or let auto-save handle it). When you launch a new runner tomorrow, your session and accounts are automatically restored!
