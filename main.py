import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Litium IA Core - MultiKAP Suite")

# CORS configurado para tu entorno en GitHub Pages
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

# Base de datos de cobertura lógica para validación rápida
ZONAS_COBERTURA_OK = ["caricuao", "ruiz pineda", "los telares", "ud7", "cumana", "centro"]

# Teléfono del equipo de ventas (Formato internacional sin el +)
WHATSAPP_ASESOR = "584120000000" 

class FormLeadRequest(BaseModel):
    name: str
    phone: str
    location: str
    context: str

@app.post("/api/formulario")
async def procesar_formulario_lead(request: FormLeadRequest):
    loc_lower = request.location.lower()
    tiene_cobertura = any(zona in loc_lower for zona in ZONAS_COBERTURA_OK)
    
    # Formateamos el mensaje que se enviará prellenado a WhatsApp
    text_whatsapp = f"Hola, vengo desde la web de Litium IA. Mi nombre es {request.name}. Ya validé mi zona ({request.location}) y deseo coordinar la instalación de mi plan de internet."
    text_encoded = text_whatsapp.replace(" ", "%20")
    ws_link = f"https://wa.me/{WHATSAPP_ASESOR}?text={text_encoded}"

    if tiene_cobertura:
        mensaje_lia = (
            f"✨ **¡Excelente, {request.name}!** He verificado tu sector (*{request.location}*) y nuestro sistema indica que "
            f"contamos con nodos de fibra óptica activos en la zona. Veo que estás listo para dar el salto a la velocidad Litium. "
            f"\n\nPara proceder con la contratación y agendar tu visita técnica, dale clic al botón de abajo para transferirte "
            f"con uno de nuestros **Asesores de Venta Humanos** en WhatsApp de inmediato."
        )
        return {
            "status": "aprobado",
            "cobertura": True,
            "response": mensaje_lia,
            "whatsapp_link": ws_link
        }
    else:
        # En caso de no tener cobertura, retenemos el lead amablemente
        mensaje_espera = (
            f"📍 **Gracias por tu interés, {request.name}.** Analicé tu ubicación (*{request.location}*) y actualmente "
            f"estamos construyendo la red para llegar a tu sector. He guardado tus datos de manera prioritaria en nuestra lista de expansión. "
            f"Te notificaremos apenas encendamos el servicio en tu calle."
        )
        return {
            "status": "lista_espera",
            "cobertura": False,
            "response": mensaje_espera,
            "whatsapp_link": None
        }
