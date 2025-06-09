import subprocess
import sys
import requests
import re
import os
from collections import defaultdict
from colorama import init, Fore

def install_package(package, import_name=None):
    try:
        __import__(import_name or package)
    except ImportError:
        print(f"[+] Установка {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_package("colorama")
install_package("requests")

init(autoreset=True)

ascii_art = """
▄▄▄▄███▄▄▄▄    ▄█     ▄████████    ▄████████  ▄██████▄     ▄████████ 
▄██▀▀▀███▀▀▀██▄ ███    ███    ███   ███    ███ ███    ███   ███    ███ 
███   ███   ███ ███▌   ███    ███   ███    ███ ███    ███   ███    ███ 
███   ███   ███ ███▌  ▄███▄▄▄▄██▀  ▄███▄▄▄▄██▀ ███    ███  ▄███▄▄▄▄██▀ 
███   ███   ███ ███▌ ▀▀███▀▀▀▀▀   ▀▀███▀▀▀▀▀   ███    ███ ▀▀███▀▀▀▀▀   
███   ███   ███ ███  ▀███████████ ▀███████████ ███    ███ ▀███████████ 
███   ███   ███ ███    ███    ███   ███    ███ ███    ███   ███    ███ 
 ▀█   ███   █▀  █▀     ███    ███   ███    ███  ▀██████▀    ███    ███ 
                        ███    ███   ███    ███              ███    ███
"""

menu = """

 [1] - Пойск по Osint             
 [2] - Пойск по GeOsint           
 [3] - Пойск по Nickname  
 [4] - Выход                    

"""

def is_ip(query):
    return re.match(r"^\d{1,3}(\.\d{1,3}){3}$", query.strip()) is not None

def is_capital_osm(address_data):
    if address_data.get('capital', '').lower() == 'yes':
        return True
    if address_data.get('state', '').lower() == 'capital':
        return True
    return False

def translate_text(text, target_lang="en", source_lang="auto"):
    url = "https://libretranslate.de/translate"
    payload = {
        "q": text,
        "source": source_lang,
        "target": target_lang,
        "format": "text"
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get("translatedText", "")
        else:
            print(f"[+] Ошибка {response.status_code}")
            return text
    except Exception as e:
        print(f"[+] Ошибка  {e}")
        return text

def pretty_print(data: dict):
    lines = []
    def maybe_translate(value):
        if isinstance(value, str) and any('\u0400' <= c <= '\u04FF' for c in value):
            return translate_text(value)
        return value

    city = maybe_translate(data.get("city"))
    capital = data.get("capital")
    cap_str = "Да" if capital else "Нет" if capital is not None else None
    street = maybe_translate(data.get("street"))
    porch = maybe_translate(data.get("porch"))
    apartment = maybe_translate(data.get("apartment"))

    if city:
        lines.append(f"├ Город -> {city}")
    if cap_str is not None:
        lines.append(f"├ Столица -> {cap_str}")
    if street:
        lines.append(f"├ Улица -> {street}")
    if porch:
        lines.append(f"├ Возможный подъезд -> {porch}")
    if apartment:
        lines.append(f"├ Возможная квартира -> {apartment}")

    if lines:
        print("\n".join(lines))
    else:
        print("[+] Нет информации")

def geolocate_ip(ip):
    print(f"[+] Поиск по IP: {ip}")
    url = f"http://ip-api.com/json/{ip}?lang=ru"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['status'] == 'success':
            city = data.get('city')
            capital = False
            pretty_print({
                "city": city,
                "capital": capital,
            })
        else:
            print("[+] Не удалось получить данные по IP")
    except Exception as e:
        print(f"[!] Ошибка: {e}")
    input(Fore.CYAN + "[+] Нажмите [Enter] для возвращения в меню...")

def geolocate_address(address):
    print(f"[+] Поиск по адресу: {address}")
    url = "https://nominatim.openstreetmap.org/search"
    try:
        response = requests.get(url, params={
            "q": address,
            "format": "json",
            "addressdetails": 1,
            "limit": 1
        }, headers={"User-Agent": "GeoOsintTool"})
        results = response.json()
        if results:
            place = results[0]
            addr = place.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("village")
            street = addr.get("road")
            house_number = addr.get("house_number")
            building = addr.get("building") or addr.get("house") or addr.get("unit")

            porch = house_number if house_number else None
            apartment = building if building else None
            capital = is_capital_osm(addr)

            pretty_print({
                "city": city,
                "capital": capital,
                "street": street,
                "porch": porch,
                "apartment": apartment
            })
        else:
            print("[+] Адрес не найден")
    except Exception as e:
        print(f"[+] Ошибка: {e}")
    input(Fore.CYAN + "[+] Нажмите [Enter] для возвращения в меню...")

def search_intelx(query):
    print(f"[+] Поиск: {query}")
    if len(query) < 8:
        print("[!] Запрос слишком короткий")
        input(Fore.CYAN + "[+] Нажмите [Enter] для возвращения в меню...")
        return

    path = f"{query[:2]}/{query[2:4]}/{query[4:6]}/{query[6:8]}.csv"
    url = f"https://data.intelx.io/saverudata/db2/dbpn/{path}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print("[!] Не удалось получить данные")
            input(Fore.CYAN + "[+] Нажмите [Enter] для возвращения в меню...")
            return

        lines = response.text.split("\n")
        if not lines:
            print("[!] Пустой ответ.")
            input(Fore.CYAN + "[+] Нажмите [Enter] для возвращения в меню...")
            return

        headers = [h.strip().strip('"') for h in lines[0].split(",")]
        query_lower = query.lower()
        found_data = defaultdict(set)
        for line in lines[1:]:
            values = [v.strip().strip('"') for v in line.split(",")]
            if any(query_lower in v.lower() for v in values):
                for i, value in enumerate(values):
                    if value:
                        found_data[headers[i]].add(value)

        if found_data:
            for key, values in found_data.items():
                print(f"{key}: {', '.join(values)}")
            print()
        else:
            print("[+] Ничего не найдено")

    except Exception as e:
        print(f"[+] Ошибка  {e}")

    input(Fore.CYAN + "[+] Нажмите [Enter] для возвращения в меню...")

while True:
    os.system("cls" if os.name == "nt" else "clear")
    print(Fore.RED + ascii_art)
    print(Fore.RED + menu)
    choice = input(Fore.RED + "[+] Выберите функцию -> ")

    if choice == "1":
        query = input(Fore.RED + "[+] Введите информацию для пойска -> ").strip()
        search_intelx(query)
    elif choice == "2":
        query = input(Fore.RED + "[+] Напишите Улицу либо IP -> ").strip()
        if is_ip(query):
            geolocate_ip(query)
        else:
            geolocate_address(query)
    elif choice == "3":
        print(Fore.YELLOW + "[+] Выход...")
        break
    else:
        print(Fore.RED + "[+] Неверный выбор")
        input(Fore.CYAN + "[+] Нажмите [Enter] для возвращения в меню...")
