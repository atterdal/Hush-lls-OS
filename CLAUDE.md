# Hushålls-OS – Projektdokumentation

Detta dokument är överlämnings-kontext från en planeringsfas i Claude.ai till
Claude Code. Det innehåller mål, beslut, arkitektur och öppna frågor. Läs hela
dokumentet innan du föreslår förändringar i koden.

## Sammanhang

Användaren bor med två söner (7 och 10 år) som är hos honom 50 % av tiden, dock
inte alltid varannan vecka. Han bor i Habo. Han har en Home Assistant-server
och Docker-/Portainer-vana. Google Home-enheter i hemmet kör nu Gemini.

Projektets långsiktiga ambition är ett hushålls-OS som hanterar:

- Hushållsvaror (toapapper, deo, schampo, tandkräm) med förbrukningsstatistik
- Skafferi och färskvaror med inventering, utgångsdatum och frys-flagga
- Veckomatsedel som genereras söndagar utifrån erbjudanden, lager, schema barn
  och kostprofil (DASH för vuxna, enkel receptbank för barn)
- Två separata inköpslistor (ICA och Willys) med per-vara-prisjämförelse
- Hämtning i butik måndagar (inte hemleverans)
- Manuell ordergodkännande – användaren klickar beställ själv
- Bulkvaror via Amazon m.fl. (steg 2)

Den långsiktiga ambitionen är **inte** scope för MVP. Den finns dokumenterad
nedan eftersom arkitekturen ska tåla att utökas dit utan ombyggnad.

## Mätbara mål

Användaren har uttryckt tre konkreta mål för helheten:

1. Komma igång med att laga mat regelbundet
2. Mindre matsvinn (klassiska "rutten gurka i grönsakslådan"-fall)
3. Inget "fan, det är slut på tandkräm" på morgonen för barnen

Dessa mål är riktning, inte acceptanskriterier för MVP.

## MVP-scope (Steg 1)

**Story 1 är hela MVP:n:**

> Användaren står i köket och kommer på att riset är slut. Han säger
> "Ok Google, lägg till ris i inköpslistan". När han är på Willys nästa gång
> och kollar inköpslistan i Willys-appen ser han att han behöver köpa ris.

Inget annat ingår i MVP. Inte matplanering, inte recept, inte lager, inte
utgångsdatum, inte statistik, inte ICA, inte Amazon, inte söndagsbeställning.

Story 2 (söndagsbeställning från Willys hemsida) är dokumenterad som nästa
steg men ska inte påverka MVP-implementationen utöver att arkitekturen ska
tillåta det.

## Arkitekturprinciper

### Home Assistant är Single Source of Truth (SSoT)

Listan bor i HA. Allt annat är vyer eller speglar. Det är ett uttryckligt
designval för att:

- Input-källor (Google Home, Apple, fysiska knappar) ska vara utbytbara
- Output-mål (Willys, ICA, Amazon) ska vara utbytbara
- HA är ekosystemet redan finns hos användaren

### Synk är enkelriktad: HA → externa system

Från HA till Willys, ICA, Amazon. Inte tvärtom. Det förenklar designen rejält.
Det betyder att om användaren bockar av varor i Willys-appen efter att han
handlat behöver han också städa HA-listan – eller så bygger vi en
återflödes-mekanism senare. För MVP räcker enkelriktat.

### Frikopplad input och output

Användaren bygger Google Home → HA-integrationen själv. Claude Code ska
fokusera på HA → Willys. Det är medvetet uppdelat så att de två sidorna kan
utvecklas oberoende.

### Iterativ utveckling

Listan kan börja i HA och visas i HA-appen tills Willys-bryggan är på plats.
Det är ok att gå live med "halva flödet" först och bygga klart resten i lugn
och ro.

## Tekniska beslut

### Willys saknar officiellt publikt API

Verifierat via webbsökning. Två community-projekt har reverse-engineerat det
interna API:et och båda bekräftar att Willys kräver inloggning via headless
browser (Puppeteer) för att få session-cookies, sedan REST-anrop till interna
endpoints.

