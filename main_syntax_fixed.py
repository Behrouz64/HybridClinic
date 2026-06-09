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
import traceback

# =====================================================================
# ۱. بخش مدیریت پایگاه داده (DATABASE MANAGER - CRASH PROOF)
# =====================================================================
class DynamicDataManager:
    def __init__(self):
        self.ram_mode = False
        self.data = {
            "settings": {"sms_mode": "local", "sms_text": "از مراجعه شما به مطب سپاسگزاریم."},
            "comments": {
                "lasik": ["نتیجه عمل لیزیک من فوق‌العاده بود، ممنون از پزشک حاذق.", "بسیار متبحر و با اخلاق هستند."],
                "cataract": ["عمل کاتاراکت مادرم عالی بود و بینایی‌شون کاملا برگشت.", "توضیحات دقیق و جراحی بی‌نقص."],
                "retina": ["تزریق شبکیه کاملا بدون درد و با دقت بالا انجام شد.", "پزشک بسیار دلسوز و مسلط."],
                "blepharoplasty": ["جراحی پلک من بسیار طبیعی و بدون رد بخیه انجام شد.", "فرم چشم‌هایم عالی شده است."]
            },
            "users": {
                "admin": {"password": "123", "is_active": True, "can_edit_comments": True, "can_send_reports": True},
                "monshi": {"password": "456", "is_active": True, "can_edit_comments": True, "can_send_reports": True}
            },
            "logs": []
        }
        
        dirs_to_try = [os.environ.get("HOME"), os.path.expanduser("~"), os.getcwd()]
        self.base_dir = None
        
        for d in dirs_to_try:
            if d:
                try:
                    p = os.path.join(d, "hybrid_clinic_storage")
                    os.makedirs(p, exist_ok=True)
                    self.base_dir = p
                    break
                except:
                    continue
                    
        if not self.base_dir:
            self.ram_mode = True

    def get_file_path(self, filename):
        return os.path.join(self.base_dir, filename) if self.base_dir else None

    def load_key(self, filename, key_name):
        path = self.get_file_path(filename)
        if not self.ram_mode and path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return self.data[key_name]
        return self.data[key_name]

    def save_key(self, filename, key_name, value_data):
        self.data[key_name] = value_data
        path = self.get_file_path(filename)
        if not self.ram_mode and path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(value_data, f, ensure_ascii=False, indent=4)
            except:
                pass

    def load_settings(self): return self.load_key("settings.json", "settings")
    def save_settings(self, d): self.save_key("settings.json", "settings", d)
    def load_comments(self): return self.load_key("comments.json", "comments")
    def save_comments(self, d): self.save_key("comments.json", "comments", d)
    def load_users(self): return self.load_key("users.json", "users")
    def load_logs(self): return self.load_key("logs.json", "logs")
    def save_logs(self, d): self.save_key("logs.json", "logs", d)
    def clear_logs(self): self.save_key("logs.json", "logs", [])


