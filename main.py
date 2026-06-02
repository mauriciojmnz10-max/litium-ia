import os
import logging
import requests
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from datetime import datetime, timedelta

# 1. LOGS Y CONFIGURACIÓN
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Litium Fibra Óptica - API de Ventas y Soporte", version="1.0.0")

# Configuración masiva de CORS para permitir peticiones desde GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que cualquier frontend se conecte de forma segura en la nube
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. INVENTARIO MAESTRO COMERCIAL DE LITIUM
PLANES_LITIUM = [
    {
        "id": "l1",
        "nombre": "Plan Hogar Inicial",
        "velocidad": "100 Mbps",
        "precio": 25,
        "emoji": "🌐",
        "descripcion": "Ideal para navegación básica, redes sociales y tareas escolares."
    },
    {
        "id": "l2",
        "nombre": "Plan Hogar Pro",
        "velocidad": "300 Mbps",
        "precio": 40,
        "emoji": "⚡",
        "descripcion": "Ideal para streaming en 4K, teletrabajo y sesiones de gaming estables."
    },
    {
        "id": "l3",
        "nombre": "Plan Litium Simétrico",
        "velocidad": "600 Mbps",
        "precio": 60,
        "emoji": "🚀",
        "descripcion": "Ultra velocidad simétrica ideal para creadores de contenido y múltiples dispositivos."
    },
    {
        "id": "l4",
        "nombre": "Plan Empresarial Dedicado",
        "velocidad": "1 Gbps (1000 Mbps)",
        "precio": 0,
        "emoji": "🏢",
        "descripcion": "Enlace dedicado corporativo. Precio a consultar según factibilidad técnica."
    }
]

# 3. SISTEMA CAMBIARIO AUTOMATIZADO CON CACHÉ (MONITOR BCV)
cache_bcv = {"valor": None, "ultima_actualizacion": None}

def obtener_tasa_bcv():
    ahora = datetime.now()
    if cache_bcv["valor"] and cache_bcv["ultima_actualizacion"] > ahora - timedelta(minutes=30):
        return cache_bcv["valor"]
    
    url_primaria = "https://ve.dolarapi.com/v1/dolares/oficial"
    try:
        respuesta = requests.get(url_primaria, timeout=3)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            valor = datos.get("promedio") or datos.get("precio") or datos.get("valor")
            if valor:
                cache_bcv.update({"valor": float(valor), "ultima_actualizacion": ahora})
                logger.info(f"Tasa BCV actualizada desde API primaria: {valor}")
                return float(valor)
    except Exception as e:
        logger.warning(f"Fallo en API primaria de divisas: {e}")
        
    # Ultra-Fallback de seguridad ante caídas de la red cambiaria en Venezuela
    fallback_seguro = cache_bcv["valor"] or 60.00
    logger.warning(f"Usando tasa de contingencia del sistema: {fallback_seguro}")
    return fallback_seguro

