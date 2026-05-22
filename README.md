# Monitorovací systém kvality vnútorného prostredia v reálnom čase

Bakalárska práca — Miriam Gurská
Fakulta strojního inženýrství, Vysoké učení technické v Brně, 2026
Vedúci práce: Ing. Jan Turčínek, Ph.D.

---

## O projekte

Cieľom práce je návrh a implementácia modulárneho systému pre sledovanie kvality vnútorného prostredia v reálnom čase. Systém zabezpečuje zber, ukladanie a vizualizáciu fyzikálnych veličín — teploty, relatívnej vlhkosti, koncentrácie prchavých organických látok a prachových častíc — z viacerých miestností súčasne.

---

## Architektúra systému

Projekt využíva distribuovanú architektúru rozdelenú na senzorovú, sieťovú a aplikačnú vrstvu.

### Hardvérové komponenty

| Komponent | Úloha |
|-----------|-------|
| Raspberry Pi 5 (2 GB RAM) | Centrálna jednotka — zber dát, databáza, API, vizualizácia |
| Raspberry Pi Touch Display 2 | Lokálny dotykový displej pre kiosk rozhranie |
| Senzor DHT22 | Meranie teploty a relatívnej vlhkosti (pripojený na RPi) |
| Senzor MQ-135 | Meranie koncentrácie TVOC v ppm (pripojený na RPi) |
| AD prevodník MCP3208-BI/P | Prevod analógových signálov pre RPi |
| Wio Terminal (Seeed Studio) | Bezdrôtový vzdialený uzol |
| Senzor DHT11 | Meranie teploty a relatívnej vlhkosti (pripojený na Wio) |
| Senzor prachu Waveshare | Meranie pevných častíc PM v µg/m³ (pripojený na Wio) |

### Softvérový stack

| Technológia | Účel |
|-------------|------|
| Python 3 | Zber dát zo senzorov, zápis do databázy |
| FastAPI | REST API backend pre distribúciu dát na frontend |
| InfluxDB v1.x | Časovo-orientovaná databáza pre trvalé uchovávanie meraní |
| Mosquitto | MQTT broker pre komunikáciu medzi uzlami |
| Node-RED | Spracovanie dátových tokov, obsluha Telegram rozhrania |
| Grafana OSS | Analytické dashboardy a historické grafy |
| HTML / JavaScript | Vlastný webový frontend (kiosk a analytická obrazovka) |

---

## Funkcie systému

1. **Zber telemetrie v reálnom čase** — automatické meranie a agregácia fyzikálnych veličín z viacerých lokalít v 10-sekundových intervaloch.
2. **Detekcia anomálií a notifikácie** — zasielanie výstražných správ prostredníctvom služby Telegram pri prekročení používateľom definovaných limitných hodnôt.
3. **Vzdialená konfigurácia** — možnosť upravovať varovné limity pre jednotlivé uzly priamo z prostredia Telegram chatu príkazom `/limit`.
4. **Vyhodnotenie tepelného komfortu** — matematický model klasifikujúci aktuálny stav prostredia do kategórií podľa normy ISO 7730.
5. **Interaktívny kiosk dashboard** — webové rozhranie optimalizované pre dotykový displej s aktuálnymi hodnotami, grafmi, kalendárom a predpoveďou počasia.

---

## Štruktúra repozitára

```
iot-environment-monitor/
│
├── README.md
│
├── centralny_uzol/
│   ├── main.py               – Centrálny skript: čítanie senzorov, MQTT odber, zápis do InfluxDB
│   ├── api.py                – FastAPI backend: REST API endpointy a správa limitov
│   ├── mq135.py              – Obsluha senzora MQ-135 s teplotno-vlhkostnou korekciou
│   ├── dht22.py              – Čítanie teploty a vlhkosti zo senzora DHT22
│   │
│   └── web/
│       └── sablony/
│           ├── kiosk.html    – Frontend pre dotykový kiosk displej
│           └── grafy.html    – Webová stránka s dynamickými historickými grafmi
│
├── bezdrotovy_uzol/
│   └── wio_terminal/
│       └── wio_terminal.ino  – Kód pre Wio Terminal (DHT11 + senzor prachu)
│
└── node_red/
    └── flows.json            – Exportovaný tok pre Node-RED
```

---

## Požiadavky

