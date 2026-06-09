# -*- coding: utf-8 -*-
import flet as ft
import traceback

# 🟢 سیستم تشخیص خطای وارد کردن کتابخانه‌ها (قبل از گرافیک)
GLOBAL_ERROR = None
try:
    import requests
    import random
    import datetime
    import csv
    import io
    import urllib.parse
except Exception as e:
    GLOBAL_ERROR = traceback.format_exc()

# =====================================================================
# ۱. پایگاه داده موقت (RAM Only - بدون هیچ درگیری با فایل‌های اندروید)
# =====================================================================
class DataManager:
    def __init__(self):
        # ذخیره تمام اطلاعات فقط در حافظه موقت (رم)
        self.settings = {"sms_mode": "local", "sms_text": "از مراجعه شما به مطب سپاسگزاریم."}
        self.comments = {
            "lasik": ["نتیجه عمل لیزیک من فوق‌العاده بود، ممنون از پزشک حاذق.", "بسیار متبحر و با اخلاق هستند."],
            "cataract": ["عمل کاتاراکت مادرم عالی بود و بینایی‌شون کاملا برگشت.", "توضیحات دقیق و جراحی بی‌نقص."],
            "retina": ["تزریق شبکیه کاملا بدون درد و با دقت بالا انجام شد.", "پزشک بسیار دلسوز و مسلط."],
            "blepharoplasty": ["جراحی پلک من بسیار طبیعی و بدون رد بخیه انجام شد.", "فرم چشم‌هایم عالی شده است."]
        }
        self.users = {
            "admin": {"password": "123", "is_active": True, "can_edit_comments": True, "can_send_reports": True},
            "monshi": {"password": "456", "is_active": True, "can_edit_comments": True, "can_send_reports": True}
        }
        self.logs = []
        
    def load_settings(self): return self.settings
    def save_settings(self, data): self.settings = data
    def load_comments(self): return self.comments
    def load_users(self): return self.users
    def load_logs(self): return self.logs
    def save_logs(self, data): self.logs = data
    def clear_logs(self): self.logs = []


# =====================================================================
# ۲. موتور پیامک
# =====================================================================
def send_sms(page, mobile, text, mode, settings):
    if not mobile or len(mobile) != 11 or not mobile.startswith("09"): return False
    if mode == "local":
        try:
            page.launch_url(f"sms:{mobile}?body={urllib.parse.quote(text)}")
            return True
        except: return False
    elif mode == "api":
        api_key = settings.get("kavenegar_api", "").strip()
        sender = settings.get("kavenegar_sender", "").strip()
        if not api_key or not sender:
            try:
                page.launch_url(f"sms:{mobile}?body={urllib.parse.quote(text)}")
                return True
            except: return False
        try:
            res = requests.post(f"https://api.kavenegar.com/v1/{api_key}/sms/send.json", data={"receptor": mobile, "message": text, "sender": sender}, timeout=5)
            if res.status_code == 200: return True
            else:
                page.launch_url(f"sms:{mobile}?body={urllib.parse.quote(text)}")
                return False
        except:
            page.launch_url(f"sms:{mobile}?body={urllib.parse.quote(text)}")
            return False
    return False


# =====================================================================
# ۳. رابط کاربری تنظیمات
# =====================================================================
class SettingsView(ft.View):
    def __init__(self, page: ft.Page, db: DataManager):
        super().__init__(route="/settings", scroll="auto")
        self.page_ref = page
        self.db = db
        self.settings = self.db.load_settings()
        self.sms_mode = self.settings.get("sms_mode", "local")
        
        self.mode_radio = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="local", label="📱 ارسال آفلاین (سیم‌کارت)"),
                ft.Radio(value="api", label="🌐 ارسال آنلاین (کاوه‌نگار)")
            ], spacing=15), value=self.sms_mode, on_change=self.handle_mode_change
        )
        self.save_btn = ft.ElevatedButton("💾 ذخیره", on_click=self.save_settings, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, width=250)
        self.status_text = ft.Text("سیستم در حالت امن (RAM) است.", color=ft.Colors.ORANGE, size=12)
        
        self.controls = [
            ft.AppBar(leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=self.go_back), title=ft.Text("تنظیمات", color=ft.Colors.WHITE), bgcolor=ft.Colors.TEAL_700, actions=[ft.TextButton(content=ft.Text("خروج", color=ft.Colors.RED_100), on_click=self.do_logout)]),
            ft.Container(content=ft.Column([ft.Text("نحوه ارسال پیامک:"), self.mode_radio, self.save_btn, self.status_text], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=25)
        ]
        
    def handle_mode_change(self, e): self.sms_mode = e.control.value
    def save_settings(self, e):
        self.settings["sms_mode"] = self.sms_mode
        self.db.save_settings(self.settings)
        self.status_text.value = "تنظیمات ذخیره شد."
        self.page_ref.update()
    def go_back(self, e): self.page_ref.go_to("/")
    def do_logout(self, e):
        self.page_ref.auth_user = None
        self.page_ref.go_to("/")


