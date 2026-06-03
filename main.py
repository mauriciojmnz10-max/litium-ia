import os
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from groq import Groq

# Inicialización de la aplicación FastAPI bajo el entorno unificado MultiKAP
app = FastAPI(
    title="Litium IA Backend",
    description="Ecosistema core para Litium utilizando la infraestructura MultiKAP.",
    version="1.3.0"
)

# =====================================================================
# CONFIGURACIÓN DE SEGURIDAD (CORS)
# =====================================================================
origins = [
    "https://mauriciojmnz10-max.github.io",  # Frontend oficial en GitHub Pages
    "http://localhost:5500",                  # Entorno local con Live Server
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

# =====================================================================
# CONFIGURACIÓN COMERCIAL Y CONSTANTES
# =====================================================================
PLANES_LITIUM = {
    "hogar": {"velocidad": "200 Mbps", "precio": 25.00, "detalles": "Ideal para streaming 4K y teletrabajo."},
    "pro": {"velocidad": "500 Mbps", "precio": 40.00, "detalles": "Para gamers y creadores de contenido exigentes."},
    "corporativo": {"velocidad": "1 Gbps", "precio": 80.00, "detalles": "Enlace dedicado exclusivo con SLA 99.9%."}
}

GROQ_CLIENT = None
if os.environ.get("GROQ_API_KEY"):
    GROQ_CLIENT = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# =====================================================================
# MODELOS DE CONTROL DE DATOS (Pydantic)
# =====================================================================
class ChatRequest(BaseModel):
    message: str
    mode: str

class ChatResponse(BaseModel):
    response: str
    show_form: bool
    form_title: Optional[str] = None
    form_subtitle: Optional[str] = None
    form_context: Optional[str] = None


# =====================================================================
# EXTRACCIÓN DE TASA BCV (Scraping de Alta Fidelidad)
# =====================================================================
def extraer_tasa_bcv_directo() -> float:
    url_bcv = "https://www.bcv.org.ve/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        response = requests.get(url_bcv, headers=headers, verify=False, timeout=8.0)
        if response.status_code != 200:
            return 0.0

        soup = BeautifulSoup(response.text, "html.parser")
        contenedor_dolar = soup.find("div", id="dolar")
        if not contenedor_dolar:
            return 0.0
            
        tag_strong = contenedor_dolar.find("strong")
        if not tag_strong:
            return 0.0
            
        tasa_texto = tag_strong.text.strip()
        tasa_limpia = tasa_texto.replace(",", ".")
        return float(tasa_limpia)
    except Exception as e:
        print(f"[Requests BCV] Error: {str(e)}")
        return 0.0

# =====================================================================
# ENDPOINTS CORE API
# =====================================================================
@app.get("/api/tasa")
def get_tasa_bcv():
    tasa = extraer_tasa_bcv_directo()
    if tasa == 0.0:
        # Fallback de seguridad por si el portal del BCV bloquea la IP del server de Render
        return {"tasa": 46.50, "source": "Litium Core Fallback"}
    return {"tasa": tasa, "source": "Banco Central de Venezuela"}


@app.post("/api/chat", response_model=ChatResponse)
async def procesar_chat_litium(request: ChatRequest):
    msg_lower = request.message.lower()
    
    # Inicialización de banderas por defecto
    show_form = False
    form_title = None
    form_subtitle = None
    form_context = None
    
    # 1. Mapeo de lógica para despliegue automático de formularios (Lead Generation Triggers)
    if request.mode == "ventas" and any(x in msg_lower for x in ["contratar", "comprar", "adquirir", "interesa", "precio", "plan"]):
        show_form = True
        form_title = "Solicitud de Adquisición de Plan"
        form_subtitle = "Introduce tus datos de contacto para formalizar el alta técnica."
        form_context = f"Interés comercial detectado en mensaje: '{request.message}'"
        
    elif request.mode == "soporte" and any(x in msg_lower for x in ["falla", "lento", "caido", "sin internet", "error", "malo", "no sirve"]):
        show_form = True
        form_title = "Apertura de Ticket de Soporte Técnico"
        form_subtitle = "Reporta tu incidencia directamente a la central de ingenieros."
        form_context = f"Incidencia Técnica Reportada: '{request.message}'"
        
    elif request.mode == "cobertura" and any(x in msg_lower for x in ["cobertura", "calle", "sector", "zona", "viven", "disponible"]):
        show_form = True
        form_title = "Validación de Factibilidad de Fibra"
        form_subtitle = "Analizaremos los nodos de distribución más cercanos a tu ubicación."
        form_context = f"Dirección a validar factibilidad: '{request.message}'"

    # 2. Generación de Respuesta Conversacional (Groq LLM o Base Estática)
    if GROQ_CLIENT:
        try:
            prompt_sistema = (
                f"Eres Lia, la IA operativa y consultora de negocios para 'Litium', una empresa líder de Internet por Fibra Óptica Simétrica. "
                f"Operas bajo la suite tecnológica MultiKAP. Tu tono debe ser impecable, tecnológico, conciso y altamente comercial.\n\n"
                f"Estás operando actualmente bajo el MODO: {request.mode.upper()}.\n"
                f"Información de planes actuales de Litium:\n{PLANES_LITIUM}\n\n"
                f"Regla: Si el usuario muestra interés directo en avanzar con una compra, soporte o cobertura, menciónale de forma profesional "
                f"que le has habilitado un formulario en pantalla para recolectar sus datos y transferirlo con el departamento correspondiente."
            )
            
            completion = GROQ_CLIENT.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": request.message}
                ],
                temperature=0.5,
                max_tokens=250
            )
            respuesta_ia = completion.choices[0].message.content
        except Exception as e:
            respuesta_ia = f"Entendido tu requerimiento sobre Litium Fibra Óptica. Para procesar tu solicitud con prioridad, por favor completa el formulario dinámico que acabo de desplegar abajo."
            show_form = True
    else:
        # Fallback determinista en caso de que falte la API Key en el entorno
        if request.mode == "ventas":
            respuesta_ia = "¡Excelente elección! Litium ofrece conectividad simétrica real. He desplegado el formulario de registro para agendar tu instalación."
        elif request.mode == "soporte":
            respuesta_ia = "Lamento los inconvenientes con tu navegación. He abierto la ventana del formulario técnico para que nuestro equipo de guardia verifique el estado de tu ONT."
        else:
            respuesta_ia = "Para verificar si contamos con cobertura en tu zona residencial o comercial, por favor ingresa tus datos en el formulario adjunto."

    return ChatResponse(
        response=respuesta_ia,
        show_form=show_form,
        form_title=form_title,
        form_subtitle=form_subtitle,
        form_context=form_context
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
