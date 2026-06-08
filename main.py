# -*- coding: utf-8 -*-
import flet as ft
import requests
import random
import datetime
import csv
import io
import urllib.parse
import json
import os
import logging

# =====================================================================
# ۱. بخش مدیریت پایگاه داده (DATABASE MANAGER - EMBEDDED)
# =====================================================================
SETTINGS_FILE = "settings.json"
COMMENTS_FILE = "comments.json"
USERS_FILE = "users.json"
LOGS_FILE = "logs.json"

def load_json(filepath, default_val):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_val
    return default_val

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        pass

def load_settings():
    return load_json(SETTINGS_FILE, {"sms_mode": "local", "sms_text": "از مراجعه شما به مطب سپاسگزاریم."})

def save_settings(data):
    save_json(SETTINGS_FILE, data)

def load_comments():
    # دیتابیس پیش‌فرض نظرات کلینیک در صورت عدم وجود فایل خارجی
    default_comments = {
        "lasik": ["نتیجه عمل لیزیک من فوق‌العاده بود، ممنون از پزشک حاذق.", "بسیار متبحر و با اخلاق هستند."],
        "cataract": ["عمل کاتاراکت مادرم عالی بود و بینایی‌شون کاملا برگشت.", "توضیحات دقیق و جراحی بی‌نقص."],
        "retina": ["تزریق شبکیه کاملا بدون درد و با دقت بالا انجام شد.", "پزشک بسیار دلسوز و مسلط."],
        "blepharoplasty": ["جراحی پلک من بسیار طبیعی و بدون رد بخیه انجام شد.", "فرم چشم‌هایم عالی شده است."]
    }
    return load_json(COMMENTS_FILE, default_comments)

def save_comments(data):
    save_json(COMMENTS_FILE, data)

def load_users():
    # حساب کاربری پیش‌فرض منشی‌ها
    default_users = {
        "maryam": {"password": "123", "is_active": True, "can_edit_comments": True, "can_send_reports": True},
        "monshi": {"password": "456", "is_active": True, "can_edit_comments": True, "can_send_reports": True}
    }
    return load_json(USERS_FILE, default_users)

def save_users(data):
    save_json(USERS_FILE, data)

def load_logs():
    return load_json(LOGS_FILE, [])

def save_logs(data):
    save_json(LOGS_FILE, data)

def clear_logs():
    save_json(LOGS_FILE, [])


# =====================================================================
# ۲. بخش موتور ارسال پیامک خوش‌آمدگویی (SMS ENGINE - EMBEDDED)
# =====================================================================
def send_sms(page, mobile, text, mode="local"):
    if not mobile or len(mobile) != 11 or not mobile.startswith("09"):
        if hasattr(page, "snack_bar"):
            page.snack_bar.content.value = "❌ خطای فرمت شماره موبایل."
            page.snack_bar.open = True
            page.update()
        return False

    if mode == "local":
        try:
            encoded_text = urllib.parse.quote(text)
            page.launch_url(f"sms:{mobile}?body={encoded_text}")
            return True
        except:
            return False

    elif mode == "api":
        settings = load_settings()
        api_key = settings.get("kavenegar_api", "").strip()
        sender = settings.get("kavenegar_sender", "").strip()

        if not api_key or not sender:
            try:
                encoded_text = urllib.parse.quote(text)
                page.launch_url(f"sms:{mobile}?body={encoded_text}")
                return True
            except:
                return False

        try:
            url = f"https://api.kavenegar.com/v1/{api_key}/sms/send.json"
            payload = {"receptor": mobile, "message": text, "sender": sender}
            res = requests.post(url, data=payload, timeout=5)

            if res.status_code == 200:
                return True
            else:
                encoded_text = urllib.parse.quote(text)
                page.launch_url(f"sms:{mobile}?body={encoded_text}")
                return False
        except Exception:
            encoded_text = urllib.parse.quote(text)
            page.launch_url(f"sms:{mobile}?body={encoded_text}")
            return False

    return False


