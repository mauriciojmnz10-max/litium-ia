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
    description="Ecosistema unificado de procesamiento inteligente.",
    version="2.0.0"
)

# Orígenes autorizados para la comunicación fluida del ecosistema
origins = [
    "https://mauriciojmnz10-max.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Catálogo Corporativo Oficial extraído directamente de "images.jpg"
PLANES_LITIUM = {
    "basico": {"velocidad": "400 Mbps", "precio": "$10", "detalles": "Full conexión a velocidad de entrada."},
    "hogar": {"velocidad": "600 Mbps", "precio": "Consultar", "detalles": "Diseñado para la estabilidad familiar."},
    "fiel": {"velocidad": "800 Mbps", "precio": "Consultar", "detalles": "Ancho de banda premium para múltiples dispositivos."},
    "premium": {"velocidad": "1 Gbps", "precio": "Consultar", "detalles": "Máxima potencia simétrica disponible."}
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

def extraer_tasa_bcv_directo() -> float:
    url_bcv = "https://www.bcv.org.ve/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url_bcv, headers=headers, verify=False, timeout=6.0)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            contenedor = soup.find("div", id="dolar")
            if contenedor and contenedor.find("strong"):
                return float(contenedor.find("strong").text.strip().replace(",", "."))
    except Exception:
        pass
    return 0.0

@app.get("/api/tasa")
def get_tasa_bcv():
    tasa = extraer_tasa_bcv_directo()
    if tasa == 0.0:
        return {"tasa": 46.55, "source": "Fallback Local"}
    return {"tasa": tasa, "source": "Banco Central de Venezuela"}

@app.post("/api/chat", response_model=ChatResponse)
async def procesar_chat_litium(request: ChatRequest):
    msg_lower = request.message.lower()
    show_form = False
    form_title = None
    form_subtitle = None
    form_context = None

    # Activadores inteligentes basados en comportamiento de pestañas y referencias visuales
    if request.mode == "ventas" and any(x in msg_lower for x in ["contratar", "comprar", "interesa", "plan", "400", "600", "800", "1 gbps"]):
        show_form = True
        form_title = "Adquisición de Plan Litium"
        form_subtitle = "Introduce tus datos básicos para iniciar tu orden de instalación gratis."
        form_context = f"Solicitud comercial de Plan desde mensaje: '{request.message}'"
        
    elif request.mode == "soporte" and any(x in msg_lower for x in ["pago", "mensual", "pagar", "reportar", "falla", "corte"]):
        show_form = True
        form_title = "Gestión de Cuenta / Reporte de Incidencias"
        form_subtitle = "Completa los campos para conciliar tu pago o reportar la falla a ingenieros."
        form_context = f"Gestión administrativa/técnica: '{request.message}'"
        
    elif request.mode == "cobertura" and any(x in msg_lower for x in ["cobertura", "zona", "sector", "calle", "llegar"]):
        show_form = True
        form_title = "Estudio de Factibilidad Técnica"
        form_subtitle = "Comprobaremos la disponibilidad de fibra óptica simétrica en tu sector."
        form_context = f"Ubicación de cobertura consultada: '{request.message}'"

    if GROQ_CLIENT:
        try:
            prompt_sistema = (
                f"Eres Lia, la IA central del ecosistema MultiKAP para la marca 'Litium', un proveedor de internet de Fibra Óptica Simétrica.\n"
                f"Tu tono de comunicación es conciso, amigable, directo, usando viñetas limpias si das listas.\n"
                f"Estás atendiendo en el MODO: {request.mode.upper()}.\n"
                f"Catálogo oficial de velocidades de la marca: {PLANES_LITIUM}.\n"
                f"Importante: Recuerda al cliente de forma sutil que la instalación es GRATIS y que los pagos se realizan antes del día 5 de cada mes."
            )
            completion = GROQ_CLIENT.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": request.message}
                ],
                temperature=0.4,
                max_tokens=200
            )
            respuesta_ia = completion.choices[0].message.content
        except Exception:
            respuesta_ia = "¡Perfecto! He recibido tu solicitud. He habilitado el formulario de datos para procesar tu caso inmediatamente."
    else:
        respuesta_ia = "Entendido tu mensaje. Para darte una respuesta inmediata y formal, ingresa tus datos en el formulario desplegado."

    return ChatResponse(
        response=respuesta_ia,
        show_form=show_form,
        form_title=form_title,
        form_subtitle=form_subtitle,
        form_context=form_context
    )
