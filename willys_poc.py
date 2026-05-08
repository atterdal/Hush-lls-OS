#!/usr/bin/env python3
"""
Proof-of-concept: Logga in på Willys och lägg till varor på inköpslistan.

Användning:
    1. Skapa .credentials med WILLYS_USERNAME och WILLYS_PASSWORD
    2. pip install playwright
    3. playwright install chromium
    4. python willys_poc.py

Första körningen loggar in via headless browser och sparar cookies.
Efterföljande körningar återanvänder sparade cookies (giltiga ~24h).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

COOKIE_FILE = Path(__file__).parent / "playwright-state" / "cookies.json"
CREDENTIALS_FILE = Path(__file__).parent / ".credentials"
BASE_URL = "https://www.willys.se"


def load_credentials() -> tuple[str, str]:
    if not CREDENTIALS_FILE.exists():
        print(f"Saknar {CREDENTIALS_FILE}")
        print(f"Skapa filen med innehåll:")
        print(f"  WILLYS_USERNAME=din@email.se")
        print(f"  WILLYS_PASSWORD=ditt-lösenord")
        sys.exit(1)

    creds = {}
    for line in CREDENTIALS_FILE.read_text().strip().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            creds[key.strip()] = value.strip()

    email = creds.get("WILLYS_USERNAME", "")
    password = creds.get("WILLYS_PASSWORD", "")
    if not email or not password:
        print("WILLYS_USERNAME och WILLYS_PASSWORD måste finnas i .credentials")
        sys.exit(1)
    return email, password


def login_and_save_cookies(email: str, password: str) -> list[dict]:
    from playwright.sync_api import sync_playwright

    print("Startar headless browser för inloggning...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        page.goto(f"{BASE_URL}/anvandare/inloggning", wait_until="networkidle")
        time.sleep(2)

        # Hantera cookie-consent
        try:
            consent = page.locator("#onetrust-accept-btn-handler")
            if consent.is_visible(timeout=3000):
                consent.click()
                time.sleep(1)
        except Exception:
            pass

        # Klicka "Lösenord"-fliken (Willys har flikar: BankID / Lösenord)
        try:
            pwd_tab = page.locator("button:has-text('Lösenord')")
            if pwd_tab.is_visible(timeout=2000):
                pwd_tab.click()
                time.sleep(1)
        except Exception:
            pass

        # Fyll i inloggning
        page.locator('input[name="j_username"]').fill(email)
        page.locator('input[name="j_password"]').fill(password)
        time.sleep(1)

        # Klicka login och fånga nätverksresponsen
        with page.expect_response(
            lambda r: "login" in r.url or "authenticate" in r.url or "j_spring" in r.url,
            timeout=15000,
        ) as response_info:
            page.locator('button:has-text("Logga in")').click()

        login_resp = response_info.value
        print(f"Login response: {login_resp.status} {login_resp.url}")

        time.sleep(3)
        page.screenshot(path="poc_debug_after_login.png")
        print(f"URL efter login: {page.url}")

        # Verifiera inloggning
        response = page.request.get(f"{BASE_URL}/axfood/rest/customer")
        if response.status != 200:
            print(f"Inloggning misslyckades (status {response.status})")
            browser.close()
            sys.exit(1)

        customer = response.json()
        first_name = customer.get("firstName", "anonymous")
        if first_name == "anonymous":
            print("Inloggning misslyckades – fortfarande anonymous")
            print("Kontrollera credentials i .credentials")
            browser.close()
            sys.exit(1)

        print(f"Inloggad som: {first_name} {customer.get('lastName', '?')}")

        # Spara cookies
        cookies = context.cookies()
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"Cookies sparade i {COOKIE_FILE}")

        browser.close()
        return cookies


def load_cookies() -> Optional[list[dict]]:
    if not COOKIE_FILE.exists():
        return None

    cookies = json.loads(COOKIE_FILE.read_text())

    # Kolla om cookies har gått ut (enkel check på ålder)
    file_age_hours = (time.time() - COOKIE_FILE.stat().st_mtime) / 3600
    if file_age_hours > 20:
        print("Sparade cookies är äldre än 20h, loggar in igen...")
        return None

    return cookies


def make_session(cookies: list[dict]):
    import requests

    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain", ".willys.se"),
            path=cookie.get("path", "/"),
        )
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return session


def get_csrf_token(session) -> str:
    resp = session.get(f"{BASE_URL}/axfood/rest/csrf-token")
    resp.raise_for_status()
    token = resp.text.strip().strip('"')
    return token


def list_wishlists(session) -> list[dict]:
    resp = session.get(
        f"{BASE_URL}/axfood/rest/user-wishlist",
        params={"basic": "true", "sorting": "LAST_UPDATED_DESC"},
    )
    resp.raise_for_status()
    return resp.json()


def get_wishlist(session, list_id: str) -> dict:
    resp = session.get(f"{BASE_URL}/axfood/rest/user-wishlist/{list_id}")
    resp.raise_for_status()
    return resp.json()


def add_freetext_item(session, list_id: str, item_name: str, quantity: int = 1) -> bool:
    csrf = get_csrf_token(session)

    payload = {
        "entries": [
            {
                "entryType": "FREETEXT",
                "quantity": quantity,
                "checked": False,
                "salableOnline": False,
                "freeTextProduct": item_name,
            }
        ]
    }

    resp = session.post(
        f"{BASE_URL}/axfood/rest/user-wishlist/{list_id}",
        json=payload,
        headers={"x-csrf-token": csrf},
    )

    if resp.status_code == 401:
        # Retry med ny CSRF-token
        csrf = get_csrf_token(session)
        resp = session.post(
            f"{BASE_URL}/axfood/rest/user-wishlist/{list_id}",
            json=payload,
            headers={"x-csrf-token": csrf},
        )

    if resp.status_code == 200:
        print(f"  ✓ '{item_name}' tillagd på listan")
        return True
    else:
        print(f"  ✗ Misslyckades lägga till '{item_name}' (status {resp.status_code})")
        print(f"    {resp.text[:200]}")
        return False


def remove_freetext_item(session, list_id: str, item_name: str) -> bool:
    csrf = get_csrf_token(session)

    payload = {
        "entries": [
            {
                "entryType": "FREETEXT",
                "quantity": 0,
                "checked": False,
                "salableOnline": False,
                "freeTextProduct": item_name,
            }
        ]
    }

    resp = session.post(
        f"{BASE_URL}/axfood/rest/user-wishlist/{list_id}",
        json=payload,
        headers={"x-csrf-token": csrf},
    )

    if resp.status_code == 200:
        print(f"  ✓ '{item_name}' borttagen från listan")
        return True
    else:
        print(f"  ✗ Misslyckades ta bort '{item_name}' (status {resp.status_code})")
        return False


def main():
    print("=== Willys Inköpslista PoC ===\n")

    # 1. Cookies (logga in om nödvändigt)
    cookies = load_cookies()
    if cookies is None:
        email, password = load_credentials()
        cookies = login_and_save_cookies(email, password)

    session = make_session(cookies)

    # 2. Verifiera att sessionen fungerar
    print("\nHämtar listor...")
    try:
        wishlists = list_wishlists(session)
    except Exception:
        print("Sparade cookies fungerar inte, loggar in igen...")
        email, password = load_credentials()
        cookies = login_and_save_cookies(email, password)
        session = make_session(cookies)
        wishlists = list_wishlists(session)

    if not wishlists:
        print("Inga inköpslistor hittades!")
        sys.exit(1)

    print(f"Hittade {len(wishlists)} listor:")
    for wl in wishlists:
        print(f"  - {wl['name']} ({wl['numberOfProducts']} varor) [id: {wl['id']}]")

    # 3. Använd första listan
    target_list = wishlists[0]
    list_id = target_list["id"]
    print(f"\nAnvänder lista: {target_list['name']}")

    # 4. Visa nuvarande innehåll
    details = get_wishlist(session, list_id)
    print(f"Nuvarande varor ({len(details['entries'])}):")
    for entry in details["entries"]:
        name = entry.get("freeTextProduct") or entry.get("product", {}).get("name", "?")
        print(f"  - {name} ({entry['entryType']}, {entry['quantity']} st)")

    # 5. Lägg till en testvara
    test_item = "TEST-ris-poc"
    print(f"\nLägger till testvara: '{test_item}'...")
    if add_freetext_item(session, list_id, test_item):
        print("\n→ Kolla din Willys-app nu! Varan ska synas på listan.")
        print("Tar bort testvaran om 30 sekunder...")
        time.sleep(30)
        remove_freetext_item(session, list_id, test_item)
        print("Klart!")
    else:
        print("\nKunde inte lägga till vara. Kolla credentials och försök igen.")


if __name__ == "__main__":
    main()
