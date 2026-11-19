import os
import sys
import json
import time
import html
import platform
import urllib.request
import urllib.parse
import urllib.error

class TelegramRDPBot:
    def __init__(self):
        # Read environment variables with hardcoded fallbacks
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not self.token:
            self.token = "9256338881:AAEv3FIlK4-h03NnbDgT_iI_-KdTpFs9Aeg"

        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.host = os.environ.get("RDP_HOST", "127.0.0.1").strip()
        self.port = str(os.environ.get("RDP_PORT", "3389")).strip()
        self.username = os.environ.get("RDP_USER", "runneradmin").strip()
        self.pin = os.environ.get("RDP_PIN", "123456").strip()
        if not self.pin:
            self.pin = "123456"

        self.tunnel_type = os.environ.get("TUNNEL_TYPE", "Ngrok").strip()
        self.crd_active = os.environ.get("CRD_ACTIVE", "false").strip().lower() == "true"
        self.initial_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

        self.start_time = time.time()
        # GitHub Actions max job duration is 6 hours; shut down gracefully 5 mins before
        self.max_duration_seconds = 6 * 3600 - 300
        self.running = True

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

    def get_inline_keyboard(self):
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Status & Uptime", "callback_data": "cmd_status"},
                    {"text": "📋 Copy Info", "callback_data": "cmd_info"}
                ],
                [
                    {"text": "🛑 Stop Runner", "callback_data": "cmd_stop"}
                ]
            ]
        }

    def format_credentials_message(self):
        crd_badge = "✅ <b>Chrome Remote Desktop:</b> Active\n" if self.crd_active else ""
        return (
            f"🎉 <b>VPS Windows RDP is Online!</b>\n\n"
            f"🌐 <b>Tunnel:</b> {html.escape(self.tunnel_type)}\n"
            f"🖥 <b>Host / IP:</b> <code>{html.escape(self.host)}</code>\n"
            f"🔌 <b>Port:</b> <code>{html.escape(self.port)}</code>\n"
            f"👤 <b>Username:</b> <code>{html.escape(self.username)}</code> (or <code>Administrator</code>)\n"
            f"🔑 <b>VPS PIN / Password:</b> <code>{html.escape(self.pin)}</code>\n\n"
            f"📱 <b>Direct Connection String (for RDP Apps):</b>\n"
            f"<code>{html.escape(self.host)}:{html.escape(self.port)}</code>\n\n"
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
            f"💡 <i>Commands: /start (info) | /status (uptime) | /stop (shutdown)</i>"
        )

    def format_status_message(self):
        elapsed = int(time.time() - self.start_time)
        remaining = max(0, int(self.max_duration_seconds - elapsed))
        elapsed_m, elapsed_s = divmod(elapsed, 60)
        elapsed_h, elapsed_m = divmod(elapsed_m, 60)
        rem_m, rem_s = divmod(remaining, 60)
        rem_h, rem_m = divmod(rem_m, 60)

        return (
            f"📊 <b>Runner Status:</b> Active ✅\n\n"
            f"⏱ <b>Uptime:</b> {elapsed_h}h {elapsed_m}m {elapsed_s}s\n"
            f"⏳ <b>Time Remaining:</b> {rem_h}h {rem_m}m\n"
            f"🖥 <b>Address:</b> <code>{html.escape(self.host)}:{html.escape(self.port)}</code>\n"
            f"👤 <b>User:</b> <code>{html.escape(self.username)}</code>\n"
            f"🔑 <b>PIN:</b> <code>{html.escape(self.pin)}</code>\n"
            f"🌐 <b>Tunnel:</b> {html.escape(self.tunnel_type)}\n"
            f"💻 <b>OS:</b> {html.escape(platform.system())} {html.escape(platform.release())}"
        )

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

    def run(self):
        print("Authenticating Telegram Bot...")
        me = self.call_api("getMe")
        if not me or not me.get("ok"):
            print("[ERROR] Failed to authenticate with Telegram Bot Token!")
            print("Please ensure your token is valid.")
            sys.exit(1)

        bot_info = me.get("result", {})
        bot_user = bot_info.get("username", "UnknownBot")
        print(f"✅ Telegram Bot Authenticated: @{bot_user} ({bot_info.get('first_name', '')})")

        # Proactively send credentials if initial chat_id is provided
        if self.initial_chat_id:
            print(f"Sending credentials to initial Chat ID: {self.initial_chat_id}")
            self.send_message(
                self.initial_chat_id,
                self.format_credentials_message(),
                self.get_inline_keyboard()
            )

        print(f"Listening for commands on Telegram... Send /start to @{bot_user}")

        offset = 0
        last_keepalive = time.time()

        while self.running:
            now = time.time()
            if now - self.start_time > self.max_duration_seconds:
                print("Approaching max GitHub Actions runtime limit (6 hours). Shutting down.")
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

                    # Handle inline button callbacks
                    if "callback_query" in update:
                        cq = update["callback_query"]
                        cq_id = cq["id"]
                        cb_data = cq.get("data", "")
                        chat_id = cq["message"]["chat"]["id"]

                        if cb_data == "cmd_status":
                            self.answer_callback_query(cq_id, "Refreshing status...")
                            self.send_message(chat_id, self.format_status_message(), self.get_inline_keyboard())
                        elif cb_data == "cmd_info":
                            self.answer_callback_query(cq_id, "Sending connection info...")
                            self.send_message(chat_id, self.format_credentials_message(), self.get_inline_keyboard())
                        elif cb_data == "cmd_stop":
                            self.answer_callback_query(cq_id, "Stopping runner...")
                            self.send_message(chat_id, "🛑 <b>Stopping runner session... Goodbye!</b>")
                            self.running = False
                            break
                        else:
                            self.answer_callback_query(cq_id)
                        continue

                    # Handle incoming chat messages
                    msg = update.get("message")
                    if not msg:
                        continue

                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "").strip()

                    print(f"[Telegram Message] From: {chat_id} | Text: {text}")

                    if text.startswith("/start") or text.startswith("/rdp") or text.startswith("/info"):
                        self.send_message(chat_id, self.format_credentials_message(), self.get_inline_keyboard())
                    elif text.startswith("/status"):
                        self.send_message(chat_id, self.format_status_message(), self.get_inline_keyboard())
                    elif text.startswith("/stop"):
                        self.send_message(chat_id, "🛑 <b>Stopping runner session... Goodbye!</b>")
                        self.running = False
                        break
                    elif text.startswith("/help"):
                        help_text = (
                            "📖 <b>Telegram RDP Bot Commands:</b>\n\n"
                            "• <b>/start</b> - Get IP, Port, Username & PIN to connect\n"
                            "• <b>/status</b> - Show live VPS uptime & stats\n"
                            "• <b>/stop</b> - Shut down the VPS runner"
                        )
                        self.send_message(chat_id, help_text, self.get_inline_keyboard())
                    else:
                        # Any other message returns connection details
                        self.send_message(chat_id, self.format_credentials_message(), self.get_inline_keyboard())

            except Exception as e:
                print(f"[Polling Exception] {e}")
                time.sleep(3)

        print("Runner loop finished.")

if __name__ == "__main__":
    bot = TelegramRDPBot()
    bot.run()
