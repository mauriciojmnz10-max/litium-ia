import os
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from groq import Groq  # Importación nativa de tu librería del requirements

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
    "http://localhost:5500",                # Entorno local con Live Server
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
    "hogar": {"velocidad": "200 Mbps", "precio": 25.00},
    "pro": {"velocidad": "500 Mbps", "precio": 40.00},
    "corporativo": {"velocidad": "1 Gbps", "precio": 80.00}
}

# Inicialización opcional del cliente Groq utilizando tus variables de entorno en Render
# GROQ_API_KEY debe estar configurada en el panel de Render
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
# EXTRACCIÓN DIRECTA DE INTERNET (Mecanismo Síncrono con Requests)
# =====================================================================
def extraer_tasa_bcv_directo() -> float:
    """
    Se conecta directamente al portal oficial del Banco Central de Venezuela
    utilizando requests, procesa el HTML y extrae la tasa del dólar en vivo.
    """
    url_bcv = "https://www.bcv.org.ve/"
    
    # Headers para simular un navegador real y evitar bloqueos por políticas de seguridad del BCV
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5"
    }
    
    try:
        # Realizamos la petición síncrona con un timeout estricto de 8 segundos
        # verify=False previene fallos si los certificados intermedios del BCV expiran
        response = requests.get(url_bcv, headers=headers, verify=False, timeout=8.0)
        
        if response.status_code != 200:
            print(f"[Requests BCV] Código de estado inválido: {response.status_code}")
            return 0.0

        # Procesamiento del árbol HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Localización exacta de las etiquetas contenedoras del valor de la divisa estadounidense
        contenedor_dolar = soup.find("div", id="dolar")
        if not contenedor_dolar:
            print("[Requests BCV] No se encontró el contenedor id='dolar'")
            return 0.0
            
        tag_strong = contenedor_dolar.find("strong")
        if not tag_strong:
            print("[Requests BCV] No se encontró la etiqueta strong con el valor")
            return 0.0
            
        # Limpieza de espacios y cambio de coma decimal europea a punto flotante de Python
        tasa_texto = tag_strong.text.strip()
        tasa_limpia = tasa_texto.replace(",", ".")
        
        return float(tasa_limpia)

    except Exception as e:
        print(f"[Requests BCV] Error durante la extracción de datos: {str(e)}")
        return 0.0


# =====================================================================
# ENDPOINTS OPERATIVOS DE LA API
# =====================================================================

@app.get("/")
def health_check():
    """Ruta raíz para que el validador de Render compruebe que el servicio está activo."""
    return {
        "status": "online",
        "ecosystem": "MultiKAP",
        "service": "Litium IA Core Engine"
    }


