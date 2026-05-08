#!/usr/bin/env python3
"""
Willys Shopping List Sync – HA Add-on

Lyssnar på Home Assistants inköpslista via Supervisor API.
Nya varor synkas till Willys inköpslista som fritext.
Enkelriktad: HA → Willys.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

WILLYS_BASE = "https://www.willys.se"
COOKIE_FILE = Path(os.environ.get("COOKIE_DIR", "/share/willys")) / "cookies.json"

log = logging.getLogger("willys-sync")


# ---------------------------------------------------------------------------
# Willys API
# ---------------------------------------------------------------------------

class WillysClient:
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def ensure_authenticated(self) -> bool:
        if self._load_cookies():
            if self._is_logged_in():
                return True
            log.info("Sparade cookies ogiltiga, loggar in igen...")

        return self._login()

    def _is_logged_in(self) -> bool:
        try:
            resp = self._session.get(f"{WILLYS_BASE}/axfood/rest/customer", timeout=10)
            if resp.status_code != 200:
                return False
            data = resp.json()
            return data.get("firstName", "anonymous") != "anonymous"
        except Exception:
            return False

    def _load_cookies(self) -> bool:
        if not COOKIE_FILE.exists():
            return False

        age_hours = (time.time() - COOKIE_FILE.stat().st_mtime) / 3600
        if age_hours > 20:
            log.info("Cookies äldre än 20h, loggar in igen...")
            return False

        try:
            cookies = json.loads(COOKIE_FILE.read_text())
            for c in cookies:
                self._session.cookies.set(
                    c["name"], c["value"],
                    domain=c.get("domain", ".willys.se"),
                    path=c.get("path", "/"),
                )
            return True
        except Exception as e:
            log.warning("Kunde inte läsa cookies: %s", e)
            return False

    def _login(self) -> bool:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            log.error("Selenium ej installerat")
            return False

        log.info("Loggar in på Willys via headless browser...")
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1280,800")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        opts.binary_location = os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium-browser")

        driver = None
        try:
            service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
            driver = webdriver.Chrome(service=service, options=opts)
            wait = WebDriverWait(driver, 10)

            driver.get(f"{WILLYS_BASE}/anvandare/inloggning")
            time.sleep(3)

            # Cookie-consent
            try:
                consent = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                consent.click()
                time.sleep(1)
            except Exception:
                pass

            # Klicka "Lösenord"-fliken
            try:
                pwd_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Lösenord')]")))
                pwd_tab.click()
                time.sleep(1)
            except Exception:
                pass

            # Fyll i och logga in
            user_field = wait.until(EC.presence_of_element_located((By.NAME, "j_username")))
            pass_field = driver.find_element(By.NAME, "j_password")
            user_field.clear()
            user_field.send_keys(self._username)
            pass_field.clear()
            pass_field.send_keys(self._password)
            time.sleep(1)

            login_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Logga in')]")
            login_btn.click()
            time.sleep(5)

            # Hämta cookies
            selenium_cookies = driver.get_cookies()
            driver.quit()
            driver = None

            # Konvertera och spara
            cookies = []
            self._session.cookies.clear()
            for c in selenium_cookies:
                cookies.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".willys.se"),
                    "path": c.get("path", "/"),
                })
                self._session.cookies.set(
                    c["name"], c["value"],
                    domain=c.get("domain", ".willys.se"),
                    path=c.get("path", "/"),
                )

            COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
            COOKIE_FILE.write_text(json.dumps(cookies))

            # Verifiera
            if not self._is_logged_in():
                log.error("Inloggning misslyckades – kontrollera credentials")
                return False

            resp = self._session.get(f"{WILLYS_BASE}/axfood/rest/customer", timeout=10)
            customer = resp.json()
            log.info("Inloggad som %s %s", customer.get("firstName", "?"), customer.get("lastName", "?"))
            return True

        except Exception as e:
            log.error("Login-fel: %s", e)
            return False
        finally:
            if driver:
                driver.quit()

    def _get_csrf_token(self) -> str:
        resp = self._session.get(f"{WILLYS_BASE}/axfood/rest/csrf-token", timeout=10)
        resp.raise_for_status()
        return resp.text.strip().strip('"')

    def list_wishlists(self) -> list[dict]:
        resp = self._session.get(
            f"{WILLYS_BASE}/axfood/rest/user-wishlist",
            params={"basic": "true", "sorting": "LAST_UPDATED_DESC"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_wishlist(self, list_id: str) -> dict:
        resp = self._session.get(
            f"{WILLYS_BASE}/axfood/rest/user-wishlist/{list_id}",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def add_freetext_item(self, list_id: str, item_name: str, qty: int = 1) -> bool:
        csrf = self._get_csrf_token()
        payload = {
            "entries": [{
                "entryType": "FREETEXT",
                "quantity": qty,
                "checked": False,
                "salableOnline": False,
                "freeTextProduct": item_name,
            }]
        }
        resp = self._session.post(
            f"{WILLYS_BASE}/axfood/rest/user-wishlist/{list_id}",
            json=payload,
            headers={"x-csrf-token": csrf},
            timeout=10,
        )
        if resp.status_code == 401:
            csrf = self._get_csrf_token()
            resp = self._session.post(
                f"{WILLYS_BASE}/axfood/rest/user-wishlist/{list_id}",
                json=payload,
                headers={"x-csrf-token": csrf},
                timeout=10,
            )
        if resp.status_code == 200:
            log.info("Tillagd på Willys: '%s'", item_name)
            return True
        log.error("Kunde inte lägga till '%s' (status %s)", item_name, resp.status_code)
        return False


# ---------------------------------------------------------------------------
# Home Assistant API
# ---------------------------------------------------------------------------

class HAClient:
    def __init__(self, url: str, token: str):
        self._url = url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get_shopping_list(self) -> list[dict]:
        resp = requests.get(
            f"{self._url}/api/shopping_list",
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Sync loop
# ---------------------------------------------------------------------------

def sync_once(ha: HAClient, willys: WillysClient, list_id: str, synced: set) -> set:
    ha_items = ha.get_shopping_list()
    new_synced = set()

    for item in ha_items:
        if item.get("complete", False):
            continue

        name = item.get("name", "").strip()
        item_id = item.get("id", "")
        if not name:
            continue

        new_synced.add(item_id)

        if item_id in synced:
            continue

        log.info("Ny vara i HA: '%s' → synkar till Willys", name)
        if not willys.ensure_authenticated():
            log.error("Kan inte autentisera mot Willys, hoppar över")
            break

        willys.add_freetext_item(list_id, name)

    return new_synced


def resolve_list_id(willys: WillysClient, configured_id: str) -> str:
    if configured_id:
        return configured_id

    wishlists = willys.list_wishlists()
    if not wishlists:
        log.error("Inga inköpslistor hittades på Willys-kontot")
        sys.exit(1)

    chosen = wishlists[0]
    log.info("Ingen list-ID konfigurerad, använder '%s' (id: %s)", chosen["name"], chosen["id"])
    return chosen["id"]


def main():
    level = getattr(logging, os.environ.get("LOG_LEVEL", "info").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    username = os.environ.get("WILLYS_USERNAME", "")
    password = os.environ.get("WILLYS_PASSWORD", "")
    if not username or not password:
        log.error("WILLYS_USERNAME och WILLYS_PASSWORD måste vara satta")
        sys.exit(1)

    ha_token = os.environ.get("HA_TOKEN", "")
    ha_url = os.environ.get("HA_URL", "http://supervisor/core")
    if not ha_token:
        log.error("HA_TOKEN (SUPERVISOR_TOKEN) saknas")
        sys.exit(1)

    interval = int(os.environ.get("SYNC_INTERVAL", "30"))
    configured_list_id = os.environ.get("WILLYS_LIST_ID", "")

    willys = WillysClient(username, password)
    ha = HAClient(ha_url, ha_token)

    log.info("Autentiserar mot Willys...")
    if not willys.ensure_authenticated():
        log.error("Kunde inte logga in på Willys – kontrollera credentials")
        sys.exit(1)

    list_id = resolve_list_id(willys, configured_list_id)
    log.info("Synkar till Willys-lista: %s", list_id)

    # Hämta initialt state så vi inte synkar existerande varor
    log.info("Hämtar nuvarande HA-lista...")
    synced = set()
    try:
        ha_items = ha.get_shopping_list()
        for item in ha_items:
            if not item.get("complete", False):
                synced.add(item.get("id", ""))
        log.info("Ignorerar %d befintliga varor", len(synced))
    except Exception as e:
        log.warning("Kunde inte hämta HA-lista: %s", e)

    log.info("Startad! Pollar var %ds...", interval)
    while True:
        try:
            synced = sync_once(ha, willys, list_id, synced)
        except Exception as e:
            log.error("Sync-fel: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    main()
