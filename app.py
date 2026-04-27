import streamlit as st
import google.generativeai as genai
import pypdf
import json

# 1. ESTILO DEFINITIVO (SIN ERRORES DE CONTRASTE)
st.set_page_config(page_title="Ramale Exam Center", page_icon="🏥")

st.markdown("""
    <style>
    /* Fondo principal marfil */
    .stApp { background-color: #FAF9F6 !important; }
    
    /* Barra lateral: Todo el texto blanco */
    [data-testid="stSidebar"] { background-color: #262730 !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Área principal: TODO el texto negro intenso */
    .main * { color: #000000 !important; }
    
    /* Excepción para el título y botones para que no se pierdan */
    .main h1, .main h2, .main h3 { color: #5D4037 !important; }
    div.stButton > button { 
        background-color: #B87333 !important; 
        color: white !important; 
        border: none !important;
    }
    
    /* Arreglo para los Radio Buttons (Opciones) */
    div[data-testid="stMarkdownContainer"] p { color: #000000 !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Ramale Exam Center")
st.subheader("Simulador Quirúrgico Personalizado")

# 2. PANEL LATERAL (AJUSTES)
with st.sidebar:
    st.header("Ajustes")
    api_key = st.text_input("Gemini API Key", type="password").strip()
    uploaded_file = st.file_uploader("Subir PDF de Neligan / Otros", type="pdf")
    dificultad = st.selectbox("Nivel", ["Residente", "Jefe de Residentes", "Consejo-level"])

# 3. LÓGICA DE PROCESAMIENTO
if uploaded_file and api_key:
    try:
        genai.configure(api_key=api_key)
        # Búsqueda dinámica de modelo para evitar Error 404
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model = next((m for m in models if "flash" in m), models[0])
        model = genai.GenerativeModel(selected_model)
        
        reader = pypdf.PdfReader(uploaded_file)
        texto_pdf = ""
        for page in reader.pages:
            texto_pdf += page.extract_text() + "\n"

        if st.button("🚀 GENERAR EXAMEN"):
            with st.spinner("Analizando literatura quirúrgica..."):
                prompt = f"Genera 5 preguntas nivel {dificultad} basadas en: {texto_pdf[:12000]}. Responde UNICAMENTE JSON: [{{'id':1, 'pregunta':'...', 'opciones':['A','B','C','D'], 'correcta':'A'}}]"
                response = model.generate_content(prompt)
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.examen = json.loads(clean_json)
                st.session_state.respuestas = {}
                st.success("¡Examen listo! Responde abajo.")
    except Exception as e:
        st.error(f"Error: {e}")

# 4. DESPLIEGUE DE PREGUNTAS
if 'examen' in st.session_state:
    st.markdown("---")
    for q in st.session_state.examen:
        st.markdown(f"**{q['id']}. {q['pregunta']}**")
        st.session_state.respuestas[q['id']] = st.radio(
            f"Selecciona:", q['opciones'], key=f"r_{q['id']}", label_visibility="collapsed"
        )
    
    if st.button("📊 VER RESULTADOS"):
        aciertos = 0
        for q in st.session_state.examen:
            if st.session_state.respuestas.get(q['id']) == q['correcta']:
                aciertos += 1
                st.success(f"P{q['id']}: Correcta ✅")
            else:
                st.error(f"P{q['id']}: Incorrecta (Era {q['correcta']}) ❌")
        st.metric("Puntuación", f"{aciertos}/{len(st.session_state.examen)}")
