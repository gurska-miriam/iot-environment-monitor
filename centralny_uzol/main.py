import os
import time
import dht22
import mq135
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt

# ── INFLUXDB NASTAVENIE ──
client_db = InfluxDBClient(
    host='localhost', port=8086,
    username=os.getenv('INFLUX_USER', 'pi'),
    password=os.getenv('INFLUX_PASSWORD'),
    database='smarthome'
)
INTERVAL_MERANIA = 10

# ── MQTT A LIMITY NASTAVENIE ──
# Predvolené limity pre RPi (môžu sa zmeniť cez Telegram)
limity = {
    "tMax": 30.0,
    "tMin": 15.0,
    "vocMax": 800.0 
}

# Pamäť pre najnovšie dáta z Wio Terminalu
wio_data = {
    "temperature": None,
    "humidity": None,
    "dust_ug_m3": None
}

# Zamedzenie spamu na Telegrame (upozornenie pošle len raz za 5 minút)
cas_posledneho_varovania = 0
INTERVAL_VAROVANIA = 300 

def on_connect(client, userdata, flags, rc):
    print("  [MQTT] Úspešne pripojené k brokerovi.")
    # Po pripojení začne počúvať na všetky limity pre rpi
    client.subscribe("uzol/rpi/limit/#")
    
    # Počúvanie na Wio senzory
    client.subscribe("uzol/wio/teplota")
    client.subscribe("uzol/wio/vlhkost")
    client.subscribe("uzol/wio/prach")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8")
    
    # Rozhodovanie, či ide o limit
    if "limit" in topic:
        print(f"\n  [MQTT PRIJATÉ] {topic} -> {payload}")
        velicina = topic.split("/")[-1]
        try:
            hodnota = float(payload.split(" ")[0]) 
            if velicina in limity:
                limity[velicina] = hodnota
                print(f"  [SYSTÉM] Limit pre {velicina} bol zmenený na {hodnota}\n")
        except ValueError:
            print("  [CHYBA] Neplatný formát limitu.")
            
    # Zachytávanie senzorických dát z Wia
    elif "uzol/wio/" in topic:
        try:
            hodnota = float(payload)
            if topic == "uzol/wio/teplota":
                wio_data["temperature"] = hodnota
            elif topic == "uzol/wio/vlhkost":
                wio_data["humidity"] = hodnota
            elif topic == "uzol/wio/prach":
                wio_data["dust_ug_m3"] = hodnota
        except ValueError:
            pass # Ignorujeme, ak neprišlo číslo

# Inicializácia MQTT klienta
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883, 60)
mqtt_client.loop_start() # Spustí počúvanie na pozadí, neblokuje náš zber dát

try:
    print("Spúšťam zber dát (Centrálny Logger pre RPi a Wio)...")
    print("=" * 50)
   
    while True:
        # ── 1. ČÍTANIE DÁT Z RASPBERRY PI ──
        temp, hum = dht22.meraj_dht22()
        
        if temp is not None and hum is not None:
            hodnota_voc, volt_voc = mq135.zmeraj_mq(teplota=temp, vlhkost=hum)
        else:
            hodnota_voc, volt_voc = mq135.zmeraj_mq()

        print(f"[{time.strftime('%H:%M:%S')}] Zmerané na RPi:")
        if temp is not None:
            print(f"  Klíma:  {temp:.1f}°C | {hum:.1f}%")
            mqtt_client.publish("uzol/rpi/teplota", round(temp, 1))
            mqtt_client.publish("uzol/rpi/vlhkost", round(hum, 1))
            
        if hodnota_voc > 0:
            print(f"  Vzduch: {hodnota_voc:.0f} voc_ppm | {volt_voc:.2f}V")
            mqtt_client.publish("uzol/rpi/voc", round(hodnota_voc, 0))

        # ── 2. KONTROLA LIMITOV A ODOSIELANIE VAROVANÍ (RPi) ──
        aktualny_cas = time.time()
        if (aktualny_cas - cas_posledneho_varovania) > INTERVAL_VAROVANIA:
            varovanie = None
            
            if temp is not None and temp > limity["tMax"]:
                varovanie = f"RPi ALERT: Teplota stúpla na {temp:.1f}°C! (Limit: {limity['tMax']}°C)"
            elif temp is not None and temp < limity["tMin"]:
                varovanie = f"RPi ALERT: Teplota klesla na {temp:.1f}°C! (Limit: {limity['tMin']}°C)"
            elif hodnota_voc > limity["vocMax"]:
                varovanie = f"RPi ALERT: Zlá kvalita vzduchu! TVOC: {hodnota_voc:.0f} (Limit: {limity['vocMax']})"
                
            if varovanie:
                mqtt_client.publish("uzol/rpi/upozornenie", varovanie)
                print(f"  >>> ODOSLANÉ MQTT VAROVANIE: {varovanie} <<<")
                cas_posledneho_varovania = aktualny_cas

        # ── 3. ZÁPIS DO DATABÁZY (RPi + Wio) ──
        json_data = []

        # --- Dáta z RPi ---
        if temp is not None and hum is not None:
            json_data.append({
                "measurement": "temperature_humidity",
                "tags": {"sensor": "DHT22", "location": "rpi_station"},
                "fields": {"temperature": float(round(temp, 1)), "humidity": float(round(hum, 1))}
            })

        air_fields = {}
        if hodnota_voc > 0:
            air_fields["voc_ppm"] = float(round(hodnota_voc, 0))
            air_fields["voc_voltage"] = float(round(volt_voc, 3))

        if air_fields:
            json_data.append({
                "measurement": "air_quality",
                "tags": {"location": "rpi_station"},
                "fields": air_fields
            })

        # --- Dáta z Wio Terminalu ---
        if wio_data["temperature"] is not None and wio_data["humidity"] is not None:
            json_data.append({
                "measurement": "temperature_humidity",
                "tags": {
                    "sensor": "DHT11",
                    "location": "wio_terminal"
                },
                "fields": {
                    "temperature": float(round(wio_data["temperature"], 1)),
                    "humidity": float(round(wio_data["humidity"], 1))
                }
            })

        if wio_data["dust_ug_m3"] is not None:
            json_data.append({
                "measurement": "air_quality",
                "tags": {
                    "sensor": "Waveshare",
                    "location": "wio_terminal"
                },
                "fields": {
                    "dust_ug_m3": float(round(wio_data["dust_ug_m3"], 1))
                }
            })

        # --- Samotný zápis do InfluxDB ---
        if json_data:
            try:
                client_db.write_points(json_data)
            except Exception as e:
                print(f"  >>> CHYBA ZÁPISU DO DB: {e} <<<")
        
        print("-" * 50)
        time.sleep(INTERVAL_MERANIA)

except KeyboardInterrupt:
    print("\nUkončujem program")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