# =====================================================================
# ۳. بخش رابط کاربری تنظیمات (SETTINGS VIEW - EMBEDDED)
# =====================================================================
class SettingsView(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/settings", scroll="auto")
        self.page_ref = page
        self.settings = load_settings()
        self.sms_mode = self.settings.get("sms_mode", "local")
        
        self.mode_radio = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="local", label="📱 ارسال آفلاین (از سیم‌کارت گوشی)"),
                ft.Radio(value="api", label="🌐 ارسال آنلاین (وب‌سرویس کاوه‌نگار)")
            ], spacing=15),
            value=self.sms_mode,
            on_change=self.handle_mode_change
        )
        
        self.save_btn = ft.ElevatedButton(
            "💾 ذخیره تنظیمات", 
            on_click=self.save_settings, 
            bgcolor=ft.Colors.GREEN_700, 
            color=ft.Colors.WHITE,
            width=250,
            height=45
        )
        self.status_text = ft.Text("", color=ft.Colors.GREEN, weight="bold")
        
        self.controls = [
            ft.AppBar(
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=self.go_back, tooltip="بازگشت به پنل اصلی"),
                title=ft.Text("⚙️ تنظیمات سیستم", color=ft.Colors.WHITE), 
                bgcolor=ft.Colors.TEAL_700, 
                actions=[
                    ft.TextButton(content=ft.Text("🚪 خروج از حساب", color=ft.Colors.RED_100), on_click=self.do_logout)
                ]
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("نحوه ارسال پیامک خوش‌آمدگویی را انتخاب کنید:", weight="bold", size=16),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    self.mode_radio,
                    ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                    self.save_btn,
                    self.status_text,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=25
            )
        ]
        
    def handle_mode_change(self, e):
        self.sms_mode = e.control.value
        
    def save_settings(self, e):
        self.settings["sms_mode"] = self.sms_mode
        save_settings(self.settings)
        self.status_text.value = "✅ تنظیمات با موفقیت ذخیره شد."
        self.page_ref.update()
        
    def go_back(self, e):
        if hasattr(self.page_ref, "go_to"):
            self.page_ref.go_to("/")

    def do_logout(self, e):
        setattr(self.page_ref, "auth_user", None)
        if hasattr(self.page_ref, "go_to"):
            self.page_ref.go_to("/")


