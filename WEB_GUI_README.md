# DL24P Web GUI - Schnellstart

## Übersicht

Das Web GUI bietet eine moderne Browser-basierte Oberfläche für den ATorch DL24P Battery Tester mit:
- ⚡ Echtzeit-Monitoring von Spannung, Strom, Leistung
- 📊 Live-Diagramme der Entladekurve
- 🔋 Vordefinierte Batterie-Presets (18650, LiPo, LiFePO4, NiMH, etc.)
- 💾 CSV-Export der Messdaten
- 🎨 Modernes Dark-Theme Interface

## Installation

### 1. Abhängigkeiten installieren

```bash
pip3 install -r requirements.txt
```

Die benötigten Pakete sind:
- flask (Webserver)
- flask-cors (CORS-Unterstützung für API)
- pyserial (Serielle Kommunikation)

### 2. Gerät konfigurieren

Erstellen/bearbeiten Sie `~/.dl24.cfg`:

**Für TCP/WiFi-Verbindung:**
```ini
host=dt24p.local
port=8888
```

**Für USB-Serial:**
```ini
serport=/dev/ttyUSB0
baudrate=9600
```

**Für Bluetooth:**
```ini
serport=/dev/rfcomm0
baudrate=9600
waitcomm=1
```

### 3. Webserver starten

**Einfacher Weg:**
```bash
./START_WEB_GUI.sh
```

**Manueller Weg:**
```bash
./dl24_webserver.py
```

### 4. Browser öffnen

Öffnen Sie: **http://localhost:5000**

## Benutzung

### Test starten

1. **Batterie-Typ** auswählen oder Preset-Button klicken (z.B. "18650")
2. **Entladestrom** einstellen (z.B. 1.0 A)
3. **Cut-off Spannung** prüfen (wird automatisch für Batterie-Typ gesetzt)
4. **Max. Zeit** optional setzen (0 = unbegrenzt)
5. **Test Starten** klicken

Der Test läuft automatisch, bis:
- Die Cut-off Spannung erreicht wird ODER
- Die maximale Zeit abläuft ODER
- Sie manuell auf "Test Stoppen" klicken

### Live-Daten

Während des Tests werden angezeigt:
- **Spannung** (V) - Aktuelle Batteriespannung
- **Strom** (A) - Entladestrom
- **Leistung** (W) - Momentane Leistung
- **Kapazität** (mAh) - Integrierte Kapazität
- **Energie** (mWh) - Integrierte Energie
- **Laufzeit** - Verstrichene Zeit

### Daten exportieren

Nach dem Test können Sie auf "Daten Exportieren (CSV)" klicken, um alle Messpunkte als CSV-Datei zu speichern.

Format:
```csv
Zeit (s),Spannung (V),Strom (A),Kapazität (mAh)
0.0,4.200,1.000,0.0
5.0,4.185,1.000,1.4
10.0,4.170,1.000,2.8
...
```

## Batterie-Presets

| Preset | Typ | Cutoff | Typischer Strom |
|--------|-----|--------|-----------------|
| 18650 | Li-Ion | 2.5V | 1.0A |
| LiFePO4 | LiFePO4 | 2.5V | 1.0A |
| NiMH AA | NiMH | 0.9V | 0.5A |
| LiPo 1S | LiPo | 3.0V | 1.0A |

Sie können auch "Benutzerdefiniert" wählen und eigene Werte eingeben.

## Simulations-Modus (ohne Hardware)

Für Tests ohne angeschlossene Hardware:

1. Öffnen Sie `index.html` in einem Editor
2. Ändern Sie Zeile 414: `const SIMULATION_MODE = true;`
3. Starten Sie einen einfachen Webserver:
   ```bash
   python3 -m http.server 8000
   ```
4. Öffnen Sie: http://localhost:8000/index.html

Im Simulations-Modus werden realistische Entladekurven simuliert.

## API-Endpunkte

Das Backend stellt folgende REST-API bereit:

### GET /api/status
Aktuelle Gerätedaten abrufen
```json
{
  "connected": true,
  "running": false,
  "data": {
    "voltage": 12.34,
    "current": 1.00,
    "power": 12.34,
    "capacity": 1234,
    "energy": 5678,
    "temperature": 25,
    "runtime": 0
  }
}
```

### POST /api/start
Test starten
```json
{
  "current": 1.0,
  "cutoff": 3.0,
  "maxTime": 3600
}
```

### POST /api/stop
Test stoppen

### GET /api/data
Alle aufgezeichneten Datenpunkte abrufen

### POST /api/reset
Energie-Zähler zurücksetzen

### GET /api/config
Geräte-Konfiguration abrufen

## Troubleshooting

### "❌ Server nicht erreichbar"
- Stellen Sie sicher, dass `dl24_webserver.py` läuft
- Prüfen Sie, ob Port 5000 frei ist
- Firewall-Einstellungen überprüfen

### "⚠️ Gerät nicht verbunden"
- Überprüfen Sie `~/.dl24.cfg`
- Für USB: Ist das Gerät angeschlossen? (`ls /dev/ttyUSB*`)
- Für TCP: Ist die IP-Adresse erreichbar? (`ping dt24p.local`)
- Für Bluetooth: Ist rfcomm verbunden? (`rfcomm connect 0 XX:XX:XX:XX:XX:XX`)

### Test startet nicht
- Prüfen Sie die Parameter (Strom muss > 0, Cutoff > 0)
- Checken Sie das Server-Log in der Konsole
- Stellen Sie sicher, dass keine Batterie-Unterspannung vorliegt

### Keine Daten im Chart
- Warten Sie mindestens ein Log-Intervall (Standard: 5 Sekunden)
- Prüfen Sie, ob der Test wirklich läuft (grüner Status)
- Browser-Konsole auf Fehler prüfen (F12)

## Erweiterte Nutzung

### Fernzugriff aktivieren

Standardmäßig ist der Server nur auf localhost erreichbar. Für Netzwerk-Zugriff:

1. In `dl24_webserver.py` ist bereits konfiguriert: `host='0.0.0.0'`
2. Finden Sie Ihre IP-Adresse: `ip addr show`
3. Öffnen Sie im Browser: `http://<IhreIP>:5000`

**Sicherheitshinweis:** Kein Passwortschutz! Nur in vertrauenswürdigen Netzwerken verwenden.

### Eigene Batterie-Presets hinzufügen

In `index.html` Zeile 422-427:
```javascript
const presets = {
    '18650': { type: 'liion', current: 1.0, cutoff: 2.5 },
    'mein_akku': { type: 'custom', current: 2.0, cutoff: 2.8 },  // NEU
    // ...
};
```

Dann in HTML Zeile 341-345 Button hinzufügen:
```html
<button class="preset-btn" onclick="setPreset('mein_akku')">Mein Akku</button>
```

## Architektur

```
┌─────────────┐      HTTP/REST      ┌──────────────────┐
│ index.html  │ ◄──────────────────► │ dl24_webserver.py│
│ (Browser)   │    JSON (5000)       │  (Flask Server)  │
└─────────────┘                      └──────────────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │    dl24.py       │
                                     │  (Instr_Atorch)  │
                                     └──────────────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │  DL24P Hardware  │
                                     │ (USB/BT/TCP)     │
                                     └──────────────────┘
```

## Lizenz

Gleiche Lizenz wie dl24.py (siehe Hauptprojekt)
