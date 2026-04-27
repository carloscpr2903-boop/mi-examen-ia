import streamlit as st
import google.generativeai as genai
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
    num_preguntas = st.slider("Preguntas", 3, 15, 5)
    dificultad = st.selectbox("Nivel", ["Residente R1-R2", "Jefe de Residentes", "Consejo-level"])

if uploaded_file and api_input:
    try:
        genai.configure(api_key=api_input)
        
        # --- BLOQUE DE AUTO-DETECCIÓN DE MODELO ---
        # Esto busca qué modelo está activo en tu cuenta para evitar el error 404
        model_name = 'gemini-1.5-flash' # Default
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini-1.5-flash' in m.name:
                        model_name = m.name
                        break
        except:
            pass # Si falla el listado, usamos el default
        
        model = genai.GenerativeModel(model_name=model_name)
        
        # Procesar PDF
        reader = pypdf.PdfReader(uploaded_file)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
        
        if st.button("🚀 GENERAR EXAMEN"):
            if not text_content.strip():
                st.error("El PDF parece estar vacío o ser solo imágenes.")
            else:
                with st.spinner(f"Usando {model_name} para generar reactivos..."):
                    prompt = f"Actúa como sinodal. Basado en: {text_content[:12000]}. Genera {num_preguntas} preguntas nivel {dificultad}. Formato JSON: [{{'id': 1, 'pregunta': '...', 'opciones': ['A', 'B', 'C', 'D'], 'correcta': 'A'}}]"
                    response = model.generate_content(prompt)
                    raw_text = response.text.replace('```json', '').replace('```', '').strip()
                    st.session_state.examen = json.loads(raw_text)
                    st.session_state.respuestas = {}
                    st.success("Examen listo.")

    except Exception as e:
        st.error(f"Error detectado: {e}. Verifica que tu API Key sea de Google AI Studio.")

if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.write(f"**{q['id']}. {q['pregunta']}**")
        st.session_state.respuestas[q['id']] = st.radio(f"Opción para {q['id']}:", q['opciones'], key=f"radio_{q['id']}")
    
    if st.button("📊 FINALIZAR Y EVALUAR"):
        aciertos = 0
        for q in st.session_state.examen:
            if st.session_state.respuestas.get(q['id']) == q['correcta']:
                aciertos += 1
                st.success(f"P{q['id']}: Correcta ✅")
            else:
                st.error(f"P{q['id']}: Incorrecta. La respuesta era {q['correcta']} ❌")
        st.metric("Puntuación Final", f"{aciertos}/{len(st.session_state.examen)}")
