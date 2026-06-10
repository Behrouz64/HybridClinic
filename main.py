 = msg["chat"]["id"]
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
