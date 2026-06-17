import flet as ft
import requests
import random
import json

# شناسه اختصاصی شما در سایت نوبت دات آی آر
DOCTOR_ID = "245932"
HEADERS = {
    "origin": "https://plugin.nobat.ir",
    "referer": "https://plugin.nobat.ir/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}

def main(page: ft.Page):
    # تنظیمات پنجره
    page.title = "سیستم ثبت هوشمند نظرات بیماران"
    page.window_width = 460
    page.window_height = 760
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed="teal") 
    page.rtl = True
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    # متغیرهای ذخیره وضعیت (State)
    app_state = {
        "token": None,
        "category": None,
        "admin_mode": False
    }

    # --- توابع مدیریت ماندگاری حالت پزشک با فایل لوکال ---
    def check_admin_status():
        try:
            with open('admin_status.txt', 'r', encoding='utf-8') as f:
                return f.read().strip() == "activated"
        except:
            return False

    def save_admin_status():
        try:
            with open('admin_status.txt', 'w', encoding='utf-8') as f:
                f.write("activated")
        except:
            pass

    # بازیابی وضعیت از فایل
    app_state["admin_mode"] = check_admin_status()

    # --- بارگذاری دیتابیس نظرات ---
    def load_comments():
        try:
            with open('comments.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"error": "فایل پیدا نشد"}

    comments_db = load_comments()

    # --- المان‌های رابط کاربری ---
    mobile_field = ft.TextField(
        label="شماره موبایل بیمار", 
        width=350, 
        text_align=ft.TextAlign.LEFT,
        filled=True,
        border_radius=10
    )
    
    code_field = ft.TextField(
        label="کد ۴ رقمی پیامک", 
        width=150, 
        text_align=ft.TextAlign.LEFT,
        filled=True,
        border_radius=10
    )
    
    # نمایش وضعیت اولیه بر اساس فایل ذخیره‌شده
    initial_status = "وضعیت: آماده عملیات (حالت پیشرفته فعال)" if app_state["admin_mode"] else "وضعیت: آماده عملیات"
    initial_color = "blue700" if app_state["admin_mode"] else "grey700"
    status_text = ft.Text(value=initial_status, color=initial_color, size=14, weight="bold")

    preview_field = ft.TextField(
        label="متن نظر (قابل ویرایش)", 
        multiline=True, 
        min_lines=3, 
        max_lines=6,
        width=350,
        filled=True,
        border_radius=10
    )
    
    def show_status(msg, color="green"):
        status_text.value = msg
        status_text.color = color
        page.update()

    # --- توابع دکمه‌ها ---
    
    def on_cancel(e=None):
        mobile_field.value = ""
        mobile_field.disabled = False
        code_field.value = ""
        code_field.disabled = False
        preview_field.value = ""
        app_state["token"] = None
        app_state["category"] = None
        
        category_buttons.disabled = False
        preview_container.visible = False
        
        if app_state["admin_mode"]:
            show_status("فرم پاک شد. آماده برای بیمار جدید (حالت پیشرفته)", "blue700")
        else:
            show_status("فرم پاک شد. آماده برای بیمار جدید.", "grey700")
        page.update()

    # 1️⃣ گام اول: درخواست کد تایید (JSON عمومی بهینه)
    def on_request_otp(e):
        mobile = mobile_field.value.strip()
        if not mobile:
            show_status("❌ ابتدا شماره موبایل را وارد کنید.", "red")
            return
        
        show_status("⏳ در حال ارسال درخواست پیامک...", "blue")
        url = "https://api.nobat.ir/patient/login/phone"
        payload = {"mobile": mobile}
        
        try:
            res = requests.post(url, json=payload, headers=HEADERS, timeout=15)
            if res.status_code == 200 and res.json().get("status") == "success":
                show_status(f"✅ پیامک به {mobile} ارسال شد. منتظر کد...", "green")
            else:
                show_status("❌ خطا در ارسال پیامک. بررسی کنید یا حالت پرواز را تغییر دهید.", "red")
        except Exception:
            show_status("❌ خطای شبکه! لطفاً حالت پرواز (Flight Mode) گوشی را یک‌بار روشن و خاموش کنید.", "red")

    # 2️⃣ گام دوم: شکار توکن امنیتی عمومی
    def on_verify_and_preview(e):
        category = e.control.data
        mobile = mobile_field.value.strip()
        code = code_field.value.strip()

        if not mobile or not code:
            show_status("❌ شماره موبایل و کد تایید الزامی است.", "red")
            return

        # بررسی کد جادویی و ذخیره پایدار در فایل برای همیشه
        if mobile == "09120196457" and code == "0000":
            app_state["admin_mode"] = True
            save_admin_status()
            show_status("🔓 حالت پیشرفته برای همیشه روی این دستگاه فعال شد!", "blue700")
            mobile_field.value = ""
            code_field.value = ""
            page.update()
            return

        if "error" in comments_db:
            show_status("❌ فایل comments.json پیدا نشد!", "red")
            return

        # 🧪 بررسی حالت تست (کد 1111) بدون نیاز به ارتباط با سرور
        if code == "1111":
            app_state["token"] = "mock_test_token"
            app_state["category"] = category
            
            # انتخاب متن رندوم در پشت صحنه
            preview_field.value = random.choice(comments_db.get(category, ["عالی بود"]))
            
            mobile_field.disabled = True
            code_field.disabled = True
            category_buttons.disabled = True
            
            if app_state["admin_mode"]:
                preview_container.visible = True
                show_status("🧪 حالت تست فعال شد! نظر را بررسی و تایید کنید.", "orange")
                page.update()
            else:
                show_status("⏳ حالت تست! در حال ثبت شبیه‌سازی‌شده نظر...", "blue")
                on_final_submit(None)
            return

        show_status("⏳ در حال بررسی کد تایید...", "blue")
        verify_url = "https://api.nobat.ir/patient/login/verify"
        verify_payload = {"mobile": mobile, "code": code}
        
        try:
            res_verify = requests.post(verify_url, json=verify_payload, headers=HEADERS, timeout=15)
            res_json = res_verify.json()
            
            if "token" not in res_json:
                show_status("❌ کد اشتباه است یا منقضی شده.", "red")
                return
            
            app_state["token"] = res_json["token"]
            app_state["category"] = category
            
            # انتخاب متن رندوم در پشت صحنه
            preview_field.value = random.choice(comments_db.get(category, ["عالی بود"]))
            
            mobile_field.disabled = True
            code_field.disabled = True
            category_buttons.disabled = True
            
            if app_state["admin_mode"]:
                preview_container.visible = True
                show_status("✅ کد تایید شد! نظر را بررسی و ثبت نهایی کنید.", "green")
                page.update()
            else:
                show_status("⏳ کد تایید شد. در حال ثبت خودکار نظر در سایت...", "blue")
                on_final_submit(None) 
                
        except Exception:
            show_status("❌ خطای شبکه در بررسی کد! در صورت تکرار حالت پرواز را روشن/خاموش کنید.", "red")

    def on_regenerate_text(e):
        cat = app_state["category"]
        if cat and cat in comments_db:
            preview_field.value = random.choice(comments_db[cat])
            page.update()

    # 3️⃣ گام سوم: ثبت نظر
    def on_final_submit(e):
        token = app_state["token"]
        final_comment = preview_field.value.strip()
        
        if not token or not final_comment:
            show_status("❌ خطای سیستمی: توکن یا متن نظر خالی است.", "red")
            return

        if e is not None:
            show_status("⏳ در حال ثبت نهایی نظر...", "blue")

        # 🧪 شبیه‌سازی موفقیت‌آمیز در صورت فعال بودن حالت تست
        if token == "mock_test_token":
            on_cancel()
            show_status("🎉 (حالت تست) مراحل با موفقیت شبیه‌سازی و ثبت شد!", "green")
            return
            
        store_url = "https://api.nobat.ir/nuser/comments/store"
        store_files = {
            "token": (None, token),
            "doctor_id": (None, DOCTOR_ID),
            "comment": (None, final_comment),
            "score": (None, "3") 
        }
        
        try:
            res_store = requests.post(store_url, files=store_files, headers=HEADERS, timeout=15)
            if res_store.status_code == 200 and res_store.json().get("status") == "success":
                on_cancel()
                show_status("🎉 نظر با موفقیت در سایت ثبت شد!", "green")
            else:
                on_cancel()
                show_status("❌ خطا در ثبت نظر در سایت نوبت دات آی آر.", "red")
        except Exception:
            on_cancel()
            show_status("❌ خطای شبکه هنگام ثبت نهایی. وضعیت اتصال را چک کنید.", "red")

    page.appbar = ft.AppBar(
        title=ft.Text("سیستم ثبت هوشمند نظرات بیماران", weight="bold", size=18, color="teal"),
        center_title=True
    )

    # --- چیدمان دسته‌بندی‌ها ---
    category_buttons = ft.Column([
        ft.Row([
            ft.ElevatedButton("لیزیک", data="lasik", on_click=on_verify_and_preview, width=170, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
            ft.ElevatedButton("کاتاراکت", data="cataract", on_click=on_verify_and_preview, width=170, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        ft.Container(height=2),
        ft.Row([
            ft.ElevatedButton("شبکیه / دیابت", data="retina", on_click=on_verify_and_preview, width=170, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
            ft.ElevatedButton("بلفاروپلاستی", data="blepharoplasty", on_click=on_verify_and_preview, width=170, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
    ])

    # --- چیدمان مرحله سوم ---
    preview_container = ft.Container(
        visible=False,
        content=ft.Column([
            ft.Divider(height=20),
            ft.Text("مرحله سوم: بررسی و تایید نهایی", weight="bold", color="teal", size=15),
            preview_field,
            ft.Row([
                ft.ElevatedButton("تغییر متن (رندوم)", on_click=on_regenerate_text, bgcolor="grey200", color="black", height=45),
                ft.ElevatedButton("ثبت نهایی نظر", on_click=on_final_submit, bgcolor="green600", color="white", height=45),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Container(height=5),
            ft.TextButton(content=ft.Text("انصراف و پاک کردن فرم", color="red"), on_click=on_cancel)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    )

    # --- کانتینر اصلی صفحه ---
    main_layout = ft.Container(
        width=400,
        padding=15,
        content=ft.Column([
            ft.Text("مرحله اول:", weight="bold", size=15),
            mobile_field,
            ft.ElevatedButton("ارسال کد پیامک به گوشی بیمار", on_click=on_request_otp, width=350, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
            
            ft.Divider(height=25),
            
            ft.Text("مرحله دوم:", weight="bold", size=15),
            code_field,
            ft.Text("نوع درمان را انتخاب کنید (ابتدا کد بررسی می‌شود):", size=13),
            category_buttons,
            
            preview_container, 
            
            ft.Divider(height=15),
            status_text
            
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
    )

    page.add(main_layout)

ft.app(target=main)