- [jimmystridh/willys-mcp](https://github.com/jimmystridh/willys-mcp) – TypeScript/Next.js, 19 MCP-tools, hobbyprojekt (0 stars vid undersökningstillfället, 4 commits)
- [effati-willys-mcp](https://lobehub.com/mcp/effati-willys-mcp) – likvärdigt mönster

Båda hanterar **kundvagn**, inte **inköpslista**. Det är en ouppklarad fråga
(se Öppna frågor nedan).

### Två arkitekturval för bryggan

**Variant A: HA custom_component**

En egen HA-integration (Python) i `custom_components/willys_shopping_list/`.
Pratar direkt med Willys interna API. HA's inbyggda `shopping_list_updated`-event
triggar att raden skickas vidare till Willys.

- Fördel: Allt i HA-ekosystemet, inget externt att underhålla
- Nackdel: Måste skrivas från scratch i Python

**Variant B: HA → MCP-broker via REST**

MCP-servern (jimmystridh's eller egen fork) körs som separat tjänst, t.ex. i
Docker. HA pratar med den via HTTP/REST när någon lägger till på listan.

- Fördel: Återanvänder befintlig kod
- Nackdel: Två system att hålla igång, MCP:n är hobbykod (0 stars)

**Inget val är gjort.** Variant A känns mer i linje med "HA är SSoT", men
Variant B går snabbare att få igång.

### Prejudikat: Alexa-integration

[madmachinations/home-assistant-alexa-shopping-list](https://github.com/madmachinations/home-assistant-alexa-shopping-list)
löser exakt samma problem för Amazons Alexa Shopping List efter att Amazon
stängde tredjepartsåtkomst sommaren 2024. Den använder Selenium för att
fjärrstyra en webbläsare. Denna repo bör läsas innan implementation av
Variant A – den visar mönstret för "HA-integration som synkar mot extern
lista via headless browser".

## Öppna frågor

### 1. Skiljer Willys interna API på inköpslista och kundvagn?

**Detta är den viktigaste obesvarade frågan.** De MCP:er som finns hanterar
kundvagn. Vi vet inte om inköpslistan är en separat resurs i deras backend.

**Hur du svarar på frågan:**

1. Logga in på willys.se i en webbläsare
2. Öppna devtools → Network-fliken
3. Lägg manuellt till en vara på inköpslistan i UI:t
4. Inspektera vilka API-anrop som faktiskt görs
5. Notera URL:er, HTTP-metoder, payload-strukturer

Resultatet styr hela arkitekturen. Om inköpslistan är en separat endpoint
behöver vi bygga stöd för den. Om det är samma backend som kundvagnen kanske
befintliga MCP:er räcker.

### 2. Bevarar Willys-appen butikssortering oavsett input-källa?

Användarens primära skäl till att vilja ha varorna i Willys-appen
(snarare än i Bring/Keep/HA) är att appen sorterar listan efter butikens
fysiska layout och kopplas ihop med scannern. Detta ska verifieras: läggs en
vara in via API, syns den då sorterad i appen?

Trolig som ja, men måste testas.

### 3. Skörhet och underhåll

Inofficiella API:er kan brytas. Användaren har inte explicit tagit ställning
till hur skör integrationen får vara. Anta tills vidare att 95 % uptime är ok
och att han löser de 5 % manuellt. Bygg gärna in graceful degradation:
om Willys-anropet failar, behåll varan på HA-listan och försök igen senare.

### 4. Två-vägs synk i framtiden

Om användaren bockar av en vara i Willys-appen efter handling, ska den då
också tas bort från HA-listan? För MVP nej. För framtid kanske. Designa
arkitekturen så att två-vägs är möjligt utan ombyggnad – t.ex. genom att
behålla en mappning mellan HA-list-items och Willys-list-items.

### 5. Produkt-mappning

När användaren säger "mjölk" till Google Home – vilken mjölk hamnar i Willys?
Tre nivåer av lösningar:

- Första träffen i sökresultatet (snabb, kan bli fel)
- Mappnings-fil ("mjölk" → specifik produktkod, byggs upp över tid)
- Manuell godkänning innan synk (för säkrast)

Detta är **inte ett MVP-problem** men kommer dyka upp omedelbart i
användning. Förbered datamodellen för att kunna lagra "favoritprodukt per
listpost" senare.

## Säkerhet

- Användarens Willys-credentials ska aldrig hardkodas. Använd HA's
  `secrets.yaml` eller config flow.
- För testning under utveckling: lägg credentials i en lokal `.credentials`-fil
  som är gitignore:ad. Aldrig commit:a credentials.
- Sessions från Willys headless-login går ut efter 24h. Bygg
  re-autentisering som tål detta.
- En tidigare credential-läcka inträffade i planeringschatten. Användaren har
  blivit påmind om att rotera lösenordet. Om han inte hunnit, påminn igen
  innan implementation börjar.

## Användarens befintliga miljö

Detta vet vi från konversationen:

- Home Assistant körs som HAOS på en Intel NUC
- Docker/Portainer-erfarenhet är ej bekräftad (felaktigt antaget i planeringsfasen)
- Tidigare har det funnits en server kallad "RickAusFrankfurt", men det är
  oklart om den fortfarande är aktuell. **Fråga användaren** innan du antar
  något om infrastrukturen.
- Google Home med Gemini i hemmet
- Han har redan satt upp HA's inventory-funktion men är öppen för att byta

## Receptbank (för framtid, inte MVP)

Användaren har specificerat att receptbanken ska vara minimal. Tre ingredienser
i typfallet. Exempel på rätter han faktiskt lagar för barnen:

- Hemlagad tomatsoppa (ersätter Kelda Mild Tomatsoppa)
- Köttbullar och spaghetti
- Köttbullar och stuvade makaroner
- Falukorv och stuvade makaroner (1 ring delas i 3, 2 fryses)
- Lax och ris
- Wok och ris

För egen del följer han DASH-kost. Receptens struktur:

- Ingredienser med mängd
- Kort tillagningsbeskrivning
- "Rätt-typ"-tagg (pasta, ris, soppa) för variations-logik
- Flagga: "kan halvfabrikat ersättas med hemmagjort?"

Detta är **dokumentation för framtida utveckling**, inte aktuell uppgift.

## Hårda regler för framtida matplanering

- **Edward (en av sönerna) är allergisk mot nötter.** Aldrig nötter, inte
  ens "kan innehålla spår av nötter".
- Aldrig samma rätt två gånger samma vecka
- Svenskt kött föredras där rimligt
- Inget budgettak – billigast vinner

Detta är inte aktuellt för MVP men ska respekteras när matplanering byggs.

## Tredjepartstjänster för pris- och erbjudandedata (för framtida steg)

Detta är **inte aktuellt för MVP** men dokumenterat för att inte glömmas
när Story 2 (söndagsbeställning med erbjudandedata) byggs.

### Matpriskollen

[matpriskollen.se](https://matpriskollen.se/) – svensk prisjämförelse-tjänst
med app som täcker Willys, ICA, Coop, City Gross med flera. Användaren har
specifikt påpekat att Matpriskollen har Willys Habo (butiks-ID 2321 i
Willys eget system, "Willys Habo Kärnekulla").

Funktioner relevanta för senare steg:

- Erbjudande-data per butik vecka för vecka
- Smart inköpslista som kan delas med familj
- Bevakning av enskilda produkter med notis vid extrapris
- Receptförslag länkade till erbjudanden (Arla Köket)

Det är okänt om Matpriskollen har ett publikt API. Det får undersökas när
det blir aktuellt.

### Matspar.se

[matspar.se](https://www.matspar.se/) – jämför totalpriset på en hel
inköpslista mellan ICA, Willys, Coop, Hemköp och Mathem. Användaren valde
att inte använda Matspar för MVP eftersom Matspar bara visar **online-priser
för hemleverans**, och användaren vill **hämta i butik**. Butikspriserna
kan skilja sig från online-priserna och Matspar fångar inte den skillnaden.

Skulle bli mer relevant om användaren senare ändrar strategi till
hemleverans, vilket är osannolikt men möjligt.

### ICAs reverse-engineerade API

[svendahlstrand/ica-api](https://github.com/svendahlstrand/ica-api) –
inofficiell dokumentation av ICAs interna API. Endpoint
`GET /api/offers?Stores={store-id}` ger erbjudanden per butik. Auth via
personnummer + lösenord från Buffé-utskick. Relevant för Story 2 om/när
ICA-integration ska byggas.

## Vad som inte ska byggas

För att göra scope-gränsen tydlig:

- ❌ Matplanering
- ❌ Recept
- ❌ Lager-tracking
- ❌ Utgångsdatum
- ❌ Förbrukningsstatistik
- ❌ ICA-integration
- ❌ Amazon-integration
- ❌ Hemleverans
- ❌ Erbjudande-skrapning
- ❌ Frys-kapacitetshantering
- ❌ Receptdatabas (Mealie/Tandoor)
- ❌ Söndagsbeställning till kundvagn (kommer som Story 2)

## Vad som ska byggas

✅ Brygga från HA inköpslista till Willys inköpslista, enkelriktad

Det är allt som ska finnas när MVP är klar.

## Föreslagen ordning för Claude Code

1. **Verifiera den öppna frågan om inköpslista vs kundvagn** (ovan, fråga 1).
   Detta är en blockerare innan implementation.
2. **Läs jimmystridh/willys-mcp i sin helhet** för att förstå auth-flödet
   och vilka endpoints som faktiskt anropas.
3. **Läs madmachinations/home-assistant-alexa-shopping-list** som mall för
   strukturen av en HA custom_component som synkar mot extern lista.
4. **Diskutera med användaren val mellan Variant A och B** baserat på vad
   du lärt dig i steg 1–3.
5. Implementera vald variant i en separat git-repo som user kan
   versionshantera.
6. Dokumentera underhållsförväntningar (hur märker man att Willys ändrat
   sitt API, hur återställer man).

## Påminnelser

- Detta är inte en blueprint som ska följas blint. Det är beslut och
  insikter från en planeringsfas. Ifrågasätt antaganden som inte håller.
- Användaren har varit tydlig med att han inte vill ha "spretiga" förslag.
  Håll dig till MVP-scopet. Spara framtida idéer till diskussion när MVP
  är på plats.
- Användaren är tekniskt kompetent men har inte oändligt med tid. Optimera
  för minsta möjliga underhållsbörda.
