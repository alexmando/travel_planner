# 🧳 AI Travel Planner (CrewAI)

Sistema intelligente di pianificazione viaggi che seleziona automaticamente destinazione, voli, hotel e attività in base alle preferenze dell'utente.

## 📁 Struttura del progetto
travel_planner/
├── .env # Chiavi API (non committare)
├── knowledge/
│ ├── destinations.json # Database delle destinazioni
│ └── user_preference.txt
├── src/
│ └── travel_planner/
│ ├── crew.py # Agenti, task e Crew
│ ├── main.py # Punto d'ingresso
│ └── tools/ # Strumenti personalizzati
├── pyproject.toml
├── uv.lock
└── README.md

text

## 🚀 Avvio rapido

### 1. Clona il repository

```bash
git clone https://github.com/tuo-username/travel_planner.git
cd travel_planner
2. Ambiente Python
Con uv (consigliato):

bash
uv sync
Oppure con venv standard:

bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
pip install -e .
3. Configura il file .env
Crea un file .env nella cartella principale travel_planner/ con il seguente contenuto:

env
# ==========================================
# MODELLO LLM (Groq)
# ==========================================
MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=la_tua_groq_api_key_qui

# ==========================================
# RAPIDAPI (unica chiave per tutti i servizi)
# ==========================================
RAPIDAPI_KEY=la_tua_rapidapi_key_qui

# Host specifici (già configurati nei tool)
RAPIDAPI_HOST_SKYSCRAPPER=sky-scrapper.p.rapidapi.com
RAPIDAPI_HOST_BOOKING=booking-com15.p.rapidapi.com
RAPIDAPI_HOST_HOTELS=hotels4.p.rapidapi.com
⚠️ Importante: non committare mai il file .env – aggiungilo al .gitignore.

4. Ottieni le chiavi API
🔐 Groq API (necessaria)
Link per la registrazione e la generazione della chiave:
https://console.groq.com

Crea un account gratuito (piano gratuito: fino a 1000 richieste/giorno e 100.000 token/giorno)

Nel menu in alto a destra, clicca su API Keys → Create API Key

Assegna un nome alla chiave e clicca su Submit

Copia la chiave che inizia con gsk_ e incollala in GROQ_API_KEY

🔐 RapidAPI Key (per voli, hotel, attività)
Crea un account gratuito su RapidAPI

Iscriviti ai seguenti API (piano gratuito sufficiente per test):

Servizio	Link API	Host (X-RapidAPI-Host)
Sky Scrapper (voli)	Sky Scrapper API	sky-scrapper.p.rapidapi.com
Booking.com (hotel)	Booking.com API	booking-com15.p.rapidapi.com
Hotels4 (hotel – fallback)	Hotels4 API	hotels4.p.rapidapi.com
Dopo l'iscrizione, vai su Security → copia la tua X-RapidAPI-Key

Incollala in RAPIDAPI_KEY

La stessa chiave funziona per tutti i servizi RapidAPI, e gli host specifici sono già configurati nei tool.

5. Esegui il planner
# Con uv (consigliato)
uv run python travel_planner/src/travel_planner/main.py

# Oppure con ambiente virtuale attivo
python travel_planner/src/travel_planner/main.py
⚙️ Personalizzazione
Cambiare modello LLM
Modifica la variabile MODEL nel file .env:

env
MODEL=groq/mixtral-8x7b-32768      # più stabile, ampio contesto
# oppure
MODEL=groq/llama-3.1-8b-instant    # più veloce, minore consumo token
Lista completa dei modelli supportati da Groq:

Modello	ID nel progetto	Caratteristiche
Llama 3.3 70B	groq/llama-3.3-70b-versatile	Multilingua, 70B parametri, 128k contesto
Mixtral 8x7B	groq/mixtral-8x7b-32768	32k contesto, ottimo per documenti lunghi
Llama 3.1 8B	groq/llama-3.1-8b-instant	Veloce, economico in token
Documentazione ufficiale Groq sui modelli: https://console.groq.com/docs/models

Modificare le preferenze utente
Apri main.py e aggiorna il dizionario user_inputs:

user_inputs = {
    "budget": "medium",           # low, medium, high
    "period": "summer",           # summer, winter, spring, autumn
    "style": "nightlife",         # nightlife, relax, culture, adventure, family, food, nature, mixed
    "age_group": "18-25",         # 18-25, 26-35, 36-50, 50+
    "origin": "Milan",
    "departure_date": "2026-08-10",
    "return_date": "2026-08-17",
}
Aggiungere destinazioni
Modifica il file knowledge/destinations.json seguendo il formato esistente:

json
[
  {
    "city": "Barcellona",
    "country": "Spagna",
    "continent": "Europa",
    "budget": "medium",
    "styles": ["nightlife", "cultura", "cibo"],
    "best_period": ["primavera", "estate"],
    "best_for_age": ["18-25", "26-35"],
    "description": "Città vibrante con spiagge e architettura di Gaudí."
  }
]
🐛 Risoluzione problemi
❌ ModuleNotFoundError: No module named 'dotenv'
Assicurati che l'ambiente virtuale sia attivo

Installa il pacchetto: pip install python-dotenv

Oppure esegui uv sync per installare tutte le dipendenze

❌ Rate limit reached for model
Aspetta 10-15 secondi e riprova

Usa un modello con limite TPM più alto (es. groq/llama-3.3-70b-versatile → 12.000 TPM)

Riduci il consumo di token: imposta verbose=False negli agenti e accorcia le descrizioni dei task

❌ SSL: UNEXPECTED_EOF_WHILE_READING
Problema temporaneo di rete o del server Groq – riprova dopo un minuto

Disabilita VPN/proxy se attivi

Prova un modello diverso (es. groq/mixtral-8x7b-32768)

❌ destinations.json not found
Verifica che il file esista in travel_planner/knowledge/destinations.json

Il tool cerca il percorso: .../travel_planner/knowledge/destinations.json

❌ Error executing tool: name 'departure_date' is not defined
È stato corretto nel tool hotel_tool.py usando checkin_date e checkout_date

Assicurati di avere l'ultima versione del codice

❌ No module named 'botocore'
Warning innocuo – non influisce sul funzionamento. Puoi ignorarlo.

📄 Licenza
Progetto a scopo educativo e personale.
