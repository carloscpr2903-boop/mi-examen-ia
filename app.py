import streamlit as st
import google.generativeai as genai
import pypdf
import json

# Configuración de la página
st.set_page_config(page_title="Ramale Exam Center", page_icon="🏥", layout="centered")

# Estilo personalizado
st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; }
    .stButton>button { background-color: #B87333; color: white; border-radius: 10px; }
    h1 { color: #5D4037; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Generador Quirúrgico Dinámico")
st.subheader("Preparación para el Examen de Consejo 2027")

with st.sidebar:
    st.header("Configuración")
    api_key = st.text_input("Gemini API Key", type="password")
    uploaded_file = st.file_uploader("Cargar capítulo PDF", type="pdf")
    num_preguntas = st.slider("Número de preguntas", 3, 20, 5)
    dificultad = st.selectbox("Nivel de exigencia", ["Básico", "Intermedio", "Avanzado", "Consejo-level"])
    tipo_examen = st.multiselect("Tipos de pregunta", ["Opción Múltiple", "Respuesta Abierta"], default=["Opción Múltiple"])

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    reader = pypdf.PdfReader(uploaded_file)
    text_content = ""
    for page in reader.pages:
        text_content += page.extract_text()
    
    if st.button("Generar Nuevo Examen"):
        with st.spinner("Analizando literatura quirúrgica..."):
            prompt = f"Actúa como sinodal de cirugía plástica. Basado en: {text_content[:15000]}. Genera {num_preguntas} preguntas de nivel {dificultad}. Tipos: {tipo_examen}. Formato JSON estricto: [{{'id': 1, 'tipo': 'opción múltiple/abierta', 'pregunta': '', 'opciones': [], 'correcta': ''}}]"
            response = model.generate_content(prompt)
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            st.session_state.examen = json.loads(clean_json)
            st.session_state.respuestas = {}

if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.write(f"### Pregunta {q['id']}")
        st.write(q['pregunta'])
        if q['tipo'].lower() == "opción múltiple":
            st.session_state.respuestas[q['id']] = st.radio(f"Opción para {q['id']}:", q['opciones'], key=f"q_{q['id']}")
        else:
            st.session_state.respuestas[q['id']] = st.text_area("Respuesta técnica:", key=f"q_{q['id']}")

    if st.button("Evaluar Examen"):
        for q in st.session_state.examen:
            ans = st.session_state.respuestas.get(q['id'])
            eval_p = f"Pregunta: {q['pregunta']}\nRespuesta: {ans}\nCorrecta: {q['correcta']}\nEvalúa brevemente."
            feedback = model.generate_content(eval_p)
            st.info(f"Feedback Q{q['id']}: {feedback.text}")