@app.get("/api/tasa")
async def get_tasa_cambiaria():
    """
    Endpoint de consulta para el Navbar de tu Frontend.
    Garantiza una tasa de respaldo si el servidor del BCV sufre una desconexión total.
    """
    tasa = extraer_tasa_bcv_directo()
    
    if tasa > 0.0:
        return {"tasa": tasa}
    else:
        # Fallback de contingencia técnica para evitar bloqueos en cascada en la interfaz
        tasa_contingencia = 40.55
        print(f"[Alerta] Aplicando tasa de respaldo: {tasa_contingencia}")
        return {"tasa": tasa_contingencia}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_handler(request: ChatRequest):
    """
    Controlador del chat inteligente de Lia. Utiliza segmentación por intenciones
    y permite la integración directa de los modelos de inferencia de Groq.
    """
    user_message = request.message.strip()
    mode = request.mode.lower()

    if not user_message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    try:
        ai_reply = ""
        should_trigger_form = False
        f_title = None
        f_subtitle = None
        f_context = None

        # Variables comerciales inyectadas en caliente
        info_planes = (
            f"Plan Hogar ({PLANES_LITIUM['hogar']['velocidad']} por ${PLANES_LITIUM['hogar']['precio']:.2f}), "
            f"Plan Pro ({PLANES_LITIUM['pro']['velocidad']} por ${PLANES_LITIUM['pro']['precio']:.2f}) y "
            f"Plan Corporativo ({PLANES_LITIUM['corporativo']['velocidad']} por ${PLANES_LITIUM['corporativo']['precio']:.2f})."
        )

        # -----------------------------------------------------------------
        # LÓGICA CONVERSACIONAL Y ACCIONADORES DE FORMULARIOS
        # -----------------------------------------------------------------
        if mode == "ventas":
            palabras_cierre = ["contratar", "adquirir", "comprar", "quiero el plan", "me interesa"]
            if any(palabra in user_message.lower() for palabra in palabras_cierre):
                ai_reply = "¡Excelente elección! Para registrar tu solicitud de instalación de fibra en nuestro sistema MultiKAP, por favor rellena el formulario de alta que acaba de aparecer en tu pantalla."
                should_trigger_form = True
                f_title = "Formulario de Contratación"
                f_subtitle = "Introduce tus datos de contacto para agendar la instalación."
                f_context = f"Cierre comercial de ventas. Mensaje: '{user_message}'"
            else:
                ai_reply = f"Actualmente ofrecemos navegación simétrica premium: {info_planes} ¿Cuál de estas alternativas prefieres activar para tu conectividad?"

        elif mode == "soporte":
            palabras_falla = ["caido", "sin internet", "falla", "averia", "luz roja", "no navega"]
            if any(palabra in user_message.lower() for palabra in palabras_falla):
                ai_reply = "Entendido. He abierto un canal de atención de incidencias en tu pantalla. Rellena los datos para generar tu orden técnica prioritaria inmediatamente."
                should_trigger_form = True
                f_title = "Apertura de Ticket de Soporte"
                f_subtitle = "Reporta tu incidencia directamente a nuestro equipo de guardia técnica."
                f_context = f"Falla de línea reportada: '{user_message}'"
            else:
                ai_reply = "Por favor, indícame si el bombillo led marcado como LOS en tu equipo óptico está encendido en color rojo fijo para asistirte en el descarte rápido."

        elif mode == "cobertura":
            ai_reply = "Disponemos de cobertura activa en sectores de Caracas (Caricuao, Ruiz Pineda, Los Telares) y zonas de Cumaná. Indícame tu dirección o abre el formulario adjunto para proceder con un estudio de factibilidad detallado."
            palabras_cobertura = ["verificar", "cobertura", "vivo en", "saber si llega"]
            if any(palabra in user_message.lower() for palabra in palabras_cobertura):
                should_trigger_form = True
                f_title = "Estudio de Factibilidad Técnica"
                f_subtitle = "Verificamos si disponemos de puertos libres en tu zona residencial."
                f_context = f"Solicitud geográfica para la ubicación: '{user_message}'"
        else:
            ai_reply = "Por favor, selecciona una pestaña válida (Planes, Soporte o Cobertura) para poder procesar tu requerimiento de forma exacta."

        # -----------------------------------------------------------------
        # BLOQUE OPCIONAL: LLAMADA A TU CLIENTE DE GROQ (SI ESTÁ CONFIGURADO)
        # -----------------------------------------------------------------
        # Si prefieres que Groq genere el texto final en lugar de usar las respuestas estáticas:
        # if GROQ_CLIENT:
        #     completion = GROQ_CLIENT.chat.completions.create(
        #         model="llama3-8b-8192",
        #         messages=[
        #             {"role": "system", "content": f"Eres Lia de Litium IA. Contexto actual: {info_planes}. Modo activo: {mode}."},
        #             {"role": "user", "content": user_message}
        #         ]
        #     )
        #     ai_reply = completion.choices[0].message.content

        return ChatResponse(
            response=ai_reply,
            show_form=should_trigger_form,
            form_title=f_title,
            form_subtitle=f_subtitle,
            form_context=f_context
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo crítico en el motor conversacional: {str(e)}")
