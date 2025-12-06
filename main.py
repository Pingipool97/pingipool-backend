"""
PINGIPOOL Backend - J.A.R.V.I.S. System
Con generazione AI di progetti 3D
"""

import os
import json
import httpx
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic

load_dotenv()

app = FastAPI(title="PINGIPOOL J.A.R.V.I.S. Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class BlueprintRequest(BaseModel):
    prompt: str

class RTCOffer(BaseModel):
    sdp: str
    type: str

# ═══════════════════════════════════════════════════════════════════════════
# BLUEPRINT 3D GENERATION PROMPT
# ═══════════════════════════════════════════════════════════════════════════

BLUEPRINT_SYSTEM_PROMPT = """Sei J.A.R.V.I.S., un sistema di progettazione 3D holografica avanzato.
Quando l'utente chiede di costruire/progettare qualcosa, genera un blueprint 3D dettagliato in JSON.

COORDINATE:
- Centro: (0, 0, 0)
- Y = altezza (verticale)
- Scala: 1 unità = 1 metro circa
- Mantieni oggetti tra -5 e +5 su ogni asse

REQUISITI:
- Genera ALMENO 80-150 linee per oggetti complessi
- Distribuisci i delay da 0 fino a duration
- Sii MOLTO dettagliato: strutture interne, pannelli, dettagli
- Per cerchi: usa 12-24 segmenti di linea
- Per sfere: usa anelli orizzontali + meridiani verticali

FORMATO - RISPONDI SOLO CON QUESTO JSON, NIENTE ALTRO:
{
  "name": "NOME PROGETTO MAIUSCOLO",
  "code": "XXX-CODE-001",
  "dimensions": {"width": "Xm", "height": "Ym", "depth": "Zm"},
  "components": [
    {"name": "Componente", "qty": "N unità", "icon": "🔧"}
  ],
  "materials": [
    {"name": "Materiale", "qty": "X kg", "icon": "⚙️"}
  ],
  "lines": [
    {"start": [0, 0, 0], "end": [1, 0, 0], "delay": 0.0}
  ],
  "labels": [
    {"text": "LABEL", "pos": [0, 2, 0], "delay": 1.0}
  ],
  "duration": 10.0,
  "narration": [
    {"time": 0, "text": "Inizio costruzione..."}
  ],
  "aiNotes": "Specifiche tecniche del progetto"
}

ESEMPI GEOMETRIE:

Cerchio orizzontale (raggio 2, y=1, 12 segmenti):
for i in range(12):
  a1 = i/12 * 2π, a2 = (i+1)/12 * 2π
  line: [cos(a1)*2, 1, sin(a1)*2] → [cos(a2)*2, 1, sin(a2)*2]

Cilindro (raggio 1, altezza 3):
- Cerchio base a y=0
- Cerchio top a y=3  
- 8-12 linee verticali che connettono

Box (da punto1 a punto2):
- 4 linee base, 4 linee top, 4 verticali

USA LA TUA CREATIVITÀ per progettare oggetti belli e dettagliati!"""


@app.get("/")
async def root():
    return {"status": "online", "service": "PINGIPOOL J.A.R.V.I.S."}


@app.post("/api/ephemeral-key")
async def get_ephemeral_key():
    """Genera una chiave effimera per OpenAI Realtime API"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "voice": "echo",
                "instructions": """Sei J.A.R.V.I.S., l'assistente AI di PINGIPOOL.

REGOLA ASSOLUTA: Parla SEMPRE e SOLO in italiano. MAI in inglese, spagnolo o altre lingue.

PERSONALITÀ:
- Chiama l'utente "Signore"
- Risposte brevi (max 2-3 frasi)
- Professionale con un tocco di ironia

Quando l'utente chiede di costruire qualcosa, usa la funzione show_3d_build con il nome ESATTO dell'oggetto."""
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"OpenAI error: {response.text}")
        
        data = response.json()
        # Restituisco nel formato che il frontend si aspetta
        return {"key": data.get("client_secret", {}).get("value", "")}


@app.post("/generate-blueprint")
async def generate_blueprint(request: BlueprintRequest):
    """Genera un blueprint 3D usando Claude AI"""
    try:
        # Chiedi a Claude di generare il blueprint
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=BLUEPRINT_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Progetta e costruisci: {request.prompt}\n\nGenera un blueprint 3D dettagliato con almeno 100 linee. Rispondi SOLO con il JSON."
                }
            ]
        )
        
        # Estrai il JSON dalla risposta
        response_text = message.content[0].text.strip()
        
        # Prova a parsare il JSON
        # Rimuovi eventuale markdown code block
        if response_text.startswith("```"):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        try:
            blueprint = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Prova a trovare il JSON nella risposta
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                blueprint = json.loads(json_match.group())
            else:
                raise HTTPException(status_code=500, detail=f"Invalid JSON from AI: {str(e)}")
        
        # Validazione base
        if "lines" not in blueprint or len(blueprint["lines"]) == 0:
            raise HTTPException(status_code=500, detail="Blueprint has no lines")
        
        return {
            "success": True,
            "blueprint": blueprint,
            "lineCount": len(blueprint.get("lines", []))
        }
        
    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"AI API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/rtc-connect")
async def rtc_connect(offer: RTCOffer):
    """WebRTC connection per voice chat"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/sdp",
                "OpenAI-Beta": "realtime"
            },
            content=offer.sdp
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="RTC connection failed")
        
        return {"sdp": response.text, "type": "answer"}


# ═══════════════════════════════════════════════════════════════════════════
# IMAGE ANALYSIS (GPT-4V)
# ═══════════════════════════════════════════════════════════════════════════

class ImageAnalysisRequest(BaseModel):
    image: str  # Base64 encoded image
    prompt: str = "Descrivi cosa vedi in questa immagine in italiano. Sii dettagliato ma conciso."


@app.post("/api/analyze-image")
async def analyze_image(request: ImageAnalysisRequest):
    """Analizza un'immagine usando GPT-4V"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    # Gestisci il formato dell'immagine
    image_data = request.image
    
    # Se l'immagine ha già il prefisso data:, usalo direttamente
    if image_data.startswith("data:"):
        image_url = image_data
    else:
        # Altrimenti aggiungi il prefisso (prova png se jpeg non funziona)
        image_url = f"data:image/png;base64,{image_data}"
    
    print(f"📷 Analyzing image, base64 length: {len(request.image)}")
    print(f"📷 Image URL prefix: {image_url[:50]}...")
    print(f"📝 Prompt: {request.prompt[:100]}...")
    
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Sei J.A.R.V.I.S., un sistema di visione AI avanzato. Analizza le immagini in modo dettagliato e rispondi SEMPRE in italiano."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": request.prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": image_url
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 500
                },
                timeout=30.0
            )
            
            print(f"📡 OpenAI response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ OpenAI error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"OpenAI error: {response.text}")
            
            data = response.json()
            analysis = data["choices"][0]["message"]["content"]
            print(f"✅ Analysis: {analysis[:100]}...")
            
            return {
                "success": True,
                "analysis": analysis
            }
            
    except httpx.TimeoutException:
        print("❌ Timeout")
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
