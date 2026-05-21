#include <TFT_eSPI.h>
#include "DHT.h"
#include <rpcWiFi.h>
#include <PubSubClient.h>

#define DHTPIN D1      
#define DHTTYPE DHT11 

// --- PINY PRE SENZOR PRACHU ---
#define PIN_AOUT A0
#define PIN_ILED D6

// --- DOPLŇ SVOJE ÚDAJE SEM ---
const char* ssid = "YOUR_WIFI_SSID";       
const char* password = "YOUR_WIFI_PASSWORD";   
const char* mqtt_server = "YOUR_MQTT_SERVER_IP"; 

DHT dht(DHTPIN, DHTTYPE);
TFT_eSPI tft;
WiFiClient wioClient;
PubSubClient client(wioClient);

// --- ČASOVAČE ---
unsigned long posledneMeranie = 0;
unsigned long poslednyPokusMQTT = 0; 

// --- STAV OBRAZOVKY A POSLEDNÉ HODNOTY ---
int aktualnaObrazovka = 0; // 0 = Teplota a Vlhkosť, 1 = Prach
float lastT = 0.0;
float lastH = 0.0;
float lastP = 0.0;
bool chybaDHT = false;

// --- ROZŠÍRENÉ LIMITOVÉ PREMENNÉ ---
float tMin = 20.0, tMax = 28.0;
float hMin = 30.0, hMax = 60.0;
float pMax = 150.0; 

// --- SAMOSTATNÉ ALARMY ---
bool alarmTeplota = false;
bool alarmVlhkost = false;
bool alarmPrach = false;

// --- FUNKCIA: Vykreslenie obrazovky 0 (Teplota/Vlhkosť) ---
void vykresliObrazovkuDHT(bool alarmT, bool alarmH) {
  uint16_t bgT = alarmT ? TFT_RED : TFT_BLACK;
  uint16_t fgT = alarmT ? TFT_WHITE : TFT_LIGHTGREY;
  
  uint16_t bgH = alarmH ? TFT_RED : TFT_BLACK;
  uint16_t fgH = alarmH ? TFT_WHITE : TFT_LIGHTGREY;
  
  tft.fillRect(0, 0, 160, 240, bgT);    
  tft.fillRect(160, 0, 160, 240, bgH);  
  tft.drawLine(160, 20, 160, 220, TFT_LIGHTGREY); 
  
  tft.setTextColor(fgT, bgT);
  tft.drawCentreString("Teplota (`C)", 80, 140, 4);
  tft.setTextColor(fgH, bgH);
  tft.drawCentreString("Vlhkost (%)", 240, 140, 4);
  
  tft.setTextColor(TFT_YELLOW, bgT);
  tft.drawCentreString(String(tMin, 1) + " - " + String(tMax, 1), 80, 180, 4);
  
  tft.setTextColor(TFT_YELLOW, bgH);
  tft.drawCentreString(String(hMin, 0) + " - " + String(hMax, 0), 240, 180, 4);
}

// --- FUNKCIA: Vykreslenie obrazovky 1 (Prach) ---
void vykresliObrazovkuPrach(bool alarmP) {
  uint16_t bgP = alarmP ? TFT_RED : TFT_BLACK;
  uint16_t fgP = alarmP ? TFT_WHITE : TFT_LIGHTGREY;
  
  tft.fillRect(0, 0, 320, 240, bgP); 
  
  tft.setTextColor(fgP, bgP);
  tft.drawCentreString("Prachove castice", 160, 140, 4);
  tft.drawCentreString("(ug/m3)", 160, 170, 4);
  
  tft.setTextColor(TFT_YELLOW, bgP);
  tft.drawCentreString("Max: " + String(pMax, 0), 160, 200, 4);
}

// --- FUNKCIA: Okamžité vykreslenie čísel na displej ---
void aktualizujCislaNaDispleji() {
  if (aktualnaObrazovka == 0) {
    tft.setTextColor(TFT_WHITE, alarmTeplota ? TFT_RED : TFT_BLACK);
    if (chybaDHT) tft.drawCentreString("Err  ", 80, 60, 6);
    else tft.drawCentreString(String(lastT, 1) + "  ", 80, 60, 6); 
    
    tft.setTextColor(TFT_WHITE, alarmVlhkost ? TFT_RED : TFT_BLACK);
    if (chybaDHT) tft.drawCentreString("Err  ", 240, 60, 6);
    else tft.drawCentreString(String(lastH, 1) + "  ", 240, 60, 6);
  } else {
    tft.setTextColor(TFT_WHITE, alarmPrach ? TFT_RED : TFT_BLACK);
    tft.drawCentreString(String(lastP, 1) + "  ", 160, 60, 7); 
  }
}

