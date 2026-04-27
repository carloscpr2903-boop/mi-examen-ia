import streamlit as st
import google.generativeai as genai
import pypdf
import json
import requests

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="HGC - Cirugía Plástica", page_icon="🏦", layout="wide")

# --- 2. ESTILOS CSS (GRIS CLARO EN SIDEBAR Y GRADIENTE) ---
st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6 !important; }
    
    /* SIDEBAR: Gradiente y letras Gris Claro */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(255,255,255,1) 18%, rgba(0,31,91,1) 28%, rgba(0,31,91,1) 100%) !important;
        border-right: 1px solid #D4AF37 !important;
    }
    
    /* Letras en Gris Claro para mejor lectura sobre el Navy */
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 { 
        color: #D1D1D1 !important; 
        font-weight: 400 !important;
    }
    
    /* Registro en Dorado */
    [data-testid="stSidebar"] h2#registro { color: #D4AF37 !important; }

    /* ÁREA PRINCIPAL: Negro y Azul Navy */
    .main * { color: #000000 !important; }
    h1, h2, h3, h4 { 
        color: #001F5B !important; 
        font-family: 'Georgia', serif !important;
    }
    
    /* BOTÓN DORADO */
    div.stButton > button { 
        background-color: #D4AF37 !important; 
        color: #001F5B !important; 
        font-weight: bold !important; 
        border-radius: 4px !important;
        text-transform: uppercase;
    }
    
    /* TEXTO EXAMEN */
    div[data-testid="stMarkdownContainer"] p { 
        color: #000000 !important; 
        font-size: 19px !important;
    }
    </style>
    """, unsafe_allow_html=True)

URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

# --- 3. SIDEBAR ---
with st.sidebar:
    logo_url = "https://raw.githubusercontent.com/carloscpr2903-boop/mi-examen-ia/main/Logotipo%20Principal%20Sin%20Fondo%20(1).png"
    st.image(logo_url, use_container_width=True)
    st.markdown("<br><h2 id='registro' style='text-align:center;'>REGISTRO</h2>", unsafe_allow_html=True)
    nombre = st.text_input("Nombre del Residente")
    grado = st.selectbox("Grado", ["R1", "R2", "R3", "R4 (Jefe)"])
    api_key = st.text_input("Gemini API Key", type="password").strip()
    pdf_file = st.file_uploader("Cargar PDF Técnico", type="pdf")

st.markdown("<h1 style='text-align: center; font-size: 28px;'>HGC - EVALUACIÓN DE ALTA ESPECIALIDAD EN CIRUGÍA PLÁSTICA Y RECONSTRUCTIVA</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #D4AF37 !important;'>División de Estudios de Posgrado e Investigación</h3>", unsafe_allow_html=True)
st.markdown("---")

# --- 4. MOTOR IA ---
if pdf_file and api_key and nombre:
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in models if "flash" in m), models[0])
        model = genai.GenerativeModel(model_name)
        
        reader = pypdf.PdfReader(pdf_file)
        texto = "\n".join([p.extract_text() for p in reader.pages[:15]])

        if st.button("🚀 GENERAR EVALUACIÓN DE GRADO"):
            with st.spinner("Diseñando reactivos..."):
                prompt = f"Genera 9 preguntas nivel Consejo basadas en: {texto[:10000]}. 3 Sencillas, 3 Moderadas, 3 Difíciles. Sin frases genéricas. Responde solo JSON: [{{"id":1, "nivel":"Sencilla", "pregunta":"...", "opciones":["A)","B)","C)","D)"], "correcta":"A", "justificacion":"..."}}]"
                res = model.generate_content(prompt)
                st.session_state.examen_data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
                st.session_state.answers = {} # INICIALIZACIÓN CRÍTICA
                st.success("Examen generado.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 5. EXAMEN ---
if 'examen_data' in st.session_state:
    # Aseguramos que el diccionario exista antes de renderizar los radios
    if 'answers' not in st.session_state:
        st.session_state.answers = {}

    for item in st.session_state.examen_data:
        st.markdown(f"#### {item['id']}. {item['pregunta']}")
        st.session_state.answers[item['id']] = st.radio(
            "Seleccione:", item['opciones'], key=f"r_{item['id']}", label_visibility="collapsed"
        )
        st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📊 FINALIZAR Y ENVIAR A JEFATURA"):
        stats = {"Sencilla": 0, "Moderada": 0, "Difícil": 0}
        errores = []
        for item in st.session_state.examen_data:
            idx = ord(item['correcta']) - 65
            if st.session_state.answers.get(item['id']) == item['opciones'][idx]:
                stats[item['nivel']] += 1
            else:
                errores.append(f"**P{item['id']}**: {item['justificacion']}")

        nota = round((sum(stats.values()) / 9) * 10, 1)
        payload = {"nombre": nombre, "grado": grado, "calificacion": nota, "sencillas": f"{stats['Sencilla']}/3", "moderadas": f"{stats['Moderada']}/3", "dificiles": f"{stats['Difícil']}/3", "detalles_errores": " | ".join(errores)}
        
        try:
            requests.post(URL_SHEET, json=payload, timeout=10)
            st.success("✅ Reporte enviado a la Jefatura.")
        except:
            st.warning("⚠️ Error de conexión.")

        st.header(f"Resultado: {nota}/10")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sencillas", payload["sencillas"])
        c2.metric("Moderadas", payload["moderadas"])
        c3.metric("Difíciles", payload["dificiles"])
        if errores:
            for e in errores: st.info(e)
