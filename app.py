import streamlit as st
import google.generativeai as genai
import pypdf
import json

# --- CONFIGURACIÓN DE INTERFAZ PREMIUM ---
st.set_page_config(page_title="HGC - Cirugía Plástica", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; }
    [data-testid="stSidebar"] { background-color: #1E1E1E !important; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    .main * { color: #000000 !important; }
    .stButton>button { background-color: #B87333 !important; color: white !important; width: 100%; border-radius: 8px; }
    .resumen-card { padding: 20px; border-radius: 10px; border: 1px solid #B87333; background-color: #FFFFFF; }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL (DATOS DE CONTROL) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1021/1021566.png", width=100)
    st.header("Control Académico")
    nombre = st.text_input("Nombre Completo del Residente")
    grado = st.selectbox("Grado", ["R1", "R2", "R3", "R4 (Jefe)"])
    api_key = st.text_input("Gemini API Key", type="password").strip()
    pdf_file = st.file_uploader("Cargar Literatura (Neligan, Jacono, etc.)", type="pdf")
    num_preguntas = st.slider("Número de Reactivos", 5, 25, 10)

st.title("🏥 Sistema de Evaluación Quirúrgica")
st.write(f"**Hospital General de Culiacán** | Especialidad en Cirugía Plástica y Reconstructiva")

# --- MOTOR DE INTELIGENCIA ---
if pdf_file and api_key and nombre:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Extracción de texto
        reader = pypdf.PdfReader(pdf_file)
        full_text = "\n".join([p.extract_text() for p in reader.pages])

        if st.button("🚀 GENERAR EXAMEN DE ALTA EXIGENCIA"):
            with st.spinner("Generando reactivos nivel Consejo..."):
                prompt = f"""
                Actúa como un Sinodal Senior del Consejo Mexicano de Cirugía Plástica.
                Utiliza este texto técnico: {full_text[:15000]}
                Genera {num_preguntas} preguntas de opción múltiple.
                REGLAS:
                1. No uses frases como 'según el texto'. Habla como experto.
                2. Nivel de dificultad: Muy Alto (Enfocado en anatomía quirúrgica, planos, complicaciones y técnica).
                3. Formato JSON ESTRICTO: [{{"id":1, "pregunta":"...", "opciones":["...","...","...","..."], "correcta":"A", "justificacion":"..."}}]
                """
                response = model.generate_content(prompt)
                data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                st.session_state.current_exam = data
                st.session_state.user_answers = {}
                st.success("Examen generado. Responda con precisión quirúrgica.")

    except Exception as e:
        st.error(f"Error de sistema: {e}")

# --- DESPLIEGUE DEL EXAMEN ---
if 'current_exam' in st.session_state:
    for q in st.session_state.current_exam:
        st.markdown(f"#### {q['id']}. {q['pregunta']}")
        st.session_state.user_answers[q['id']] = st.radio(
            f"Seleccione respuesta para P{q['id']}:", 
            q['opciones'], 
            key=f"q_{q['id']}", 
            label_visibility="collapsed"
        )
        st.markdown("---")

    if st.button("📊 FINALIZAR Y ENVIAR A JEFATURA"):
        score = 0
        st.header("Dictamen Final")
        
        for q in st.session_state.current_exam:
            # Lógica de comparación de letras (A, B, C, D)
            # Extraemos la letra de la opción seleccionada (asumiendo formato "A) Texto")
            idx_correcta = ord(q['correcta']) - 65
            opcion_correcta_texto = q['opciones'][idx_correcta]
            user_choice = st.session_state.user_answers[q['id']]
            
            if user_choice == opcion_correcta_texto:
                score += 1
                st.success(f"**P{q['id']}: CORRECTA**")
            else:
                st.error(f"**P{q['id']}: INCORRECTA**")
                st.info(f"**Justificación Técnica:** {q['justificacion']}")

        final_grade = (score / len(st.session_state.current_exam)) * 10
        st.metric(f"Calificación de {nombre}", f"{final_grade}/10")
        
        # NOTA: Aquí es donde conectaremos el envío a la Dra. Rafaela en el siguiente paso.
        st.warning("Copia esta pantalla o descarga el reporte para entrega a la Jefatura.")
