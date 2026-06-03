import os
import json
import hashlib
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq
from bs4 import BeautifulSoup

# ============ ⚠️ IMPORTANTE: LÍNEAS QUE PIDE GEMINI ============
from dotenv import load_dotenv
load_dotenv()  # ← Esto carga tu archivo .env automáticamente
# ================================================================

# ============ CONFIGURACIÓN EXTREMA ============
class Config:
    # Render Free Tier friendly - Lee desde variables de entorno
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    CLOUDINARY_CLOUD = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
    
    # Tasa BCV - caché en RAM (no disco)
    TASA_CACHE = {"value": 46.85, "timestamp": 0, "ttl": 300}
    
    # Cobertura (en RAM, no disco)
    ZONAS_COBERTURA = [
        "caricuao", "ruiz pineda", "los telares", "ud7", "ud2", "ud3",
        "macarao", "cumana", "centro de cumana", "los ipres", "cantarrana"
    ]
    
    # WhatsApp (sin base de datos)
    WHATSAPP_ASESOR = "584120000000"

config = Config()

# ============ MODELOS LIVIANOS ============
class ChatRequest(BaseModel):
    message: str
    mode: str  # "ventas" o "soporte"

class FormRequest(BaseModel):
    name: str
    phone: str
    location: str
    context: str

# ============ FASTAPI CON LIFESPAN LIMPIO ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio - sin nada pesado
    print("🔥 Litium IA iniciado en modo minimalista")
    print(f"📦 Cloudinary configurado: {'✅ SI' if config.CLOUDINARY_CLOUD else '❌ NO'}")
    print(f"🤖 Groq configurado: {'✅ SI' if config.GROQ_API_KEY else '❌ NO'}")
    yield
    # Cierre - liberar RAM
    print("💀 Cerrando conexiones...")

app = FastAPI(lifespan=lifespan)

# CORS para GitHub Pages + local
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mauriciojmnz10-max.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ============ 1. TASA BCV CON CACHÉ EN RAM ============
@app.get("/api/tasa")
async def get_tasa():
    ahora = time.time()
    if ahora - config.TASA_CACHE["timestamp"] < config.TASA_CACHE["ttl"]:
        return {"tasa": config.TASA_CACHE["value"], "source": "cache"}
    
    try:
        response = requests.get("https://www.bcv.org.ve/", timeout=2)
        soup = BeautifulSoup(response.text, "html.parser")
        dolar_div = soup.find("div", id="dolar")
        if dolar_div and dolar_div.find("strong"):
            tasa = float(dolar_div.find("strong").text.replace(",", "."))
            config.TASA_CACHE = {"value": tasa, "timestamp": ahora, "ttl": 300}
            return {"tasa": tasa, "source": "bcv"}
    except:
        pass
    
    return {"tasa": config.TASA_CACHE["value"], "source": "fallback"}

# ============ 2. CHAT CON GROQ (sin memoria pesada) ============
client = Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None

@app.post("/api/chat")
async def chat(request: ChatRequest):
    msg_lower = request.message.lower()
    
    # Detectar necesidad de formulario (reglas simples, sin LLM pesado)
    show_form = False
    form_title = None
    form_subtitle = None
    
    if request.mode == "ventas" and any(p in msg_lower for p in ["contratar", "plan", "400", "600", "800", "precio", "1 gbps"]):
        show_form = True
        form_title = "Contratación Litium"
        form_subtitle = "Verificamos cobertura en tu sector"
    elif request.mode == "soporte" and any(s in msg_lower for s in ["lento", "falla", "no funciona", "avería", "atenuación"]):
        show_form = True
        form_title = "Reporte Técnico"
        form_subtitle = "Abre un ticket para asistencia prioritaria"
    
    # Respuesta base (si no hay Groq o falla)
    respuesta = "Por favor, completa el formulario para continuar con tu solicitud."
    
    if client:
        try:
            sys_prompt = "Eres Lia, asistente de Litium. Responde breve (max 80 palabras). NO uses **. Sé amable y directa."
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": request.message}
                ],
                temperature=0.3,
                max_tokens=120
            )
            respuesta = completion.choices[0].message.content
            # Limpiar **
            respuesta = respuesta.replace("**", "")
        except Exception as e:
            print(f"Groq error: {e}")
            respuesta = "¡Hola! Por favor, completa el formulario para que podamos ayudarte."
    
    return {
        "response": respuesta,
        "show_form": show_form,
        "form_title": form_title,
        "form_subtitle": form_subtitle,
        "form_context": request.message
    }

