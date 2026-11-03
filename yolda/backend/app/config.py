from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://yolda:yolda@localhost:5432/yolda"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    DEMO_SIMULATION: bool = False
    RUN_WORKERS: bool = True
    RATE_LIMIT_PER_MIN: int = 60
    OSRM_URL: str = "https://router.project-osrm.org"  # marshrut serveri; bo'sh = faqat to'g'ri chiziq
    BOT_API_KEY: str = ""  # Telegram bot servisi shu kalit bilan /api/bot ga murojaat qiladi (bo'sh = o'chiq)

    # Multicard (Rahmat) to'lov shlyuzi. Bo'sh = o'chiq (/pay 503 qaytaradi)
    MULTICARD_BASE_URL: str = "https://dev-mesh.multicard.uz"  # production: https://mesh.multicard.uz
    MULTICARD_APP_ID: str = ""
    MULTICARD_SECRET: str = ""        # token olish va callback imzosi uchun
    MULTICARD_STORE_ID: str = ""      # kassa ID
    MULTICARD_MXIK: str = ""          # taomlar uchun IKPU kodi (tasnif.soliq.uz) — fiskal chek uchun majburiy
    MULTICARD_PACKAGE_CODE: str = ""  # shu IKPU ning o'ram kodi
    MULTICARD_DELIVERY_MXIK: str = ""      # yetkazib berish xizmati IKPU (bo'sh = MULTICARD_MXIK)
    MULTICARD_DELIVERY_PACKAGE_CODE: str = ""
    MULTICARD_CALLBACK_IPS: str = ""  # vergul bilan; bo'sh = IP tekshirilmaydi (imzo baribir tekshiriladi). Multicard: 195.158.26.90
    MULTICARD_METHODS: str = "card,payme,click,uzum"  # saytlarda ko'rsatiladigan usullar (payments.METHODS dagi kodlar)
    MULTICARD_INVOICE_TTL: int = 3600  # to'lov havolasi amal qilish muddati (soniya)
    PUBLIC_API_URL: str = ""          # callback manzili uchun, masalan https://yolda-api.2-31-28-150.sslip.io

    # Biznes konstantalari
    SLA: int = 45
    CASH_LIMIT: int = 400_000
    COMMISSION: float = 0.15
    VENDOR_COMMISSION: float = 0.15  # restoran buyurtma summasidan platforma komissiyasi
    BONUS_PER_10: int = 20_000
    LATE_FINE: int = 5_000


settings = Settings()
SLA = settings.SLA

TRANSPORTS = {
    "Skuter": {"name": "Skuter", "speed": 28, "max_km": 12.0},
    "Avto": {"name": "Avtomobil", "speed": 24, "max_km": None},
    "Velo": {"name": "Velosiped", "speed": 15, "max_km": 5.0},
    "Piyoda": {"name": "Piyoda", "speed": 6, "max_km": 2.5},
}

ORDER_STATUS = {
    "new": ("Kuryer kutilmoqda", "red"),
    "assigned": ("Kuryer restoranga yo'lda", "blue"),
    "onway": ("Mijozga yo'lda", "teal"),
    "delivered": ("Yetkazildi", "grey"),
    "cancelled": ("Bekor qilindi", "red"),
}

PAY_STATUS = {
    "paid": ("To'langan", "teal"),
    "pending": ("Tasdiqlanmoqda", "amber"),
    "failed": ("To'lov o'tmadi", "red"),
    "cod": ("Kuryer oladi", "blue"),
    "collected": ("Kuryer oldi", "grey"),
    "refunded": ("Qaytarildi", "violet"),
    "void": ("To'lanmagan", "grey"),
}

ISSUES = {
    "noanswer": {"text": "Mijoz telefonni ko'tarmayapti", "when": "delivering", "delay": 6},
    "address": {"text": "Mijoz manzili topilmadi", "when": "delivering", "delay": 8},
    "restdelay": {"text": "Restoran buyurtmani kechiktirmoqda", "when": "pickup", "delay": 10},
    "vehicle": {"text": "Transport nosozligi", "when": "any", "delay": 12},
    "wrong": {"text": "Buyurtma tarkibida xatolik", "when": "delivering", "delay": 5},
}

VENDOR_LEDGER_TYPES = {
    "payment": ("To'lov", "green"),
    "commission": ("Komissiya", "amber"),
    "payout": ("Pul o'tkazildi", "blue"),
    "fix": ("Tuzatish", "violet"),
}

LEDGER_TYPES = {
    "earn": ("Yetkazish haqi", "teal"),
    "cash": ("Naqd pul mijozdan olindi", "red"),
    "topup": ("Naqd pul topshirildi", "blue"),
    "payout": ("Maosh to'lab berildi", "amber"),
    "fix": ("Bonus / tuzatish", "violet"),
    "penalty": ("Kechikish jarimasi", "red"),
}