### Hardvér
- Raspberry Pi 5 (2 GB RAM alebo viac)
- Raspberry Pi Touch Display 2
- Senzor DHT22
- Senzor plynu MQ-135
- Senzor prachu Waveshare
- AD prevodník MCP3208-BI/P
- Wio Terminal (Seeed Studio)

### Softvér
- Raspberry Pi OS Full (64-bit)
- Python 3.11 alebo novší
- Node-RED
- InfluxDB v1.x
- Grafana OSS
- Mosquitto MQTT Broker
- Arduino IDE (pre nahratie kódu do Wio Terminal)
- Telegram Bot (vytvorený prostredníctvom služby [@BotFather](https://t.me/BotFather))

---

## Konfigurácia pred nasadením

Pred spustením systému je nevyhnutné upraviť nasledujúce hodnoty v zdrojovom kóde.

### 1. `wio_terminal.ino` — prihlasovacie údaje k sieti
```cpp
const char* ssid         = "YOUR_WIFI_SSID";      // názov WiFi siete
const char* password     = "YOUR_WIFI_PASSWORD";   // heslo k WiFi sieti
const char* mqtt_server  = "YOUR_MQTT_SERVER_IP";  // IP adresa Raspberry Pi v lokálnej sieti
```

### 2. `node_red/flows.json` — Telegram Chat ID
Po importe súboru `flows.json` do prostredia Node-RED je potrebné vyhľadať všetky výskyty reťazca `YOUR_CHAT_ID` a nahradiť ich vlastným identifikátorom Telegram účtu. Chat ID je možné zistiť prostredníctvom bota.

### 3. `kiosk.html` a `grafy.html` — identifikátor Grafana dashboardu
V oboch súboroch je potrebné nahradiť zástupnú hodnotu skutočným identifikátorom dashboardu vytvoreného v Grafane:
```javascript
const baseUrl = "http://localhost:3000/d-solo/YOUR_DASHBOARD_ID/iot-monitoring";
```
Identifikátor dashboardu je súčasťou URL adresy po jeho otvorení v prostredí Grafana.

---

## Inštalácia a spustenie

### 1. Klonovanie repozitára
```bash
git clone https://github.com/YOUR_USERNAME/iot-environment-monitor.git
cd smart-home-monitor
```

### 2. Príprava virtuálneho prostredia (Python)
```bash
python -m venv venv
source venv/bin/activate        # Linux / Raspberry Pi OS
```

### 3. Inštalácia a spustenie služieb

**Mosquitto MQTT Broker:**
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

**InfluxDB v1.x:**
```bash
# Inštalácia podľa oficiálnej dokumentácie:
# https://docs.influxdata.com/influxdb/v1/introduction/install/
sudo systemctl enable influxdb
sudo systemctl start influxdb
```

**Vytvorenie databázy:**
```bash
influx
> CREATE DATABASE smarthome
> EXIT
```

**Grafana OSS:**
```bash
# Inštalácia podľa oficiálnej dokumentácie:
# https://grafana.com/docs/grafana/latest/setup-grafana/installation/
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

**Node-RED:**
```bash
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
sudo systemctl enable nodered
sudo systemctl start nodered
```
Po spustení je potrebné importovať súbor `node_red/flows.json` prostredníctvom editora Node-RED dostupného na adrese `http://localhost:1880`.

### 4. Spustenie hlavného skriptu a API
```bash
cd centralny_uzol
python main.py
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 5. Nahratie kódu do Wio Terminal
Súbor `bezdrotovy_uzol/wio_terminal/wio_terminal.ino` je potrebné otvoriť v prostredí Arduino IDE, doplniť prihlasovacie údaje podľa sekcie Konfigurácia a nahrať do zariadenia.

---

## Ovládanie prostredníctvom Telegram bota

| Príkaz | Príklad použitia | Popis |
|--------|-----------------|-------|
| `/stav <zariadenie>` | `/stav wio` | Vráti posledné namerané hodnoty zo zvoleného uzla a vyhodnotí úroveň tepelného komfortu |
| `/limit <zariadenie> <velicina> <od> <do>` | `/limit rpi teplota 20 28` | Vzdialene nastaví varovný rozsah pre zvolenú veličinu na danom uzle |
| `/pomoc` | `/pomoc` | Vypíše zoznam všetkých dostupných príkazov |

---

## Licencia

Tento projekt bol vypracovaný ako bakalárska práca.
Vysoké učení technické v Brně, Fakulta strojního inženýrství, Ústav automatizace a informatiky, 2026.
