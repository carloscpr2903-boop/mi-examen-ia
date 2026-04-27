import streamlit as st
from genai import Client
import pypdf
import json

# Configuración de la página con estilo profesional
st.set_page_config(page_title="Ramale Exam Center", page_icon="🏥", layout="centered")

# Estilo personalizado (Colores Cobre y Marfil)
st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; }
    .stButton>button { background-color: #B87333; color: white; border-radius: 10px; }
    h1 { color: #5D4037; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Generador Quirúrgico Dinámico")
st.subheader("Preparación para el Examen de Consejo 2027")

# --- BARRA LATERAL: CONFIGURACIÓN ---
with st.sidebar:
    st.header("Configuración")
    api_key = st.text_input("Gemini API Key", type="password")
    uploaded_file = st.file_uploader("Cargar capítulo PDF", type="pdf")
    
    num_preguntas = st.slider("Número de preguntas", 3, 20, 5)
    dificultad = st.selectbox("Nivel de exigencia", ["Básico", "Intermedio", "Avanzado", "Consejo-level"])
    tipo_examen = st.multiselect("Tipos de pregunta", ["Opción Múltiple", "Respuesta Abierta"], default=["Opción Múltiple"])

# --- LÓGICA DE PROCESAMIENTO ---
if uploaded_file and api_key:
    client = Client(api_key=api_key)
    
    # Extraer texto del PDF
    reader = pypdf.PdfReader(uploaded_file)
    text_content = ""
    for page in reader.pages:
        text_content += page.extract_text()
    
    if st.button("Generar Nuevo Examen"):
        with st.spinner("Analizando literatura quirúrgica..."):
            prompt = f"""
            Actúa como un sinodal de cirugía plástica. Basado en este texto: {text_content[:15000]}
            Genera {num_preguntas} preguntas de nivel {dificultad}.
            Usa estos tipos: {tipo_examen}.
            Formato JSON: [{{"id": 1, "tipo": "opción múltiple/abierta", "pregunta": "", "opciones": [], "correcta": ""}}]
            """
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            st.session_state.examen = json.loads(response.text.replace('```json', '').replace('```', '').strip())
            st.session_state.respuestas = {}

# --- INTERFAZ DE EXAMEN ---
if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.write(f"### Pregunta {q['id']}")
        st.write(q['pregunta'])
        
        if q['tipo'].lower() == "opción múltiple":
            st.session_state.respuestas[q['id']] = st.radio(f"Selecciona una opción para la {q['id']}:", q['opciones'], key=f"q_{q['id']}")
        else:
            st.session_state.respuestas[q['id']] = st.text_area("Escribe tu respuesta técnica:", key=f"q_{q['id']}")

    if st.button("Evaluar Examen"):
        for q in st.session_state.examen:
            user_ans = st.session_state.respuestas.get(q['id'])
            
            eval_prompt = f"Texto: {text_content[:5000]}\nPregunta: {q['pregunta']}\nRespuesta Usuario: {user_ans}\nRespuesta Correcta: {q['correcta']}\nEvalúa y da retroalimentación médica corta."
            feedback = client.models.generate_content(model="gemini-1.5-flash", contents=eval_prompt)
            
            with st.expander(f"Resultado Pregunta {q['id']}"):
                st.write(feedback.text)
