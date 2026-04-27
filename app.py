import streamlit as st
import google.generativeai as genai
import pypdf
import json
import requests
import time
import re
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

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
# 2. ESTILOS CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap');

.stApp { background-color: #FAF9F6 !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        #FFFFFF 0%, #FFFFFF 15%,
        #001F5B 25%, #001F5B 100%) !important;
    border-right: 2px solid #D4AF37 !important;
}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stFileUploader label,
[data-testid="stSidebar"] .stSlider label {
    color: #D1D1D1 !important;
    font-size: 13px !important;
}

[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #D4AF37 !important;
    font-family: 'Playfair Display', serif !important;
    text-align: center !important;
}

h1, h2, h3 {
    color: #001F5B !important;
    font-family: 'Playfair Display', serif !important;
}

div.stButton > button {
    background: linear-gradient(135deg, #D4AF37, #B8960C) !important;
    color: #001F5B !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 12px 24px !important;
    font-size: 13px !important;
    box-shadow: 0 2px 8px rgba(212,175,55,0.4) !important;
}

.stRadio label { font-size: 15px !important; color: #111111 !important; }
.stRadio > div { gap: 8px !important; }

[data-testid="metric-container"] {
    background: white;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

[data-testid="metric-container"] label { color: #333333 !important; }
[data-testid="metric-container"] [data-testid="metric-value"] { color: #001F5B !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 3. CONSTANTES
# ─────────────────────────────────────────────
URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

# ─────────────────────────────────────────────
# 4. FUNCIONES
# ─────────────────────────────────────────────

def extraer_texto_pdf(pdf_file):
    try:
        reader = pypdf.PdfReader(pdf_file)
        texto = ""
        for i, page in enumerate(reader.pages):
            t = page.extract_text()
            if t:
                texto += f"\n--- Página {i+1} ---\n{t}"
        return texto.strip()
    except Exception as e:
        return None

def limpiar_json(texto):
    texto = re.sub(r'```json\s*', '', texto)
    texto = re.sub(r'```\s*', '', texto)
    texto = texto.strip()
    match = re.search(r'\[[\s\S]*\]', texto)
    if match:
        return match.group(0)
    return texto

def inicializar_modelo(api_key):
    genai.configure(api_key=api_key)
    modelos = [m.name for m in genai.list_models()
               if 'generateContent' in m.supported_generation_methods]
    for pref in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
        match = next((m for m in modelos if pref in m), None)
        if match:
            return genai.GenerativeModel(match), match
    return genai.GenerativeModel(modelos[0]), modelos[0]

def generar_preguntas(model, texto_pdf, num_total):
    # Distribuir preguntas por nivel
    base = num_total // 3
    resto = num_total % 3
    n_sencilla = base + (1 if resto >= 1 else 0)
    n_moderada  = base + (1 if resto >= 2 else 0)
    n_dificil   = base

    prompt = f"""Eres un experto evaluador para el Consejo Mexicano de Cirugía Plástica, Estética y Reconstructiva.

Basado en este contenido quirúrgico especializado:
{texto_pdf[:12000]}

Genera exactamente {num_total} preguntas de examen NIVEL CONSEJO en español:
- {n_sencilla} preguntas de nivel "Sencilla" (anatomía, conceptos clave, indicaciones)
- {n_moderada} preguntas de nivel "Moderada" (decisiones clínicas, técnica quirúrgica, complicaciones)
- {n_dificil} preguntas de nivel "Difícil" (casos complejos, razonamiento crítico, manejo avanzado)

REQUISITOS OBLIGATORIOS:
- Todo en ESPAÑOL
- Basadas 100% en el contenido del documento
- Razonamiento quirúrgico real (NO triviales)
- Opciones distractoras clínicamente plausibles y creíbles
- Una sola respuesta correcta inequívoca
- Justificación detallada que cita el principio del documento

RESPONDE ÚNICAMENTE CON JSON PURO. Sin texto adicional. Sin backticks. Solo el array:
[
  {{
    "id": 1,
    "nivel": "Sencilla",
    "pregunta": "texto completo de la pregunta",
    "opciones": ["A) opción", "B) opción", "C) opción", "D) opción"],
    "correcta": "A",
    "justificacion": "Explicación detallada basada en el contenido"
  }}
]"""

    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.7, "max_output_tokens": 5000}
    )
    return response.text

def calcular_estadisticas(examen_data, answers):
    stats = {
        "Sencilla": {"correctas": 0, "total": 0},
        "Moderada":  {"correctas": 0, "total": 0},
        "Difícil":   {"correctas": 0, "total": 0}
    }
    detalle = []

    for item in examen_data:
        nivel = item.get('nivel', 'Sencilla')
        if nivel not in stats:
            nivel = 'Sencilla'
        stats[nivel]["total"] += 1

        idx = ord(item['correcta'].upper()) - 65
        opcion_correcta = item['opciones'][idx] if idx < len(item['opciones']) else "N/A"
        respuesta_usuario = answers.get(item['id'], "Sin respuesta")
        es_correcto = respuesta_usuario == opcion_correcta

        if es_correcto:
            stats[nivel]["correctas"] += 1

        detalle.append({
            "id": item['id'],
            "nivel": nivel,
            "pregunta": item['pregunta'],
            "opciones": item['opciones'],
            "opcion_correcta": opcion_correcta,
            "respuesta_usuario": respuesta_usuario,
            "es_correcto": es_correcto,
            "justificacion": item.get('justificacion', '')
        })

    total_correctas = sum(s["correctas"] for s in stats.values())
    total_preg = sum(s["total"] for s in stats.values())
    nota = round((total_correctas / total_preg) * 10, 1) if total_preg > 0 else 0
    return stats, detalle, nota, total_correctas, total_preg

def generar_pdf_examen(nombre, grado, examen_data, detalle, stats, nota, fecha):
    buffer = io.BytesIO()

    # Colores institucionales
    NAVY    = colors.HexColor('#001F5B')
    DORADO  = colors.HexColor('#D4AF37')
    GRIS    = colors.HexColor('#F5F5F5')
    VERDE   = colors.HexColor('#2E7D32')
    ROJO    = colors.HexColor('#C62828')
    NEGRO   = colors.black
    BLANCO  = colors.white

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Estilos
    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        'Titulo',
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=4
    )
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        fontName='Helvetica',
        fontSize=10,
        textColor=DORADO,
        alignment=TA_CENTER,
        spaceAfter=2
    )
    estilo_seccion = ParagraphStyle(
        'Seccion',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=6
    )
    estilo_pregunta = ParagraphStyle(
        'Pregunta',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=NEGRO,
        spaceBefore=10,
        spaceAfter=4,
        leading=14
    )
    estilo_opcion = ParagraphStyle(
        'Opcion',
        fontName='Helvetica',
        fontSize=10,
        textColor=NEGRO,
        leftIndent=16,
        spaceAfter=2,
        leading=13
    )
    estilo_opcion_correcta = ParagraphStyle(
        'OpcionCorrecta',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=VERDE,
        leftIndent=16,
        spaceAfter=2,
        leading=13
    )
    estilo_opcion_incorrecta = ParagraphStyle(
        'OpcionIncorrecta',
        fontName='Helvetica',
        fontSize=10,
        textColor=ROJO,
        leftIndent=16,
        spaceAfter=2,
        leading=13
    )
    estilo_justificacion = ParagraphStyle(
        'Justificacion',
        fontName='Helvetica-Oblique',
        fontSize=9,
        textColor=colors.HexColor('#333333'),
        leftIndent=16,
        spaceBefore=4,
        spaceAfter=6,
        leading=13,
        backColor=GRIS
    )
    estilo_normal = ParagraphStyle(
        'Normal2',
        fontName='Helvetica',
        fontSize=10,
        textColor=NEGRO,
        leading=14,
        spaceAfter=4
    )
    estilo_dato = ParagraphStyle(
        'Dato',
        fontName='Helvetica',
        fontSize=10,
        textColor=NEGRO,
        leading=14
    )

    historia = []

    # ── ENCABEZADO ──
    historia.append(Paragraph("HGC — EVALUACIÓN DE ALTA ESPECIALIDAD", estilo_titulo))
    historia.append(Paragraph("División de Cirugía Plástica, Estética y Reconstructiva", estilo_subtitulo))
    historia.append(Paragraph("División de Estudios de Posgrado e Investigación", estilo_subtitulo))
    historia.append(Spacer(1, 6))
    historia.append(HRFlowable(width="100%", thickness=2, color=DORADO))
    historia.append(Spacer(1, 8))

    # ── DATOS DEL RESIDENTE ──
    total_correctas = sum(s["correctas"] for s in stats.values())
    total_preg      = sum(s["total"] for s in stats.values())

    tabla_datos = Table([
        [Paragraph("<b>Residente:</b>", estilo_dato),   Paragraph(nombre, estilo_dato),
         Paragraph("<b>Fecha:</b>", estilo_dato),        Paragraph(fecha, estilo_dato)],
        [Paragraph("<b>Grado:</b>", estilo_dato),        Paragraph(grado, estilo_dato),
         Paragraph("<b>Calificación:</b>", estilo_dato), Paragraph(f"{nota}/10", estilo_dato)],
        [Paragraph("<b>Total preguntas:</b>", estilo_dato), Paragraph(str(total_preg), estilo_dato),
         Paragraph("<b>Correctas:</b>", estilo_dato),    Paragraph(f"{total_correctas}/{total_preg}", estilo_dato)],
    ], colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])

    tabla_datos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GRIS),
        ('BOX',        (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING',    (0,0), (-1,-1), 6),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    historia.append(tabla_datos)
    historia.append(Spacer(1, 10))

    # ── RESUMEN POR NIVEL ──
    historia.append(Paragraph("RESUMEN DE DESEMPEÑO POR NIVEL", estilo_seccion))
    historia.append(HRFlowable(width="100%", thickness=1, color=DORADO))
    historia.append(Spacer(1, 6))

    fila_encabezado = [
        Paragraph("<b>Nivel</b>", estilo_dato),
        Paragraph("<b>Correctas</b>", estilo_dato),
        Paragraph("<b>Total</b>", estilo_dato),
        Paragraph("<b>Porcentaje</b>", estilo_dato)
    ]
    filas_stats = [fila_encabezado]
    for nivel in ['Sencilla', 'Moderada', 'Difícil']:
        s = stats.get(nivel, {"correctas": 0, "total": 0})
        pct = round((s['correctas'] / s['total']) * 100) if s['total'] > 0 else 0
        filas_stats.append([
            Paragraph(nivel, estilo_dato),
            Paragraph(str(s['correctas']), estilo_dato),
            Paragraph(str(s['total']), estilo_dato),
            Paragraph(f"{pct}%", estilo_dato)
        ])

    tabla_stats = Table(filas_stats, colWidths=[1.8*inch, 1.5*inch, 1.5*inch, 1.8*inch])
    tabla_stats.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('TEXTCOLOR',  (0,0), (-1,0), BLANCO),
        ('BACKGROUND', (0,1), (-1,-1), GRIS),
        ('BOX',        (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING',    (0,0), (-1,-1), 6),
        ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
    ]))
    historia.append(tabla_stats)
    historia.append(Spacer(1, 16))

    # ── PREGUNTAS Y RESPUESTAS COMPLETAS ──
    historia.append(Paragraph("EXAMEN COMPLETO — PREGUNTAS Y RETROALIMENTACIÓN", estilo_seccion))
    historia.append(HRFlowable(width="100%", thickness=1, color=DORADO))
    historia.append(Spacer(1, 6))

    for r in detalle:
        # Número y nivel
        nivel_texto = f"Pregunta {r['id']}  |  Nivel: {r['nivel']}  |  {'✓ CORRECTA' if r['es_correcto'] else '✗ INCORRECTA'}"
        color_nivel = VERDE if r['es_correcto'] else ROJO

        estilo_num = ParagraphStyle(
            f'Num{r["id"]}',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=color_nivel,
            spaceBefore=10,
            spaceAfter=3
        )
        historia.append(Paragraph(nivel_texto, estilo_num))

        # Texto de pregunta
        historia.append(Paragraph(r['pregunta'], estilo_pregunta))

        # Opciones
        for opcion in r['opciones']:
            letra = opcion[0].upper() if opcion else ""
            letra_correcta = r['opcion_correcta'][0].upper() if r['opcion_correcta'] else ""
            letra_usuario  = r['respuesta_usuario'][0].upper() if r['respuesta_usuario'] else ""

            if letra == letra_correcta and letra == letra_usuario:
                # Correcta y seleccionada
                historia.append(Paragraph(f"✓ {opcion}  ← Tu respuesta (correcta)", estilo_opcion_correcta))
            elif letra == letra_correcta:
                # Correcta pero no seleccionada
                historia.append(Paragraph(f"✓ {opcion}  ← Respuesta correcta", estilo_opcion_correcta))
            elif letra == letra_usuario:
                # Seleccionada pero incorrecta
                historia.append(Paragraph(f"✗ {opcion}  ← Tu respuesta (incorrecta)", estilo_opcion_incorrecta))
            else:
                historia.append(Paragraph(opcion, estilo_opcion))

        # Justificación
        historia.append(Spacer(1, 4))
        historia.append(Paragraph(f"<b>Justificación:</b> {r['justificacion']}", estilo_justificacion))
        historia.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#DDDDDD')))

    # ── PIE DE PÁGINA ──
    historia.append(Spacer(1, 20))
    historia.append(HRFlowable(width="100%", thickness=1, color=DORADO))
    historia.append(Spacer(1, 6))
    historia.append(Paragraph(
        f"Hospital General de Culiacán · Cirugía Plástica y Reconstructiva · Generado el {fecha}",
        ParagraphStyle('Pie', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#888888'), alignment=TA_CENTER)
    ))

    doc.build(historia)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────────
# 5. SESSION STATE
# ─────────────────────────────────────────────
for key, val in {
    'examen_data': None,
    'answers': {},
    'examen_enviado': False,
    'modelo_nombre': None,
    'detalle_resultados': None,
    'stats_resultados': None,
    'nota_final': None
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

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

    nombre  = st.text_input("👤 Nombre del Residente", placeholder="Dr./Dra. Apellido Nombre")
    grado   = st.selectbox("🎓 Grado", ["R1", "R2", "R3", "R4 (Jefe)"])
    api_key = st.text_input("🔑 Gemini API Key", type="password", placeholder="AIza...").strip()
    pdf_file = st.file_uploader("📄 Cargar PDF Técnico", type="pdf")

    st.markdown("---")
    num_preguntas = st.slider(
        "📝 Número de preguntas",
        min_value=3,
        max_value=30,
        value=9,
        step=3,
        help="Múltiplos de 3 recomendados para distribución equitativa por nivel"
    )

    st.markdown("---")
    if api_key and pdf_file and nombre:
        st.markdown("✅ **Sistema listo**")
    else:
        faltantes = []
        if not nombre:   faltantes.append("• Nombre")
        if not api_key:  faltantes.append("• API Key")
        if not pdf_file: faltantes.append("• PDF")
        st.markdown("⚠️ **Pendiente:**\n" + "\n".join(faltantes))

    if st.session_state.modelo_nombre:
        st.markdown(f"🤖 `{st.session_state.modelo_nombre.split('/')[-1]}`")

# ─────────────────────────────────────────────
# 7. ENCABEZADO PRINCIPAL
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 10px 0;">
    <h1 style="font-family:'Playfair Display',serif; color:#001F5B; font-size:26px; margin-bottom:4px;">
        HGC — EVALUACIÓN DE ALTA ESPECIALIDAD
    </h1>
    <p style="color:#D4AF37; font-size:13px; letter-spacing:2px; text-transform:uppercase; margin:0;">
        División de Cirugía Plástica, Estética y Reconstructiva · Estudios de Posgrado e Investigación
    </p>
</div>
<hr style="border:none; border-top:2px solid #D4AF37; margin:12px 0;">
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 8. GENERACIÓN DEL EXAMEN
# ─────────────────────────────────────────────
if pdf_file and api_key and nombre:

    col1, col2 = st.columns([2, 3])
    with col1:
        generar = st.button("🚀 GENERAR EVALUACIÓN", use_container_width=True)
    with col2:
        if st.session_state.examen_data and not st.session_state.examen_enviado:
            respondidas = len([a for a in st.session_state.answers.values() if a])
            st.markdown(f"<p style='color:#001F5B; margin-top:12px;'>✅ Examen activo · {respondidas}/{len(st.session_state.examen_data)} respondidas</p>", unsafe_allow_html=True)
        if st.session_state.examen_enviado:
            if st.button("🔄 NUEVO EXAMEN", use_container_width=True):
                st.session_state.examen_data = None
                st.session_state.answers = {}
                st.session_state.examen_enviado = False
                st.session_state.detalle_resultados = None
                st.session_state.stats_resultados = None
                st.session_state.nota_final = None
                st.rerun()

    if generar:
        for k in ['examen_data','answers','examen_enviado','detalle_resultados','stats_resultados','nota_final']:
            st.session_state[k] = None if k != 'answers' else {}
        st.session_state['examen_enviado'] = False

        progress = st.progress(0)
        status   = st.empty()

        try:
            status.info("📄 Extrayendo contenido del PDF...")
            progress.progress(15)
            texto_pdf = extraer_texto_pdf(pdf_file)

            if not texto_pdf:
                st.error("❌ No se pudo extraer texto del PDF.")
                st.stop()

            status.info(f"📄 PDF procesado · {len(texto_pdf):,} caracteres")
            progress.progress(35)

            status.info("🤖 Conectando con Gemini...")
            progress.progress(50)
            model, model_name = inicializar_modelo(api_key)
            st.session_state.modelo_nombre = model_name

            status.info(f"🧠 Generando {num_preguntas} preguntas nivel Consejo...")
            progress.progress(65)

            preguntas = None
            for intento in range(3):
                try:
                    raw = generar_preguntas(model, texto_pdf, num_preguntas)
                    limpio = limpiar_json(raw)
                    preguntas = json.loads(limpio)

                    if not isinstance(preguntas, list) or len(preguntas) == 0:
                        raise ValueError("JSON inválido")

                    for p in preguntas:
                        for campo in ['id','nivel','pregunta','opciones','correcta','justificacion']:
                            if campo not in p:
                                raise ValueError(f"Falta campo: {campo}")
                    break
                except Exception as e:
                    if intento < 2:
                        status.warning(f"⚠️ Reintentando... ({intento+2}/3)")
                        time.sleep(2)
                    else:
                        raise Exception(f"No se generó JSON válido: {e}")

            progress.progress(100)
            st.session_state.examen_data = preguntas
            st.session_state.answers = {}
            st.rerun()

        except Exception as e:
            progress.empty()
            status.empty()
            msg = str(e)
            if "API_KEY" in msg or "invalid" in msg.lower():
                st.error("❌ API Key inválida. Verifica en https://aistudio.google.com/apikey")
            elif "quota" in msg.lower():
                st.error("❌ Cuota de API agotada. Espera unos minutos.")
            else:
                st.error(f"❌ Error: {msg}")

elif not nombre or not api_key or not pdf_file:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:48px;">🏥</div>
        <p style="font-size:16px; color:#666; margin-top:16px;">
            <strong>Sistema de Evaluación HGC</strong><br><br>
            Completa los campos en el panel izquierdo:<br>
            <strong>Nombre · API Key · PDF · Número de preguntas</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 9. EXAMEN
# ─────────────────────────────────────────────
if st.session_state.examen_data and not st.session_state.examen_enviado:

    examen_data = st.session_state.examen_data
    total_preg  = len(examen_data)
    respondidas = len([a for a in st.session_state.answers.values() if a])

    st.markdown(f"**Progreso:** {respondidas}/{total_preg} preguntas respondidas")
    st.progress(respondidas / total_preg if total_preg > 0 else 0)
    st.markdown("<br>", unsafe_allow_html=True)

    NIVEL_COLOR = {'Sencilla': '#2E7D32', 'Moderada': '#E65100', 'Difícil': '#C62828'}

    for item in examen_data:
        nivel  = item.get('nivel', 'Sencilla')
        color  = NIVEL_COLOR.get(nivel, '#001F5B')

        st.markdown(f"""
        <div style="background:white; border:1px solid #E8E8E8; border-left:4px solid #001F5B;
                    border-radius:8px; padding:20px 24px; margin-bottom:8px;
                    box-shadow:0 2px 8px rgba(0,31,91,0.08);">
            <div style="font-size:11px; color:#D4AF37; font-weight:600; letter-spacing:2px;
                        text-transform:uppercase; margin-bottom:6px;">
                Pregunta {item['id']} de {total_preg}
            </div>
            <span style="display:inline-block; padding:2px 10px; border-radius:12px;
                         font-size:11px; font-weight:600; letter-spacing:1px;
                         text-transform:uppercase; margin-bottom:10px;
                         background:{color}22; color:{color};">
                {nivel}
            </span>
            <div style="font-size:16px; color:#001F5B; font-weight:600; line-height:1.5;">
                {item['pregunta']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        respuesta = st.radio(
            "Selecciona:",
            item.get('opciones', []),
            key=f"radio_{item['id']}",
            label_visibility="collapsed",
            index=None
        )
        if respuesta:
            st.session_state.answers[item['id']] = respuesta

        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")

    if respondidas < total_preg:
        st.warning(f"⚠️ {total_preg - respondidas} pregunta(s) sin responder.")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        finalizar = st.button("📊 FINALIZAR Y ENVIAR A JEFATURA", use_container_width=True)

    if finalizar:
        if respondidas < total_preg:
            st.error("❌ Responde todas las preguntas antes de enviar.")
        else:
            # ─────────────────────────────────────────────
            # 10. RESULTADOS
            # ─────────────────────────────────────────────
            st.session_state.examen_enviado = True
            stats, detalle, nota, total_correctas, total_count = calcular_estadisticas(
                examen_data, st.session_state.answers
            )
            st.session_state.detalle_resultados = detalle
            st.session_state.stats_resultados   = stats
            st.session_state.nota_final         = nota

            # Calificación
            if nota >= 8:
                emoji, mensaje, color_nota = "🏆", "EXCELENTE", "#D4AF37"
            elif nota >= 6:
                emoji, mensaje, color_nota = "✅", "APROBADO", "#388E3C"
            else:
                emoji, mensaje, color_nota = "📚", "NECESITA REFUERZO", "#C62828"

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#001F5B,#003080);
                        border:2px solid #D4AF37; border-radius:12px;
                        padding:32px; text-align:center; margin:24px 0;">
                <div style="font-size:48px; margin-bottom:8px;">{emoji}</div>
                <div style="font-family:'Georgia',serif; font-size:72px; color:{color_nota}; font-weight:700; line-height:1;">
                    {nota}
                </div>
                <div style="color:#D1D1D1; font-size:14px; letter-spacing:2px; text-transform:uppercase; margin-top:8px;">
                    / 10 — {mensaje}
                </div>
                <div style="color:#D1D1D1; margin-top:12px; font-size:13px;">
                    {nombre} · {grado} · {total_correctas}/{total_count} correctas
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Métricas por nivel
            st.markdown("### 📊 Desempeño por Nivel")
            col1, col2, col3 = st.columns(3)
            for col, nivel in zip([col1, col2, col3], ['Sencilla', 'Moderada', 'Difícil']):
                s = stats.get(nivel, {"correctas": 0, "total": 0})
                pct = round((s["correctas"] / s["total"]) * 100) if s["total"] > 0 else 0
                with col:
                    st.metric(f"Nivel {nivel}", f"{s['correctas']}/{s['total']}", f"{pct}%")

            # Retroalimentación
            st.markdown("---")
            st.markdown("### 🔍 Retroalimentación Detallada")

            correctas_list   = [r for r in detalle if r['es_correcto']]
            incorrectas_list = [r for r in detalle if not r['es_correcto']]

            tab1, tab2 = st.tabs([
                f"✅ Correctas ({len(correctas_list)})",
                f"❌ Incorrectas ({len(incorrectas_list)})"
            ])

            def render_resultado(r, tab):
                with tab:
                    color_borde = "#2E7D32" if r['es_correcto'] else "#C62828"
                    bg_color    = "#F1F8F1" if r['es_correcto'] else "#FFF1F1"
                    icono       = "✅" if r['es_correcto'] else "❌"

                    st.markdown(f"""
                    <div style="background:{bg_color}; border-left:4px solid {color_borde};
                                border-radius:4px; padding:16px 20px; margin-bottom:16px;">
                        <p style="font-size:13px; font-weight:700; color:{color_borde};
                                   margin:0 0 8px 0; letter-spacing:0.5px;">
                            {icono} P{r['id']} · {r['nivel']}
                        </p>
                        <p style="font-size:14px; font-weight:600; color:#111111;
                                   margin:0 0 10px 0; line-height:1.5;">
                            {r['pregunta']}
                        </p>
                        <p style="font-size:13px; color:#222222; margin:0 0 4px 0;">
                            <strong>Tu respuesta:</strong> {r['respuesta_usuario']}
                        </p>
                        {"" if r['es_correcto'] else f'<p style="font-size:13px; color:#2E7D32; margin:0 0 4px 0;"><strong>Respuesta correcta:</strong> {r["opcion_correcta"]}</p>'}
                        <p style="font-size:12px; color:#444444; margin:10px 0 0 0;
                                   background:rgba(0,0,0,0.04); padding:8px 12px;
                                   border-radius:4px; line-height:1.6;">
                            📖 <em>{r['justificacion']}</em>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

            for r in correctas_list:
                render_resultado(r, tab1)
            if not correctas_list:
                with tab1:
                    st.info("No hubo respuestas correctas.")

            for r in incorrectas_list:
                render_resultado(r, tab2)
            if not incorrectas_list:
                with tab2:
                    st.success("🎉 ¡Todas las respuestas fueron correctas!")

            # ── ENVIAR A GOOGLE SHEETS ──
            st.markdown("---")
            errores_resumen = []
            for r in incorrectas_list:
                errores_resumen.append(f"P{r['id']} ({r['nivel']}): {r['pregunta'][:60]}... | Correcta: {r['opcion_correcta'][:30]}")

            payload = {
                "nombre":     nombre,
                "grado":      grado,
                "fecha":      datetime.now().strftime("%d/%m/%Y %H:%M"),
                "calificacion": nota,
                "total_preguntas": total_count,
                "total_correctas": total_correctas,
                "total_incorrectas": total_count - total_correctas,
                "sencillas":  f"{stats['Sencilla']['correctas']}/{stats['Sencilla']['total']}",
                "moderadas":  f"{stats['Moderada']['correctas']}/{stats['Moderada']['total']}",
                "dificiles":  f"{stats['Difícil']['correctas']}/{stats['Difícil']['total']}",
                "errores":    " | ".join(errores_resumen) if errores_resumen else "Sin errores"
            }

            with st.spinner("📤 Enviando resultados a Jefatura..."):
                try:
                    r = requests.post(URL_SHEET, json=payload, timeout=15)
                    st.success("✅ Resultados enviados a Jefatura.")
                except requests.exceptions.Timeout:
                    st.warning("⚠️ Tiempo de espera agotado al enviar.")
                except requests.exceptions.ConnectionError:
                    st.warning("⚠️ Sin conexión. Resultados no enviados.")
                except Exception as e:
                    st.warning(f"⚠️ Error al enviar: {e}")

            # ── DESCARGAR PDF ──
            st.markdown("---")
            st.markdown("### 📄 Descargar Examen Completo en PDF")

            fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            with st.spinner("📄 Generando PDF..."):
                try:
                    pdf_buffer = generar_pdf_examen(
                        nombre, grado, examen_data,
                        detalle, stats, nota, fecha_str
                    )
                    st.download_button(
                        label="⬇️ DESCARGAR PDF DEL EXAMEN",
                        data=pdf_buffer,
                        file_name=f"HGC_Examen_{nombre.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("✅ PDF generado correctamente.")
                except Exception as e:
                    st.error(f"❌ Error al generar PDF: {e}")

            # ── NUEVO EXAMEN ──
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 GENERAR NUEVO EXAMEN", use_container_width=True):
                    st.session_state.examen_data = None
                    st.session_state.answers = {}
                    st.session_state.examen_enviado = False
                    st.session_state.detalle_resultados = None
                    st.session_state.stats_resultados = None
                    st.session_state.nota_final = None
                    st.rerun()

elif st.session_state.examen_enviado:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:48px;">✅</div>
        <p style="font-size:16px; color:#333; margin-top:16px;">
            <strong>Examen completado y enviado a Jefatura.</strong><br>
            Usa el botón "NUEVO EXAMEN" para continuar.
        </p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 NUEVO EXAMEN", use_container_width=True):
            st.session_state.examen_data = None
            st.session_state.answers = {}
            st.session_state.examen_enviado = False
            st.session_state.detalle_resultados = None
            st.session_state.stats_resultados = None
            st.session_state.nota_final = None
            st.rerun()
