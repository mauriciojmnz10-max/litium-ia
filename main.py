import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Inicialización de la App
app = FastAPI(
    title="Litium IA Backend",
    description="Ecosistema de automatización para conectividad de fibra óptica bajo el entorno MultiKAP",
    version="1.0.0"
)

# =====================================================================
# 1. CONFIGURACIÓN DE SEGURIDAD (CORS)
# =====================================================================
# Añadimos los orígenes autorizados para destruir el error de bloqueo del navegador.
origins = [
    "https://mauriciojmnz10-max.github.io",  # Frontend en producción (GitHub Pages)
    "http://localhost:5500",                # Pruebas locales con Live Server
    "http://127.0.0.1:5500",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos: OPTIONS, GET, POST, etc.
    allow_headers=["*"],  # Permite todos los headers personalizados
)

# =====================================================================
# 2. MODELOS DE DATOS (Pydantic)
# =====================================================================
class ChatRequest(BaseModel):
    message: str
    mode: str  # 'ventas', 'soporte' o 'cobertura'

class ChatResponse(BaseModel):
    response: str
    show_form: bool
    form_title: Optional[str] = None
    form_subtitle: Optional[str] = None
    form_context: Optional[str] = None

# =====================================================================
# 3. ENDPOINTS / RUTAS DE LA API
# =====================================================================

@app.get("/")
def read_root():
    """
    Ruta raíz obligatoria.
    Evita que Render marque el despliegue con error (404) durante el Health Check.
    """
    return {
        "status": "online",
        "ecosystem": "MultiKAP",
        "service": "Litium IA Core Engine"
    }


@app.get("/api/tasa")
async def get_tasa_bcv():
    """
    Endpoint para proveer la tasa oficial del BCV al navbar del frontend.
    Modifica el valor de retorno con tu lógica de scraping o consumo automatizado.
    """
    try:
        # Tasa base simulada (Ajusta con tu scraper o integración real cuando sea necesario)
        tasa_actual = 36.52
        return {"tasa": tasa_actual}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la tasa cambiaria: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_handler(request: ChatRequest):
    """
    Procesador inteligente de interacciones con Lia.
    Administra la lógica de negocio segmentada por el modo activo del usuario.
    """
    user_message = request.message.strip()
    mode = request.mode.lower()

    if not user_message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    try:
        # -----------------------------------------------------------------
        # BLOQUE DE CONTEXTO SE SEGÚN EL MODO SELECCIONADO
        # -----------------------------------------------------------------
        # Aquí puedes integrar la llamada a la API de Groq / DeepSeek / Llama.
        # Pasándole este contexto en el 'system prompt'.
        
        system_prompt = ""
        ai_reply = ""
        should_trigger_form = False
        
        # Variables de configuración para el formulario si se activa
        f_title = None
        f_subtitle = None
        f_context = None

        if mode == "ventas":
            system_prompt = "Eres Lia, asesora comercial de Litium. Tu meta es vender planes de fibra óptica (Hogar 200Mbps por $25, Pro 500Mbps por $40, Corp 1Gbps por $80). Sé persuasiva y concisa."
            
            # Lógica de ejemplo: Si el usuario muestra intención directa de contratar, disparamos el formulario
            intenciones_compra = ["contratar", "adquirir", "comprar", "quiero el plan", "me interesa el plan"]
            if any(palabra in user_message.lower() for palabra in intenciones_compra):
                ai_reply = "¡Excelente elección! Para proceder con el alta del servicio y agilizar tu orden en el sistema, por favor completa el formulario que acabo de desplegar en tu pantalla. Uno de nuestros consultores validará la información de inmediato."
                should_trigger_form = True
                f_title = "Solicitud de Alta de Servicio"
                f_subtitle = "Introduce tus datos de contacto para procesar la contratación."
                f_context = f"El cliente solicita contratación rápida desde el asistente de IA. Mensaje de origen: '{user_message}'"
            else:
                ai_reply = "Ofrecemos velocidades simétricas estables ideales para streaming y gaming. ¿Cuál de nuestros planes se adapta mejor a lo que estás buscando hoy?"

        elif mode == "soporte":
            system_prompt = "Eres Lia de Soporte Técnico de Litium. Ayuda al usuario a diagnosticar problemas de conectividad (luces del router, reinicios, lentitud) con un tono calmado, técnico y eficiente."
            
            intenciones_soporte = ["caido", "sin internet", "no navega", "luz roja", "falla", "averia"]
            if any(palabra in user_message.lower() for palabra in intenciones_soporte):
                ai_reply = "Entiendo perfectamente la urgencia de tu caso. He abierto una pestaña de asistencia técnica especializada debajo. Completa los datos solicitados para generar tu ticket de soporte prioritario de inmediato."
                should_trigger_form = True
                f_title = "Reporte de Incidencia Técnica"
                f_subtitle = "Describe tu falla para asignar un técnico de guardia."
                f_context = f"Reporte técnico automatizado. El usuario experimenta incidencias: '{user_message}'"
            else:
                ai_reply = "Por favor, indícame si la luz 'LOS' de tu equipo óptico parpadea en color rojo, o si la lentitud ocurre en todos tus dispositivos para guiarte en el descarte."

        elif mode == "cobertura":
            system_prompt = "Eres Lia, encargada de verificar la cobertura de fibra de Litium. Tu objetivo es mapear la dirección del usuario."
            
            ai_reply = "Actualmente contamos con nodos activos de fibra de alta velocidad en sectores estratégicos de Caracas (como Caricuao, Ruiz Pineda, Los Telares) y zonas céntricas de Cumaná. Por favor, indícame tu calle o punto de referencia exacto, o rellena el formulario de factibilidad si deseas que verifiquemos tu zona de forma manual."
            
            # El modo cobertura puede ofrecer el formulario opcionalmente si el usuario lo pide
            if "verificar" in user_message.lower() or "vivo en" in user_message.lower():
                should_trigger_form = True
                f_title = "Estudio de Factibilidad Óptica"
                f_subtitle = "Comprobaremos si nuestros hilos de fibra llegan a tu dirección exacta."
                f_context = f"Validación geográfica solicitada para la dirección: '{user_message}'"

        else:
            ai_reply = "Disculpa, no reconozco el modo de operación seleccionado. ¿Podrías indicarme si deseas consultar planes, reportar una falla o validar tu cobertura?"

        # -----------------------------------------------------------------
        # RETORNO ESTRUCTURADO HACIA EL FRONTEND
        # -----------------------------------------------------------------
        return ChatResponse(
            response=ai_reply,
            show_form=should_trigger_form,
            form_title=f_title,
            form_subtitle=f_subtitle,
            form_context=f_context
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el motor de IA del Chat: {str(e)}")
