import streamlit as st
import google.generativeai as genai
import pypdf
import json
import requests

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="HGC - Cirugía Plástica", page_icon="🏦", layout="wide")

# --- 2. ESTILOS CSS BLINDADOS (SERIEDAD ACADÉMICA) ---
st.markdown("""
    <style>
    /* Fondo principal marfil claro */
    .stApp { background-color: #FAF9F6 !important; }
    
    /* === BARRA LATERAL (SIDEBAR) === */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(255,255,255,1) 15%, rgba(0,31,91,1) 25%, rgba(0,31,91,1) 100%) !important;
        border-right: 1px solid #D4AF37 !important;
    }
    
    /* Contraste forzado para textos en la Sidebar (Azul Navy de fondo) */
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 { 
        color: #FFFFFF !important; 
        font-weight: 500 !important;
    }
    
    /* Excepción: Título de 'Registro' en Dorado */
    [data-testid="stSidebar"] h2#registro {
        color: #D4AF37 !important;
    }

    /* === ÁREA PRINCIPAL === */
    /* Texto del Examen: NEGRO INTENSO */
    .main * { color: #000000 !important; }
    
    /* Títulos Institucionales Azul Navy */
    h1, h2, h3, h4 { 
        color: #001F5B !important; 
        font-family: 'Georgia', serif !important;
        font-weight: bold !important;
    }
    
    /* BOTÓN PRINCIPAL DORADO */
    div.stButton > button { 
        background-color: #D4AF37 !important; 
        color: #001F5B !important; 
        font-weight: bold !important; 
        border-radius: 4px !important;
        border: 2px solid #D4AF37 !important;
        width: 100%;
        transition: 0.3s;
        text-transform: uppercase;
    }
    div.stButton > button:hover { 
        background-color: #FFFFFF !important; 
        color: #D4AF37 !important; 
    }
    
    /* Visibilidad de Radio Buttons y Preguntas (Negro) */
    div[data-testid="stMarkdownContainer"] p, 
    div[data-testid="stWidgetLabel"] p { 
        color: #000000 !important; 
        font-size: 19px !important;
        line-height: 1.6 !important;
    }
    
    /* Estilo de la Justificación (Retroalimentación) */
    .stInfo {
        background-color: #e3f2fd !important;
        color: #0d47a1 !important;
        border-left: 5px solid #D4AF37 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. URL DE TU GOOGLE SHEET (Dra. Rafaela) ---
URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

# --- 4. BARRA LATERAL CON LOGO DIFUMINADO ---
with st.sidebar:
    # Contenedor del logo con fondo blanco (el CSS maneja el gradiente)
    logo_url = "https://raw.githubusercontent.com/carloscpr2903-boop/mi-examen-ia/main/Logotipo%20Principal%20Sin%20Fondo%20(1).png"
    st.image(logo_url, use_container_width=True)
    
    st.markdown("<br><h2 id='registro' style='text-align:center;'>REGISTRO</h2>", unsafe_allow_html=True)
    nombre = st.text_input("Nombre Completo del Residente")
    grado = st.selectbox("Grado Académico", ["R1", "R2", "R3", "R4 (Jefe)"])
    api_key = st.text_input("Gemini API Key", type="password").strip()
    pdf_file = st.file_uploader("Cargar Literatura Base (PDF)", type="pdf")

# --- 5. TÍTULO INSTITUCIONAL (SIN ICONOS GENERIQUOS) ---
st.markdown("<h1 style='text-align: center; font-size: 32px;'>HGC - EVALUACIÓN DE ALTA ESPECIALIDAD EN CIRUGÍA PLÁSTICA Y RECONSTRUCTIVA</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #D4AF37 !important;'>División de Estudios de Posgrado e Investigación</h3>", unsafe_allow_html=True)
st.markdown("---")

# --- 6. LÓGICA DE GENERACIÓN AUTÓNOMA ---
if pdf_file and api_key and nombre:
    try:
        genai.configure(api_key=api_key)
        # Auto-detección de modelo disponible
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in models if "flash" in m), models[0])
        model = genai.GenerativeModel(model_name)
        
        # Procesar PDF (Primeras 20 páginas para contexto técnico)
        reader = pypdf.PdfReader(pdf_file)
        texto = "\n".join([p.extract_text() for p in reader.pages[:20]])

        if st.button("🚀 GENERAR EVALUACIÓN DE GRADO"):
            with st.spinner("Analizando literatura quirúrgica y diseñando reactivos..."):
                prompt = f"""
                Genera 9 preguntas de opción múltiple nivel Consejo basadas en: {texto[:14000]}
                Estructura: 3 Sencillas, 3 Moderadas, 3 Difíciles. 
                REGLAS DE SEGURIDAD:
                1. No uses frases como 'según el texto' o 'basado en el autor'. Habla con autoridad clínica.
                2. Formato JSON ESTRICTO: 
                [
                  {{
                    "id":1, 
                    "nivel":"Sencilla", 
                    "pregunta":"...", 
                    "opciones":["A)...","B)...","C)...","D)..."], 
                    "correcta":"A", 
                    "justificacion":"..."
                  }}
                ]
                """
                res = model.generate_content(prompt)
                st.session_state.examen_data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.answers = {}
                st.success("Evaluación generada con éxito. Responda con precisión.")
    except Exception as e:
        st.error(f"Error en la conexión con la IA: {e}")

# --- 7. EXAMEN Y EVALUACIÓN (LIMPIEZA DE PREGUNTAS) ---
if 'examen_data' in st.session_state:
    for item in st.session_state.examen_data:
        # Pregunta limpia (sin prefijo de dificultad)
        st.markdown(f"#### {item['id']}. {item['pregunta']}")
        st.session_state.answers[item['id']] = st.radio(
            "Seleccione:", 
            item['opciones'], 
            key=f"r_{item['id']}", 
            label_visibility="collapsed"
        )
        st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📊
