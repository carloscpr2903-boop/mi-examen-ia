import streamlit as st
import google.generativeai as genai
import pypdf
import json

st.set_page_config(page_title="Ramale Exam Center", page_icon="🏥", layout="centered")

# Estilo Premium
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
    # El .strip() elimina espacios accidentales al pegar la clave
    api_input = st.text_input("Gemini API Key", type="password").strip()
    uploaded_file = st.file_uploader("Cargar PDF Quirúrgico", type="pdf")
    num_preguntas = st.slider("Preguntas", 3, 15, 5)
    dificultad = st.selectbox("Nivel", ["Residente R1-R2", "Jefe de Residentes", "Consejo-level"])

if uploaded_file and api_input:
    try:
        genai.configure(api_key=api_input)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Procesar PDF
        reader = pypdf.PdfReader(uploaded_file)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
        
        if st.button("🚀 GENERAR EXAMEN"):
            with st.spinner("Generando reactivos nivel Consejo..."):
                # Prompt mejorado para evitar errores de formato
                prompt = f"""Genera un examen de {num_preguntas} preguntas basado en: {text_content[:10000]}. 
                Dificultad: {dificultad}. Responde ÚNICAMENTE con un JSON válido.
                Formato: [{{"id": 1, "pregunta": "...", "opciones": ["A", "B", "C", "D"], "correcta": "A"}}]"""
                
                response = model.generate_content(prompt)
                
                # Limpieza de la respuesta JSON
                raw_text = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.examen = json.loads(raw_text)
                st.session_state.respuestas = {}
                st.success("Examen generado con éxito.")

    except Exception as e:
        st.error(f"Error de configuración: {e}. Verifica tu API Key.")

# Mostrar examen si ya existe en la sesión
if 'examen' in st.session_state:
    for q in st.session_state.examen:
        st.write(f"**{q['id']}. {q['pregunta']}**")
        st.session_state.respuestas[q['id']] = st.radio(f"Opción para {q['id']}:", q['opciones'], key=f"radio_{q['id']}")
    
    if st.button("📊 FINALIZAR Y EVALUAR"):
        aciertos = 0
        for q in st.session_state.examen:
            user_ans = st.session_state.respuestas.get(q['id'])
            if user_ans == q['correcta']:
                aciertos += 1
                st.success(f"Pregunta {q['id']}: Correcta")
            else:
                st.error(f"Pregunta {q['id']}: Incorrecta. La opción era {q['correcta']}")
        st.metric("Resultado Final", f"{aciertos}/{len(st.session_state.examen)}")
