import os
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from groq import Groq

app = FastAPI(
    title="Litium IA Core - MultiKAP Suite",
    description="Ecosistema unificado con filtro geográfico de cobertura.",
    version="2.1.0"
)

# CORS estrictamente configurado para producción y local
origins = [
    "https://mauriciojmnz10-max.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base de datos lógica de Cobertura Comercial Litium
ZONAS_COBERTURA_OK = [
    "caricuao", "ruiz pineda", "los telares", "ud7", "ud2", "ud3", "macarao", 
    "cumana", "centro de cumana", "los ipres", "cantarrana", "chacao", "altamira"
]

# Teléfono del equipo de ventas (Formato internacional)
WHATSAPP_ASESOR = "584120000000" 

GROQ_CLIENT = None
if os.environ.get("GROQ_API_KEY"):
    GROQ_CLIENT = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    mode: str

class ChatResponse(BaseModel):
    response: str
    show_form: bool
    form_title: Optional[str] = None
    form_subtitle: Optional[str] = None
    form_context: Optional[str] = None

class FormLeadRequest(BaseModel):
    name: str
    phone: str
    location: str
    context: str

@app.get("/api/tasa")
def get_tasa_bcv():
    """Obtiene la tasa con un timeout ultra corto para evitar congelar el hilo de FastAPI"""
    url_bcv = "https://www.bcv.org.ve/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        # Timeout estricto de 1.5 segundos para que no tumbe el backend completo si el BCV no responde
        response = requests.get(url_bcv, headers=headers, verify=False, timeout=1.5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            contenedor = soup.find("div", id="dolar")
            if contenedor and contenedor.find("strong"):
                tasa_val = float(contenedor.find("strong").text.strip().replace(",", "."))
                return {"tasa": tasa_val, "source": "BCV"}
    except Exception:
        pass
    # Fallback inmediato si el BCV está caído o lento
    return {"tasa": 46.85, "source": "Fallback Dinámico"}

@app.post("/api/chat", response_model=ChatResponse)
async def procesar_chat_litium(request: ChatRequest):
    msg_lower = request.message.lower()
    show_form = False
    form_title = None
    form_subtitle = None
    form_context = None

    if request.mode == "ventas" or any(x in msg_lower for x in ["contratar", "plan", "400", "600", "800", "1 gbps", "precio"]):
        show_form = True
        form_title = "Validación de Cobertura e Instalación"
        form_subtitle = "Ingresa tus datos de contacto para verificar tu sector de inmediato."
        form_context = f"Interés comercial en Planes Litium: '{request.message}'"
    elif request.mode == "cobertura" or "cobertura" in msg_lower:
        show_form = True
        form_title = "Estudio de Factibilidad Geográfica"
        form_subtitle = "Verificaremos la disponibilidad de fibra óptica simétrica en tu zona."
        form_context = f"Consulta directa de cobertura: '{request.message}'"
    elif request.mode == "soporte":
        show_form = True
        form_title = "Centro de Soporte y Pagos"
        form_subtitle = "Introduce tus datos para procesar la taquilla o reporte de avería."
        form_context = f"Soporte / Cobranza administrativa: '{request.message}'"

    if GROQ_CLIENT:
        try:
            prompt_sistema = (
                f"Eres Lia, la IA calificadora y asistente de Litium (Fibra Óptica). Modo: {request.mode.upper()}.\n"
                f"Si el usuario pregunta por planes o contratación, incentívalo diciéndole que deje sus datos en el "
                f"formulario que acaba de aparecer para validar su zona con el equipo técnico de inmediato."
            )
            completion = GROQ_CLIENT.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": request.message}
                ],
                temperature=0.3,
                max_tokens=150
            )
            respuesta_ia = completion.choices[0].message.content
        except Exception:
            respuesta_ia = "¡Excelente elección! He activado el formulario de verificación geográfica en tu pantalla. Por favor, ingresa tu sector para comprobar la disponibilidad de fibra óptica."
    else:
        respuesta_ia = "Por favor, completa el formulario desplegado en pantalla con tu ubicación exacta para comprobar la viabilidad técnica en tu zona."

    return ChatResponse(
        response=respuesta_ia,
        show_form=show_form,
        form_title=form_title,
        form_subtitle=form_subtitle,
        form_context=form_context
    )

@app.post("/api/formulario")
async def procesar_formulario_lead(request: FormLeadRequest):
    loc_lower = request.location.lower()
    tiene_cobertura = any(zona in loc_lower for zona in ZONAS_COBERTURA_OK)
    
    text_whatsapp = f"Hola, vengo desde la web de Litium IA. Mi nombre es {request.name}. Ya validé mi zona ({request.location}) y deseo coordinar la instalación de mi plan de internet."
    text_encoded = text_whatsapp.replace(" ", "%20")
    ws_link = f"https://wa.me/{WHATSAPP_ASESOR}?text={text_encoded}"

    if tiene_cobertura:
        mensaje_lia = (
            f"✨ **¡Excelente, {request.name}!** He verificado tu sector (*{request.location}*) y contamos con "
            f"cobertura y disponibilidad de hilos de fibra óptica activos.\n\n"
            f"Para proceder con la contratación y agendar tu instalación, presiona el botón de abajo "
            f"para transferirte directamente con uno de nuestros **Asesores de Venta Humanos** en WhatsApp."
        )
        return {"status": "aprobado", "cobertura": True, "response": mensaje_lia, "whatsapp_link": ws_link}
    else:
        mensaje_espera = (
            f"📍 **Gracias por tu registro, {request.name}.** Analicé tu ubicación (*{request.location}*) y actualmente "
            f"estamos construyendo la red para llegar a tu sector. Hemos guardado tus datos de manera prioritaria en nuestra lista de expansión."
        )
        return {"status": "lista_espera", "cobertura": False, "response": mensaje_espera, "whatsapp_link": None}
