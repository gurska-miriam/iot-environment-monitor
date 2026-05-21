import time
import board
import adafruit_dht

# DHT22 connected to GPIO4
dht_device = adafruit_dht.DHT22(board.D4)

def meraj_dht22():
    try:
        temp = dht_device.temperature
        hum = dht_device.humidity
        return temp, hum
    except RuntimeError:
        return None, None
    except Exception as error:
        return None, None
        
# --- testovanie
if __name__ == "__main__":
    import time
    print("Testujem DHT22...")
    while True:
        temp, hum = meraj_dht22()
        if temp is not None:
            print(f"Teplota: {temp:.1f} C | Vlhkost: {hum:.1f} %")
        else:
            print("Chyba citania, skusam znova...")
        time.sleep(2)

