# Telegram Hesap Al-Sat Botu

Bu proje, Telegram üzerinden kripto yatırma, bakiye takibi ve hesap al-sat işlemlerini yönetmek için bir bot altyapısı sağlar.

## Özellikler

- Kripto yatırma için ağ seçimi ve kullanıcıya özel adres üretimi.
- Yatırma adresleri kullanıcıya özel olarak saklanır.
- /balance komutu ile bakiye görüntüleme.
- /sell komutu ile hesap satış akışı (ödeme birimi, adres, e-posta, şifre, iletişim).
- Satış bilgileri admin sohbetine otomatik iletilir.
- Yatırma kontrolü için periyodik iş (mock sağlayıcı ile).

> Not: Gerçek blok zinciri entegrasyonu için `wallet_provider.py` dosyasındaki sağlayıcıyı gerçek API ile değiştirmeniz gerekir.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Çalıştırma

Önce `.env` dosyasını oluşturun:

```bash
cp .env.example .env
```

Ardından botu çalıştırın:

```bash
export $(cat .env | xargs)
python -m src.bot
```

## Ortam Değişkenleri

- `TELEGRAM_BOT_TOKEN`: Telegram bot token.
- `ADMIN_CHAT_ID`: Satış taleplerinin iletileceği admin sohbet ID'si.
- `BOT_DB_PATH`: SQLite veritabanı yolu (varsayılan: `data/bot.db`).
- `MOCK_WALLET_PREFIX`: Mock adresler için ön ek (opsiyonel).
