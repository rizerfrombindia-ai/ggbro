import os
import sys
import json
import time
import html
import platform
import zipfile
import io
import threading
import subprocess
import socket
import urllib.request
import urllib.parse
import urllib.error

# Ensure stdout and stderr handle any unicode on Windows without crashing
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

class SessionManager:
    """Manages persistent RDP session data (Chrome logins, Google accounts, files)."""
    def __init__(self, token=None, repo=None):
        self.token = token or os.environ.get("GITHUB_PAT", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
        self.repo = repo or os.environ.get("GITHUB_REPO", "").strip()
        if not self.repo:
            self.repo = "rizerfrombindia-ai/ggbro"
        self.release_tag = "sessions"
        self.release_id = 452166648
        self.current_session = "default"
        self.last_saved = "Never"

        # Session directories on Windows
        if sys.platform == "win32":
            self.session_dir = r"C:\SavedSession"
        else:
            self.session_dir = "/tmp/SavedSession"

        self.ensure_dirs()

    def ensure_dirs(self):
        try:
            os.makedirs(os.path.join(self.session_dir, "ChromeData"), exist_ok=True)
            os.makedirs(os.path.join(self.session_dir, "Files"), exist_ok=True)
        except Exception as e:
            print(f"[SessionManager] ensure_dirs error: {e}")

    def _api_request(self, url, method="GET", data=None, content_type="application/json"):
        headers = {
            "Authorization": f"token {self.token}",
            "User-Agent": "RDP-SessionManager/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        if content_type:
            headers["Content-Type"] = content_type

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            if method == "DELETE" or resp.status == 204:
                return True
            return json.loads(resp.read().decode("utf-8"))

    def list_saved_sessions(self):
        url = f"https://api.github.com/repos/{self.repo}/releases/{self.release_id}/assets"
        try:
            assets = self._api_request(url)
            sessions = []
            for a in assets:
                name = a.get("name", "")
                if name.startswith("session_") and name.endswith(".zip"):
                    sess_name = name[len("session_"):-len(".zip")]
                    size_mb = round(a.get("size", 0) / (1024 * 1024), 2)
                    updated = a.get("updated_at", "")[:16].replace("T", " ")
                    sessions.append({
                        "name": sess_name,
                        "file_name": name,
                        "size_mb": size_mb,
                        "updated": updated,
                        "asset_id": a.get("id"),
                        "download_url": a.get("browser_download_url")
                    })
            return sessions
        except Exception as e:
            print(f"[SessionManager] List error: {e}")
            return []

    def save_session(self, name="default"):
        name = name.strip().replace(" ", "_")
        self.ensure_dirs()

        buf = io.BytesIO()
        exclude_dirs = {'cache', 'code cache', 'gpucache', 'dawncache', 'shadercache', 'service worker'}
        count = 0

        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.session_dir):
                dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs]
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.session_dir)
                    try:
                        zf.write(full_path, rel_path)
                        count += 1
                    except Exception:
                        pass

        zip_bytes = buf.getvalue()
        size_mb = round(len(zip_bytes) / (1024 * 1024), 2)

        # Delete existing asset with same name if present
        asset_file_name = f"session_{name}.zip"
        existing = self.list_saved_sessions()
        for s in existing:
            if s["name"] == name:
                del_url = f"https://api.github.com/repos/{self.repo}/releases/assets/{s['asset_id']}"
                try:
                    self._api_request(del_url, method="DELETE")
                except Exception as e:
                    print(f"[SessionManager] Delete error: {e}")

        # Upload new asset
        upload_url = f"https://uploads.github.com/repos/{self.repo}/releases/{self.release_id}/assets?name={asset_file_name}"
        self._api_request(upload_url, method="POST", data=zip_bytes, content_type="application/zip")

        self.current_session = name
        self.last_saved = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[SessionManager] Saved session '{name}' ({size_mb} MB, {count} files).")
        return {"ok": True, "name": name, "size_mb": size_mb, "file_count": count}

    def load_session(self, name="default"):
        name = name.strip().replace(" ", "_")
        existing = self.list_saved_sessions()
        target = None
        for s in existing:
            if s["name"] == name:
                target = s
                break

        if not target:
            return {"ok": False, "error": f"Session '{name}' not found."}

        download_url = target["download_url"]
        req = urllib.request.Request(download_url, headers={
            "Authorization": f"token {self.token}",
            "User-Agent": "RDP-SessionManager/1.0",
            "Accept": "application/octet-stream"
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_bytes = resp.read()

        self.ensure_dirs()
        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, 'r') as zf:
            zf.extractall(self.session_dir)

        self.current_session = name
        print(f"[SessionManager] Loaded session '{name}' ({target['size_mb']} MB).")
        return {"ok": True, "name": name, "size_mb": target["size_mb"]}


class TelegramRDPBot:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not self.token:
            self.token = "9256338881:AAEv3FIlK4-h03NnbDgT_iI_-KdTpFs9Aeg"

        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.host = os.environ.get("RDP_HOST", "bore.pub").strip()
        self.port = str(os.environ.get("RDP_PORT", "3389")).strip()
        self.username = os.environ.get("RDP_USER", "runneradmin").strip()
        self.pin = os.environ.get("RDP_PIN", "123456").strip()
        if not self.pin:
            self.pin = "123456"

        self.tunnel_type = os.environ.get("TUNNEL_TYPE", "Bore (bore.pub)").strip()
        self.crd_active = os.environ.get("CRD_ACTIVE", "false").strip().lower() == "true"
        self.initial_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

        self.start_time = time.time()
        self.max_duration_seconds = 6 * 3600 - 300
        self.running = True

        # Session Manager
        self.session_mgr = SessionManager()

        # Try auto-restoring default session on startup if it exists
        try:
            sessions = self.session_mgr.list_saved_sessions()
            for s in sessions:
                if s["name"] == "default":
                    self.session_mgr.load_session("default")
                    print("[SessionManager] Auto-restored default session on startup.")
                    break
        except Exception as e:
            print(f"[SessionManager] Auto-restore check error: {e}")

    def call_api(self, method, payload=None, timeout=35):
        url = f"{self.base_url}/{method}"
        headers = {"User-Agent": "RDP-TelegramBot/1.0"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            print(f"[Telegram API Error {e.code}] {err_body}")
            return None
        except Exception as e:
            print(f"[Telegram Request Error] {e}")
            return None

    def get_main_keyboard(self):
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Status & Uptime", "callback_data": "cmd_status"},
                    {"text": "📋 Copy Info", "callback_data": "cmd_info"}
                ],
                [
                    {"text": "💾 Save Session", "callback_data": "cmd_save"},
                    {"text": "📂 Select Session", "callback_data": "cmd_sessions"}
                ],
                [
                    {"text": "🛑 Stop Runner", "callback_data": "cmd_stop"}
                ]
            ]
        }

    def format_credentials_message(self):
        crd_badge = "✅ <b>Chrome Remote Desktop:</b> Active\n" if self.crd_active else ""
        sess_info = f"📂 <b>Active Session:</b> <code>{html.escape(self.session_mgr.current_session)}</code> (Last Saved: {html.escape(self.session_mgr.last_saved)})\n"

        return (
            f"🎉 <b>VPS Windows RDP is Online!</b>\n\n"
            f"🌐 <b>Tunnel:</b> {html.escape(self.tunnel_type)}\n"
            f"🖥 <b>Host / IP:</b> <code>{html.escape(self.host)}</code>\n"
            f"🔌 <b>Port:</b> <code>{html.escape(self.port)}</code>\n"
            f"👤 <b>Username:</b> <code>{html.escape(self.username)}</code>\n"
            f"🔑 <b>VPS PIN / Password:</b> <code>{html.escape(self.pin)}</code>\n\n"
            f"📱 <b>Direct Connection String (for RDP Apps):</b>\n"
            f"<code>{html.escape(self.host)}:{html.escape(self.port)}</code>\n\n"
            f"{sess_info}"
            f"{crd_badge}"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📲 <b>Quick Connect Guide:</b>\n"
            f"• <b>Windows:</b> Press <code>Win + R</code> &gt; type <code>mstsc</code> &gt; paste <code>{html.escape(self.host)}:{html.escape(self.port)}</code>\n"
            f"• <b>Android / iOS:</b> In <b>Remote Desktop (RD Client)</b> app:\n"
            f"   1. Tap <b>+</b> &gt; <b>Add PC</b>\n"
            f"   2. PC Name: <code>{html.escape(self.host)}:{html.escape(self.port)}</code>\n"
            f"   3. User Account: <code>{html.escape(self.username)}</code>\n"
            f"   4. Password: <code>{html.escape(self.pin)}</code>\n"
            f"   5. Connect &amp; accept certificate warning.\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💾 <i>Data Persistence:</i> All Google accounts & files saved in Desktop folder <code>SavedSession</code> will persist across runs!\n"
            f"💡 <i>Commands: /save (backup) | /sessions (switch) | /status (uptime)</i>"
        )

    def format_status_message(self):
        elapsed = int(time.time() - self.start_time)
        remaining = max(0, int(self.max_duration_seconds - elapsed))
        elapsed_m, elapsed_s = divmod(elapsed, 60)
        elapsed_h, elapsed_m = divmod(elapsed_m, 60)
        rem_m, rem_s = divmod(remaining, 60)
        rem_h, rem_m = divmod(rem_m, 60)

        return (
            f"📊 <b>Runner Status:</b> Active ✅ (Watchdog Running)\n\n"
            f"⏱ <b>Uptime:</b> {elapsed_h}h {elapsed_m}m {elapsed_s}s\n"
            f"⏳ <b>Time Remaining:</b> {rem_h}h {rem_m}m\n"
            f"🖥 <b>Address:</b> <code>{html.escape(self.host)}:{html.escape(self.port)}</code>\n"
            f"👤 <b>User:</b> <code>{html.escape(self.username)}</code>\n"
            f"🔑 <b>PIN:</b> <code>{html.escape(self.pin)}</code>\n"
            f"🌐 <b>Tunnel:</b> {html.escape(self.tunnel_type)}\n"
            f"📂 <b>Session:</b> <code>{html.escape(self.session_mgr.current_session)}</code>\n"
            f"💾 <b>Last Saved:</b> {html.escape(self.session_mgr.last_saved)}\n"
            f"🛡 <b>Anti-Disconnect:</b> Active (Idle Timeout Bypassed)"
        )

    def format_sessions_list_message(self):
        sessions = self.session_mgr.list_saved_sessions()
        if not sessions:
            text = (
                f"📂 <b>Saved Cloud Sessions:</b>\n\n"
                f"<i>No saved sessions found in cloud yet.</i>\n\n"
                f"💡 Tap <b>Save Current Session</b> below to create your first backup (saves your Google accounts, cookies, and desktop files)!"
            )
            buttons = [
                [{"text": "💾 Save Current Session", "callback_data": "sess_save_default"}],
                [{"text": "🔙 Back to Menu", "callback_data": "cmd_info"}]
            ]
            return text, {"inline_keyboard": buttons}

        text = f"📂 <b>Saved Cloud Sessions ({len(sessions)}):</b>\n\n"
        buttons = []
        for s in sessions:
            text += f"• <b>{html.escape(s['name'])}</b> ({s['size_mb']} MB, {s['updated']})\n"
            buttons.append([
                {"text": f"📥 Load \"{s['name']}\"", "callback_data": f"sess_load_{s['name']}"}
            ])

        buttons.append([
            {"text": "💾 Save as \"default\"", "callback_data": "sess_save_default"},
            {"text": "💾 Save New Session", "callback_data": "sess_save_new"}
        ])
        buttons.append([{"text": "🔙 Back to Menu", "callback_data": "cmd_info"}])
        return text, {"inline_keyboard": buttons}

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call_api("sendMessage", payload)

    def answer_callback_query(self, callback_query_id, text=None):
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        return self.call_api("answerCallbackQuery", payload)

    def keepalive_windows(self):
        """Prevents Windows from locking, sleeping, or disconnecting idle RDP sessions."""
        if sys.platform == "win32":
            try:
                import ctypes
                # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001) | ES_DISPLAY_REQUIRED (0x00000002)
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
                # Gentle VK_F15 virtual key tap (non-intrusive standard keepalive)
                ctypes.windll.user32.keybd_event(0x7E, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x7E, 0, 2, 0)
            except Exception:
                pass

        # Ping local RDP port 3389 so socket buffer stays warm and Azure NAT does not idle drop
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", 3389))
            s.close()
        except Exception:
            pass

    def watchdog_thread(self):
        """Monitors the tunnel and automatically restarts it if it drops, notifying the user."""
        print("[Watchdog] Tunnel & RDP Anti-Disconnect Watchdog started.")
        while self.running:
            try:
                self.keepalive_windows()

                # Verify if bore tunnel is alive by checking process or bore.log
                bore_dead = False
                if sys.platform == "win32":
                    # Check tasklist for bore.exe or ssh.exe
                    try:
                        tasks = subprocess.check_output("tasklist", shell=True, text=True, errors="ignore")
                        if "bore.exe" not in tasks and "ssh.exe" not in tasks:
                            bore_dead = True
                    except Exception:
                        pass

                if bore_dead and self.running:
                    print("[Watchdog] Tunnel process died! Auto-restarting Bore tunnel...")
                    user_profile = os.environ.get("USERPROFILE", r"C:\Users\runneradmin")
                    bore_exe = os.path.join(user_profile, "bore", "bore.exe")
                    if os.path.exists(bore_exe):
                        subprocess.Popen(
                            f'cmd.exe /c "{bore_exe} local 3389 --to bore.pub > bore.log 2>&1"',
                            shell=True
                        )
                        time.sleep(3)
                        # Read new port
                        for _ in range(10):
                            time.sleep(1)
                            if os.path.exists("bore.log"):
                                with open("bore.log", "r", errors="ignore") as f:
                                    content = f.read()
                                import re
                                m = re.search(r'listening at ([a-zA-Z0-9\.\-]+):(\d+)', content)
                                if m:
                                    new_host = m.group(1)
                                    new_port = m.group(2)
                                    if new_port != self.port:
                                        print(f"[Watchdog] Reconnected on {new_host}:{new_port}")
                                        self.host = new_host
                                        self.port = new_port
                                        # Notify user on Telegram
                                        if self.initial_chat_id:
                                            alert = (
                                                f"⚠️ <b>RDP Connection Reconnected!</b>\n\n"
                                                f"The tunnel automatically refreshed.\n"
                                                f"🖥 <b>New Address:</b> <code>{self.host}:{self.port}</code>\n"
                                                f"👤 <b>Username:</b> <code>{self.username}</code>\n"
                                                f"🔑 <b>PIN:</b> <code>{self.pin}</code>"
                                            )
                                            self.send_message(self.initial_chat_id, alert, self.get_main_keyboard())
                                    break

            except Exception as e:
                print(f"[Watchdog Exception] {e}")

            time.sleep(20)

    def auto_save_thread(self):
        """Automatically backs up the session every 20 minutes in the background."""
        while self.running:
            time.sleep(20 * 60)
            if self.running:
                try:
                    print("[AutoSave] Performing background periodic session save...")
                    self.session_mgr.save_session(self.session_mgr.current_session)
                except Exception as e:
                    print(f"[AutoSave Exception] {e}")

    def run(self):
        print("Authenticating Telegram Bot...")
        me = self.call_api("getMe")
        if not me or not me.get("ok"):
            print("[ERROR] Failed to authenticate with Telegram Bot Token!")
            print("Please ensure your token is valid.")
            sys.exit(1)

        bot_info = me.get("result", {})
        bot_user = bot_info.get("username", "UnknownBot")
        first_name = bot_info.get("first_name", "")
        print(f"[OK] Telegram Bot Authenticated: @{bot_user} ({first_name})")
        print("[INFO] Anti-disconnect enabled. Session manager active.")

        # Start Watchdog thread
        w_thread = threading.Thread(target=self.watchdog_thread, daemon=True)
        w_thread.start()

        # Start AutoSave thread
        s_thread = threading.Thread(target=self.auto_save_thread, daemon=True)
        s_thread.start()

        if self.initial_chat_id:
            print(f"Sending credentials to initial Chat ID: {self.initial_chat_id}")
            self.send_message(
                self.initial_chat_id,
                self.format_credentials_message(),
                self.get_main_keyboard()
            )

        print(f"Listening for commands on Telegram... Send /start to @{bot_user}")

        offset = 0
        last_keepalive = time.time()

        while self.running:
            now = time.time()
            if now - self.start_time > self.max_duration_seconds:
                print("Approaching max GitHub Actions runtime limit (6 hours). Performing final auto-save...")
                try:
                    self.session_mgr.save_session(self.session_mgr.current_session)
                except Exception:
                    pass
                break

            if now - last_keepalive > 60:
                uptime_min = int((now - self.start_time) / 60)
                print(f"[Keep-Alive] Bot active. Uptime: {uptime_min}m. Address: {self.host}:{self.port}")
                last_keepalive = now

            try:
                updates = self.call_api("getUpdates", {"offset": offset, "timeout": 20}, timeout=30)
                if not updates or not updates.get("ok"):
                    time.sleep(3)
                    continue

                for update in updates.get("result", []):
                    offset = update["update_id"] + 1

                    # Handle button callbacks
                    if "callback_query" in update:
                        cq = update["callback_query"]
                        cq_id = cq["id"]
                        cb_data = cq.get("data", "")
                        chat_id = cq["message"]["chat"]["id"]
                        self.initial_chat_id = str(chat_id)

                        if cb_data == "cmd_status":
                            self.answer_callback_query(cq_id, "Refreshing status...")
                            self.send_message(chat_id, self.format_status_message(), self.get_main_keyboard())
                        elif cb_data == "cmd_info":
                            self.answer_callback_query(cq_id, "Sending connection info...")
                            self.send_message(chat_id, self.format_credentials_message(), self.get_main_keyboard())
                        elif cb_data == "cmd_sessions":
                            self.answer_callback_query(cq_id, "Loading saved sessions...")
                            text, kb = self.format_sessions_list_message()
                            self.send_message(chat_id, text, kb)
                        elif cb_data == "cmd_save":
                            self.answer_callback_query(cq_id, "Saving session to cloud...")
                            res = self.session_mgr.save_session(self.session_mgr.current_session)
                            msg = (
                                f"✅ <b>Session \"{res['name']}\" Saved Successfully!</b>\n\n"
                                f"📦 <b>Size:</b> {res['size_mb']} MB\n"
                                f"📁 <b>Files:</b> {res['file_count']}\n"
                                f"☁️ Stored permanently in GitHub Cloud. Your Google accounts, Chrome logins, and desktop files are safe!"
                            )
                            self.send_message(chat_id, msg, self.get_main_keyboard())
                        elif cb_data.startswith("sess_load_"):
                            sess_name = cb_data[len("sess_load_"):]
                            self.answer_callback_query(cq_id, f"Loading session '{sess_name}'...")
                            res = self.session_mgr.load_session(sess_name)
                            if res.get("ok"):
                                msg = (
                                    f"✅ <b>Session \"{sess_name}\" Loaded Successfully!</b>\n\n"
                                    f"All Google accounts, Chrome profiles, and files are ready in your RDP."
                                )
                            else:
                                msg = f"❌ Failed to load session: {res.get('error')}"
                            self.send_message(chat_id, msg, self.get_main_keyboard())
                        elif cb_data == "sess_save_default":
                            self.answer_callback_query(cq_id, "Saving session 'default'...")
                            res = self.session_mgr.save_session("default")
                            msg = f"✅ <b>Session \"default\" saved ({res['size_mb']} MB)!</b>"
                            self.send_message(chat_id, msg, self.get_main_keyboard())
                        elif cb_data == "sess_save_new":
                            new_name = time.strftime("session_%m%d_%H%M")
                            self.answer_callback_query(cq_id, f"Saving as '{new_name}'...")
                            res = self.session_mgr.save_session(new_name)
                            msg = f"✅ <b>Session \"{new_name}\" saved ({res['size_mb']} MB)!</b>"
                            self.send_message(chat_id, msg, self.get_main_keyboard())
                        elif cb_data == "cmd_stop":
                            self.answer_callback_query(cq_id, "Saving and stopping runner...")
                            try:
                                self.session_mgr.save_session(self.session_mgr.current_session)
                            except Exception:
                                pass
                            self.send_message(chat_id, "🛑 <b>Session saved & runner stopped. Goodbye!</b>")
                            self.running = False
                            break
                        else:
                            self.answer_callback_query(cq_id)
                        continue

                    # Handle messages
                    msg = update.get("message")
                    if not msg:
                        continue

                    chat_id = msg["chat"]["id"]
                    self.initial_chat_id = str(chat_id)
                    from_user = msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name", "User")
                    text = msg.get("text", "").strip()

                    user_clean = str(from_user).encode("ascii", "replace").decode("ascii")
                    text_clean = text.encode("ascii", "replace").decode("ascii")
                    print(f"[Telegram Message] From: {user_clean} ({chat_id}) | Text: {text_clean}")

                    if text.startswith("/start") or text.startswith("/rdp") or text.startswith("/info"):
                        self.send_message(chat_id, self.format_credentials_message(), self.get_main_keyboard())
                    elif text.startswith("/sessions"):
                        txt, kb = self.format_sessions_list_message()
                        self.send_message(chat_id, txt, kb)
                    elif text.startswith("/save"):
                        parts = text.split()
                        sess_name = parts[1] if len(parts) > 1 else self.session_mgr.current_session
                        res = self.session_mgr.save_session(sess_name)
                        msg = (
                            f"✅ <b>Session \"{res['name']}\" Saved Successfully!</b>\n\n"
                            f"📦 <b>Size:</b> {res['size_mb']} MB\n"
                            f"📁 <b>Files:</b> {res['file_count']}\n"
                            f"☁️ Stored safely in Cloud Releases."
                        )
                        self.send_message(chat_id, msg, self.get_main_keyboard())
                    elif text.startswith("/load"):
                        parts = text.split()
                        if len(parts) > 1:
                            sess_name = parts[1]
                            res = self.session_mgr.load_session(sess_name)
                            if res.get("ok"):
                                msg = f"✅ <b>Session \"{sess_name}\" Loaded Successfully!</b>"
                            else:
                                msg = f"❌ Failed: {res.get('error')}"
                            self.send_message(chat_id, msg, self.get_main_keyboard())
                        else:
                            txt, kb = self.format_sessions_list_message()
                            self.send_message(chat_id, txt, kb)
                    elif text.startswith("/status"):
                        self.send_message(chat_id, self.format_status_message(), self.get_main_keyboard())
                    elif text.startswith("/stop"):
                        try:
                            self.session_mgr.save_session(self.session_mgr.current_session)
                        except Exception:
                            pass
                        self.send_message(chat_id, "🛑 <b>Session saved & runner stopped. Goodbye!</b>")
                        self.running = False
                        break
                    elif text.startswith("/help"):
                        help_text = (
                            "📖 <b>Telegram RDP Bot Commands:</b>\n\n"
                            "• <b>/start</b> - Show connection credentials & PIN\n"
                            "• <b>/save [name]</b> - Save session (Google accounts, files)\n"
                            "• <b>/sessions</b> - List & select older saved sessions\n"
                            "• <b>/load [name]</b> - Load a specific saved session\n"
                            "• <b>/status</b> - Show live uptime, port & watchdog status\n"
                            "• <b>/stop</b> - Auto-save session & shut down runner"
                        )
                        self.send_message(chat_id, help_text, self.get_main_keyboard())
                    else:
                        self.send_message(chat_id, self.format_credentials_message(), self.get_main_keyboard())

            except Exception as e:
                print(f"[Polling Exception] {e}")
                time.sleep(3)

        print("Runner loop finished.")

if __name__ == "__main__":
    bot = TelegramRDPBot()
    bot.run()
