import streamlit as st
import google.generativeai as genai
import pypdf
import json
import requests
import time
import re

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="HGC - Cirugía Plástica",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# 2. ESTILOS CSS COMPLETOS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap');

/* APP GENERAL */
.stApp {
    background-color: #FAF9F6 !important;
    font-family: 'Source Sans 3', sans-serif !important;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        #FFFFFF 0%,
        #FFFFFF 15%,
        #001F5B 25%,
        #001F5B 100%) !important;
    border-right: 2px solid #D4AF37 !important;
}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stFileUploader label {
    color: #D1D1D1 !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-size: 13px !important;
    letter-spacing: 0.5px !important;
}

[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #D4AF37 !important;
    font-family: 'Playfair Display', serif !important;
    text-align: center !important;
}

/* INPUT FIELDS EN SIDEBAR */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] .stSelectbox select {
    background-color: rgba(255,255,255,0.1) !important;
    border: 1px solid #D4AF37 !important;
    color: white !important;
    border-radius: 4px !important;
}

/* TÍTULO PRINCIPAL */
.titulo-principal {
    font-family: 'Playfair Display', serif;
    color: #001F5B;
    text-align: center;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 0;
    padding: 10px 0;
}

.subtitulo {
    font-family: 'Source Sans 3', sans-serif;
    color: #D4AF37;
    text-align: center;
    font-size: 14px;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 4px;
}

/* DIVISOR DORADO */
.divisor-dorado {
    border: none;
    border-top: 2px solid #D4AF37;
    margin: 16px 0;
}

/* TARJETAS DE PREGUNTA */
.pregunta-card {
    background: white;
    border: 1px solid #E8E8E8;
    border-left: 4px solid #001F5B;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,31,91,0.08);
}

.pregunta-numero {
    font-size: 11px;
    color: #D4AF37;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.pregunta-texto {
    font-family: 'Source Sans 3', sans-serif;
    font-size: 16px;
    color: #001F5B;
    font-weight: 600;
    line-height: 1.5;
    margin-bottom: 12px;
}

.nivel-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 12px;
}

