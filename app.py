import streamlit as st
import google.generativeai as genai
import pypdf
import json
import requests

# --- CONFIGURACIÓN DE INTERFAZ PREMIUM HGC ---
st.set_page_config(page_title="HGC - Evaluación de Especialidad", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; }
    [data-testid="stSidebar"] { background-color: #1E1E1E !important; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    .main * { color: #000000 !important; }
    .stButton>button { background-color: #B87333 !important; color: white !important; font-weight: bold; border-radius: 8px; }
    h1, h2, h3 { color: #5D4037 !important; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; border: 1px solid #B87333; }
    </style>
    """, unsafe_allow_html=True)

# --- URL DE TU BASE DE DATOS (GOOGLE SHEETS) ---
URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

# --- PANEL DE CONTROL ---
with st.sidebar:
    st.header("📋 Registro Académico")
    nombre_residente = st.text_input("Nombre Completo")
    grado_residente = st.selectbox("Grado Académico", ["R1", "R2", "R3", "R4 (Jefe)"])
    api_key = st.text_input("Gemini API Key", type="password").strip()
    pdf_file = st.file_uploader("Subir Literatura Técnica (PDF)", type="pdf")

st.title("🏥 Ramale Exam Center v3.0")
st.write(f"**Hospital General de Culiacán** | Jefatura de Residentes")

# --- MOTOR DE GENERACIÓN ---
if pdf_file and api_key and nombre_residente:
    try:
        genai.configure(api_key=api_key)
        
        # --- BUSCADOR DINÁMICO DE MODELO (SOLUCIÓN AL 404) ---
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in available_models if "flash" in m), available_models[0])
        model = genai.GenerativeModel(model_name)
        
        reader = pypdf.PdfReader(pdf_file)
        texto_base = "\n".join([page.extract_text() for page in reader.pages[:15]])

        if st.button("🚀 INICIAR EXAMEN DE GRADO"):
            with st.spinner(f"Usando motor {model_name} para nivel Consejo..."):
                prompt = f"""
                Actúa como un Sinodal de Cirugía Plástica experto. 
                Basado en este contenido: {texto_base[:12000]}
                Genera EXACTAMENTE 9 preguntas de opción múltiple.
                - 3 Sencillas (Anatomía/Conceptos básicos)
                - 3 Moderadas (Técnica/Planificación)
                - 3 Difíciles (Complicaciones/Casos complejos)
                Responde ÚNICAMENTE con este formato JSON:
                [
                  {{
                    "id": 1,
                    "nivel": "Sencilla",
                    "pregunta": "...",
                    "opciones": ["A) ...", "B) ...", "C) ...", "D) ..."],
                    "correcta": "A",
                    "justificacion": "..."
                  }}
                ]
                """
                response = model.generate_content(prompt)
                raw_json = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.examen_data = json.loads(raw_json)
                st.session_state.user_answers = {}
                st.success("Examen generado correctamente.")

    except Exception as e:
        st.error(f"Error en el sistema: {e}")

# --- DESPLIEGUE Y EVALUACIÓN ---
if 'examen_data' in st.session_state:
    st.markdown("---")
    for item in st.session_state.examen_data:
        st.markdown(f"**[{item['nivel']}] {item['id']}. {item['pregunta']}**")
        st.session_state.user_answers[item['id']] = st.radio(
            "Seleccione:", item['opciones'], key=f"radio_{item['id']}", label_visibility="collapsed"
        )
        st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📊 FINALIZAR Y NOTIFICAR A JEFATURA"):
        stats = {"Sencilla": 0, "Moderada": 0, "Difícil": 0}
        log_errores = []

        for item in st.session_state.examen_data:
            idx = ord(item['correcta']) - 65
            texto_correcto = item['opciones'][idx]
            if st.session_state.user_answers[item['id']] == texto_correcto:
                stats[item['nivel']] += 1
            else:
                log_errores.append(f"P{item['id']} ({item['nivel']}): {item['justificacion']}")

        total_aciertos = sum(stats.values())
        nota_final = round((total_aciertos / 9) * 10, 1)
        detalles_texto = " | ".join(log_errores) if log_errores else "Sin errores."

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
            requests.post(URL_SHEET, json=payload)
            st.success(f"✅ Reporte enviado a la Dra. Rafaela.")
        except:
            st.warning("⚠️ Error de envío a la nube.")

        st.header(f"Calificación Final: {nota_final}/10")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sencillas", payload["sencillas"])
        c2.metric("Moderadas", payload["moderadas"])
        c3.metric("Difíciles", payload["dificiles"])
        
        if log_errores:
            st.subheader("Retroalimentación Técnica:")
            for err in log_errores:
                st.info(err)