# Ajustada a /api/tasa para engranar con el frontend
@app.get("/api/tasa")
async def get_tasa_bcv():
    try:
        tasa = obtener_tasa_bcv()
        return {"tasa": tasa, "estatus": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al recuperar la cotización de divisas.")

# 4. MODELO DE DATOS PARA CHAT INTERACTIVO
class MensajeEstructura(BaseModel):
    message: str  # Cambiado de 'mensaje' a 'message' para calzar con el JSON enviado por el JS
    historial: list = []
    modo_asesor: str = "ventas"  # Opciones: 'ventas', 'soporte', 'cobertura'

# 5. CORE ENDPOINT - PROCESAMIENTO CON IA GROQ (LIA)
# Ajustada a /api/chat para solventar el error 404 de la consola
@app.post("/api/chat")
async def procesar_chat(datos_chat: MensajeEstructura):
    try:
        tasa_bcv = obtener_tasa_bcv()
        api_key_groq = os.environ.get("GROQ_API_KEY")
        if not api_key_groq:
            raise HTTPException(
                status_code=500, 
                detail="Error de configuración: GROQ_API_KEY no encontrada en las variables de entorno."
            )
            
        client = Groq(api_key=api_key_groq)
        
        modo = datos_chat.modo_asesor.lower()
        if modo not in ["ventas", "soporte", "cobertura"]:
            modo = "ventas"

        # Inyección contextual dinámica basada en la selección de pestaña del cliente
        if modo == "ventas":
            contexto_especifico = f"""Tu rol actual es VENTAS. Promueve de forma sutil, corporativa y elegante nuestro catálogo de planes.
            Catálogo Comercial Litium disponible en base de datos:
            {json.dumps(PLANES_LITIUM, ensure_ascii=False)}
            Instrucción comercial: Explica los beneficios de la alta velocidad y simetría. Si te preguntan por el Plan Empresarial de 1 Gbps, indícales de forma persuasiva que requiere factibilidad personalizada y que un ejecutivo lo cotizará de inmediato por WhatsApp."""
        elif modo == "soporte":
            contexto_especifico = """Tu rol actual es SOPORTE TÉCNICO BÁSICO. Ayuda con empatía corporativa.
            Flujo de diagnóstico de fallas permitido:
            1. Solicita amablemente validar si las luces del módem de fibra (ONT) están en verde o si hay alguna luz roja (LOS) encendida.
            2. Recomienda el reinicio básico de hardware: apagar el router y la ONT por 30 segundos y encenderlos nuevamente.
            3. Si la falla persiste o reportan rotura de cable de fibra, indícales que recopilarás sus datos para transferirlos al equipo técnico de campo de nivel 2 mediante WhatsApp."""
        else:
            contexto_especifico = """Tu rol actual es COBERTURA Y FACTIBILIDAD. Nos especializamos en CARACAS y MARACAY.
            Zonas activas de cobertura en nuestra red principal:
            - CARACAS: Chacao, Altamira, Las Mercedes, El Cafetal, La Candelaria, Sabana Grande, Los Dos Caminos, El Hatillo.
            - MARACAY: Las Delicias, El Limón, San Jacinto, Base Aragua, Centro de Maracay, La Soledad.
            Instrucción operativa: Si el usuario te nombra una zona de estas ciudades, confírmale con total entusiasmo que contamos con nodos troncales activos. Si nombra otra zona o estado, dile que tu sistema requiere las coordenadas exactas o dirección en texto para que el equipo de ingeniería realice la verificación por mapa de cobertura vía WhatsApp."""

        prompt_sistema = f"""
        Eres Lia, la asesora virtual inteligente oficial de Litium, la empresa líder en soluciones de conectividad por internet de Fibra Óptica en Caracas y Maracay.
        Tu tono es impecablemente corporativo, tecnológico, elegante, claro y altamente persuasivo. No eres un bot robótico común, eres una ejecutiva de nivel de negocios.

        CONTEXTO ECONÓMICO ACTUAL EN VENEZUELA:
        - Tasa Oficial de Referencia BCV: {tasa_bcv} Bs./$

        REGLA DE CÁLCULO ESTRICTA Y MANDATORIA:
        Cada vez que el usuario consulte por el precio de un plan, hagas una cotización o indiques una tarifa en dólares ($), debes obligatoriamente calcular en tiempo real y mostrar el contravalor exacto en Bolívares usando la tasa de {tasa_bcv}.
        Ejemplo obligatorio de redacción numérica: "El Plan Hogar Pro de 300 Mbps tiene una mensualidad de $40 ({40 * tasa_bcv:.2f} Bs.) ⚡". Haz la multiplicación aritmética exacta.

        DIRECTRICES DE OPERACIÓN DE LIA:
        1. {contexto_especifico}
        2. Siempre mantén una postura proactiva orientada a la resolución o a la conversión. Usa emojis tecnológicos limpios de forma sofisticada (⚡, 🌐, 🚀, 🏢, 💻).
        3. Nunca inventes planes, velocidades falsas ni rangos de precios fuera de la estructura corporativa inyectada.
        """

        mensajes_procesamiento = [{"role": "system", "content": prompt_sistema}]
        for m in datos_chat.historial[-8:]:
            mensajes_procesamiento.append(m)
        mensajes_procesamiento.append({"role": "user", "content": datos_chat.message})

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensajes_procesamiento,
            temperature=0.4,
            max_tokens=700
        )

        respuesta_ia = completion.choices[0].message.content

        # LÓGICA INTELIGENTE DE DISPARO DE LEAD (TRIGGER WHATSAPP)
        disparadores_leads = [
            "comprar", "contratar", "precio", "cuánto cuesta", "factibilidad", "cobertura", 
            "chacao", "delicias", "falla", "luz roja", "soporte", "interesado", "adquirir", "instalar"
        ]
        activar_ws = any(palabra in datos_chat.message.lower() or palabra in respuesta_ia.lower() for palabra in disparadores_leads)

        # Cambiado a 'reply' y 'whatsapp_button' para emparejar con el JavaScript del frontend
        return {"reply": respuesta_ia, "whatsapp_button": activar_ws}

    except Exception as e:
        logger.error(f"Error crítico en procesamiento de chat para Litium: {e}")
        raise HTTPException(status_code=500, detail="Error interno del motor de inteligencia artificial.")
