# Willys Shopping List Sync

Home Assistant Add-on som synkar din HA-inköpslista till Willys inköpslista.

## Hur det fungerar

1. Du lägger till varor på HA:s inköpslista (t.ex. via Google Home: "Lägg till ris i inköpslistan")
2. Add-on:et pollar HA:s lista och synkar nya varor till din Willys-inköpslista
3. Varorna dyker upp i Willys-appen, sorterade efter butikslayout

Synken är **enkelriktad** (HA → Willys).

## Installation

1. Lägg till detta repo som custom repository i HA:
   - Gå till **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
   - Klistra in repo-URL:en
2. Installera "Willys Shopping List Sync"
3. Konfigurera med ditt Willys Plus-nummer och lösenord
4. Starta add-on:et

## Konfiguration

| Fält | Beskrivning |
|------|-------------|
| `willys_username` | Personnummer eller Willys Plus-nummer |
| `willys_password` | Ditt Willys-lösenord |
| `willys_list_id` | (Valfritt) ID för specifik lista. Lämna tomt för att använda senast uppdaterade |
| `sync_interval_seconds` | Pollnings-intervall i sekunder (default: 30) |
| `log_level` | Loggnivå: debug, info, warning, error |
