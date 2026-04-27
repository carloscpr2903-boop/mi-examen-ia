import streamlit as st
import pypdf
import json
import requests
import time
import re
import io
import os
from datetime import datetime
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

st.set_page_config(page_title="HGC - Cirugía Plástica", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

# API KEY
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ESTILOS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap');
.stApp { background-color: #FAF9F6 !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #FFFFFF 15%, #001F5B 25%, #001F5B 100%) !important;
    border-right: 2px solid #D4AF37 !important;
}
[data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stFileUploader label, [data-testid="stSidebar"] .stSlider label {
    color: #D1D1D1 !important; font-size: 13px !important;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #D4AF37 !important; font-family: 'Playfair Display', serif !important; text-align: center !important;
}
div.stButton > button {
    background: linear-gradient(135deg, #D4AF37, #B8960C) !important;
    color: #001F5B !important; font-weight: 700 !important; letter-spacing: 1.5px !important;
    text-transform: uppercase !important; border: none !important; border-radius: 4px !important;
    padding: 12px 24px !important; font-size: 13px !important; box-shadow: 0 2px 8px rgba(212,175,55,0.4) !important;
}
.stRadio label { font-size: 15px !important; color: #111111 !important; }
.stRadio > div { gap: 8px !important; }
div[data-testid="stRadio"] label { color: #111111 !important; }
div[data-testid="stRadio"] label span { color: #111111 !important; }
div[data-testid="stRadio"] p { color: #111111 !important; }
</style>
""", unsafe_allow_html=True)

URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

# ─── FUNCIONES ───

def extraer_texto_pdf(pdf_file):
    try:
        reader = pypdf.PdfReader(pdf_file)
        texto = ""
        for i, page in enumerate(reader.pages):
            t = page.extract_text()
            if t:
                texto += f"\n--- Página {i+1} ---\n{t}"
        return texto.strip()
    except:
        return None

def limpiar_json(texto):
    texto = re.sub(r'```json\s*', '', texto)
    texto = re.sub(r'```\s*', '', texto)
    texto = texto.strip()
    match = re.search(r'\[[\s\S]*\]', texto)
    return match.group(0) if match else texto

def generar_preguntas(texto_pdf, num_total):
    """Genera preguntas clínicas REALES basadas 100% en el PDF"""
    base = num_total // 3
    resto = num_total % 3
    n_sencilla = base + (1 if resto >= 1 else 0)
    n_moderada = base + (1 if resto >= 2 else 0)
    n_dificil = base

    prompt = f"""INSTRUCCIÓN CRÍTICA: Eres un experto evaluador clínico del Consejo Mexicano de Cirugía Plástica, Estética y Reconstructiva. 

CONTENIDO DEL DOCUMENTO A USAR:
{texto_pdf[:15000]}

GENERA EXACTAMENTE {num_total} PREGUNTAS DE EXAMEN NIVEL CONSEJO.

REQUISITOS OBLIGATORIOS - LEE CUIDADOSAMENTE:

1. IDIOMA: **ÚNICAMENTE ESPAÑOL** - Sin palabras en inglés. Sin mezcla.

2. ESPECIFICIDAD: Cada pregunta debe:
   - Citar DIRECTAMENTE conceptos, números, estructuras, técnicas del PDF
   - NO ser genérica (no "¿Qué es la facelift?" sino "¿Cuál es la profundidad exacta del SMAS en brow lift?")
   - Requerir conocimiento clínico específico del documento

3. OPCIONES: 
   - A, B, C, D deben ser DIFERENTES entre preguntas
   - Distractores clínicamente plausibles (no obvias)
   - UNA sola respuesta correcta inequívoca

4. JUSTIFICACIÓN:
   - Citar TEXTUALMENTE la sección relevante del PDF
   - Explicar POR QUÉ las otras opciones son incorrectas
   - Mínimo 3 oraciones

5. DISTRIBUCIÓN:
   - {n_sencilla} preguntas "Sencilla" (anatomía básica, indicaciones directas del PDF)
   - {n_moderada} preguntas "Moderada" (decisiones clínicas basadas en el contenido)
   - {n_dificil} preguntas "Difícil" (casos clínicos complejos, razonamiento quirúrgico)

RESPONDE ÚNICAMENTE EN JSON VÁLIDO. Sin texto adicional. Sin backticks:

[
  {{
    "id": 1,
    "nivel": "Sencilla",
    "pregunta": "¿Cuál es [concepto específico del PDF]?",
    "opciones": ["A) [opción diferente]", "B) [opción diferente]", "C) [opción diferente]", "D) [opción diferente]"],
    "correcta": "A",
    "justificacion": "Según el documento: [cita textual]. [Explicación de por qué es correcta]. [Por qué las otras son incorrectas]."
  }}
]"""

    client = Groq(api_key=GROQ_API_KEY)
    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=6000
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error Groq: {str(e)}")

def calcular_estadisticas(examen_data, answers):
    stats = {
        "Sencilla": {"correctas": 0, "total": 0},
        "Moderada": {"correctas": 0, "total": 0},
        "Difícil": {"correctas": 0, "total": 0}
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
    """Genera PDF profesional con examen completo"""
    buffer = io.BytesIO()

    NAVY = colors.HexColor('#001F5B')
    DORADO = colors.HexColor('#D4AF37')
    GRIS = colors.HexColor('#F5F5F5')
    VERDE = colors.HexColor('#2E7D32')
    ROJO = colors.HexColor('#C62828')
    NEGRO = colors.black
    BLANCO = colors.white

    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          leftMargin=0.75*inch, rightMargin=0.75*inch,
                          topMargin=0.75*inch, bottomMargin=0.75*inch)

    historia = []
    styles = getSampleStyleSheet()

    # ENCABEZADO
    titulo = ParagraphStyle('Titulo', fontName='Helvetica-Bold', fontSize=16, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4)
    subtitulo = ParagraphStyle('Sub', fontName='Helvetica', fontSize=10, textColor=DORADO, alignment=TA_CENTER, spaceAfter=2)

    historia.append(Paragraph("HGC — EVALUACIÓN DE ALTA ESPECIALIDAD", titulo))
    historia.append(Paragraph("División de Cirugía Plástica, Estética y Reconstructiva", subtitulo))
    historia.append(Paragraph("División de Estudios de Posgrado e Investigación", subtitulo))
    historia.append(Spacer(1, 6))
    historia.append(HRFlowable(width="100%", thickness=2, color=DORADO))
    historia.append(Spacer(1, 8))

    # DATOS
    total_correctas = sum(s["correctas"] for s in stats.values())
    total_preg = sum(s["total"] for s in stats.values())

    estilo_dato = ParagraphStyle('Dato', fontName='Helvetica', fontSize=10, textColor=NEGRO, leading=14)
    tabla_datos = Table([
        [Paragraph("<b>Residente:</b>", estilo_dato), Paragraph(nombre, estilo_dato),
         Paragraph("<b>Fecha:</b>", estilo_dato), Paragraph(fecha, estilo_dato)],
        [Paragraph("<b>Grado:</b>", estilo_dato), Paragraph(grado, estilo_dato),
         Paragraph("<b>Calificación:</b>", estilo_dato), Paragraph(f"{nota}/10", estilo_dato)],
        [Paragraph("<b>Total preguntas:</b>", estilo_dato), Paragraph(str(total_preg), estilo_dato),
         Paragraph("<b>Correctas:</b>", estilo_dato), Paragraph(f"{total_correctas}/{total_preg}", estilo_dato)],
    ], colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])

    tabla_datos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GRIS),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    historia.append(tabla_datos)
    historia.append(Spacer(1, 10))

    # RESUMEN
    historia.append(Paragraph("RESUMEN DE DESEMPEÑO POR NIVEL", 
                             ParagraphStyle('Sec', fontName='Helvetica-Bold', fontSize=12, textColor=NAVY, spaceBefore=14, spaceAfter=6)))
    historia.append(HRFlowable(width="100%", thickness=1, color=DORADO))
    historia.append(Spacer(1, 6))

    filas = [[Paragraph("<b>Nivel</b>", estilo_dato), Paragraph("<b>Correctas</b>", estilo_dato),
              Paragraph("<b>Total</b>", estilo_dato), Paragraph("<b>Porcentaje</b>", estilo_dato)]]
    for nivel in ['Sencilla', 'Moderada', 'Difícil']:
        s = stats.get(nivel, {"correctas": 0, "total": 0})
        pct = round((s['correctas'] / s['total']) * 100) if s['total'] > 0 else 0
        filas.append([Paragraph(nivel, estilo_dato), Paragraph(str(s['correctas']), estilo_dato),
                      Paragraph(str(s['total']), estilo_dato), Paragraph(f"{pct}%", estilo_dato)])

    tabla_stats = Table(filas, colWidths=[1.8*inch, 1.5*inch, 1.5*inch, 1.8*inch])
    tabla_stats.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('TEXTCOLOR', (0,0), (-1,0), BLANCO),
        ('BACKGROUND', (0,1), (-1,-1), GRIS),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
    ]))
    historia.append(tabla_stats)
    historia.append(PageBreak())

    # PREGUNTAS Y RESPUESTAS
    historia.append(Paragraph("EXAMEN COMPLETO CON SOLUCIONES", 
                             ParagraphStyle('Sec', fontName='Helvetica-Bold', fontSize=14, textColor=NAVY, spaceBefore=14, spaceAfter=6)))
    historia.append(HRFlowable(width="100%", thickness=2, color=DORADO))
    historia.append(Spacer(1, 10))

    estilo_preg = ParagraphStyle('Preg', fontName='Helvetica-Bold', fontSize=11, textColor=NEGRO, spaceBefore=10, spaceAfter=4, leading=14)
    estilo_opcion = ParagraphStyle('Op', fontName='Helvetica', fontSize=10, textColor=NEGRO, leftIndent=16, spaceAfter=2, leading=13)
    estilo_opcion_correcta = ParagraphStyle('OpC', fontName='Helvetica-Bold', fontSize=10, textColor=VERDE, leftIndent=16, spaceAfter=2, leading=13)
    estilo_opcion_incorrecta = ParagraphStyle('OpI', fontName='Helvetica', fontSize=10, textColor=ROJO, leftIndent=16, spaceAfter=2, leading=13)
    estilo_just = ParagraphStyle('Just', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#333333'), leftIndent=16, spaceBefore=6, spaceAfter=8, leading=13, backColor=GRIS, borderPadding=8)

    for r in detalle:
        color_nivel = VERDE if r['es_correcto'] else ROJO
        estado = "✓ CORRECTA" if r['es_correcto'] else "✗ INCORRECTA"
        
        historia.append(Paragraph(f"<b>Pregunta {r['id']} | {r['nivel']} | {estado}</b>",
                                 ParagraphStyle(f'N{r["id"]}', fontName='Helvetica-Bold', fontSize=10,
                                               textColor=color_nivel, spaceBefore=10, spaceAfter=4)))
        historia.append(Paragraph(r['pregunta'], estilo_preg))

        for opcion in r['opciones']:
            letra = opcion[0].upper() if opcion else ""
            letra_correcta = r['opcion_correcta'][0].upper() if r['opcion_correcta'] else ""
            letra_usuario = r['respuesta_usuario'][0].upper() if r['respuesta_usuario'] else ""

            if letra == letra_correcta and letra == letra_usuario:
                historia.append(Paragraph(f"✓ {opcion} ← TU RESPUESTA (CORRECTA)", estilo_opcion_correcta))
            elif letra == letra_correcta:
                historia.append(Paragraph(f"✓ {opcion} ← RESPUESTA CORRECTA", estilo_opcion_correcta))
            elif letra == letra_usuario:
                historia.append(Paragraph(f"✗ {opcion} ← TU RESPUESTA (INCORRECTA)", estilo_opcion_incorrecta))
            else:
                historia.append(Paragraph(opcion, estilo_opcion))

        historia.append(Spacer(1, 4))
        historia.append(Paragraph(f"<b>JUSTIFICACIÓN:</b> {r['justificacion']}", estilo_just))
        historia.append(Spacer(1, 8))
        historia.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#DDDDDD')))
        historia.append(Spacer(1, 4))

    # PIE
    historia.append(Spacer(1, 20))
    historia.append(HRFlowable(width="100%", thickness=1, color=DORADO))
    historia.append(Spacer(1, 6))
    historia.append(Paragraph(f"Hospital General de Culiacán · Cirugía Plástica y Reconstructiva · {fecha}",
                             ParagraphStyle('Pie', fontName='Helvetica', fontSize=8,
                                           textColor=colors.HexColor('#888888'), alignment=TA_CENTER)))

    doc.build(historia)
    buffer.seek(0)
    return buffer

# SESSION STATE
for key, val in {'examen_data': None, 'answers': {}, 'examen_enviado': False,
                 'detalle_resultados': None, 'stats_resultados': None, 'nota_final': None}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# SIDEBAR
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
    pdf_file = st.file_uploader("📄 Cargar PDF Técnico", type="pdf")

    st.markdown("---")
    num_preguntas = st.slider("📝 Número de preguntas", min_value=3, max_value=30, value=9, step=3,
                             help="Múltiplos de 3 para distribución equitativa")

    st.markdown("---")
    if nombre and pdf_file:
        st.markdown("✅ **Sistema listo**")
    else:
        faltantes = []
        if not nombre:
            faltantes.append("• Nombre")
        if not pdf_file:
            faltantes.append("• PDF")
        st.markdown("⚠️ **Pendiente:**\n" + "\n".join(faltantes))

    if not GROQ_API_KEY:
        st.error("⚙️ API Key no configurada.")

# ENCABEZADO
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

# GENERACIÓN
if pdf_file and nombre and GROQ_API_KEY:
    col1, col2 = st.columns([2, 3])
    with col1:
        generar = st.button("🚀 GENERAR EVALUACIÓN", use_container_width=True)
    with col2:
        if st.session_state.examen_data and not st.session_state.examen_enviado:
            respondidas = len([a for a in st.session_state.answers.values() if a])
            st.markdown(f"<p style='color:#001F5B; margin-top:12px;'>✅ Examen activo · {respondidas}/{len(st.session_state.examen_data)} respondidas</p>", unsafe_allow_html=True)
        if st.session_state.examen_enviado:
            if st.button("🔄 NUEVO EXAMEN", use_container_width=True):
                for k in ['examen_data','answers','examen_enviado','detalle_resultados','stats_resultados','nota_final']:
                    st.session_state[k] = None if k != 'answers' else {}
                st.rerun()

    if generar:
        for k in ['examen_data','answers','examen_enviado','detalle_resultados','stats_resultados','nota_final']:
            st.session_state[k] = None if k != 'answers' else {}

        error_msg = None
        preguntas = None

        with st.status("Generando examen clínico...", expanded=True) as status:
            try:
                st.write("📄 Extrayendo contenido del PDF...")
                texto_pdf = extraer_texto_pdf(pdf_file)
                if not texto_pdf:
                    raise Exception("No se pudo extraer texto del PDF.")
                st.write(f"✅ PDF procesado · {len(texto_pdf):,} caracteres")

                st.write(f"🧠 Generando {num_preguntas} preguntas clínicas basadas en el documento...")
                for intento in range(3):
                    try:
                        raw = generar_preguntas(texto_pdf, num_preguntas)
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
                            st.write(f"⚠️ Reintentando... ({intento+2}/3)")
                            time.sleep(2)
                        else:
                            raise Exception(f"Error JSON: {e}")

                status.update(label="✅ Examen generado", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ Error al generar", state="error", expanded=True)
                error_msg = str(e)

        if error_msg:
            st.error(f"❌ {error_msg}")
        elif preguntas:
            st.session_state.examen_data = preguntas
            st.session_state.answers = {}
            st.rerun()

elif not GROQ_API_KEY:
    st.error("⚙️ La API Key no está configurada. Contacta al administrador.")
elif not nombre or not pdf_file:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:48px;">🏥</div>
        <p style="font-size:16px; color:#666; margin-top:16px;">
            <strong>Sistema de Evaluación HGC</strong><br><br>
            Completa: <strong>Nombre · PDF · Número de preguntas</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

# EXAMEN
if st.session_state.examen_data and not st.session_state.examen_enviado:
    examen_data = st.session_state.examen_data
    total_preg = len(examen_data)
    respondidas = len([a for a in st.session_state.answers.values() if a])

    st.markdown(f"**Progreso:** {respondidas}/{total_preg} preguntas respondidas")
    st.progress(respondidas / total_preg if total_preg > 0 else 0)
    st.markdown("<br>", unsafe_allow_html=True)

    NIVEL_COLOR = {'Sencilla': '#2E7D32', 'Moderada': '#E65100', 'Difícil': '#C62828'}

    for item in examen_data:
        nivel = item.get('nivel', 'Sencilla')
        color = NIVEL_COLOR.get(nivel, '#001F5B')

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
            st.session_state.examen_enviado = True
            stats, detalle, nota, total_correctas, total_count = calcular_estadisticas(
                examen_data, st.session_state.answers
            )
            st.session_state.detalle_resultados = detalle
            st.session_state.stats_resultados = stats
            st.session_state.nota_final = nota

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

            st.markdown("### 📊 Desempeño por Nivel")
            col1, col2, col3 = st.columns(3)
            for col, nivel in zip([col1, col2, col3], ['Sencilla', 'Moderada', 'Difícil']):
                s = stats.get(nivel, {"correctas": 0, "total": 0})
                pct = round((s["correctas"] / s["total"]) * 100) if s["total"] > 0 else 0
                with col:
                    st.metric(f"Nivel {nivel}", f"{s['correctas']}/{s['total']}", f"{pct}%")

            # GOOGLE SHEETS
            st.markdown("---")
            errores_resumen = [
                f"P{r['id']} ({r['nivel']}): {r['pregunta'][:60]}..."
                for r in detalle if not r['es_correcto']
            ]
            payload = {
                "nombre": nombre, "grado": grado,
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "calificacion": nota,
                "total_preguntas": total_count,
                "total_correctas": total_correctas,
                "total_incorrectas": total_count - total_correctas,
                "sencillas": f"{stats['Sencilla']['correctas']}/{stats['Sencilla']['total']}",
                "moderadas": f"{stats['Moderada']['correctas']}/{stats['Moderada']['total']}",
                "dificiles": f"{stats['Difícil']['correctas']}/{stats['Difícil']['total']}",
                "errores": " | ".join(errores_resumen) if errores_resumen else "Sin errores"
            }

            with st.spinner("📤 Enviando resultados a Jefatura..."):
                try:
                    requests.post(URL_SHEET, json=payload, timeout=15)
                    st.success("✅ Resultados enviados a Jefatura.")
                except:
                    st.warning("⚠️ No se pudo enviar, pero el PDF se generó.")

            # PDF - ESTO SIEMPRE SE GENERA
            st.markdown("---")
            st.markdown("### 📄 Descargar Examen Completo con Soluciones")
            fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            with st.spinner("📄 Generando PDF con todo el examen y soluciones..."):
                try:
                    pdf_buffer = generar_pdf_examen(
                        nombre, grado, examen_data,
                        detalle, stats, nota, fecha_str
                    )
                    st.download_button(
                        label="⬇️ DESCARGAR PDF EXAMEN + SOLUCIONES",
                        data=pdf_buffer,
                        file_name=f"HGC_{nombre.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("✅ PDF generado: examen completo + respuestas + justificaciones")
                except Exception as e:
                    st.error(f"❌ Error PDF: {e}")

            # NUEVO EXAMEN
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 GENERAR NUEVO EXAMEN", use_container_width=True):
                    for k in ['examen_data','answers','examen_enviado','detalle_resultados','stats_resultados','nota_final']:
                        st.session_state[k] = None if k != 'answers' else {}
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
            for k in ['examen_data','answers','examen_enviado','detalle_resultados','stats_resultados','nota_final']:
                st.session_state[k] = None if k != 'answers' else {}
            st.rerun()
