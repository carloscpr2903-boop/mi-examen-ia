import streamlit as st
import google.generativeai as genai
import pypdf
import json
import requests

# --- INTERFAZ PREMIUM ---
st.set_page_config(page_title="HGC - Evaluación Plástica", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; }
    [data-testid="stSidebar"] { background-color: #1E1E1E !important; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    .main * { color: #000000 !important; }
    .stButton>button { background-color: #B87333 !important; color: white !important; font-weight: bold; border-radius: 8px; }
    .card { padding: 15px; border-radius: 10px; border-left: 5px solid #B87333; background-color: #fcfcfc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN ---
URL_SHEET = "URL_DE_TU_GOOGLE_SCRIPT" # <--- PEGA AQUÍ TU URLhttps://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec 

with st.sidebar:
    st.header("📋 Registro Académico")
    nombre = st.text_input("Nombre del Residente")
    grado = st.selectbox("Grado", ["R1", "R2", "R3", "R4"])
    api_key = st.text_input("Gemini API Key", type="password").strip()
    pdf_file = st.file_uploader("Literatura Base (PDF)", type="pdf")
    
st.title("🏥 Ramale Exam Center v3.0")
st.subheader("Evaluación de Alta Especialidad - HGC")

# --- LÓGICA ---
if pdf_file and api_key and nombre:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        reader = pypdf.PdfReader(pdf_file)
        full_text = "\n".join([p.extract_text() for p in reader.pages[:20]]) # Limitamos a 20 páginas por velocidad

        if st.button("🚀 INICIAR EVALUACIÓN DE GRADO"):
            with st.spinner("Diseñando examen por niveles de dificultad..."):
                prompt = f"""
                Eres un sinodal de Cirugía Plástica. Basado en: {full_text[:15000]}
                Genera 9 preguntas distribuidas así: 3 Sencillas, 3 Moderadas, 3 Difíciles.
                JSON: [{{"id":1, "nivel":"Sencilla", "pregunta":"...", "opciones":["A","B","C","D"], "correcta":"A", "justificacion":"..."}}]
                """
                response = model.generate_content(prompt)
                data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                st.session_state.examen = data
                st.session_state.respuestas = {}
                st.success("Examen listo.")

    except Exception as e:
        st.error(f"Error: {e}")

# --- EXAMEN Y EVALUACIÓN ---
if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.markdown(f"**[{q['nivel']}] {q['id']}. {q['pregunta']}**")
        st.session_state.respuestas[q['id']] = st.radio("Opción:", q['opciones'], key=f"q_{q['id']}", label_visibility="collapsed")
        st.markdown("---")

    if st.button("📊 FINALIZAR Y ENVIAR A LA DRA. RAFAELA"):
        resultados = {"Sencilla": 0, "Moderada": 0, "Difícil": 0}
        errores_log = ""
        
        for q in st.session_state.examen:
            # Corregimos evaluación: comparamos el texto exacto
            ans_correcta = q['opciones'][ord(q['correcta'])-65]
            if st.session_state.respuestas[q['id']] == ans_correcta:
                resultados[q['nivel']] += 1
            else:
                errores_log += f"P{q['id']} ({q['nivel']}): {q['justificacion']} | "

        total = sum(resultados.values())
        final_grade = round((total / len(st.session_state.examen)) * 10, 1)
        
        # Enviar a Google Sheets
        payload = {
            "nombre": nombre,
            "grado": grado,
            "calificacion": final_grade,
            "sencillas": f"{resultados['Sencilla']}/3",
            "moderadas": f"{resultados['Moderada']}/3",
            "dificiles": f"{resultados['Difícil']}/3",
            "detalles_errores": errores_log
        }
        
        try:
            requests.post(URL_SHEET, json=payload)
            st.success(f"Resultados enviados con éxito a la Jefatura.")
        except:
            st.warning("Error al enviar a la nube, pero aquí están tus resultados.")

        st.header(f"Calificación Final: {final_grade}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Sencillas", payload["sencillas"])
        col2.metric("Moderadas", payload["moderadas"])
        col3.metric("Difíciles", payload["dificiles"])
