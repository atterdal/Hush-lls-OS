# Willys Inköpsliste-API (Wishlist) – Reverse-Engineered

Dokumenterat 2026-05-08 genom att inspektera nätverkstrafik på willys.se.

## Grundläggande

- **Base URL:** `https://www.willys.se`
- **API-prefix:** `/axfood/rest/`
- **Backend:** SAP Hybris Commerce (Axfood)
- **Inköpslistan heter "wishlist" i API:t** – separat från kundvagnen (`/cart/`)

## Autentisering

1. Headless browser (Puppeteer/Playwright) öppnar `/anvandare/inloggning`
2. Fyller i `input[name="j_username"]` och `input[name="j_password"]`
3. Klickar "Logga in"
4. Extraherar session-cookies från browsern
5. Cookies används i alla efterföljande REST-anrop

Session-cookies är giltiga i ~24 timmar.

## CSRF-token

State-ändande anrop (POST) kräver en CSRF-token.

```
GET /axfood/rest/csrf-token
```

Returnerar en UUID-sträng. Skickas som header `x-csrf-token` i POST-anrop.

Vid 401 på POST: hämta ny CSRF-token och försök igen (detta är det observerade beteendet i frontend).

## Endpoints

### Lista alla listor

```
GET /axfood/rest/user-wishlist?basic=true&sorting=LAST_UPDATED_DESC
```

**Respons:**
```json
[
  {
    "id": "9649562004007",
    "name": "Att handla 16 mars 2026",
    "numberOfProducts": 1,
    "modifiedTime": "2026-05-08",
    "image": null,
    "sorting": null,
    "description": null
  }
]
```

### Hämta en lista

```
GET /axfood/rest/user-wishlist/{listId}
```

**Respons:**
```json
{
  "sharedUntil": null,
  "entries": [
    {
      "checkedOrder": null,
      "categoryName": "Hem & Städ",
      "entryType": "FREETEXT",
      "freeTextProduct": "toapapper",
      "checked": false,
      "salableInStore": false,
      "promotion": null,
      "product": null,
      "quantity": 1.0,
      "pickUnit": null
    },
    {
      "checkedOrder": null,
      "categoryName": "Skafferi",
      "entryType": "PRODUCT",
      "freeTextProduct": null,
      "checked": false,
      "salableInStore": true,
      "promotion": null,
      "product": {
        "productCode": "101488799_ST",
        "pickupProductLine2": "GARANT, 2kg",
        "priceNoUnit": "75,61"
      },
      "quantity": 1.0,
      "pickUnit": "pieces"
    }
  ]
}
```

### Lägg till vara (fritext)

```
POST /axfood/rest/user-wishlist/{listId}
Content-Type: application/json
x-csrf-token: {token}
```

**Payload:**
```json
{
  "entries": [
    {
      "entryType": "FREETEXT",
      "quantity": 1,
      "checked": false,
      "salableOnline": false,
      "freeTextProduct": "ris"
    }
  ]
}
```

### Lägg till vara (specifik produkt)

```
POST /axfood/rest/user-wishlist/{listId}
Content-Type: application/json
x-csrf-token: {token}
```

**Payload:**
```json
{
  "entries": [
    {
      "entryType": "PRODUCT",
      "quantity": 1,
      "checked": false,
      "salableOnline": true,
      "productCode": "101488799_ST",
      "pickUnit": "pieces"
    }
  ]
}
```

### Ta bort vara

Samma endpoint och payload som "lägg till", men med `"quantity": 0`.

**Fritext-borttagning:**
```json
{
  "entries": [
    {
      "entryType": "FREETEXT",
      "quantity": 0,
      "checked": false,
      "salableOnline": false,
      "freeTextProduct": "toapapper"
    }
  ]
}
```

**Produkt-borttagning:**
```json
{
  "entries": [
    {
      "entryType": "PRODUCT",
      "quantity": 0,
      "checked": false,
      "salableOnline": true,
      "productCode": "101488799_ST",
      "pickUnit": "pieces"
    }
  ]
}
```

## Observationer

- Sökning i inköpslistan sker client-side (inga API-anrop för sök i lista-kontexten)
- Willys kategoriserar automatiskt fritextvaror (t.ex. "toapapper" → "Hem & Städ")
- Varje lista har ett numeriskt ID (t.ex. `9649562004007`)
- `entries`-arrayen i POST kan troligen innehålla flera varor på en gång
- Vid 401 på POST hämtar frontenden automatiskt ny CSRF-token och gör retry

## Ej verifierat

- Skapa ny lista (endpoint okänd, troligen `POST /axfood/rest/user-wishlist`)
- Ta bort en hel lista
- Uppdatera listnamn
- Dela lista
- Hur `checked`-flaggan fungerar (bocka av varor)
- Om appen sorterar API-tillagda varor efter butikslayout