# =====================================================================
# ۴. رابط کاربری اصلی
# =====================================================================
class HomeView(ft.View):
    def __init__(self, page: ft.Page, db: DataManager):
        super().__init__(route="/", scroll="auto")
        self.page_ref = page
        self.db = db
        self.settings = self.db.load_settings()
        self.app_state = {"token": None, "category": None}
        self.current_user = getattr(self.page_ref, "auth_user", None)
        is_logged_in = bool(self.current_user)
        
        self.login_user = ft.TextField(label="نام کاربری", width=300, filled=True)
        self.login_pass = ft.TextField(label="رمز عبور", password=True, width=300, filled=True)
        self.login_err = ft.Text("", color=ft.Colors.RED, weight="bold")
        self.btn_login = ft.ElevatedButton("ورود", on_click=self.do_login, bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE, width=300)
        self.login_container = ft.Container(content=ft.Column([ft.Text("🔒", size=60), self.login_user, self.login_pass, self.btn_login, self.login_err], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=20, visible=not is_logged_in)

        self.mobile_field = ft.TextField(label="شماره موبایل", width=350, filled=True, keyboard_type=ft.KeyboardType.PHONE, input_filter=ft.NumbersOnlyInputFilter(), max_length=11, on_change=self.update_sms_urls)
        self.code_field = ft.TextField(label="کد تایید", width=150, filled=True, keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.NumbersOnlyInputFilter(), max_length=4)
        self.status_bar = ft.Text("آماده...", color=ft.Colors.GREY, weight="bold", text_align=ft.TextAlign.CENTER)
        
        self.preview_field = ft.TextField(label="متن نظر", multiline=True, min_lines=3, width=350, filled=True, suffix=ft.TextButton("تعویض", on_click=self.on_randomize))
        self.sms_text_field = ft.TextField(label="متن پیامک", value=self.settings.get("sms_text", "سپاسگزاریم."), multiline=True, min_lines=2, width=350, filled=True, on_change=self.update_sms_urls)
        
        self.btn_both = ft.ElevatedButton("ثبت نظر + پیامک", data="both", on_click=self.execute_action, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, width=300)
        self.btn_submit = ft.ElevatedButton("فقط ثبت نظر", data="submit", on_click=self.execute_action, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, width=145)
        self.btn_sms = ft.ElevatedButton("فقط پیامک", data="sms", on_click=self.execute_action, bgcolor=ft.Colors.ORANGE_600, color=ft.Colors.WHITE, width=145)
        self.btn_cancel = ft.TextButton("پاکسازی فرم", on_click=self.reset_form, icon=ft.Icons.REFRESH, icon_color=ft.Colors.RED)

        self.preview_container = ft.Column([self.preview_field, self.sms_text_field, ft.Column([ft.Row([self.btn_submit, self.btn_sms], alignment=ft.MainAxisAlignment.CENTER), self.btn_both], horizontal_alignment=ft.CrossAxisAlignment.CENTER)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
        self.category_buttons = ft.Column([ft.Row([ft.ElevatedButton("لیزیک", data="lasik", on_click=self.on_verify), ft.ElevatedButton("کاتاراکت", data="cataract", on_click=self.on_verify)], alignment=ft.MainAxisAlignment.CENTER), ft.Row([ft.ElevatedButton("شبکیه", data="retina", on_click=self.on_verify), ft.ElevatedButton("بلفارو", data="blepharoplasty", on_click=self.on_verify)], alignment=ft.MainAxisAlignment.CENTER)])
        self.end_shift_btn = ft.ElevatedButton("پایان شیفت", on_click=self.confirm_end_shift, bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE, width=350)
        self.confirm_section = ft.Column([ft.Text("تایید نهایی ارسال گزارش؟", color=ft.Colors.RED_800), ft.Row([ft.ElevatedButton("بله", on_click=self.do_end_shift, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE), ft.ElevatedButton("خیر", on_click=self.cancel_end_shift)], alignment=ft.MainAxisAlignment.CENTER)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
        self.main_container = ft.Container(content=ft.Column([self.mobile_field, ft.ElevatedButton("دریافت کد", on_click=self.request_otp), self.code_field, self.category_buttons, self.btn_cancel, self.preview_container, self.status_bar, self.end_shift_btn, self.confirm_section], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=20, visible=is_logged_in)
        self.controls = [ft.AppBar(title=ft.Text("پنل مطب", color=ft.Colors.WHITE), bgcolor=ft.Colors.TEAL_700, actions=[ft.TextButton(content=ft.Text("⚙️", color=ft.Colors.WHITE), on_click=self.go_to_settings)]), self.login_container, self.main_container]
        if is_logged_in: self.apply_permissions()

    def update_sms_urls(self, e):
        m, t, mo = self.mobile_field.value.strip(), self.sms_text_field.value.strip(), self.settings.get("sms_mode", "local")
        url = f"sms:{m}?body={urllib.parse.quote(t)}" if mo == "local" and len(m)==11 else None
        self.btn_sms.url = self.btn_both.url = url
        self.page_ref.update()

    def do_login(self, e):
        u, p, db_users = self.login_user.value.strip(), self.login_pass.value.strip(), self.db.load_users()
        if u in db_users and db_users[u]["password"] == p and db_users[u]["is_active"]:
            self.current_user = u
            self.page_ref.auth_user = u
            self.login_container.visible, self.main_container.visible = False, True
            self.status_bar.value = f"کاربر {u} وارد شد"
            self.apply_permissions()
        else: self.login_err.value = "ورود ناموفق!"
        self.page_ref.update()

    def do_logout(self, msg=""):
        self.current_user = self.page_ref.auth_user = None
        self.login_pass.value, self.login_err.value = "", msg
        self.main_container.visible, self.login_container.visible = False, True
        self.page_ref.update()

    def check_auth_live(self):
        if not self.current_user or not self.db.load_users().get(self.current_user, {}).get("is_active"):
            self.do_logout("نشست منقضی شد")
            return False
        return True

    def apply_permissions(self):
        u_data = self.db.load_users().get(self.current_user, {})
        self.preview_field.visible = u_data.get("can_edit_comments", False)
        self.end_shift_btn.visible = u_data.get("can_send_reports", False)

    def request_otp(self, e):
        if not self.check_auth_live(): return
        if len(self.mobile_field.value.strip()) != 11:
            self.status_bar.value, self.status_bar.color = "❌ موبایل نامعتبر", ft.Colors.RED
            self.page_ref.update()
            return
        self.status_bar.value = "در حال ارتباط..."
        self.page_ref.update()
        try:
            res = requests.post("https://api.nobat.ir/patient/login/phone", data={"mobile": self.mobile_field.value}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") is False: self.status_bar.value, self.status_bar.color = f"❌ {data.get('message')}", ft.Colors.ORANGE
                else: self.status_bar.value, self.status_bar.color = "✅ پیامک شد.", ft.Colors.GREEN
            else: self.status_bar.value, self.status_bar.color = "❌ رد شد", ft.Colors.RED
        except: self.status_bar.value, self.status_bar.color = "❌ خطای اینترنت", ft.Colors.RED
        self.page_ref.update()

    def on_verify(self, e):
        if not self.check_auth_live(): return
        m, c, self.app_state["category"] = self.mobile_field.value.strip(), self.code_field.value.strip(), e.control.data
        if len(m) != 11 or len(c) != 4: return
        self.status_bar.value = "در حال تایید..."
        self.page_ref.update()
        try:
            res = requests.post("https://api.nobat.ir/patient/login/verify", data={"mobile": m, "code": c}, timeout=5)
            if res.status_code == 200 and "token" in res.json():
                self.app_state["token"] = res.json()["token"]
                self.preview_field.value = random.choice(self.db.load_comments().get(self.app_state["category"], ["عالی است"]))
                self.preview_container.visible = True
                self.status_bar.value, self.status_bar.color = "✅ تایید شد", ft.Colors.GREEN
            else: self.status_bar.value, self.status_bar.color = "❌ کد اشتباه", ft.Colors.RED
        except: self.status_bar.value, self.status_bar.color = "❌ خطای شبکه", ft.Colors.RED
        self.page_ref.update()

    def on_randomize(self, e):
        opts = self.db.load_comments().get(self.app_state.get("category"), ["عالی است"])
        self.preview_field.value = random.choice(opts)
        self.page_ref.update()

    def execute_action(self, e):
        if not self.check_auth_live(): return
        e.control.disabled = True
        self.page_ref.update()
        msgs, token = [], self.app_state.get("token") or ""
        if e.control.data in ["submit", "both"]:
            try: 
                res = requests.post("https://api.nobat.ir/nuser/comments/store", data={"token": token, "doctor_id": "245932", "comment": self.preview_field.value, "score": "3"}, timeout=5)
                msgs.append("✅ ثبت نظر") if res.status_code == 200 else msgs.append("❌ خطای ثبت")
            except: msgs.append("❌ شبکه")
        if e.control.data in ["sms", "both"]:
            try: msgs.append("✅ پیامک") if send_sms(self.page_ref, self.mobile_field.value, self.sms_text_field.value, self.settings.get("sms_mode", "local"), self.settings) else msgs.append("❌ پیامک")
            except: msgs.append("❌ ارور سیستم")
            
        logs = self.db.load_logs()
        logs.append({"date_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "secretary": self.current_user, "mobile": self.mobile_field.value, "category": self.app_state.get("category", ""), "action": e.control.data, "comment": self.preview_field.value})
        self.db.save_logs(logs)
        self.status_bar.value = " | ".join(msgs)
        self.status_bar.color = ft.Colors.TEAL
        e.control.disabled = False
        self.reset_form(None)

    def reset_form(self, e):
        self.mobile_field.value, self.code_field.value, self.preview_field.value = "", "", ""
        self.app_state["token"], self.preview_container.visible = None, False
        if e: self.status_bar.value = "پاکسازی شد."
        self.page_ref.update()

    def confirm_end_shift(self, e): self.end_shift_btn.visible, self.confirm_section.visible = False, True; self.page_ref.update()
    def cancel_end_shift(self, e): self.confirm_section.visible, self.end_shift_btn.visible = False, True; self.page_ref.update()

    def do_end_shift(self, e):
        if not self.check_auth_live(): return
        self.confirm_section.visible, self.end_shift_btn.visible = False, True  
        self.status_bar.value = "در حال ارسال..."
        self.page_ref.update()
        logs = self.db.load_logs()
        if not logs:
            self.status_bar.value = "⚠️ لیست خالی است."
            self.page_ref.update()
            return
        output = io.StringIO()
        output.write('﻿')
        writer = csv.writer(output)
        for i, log in enumerate(logs, 1): writer.writerow([i, log.get("mobile"), log.get("comment", "")])
        try:
            res_bale = requests.post("https://tapi.bale.ai/bot1137791878:xD-QEx6ZHEuqnzBmBFRUklgzo7wFqTDrOmY/sendDocument", data={"chat_id": "4448378011", "caption": f"شیفت: {self.current_user}"}, files={"document": ("Report.csv", output.getvalue().encode('utf-8'), "text/csv")}, timeout=10)
            if res_bale.status_code == 200:
                self.db.clear_logs()
                self.status_bar.value = "✅ ارسال شد."
            else: self.status_bar.value = "❌ خطا در بله"
        except: self.status_bar.value = "❌ خطای شبکه"
        self.page_ref.update()

    def go_to_settings(self, e): self.page_ref.go_to("/settings")

# =====================================================================
# ۵. بخش روتینگ و بوت برنامه
# =====================================================================
def main(page: ft.Page):
    # اگر کتابخانه‌ای مثل requests روی گوشی شما لود نشود، اینجا مچش را می‌گیریم!
    if GLOBAL_ERROR:
        page.scroll = "auto"
        page.add(ft.Text("🚨 خطای ناسازگاری سیستم‌عامل", color="red", size=20, weight="bold"))
        page.add(ft.Text(GLOBAL_ERROR, selectable=True, color="black"))
        page.update()
        return
        
    try:
        page.title = "سامانه کلینیک"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.rtl = True
        page.auth_user = None

        db = DataManager()

        def go_to(route_path):
            page.route = route_path
            page.update()
        page.go_to = go_to

        def route_change(route):
            try:
                page.views.clear()
                if page.route == "/":
                    page.views.append(HomeView(page, db))
                elif page.route == "/settings":
                    page.views.append(SettingsView(page, db))
                page.update()
            except Exception as inner_e:
                page.views.clear()
                page.views.append(
                    ft.View("/error", [
                        ft.Text("🚨 خطای رندر صفحه", color="red", weight="bold", size=20),
                        ft.Text(traceback.format_exc(), selectable=True, color="black", size=11)
                    ], scroll="auto")
                )
                page.update()

        page.on_route_change = route_change
        page.go("/")
        
    except Exception as e:
        page.clean()
        page.scroll = "auto"
        page.add(
            ft.Text("🚨 خطای اجرای اصلی", color="white", bgcolor="red", weight="bold", size=18),
            ft.Text(traceback.format_exc(), selectable=True, color="red", size=12)
        )
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
