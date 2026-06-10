---
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
        output.write('\ufeff')
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
    # رندر نهایی لایه‌های دکمه بار بالا (اصلاح قطعی با حذف آیکون باتن مشکل دار)
    # -----------------------------------------------------------------
    page.appbar = ft.AppBar(
        title=ft.Text("مدیریت هوشمند کلینیک", color="white"),
        bgcolor="teal700",
        actions=[
            ft.TextButton(content=ft.Text("⚙️ تنظیمات", color="white"), on_click=open_settings),
            ft.TextButton(content=ft.Text("🚪 خروج", color="white"), on_click=do_logout)
        ]
    )
    
    page.add(login_panel, main_panel, settings_panel)

if __name__ == "__main__":
    ft.app(target=main)
