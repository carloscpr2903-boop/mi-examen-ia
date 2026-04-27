import streamlit as st
import google.generativeai as genai
import pypdf
import json

# Estética Premium Ramale
st.set_page_config(page_title="Ramale Exam Center", page_icon="🏥")
st.markdown("<style>.stApp {background-color: #FAF9F6;} .stButton>button {background-color: #B87333; color: white;}</style>", unsafe_allow_html=True)

st.title("🏥 Ramale Exam Center")
st.subheader("Simulador Quirúrgico Personalizado")

with st.sidebar:
    st.header("Ajustes")
    api_key = st.text_input("Gemini API Key", type="password").strip()
    uploaded_file = st.file_uploader("Subir PDF Quirúrgico", type="pdf")
    dificultad = st.selectbox("Nivel", ["Residente", "Jefe de Residentes", "Consejo-level"])

if uploaded_file and api_key:
    try:
        genai.configure(api_key=api_key)
        # Usamos el modelo con nombre largo para evitar el 404
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        
        reader = pypdf.PdfReader(uploaded_file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() + "\n"

        if st.button("🚀 GENERAR EXAMEN"):
            with st.spinner("Analizando técnica quirúrgica..."):
                prompt = f"Genera 5 preguntas nivel {dificultad} basadas en: {texto[:10000]}. Responde solo JSON: [{{'id':1, 'pregunta':'...', 'opciones':['A','B','C','D'], 'correcta':'A'}}]"
                response = model.generate_content(prompt)
                st.session_state.examen = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                st.session_state.respuestas = {}
                st.success("Examen listo.")
    except Exception as e:
        st.error(f"Error: {e}")

if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.write(f"**{q['id']}. {q['pregunta']}**")
        st.session_state.respuestas[q['id']] = st.radio(f"Elije para P{q['id']}:", q['opciones'], key=f"r_{q['id']}")
    
    if st.button("📊 RESULTADOS"):
        for q in st.session_state.examen:
            if st.session_state.respuestas.get(q['id']) == q['correcta']:
                st.success(f"P{q['id']}: Correcta")
            else:
                st.error(f"P{q['id']}: Incorrecta (Era {q['correcta']})")
