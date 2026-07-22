import requests

def get_tokens():
    print("="*50)
    print("أداة استخراج التوكن الدائم لفيسبوك")
    print("="*50)
    
    app_id = input("1. أدخل الـ App ID (معرف التطبيق): ").strip()
    app_secret = input("2. أدخل الـ App Secret (الرقم السري للتطبيق): ").strip()
    short_token = input("3. أدخل التوكن القصير الذي ظهر لك في صفحة Graph API: ").strip()
    
    if not all([app_id, app_secret, short_token]):
        print("❌ يجب إدخال جميع البيانات!")
        return

    print("\n⏳ جاري تحويل التوكن القصير إلى توكن 60 يوم...")
    url = f"https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={short_token}"
    
    try:
        res = requests.get(url).json()
        if 'access_token' not in res:
            print("❌ حدث خطأ:", res)
            return
            
        long_user_token = res['access_token']
        print("✅ تم استخراج توكن الـ 60 يوم بنجاح!\n")
        
        print("⏳ جاري استخراج توكن الصفحة الأبدي (الذي لا ينتهي أبداً)...")
        pages_url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={long_user_token}"
        pages_res = requests.get(pages_url).json()
        
        if 'data' not in pages_res or len(pages_res['data']) == 0:
            print("❌ لم يتم العثور على أي صفحات مربوطة بهذا الحساب. تأكد من إعطاء صلاحية pages_manage_posts")
            return
            
        for page in pages_res['data']:
            print("-" * 30)
            print(f"📌 اسم الصفحة: {page.get('name')}")
            print(f"🆔 أيدي الصفحة: {page.get('id')}")
            print(f"🔑 التوكن الأبدي: {page.get('access_token')}")
            print("-" * 30)
            print("🚀 مبروك! انسخ التوكن الأبدي وضعه في إعدادات البوت.")
            
    except Exception as e:
        print("❌ خطأ في الاتصال:", e)

if __name__ == '__main__':
    get_tokens()
