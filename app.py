import streamlit as st
import google.generativeai as genai
import pypdf
import json
import requests

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Ramale Exam Center", page_icon="🎓", layout="wide")

# --- 2. ESTILOS CSS PERSONALIZADOS (AZUL NAVY, DORADO, BLANCO) ---
st.markdown("""
    <style>
    /* Fondo principal marfil claro */
    .stApp { 
        background-color: #FAF9F6 !important; 
    }
    
    /* Barra lateral Azul Navy */
    [data-testid="stSidebar"] { 
        background-color: #001F5B !important; 
    }
    [data-testid="stSidebar"] * { 
        color: #FFFFFF !important; 
    }
    
    /* BOTÓN PRINCIPAL DORADO */
    div.stButton > button { 
        background-color: #D4AF37 !important; 
        color: #001F5B !important; 
        font-weight: bold !important; 
        border-radius: 8px !important;
        border: 2px solid #D4AF37 !important;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover { 
        background-color: #FFFFFF !important; 
        color: #D4AF37 !important; 
    }
    
    /* TEXTO DEL EXAMEN: NEGRO INTENSO PARA LECTURA CLARA */
    .main * { 
        color: #000000 !important; 
    }
    
    /* Títulos Azul Navy con tipografía elegante */
    h1, h2, h3, h4 { 
        color: #001F5B !important; 
        font-family: 'Georgia', serif !important;
    }
    
    /* Estilo de los Radio Buttons y etiquetas */
    div[data-testid="stMarkdownContainer"] p, 
    div[data-testid="stWidgetLabel"] p { 
        color: #000000 !important; 
        font-size: 18px !important;
    }
    
    /* Caja de métricas de resultados */
    [data-testid="stMetricValue"] {
        color: #001F5B !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONFIGURACIÓN DE ENDPOINTS (GOOGLE SHEETS) ---
URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

# --- 4. BARRA LATERAL CON LOGOTIPO POR DEFAULT ---
with st.sidebar:
    # Enlace directo al archivo Raw en tu GitHub
    logo_default = "https://raw.githubusercontent.com/carloscpr2903-boop/mi-examen-ia/main/Logotipo%20Principal%20Sin%20Fondo%20(1).png"
    st.image(logo_default, use_container_width=True)
    
    st.markdown("---")
    st.header("📋 Datos del Residente")
    nombre_residente = st.text_input("Nombre Completo")
    grado_residente = st.selectbox("Grado Académico", ["R1", "R2", "R3", "R4 (Jefe)"])
    api_key = st.text_input("Gemini API Key", type="password").strip()
    pdf_file = st.file_uploader("Subir Literatura Técnica (PDF)", type="pdf")

st.title("🎓 Ramale Exam Center v3.1")
st.write(f"**Hospital General de Culiacán** | Especialidad en Cirugía Plástica y Reconstructiva")

# --- 5. LÓGICA DE GENERACIÓN ---
if pdf_file and api_key and nombre_residente:
    try:
        genai.configure(api_key=api_key)
        
        # Auto-detección de modelos disponibles
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in models if "flash" in m), models[0])
        model = genai.GenerativeModel(model_name)
        
        reader = pypdf.PdfReader(pdf_file)
        texto_base = "\n".join([page.extract_text() for page in reader.pages[:15]])

        if st.button("🚀 INICIAR EVALUACIÓN DE GRADO"):
            with st.spinner("Procesando literatura y diseñando reactivos..."):
                prompt = f"""
                Eres un Sinodal experto. Basado en este contenido: {texto_base[:12000]}
                Genera 9 preguntas de opción múltiple (3 Sencillas, 3 Moderadas, 3 Difíciles).
                REGLAS:
                - No uses 'según el texto'. Habla con autoridad médica.
                - Formato JSON ESTRICTO:
                [
                  {{
                    "id": 1,
                    "nivel": "Sencilla",
                    "pregunta": "...",
                    "opciones": ["A) Opción 1", "B) Opción 2", "C) Opción 3", "D) Opción 4"],
                    "correcta": "A",
                    "justificacion": "..."
                  }}
                ]
                """
                response = model.generate_content(prompt)
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.examen_data = json.loads(clean_json)
                st.session_state.user_answers = {}
                st.success("Examen generado. Responda con precisión quirúrgica.")

    except Exception as e:
        st.error(f"Error de sistema: {e}")

# --- 6. DESPLIEGUE DEL EXAMEN ---
if 'examen_data' in st.session_state:
    st.markdown("---")
    for q in st.session_state.examen_data:
        st.markdown(f"#### [{q['nivel']}] {q['id']}. {q['pregunta']}")
        st.session_state.user_answers[q['id']] = st.radio(
            "Seleccione su respuesta:", 
            q['opciones'], 
            key=f"q_{q['id']}", 
            label_visibility="collapsed"
        )
        st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📊 FINALIZAR Y NOTIFICAR A JEFATURA"):
        stats = {"Sencilla": 0, "Moderada": 0, "Difícil": 0}
        log_errores = []

        for q in st.session_state.examen_data:
            # Calificación por texto exacto para evitar errores de letra
            idx_correcta = ord(q['correcta']) - 65
            texto_correcto = q['opciones'][idx_correcta]
            
            if st.session_state.user_answers[q['id']] == texto_correcto:
                stats[q['nivel']] += 1
            else:
                log_errores.append(f"P{q['id']} ({q['nivel']}): {q['justificacion']}")

        nota_final = round((sum(stats.values()) / 9) * 10, 1)
        detalles_texto = " | ".join(log_errores) if log_errores else "Sin errores."

        # Preparar envío a la Dra. Rafaela
        payload = {
            "nombre": nombre_residente,
            "grado": grado_residente,
            "calificacion": nota_final,
            "sencillas": f"{stats['Sencilla']}/3",
            "moderadas": f"{stats['Moderada']}/3",
            "dificiles": f"{stats['Difícil']}/3",
            "detalles_errores": detalles_texto
        }

        try:
            requests.post(URL_SHEET, json=payload, timeout=10)
            st.success(f"✅ Evaluación finalizada. Reporte enviado a la Dra. Rafaela.")
        except:
            st.warning("⚠️ Los resultados se calcularon, pero hubo un problema de conexión con la base de datos.")

        # Resultados en pantalla
        st.header(f"Calificación Final: {nota_final}/10")
        c1, c2, c3 = st.columns(3)
        c1.metric("Nivel Sencillo", payload["sencillas"])
        c2.metric("Nivel Moderado", payload["moderadas"])
        c3.metric("Nivel Difícil", payload["dificiles"])
        
        if log_errores:
            st.subheader("Retroalimentación Técnica:")
            for err in log_errores:
                st.info(err)
        else:
            st.balloons()
