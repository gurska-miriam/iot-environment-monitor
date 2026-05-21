# Monitorovací systém kvality vnútorného prostredia v reálnom čase

## O projekte
Tento projekt je zameraný na návrh a implementáciu modulárneho monitorovacieho systému určeného na sledovanie kvality vnútorného prostredia (teplota, vlhkosť, kvalita vzduchu) v reálnom čase. Systém poskytuje užívateľovi nástroj pre správu domáceho prostredia s potenciálom nasadenia v inteligentných domácnostiach (Smart Home).

## Architektúra systému
Projekt využíva distribuovanú architektúru rozdelenú na aplikačnú, sieťovú a senzorovú vrstvu.

### Hardvérové komponenty
* **Centrálna jednotka (Raspberry Pi 5 (2GB RAM)):** Zabezpečuje zber dát zo senzora **DHT22** (teplota, vlhkosť) a senzora kvality vzduchu **MQ-135** (koncentrácia TVOC v ppm). Zároveň slúži ako hlavný server pre databázu, broker a API.
* **Bezdrôtový uzol (Wio Terminal):** Vzdialený uzol s **DHT11** a prachovým senzorom **Waveshare** (meranie pevných častíc PM v µg/m³), ktorý publikuje namerané hodnoty do siete prostredníctvom protokolu MQTT.

### Softvér
* **Riadiaca logika:** Node-RED (spracovanie tokov dát, smerovanie správ, obsluha Telegram rozhrania).
* **Komunikačný protokol:** MQTT (obojsmerná komunikácia medzi hardvérovými uzlami a Node-RED).
* **Ukladanie dát:** InfluxDB v1.x (časovo-orientovaná databáza pre trvalé uchovávanie dát).
* **Backend API:** FastAPI / Python (poskytovanie aktuálnych dát cez JSON a správa limitov).
* **Vizualizácia & Frontend:** Grafana (analytické dashboardy) + Vlastný webový frontend (**Kiosk** & **Dynamické grafy**).

---

## Funkcie systému

1. **Zber telemetrie v reálnom čase:** Automatické meranie, distribúcia a agregácia fyzikálnych veličín z viacerých lokalít v 10-sekundových intervaloch.
2. **Detekcia anomálií & Notifikácie:** Okamžité zasielanie výstražných správ na Telegram pri prekročení stanovených hodnôt teploty, vlhkosti, prašnosti a TVOC.
3. **Vzdialená konfigurácia:** Možnosť meniť a nastavovať varovné limity pre jednotlivé uzly priamo z prostredia chatu Telegram pomocou príkazu `/limit`.
4. **Matematický model komfortu:** Vyhodnocuje index komfortu v miestnosti (*Komfortné, Prijateľné, Nepríjemné*).
5. **Interaktívny Kiosk Dashboard:** Webové rozhranie optimalizované pre dotykový displej s hodinami, kalendárom, predpoveďou počasia (Open-Meteo API) a Grafana panelmi.

---

## Štruktúra repozitára

* `main.py` – Centrálny skript spustený na Raspberry Pi. Zabezpečuje čítanie dát z lokálnych senzorov, odber MQTT správ a zápis do InfluxDB.
* `api.py` – FastAPI backend aplikácia poskytujúca REST API endpointy (`/api/sensors`, `/api/set_limit`) pre distribúciu dát na frontend a synchronizáciu limitov s Node-RED.
* `mq135.py` – Matematicky nakalibrovaná obsluha senzora plynov MQ-135 s implementovanou nelineárnou teplotno-vlhkostnou korekciou pre výpočet koncentrácie PPM.
* `dht22.py` – Skript na čítanie hodnôt teploty a vlhkosti zo senzora DHT22 prostredníctvom knižnice CircuitPython.
* `kiosk.html` – Frontend rozhranie pre domáci kiosk obsahujúce hodiny, kalendár, predpoveď počasia a živé dáta.
* `grafy.html` – Webová stránka umožňujúca dynamické pridávanie, kombinovanie a časové filtrovanie historických grafov z Grafany.
* `flows.json` – Kompletný exportovaný tok (flow) pre platformu Node-RED obsahujúci spracovanie Telegram správ a kontrolu alarmov.
