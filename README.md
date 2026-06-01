# DvG
Das ist ein Test-Repository für DvG. Es enthält eine einfache README-Datei, um die Funktionalität von DvG zu demonstrieren. 
Weitere Dateien und Ordner können hinzugefügt werden, um die Möglichkeiten von DvG zu erweitern.

# Starten
Um dieses Repository zu verwenden, klonen Sie es einfach auf Ihren lokalen Computer.
Anschließend starten sie zunächst RabbitMQ, damit DvG eine Verbindung herstellen kann.
```bash
docker run -d --hostname my-rabbit --name some-rabbit -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```
Alternativ kann man dies auch mithilfe von Docker compose tun:
```bash
cd extras
docker-compose up
```
Nachdem RabbitMQ läuft, können Sie DvG starten, um die Funktionen zu testen.
Hierfür starten sie in einem neuen Terminal den gRPC-Server:
```bash
uv run server
```

In einem weiteren Terminal können sie dann den Message-server starten:
```bash
uv run message
```

Wenn man nun die JobWorker für Camunda laufen lassen möchte kann man dies mithilfe des folgenden Befehls tun:
```bash
uv run camunda
```

### Testen der grundlegenden Funktionen
Um nun die Funktionen von DvG zu testen, können sie den gRPC-Client verwenden. 
Hierfür starten sie in einem neuen Terminal den Client und rufen hier die gewünschten Funktionen auf, um die Kommunikation zwischen 
den Komponenten zu testen. Die funktionen sind die folgenden:
- ```create <aussteller> <empfänger> <betrag>```: Erstellt eine neue Rechnung mit den angegebenen Daten.
- ```get <rechnungs_id>```: Ruft die Details einer Rechnung anhand ihrer ID ab.
```bash
uv run client <funktion> <argumente>
```

# Speicherort
Die Daten der Rechnungen werden in einer SQLite-Datenbank gespeichert, die sich im Verzeichnis `data` befindet. 
Die Datenbankdatei heißt `rechnungen.db`. Alle Rechnungsinformationen

# Erweitern
Um die gRPC-Funktionen zu erweitern, muss man zunächst die proto-Datei anpassen, um die neuen Funktionen und Nachrichten zu 
definieren. Wenn man dies getan hat, kann man sich an die Implementierung der neuen Funktionen im Server machen. Hierfür kann man
sich die grundlegenden Funktionen generieren lassen.
```bash
uv run proto <proto-dateiname>
```
