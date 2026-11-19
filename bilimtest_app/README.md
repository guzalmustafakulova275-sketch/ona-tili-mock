# BilimTest — ishga tushirish

## Talablar
- Python 3.10 yoki yangiroq
- Internetga ulash uchun server (Render, VPS va boshqalar)

## Lokal ishga tushirish
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Brauzerda `http://127.0.0.1:5000` ni oching. Boshqa qurilmalar bir Wi-Fi tarmog‘ida bo‘lsa, server kompyuterining lokal IP manzili va `:5000` porti orqali ulanishi mumkin.

## Admin
- Tugma: **Admin kirish**
- Standart parol: `ahmadjon123`
- Deployda `ADMIN_PASSWORD` va `SECRET_KEY` environment variable qilib belgilang.

## Muhim funksiyalar
- Admin autentifikatsiyasi server sessiyasi bilan
- O‘quvchi ismi va imtihon kodi bilan kutish xonasiga kiradi
- Server vaqtiga asoslangan umumiy start va taymer
- Javoblar SQLite bazasiga avtomatik saqlanadi
- Admin imtihonni boshlaydi/yakunlaydi, sessiya ochadi
- Ishtirokchilar ro‘yxati va javoblar soni yangilanib turadi
- Natijalar admin tomonidan e’lon qilinmaguncha o‘quvchiga ko‘rsatilmaydi
- Javoblarni CSV/Excel uchun eksport qilish
- Imtihonlar tarixi
- Oldindan tayyorlangan 44 savolli JSON importi

## Savollar JSON formati
`questions` massivida aynan 44 obyekt bo‘lishi kerak. Namuna:
```json
{
  "questions": [
    {"text":"Savol matni", "type":"choice", "options":["A javob","B javob","C javob","D javob"]},
    {"text":"Ochiq savol matni", "type":"open"}
  ]
}
```
Massiv 44 ta elementdan iborat bo‘lishi shart.

## Hozircha cheklovlar
- SQLite bitta server uchun demo/prototip bazasi. Katta oqim uchun PostgreSQL tavsiya qilinadi.
- Javoblar yig‘iladi, ammo rasmiy javob kaliti va BMBA kalibrlash parametrlari bo‘lmagani sababli avtomatik baho/Rasch 75 ball hisoblanmaydi.
- Ochiq javoblarni rubrika asosida tekshirish va admin tasdiqlashi keyingi modul sifatida qo‘shilishi kerak.
- Demo parolni internetga ochiq serverda albatta o‘zgartiring.

## Windows uchun tez ishga tushirish
`start_windows.bat` faylini ikki marta bosing. U Flask kutubxonasini o‘rnatib, serverni ishga tushiradi. Birinchi marta internet kerak bo‘ladi.