// --- SPRACOVANIE A OCHRANA LIMITOV Z MQTT ---
void prijataSprava(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) msg += (char)payload[i];
  String t = String(topic);

  int medzeraIndex = msg.indexOf(' ');

  if (t == "uzol/wio/limit/teplota" && medzeraIndex > 0) {
    tMin = msg.substring(0, medzeraIndex).toFloat();
    tMax = msg.substring(medzeraIndex + 1).toFloat();
  }
  else if (t == "uzol/wio/limit/vlhkost" && medzeraIndex > 0) {
    hMin = constrain(msg.substring(0, medzeraIndex).toFloat(), 0.0, 100.0);
    hMax = constrain(msg.substring(medzeraIndex + 1).toFloat(), 0.0, 100.0);
  }
  else if (t == "uzol/wio/limit/prach") {
    pMax = msg.toFloat();
    if (pMax < 0.0) pMax = 0.0;
  }
  else if (t == "uzol/wio/limit/tMin") tMin = msg.toFloat();
  else if (t == "uzol/wio/limit/tMax") tMax = msg.toFloat();
  else if (t == "uzol/wio/limit/hMin") hMin = constrain(msg.toFloat(), 0.0, 100.0);
  else if (t == "uzol/wio/limit/hMax") hMax = constrain(msg.toFloat(), 0.0, 100.0);
  else if (t == "uzol/wio/limit/pMax") {
    pMax = msg.toFloat();
    if (pMax < 0.0) pMax = 0.0;
  }

  // Po prijatí limitu ihneď prekreslíme pozadie a čísla s novými limitmi
  if (aktualnaObrazovka == 0) vykresliObrazovkuDHT(alarmTeplota, alarmVlhkost);
  else vykresliObrazovkuPrach(alarmPrach);
  aktualizujCislaNaDispleji();
}

void setup() {
  Serial.begin(115200);
  
  pinMode(LCD_BACKLIGHT, OUTPUT);
  digitalWrite(LCD_BACKLIGHT, HIGH);
  
  pinMode(WIO_5S_LEFT, INPUT_PULLUP);
  pinMode(WIO_5S_RIGHT, INPUT_PULLUP);
  
  // Inicializácia senzora prachu
  pinMode(PIN_ILED, OUTPUT);
  digitalWrite(PIN_ILED, LOW);
  pinMode(PIN_AOUT, INPUT);
  analogReadResolution(12);

  dht.begin();
  tft.begin();
  tft.setRotation(3);
  vykresliObrazovkuDHT(false, false);

  Serial.println("\n--- START WIO TERMINAL ---");
  Serial.print("Pripajam sa k WiFi: ");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print("."); 
  }
  Serial.println("\nWiFi pripojene!");
  
  client.setServer(mqtt_server, 1883);
  client.setCallback(prijataSprava);
}

