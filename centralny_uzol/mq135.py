from gpiozero import MCP3208
import math

adc = MCP3208(channel = 0)
RLOAD = 1.0
RZERO = 3.1     # Kalibrovaná hodnota odporu pre čistý vzduch

# Upravené parametre logaritmickej krivky pre ppm
PARA_A = 116.60
PARA_B = -2.769

def zmeraj_mq(teplota = None, vlhkost = None):
    percento = adc.value    # od 0.0 do 1.0
    napatie = percento * 3.3
    
    v_out = napatie / 0.6   # skutocne napatie zo senzora
    
    # Ochrana proti chybným hodnotám
    if v_out <= 0.01 or v_out >= 4.99:
        return 0, napatie
        
    rs = ((5.0 - v_out) / v_out) * RLOAD   # akt. el. odpor
    
    # uprava ak vieme aktualnu teplotu a vlhkost v miestnosti
    korekcia = 1.0
    if teplota is not None and vlhkost is not None:
        korekcia = (0.0003 * teplota * teplota) - (0.017 * teplota) + (0.002 * vlhkost) + 1.25  
        
    rs_korigovane = rs / korekcia
    
    # ppm (koncentrácia)
    if rs_korigovane <= 0: 
        return 0, napatie
        
    ratio = rs_korigovane / RZERO
    ppm = PARA_A * pow(ratio, PARA_B)
    
    return ppm, napatie
    
# --- testovanie
if __name__ == "__main__":
    import time
    print("Testujem MQ-135...")
    while True:
        hodnota, volt = zmeraj_mq()
        print(f"Napatie: {volt:.2f} V | Koncentracia: {hodnota:.0f} ppm")
        time.sleep(1)
