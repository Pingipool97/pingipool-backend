# PINGIPOOL Backend

Backend server per PINGIPOOL - Assistente AI vocale.

## Deploy su Render

1. Fork/clona questo repo
2. Crea un nuovo Web Service su Render
3. Collega il repo GitHub
4. Configura:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Aggiungi Environment Variable:
   - `OPENAI_API_KEY` = la tua chiave API OpenAI

## Endpoint

- `GET /health` - Verifica stato server
- `POST /api/ephemeral-key` - Genera chiave temporanea per WebRTC
- `GET /api/config` - Configurazione per frontend
