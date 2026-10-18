"""Demo menyular va Toshkent tumanlari (seed va simulyator uchun)."""
import random

MENUS = {
    "kafe": [("Kapuchino", 25000), ("Latte", 27000), ("Cheesecake", 35000), ("Sezar salati", 45000),
             ("Karbonara pastasi", 62000), ("Limonad", 22000), ("Kruassan", 18000)],
    "milliy": [("Osh (to'y oshi)", 45000), ("Somsa", 12000), ("Lag'mon", 38000), ("Manti", 36000), ("Norin", 40000),
               ("Achchiq-chuchuk", 15000), ("Non", 5000), ("Ko'k choy", 8000)],
    "fast": [("Lavash", 32000), ("Tandir lavash", 35000), ("Burger", 39000), ("Cheeseburger", 42000),
             ("Hot-dog", 18000), ("Kartoshka fri", 15000), ("Kola 0.5", 10000)],
    "pitsa": [("Margarita", 69000), ("Pepperoni", 79000), ("To'rt pishloq", 85000), ("Tovuqli BBQ", 82000),
              ("Sezar salati", 42000), ("Kola 1L", 14000)],
    "sushi": [("Filadelfiya roll", 89000), ("Kaliforniya roll", 75000), ("Sakura set", 189000),
              ("Miso sho'rva", 28000), ("Gunkan losos", 42000)],
    "grill": [("Qo'y go'shti shashlik", 25000), ("Lyulya kabob", 22000), ("Jigar shashlik", 20000),
              ("Tovuq qanotlari", 45000), ("Piyoz salat", 8000), ("Non", 5000)],
    "soglom": [("Tovuqli bowl", 55000), ("Losos bowl", 78000), ("Yashil smuzi", 30000), ("Grek salati", 40000),
                ("Granola", 28000)],
}

RESTAURANT_MENU = {
    "Mondi kafe": "kafe", "Rayhon milliy taomlar": "milliy", "Lavash Markazi": "fast", "Pizza Bello": "pitsa",
    "Sakura Sushi": "sushi", "Choyxona Navro'z": "milliy", "Burger Town": "fast", "Shashlik Usta": "grill",
    "Green Bowl": "soglom", "Somsa Ota": "milliy", "Dolce Cafe": "kafe", "Sergeli Lavash": "fast",
}

DISTRICTS = {
    "Yunusobod": (41.3650, 69.2890), "Olmazor": (41.3500, 69.2200), "Shayxontohur": (41.3280, 69.2380),
    "Chilonzor": (41.2750, 69.2040), "Yakkasaroy": (41.2950, 69.2620), "Mirobod": (41.2990, 69.2850),
    "Mirzo Ulug'bek": (41.3380, 69.3340), "Yashnobod": (41.3110, 69.3450), "Sergeli": (41.2250, 69.2200),
    "Uchtepa": (41.2870, 69.1650),
}

FIRST_NAMES = ["Sardor", "Jasur", "Bekzod", "Otabek", "Aziz", "Dilshod", "Rustam", "Shoxrux", "Akmal", "Nodir",
               "Sanjar", "Farrux", "Ulug'bek", "Jahongir", "Behruz", "Eldor", "Timur", "Islom", "Anvar", "Kamol",
               "Oybek", "Bobur", "Zafar", "Abdulla", "Madina", "Dilnoza"]
LAST_NAMES = ["Karimov", "Rahimov", "Tursunov", "Yusupov", "Abdullayev", "Ergashev", "Nazarov", "Saidov", "Ismoilov",
              "Qodirov", "Mirzayev", "Hasanov", "Normatov", "Sobirov", "Xolmatov", "Toshmatov", "Aliyev", "Rustamov",
              "Usmonov", "Bekmurodov", "Jo'rayev", "Haydarov", "Salimov", "Umarov", "Karimova", "Rahimova"]
CUSTOMER_NAMES = ["Dilnoza A.", "Sardor M.", "Madina K.", "Jasur T.", "Nigora S.", "Aziza R.", "Bobur Q.", "Zarina H.",
                  "Otabek N.", "Malika Y.", "Shahzod I.", "Gulnora B.", "Timur A.", "Kamila D.", "Rustam E."]
CANCEL_REASONS = ["Mijoz bekor qildi", "Restoranda mahsulot tugagan", "Mijoz telefonni ko'tarmadi",
                  "Kutish vaqti uzoq bo'ldi", "Manzil noto'g'ri ko'rsatilgan", "Onlayn to'lov o'tmadi"]


def menu_for(restaurant) -> list[tuple[str, int]]:
    return MENUS[RESTAURANT_MENU.get(restaurant.name, "fast")]


def pick_items(restaurant, rnd: random.Random, n: int | None = None) -> list[dict]:
    menu = menu_for(restaurant)
    n = n or rnd.choice([1, 2, 2, 3, 3, 4])
    chosen = rnd.sample(menu, min(n, len(menu)))
    return [{"name": nm, "qty": rnd.choice([1, 1, 1, 2, 2, 3]), "price": pr} for nm, pr in chosen]


def rand_phone(rnd: random.Random) -> str:
    return "+998" + rnd.choice(["90", "91", "93", "94", "97", "99", "88", "95"]) + "".join(str(rnd.randint(0, 9)) for _ in range(7))