.nivel-sencilla { background: #E8F5E9; color: #2E7D32; }
.nivel-moderada { background: #FFF3E0; color: #E65100; }
.nivel-dificil  { background: #FFEBEE; color: #C62828; }

/* BOTÓN PRINCIPAL */
div.stButton > button {
    background: linear-gradient(135deg, #D4AF37, #B8960C) !important;
    color: #001F5B !important;
    font-weight: 700 !important;
    font-family: 'Source Sans 3', sans-serif !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 12px 24px !important;
    font-size: 13px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(212,175,55,0.4) !important;
}

div.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(212,175,55,0.5) !important;
}

/* MÉTRICAS */
[data-testid="metric-container"] {
    background: white;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* RESULTADO FINAL */
.resultado-box {
    background: linear-gradient(135deg, #001F5B, #003080);
    border: 2px solid #D4AF37;
    border-radius: 12px;
    padding: 32px;
    text-align: center;
    margin: 24px 0;
}

.resultado-nota {
    font-family: 'Playfair Display', serif;
    font-size: 72px;
    color: #D4AF37;
    font-weight: 700;
    line-height: 1;
}

.resultado-label {
    font-family: 'Source Sans 3', sans-serif;
    color: #D1D1D1;
    font-size: 14px;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 8px;
}

/* JUSTIFICACIONES */
.justificacion-box {
    background: #F0F4FF;
    border-left: 4px solid #001F5B;
    border-radius: 4px;
    padding: 12px 16px;
    margin-top: 8px;
}

.justificacion-box p {
    font-size: 14px !important;
    color: #333 !important;
    margin: 0 !important;
    line-height: 1.6 !important;
}

/* CORRECTO / INCORRECTO */
.correcto { border-left-color: #2E7D32 !important; background: #F1F8F1 !important; }
.incorrecto { border-left-color: #C62828 !important; background: #FFF1F1 !important; }

/* RADIO BUTTONS */
.stRadio label {
    font-size: 15px !important;
    color: #333 !important;
}

/* ESTADO VACÍO */
.estado-vacio {
    text-align: center;
    padding: 60px 20px;
    color: #999;
}

.estado-vacio-icono {
    font-size: 48px;
    margin-bottom: 16px;
}

.estado-vacio-texto {
    font-size: 16px;
    color: #666;
    line-height: 1.6;
}

/* HEADER EXAMEN */
.header-examen {
    background: white;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
    padding: 16px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* PROGRESS BAR */
.stProgress > div > div {
    background: linear-gradient(90deg, #001F5B, #D4AF37) !important;
}

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 3. CONSTANTES
# ─────────────────────────────────────────────
URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

NUM_PREGUNTAS = 9  # 3 sencillas + 3 moderadas + 3 difíciles

# ─────────────────────────────────────────────
# 4. FUNCIONES UTILITARIAS
# ─────────────────────────────────────────────

def extraer_texto_pdf(pdf_file):
    """Extrae TODO el texto del PDF sin límite de páginas."""
    try:
        reader = pypdf.PdfReader(pdf_file)
        texto = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                texto += f"\n--- Página {i+1} ---\n{page_text}"
        return texto.strip()
    except Exception as e:
        return None, str(e)

def limpiar_json(texto):
    """Limpia la respuesta de Gemini y extrae JSON válido."""
    # Quitar bloques de código markdown
    texto = re.sub(r'```json\s*', '', texto)
    texto = re.sub(r'```\s*', '', texto)
    texto = texto.strip()

    # Buscar el array JSON
    match = re.search(r'\[[\s\S]*\]', texto)
    if match:
        return match.group(0)
    return texto

def generar_preguntas(model, texto_pdf, num_preguntas=9):
    """Genera preguntas con manejo de errores robusto."""
    prompt = f"""Eres un experto evaluador para el Consejo Mexicano de Cirugía Plástica, Estética y Reconstructiva.

Basado en el siguiente contenido quirúrgico especializado:

{texto_pdf[:12000]}

Genera exactamente {num_preguntas} preguntas de examen NIVEL CONSEJO para residentes de cirugía plástica:
- 3 preguntas de nivel "Sencilla" (conceptos fundamentales, anatomía, indicaciones básicas)
- 3 preguntas de nivel "Moderada" (decisiones clínicas, técnica quirúrgica, complicaciones)
- 3 preguntas de nivel "Difícil" (casos complejos, razonamiento crítico, manejo avanzado)

REQUISITOS OBLIGATORIOS:
- Basadas 100% en el contenido del documento
- Preguntas clínicas con razonamiento quirúrgico (NO triviales ni memorísticas)
- Opciones distractoras CREÍBLES y clínicamente plausibles
- Una sola respuesta correcta inequívoca
- Justificación detallada que explique POR QUÉ la respuesta es correcta
- Énfasis en: anatomía quirúrgica, técnica, complicaciones, selección de pacientes

RESPONDE ÚNICAMENTE CON UN ARRAY JSON VÁLIDO. Sin texto adicional. Sin backticks. Solo JSON puro:
[
  {{
    "id": 1,
    "nivel": "Sencilla",
    "pregunta": "texto completo de la pregunta clínica",
    "opciones": ["A) opción uno", "B) opción dos", "C) opción tres", "D) opción cuatro"],
    "correcta": "A",
    "justificacion": "Explicación detallada de por qué esta respuesta es correcta y por qué las otras son incorrectas"
  }}
]"""

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 4000,
        }
    )
    return response.text

def inicializar_modelo(api_key):
    """Inicializa el modelo Gemini."""
    genai.configure(api_key=api_key)
    models_available = [m.name for m in genai.list_models()
                       if 'generateContent' in m.supported_generation_methods]
    # Preferir flash por velocidad/costo, luego pro
    preferred = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    model_name = None
    for pref in preferred:
        match = next((m for m in models_available if pref in m), None)
        if match:
            model_name = match
            break
    if not model_name:
        model_name = models_available[0]
    return genai.GenerativeModel(model_name), model_name

def calcular_estadisticas(examen_data, answers):
    """Calcula estadísticas detalladas del examen."""
    stats = {"Sencilla": {"correctas": 0, "total": 0},
             "Moderada": {"correctas": 0, "total": 0},
             "Difícil": {"correctas": 0, "total": 0}}
    resultados_detalle = []

    for item in examen_data:
        nivel = item.get('nivel', 'Sencilla')
        if nivel not in stats:
            nivel = 'Sencilla'
        stats[nivel]["total"] += 1

        idx_correcto = ord(item['correcta'].upper()) - 65
        respuesta_usuario = answers.get(item['id'], "")
        es_correcto = False

        if respuesta_usuario and idx_correcto < len(item['opciones']):
            opcion_correcta = item['opciones'][idx_correcto]
            es_correcto = respuesta_usuario == opcion_correcta

        if es_correcto:
            stats[nivel]["correctas"] += 1

        resultados_detalle.append({
            "id": item['id'],
            "nivel": nivel,
            "pregunta": item['pregunta'],
            "correcta": item['opciones'][idx_correcto] if idx_correcto < len(item['opciones']) else "N/A",
            "respuesta_usuario": respuesta_usuario,
            "es_correcto": es_correcto,
            "justificacion": item.get('justificacion', '')
        })

    total_correctas = sum(s["correctas"] for s in stats.values())
    total_preguntas = sum(s["total"] for s in stats.values())
    nota = round((total_correctas / total_preguntas) * 10, 1) if total_preguntas > 0 else 0

    return stats, resultados_detalle, nota, total_correctas, total_preguntas

# ─────────────────────────────────────────────
# 5. INICIALIZACIÓN DE SESSION STATE
# ─────────────────────────────────────────────
if 'examen_data' not in st.session_state:
    st.session_state.examen_data = None
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'examen_enviado' not in st.session_state:
    st.session_state.examen_enviado = False
if 'modelo_nombre' not in st.session_state:
    st.session_state.modelo_nombre = None

# ─────────────────────────────────────────────
# 6. SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    logo_url = "https://raw.githubusercontent.com/carloscpr2903-boop/mi-examen-ia/main/Logotipo%20Principal%20Sin%20Fondo%20(1).png"
    try:
        st.image(logo_url, use_container_width=True)
    except:
        st.markdown("### 🏥 HGC")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## REGISTRO")
    st.markdown("---")

    nombre = st.text_input("👤 Nombre del Residente", placeholder="Dr./Dra. Apellido Nombre")
    grado = st.selectbox("🎓 Grado", ["R1", "R2", "R3", "R4 (Jefe)"])
    api_key = st.text_input("🔑 Gemini API Key", type="password", placeholder="AIza...").strip()
    pdf_file = st.file_uploader("📄 Cargar PDF Técnico", type="pdf",
                                help="Cualquier capítulo de cirugía plástica")

    st.markdown("---")

    # Estado del sistema
    if api_key and pdf_file and nombre:
        st.markdown("✅ **Sistema listo**")
    else:
        faltantes = []
        if not nombre: faltantes.append("• Nombre")
        if not api_key: faltantes.append("• API Key")
        if not pdf_file: faltantes.append("• PDF")
        st.markdown(f"⚠️ **Pendiente:**\n" + "\n".join(faltantes))

    if st.session_state.modelo_nombre:
        st.markdown(f"🤖 Modelo: `{st.session_state.modelo_nombre.split('/')[-1]}`")

# ─────────────────────────────────────────────
# 7. ENCABEZADO PRINCIPAL
# ─────────────────────────────────────────────
st.markdown('<p class="titulo-principal">HGC — EVALUACIÓN DE ALTA ESPECIALIDAD</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo">División de Cirugía Plástica, Estética y Reconstructiva · Estudios de Posgrado e Investigación</p>', unsafe_allow_html=True)
st.markdown('<hr class="divisor-dorado">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 8. MOTOR DE GENERACIÓN
# ─────────────────────────────────────────────
if pdf_file and api_key and nombre:

    col_btn, col_info = st.columns([2, 3])

    with col_btn:
        generar = st.button("🚀 GENERAR EVALUACIÓN", use_container_width=True)

    with col_info:
        if st.session_state.examen_data:
            st.markdown(f"✅ Examen activo · {len(st.session_state.examen_data)} preguntas generadas")
        if st.session_state.examen_enviado:
            if st.button("🔄 NUEVO EXAMEN", use_container_width=True):
                st.session_state.examen_data = None
                st.session_state.answers = {}
                st.session_state.examen_enviado = False
                st.rerun()

    if generar:
        st.session_state.examen_data = None
        st.session_state.answers = {}
        st.session_state.examen_enviado = False

        progress = st.progress(0)
        status = st.empty()

        try:
            # Paso 1: Extraer PDF
            status.markdown("📄 **Extrayendo contenido del PDF...**")
            progress.progress(20)
            texto_pdf = extraer_texto_pdf(pdf_file)

            if not texto_pdf:
                st.error("❌ No se pudo extraer texto del PDF. Verifica que no sea un PDF escaneado.")
                st.stop()

            num_chars = len(texto_pdf)
            status.markdown(f"📄 **PDF procesado** · {num_chars:,} caracteres extraídos")
            progress.progress(40)
            time.sleep(0.5)

            # Paso 2: Inicializar modelo
            status.markdown("🤖 **Conectando con Gemini...**")
            progress.progress(50)
            model, model_name = inicializar_modelo(api_key)
            st.session_state.modelo_nombre = model_name
            progress.progress(60)

            # Paso 3: Generar preguntas (con reintento)
            status.markdown("🧠 **Generando preguntas nivel Consejo...**")
            progress.progress(70)

            max_intentos = 3
            preguntas = None

            for intento in range(max_intentos):
                try:
                    raw_response = generar_preguntas(model, texto_pdf)
                    json_limpio = limpiar_json(raw_response)
                    preguntas = json.loads(json_limpio)

                    # Validar estructura
                    if not isinstance(preguntas, list) or len(preguntas) == 0:
                        raise ValueError("JSON no es lista válida")

                    # Validar campos mínimos
                    campos_req = ['id', 'nivel', 'pregunta', 'opciones', 'correcta', 'justificacion']
                    for p in preguntas:
                        for campo in campos_req:
                            if campo not in p:
                                raise ValueError(f"Campo '{campo}' faltante en pregunta {p.get('id', '?')}")

                    break  # Salir del loop si todo bien

                except (json.JSONDecodeError, ValueError) as e:
                    if intento < max_intentos - 1:
                        status.markdown(f"⚠️ **Reintentando... ({intento + 2}/{max_intentos})**")
                        time.sleep(2)
                    else:
                        raise Exception(f"No se pudo generar JSON válido después de {max_intentos} intentos: {str(e)}")

            progress.progress(90)
            status.markdown("✅ **Examen generado exitosamente**")

            st.session_state.examen_data = preguntas
            st.session_state.answers = {}

            progress.progress(100)
            time.sleep(0.5)
            progress.empty()
            status.empty()
            st.rerun()

        except genai.types.generation_types.BlockedPromptException:
            progress.empty()
            status.empty()
            st.error("❌ Contenido bloqueado por filtros de seguridad. Intenta con otro PDF.")

        except Exception as e:
            progress.empty()
            status.empty()
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
                st.error("❌ **API Key inválida.** Verifica tu clave de Gemini en https://aistudio.google.com/apikey")
            elif "quota" in error_msg.lower():
                st.error("❌ **Cuota de API agotada.** Espera unos minutos o revisa tu plan en Google AI Studio.")
            elif "404" in error_msg:
                st.error("❌ **Modelo no disponible.** Intenta de nuevo.")
            else:
                st.error(f"❌ **Error:** {error_msg}")

elif not nombre or not api_key or not pdf_file:
    st.markdown("""
    <div class="estado-vacio">
        <div class="estado-vacio-icono">🏥</div>
        <div class="estado-vacio-texto">
            <strong>Sistema de Evaluación HGC</strong><br><br>
            Para iniciar, completa los campos en el panel izquierdo:<br>
            <strong>Nombre · API Key · PDF del tema a evaluar</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 9. RENDERIZADO DEL EXAMEN
# ─────────────────────────────────────────────
if st.session_state.examen_data and not st.session_state.examen_enviado:

    examen_data = st.session_state.examen_data
    total_preg = len(examen_data)
    respondidas = len([a for a in st.session_state.answers.values() if a])

    # Progress bar del examen
    st.markdown(f"**Progreso:** {respondidas}/{total_preg} preguntas respondidas")
    st.progress(respondidas / total_preg if total_preg > 0 else 0)
    st.markdown("<br>", unsafe_allow_html=True)

    # Renderizar cada pregunta
    for item in examen_data:
        nivel = item.get('nivel', 'Sencilla')
        nivel_class = {
            'Sencilla': 'nivel-sencilla',
            'Moderada': 'nivel-moderada',
            'Difícil': 'nivel-dificil'
        }.get(nivel, 'nivel-sencilla')

        st.markdown(f"""
        <div class="pregunta-card">
            <div class="pregunta-numero">Pregunta {item['id']} de {total_preg}</div>
            <span class="nivel-badge {nivel_class}">{nivel}</span>
            <div class="pregunta-texto">{item['pregunta']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Radio buttons para opciones
        opciones = item.get('opciones', [])
        if opciones:
            respuesta = st.radio(
                "Selecciona tu respuesta:",
                opciones,
                key=f"radio_{item['id']}",
                label_visibility="collapsed",
                index=None
            )
            if respuesta:
                st.session_state.answers[item['id']] = respuesta

        st.markdown("<br>", unsafe_allow_html=True)

    # ─── BOTÓN FINALIZAR ───
    st.markdown("---")

    if respondidas < total_preg:
        faltantes = total_preg - respondidas
        st.warning(f"⚠️ Tienes **{faltantes} pregunta(s) sin responder**. Respóndelas todas antes de enviar.")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        finalizar = st.button("📊 FINALIZAR Y ENVIAR A JEFATURA", use_container_width=True)

    if finalizar:
        if respondidas < total_preg:
            st.error("❌ Responde todas las preguntas antes de enviar.")
        else:
            # ─────────────────────────────────────────────
            # 10. RESULTADOS Y RETROALIMENTACIÓN
            # ─────────────────────────────────────────────
            st.session_state.examen_enviado = True

            stats, resultados_detalle, nota, total_correctas, total_preg_count = calcular_estadisticas(
                examen_data, st.session_state.answers
            )

            # Determinar calificación visual
            if nota >= 8:
                color_nota = "#D4AF37"
                emoji_nota = "🏆"
                mensaje_nota = "EXCELENTE"
            elif nota >= 6:
                color_nota = "#FFA726"
                emoji_nota = "✅"
                mensaje_nota = "APROBADO"
            else:
                color_nota = "#EF5350"
                emoji_nota = "📚"
                mensaje_nota = "NECESITA REFUERZO"

            # Caja de resultado principal
            st.markdown(f"""
            <div class="resultado-box">
                <div style="font-size:48px; margin-bottom:8px;">{emoji_nota}</div>
                <div class="resultado-nota" style="color:{color_nota};">{nota}</div>
                <div class="resultado-label">/ 10 — {mensaje_nota}</div>
                <div style="color:#D1D1D1; margin-top:12px; font-size:13px; letter-spacing:1px;">
                    {nombre} · {grado}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Métricas por nivel
            st.markdown("### 📊 Desempeño por Nivel")
            col1, col2, col3 = st.columns(3)

            for col, nivel in zip([col1, col2, col3], ['Sencilla', 'Moderada', 'Difícil']):
                s = stats.get(nivel, {"correctas": 0, "total": 0})
                porcentaje = round((s["correctas"] / s["total"]) * 100) if s["total"] > 0 else 0
                with col:
                    st.metric(
                        label=f"Nivel {nivel}",
                        value=f"{s['correctas']}/{s['total']}",
                        delta=f"{porcentaje}%"
                    )

            # Retroalimentación detallada
            st.markdown("---")
            st.markdown("### 🔍 Retroalimentación Detallada")

            correctas_count = sum(1 for r in resultados_detalle if r['es_correcto'])
            incorrectas_count = len(resultados_detalle) - correctas_count

            tab1, tab2 = st.tabs([f"✅ Correctas ({correctas_count})", f"❌ Incorrectas ({incorrectas_count})"])

            with tab1:
                correctas = [r for r in resultados_detalle if r['es_correcto']]
                if correctas:
                    for r in correctas:
                        st.markdown(f"""
                        <div class="justificacion-box correcto">
                            <p><strong>P{r['id']} [{r['nivel']}]:</strong> {r['pregunta']}</p>
                            <p style="margin-top:8px;">✅ <strong>Tu respuesta:</strong> {r['respuesta_usuario']}</p>
                            <p style="margin-top:8px; color:#555;">📖 {r['justificacion']}</p>
                        </div>
                        <br>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No hubo respuestas correctas.")

            with tab2:
                incorrectas = [r for r in resultados_detalle if not r['es_correcto']]
                if incorrectas:
                    for r in incorrectas:
                        st.markdown(f"""
                        <div class="justificacion-box incorrecto">
                            <p><strong>P{r['id']} [{r['nivel']}]:</strong> {r['pregunta']}</p>
                            <p style="margin-top:8px;">❌ <strong>Tu respuesta:</strong> {r['respuesta_usuario']}</p>
                            <p style="margin-top:8px;">✅ <strong>Respuesta correcta:</strong> {r['correcta']}</p>
                            <p style="margin-top:8px; color:#555;">📖 {r['justificacion']}</p>
                        </div>
                        <br>
                        """, unsafe_allow_html=True)
                else:
                    st.success("🎉 ¡Todas las respuestas fueron correctas!")

            # Enviar a Google Sheets
            st.markdown("---")
            errores_texto = " | ".join([
                f"P{r['id']}: {r['justificacion'][:80]}..."
                for r in resultados_detalle if not r['es_correcto']
            ])

            payload = {
                "nombre": nombre,
                "grado": grado,
                "calificacion": nota,
                "sencillas": f"{stats['Sencilla']['correctas']}/{stats['Sencilla']['total']}",
                "moderadas": f"{stats['Moderada']['correctas']}/{stats['Moderada']['total']}",
                "dificiles": f"{stats['Difícil']['correctas']}/{stats['Difícil']['total']}",
                "detalles_errores": errores_texto if errores_texto else "Sin errores"
            }

            with st.spinner("📤 Enviando resultados a Jefatura..."):
                try:
                    response = requests.post(URL_SHEET, json=payload, timeout=15)
                    if response.status_code == 200:
                        st.success("✅ **Resultados enviados correctamente a la Jefatura.**")
                    else:
                        st.warning(f"⚠️ Respuesta inesperada del servidor ({response.status_code}). Los resultados pueden no haberse registrado.")
                except requests.exceptions.Timeout:
                    st.warning("⚠️ Tiempo de espera agotado al enviar. Verifica conexión a internet.")
                except requests.exceptions.ConnectionError:
                    st.warning("⚠️ Sin conexión a internet. Resultados no enviados.")
                except Exception as e:
                    st.warning(f"⚠️ Error al enviar: {str(e)}")

            # Botón nuevo examen
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 GENERAR NUEVO EXAMEN", use_container_width=True):
                    st.session_state.examen_data = None
                    st.session_state.answers = {}
                    st.session_state.examen_enviado = False
                    st.rerun()

# Si el examen ya fue enviado, mostrar opción de nuevo examen
elif st.session_state.examen_enviado:
    st.markdown("""
    <div class="estado-vacio">
        <div class="estado-vacio-icono">✅</div>
        <div class="estado-vacio-texto">
            <strong>Examen completado y enviado a Jefatura.</strong><br><br>
            Usa el botón "NUEVO EXAMEN" en la parte superior para continuar.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 NUEVO EXAMEN", use_container_width=True):
            st.session_state.examen_data = None
            st.session_state.answers = {}
            st.session_state.examen_enviado = False
            st.rerun()