void loop() {
  // --- 1. NEBLOKUJÚCE PRIPÁJANIE K WIFI A MQTT ---
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - poslednyPokusMQTT > 5000) {
      poslednyPokusMQTT = millis();
      WiFi.disconnect();
      WiFi.begin(ssid, password);
    }
  } else if (!client.connected()) {
    if (millis() - poslednyPokusMQTT > 5000) { 
      poslednyPokusMQTT = millis();
      String clientId = "WioTerminal-" + String(random(0xffff), HEX);
      if (client.connect(clientId.c_str())) {
        client.subscribe("uzol/wio/limit/#"); 
      } 
    }
  }
  
  if (client.connected()) {
    client.loop();
  }

  // --- 2. KONTROLA TLAČIDLA (Prepínanie obrazoviek) ---
  if (digitalRead(WIO_5S_LEFT) == LOW || digitalRead(WIO_5S_RIGHT) == LOW) {
    aktualnaObrazovka = (aktualnaObrazovka == 0) ? 1 : 0;
    
    tft.fillScreen(TFT_BLACK);
    if (aktualnaObrazovka == 0) vykresliObrazovkuDHT(alarmTeplota, alarmVlhkost);
    else vykresliObrazovkuPrach(alarmPrach);
    
    aktualizujCislaNaDispleji(); 
    
    while(digitalRead(WIO_5S_LEFT) == LOW || digitalRead(WIO_5S_RIGHT) == LOW) {
      delay(10);
    }
    delay(50); 
  }

  // --- 3. MERANIE A ZOBRAZOVANIE (každé 2 sekundy) ---
  if (millis() - posledneMeranie >= 2000) {
    posledneMeranie = millis();
    
    // Čítanie DHT11
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    if (isnan(t) || isnan(h)) chybaDHT = true;
    else {
      chybaDHT = false;
      lastT = t; lastH = h;
    }

    // Čítanie prachového senzora
    float suceNapatia_mV = 0;
    for(int i = 0; i < 10; i++) {
      digitalWrite(PIN_ILED, HIGH); 
      delayMicroseconds(280);
      int rawHodnota = analogRead(PIN_AOUT);
      delayMicroseconds(40);
      digitalWrite(PIN_ILED, LOW); 
      suceNapatia_mV += (rawHodnota * 3300.0) / 4095.0;
      delay(10); 
    }
    float napatie_mV = suceNapatia_mV / 10.0; 
    float no_dust_voltage = 10.0; 
    float cov_ratio = 0.4;        

    lastP = 0.0;
    if(napatie_mV >= no_dust_voltage) {
      float cisteNapatie = napatie_mV - no_dust_voltage; 
      lastP = cisteNapatie * cov_ratio;
    }

    // --- 4. KONTROLA ALARMOV A ODOSLANIE NA TELEGRAM ---
    bool novyStavT = (lastT < tMin || lastT > tMax);
    bool novyStavH = (lastH < hMin || lastH > hMax);
    bool novyStavP = (lastP > pMax);
    
    // Ak nastala zmena stavu
    if (novyStavT != alarmTeplota || novyStavH != alarmVlhkost || novyStavP != alarmPrach) {
      
      if (client.connected()) {
        // Varovania o prekročení
        if (novyStavT && !alarmTeplota) {
          client.publish("uzol/wio/upozornenie", ("⚠️ POZOR! Teplota mimo limitu: " + String(lastT, 1) + " `C").c_str());
        }
        if (novyStavH && !alarmVlhkost) {
          client.publish("uzol/wio/upozornenie", ("⚠️ POZOR! Vlhkost mimo limitu: " + String(lastH, 1) + " %").c_str());
        }
        if (novyStavP && !alarmPrach) {
          client.publish("uzol/wio/upozornenie", ("⚠️ POZOR! Prach mimo limitu: " + String(lastP, 1) + " ug/m3").c_str());
        }
        
        // Potvrdenia o návrate do normálu
        if (!novyStavT && alarmTeplota) {
          client.publish("uzol/wio/upozornenie", "✅ Teplota je spat v norme.");
        }
        if (!novyStavH && alarmVlhkost) {
          client.publish("uzol/wio/upozornenie", "✅ Vlhkost je spat v norme.");
        }
        if (!novyStavP && alarmPrach) {
          client.publish("uzol/wio/upozornenie", "✅ Prach je spat v norme.");
        }
      }

      // Aktualizácia premenných pre GUI
      alarmTeplota = novyStavT; 
      alarmVlhkost = novyStavH; 
      alarmPrach = novyStavP;
      
      if (aktualnaObrazovka == 0) vykresliObrazovkuDHT(alarmTeplota, alarmVlhkost);
      else vykresliObrazovkuPrach(alarmPrach);
    }

    aktualizujCislaNaDispleji();

    // Odoslanie pravidelných dát
    if (client.connected()) {
      if (!chybaDHT) {
        client.publish("uzol/wio/teplota", String(lastT, 2).c_str());
        client.publish("uzol/wio/vlhkost", String(lastH, 2).c_str());
      }
      client.publish("uzol/wio/prach", String(lastP, 2).c_str());
    } 
  }
}
