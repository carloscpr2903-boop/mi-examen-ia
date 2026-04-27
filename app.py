import streamlit as st
from genai import Client
import pypdf
import json

st.set_page_config(page_title="Ramale Exam Center", page_icon="🏥", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; }
    .stButton>button { background-color: #B87333; color: white; border-radius: 10px; width: 100%; }
    h1 { color: #5D4037; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Ramale Exam Center")
st.subheader("Simulador de Consejo de Cirugía Plástica")

with st.sidebar:
    st.header("Configuración")
    api_input = st.text_input("Gemini API Key", type="password").strip()
    uploaded_file = st.file_uploader("Cargar PDF Quirúrgico", type="pdf")
    num_preguntas = st.slider("Preguntas", 3, 10, 5)
    dificultad = st.selectbox("Nivel", ["Residente", "Consejo-level"])

if uploaded_file and api_input:
    try:
        # Usamos el cliente de la nueva librería 2026
        client = Client(api_key=api_input)
        
        reader = pypdf.PdfReader(uploaded_file)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
        
        if st.button("🚀 GENERAR EXAMEN"):
            with st.spinner("Conectando con el servidor de Google..."):
                prompt = f"Genera un examen de {num_preguntas} preguntas nivel {dificultad} basado en: {text_content[:10000]}. Responde solo con JSON: [{{'id':1, 'pregunta':'...', 'opciones':['A','B','C','D'], 'correcta':'A'}}]"
                
                # Nueva sintaxis para evitar el error 404
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                
                raw_text = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.examen = json.loads(raw_text)
                st.session_state.respuestas = {}
                st.success("¡Examen generado exitosamente!")

    except Exception as e:
        st.error(f"Error de conexión: {e}. Revisa si tu API Key es correcta.")

if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.write(f"**{q['id']}. {q['pregunta']}**")
        st.session_state.respuestas[q['id']] = st.radio(f"Selecciona:", q['opciones'], key=f"r_{q['id']}")
    
    if st.button("📊 EVALUAR"):
        aciertos = 0
        for q in st.session_state.examen:
            if st.session_state.respuestas.get(q['id']) == q['correcta']:
                aciertos += 1
                st.success(f"P{q['id']}: Correcta")
            else:
                st.error(f"P{q['id']}: Incorrecta. Era {q['correcta']}")
        st.metric("Resultado", f"{aciertos}/{len(st.session_state.examen)}")