# =====================================================================
# ۴. بخش رابط کاربری اصلی کلینیک (HOME VIEW - EMBEDDED)
# =====================================================================
class HomeView(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__(route="/", scroll="auto")
        self.page_ref = page
        self.settings = load_settings()
        self.app_state = {"token": None, "category": None}
        
        self.current_user = getattr(self.page_ref, "auth_user", None)
        is_logged_in = bool(self.current_user)
        
        self.login_user = ft.TextField(label="نام کاربری", width=300, filled=True)
        self.login_pass = ft.TextField(label="رمز عبور", password=True, width=300, filled=True)
        self.login_err = ft.Text("", color=ft.Colors.RED, weight="bold")
        self.btn_login = ft.ElevatedButton("ورود به سیستم", on_click=self.do_login, bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE, width=300)
        
        self.login_container = ft.Container(
            content=ft.Column([
                ft.Divider(height=50, color=ft.Colors.TRANSPARENT), ft.Text("🔒", size=60), ft.Text("دروازه ورود کلینیک", size=24, weight="bold"),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT), self.login_user, self.login_pass, self.btn_login, self.login_err
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=20, visible=not is_logged_in 
        )

        self.mobile_field = ft.TextField(label="شماره موبایل", width=350, filled=True, keyboard_type=ft.KeyboardType.PHONE, input_filter=ft.NumbersOnlyInputFilter(), max_length=11, on_change=self.update_sms_urls)
        self.code_field = ft.TextField(label="کد تایید", width=150, filled=True, keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.NumbersOnlyInputFilter(), max_length=4)
        self.status_bar = ft.Text("سیستم آماده است.", color=ft.Colors.GREY, weight="bold", text_align=ft.TextAlign.CENTER)
        
        self.preview_field = ft.TextField(label="متن نظر", multiline=True, min_lines=3, width=350, filled=True, suffix=ft.TextButton("تعویض", on_click=self.on_randomize))
        self.sms_text_field = ft.TextField(label="متن پیامک", value=self.settings.get("sms_text", "از مراجعه شما به مطب سپاسگزاریم."), multiline=True, min_lines=2, width=350, filled=True, on_change=self.update_sms_urls)
        
        self.btn_both = ft.ElevatedButton("ثبت نظر + پیامک", data="both", on_click=self.execute_action, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, width=300)
        self.btn_submit = ft.ElevatedButton("فقط ثبت نظر", data="submit", on_click=self.execute_action, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, width=145)
        self.btn_sms = ft.ElevatedButton("فقط پیامک", data="sms", on_click=self.execute_action, bgcolor=ft.Colors.ORANGE_600, color=ft.Colors.WHITE, width=145)
        self.btn_cancel = ft.TextButton("🧹 پاکسازی و شروع مجدد فرم", on_click=self.reset_form, icon=ft.Icons.REFRESH, icon_color=ft.Colors.RED, style=ft.ButtonStyle(color=ft.Colors.RED))

        self.preview_container = ft.Column([
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT), self.preview_field, self.sms_text_field, 
            ft.Column([ft.Row([self.btn_submit, self.btn_sms], alignment=ft.MainAxisAlignment.CENTER), self.btn_both], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
        
        self.category_buttons = ft.Column([
            ft.Row([ft.ElevatedButton("لیزیک", data="lasik", on_click=self.on_verify), ft.ElevatedButton("کاتاراکت", data="cataract", on_click=self.on_verify)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.ElevatedButton("شبکیه", data="retina", on_click=self.on_verify), ft.ElevatedButton("بلفارو", data="blepharoplasty", on_click=self.on_verify)], alignment=ft.MainAxisAlignment.CENTER)
        ])
        
        self.settings_button = ft.TextButton(content=ft.Text("⚙️ تنظیمات", color=ft.Colors.WHITE), on_click=self.go_to_settings)
        self.end_shift_btn = ft.ElevatedButton("📊 پایان شیفت و ارسال گزارش", on_click=self.confirm_end_shift, bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE, width=350)
        
        self.confirm_section = ft.Column([
            ft.Text("⚠️ با ارسال گزارش کنتور امروز صفر می‌شود. تایید نهایی؟", color=ft.Colors.RED_800, weight="bold"),
            ft.Row([ft.ElevatedButton("✅ بله", on_click=self.do_end_shift, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE), ft.ElevatedButton("❌ انصراف", on_click=self.cancel_end_shift, bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
        
        self.main_container = ft.Container(
            content=ft.Column([
                self.mobile_field, ft.ElevatedButton("دریافت کد", on_click=self.request_otp, width=200), 
                self.code_field, self.category_buttons, self.btn_cancel, 
                self.preview_container, 
                ft.Divider(height=15), self.status_bar, ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                self.end_shift_btn, self.confirm_section    
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=20, visible=is_logged_in 
        )

        self.controls = [ft.AppBar(title=ft.Text("پنل مطب", color=ft.Colors.WHITE), bgcolor=ft.Colors.TEAL_700, actions=[self.settings_button]), self.login_container, self.main_container]
        if is_logged_in:
            self.status_bar.value = f"کاربر {self.current_user} فعال است."
            self.apply_permissions()

    def update_sms_urls(self, e):
        mobile, text, mode = self.mobile_field.value.strip(), self.sms_text_field.value.strip(), self.settings.get("sms_mode", "local")
        if mode == "local" and len(mobile) == 11 and mobile.startswith("09"):
            sms_url = f"sms:{mobile}?body={urllib.parse.quote(text)}"
            self.btn_sms.url, self.btn_both.url = sms_url, sms_url
        else: self.btn_sms.url, self.btn_both.url = None, None
        self.page_ref.update()

    def do_login(self, e):
        u, p, db = self.login_user.value.strip(), self.login_pass.value.strip(), load_users()
        if u in db and db[u]["password"] == p:
            if not db[u]["is_active"]: 
                self.login_err.value = "حساب شما مسدود است."
            else:
                self.current_user = u
                setattr(self.page_ref, "auth_user", u)
                self.login_err.value = ""
                self.login_container.visible, self.main_container.visible = False, True
                self.status_bar.value = f"کاربر {u} وارد شد."
                self.apply_permissions()
        else: 
            self.login_err.value = "نام کاربری یا رمز عبور اشتباه است."
        self.page_ref.update()

    def do_logout(self, msg=""):
        self.current_user = None
        setattr(self.page_ref, "auth_user", None)
        self.login_pass.value, self.login_err.value = "", msg
        self.main_container.visible, self.login_container.visible = False, True
        self.page_ref.update()

    def check_auth_live(self):
        if not self.current_user: return False
        if not load_users().get(self.current_user, {}).get("is_active"):
            self.do_logout("نشست منقضی شد. (حساب شما غیرفعال شده است)")
            return False
        self.apply_permissions()
        return True

    def apply_permissions(self):
        u_data = load_users().get(self.current_user, {})
        self.preview_field.visible = u_data.get("can_edit_comments", False)
        self.end_shift_btn.visible = u_data.get("can_send_reports", False)

    def request_otp(self, e):
        if not self.check_auth_live(): return
        mobile = self.mobile_field.value.strip()
        if len(mobile) != 11:
            self.status_bar.value, self.status_bar.color = "❌ شماره موبایل نامعتبر است.", ft.Colors.RED
            self.page_ref.update()
            return

        self.status_bar.value = "⏳ ارتباط با سرور نوبت..."
        self.status_bar.color = ft.Colors.BLUE
        self.page_ref.update()

        try:
            res = requests.post("https://api.nobat.ir/patient/login/phone", data={"mobile": mobile}, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("status") is False:
                    err_msg = data.get("message", "خطای محدودیت ارسال")
                    self.status_bar.value = f"❌ {err_msg}\n💡 راهنما: بیمار دیگری را تست کنید."
                    self.status_bar.color = ft.Colors.ORANGE
                else:
                    self.status_bar.value, self.status_bar.color = "✅ کد تایید پیامک شد.", ft.Colors.GREEN
            else:
                self.status_bar.value = f"❌ سایت نوبت درخواست را رد کرد.\n💡 راهنما: آی‌پی بلاک شده. حالت پرواز ✈️ را یک‌بار خاموش/روشن کنید."
                self.status_bar.color = ft.Colors.RED
        
        except requests.exceptions.Timeout:
            self.status_bar.value = "❌ سرور نوبت پاسخ نداد (اینترنت ضعیف).\n💡 راهنما: حالت پرواز ✈️ را یک‌بار خاموش/روشن کنید."
            self.status_bar.color = ft.Colors.RED
        except Exception: 
            self.status_bar.value = "❌ خطای اینترنت.\n💡 راهنما: اتصال شبکه گوشی را چک کنید."
            self.status_bar.color = ft.Colors.RED
            
        self.page_ref.update()

    def on_verify(self, e):
        if not self.check_auth_live(): return
        mobile, code, self.app_state["category"] = self.mobile_field.value.strip(), self.code_field.value.strip(), e.control.data
        if len(mobile) != 11 or len(code) != 4: 
            self.status_bar.value, self.status_bar.color = "❌ لطفا موبایل (۱۱ رقم) و کد (۴ رقم) را وارد کنید.", ft.Colors.RED
            self.page_ref.update()
            return
        
        if code == "1111":
            self.app_state["token"] = "mock_universal_test"
            self.preview_field.value = random.choice(load_comments().get(self.app_state["category"], ["پزشک عالی است"]))
            self.preview_container.visible, self.status_bar.value, self.status_bar.color = True, "سندباکس تست فعال شد.", ft.Colors.ORANGE
            self.page_ref.update()
            return
            
        self.status_bar.value = "⏳ در حال تایید کد..."
        self.status_bar.color = ft.Colors.BLUE
        self.page_ref.update()

        try:
            res = requests.post("https://api.nobat.ir/patient/login/verify", data={"mobile": mobile, "code": code}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "token" in data:
                    self.app_state["token"] = data["token"]
                    self.preview_field.value = random.choice(load_comments().get(self.app_state["category"], ["پزشک عالی است"]))
                    self.preview_container.visible = True
                    self.status_bar.value, self.status_bar.color = "✅ کد تایید شد. نظر را ثبت کنید.", ft.Colors.GREEN
                else:
                    err_msg = data.get("message", "کد اشتباه یا منقضی شده است.")
                    self.status_bar.value = f"❌ {err_msg}\n💡 راهنما: مجدداً دکمه دریافت کد را بزنید."
                    self.status_bar.color = ft.Colors.RED
            else:
                self.status_bar.value = "❌ خطای سایت نوبت.\n💡 راهنما: حالت پرواز ✈️ را یک‌بار خاموش/روشن کنید."
                self.status_bar.color = ft.Colors.RED
        except requests.exceptions.Timeout:
            self.status_bar.value = "❌ سرور پاسخ نداد.\n💡 راهنما: اینترنت را قطع و وصل کنید."
            self.status_bar.color = ft.Colors.RED
        except Exception:
            self.status_bar.value = "❌ خطای شبکه. اتصال اینترنت را بررسی کنید."
            self.status_bar.color = ft.Colors.RED
            
        self.page_ref.update()

    def on_randomize(self, e):
        db_comments = load_comments()
        cat = self.app_state.get("category")
        if cat and db_comments.get(cat): 
            options = db_comments[cat]
            if len(options) > 1:
                current_text = self.preview_field.value
                available_options = [c for c in options if c != current_text]
                if available_options:
                    self.preview_field.value = random.choice(available_options)
                else:
                    self.preview_field.value = random.choice(options)
            else:
                self.preview_field.value = random.choice(options)
        self.page_ref.update()

    def execute_action(self, e):
        if not self.check_auth_live(): return
        
        e.control.disabled = True
        self.page_ref.update()
        
        action = e.control.data
        msgs = []
        token = self.app_state.get("token") or ""
        
        if action in ["submit", "both"]:
            if token.startswith("mock_"): 
                msgs.append("✅ نظر ثبت شد (تست)")
            else:
                try: 
                    res_comment = requests.post("https://api.nobat.ir/nuser/comments/store", data={"token": token, "doctor_id": "245932", "comment": self.preview_field.value, "score": "3"}, timeout=5)
                    if res_comment.status_code == 200:
                        msgs.append("✅ نظر با موفقیت در سایت ثبت شد")
                    else:
                        try:
                            err_msg = res_comment.json().get("message", "خطای محدودیت ثبت")
                            msgs.append(f"❌ {err_msg} (کد {res_comment.status_code})")
                        except:
                            msgs.append(f"❌ خطای سایت نوبت (کد {res_comment.status_code})")
                except: 
                    msgs.append("❌ خطای شبکه در ثبت نظر. اتصال را چک کنید")

        if action in ["sms", "both"]:
            try: 
                success = send_sms(self.page_ref, self.mobile_field.value, self.sms_text_field.value, self.settings.get("sms_mode", "local"))
                if success:
                    msgs.append("✅ پیامک ارسال شد")
                else:
                    msgs.append("❌ خطای ارسال پیامک")
            except: 
                msgs.append("❌ ارور سیستمی در پیامک")

        logs = load_logs()
        logs.append({
            "date_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            "secretary": self.current_user, 
            "mobile": self.mobile_field.value, 
            "category": self.app_state.get("category", "ناشناس"), 
            "action": action, 
            "comment": self.preview_field.value
        })
        save_logs(logs)

        self.status_bar.value = " | ".join(msgs)
        self.status_bar.color = ft.Colors.TEAL if "✅" in self.status_bar.value else ft.Colors.RED
        e.control.disabled = False
        self.reset_form(None)

    def reset_form(self, e):
        self.settings = load_settings()
        self.mobile_field.value, self.code_field.value, self.preview_field.value = "", "", ""
        self.sms_text_field.value = self.settings.get("sms_text", "از مراجعه شما به مطب سپاسگزاریم.")
        self.app_state["token"], self.preview_container.visible = None, False
        self.btn_sms.url, self.btn_both.url = None, None
        
        if e: 
            self.status_bar.value, self.status_bar.color = "فرم پاکسازی شد. آماده برای بیمار جدید.", ft.Colors.GREY
            
        self.page_ref.update()

    def confirm_end_shift(self, e):
        self.end_shift_btn.visible, self.confirm_section.visible = False, True
        self.page_ref.update()

    def cancel_end_shift(self, e):
        self.confirm_section.visible, self.end_shift_btn.visible = False, True
        self.page_ref.update()

    def do_end_shift(self, e):
        if not self.check_auth_live(): return
        self.confirm_section.visible, self.end_shift_btn.visible = False, True  
        
        self.status_bar.value = "⏳ شکیبا باشید...\nدر حال ارسال گزارش به سرور و گروه بله"
        self.status_bar.color = ft.Colors.BLUE
        self.page_ref.update()
        
        logs = load_logs()
        if not logs:
            self.status_bar.value, self.status_bar.color = "⚠️ لیست بیماران امروز خالی است.", ft.Colors.ORANGE
            self.page_ref.update()
            return
            
        server_sync_status = "سرور ❌"
        try:
            headers = {"x-api-token": "Secure_Key_2026"}
            for log in logs:
                payload = {
                    "Date": log.get("date_time", ""),
                    "Shift": "شیفت کاری",
                    "Total_Patients": 1,
                    "Treatment_Details": log.get("category", ""),
                    "Platform": "nobat.ir",
                    "SMS_Mode": log.get("action", ""),
                    "Total_Income": 0,
                    "Description": log.get("comment", "")
                }
                res_server = requests.post("https://api.iranlasik.ir/api/report", json=payload, headers=headers, timeout=5)
                if res_server.status_code == 200:
                    server_sync_status = "سرور ✅"
        except Exception as err:
            logging.error(f"خطای سینک با سرور: {err}")

        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output)
        writer.writerow(["ردیف", "تاریخ", "کاربر", "موبایل", "درمان", "عملیات", "نظر"])
        
        cat_map = {"lasik": "لیزیک", "cataract": "کاتاراکت", "retina": "شبکیه", "blepharoplasty": "بلفارو"}
        act_map = {"both": "نظر+پیامک", "submit": "فقط نظر", "sms": "فقط پیامک"}
        
        for i, log in enumerate(logs, 1): 
            c_name = cat_map.get(log.get("category"), log.get("category"))
            a_name = act_map.get(log.get("action"), log.get("action"))
            clean_comment = log.get("comment", "").replace("\n", " ")
            writer.writerow([i, log.get("date_time"), log.get("secretary"), log.get("mobile"), c_name, a_name, clean_comment])
            
        csv_content = output.getvalue().encode('utf-8')
        
        BRIDGE_GROUP_ID = "4448378011"
        ASSISTANT_BOT_TOKEN = "1137791878:xD-QEx6ZHEuqnzBmBFRUklgzo7wFqTDrOmY"
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        bale_sync_status = "گروه بله ❌"
        
        try:
            res_bale = requests.post(
                f"https://tapi.bale.ai/bot{ASSISTANT_BOT_TOKEN}/sendDocument", 
                data={"chat_id": BRIDGE_GROUP_ID, "caption": f"📊 گزارش پایان شیفت کلینیک\n👤 ارسال‌کننده: {self.current_user}\n👥 تعداد بیماران: {len(logs)}"}, 
                files={"document": (f"Report_{date_str}.csv", csv_content, "text/csv")}, 
                timeout=15
            )
            if res_bale.status_code == 200:
                bale_sync_status = "گروه بله ✅"
            else:
                logging.error(f"Bale API Error: {res_bale.text}")
        except Exception as err: 
            logging.error(f"Bale Request Error: {err}")
            
        if "✅" in server_sync_status or "✅" in bale_sync_status:
            clear_logs()
            self.status_bar.value = f"✅ گزارش با موفقیت ارسال شد. ({server_sync_status} | {bale_sync_status})\n🌺 همکار گرامی خسته نباشید."
            self.status_bar.color = ft.Colors.GREEN
        else:
            self.status_bar.value = "❌ خطای اینترنت. ارسال به سرور و گروه با شکست مواجه شد."
            self.status_bar.color = ft.Colors.RED
            
        self.page_ref.update()

    def go_to_settings(self, e):
        if hasattr(self.page_ref, "go_to"):
            self.page_ref.go_to("/settings")


# =====================================================================
# ۵. بخش روتینگ و مقداردهی اولیه برنامه (MAIN ROUTER & INITIALIZATION)
# =====================================================================
def main(page: ft.Page):
    page.title = "سامانه مدیریت هوشمند کلینیک"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.rtl = True
    
    if not hasattr(page, "auth_user"):
        page.auth_user = None

    def go_to(route_path):
        page.route = route_path
        page.update()

    page.go_to = go_to

    def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.views.append(HomeView(page))
        elif page.route == "/settings":
            page.views.append(SettingsView(page))
        page.update()

    page.on_route_change = route_change
    page.go("/")

if __name__ == "__main__":
    ft.app(target=main)
