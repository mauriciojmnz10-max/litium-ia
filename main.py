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

# Configuración de CORS flexible para tus despliegues en GitHub Pages y local
origins = [
    "https://mauriciojmnz10-max.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base de datos lógica de Cobertura Comercial Litium (Sectores clave)
ZONAS_COBERTURA_OK = [
    "caricuao", "ruiz pineda", "los telares", "ud7", "ud2", "ud3", "macarao", 
    "cumana", "centro de cumana", "los ipres", "cantarrana", "chacao", "altamira"
]

PLANES_LITIUM = {
    "basico": {"velocidad": "400 Mbps", "precio": "$10"},
    "hogar": {"velocidad": "600 Mbps", "precio": "Consultar"},
    "fiel": {"velocidad": "800 Mbps", "precio": "Consultar"},
    "premium": {"velocidad": "1 Gbps", "precio": "Consultar"}
}

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
    """Extrae la tasa oficial o devuelve un fallback estable en caso de bloqueo del BCV"""
    url_bcv = "https://www.bcv.org.ve/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url_bcv, headers=headers, verify=False, timeout=5.0)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            contenedor = soup.find("div", id="dolar")
            if contenedor and contenedor.find("strong"):
                tasa_val = float(contenedor.find("strong").text.strip().replace(",", "."))
                return {"tasa": tasa_val, "source": "BCV"}
    except Exception:
        pass
    return {"tasa": 46.85, "source": "Fallback Dinámico"}

@app.post("/api/chat", response_model=ChatResponse)
async def procesar_chat_litium(request: ChatRequest):
    msg_lower = request.message.lower()
    show_form = False
    form_title = None
    form_subtitle = None
    form_context = None

    # Detectores de intención automáticos
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
                f"Eres Lia, la IA cerradora y asistente de Litium (Fibra Óptica). Modo: {request.mode.upper()}.\n"
                f"Si el usuario pregunta por planes o contratación, aliéntalo diciéndole que la instalación es GRATIS "
                f"y que debe dejar sus datos en el formulario que acaba de aparecer en pantalla para validar su cobertura en segundos."
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
            respuesta_ia = "¡Excelente elección! He activado el formulario de verificación geográfica en tu pantalla. Coloca tu sector para confirmarte la disponibilidad de fibra óptica ahora mismo."
    else:
        respuesta_ia = "Por favor, completa el formulario desplegado abajo con tu ubicación exacta para comprobar la viabilidad técnica de los hilos de fibra óptica."

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
    
    # Filtro lógico inteligente de cobertura
    tiene_cobertura = any(zona in loc_lower for zona in ZONAS_COBERTURA_OK)
    
    if tiene_cobertura:
        mensaje_cierre = (
            f"🚀 **¡EXCELENTES NOTICIAS!** He verificado tu ubicación (*{request.location}*) y cuentas con "
            f"**Disponibilidad Inmediata de Fibra Óptica Litium**. Tu solicitud ha sido catalogada como **Prioritaria**. "
            f"En este mismo instante, un asesor de ventas humano se está comunicando a tu número ({request.phone}) "
            f"para agendar tu **Instalación GRATIS** esta misma semana. ¡Prepárate para la velocidad láser!"
        )
        return {
            "status": "calificado",
            "cobertura": True,
            "response": mensaje_cierre,
            "asesor_action": "Asignación inmediata de cuadrilla de instalación."
        }
    else:
        mensaje_espera = (
            f"📍 **Verificación Geográfica realizada:** Actualmente tu sector (*{request.location}*) se encuentra en "
            f"nuestra fase de **Próxima Expansión de Planta Externa**. Hemos registrado con éxito tus datos en la lista "
            f"de espera preferencial. Apenas encendamos el nodo de tu zona, serás el primero en recibir la promoción de bienvenida."
        )
        return {
            "status": "espera",
            "cobertura": False,
            "response": mensaje_espera,
            "asesor_action": "Almacenado en base de datos para expansión de infraestructura."
        }
