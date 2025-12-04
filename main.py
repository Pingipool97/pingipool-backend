"""
PINGIPOOL Backend Server
Genera ephemeral keys per la connessione WebRTC alla Realtime API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Union
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PINGIPOOL Backend", version="1.0.0")

# CORS per permettere richieste dalla PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione, specifica il dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurazione
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REALTIME_MODEL = "gpt-4o-realtime-preview"

# System prompt per PINGIPOOL
PINGIPOOL_SYSTEM_PROMPT = """
Sei PINGIPOOL, un assistente personale AI avanzato creato da Pingipool AI Studio.

PERSONALITÀ:
- Professionale ma con un tocco di umorismo sottile
- Efficiente e diretto nelle risposte
- Proattivo nel suggerire soluzioni
- Parla in italiano a meno che l'utente non usi un'altra lingua

REGOLA FONDAMENTALE SUL CODICE:
- Quando devi creare o mostrare codice (HTML, CSS, JavaScript, Python, qualsiasi linguaggio), USA SEMPRE la funzione display_code
- NON LEGGERE MAI il codice ad alta voce - è fastidioso e inutile
- Dopo aver usato display_code, di' semplicemente "Ho preparato il codice, lo trova nella preview" o "Ecco fatto, il codice è visualizzato"
- MAI pronunciare tag, parentesi, simboli di programmazione

CAPACITÀ:
- Rispondere a domande generali
- Aiutare con calcoli e ragionamenti
- Creare codice (usando display_code, mai leggendolo)
- Fornire promemoria e organizzare informazioni
- Conversare in modo naturale

STILE DI COMUNICAZIONE:
- Usa "Signore" occasionalmente ma non in modo eccessivo
- Sii conciso ma completo
- Se non sai qualcosa, ammettilo con eleganza

Ricorda: sei un assistente avanzato, non un semplice chatbot.
"""


class EphemeralKeyResponse(BaseModel):
    key: str
    expires_at: Union[str, int]
    model: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    api_configured: bool


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica lo stato del server"""
    return HealthResponse(
        status="online",
        timestamp=datetime.utcnow().isoformat(),
        api_configured=bool(OPENAI_API_KEY)
    )


@app.post("/api/ephemeral-key", response_model=EphemeralKeyResponse)
async def get_ephemeral_key():
    """
    Genera una chiave temporanea per la connessione WebRTC.
    La chiave è valida per circa 1 minuto.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY non configurata sul server"
        )
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": REALTIME_MODEL,
                    "voice": "alloy",
                    "instructions": PINGIPOOL_SYSTEM_PROMPT,
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Errore OpenAI API: {error_detail}"
                )
            
            data = response.json()
            
            # Estrai i valori con fallback
            client_secret = data.get("client_secret", {})
            key = client_secret.get("value", "")
            expires_at = client_secret.get("expires_at", 0)
            
            return EphemeralKeyResponse(
                key=key,
                expires_at=expires_at,
                model=REALTIME_MODEL
            )
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Timeout nella richiesta a OpenAI"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Errore di connessione: {str(e)}"
            )


@app.get("/api/config")
async def get_config():
    """Restituisce la configurazione per il frontend"""
    return {
        "model": REALTIME_MODEL,
        "voice": "alloy",
        "system_prompt_preview": PINGIPOOL_SYSTEM_PROMPT[:200] + "..."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
