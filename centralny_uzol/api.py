import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from influxdb import InfluxDBClient

# ── Cesty ─────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"

app = FastAPI(title="RPi Sensor API", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # lokálne nasadenie - všetky origins povolené
    allow_methods=["*"], 
    allow_headers=["*"],
)

# ── Pripojenie na InfluxDB v1 ─────────────────────────────────
client = InfluxDBClient(host='localhost', port=8086, database='smarthome')

# ── Globálna pamäť pre limity (Prednastavené hodnoty) ─────────
LIMITS = {
    "rpi_teplota": "20 - 28",
    "wio_teplota": "18 - 25",
    "rpi_vlhkost": "30 - 60",
    "wio_vlhkost": "30 - 60",
    "rpi_voc": "0 - 500"
}

def _read_from_influx() -> dict:
    result = {
        "temperature":  None,
        "humidity":     None,
        "dust_ug_m3":   None,
        "voc_ppm":      None,
        "limit_teplota": LIMITS.get("rpi_teplota", "20 - 28"),
        "limit_vlhkost": LIMITS.get("rpi_vlhkost", "30 - 60"),
        "limit_voc":     LIMITS.get("rpi_voc", "0 - 500"),    
        "timestamp":    int(time.time()),
    }

    try:
        # 1. Dotaz na Teplotu a Vlhkosť (iba z rpi_station)
        query_th = 'SELECT last("temperature") AS t, last("humidity") AS h FROM "temperature_humidity" WHERE "location"=\'rpi_station\''
        res_th = client.query(query_th)
        pts_th = list(res_th.get_points())
        
        if pts_th:
            val_t = pts_th[0].get('t')
            val_h = pts_th[0].get('h')
            result["temperature"] = round(val_t, 1) if val_t is not None else None
            result["humidity"]    = round(val_h, 1) if val_h is not None else None

        # 2. Dotaz na Kvalitu vzduchu
        query_air = 'SELECT last("dust_ug_m3") AS d, last("voc_ppm") AS v FROM "air_quality" WHERE "location"=\'rpi_station\''
        res_air = client.query(query_air)
        pts_air = list(res_air.get_points())
        
        if pts_air:
            val_d = pts_air[0].get('d')
            val_v = pts_air[0].get('v')
            result["dust_ug_m3"] = round(val_d, 1) if val_d is not None else None
            result["voc_ppm"]    = round(val_v, 0) if val_v is not None else None

    except Exception as e:
        print(f"[ERROR] Zlyhalo čítanie z InfluxDB: {e}")

    return result

# ══════════════════════════════════════════════════════════════
# API ENDPOINTY
# ══════════════════════════════════════════════════════════════

@app.get("/api/sensors")
async def get_sensors():
    """Aktuálne hodnoty z InfluxDB databázy (JSON)."""
    return _read_from_influx()

@app.post("/api/set_limit")
async def set_limit(request: Request):
    """Prijíma zmeny limitov z Node-REDu (z Telegramu)."""
    data = await request.json()
    key = data.get("key")     
    value = data.get("value") 
    if key and value:
        LIMITS[key] = value
    return {"status": "ok", "new_limits": LIMITS}

@app.get("/api/health")
async def health():
    """Stav API a kontrola spojenia s DB."""
    try:
        client.ping()
        return {"status": "ok", "database": "connected"}
    except:
        return {"status": "error", "database": "disconnected"}

# ── HTML stránky ───────────────────────────────────────────────

@app.get("/grafy.html", include_in_schema=False)
async def serve_grafy_html():
    return FileResponse(TEMPLATES_DIR / "grafy.html")

@app.get("/kiosk.html", include_in_schema=False)
async def serve_kiosk_html():
    return FileResponse(TEMPLATES_DIR / "kiosk.html")
