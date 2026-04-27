import streamlit as st
import google.generativeai as genai
import pypdf
import json

# 1. CONFIGURACIÓN VISUAL (ESTILO RAMALE)
st.set_page_config(page_title="Ramale Exam Center", page_icon="🏥")
st.markdown("""
    <style>
    .stApp {background-color: #FAF9F6;}
    .stButton>button {background-color: #B87333; color: white; font-weight: bold;}
    /* Forzar color negro en todo el texto del examen */
    p, span, label {color: #000000 !important; font-size: 18px !important;}
    h1, h2, h3 {color: #5D4037 !important;}
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Ramale Exam Center")
st.subheader("Simulador Quirúrgico Personalizado")

# 2. PANEL LATERAL
with st.sidebar:
    st.header("Ajustes")
    api_key = st.text_input("Gemini API Key", type="password").strip()
    uploaded_file = st.file_uploader("Subir PDF de Neligan / Otros", type="pdf")
    dificultad = st.selectbox("Nivel", ["Residente", "Jefe de Residentes", "Consejo-level"])

# 3. LÓGICA DE GENERACIÓN
if uploaded_file and api_key:
    try:
        genai.configure(api_key=api_key)
        # Buscador automático de modelo disponible
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model = next((m for m in models if "flash" in m), models[0])
        model = genai.GenerativeModel(selected_model)
        
        reader = pypdf.PdfReader(uploaded_file)
        texto_pdf = ""
        for page in reader.pages:
            texto_pdf += page.extract_text() + "\n"

        if st.button("🚀 GENERAR EXAMEN"):
            with st.spinner("Analizando técnica quirúrgica..."):
                prompt = f"Genera 5 preguntas nivel {dificultad} basadas en: {texto_pdf[:10000]}. Responde UNICAMENTE JSON: [{{'id':1, 'pregunta':'...', 'opciones':['A','B','C','D'], 'correcta':'A'}}]"
                response = model.generate_content(prompt)
                # Limpiar y guardar en sesión
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.examen = json.loads(clean_json)
                st.session_state.respuestas = {}
                st.success("¡Examen listo! Responde abajo.")
                
    except Exception as e:
        st.error(f"Error: {e}")

# 4. INTERFAZ DEL EXAMEN (VISIBILIDAD MEJORADA)
if 'examen' in st.session_state:
    st.markdown("---")
    for q in st.session_state.examen:
        # Pregunta en negrita y negro
        st.markdown(f"**{q['id']}. {q['pregunta']}**")
        
        # Opciones
        st.session_state.respuestas[q['id']] = st.radio(
            f"Selecciona tu respuesta para la P{q['id']}:", 
            q['opciones'], 
            key=f"r_{q['id']}"
        )
        st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("📊 VER RESULTADOS"):
        aciertos = 0
        for q in st.session_state.examen:
            user_ans = st.session_state.respuestas.get(q['id'])
            if user_ans == q['correcta']:
                aciertos += 1
                st.success(f"Pregunta {q['id']}: Correcta ✅")
            else:
                st.error(f"Pregunta {q['id']}: Incorrecta. Era: {q['correcta']} ❌")
        
        st.metric("Puntuación", f"{aciertos}/{len(st.session_state.examen)}")
        if aciertos == len(st.session_state.examen):
            st.balloons()
