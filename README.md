# Windows RDP with Telegram Bot & Ngrok/Pinggy

This GitHub Actions workflow launches a free cloud Windows virtual machine, sets up an RDP (Remote Desktop) server, and connects it to a **Telegram Bot**. 

When you send `/start` to your Telegram Bot, it immediately replies with your **IP/Host, Port, Username, and VPS PIN**, allowing you to connect from any **Windows PC (`mstsc`)** or **Android/iOS Remote Desktop app (RD Client APK)**.

---

## 🚀 Features

- **Telegram Bot Integration:** Authenticates your bot and provides connection credentials when you send `/start`.
- **100% Working RDP Connection:**
  - Automatic TCP tunneling via **Ngrok** (recommended for ultra-stable sessions) or **Pinggy** (zero-setup free fallback).
  - Automatically disables Windows Password Complexity so simple PINs (e.g. `123456`) work without policy errors.
  - Configures Network Level Authentication (NLA) so mobile APKs and Windows apps connect without rejection.
- **Interactive Bot Commands:**
  - `/start` or `/rdp` — Receive current IP, Port, Username, PIN, and full address.
  - `/status` — View runner uptime, remaining time, and system details.
  - `/stop` — Safely shut down the runner session.
  - Interactive inline buttons (`🔄 Status & Uptime`, `📋 Copy Info`, `🛑 Stop Runner`).
- **Optional Chrome Remote Desktop (CRD):** Still supports Google CRD headless code if you wish to run CRD alongside RDP.

---

## 📋 Prerequisites

1. **Telegram Bot Token:**
   - Open Telegram and message [@BotFather](https://t.me/BotFather).
   - Send `/newbot`, choose a name and username.
   - Copy the API token provided (e.g., `7123456789:AAH...`).
2. **Ngrok Auth Token (Recommended for 100% stability):**
   - Sign up for a free account at [ngrok.com](https://ngrok.com).
   - Copy your authtoken from the [Ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken).
   - *(Note: If you leave this empty, the workflow automatically falls back to Pinggy SSH tunnel).*

---

## ⚙️ How to Run on GitHub Actions

1. Push or upload this repository to GitHub.
2. In your GitHub repository, click on the **Actions** tab.
3. Select **Windows RDP with Telegram Bot** on the left menu.
4. Click **Run workflow** and fill in the inputs:
   - **`telegram_token`**: Paste your Telegram Bot token (*Required*).
   - **`ngrok_token`**: Paste your Ngrok auth token (*Recommended*).
   - **`pin`**: Set your VPS PIN / Password (*Default: `123456`*).
   - **`chat_id`**: *(Optional)* Your Telegram chat ID if you want details sent immediately without pressing `/start`.
   - **`code`**: *(Optional)* Chrome Remote Desktop command if you also want CRD.
5. Click the green **Run workflow** button.

---

## 📱 How to Connect

1. Wait about 1-2 minutes for the workflow to initialize.
2. Open Telegram and open your bot.
3. Send **`/start`** to your bot.
4. The bot will send you:
   - **Host / IP:** `0.tcp.ap.ngrok.io` (or Pinggy link)
   - **Port:** `12345`
   - **Username:** `runneradmin` (or `Administrator`)
   - **PIN / Password:** `123456`
   - **Full Address:** `0.tcp.ap.ngrok.io:12345`

### Connecting from Windows PC (`mstsc`):
1. Press `Win + R`, type `mstsc`, and press **Enter**.
2. In **Computer**, enter the `Host:Port` (e.g. `0.tcp.ap.ngrok.io:12345`).
3. Click **Connect**.
4. Enter Username: `runneradmin` and Password: your `PIN` (`123456`).
5. If prompted with a certificate warning, click **Yes / Connect**.

### Connecting from Android or iOS (RD Client APK):
1. Install **Microsoft Remote Desktop** (or RD Client APK) from Google Play Store or App Store.
2. Tap the **`+`** icon &gt; **Add PC**.
3. In **PC Name**, enter `Host:Port` (e.g. `0.tcp.ap.ngrok.io:12345`).
4. In **User Account**, tap *Add user account*:
   - Username: `runneradmin`
   - Password: your `PIN` (`123456`)
5. Save and tap the PC tile to connect.