# ============ 3. SUBIDA DE IMÁGENES A CLOUDINARY (sin disco local) ============
@app.post("/api/pagos/validar")
async def validar_pago(
    cedula: str = Form(...),
    nombre: str = Form(...),
    banco: str = Form(...),
    referencia: str = Form(...),
    monto_usd: float = Form(...),
    comprobante: UploadFile = File(...)
):
    """Recibe la imagen, la sube DIRECTAMENTE a Cloudinary (no toca disco local)"""
    
    # Validar tipo de archivo
    if not comprobante.content_type.startswith("image/"):
        raise HTTPException(400, "Solo se permiten imágenes")
    
    # Verificar que Cloudinary está configurado
    if not config.CLOUDINARY_CLOUD or not config.CLOUDINARY_KEY:
        raise HTTPException(500, "Cloudinary no configurado. Contacta al administrador.")
    
    # Subir a Cloudinary desde memoria (sin escribir en disco)
    try:
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=config.CLOUDINARY_CLOUD,
            api_key=config.CLOUDINARY_KEY,
            api_secret=config.CLOUDINARY_SECRET
        )
        
        # Leer bytes directamente a RAM
        file_bytes = await comprobante.read()
        
        # Subir usando datos en memoria
        upload_result = cloudinary.uploader.upload(
            file_bytes,
            folder="litium_pagos",
            public_id=f"pago_{referencia}_{int(time.time())}"
        )
        
        imagen_url = upload_result.get("secure_url")
        
        return {
            "status": "ok",
            "message": "Comprobante recibido y almacenado en la nube",
            "url": imagen_url,
            "referencia": referencia
        }
        
    except Exception as e:
        print(f"Cloudinary error: {e}")
        raise HTTPException(500, f"Error al subir imagen: {str(e)}")

# ============ 4. TELEMETRÍA SIN WEBSOCKETS (polling simple) ============
# Almacenamiento en RAM volátil (para demostración)
metricas_cache = {}

@app.get("/api/metrics/{nodo_id}")
async def get_metricas(nodo_id: str):
    """Endpoint HTTP GET con caché. El frontend puede consultar cada 5-10 segundos."""
    
    ahora = time.time()
    
    # Si hay caché reciente (menos de 5 segundos), devolverla
    if nodo_id in metricas_cache and ahora - metricas_cache[nodo_id]["timestamp"] < 5:
        return metricas_cache[nodo_id]["data"]
    
    # Simular métricas (sin WebSockets, sin hilos persistentes)
    import random
    metricas = {
        "nodo_id": nodo_id,
        "latencia_ms": round(random.gauss(12, 3), 1),
        "senal_db": round(random.gauss(-45, 5), 1),
        "ancho_banda_mbps": round(random.gauss(450, 50), 0),
        "timestamp": ahora
    }
    
    metricas_cache[nodo_id] = {"data": metricas, "timestamp": ahora}
    
    # Limpiar caché vieja cada 100 requests
    if len(metricas_cache) > 50:
        for k in list(metricas_cache.keys()):
            if ahora - metricas_cache[k]["timestamp"] > 60:
                del metricas_cache[k]
    
    return metricas

# ============ 5. FORMULARIO DE LEAD (sin base de datos) ============
@app.post("/api/formulario")
async def procesar_formulario(request: FormRequest):
    ubicacion = request.location.lower()
    
    tiene_cobertura = any(zona in ubicacion for zona in config.ZONAS_COBERTURA)
    
    if tiene_cobertura:
        import urllib.parse
        texto = f"Hola, soy {request.name} de {request.location}. Quiero contratar Litium."
        link = f"https://wa.me/{config.WHATSAPP_ASESOR}?text={urllib.parse.quote(texto)}"
        
        return {
            "status": "aprobado",
            "cobertura": True,
            "response": f"✅ {request.name}, tu sector tiene cobertura. Haz clic para hablar con un asesor.",
            "whatsapp_link": link
        }
    else:
        return {
            "status": "lista_espera",
            "cobertura": False,
            "response": f"📌 {request.name}, estamos expandiendo la red a {request.location}. Quedas en lista prioritaria.",
            "whatsapp_link": None
        }

# ============ 6. HEALTH CHECK (para Render y UptimeRobot) ============
@app.get("/health")
async def health():
    return {
        "status": "alive",
        "ram_mb": "~50",
        "storage": "0MB local",
        "cloudinary": "✅" if config.CLOUDINARY_CLOUD else "❌",
        "groq": "✅" if config.GROQ_API_KEY else "❌"
    }

@app.get("/")
async def root():
    return {"message": "Litium IA - Modo Combate", "version": "3.0-minimal"}

# Si ejecutas este archivo directamente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
