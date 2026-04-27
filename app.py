import streamlit as st
import google.generativeai as genai
import pypdf
import json

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
        
        # BUSCADOR DINÁMICO DE MODELOS (Para evitar el Error 404)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Priorizamos flash, si no, el que esté disponible
        model_to_use = next((m for m in available_models if "flash" in m), available_models[0])
        
        model = genai.GenerativeModel(model_to_use)
        
        reader = pypdf.PdfReader(uploaded_file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() + "\n"

        if st.button("🚀 GENERAR EXAMEN"):
            with st.spinner(f"Usando motor {model_to_use}..."):
                prompt = f"Genera 5 preguntas nivel {dificultad} basadas en: {texto[:10000]}. Responde solo JSON: [{{'id':1, 'pregunta':'...', 'opciones':['A','B','C','D'], 'correcta':'A'}}]"
                response = model.generate_content(prompt)
                
                # Limpiar la respuesta de la IA
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.examen = json.loads(clean_json)
                st.session_state.respuestas = {}
                st.success("¡Examen listo!")
                
    except Exception as e:
        st.error(f"Error detectado: {e}")
        st.info("Tip: Asegúrate de que tu API Key sea de 'Google AI Studio'.")

if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.write(f"**{q['id']}. {q['pregunta']}**")
        st.session_state.respuestas[q['id']] = st.radio(f"Elije para P{q['id']}:", q['opciones'], key=f"r_{q['id']}")
    
    if st.button("📊 RESULTADOS"):
        aciertos = 0
        for q in st.session_state.examen:
            if st.session_state.respuestas.get(q['id']) == q['correcta']:
                aciertos += 1
                st.success(f"P{q['id']}: Correcta ✅")
            else:
                st.error(f"P{q['id']}: Incorrecta (Era {q['correcta']}) ❌")
        st.metric("Puntuación", f"{aciertos}/{len(st.session_state.examen)}")
