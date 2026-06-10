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
import threading
import time

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
# ۲. موتور ارسال پیامک خوش‌آمدگویی
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
# ۳. بدنه اصلی برنامه (تک‌صفحه‌ای ضد کرش با پالت رنگی اصلی مطب)
# =====================================================================
def main(page: ft.Page):
    # تنظیم دقیق رنگ‌ها و تم بومی کلینیک شما
    page.title = "سامانه مدیریت هوشمند کلینیک"
    page.theme = ft.Theme(color_scheme_seed="teal")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.rtl = True
    
    db = DynamicDataManager()
    state = {"user": None, "token": None, "category": None}

    # -----------------------------------------------------------------
    # بخش الف: فرم ورود (Login Screen)
    # -----------------------------------------------------------------
    login_user = ft.TextField(label="نام کاربری", width=300, filled=True)
    login_pass = ft.TextField(label="رمز عبور", password=True, width=300, filled=True)
    login_err = ft.Text("", color=ft.Colors.RED, weight="bold")
    
    def do_login(e):
        u = login_user.value.strip()
        p = login_pass.value.strip()
        users = db.load_users()
        if u in users and users[u]["password"] == p and users[u]["is_active"]:
            state["user"] = u
            login_panel.visible = False
            main_panel.visible = True
            status_bar.value = f"کاربر {u} فعال است."
            status_bar.color = ft.Colors.GREY
            
            preview_field.visible = users[u].get("can_edit_comments", False)
            end_shift_btn.visible = users[u].get("can_send_reports", False)
            
            # نمایش دکمه‌های هدر بعد از ورود موفقیت‌آمیز منشی
            btn_settings.visible = True
            btn_logout.visible = True
            page.update()
        else:
            login_err.value = "نام کاربری یا رمز عبور اشتباه است!"
            page.update()
            
    login_panel = ft.Column([
        ft.Divider(height=50, color=ft.Colors.TRANSPARENT),
        ft.Text("🔒", size=60),
        ft.Text("دروازه ورود کلینیک", size=24, weight="bold"),
        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
        login_user, login_pass,
        ft.ElevatedButton("ورود به سیستم", on_click=do_login, bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE, width=300),
        login_err
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=True)

    # -----------------------------------------------------------------
    # بخش ب: پنل اصلی فرم‌ها (Main Operation Screen)
    # -----------------------------------------------------------------
    mobile_field = ft.TextField(label="شماره موبایل بیمار", width=350, filled=True, keyboard_type=ft.KeyboardType.PHONE, max_length=11)
    code_field = ft.TextField(label="کد تایید ۴ رقمی", width=150, filled=True, keyboard_type=ft.KeyboardType.NUMBER, max_length=4)
    status_bar = ft.Text("در حال ارتباط و همگام‌سازی اطلاعات با سرور مطب...", color=ft.Colors.BLUE, weight="bold", text_align="center")
    
    preview_field = ft.TextField(label="متن نظر نوبت.آی‌آر", multiline=True, min_lines=3, width=350, filled=True)
    sms_text_field = ft.TextField(label="متن پیامک کلینیک", multiline=True, min_lines=2, width=350, filled=True)
    
    preview_container = ft.Column([
        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
        preview_field, sms_text_field,
        ft.Row([
            ft.ElevatedButton("فقط ثبت نظر", data="submit", on_click=lambda e: execute_action("submit"), bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, width=145),
            ft.ElevatedButton("فقط پیامک", data="sms", on_click=lambda e: execute_action("sms"), bgcolor=ft.Colors.ORANGE_600, color=ft.Colors.WHITE, width=145)
        ], alignment="center"),
        ft.ElevatedButton("ثبت نظر + ارسال پیامک", data="both", on_click=lambda e: execute_action("both"), bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, width=300)
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)

    def request_otp(e):
        m = mobile_field.value.strip()
        if len(m) != 11 or not m.startswith("09"):
            status_bar.value, status_bar.color = "❌ شماره موبایل نامعتبر است.", ft.Colors.RED
            page.update()
            return
        status_bar.value, status_bar.color = "⏳ در حال ارتباط با سرور نوبت...", ft.Colors.BLUE
        page.update()
        try:
            res = requests.post("https://api.nobat.ir/patient/login/phone", data={"mobile": m}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") is False:
                    status_bar.value = "❌ " + data.get('message', 'محدودیت ارسال') + chr(10) + "💡 راهنما: شماره دیگری را امتحان کنید."
                    status_bar.color = ft.Colors.ORANGE
                else:
                    status_bar.value, status_bar.color = "✅ کد تایید با موفقیت پیامک شد.", ft.Colors.GREEN
            else:
                status_bar.value = "❌ سرور درخواست را رد کرد." + chr(10) + "💡 راهنما: آی‌پي بلاک شده، حالت پرواز ✈️ بزنید."
                status_bar.color = ft.Colors.RED
        except:
            status_bar.value, status_bar.color = "❌ خطای شبکه! اتصال اینترنت گوشی را بررسی کنید.", ft.Colors.RED
        page.update()

    def verify_otp(category_data):
        m = mobile_field.value.strip()
        c = code_field.value.strip()
        state["category"] = category_data
        if len(m) != 11 or len(c) != 4:
            status_bar.value, status_bar.color = "❌ لطفاً موبایل و کد تایید را کامل وارد کنید.", ft.Colors.RED
            page.update()
            return
            
        status_bar.value, status_bar.color = "⏳ در حال تایید کد...", ft.Colors.BLUE
        page.update()
        
        if c == "1111":
            state["token"] = "mock_test_token"
            preview_field.value = random.choice(db.load_comments().get(category_data, ["پزشک عالی است"]))
            sms_text_field.value = db.load_settings().get("sms_text", "از مراجعه شما سپاسگزاریم.")
            preview_container.visible = True
            status_bar.value, status_bar.color = "✅ تست فعال شد. نظر را ثبت کنید.", ft.Colors.ORANGE
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
                    status_bar.value, status_bar.color = "✅ کد تایید شد. گزینه نهایی را انتخاب کنید.", ft.Colors.GREEN
                else:
                    status_bar.value = "❌ " + data.get('message', 'کد منقضی شده') + chr(10) + "💡 راهنما: مجدداً دکمه دریافت کد را بزنید."
                    status_bar.color = ft.Colors.RED
            else:
                status_bar.value, status_bar.color = "❌ خطای سرور نوبت. حالت پرواز ✈️ را تست کنید.", ft.Colors.RED
        except:
            status_bar.value, status_bar.color = "❌ خطای شبکه در تایید کد.", ft.Colors.RED
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
        status_bar.color = ft.Colors.TEAL
        reset_form()

    def reset_form():
        mobile_field.value, code_field.value, preview_field.value = "", "", ""
        state["token"], preview_container.visible = None, False
        page.update()

    def reset_form_click(e):
        reset_form()
        status_bar.value, status_bar.color = "فرم پاکسازی شد.", ft.Colors.GREY
        page.update()

    category_buttons = ft.Column([
        ft.Row([
            ft.ElevatedButton("لیزیک", on_click=lambda e: verify_otp("lasik")),
            ft.ElevatedButton("کاتاراکت", on_click=lambda e: verify_otp("cataract"))
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([
            ft.ElevatedButton("شبکیه", on_click=lambda e: verify_otp("retina")),
            ft.ElevatedButton("بلفارو", on_click=lambda e: verify_otp("blepharoplasty"))
        ], alignment=ft.MainAxisAlignment.CENTER)
    ])

    end_shift_btn = ft.ElevatedButton("📊 پایان شیفت و ارسال گزارش", on_click=lambda e: show_end_shift(True), bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE, width=350)
    confirm_section = ft.Column([
        ft.Text("⚠️ کنتور صفر می‌شود. تایید ارسال نهایی؟", color=ft.Colors.RED_800, weight="bold"),
        ft.Row([
            ft.ElevatedButton("✅ بله", on_click=lambda e: do_end_shift(), bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            ft.ElevatedButton("❌ خیر", on_click=lambda e: show_end_shift(False))
        ], alignment=ft.MainAxisAlignment.CENTER)
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)

    def show_end_shift(visible_status):
        end_shift_btn.visible = not visible_status
        confirm_section.visible = visible_status
        page.update()

    def do_end_shift():
        show_end_shift(False)
        status_bar.value, status_bar.color = "⏳ در حال ارسال گزارش به سرور و پیام‌رسان بله...", ft.Colors.BLUE
        page.update()
        
        logs = db.load_logs()
        if not logs:
            status_bar.value, status_bar.color = "⚠️ لیست بیماران امروز خالی است.", ft.Colors.ORANGE
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
                status_bar.value, status_bar.color = "✅ گزارش امروز با موفقیت ارسال و کنتور صفر شد.", ft.Colors.GREEN
            else: status_bar.value, status_bar.color = "❌ خطا در سرور بله.", ft.Colors.RED
        except:
            status_bar.value, status_bar.color = "❌ خطای شبکه در ارسال فایل گزارش.", ft.Colors.RED
        page.update()

    main_panel = ft.Column([
        mobile_field,
        ft.ElevatedButton("دریافت کد تایید", on_click=request_otp, width=200, bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE),
        code_field,
        category_buttons,
        ft.TextButton("🧹 پاکسازی فرم جاری", on_click=reset_form_click, icon=ft.Icons.REFRESH, icon_color="red"),
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
        status_bar.value, status_bar.color = "✅ تنظیمات با موفقیت ذخیره شد.", ft.Colors.GREEN
        close_settings(None)

    def do_logout(e):
        state["user"] = None
        main_panel.visible = False
        settings_panel.visible = False
        btn_settings.visible = False
        btn_logout.visible = False
        login_panel.visible = True
        page.update()

    settings_panel = ft.Column([
        ft.Text("⚙️ تنظیمات سیستم ارسال پیامک", size=18, weight="bold"),
        ft.Divider(height=15, color="transparent"),
        settings_radio,
        ft.Divider(height=20, color="transparent"),
        ft.ElevatedButton("💾 ذخیره تغییرات", on_click=save_settings_click, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, width=250),
        ft.TextButton("⬅️ بازگشت به پنل اصلی", on_click=close_settings)
    ], horizontal_alignment="center", visible=False)

    # -----------------------------------------------------------------
    # دکمه‌های ابزار بالای صفحه (کاملاً هماهنگ با ظاهر اصلی)
    # -----------------------------------------------------------------
    btn_settings = ft.TextButton(content=ft.Text("⚙️ تنظیمات", color=ft.Colors.WHITE), on_click=open_settings, visible=False)
    btn_logout = ft.TextButton(content=ft.Text("🚪 خروج", color=ft.Colors.WHITE), on_click=do_logout, visible=False)

    page.appbar = ft.AppBar(
        title=ft.Text("مدیریت هوشمند کلینیک", color=ft.Colors.WHITE),
        bgcolor=ft.Colors.TEAL_700,
        actions=[btn_settings, btn_logout]
    )
    
    page.add(login_panel, main_panel, settings_panel)

    # -----------------------------------------------------------------
    # دوقلوهای پایش پس‌زمینه بله و همگام‌سازی آنی سرور مرکزی در بدو ورود
    # -----------------------------------------------------------------
    def sync_with_server_bg():
        try:
            res = requests.get("https://api.iranlasik.ir/api/sync", headers={"x-api-token": "Secure_Key_2026"}, timeout=6)
            if res.status_code == 200:
                data = res.json()
                if "settings" in data: db.save_settings(data["settings"])
                if "users" in data: db.save_users(data["users"])
                if "comments" in data: db.save_comments(data["comments"])
                status_bar.value, status_bar.color = "✅ اتصال سرور برقرار است. اطلاعات سیستم بروزرسانی شد.", ft.Colors.GREEN
                page.update()
        except:
            status_bar.value, status_bar.color = "⚠️ سیستم آفلاین است. (عدم دسترسی به سرور مرکزی)", ft.Colors.ORANGE
            page.update()

    def bale_polling_bg():
        TOKEN = "1137791878:xD-QEx6ZHEuqnzBmBFRUklgzo7wFqTDrOmY"
        BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
        last_update_id = 0
        while True:
            try:
                res = requests.get(f"{BASE_URL}/getUpdates", params={"offset": last_update_id, "timeout": 10}, timeout=15)
                if res.status_code == 200:
                    updates = res.json().get("result", [])
                    for update in updates:
                        last_update_id = update["update_id"] + 1
                        msg = update.get("message", {})
                        if "document" in msg and msg["document"].get("file_name") == "clinic_data.json":
                            file_id = msg["document"]["file_id"]
                            chat_id = msg["chat"]["id"]
                            file_res = requests.get(f"{BASE_URL}/getFile", params={"file_id": file_id}).json()
                            if file_res.get("ok"):
                                file_path = file_res["result"]["file_path"]
                                content = requests.get(f"https://tapi.bale.ai/file/bot{TOKEN}/{file_path}").text
                                data = json.loads(content)
                                if "settings" in data: db.save_settings(data["settings"])
                                if "comments" in data: db.save_comments(data["comments"])
                                if "users" in data: db.save_users(data["users"])
                                requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": "✅ پکیج اضطراری دیتابیس توسط گوشی دریافت شد."})
                                status_bar.value, status_bar.color = "📥 دیتابیس اضطراری از بله دریافت شد.", ft.Colors.TEAL
                                page.update()
            except: pass
            time.sleep(5)

    # استارت آنی لوپ‌های پایش پس‌زمینه شبکه
    threading.Thread(target=sync_with_server_bg, daemon=True).start()
    threading.Thread(target=bale_polling_bg, daemon=True).start()

if __name__ == "__main__":
    ft.app(target=main)