# =====================================================================
# ۲. موتور ارسال پیامک
# =====================================================================
def send_sms(page, mobile, text, mode, settings_data):
    if not mobile or len(mobile) != 11 or not mobile.startswith("09"): return False
    if mode == "local":
        try:
            page.launch_url(f"sms:{mobile}?body={urllib.parse.quote(text)}")
            return True
        except: return False
    elif mode == "api":
        api_key = settings_data.get("kavenegar_api", "").strip()
        sender = settings_data.get("kavenegar_sender", "").strip()
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
# ۳. بدنه اصلی برنامه (تک‌صفحه‌ای و کاملاً ریسپانسیو)
# =====================================================================
def main(page: ft.Page):
    page.title = "سامانه مدیریت هوشمند کلینیک"
    page.theme_mode = "light"
    page.rtl = True
    
    db = DynamicDataManager()
    state = {"user": None, "token": None, "category": None}
    
    # -----------------------------------------------------------------
    # بخش الف: فرم ورود (Login Screen)
    # -----------------------------------------------------------------
    login_user = ft.TextField(label="نام کاربری", width=300, filled=True)
    login_pass = ft.TextField(label="رمز عبور", password=True, width=300, filled=True)
    login_err = ft.Text("", color="red", weight="bold")
    
    def do_login(e):
        u = login_user.value.strip()
        p = login_pass.value.strip()
        users = db.load_users()
        if u in users and users[u]["password"] == p and users[u]["is_active"]:
            state["user"] = u
            login_panel.visible = False
            main_panel.visible = True
            status_bar.value = f"کاربر {u} فعال است."
            status_bar.color = "grey"
            
            preview_field.visible = users[u].get("can_edit_comments", False)
            end_shift_btn.visible = users[u].get("can_send_reports", False)
            
            page.update()
        else:
            login_err.value = "نام کاربری یا رمز عبور اشتباه است!"
            page.update()
            
    login_panel = ft.Column([
        ft.Divider(height=40, color="transparent"),
        ft.Text("🔒", size=50),
        ft.Text("دروازه ورود کلینیک", size=20, weight="bold"),
        ft.Divider(height=10, color="transparent"),
        login_user, login_pass,
        ft.ElevatedButton("ورود به سیستم", on_click=do_login, bgcolor="teal800", color="white", width=300),
        login_err
    ], horizontal_alignment="center", visible=True)

    # -----------------------------------------------------------------
    # بخش ب: پنل اصلی فرم‌ها (Main Operation Screen)
    # -----------------------------------------------------------------
    mobile_field = ft.TextField(label="شماره موبایل بیمار", width=350, filled=True, keyboard_type="phone", max_length=11)
    code_field = ft.TextField(label="کد تایید ۴ رقمی", width=150, filled=True, keyboard_type="number", max_length=4)
    status_bar = ft.Text("سیستم آماده به کار است.", color="grey", weight="bold", text_align="center")
    
    preview_field = ft.TextField(label="متن نظر نوبت.آی‌آر", multiline=True, min_lines=3, width=350, filled=True)
    sms_text_field = ft.TextField(label="متن پیامک کلینیک", multiline=True, min_lines=2, width=350, filled=True)
    
    preview_container = ft.Column([
        ft.Divider(height=10, color="transparent"),
        preview_field, sms_text_field,
        ft.Row([
            ft.ElevatedButton("فقط ثبت نظر", data="submit", on_click=lambda e: execute_action("submit"), bgcolor="blue600", color="white", width=145),
            ft.ElevatedButton("فقط پیامک", data="sms", on_click=lambda e: execute_action("sms"), bgcolor="orange600", color="white", width=145)
        ], alignment="center"),
        ft.ElevatedButton("ثبت نظر + ارسال پیامک", data="both", on_click=lambda e: execute_action("both"), bgcolor="green600", color="white", width=300)
    ], horizontal_alignment="center", visible=False)

    def request_otp(e):
        m = mobile_field.value.strip()
        if len(m) != 11 or not m.startswith("09"):
            status_bar.value, status_bar.color = "❌ شماره موبایل نامعتبر است.", "red"
            page.update()
            return
        status_bar.value, status_bar.color = "⏳ در حال ارتباط با سرور نوبت...", "blue"
        page.update()
        try:
            res = requests.post("https://api.nobat.ir/patient/login/phone", data={"mobile": m}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") is False:
                    # استفاده از کلید اسکی برای جلوگیری از باگ خط جدید در رشته‌ها
                    status_bar.value = "❌ " + data.get('message', 'محدودیت ارسال') + chr(10) + "💡 راهنما: شماره دیگری را امتحان کنید."
                    status_bar.color = "orange"
                else:
                    status_bar.value, status_bar.color = "✅ کد تایید با موفقیت پیامک شد.", "green"
            else:
                status_bar.value = "❌ سرور درخواست را رد کرد." + chr(10) + "💡 راهنما: آی‌پي بلاک شده، حالت پرواز ✈️ بزنید."
                status_bar.color = "red"
        except:
            status_bar.value, status_bar.color = "❌ خطای شبکه! اتصال اینترنت گوشی را بررسی کنید.", "red"
        page.update()

    def verify_otp(category_data):
        m = mobile_field.value.strip()
        c = code_field.value.strip()
        state["category"] = category_data
        if len(m) != 11 or len(c) != 4:
            status_bar.value, status_bar.color = "❌ لطفاً موبایل و کد تایید را کامل وارد کنید.", "red"
            page.update()
            return
            
        status_bar.value, status_bar.color = "⏳ در حال تایید کد...", "blue"
        page.update()
        
        if c == "1111":
            state["token"] = "mock_test_token"
            preview_field.value = random.choice(db.load_comments().get(category_data, ["پزشک عالی است"]))
            sms_text_field.value = db.load_settings().get("sms_text", "از مراجعه شما سپاسگزاریم.")
            preview_container.visible = True
            status_bar.value, status_bar.color = "✅ تست فعال شد. نظر را ثبت کنید.", "orange"
            page.update()
            return

        try:
            res = requests.post("https://api.nobat.ir/patient/login/verify", data={"mobile": m, "code": c}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "token" in data:
                    state["token"] = data["token"]
                    preview_field.value = random.choice(db.load_comments().get(category_data, ["پزشک عالی است"]))
                    sms_text_field.value = db.load_settings().get("sms_text", "از مراجعه شما سپاسگزاریم.")
                    preview_container.visible = True
                    status_bar.value, status_bar.color = "✅ کد تایید شد. گزینه نهایی را انتخاب کنید.", "green"
                else:
                    status_bar.value = "❌ " + data.get('message', 'کد منقضی شده') + chr(10) + "💡 راهنما: مجدداً دکمه دریافت کد را بزنید."
                    status_bar.color = "red"
            else:
                status_bar.value, status_bar.color = "❌ خطای سرور نوبت. حالت پرواز ✈️ را تست کنید.", "red"
        except:
            status_bar.value, status_bar.color = "❌ خطای شبکه در تایید کد.", "red"
        page.update()

    def execute_action(action_type):
        msgs = []
        current_settings = db.load_settings()
        
        if action_type in ["submit", "both"]:
            if state["token"] == "mock_test_token":
                msgs.append("✅ نظر ثبت شد (تست)")
            else:
                try:
                    res = requests.post("https://api.nobat.ir/nuser/comments/store", data={"token": state["token"], "doctor_id": "245932", "comment": preview_field.value, "score": "3"}, timeout=5)
                    if res.status_code == 200:
                        msgs.append("✅ نظر با موفقیت ثبت شد")
                    else:
                        try:
                            err_txt = res.json().get("message", "خطای محدودیت")
                            msgs.append(f"❌ {err_txt}")
                        except: msgs.append(f"❌ خطا ({res.status_code})")
                except: msgs.append("❌ خطای شبکه نوبت")
                
        if action_type in ["sms", "both"]:
            success = send_sms(page, mobile_field.value, sms_text_field.value, current_settings.get("sms_mode", "local"), current_settings)
            msgs.append("✅ پیامک ارسال شد") if success else msgs.append("❌ خطای پیامک")
            
        logs = db.load_logs()
        logs.append({
            "date_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "secretary": state["user"],
            "mobile": mobile_field.value,
            "category": state["category"],
            "action": action_type,
            "comment": preview_field.value
        })
        db.save_logs(logs)
        
        status_bar.value = " | ".join(msgs)
        status_bar.color = "teal"
        reset_form()

    def reset_form():
        mobile_field.value, code_field.value, preview_field.value = "", "", ""
        state["token"], preview_container.visible = None, False
        page.update()

    def reset_form_click(e):
        reset_form()
        status_bar.value, status_bar.color = "فرم پاکسازی شد.", "grey"
        page.update()

    category_buttons = ft.Column([
        ft.Row([
            ft.ElevatedButton("لیزیک", on_click=lambda e: verify_otp("lasik"), bgcolor="teal700", color="white"),
            ft.ElevatedButton("کاتاراکت", on_click=lambda e: verify_otp("cataract"), bgcolor="teal700", color="white")
        ], alignment="center"),
        ft.Row([
            ft.ElevatedButton("شبکیه", on_click=lambda e: verify_otp("retina"), bgcolor="teal700", color="white"),
            ft.ElevatedButton("بلفارو", on_click=lambda e: verify_otp("blepharoplasty"), bgcolor="teal700", color="white")
        ], alignment="center")
    ])

    end_shift_btn = ft.ElevatedButton("📊 پایان شیفت و ارسال گزارش", on_click=lambda e: show_end_shift(True), bgcolor="teal800", color="white", width=350)
    confirm_section = ft.Column([
        ft.Text("⚠️ کنتور صفر می‌شود. تایید ارسال نهایی؟", color="red800", weight="bold"),
        ft.Row([
            ft.ElevatedButton("✅ بله", on_click=lambda e: do_end_shift(), bgcolor="green700", color="white"),
            ft.ElevatedButton("❌ خیر", on_click=lambda e: show_end_shift(False))
        ], alignment="center")
    ], horizontal_alignment="center", visible=False)

    def show_end_shift(visible_status):
        end_shift_btn.visible = not visible_status
        confirm_section.visible = visible_status
        page.update()

    def do_end_shift():
        show_end_shift(False)
        status_bar.value, status_bar.color = "⏳ در حال ارسال گزارش به سرور و پیام‌رسان بله...", "blue"
        page.update()
        
        logs = db.load_logs()
        if not logs:
            status_bar.value, status_bar.color = "⚠️ لیست بیماران امروز خالی است.", "orange"
            page.update()
            return
            
        try:
            for log in logs:
                payload = {"Date": log.get("date_time"), "Shift": "شیفت کاری", "Total_Patients": 1, "Treatment_Details": log.get("category"), "Platform": "nobat.ir", "SMS_Mode": log.get("action"), "Total_Income": 0, "Description": log.get("comment")}
                requests.post("https://api.iranlasik.ir/api/report", json=payload, headers={"x-api-token": "Secure_Key_2026"}, timeout=4)
        except: pass

        output = io.StringIO()
        output.write('﻿')
        writer = csv.writer(output)
        writer.writerow(["ردیف", "موبایل", "درمان", "نظر"])
        for i, log in enumerate(logs, 1):
            # 🟢 اصلاح قطعی: استفاده از chr(10) به جای کاراکتر اصلاح خط چاپی پایتون جهت جلوگیری از خطا
            clean_comment = log.get("comment", "").replace(chr(10), " ")
            writer.writerow([i, log.get("mobile"), log.get("category"), clean_comment])
            
        try:
            res_bale = requests.post(
                "https://tapi.bale.ai/bot1137791878:xD-QEx6ZHEuqnzBmBFRUklgzo7wFqTDrOmY/sendDocument",
                data={"chat_id": "4448378011", "caption": "📊 گزارش پایان شیفت کلینیک" + chr(10) + f"👤 منشی: {state['user']}" + chr(10) + f"👥 تعداد: {len(logs)}"},
                files={"document": ("Report.csv", output.getvalue().encode('utf-8'), "text/csv")}, timeout=10
            )
            if res_bale.status_code == 200:
                db.clear_logs()
                status_bar.value, status_bar.color = "✅ گزارش امروز با موفقیت ارسال و کنتور صفر شد.", "green"
            else: status_bar.value, status_bar.color = "❌ خطا در سرور بله.", "red"
        except:
            status_bar.value, status_bar.color = "❌ خطای شبکه در ارسال فایل گزارش.", "red"
        page.update()

    main_panel = ft.Column([
        mobile_field,
        ft.ElevatedButton("دریافت کد تایید", on_click=request_otp, width=200, bgcolor="teal800", color="white"),
        code_field,
        category_buttons,
        ft.TextButton("🧹 پاکسازی فرم جاری", on_click=reset_form_click, icon="refresh", icon_color="red"),
        preview_container,
        ft.Divider(height=10),
        status_bar,
        ft.Divider(height=10, color="transparent"),
        end_shift_btn, confirm_section
    ], horizontal_alignment="center", visible=False)

    # -----------------------------------------------------------------
    # بخش ج: پنل تنظیمات (Settings Screen)
    # -----------------------------------------------------------------
    settings_radio = ft.RadioGroup(content=ft.Column([
        ft.Radio(value="local", label="📱 ارسال آفلاین (سیم‌کارت گوشی منشی)"),
        ft.Radio(value="api", label="🌐 ارسال آنلاین (وب‌سرویس کاوه‌نگار)")
    ]))
    
    def open_settings(e):
        main_panel.visible = False
        settings_panel.visible = True
        settings_radio.value = db.load_settings().get("sms_mode", "local")
        page.update()

    def close_settings(e):
        settings_panel.visible = False
        main_panel.visible = True
        page.update()

    def save_settings_click(e):
        current_s = db.load_settings()
        current_s["sms_mode"] = settings_radio.value
        db.save_settings(current_s)
        status_bar.value, status_bar.color = "✅ تنظیمات با موفقیت ذخیره شد.", "green"
        close_settings(None)

    def do_logout(e):
        state["user"] = None
        main_panel.visible = False
        settings_panel.visible = False
        login_panel.visible = True
        page.update()

    settings_panel = ft.Column([
        ft.Text("⚙️ تنظیمات سیستم ارسال پیامک", size=18, weight="bold"),
        ft.Divider(height=15, color="transparent"),
        settings_radio,
        ft.Divider(height=20, color="transparent"),
        ft.ElevatedButton("💾 ذخیره تغییرات", on_click=save_settings_click, bgcolor="green700", color="white", width=250),
        ft.TextButton("⬅️ بازگشت به پنل اصلی", on_click=close_settings)
    ], horizontal_alignment="center", visible=False)

    # -----------------------------------------------------------------
    # رندر نهایی لایه‌های تک صفحه‌ای
    # -----------------------------------------------------------------
    page.appbar = ft.AppBar(
        title=ft.Text("مدیریت هوشمند کلینیک", color="white"),
        bgcolor="teal700",
        actions=[
            ft.IconButton(icon="settings", icon_color="white", on_click=open_settings, tooltip="تنظیمات"),
            ft.IconButton(icon="logout", icon_color="white", on_click=do_logout, tooltip="خروج")
        ]
    )
    
    page.add(login_panel, main_panel, settings_panel)

if __name__ == "__main__":
    ft.app(target=main)
