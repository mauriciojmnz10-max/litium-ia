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

# 2. INVENTARIO MAESTRO COMERCIAL DE LITIUM (Alineado con los planes del frontend)
PLANES_LITIUM = [
    {
        "id": "l1",
        "nombre": "Plan Hogar",
        "velocidad": "200 Mbps",
        "precio": 25,
        "emoji": "🌐",
        "descripcion": "Ideal para streaming 4K, teletrabajo y navegación familiar sin interrupciones."
    },
    {
        "id": "l2",
        "nombre": "Plan Pro",
        "velocidad": "500 Mbps",
        "precio": 40,
        "emoji": "⚡",
        "descripcion": "Para gamers, creadores de contenido y múltiples dispositivos en simultáneo."
    },
    {
        "id": "l3",
        "nombre": "Plan Corporativo Dedicated",
        "velocidad": "1 Gbps (1000 Mbps)",
        "precio": 80,
        "emoji": "🏢",
        "descripcion": "Enlace dedicado empresarial con soporte de ingeniería corporativo SLA 99.9%."
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
    message: str  
    historial: list = []
    modo_asesor: str = "ventas"  # Opciones: 'ventas', 'soporte', 'cobertura'

# 5. CORE ENDPOINT - PROCESAMIENTO CON IA GROQ (LIA)
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
            Instrucción comercial: Explica los beneficios de la alta velocidad y simetría. Si te preguntan por el Plan Corporativo de 1 Gbps, indícales de forma de asesoría que requiere una breve validación técnica y que un ejecutivo comercial especializado lo guiará de inmediato vía WhatsApp."""
        elif modo == "soporte":
            contexto_especifico = """Tu rol actual es SOPORTE TÉCNICO BÁSICO. Ayuda con empatía corporativa.
            Flujo de diagnóstico de fallas permitido:
            1. Solicita amablemente validar si las luces del módem de fibra (ONT) están en verde o si hay alguna luz roja (LOS) encendida.
            2. Recomienda el reinicio básico de hardware: apagar el router y la ONT por 30 segundos y encenderlos nuevamente.
            3. Si la falla persiste o reportan rotura de cable de fibra, indícales que recopilarás sus datos mediante el formulario de la página o los transferirás al equipo de soporte técnico de nivel 2 vía WhatsApp."""
        else:
            contexto_especifico = """Tu rol actual es COBERTURA Y FACTIBILIDAD. Nos especializamos en CARACAS y MARACAY.
            Zonas activas de cobertura en nuestra red principal:
            - CARACAS: Chacao, Altamira, Las Mercedes, El Cafetal, La Candelaria, Sabana Grande, Los Dos Caminos, El Hatillo.
            - MARACAY: Las Delicias, El Limón, San Jacinto, Base Aragua, Centro de Maracay, La Soledad.
            Instrucción operativa: Si el usuario te nombra una zona de estas ciudades, confírmale con total entusiasmo que contamos con hilos y nodos troncales activos. Si nombra otra zona o estado, indícale amablemente que use el Formulario de Factibilidad Técnica central de la web para mapear las coordenadas exactas de su dirección."""

        # Precalculamos los strings de precios de ejemplo para evitar romper la lógica del f-string
        ejemplo_calculo_hogar = f"$25 ({25 * tasa_bcv:.2f} Bs.)"
        ejemplo_calculo_pro = f"$40 ({40 * tasa_bcv:.2f} Bs.)"

        prompt_sistema = f"""
        Eres Lia, la asesora virtual inteligente oficial de Litium, la empresa líder en soluciones de conectividad por internet de Fibra Óptica en Caracas y Maracay.
        Tu tono es impecablemente corporativo, tecnológico, elegante, claro, altamente persuasivo, ejecutivo y empático. Hablas como una gerente de alto nivel, eres una ejecutiva de nivel de negocios.

        REGLA DE CÁLCULO MANDATORIA:
        Cada vez que indiques una tarifa en dólares ($), calcula y muestra el contravalor en Bolívares usando la tasa oficial de {tasa_bcv}. Ejemplo: "$40 ({40 * tasa_bcv:.2f} Bs.) ⚡".

        DIRECTRICES DE MANEJO AVANZADO DE ESCENARIOS (BLINDAJE TOTAL):
        
        1. MANEJO DE QUEJAS Y RECLAMOS FUERTES:
           Si un cliente se comunica molesto, insultando o diciendo que el servicio es deficiente, nunca te pongas a la defensiva ni uses respuestas robóticas. Adopta una postura de alta empatía institucional. Redacta así: "Comprendo perfectamente su inconformidad y la importancia de contar con un servicio estable. Para nuestra directiva en Litium, su conectividad es prioridad. Permítame iniciar un protocolo inmediato..." e introduce el diagnóstico técnico.

        2. MANEJO DE LA COMPETENCIA (Netuno, Inter, Fibex, Thundernet, etc.):
           Si el usuario menciona que otra compañía ofrece más megas por menos precio, resalta con elegancia el valor premium de Litium: "En Litium no competimos en masa de números, nos enfocamos en la pureza de la transmisión. Garantizamos Fibra Óptica 100% Simétrica (la misma velocidad para descargar que para subir videos o archivos masivos) mediante enlaces dedicados sin saturación de nodos locales, respaldados por ingeniería de campo 24/7."

        3. MANEJO DE ZONAS FUERA DE COBERTURA:
           Si te solicitan viabilidad para zonas populares o sectores donde la red aún no llega (ej. Petare, Catia, etc.), jamás respondas con un "No tenemos cobertura" directo. Responde con entusiasmo de expansión: "Nuestros hilos de fibra de alta velocidad están en constante despliegue por todo el territorio nacional. Aunque ese nodo específico está en fase de planificación, le invito a registrar sus datos en nuestro Formulario de Factibilidad Técnica en la web principal. Esto nos permite mapear la demanda y priorizar la apertura de fibra en su calle muy pronto."

        4. DIRECTRICES OPERATIVAS POR MODO:
           {contexto_especifico}

        CONTEXTO ECONÓMICO ACTUAL EN VENEZUELA:
        - Tasa Oficial de Referencia BCV: {tasa_bcv} Bs./$

        REGLA DE CÁLCULO ESTRICTA Y MANDATORIA:
        Cada vez que el usuario consulte por el precio de un plan, hagas una cotización o indiques una tarifa en dólares ($), debes obligatoriamente calcular en tiempo real y mostrar el contravalor exacto en Bolívares usando la tasa de {tasa_bcv}.
        Ejemplo obligatorio de redacción numérica: "El Plan Pro de 500 Mbps tiene una mensualidad de {ejemplo_calculo_pro} ⚡" o "El Plan Hogar de 200 Mbps tiene un costo de {ejemplo_calculo_hogar} 🌐". Haz la multiplicación aritmética exacta.

        DIRECTRICES DE OPERACIÓN DE LIA:
        1. Siempre mantén una postura proactiva orientada a la resolución o a la conversión. Usa emojis tecnológicos limpios de forma sofisticada (⚡, 🌐, 🚀, 🏢, 💻).
        2. Nunca inventes planes, velocidades falsas ni rangos de precios fuera de la estructura corporativa inyectada.
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

        return {"reply": respuesta_ia, "whatsapp_button": activar_ws}

    except Exception as e:
        logger.error(f"Error crítico en procesamiento de chat para Litium: {e}")
        raise HTTPException(status_code=500, detail="Error interno del motor de inteligencia artificial.")
