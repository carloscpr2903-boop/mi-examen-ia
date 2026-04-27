import streamlit as st
import pypdf
import json
import requests
import time
import re
import io
import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

st.set_page_config(page_title="HGC - Cirugía Plástica", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

try:
    GMAIL_USER = st.secrets.get("GMAIL_USER", "")
    GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD", "")
except:
    GMAIL_USER = os.environ.get("GMAIL_USER", "")
    GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")

OLLAMA_URL = "http://localhost:11434/api/generate"

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
div[data-testid="stRadio"] label, div[data-testid="stRadio"] label span,
div[data-testid="stRadio"] p { color: #111111 !important; }
</style>
""", unsafe_allow_html=True)

def consultar_ollama(prompt, temperatura=0.5):
    """Consulta Ollama local con optimización de calidad"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama2",
                "prompt": prompt,
                "stream": False,
                "temperature": temperatura,
                "top_p": 0.9,
                "top_k": 40,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["response"]
        else:
            raise Exception(f"Error Ollama: {response.status_code}")
    except Exception as e:
        raise Exception(f"No se puede conectar a Ollama. ¿Está corriendo? {str(e)}")

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

def crear_base_conocimiento(textos_capitulos):
    """FASE 1: Análisis estructurado profundo"""
    texto_completo = "\n\n===== NUEVO CAPÍTULO =====\n\n".join(textos_capitulos)
    
    prompt = f"""INSTRUCCIÓN CRÍTICA: ERES UN EXPERTO EN CIRUGÍA PLÁSTICA DEL CONSEJO MEXICANO.

ANALIZA ESTOS CAPÍTULOS CON MÁXIMA PROFUNDIDAD:
{texto_completo[:12000]}

EXTRAE INFORMACIÓN ESTRUCTURADA EN 8 APARTADOS. SÉ ESPECÍFICO, DETALLADO Y PRECISO:

1. DEFINICIÓN Y CONCEPTOS CLAVE - Términos exactos, sinónimos clínicos
2. ANATOMÍA PERTINENTE - Estructuras específicas, nervios, vasos, planos exactos
3. FISIOPATOLOGÍA - Mecanismos exactos de enfermedad, cambios celulares
4. CLASIFICACIONES - TODOS los sistemas: Matarasso, Huger, Bozola, etc.
5. TRATAMIENTO QUIRÚRGICO - Indicaciones, contraindicaciones, técnicas paso a paso
6. TRATAMIENTO NO QUIRÚRGICO - Cuándo NO operar, alternativas exactas
7. PRONÓSTICO Y COMPLICACIONES - Complicaciones específicas, incidencias, resolución
8. PROCEDIMIENTOS SECUNDARIOS - Complementos, timing exacto, cuándo aplicar

RESPONDE ÚNICAMENTE EN JSON VÁLIDO:

{{
  "definicion": "TEXTO DETALLADO Y PRECISO",
  "anatomia": "TEXTO DETALLADO Y PRECISO",
  "fisiopatologia": "TEXTO DETALLADO Y PRECISO",
  "clasificaciones": "TEXTO DETALLADO Y PRECISO",
  "tratamiento_quirurgico": "TEXTO DETALLADO Y PRECISO",
  "tratamiento_no_quirurgico": "TEXTO DETALLADO Y PRECISO",
  "pronostico_complicaciones": "TEXTO DETALLADO Y PRECISO",
  "procedimientos_secundarios": "TEXTO DETALLADO Y PRECISO"
}}

JSON VÁLIDO. SIN BACKTICKS. SIN TEXTO ADICIONAL."""

    try:
        respuesta = consultar_ollama(prompt, temperatura=0.3)
        
        inicio = respuesta.find('{')
        final = respuesta.rfind('}')
        if inicio >= 0 and final > inicio:
            respuesta = respuesta[inicio:final+1]
        
        base = json.loads(respuesta)
        campos = ['definicion', 'anatomia', 'fisiopatologia', 'clasificaciones', 
                 'tratamiento_quirurgico', 'tratamiento_no_quirurgico', 
                 'pronostico_complicaciones', 'procedimientos_secundarios']
        
        for campo in campos:
            if campo not in base or not base[campo]:
                base[campo] = "Información no disponible"
        
        return base
    except Exception as e:
        raise Exception(f"Error análisis: {str(e)}")

def generar_casos_clinicos(base_conocimiento, num_preguntas):
    """FASE 2: Genera casos clínicos PROFUNDOS con chain-of-thought"""
    
    base = num_preguntas // 3
    resto = num_preguntas % 3
    n_sencilla = base + (1 if resto >= 1 else 0)
    n_moderada = base + (1 if resto >= 2 else 0)
    n_dificil = base

    contexto = f"""DEFINICIÓN: {base_conocimiento.get('definicion', '')}

ANATOMÍA: {base_conocimiento.get('anatomia', '')}

FISIOPATOLOGÍA: {base_conocimiento.get('fisiopatologia', '')}

CLASIFICACIONES: {base_conocimiento.get('clasificaciones', '')}

TRATAMIENTO QUIRÚRGICO: {base_conocimiento.get('tratamiento_quirurgico', '')}

TRATAMIENTO NO QUIRÚRGICO: {base_conocimiento.get('tratamiento_no_quirurgico', '')}

PRONÓSTICO/COMPLICACIONES: {base_conocimiento.get('pronostico_complicaciones', '')}

PROCEDIMIENTOS SECUNDARIOS: {base_conocimiento.get('procedimientos_secundarios', '')}"""

    prompt = f"""ERES EXAMINADOR DEL CONSEJO MEXICANO. GENERA CASOS CLÍNICOS REALES Y PROFUNDOS.

BASE DE CONOCIMIENTO:
{contexto}

GENERA EXACTAMENTE {num_preguntas} CASOS CLÍNICOS TIPO CONSEJO:

{n_sencilla} SENCILLAS: Diagnóstico directo + clasificación + anatomía
{n_moderada} MODERADAS: Caso + decisión quirúrgica vs no quirúrgica + indicaciones
{n_dificil} DIFÍCILES: Caso complejo + complicación + razonamiento + procedimientos secundarios

CADA CASO DEBE:
- Describir paciente con edad, síntomas, hallazgos clínicos ESPECÍFICOS
- Requerer diagnóstico, clasificación, decisión terapéutica SIMULTÁNEAMENTE
- Tener 4 opciones CLÍNICAMENTE DIFERENTES (no triviales)
- Justificación que cite definición, fisiopatología, clasificación, por qué es correcta

RAZONAMIENTO: Primero piensa la respuesta correcta, luego por qué las otras son incorrectas.

RESPONDE EN JSON VÁLIDO:

[
  {{
    "id": 1,
    "nivel": "Sencilla",
    "caso": "CASO CLÍNICO COMPLETO CON DETALLES",
    "pregunta": "¿CUÁL ES LA DIAGNOSIS O DECISIÓN CORRECTA?",
    "opciones": ["A) [opción clínica]", "B) [opción clínica]", "C) [opción clínica]", "D) [opción clínica]"],
    "correcta": "A",
    "justificacion": "JUSTIFICACIÓN PROFUNDA"
  }}
]

JSON VÁLIDO. SIN BACKTICKS. SIN TEXTO ADICIONAL."""

    try:
        respuesta = consultar_ollama(prompt, temperatura=0.6)
        
        inicio = respuesta.find('[')
        final = respuesta.rfind(']')
        if inicio >= 0 and final > inicio:
            respuesta = respuesta[inicio:final+1]
        
        preguntas = json.loads(respuesta)
        
        if not isinstance(preguntas, list):
            raise ValueError("No es una lista")
        
        return preguntas
    except Exception as e:
        raise Exception(f"Error generación: {str(e)}")

def enviar_email_pdf(destinatario, nombre_residente, grado, nota, pdf_buffer):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = destinatario
        msg['Subject'] = f"Examen HGC - {nombre_residente} ({grado}) - {nota}/10"

        body = f"""Examen HGC - {nombre_residente} ({grado})
Calificación: {nota}/10
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

PDF adjunto con examen completo y soluciones."""

        msg.attach(MIMEText(body, 'plain'))
        attachment = MIMEApplication(pdf_buffer.read(), _subtype="pdf")
        attachment.add_header('Content-Disposition', 'attachment',
                             filename=f"HGC_{nombre_residente.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        msg.attach(attachment)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)

        return True, "Enviado"
    except Exception as e:
        return False, str(e)

def calcular_estadisticas(examen_data, answers):
    stats = {"Sencilla": {"correctas": 0, "total": 0}, "Moderada": {"correctas": 0, "total": 0}, "Difícil": {"correctas": 0, "total": 0}}
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

        detalle.append({"id": item['id'], "nivel": nivel, "caso": item.get('caso', ''), "pregunta": item['pregunta'], "opciones": item['opciones'], "opcion_correcta": opcion_correcta, "respuesta_usuario": respuesta_usuario, "es_correcto": es_correcto, "justificacion": item.get('justificacion', '')})

    total_correctas = sum(s["correctas"] for s in stats.values())
    total_preg = sum(s["total"] for s in stats.values())
    nota = round((total_correctas / total_preg) * 10, 1) if total_preg > 0 else 0
    return stats, detalle, nota, total_correctas, total_preg

def generar_pdf_examen(nombre, grado, examen_data, detalle, stats, nota, fecha):
    buffer = io.BytesIO()
    NAVY = colors.HexColor('#001F5B')
    DORADO = colors.HexColor('#D4AF37')
    GRIS = colors.HexColor('#F5F5F5')
    VERDE = colors.HexColor('#2E7D32')
    ROJO = colors.HexColor('#C62828')

    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
    historia = []

    titulo = ParagraphStyle('Titulo', fontName='Helvetica-Bold', fontSize=16, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4)
    subtitulo = ParagraphStyle('Sub', fontName='Helvetica', fontSize=10, textColor=DORADO, alignment=TA_CENTER, spaceAfter=2)

    historia.append(Paragraph("HGC — EVALUACIÓN DE ALTA ESPECIALIDAD", titulo))
    historia.append(Paragraph("División de Cirugía Plástica, Estética y Reconstructiva", subtitulo))
    historia.append(Spacer(1, 6))
    historia.append(HRFlowable(width="100%", thickness=2, color=DORADO))
    historia.append(Spacer(1, 8))

    total_correctas = sum(s["correctas"] for s in stats.values())
    total_preg = sum(s["total"] for s in stats.values())

    estilo_dato = ParagraphStyle('Dato', fontName='Helvetica', fontSize=10, textColor=colors.black, leading=14)
    tabla_datos = Table([[Paragraph(f"<b>Residente:</b>", estilo_dato), Paragraph(nombre, estilo_dato), Paragraph(f"<b>Fecha:</b>", estilo_dato), Paragraph(fecha, estilo_dato)], [Paragraph(f"<b>Grado:</b>", estilo_dato), Paragraph(grado, estilo_dato), Paragraph(f"<b>Calificación:</b>", estilo_dato), Paragraph(f"{nota}/10", estilo_dato)], [Paragraph(f"<b>Total preguntas:</b>", estilo_dato), Paragraph(str(total_preg), estilo_dato), Paragraph(f"<b>Correctas:</b>", estilo_dato), Paragraph(f"{total_correctas}/{total_preg}", estilo_dato)]], colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
    tabla_datos.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), GRIS), ('BOX', (0,0), (-1,-1), 1, NAVY), ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')), ('PADDING', (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    historia.append(tabla_datos)
    historia.append(Spacer(1, 10))
    historia.append(PageBreak())

    estilo_preg = ParagraphStyle('Preg', fontName='Helvetica-Bold', fontSize=11, textColor=colors.black, spaceBefore=8, spaceAfter=4, leading=14)
    estilo_opcion_correcta = ParagraphStyle('OpC', fontName='Helvetica-Bold', fontSize=10, textColor=VERDE, leftIndent=16, spaceAfter=2, leading=13)
    estilo_opcion_incorrecta = ParagraphStyle('OpI', fontName='Helvetica', fontSize=10, textColor=ROJO, leftIndent=16, spaceAfter=2, leading=13)
    estilo_just = ParagraphStyle('Just', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#333333'), leftIndent=16, spaceBefore=6, spaceAfter=8, leading=13, backColor=GRIS, borderPadding=8)

    for r in detalle:
        color_nivel = VERDE if r['es_correcto'] else ROJO
        estado = "✓ CORRECTA" if r['es_correcto'] else "✗ INCORRECTA"
        historia.append(Paragraph(f"<b>P{r['id']} | {r['nivel']} | {estado}</b>", ParagraphStyle(f'N{r["id"]}', fontName='Helvetica-Bold', fontSize=10, textColor=color_nivel, spaceBefore=10, spaceAfter=4)))
        if r['caso']:
            historia.append(Paragraph(f"<b>CASO:</b> {r['caso']}", ParagraphStyle('Caso', fontName='Helvetica-Oblique', fontSize=10, textColor=colors.black, leftIndent=12, spaceBefore=6, spaceAfter=4, leading=13)))
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
        historia.append(Spacer(1, 4))
        historia.append(Paragraph(f"<b>JUSTIFICACIÓN:</b> {r['justificacion']}", estilo_just))
        historia.append(Spacer(1, 8))

    doc.build(historia)
    buffer.seek(0)
    return buffer

for key, val in {'capitulos': {}, 'bloques': {}, 'examen_data': None, 'answers': {}, 'examen_enviado': False}.items():
    if key not in st.session_state:
        st.session_state[key] = val

with st.sidebar:
    st.markdown("### 🏥 HGC CONSEJO")
    st.markdown("---")
    st.markdown("### 📚 Cargar Capítulos")
    archivos = st.file_uploader("PDFs", type="pdf", accept_multiple_files=True)
    if archivos:
        for pdf in archivos:
            nombre_cap = st.text_input(f"Nombre: {pdf.name[:20]}", value=pdf.name.replace('.pdf', ''), key=f"nombre_{pdf.name}")
            if nombre_cap and pdf.name not in st.session_state.capitulos:
                texto = extraer_texto_pdf(pdf)
                if texto:
                    st.session_state.capitulos[nombre_cap] = texto
                    st.success(f"✅ {nombre_cap}")
    if st.session_state.capitulos:
        st.markdown("---")
        for cap in st.session_state.capitulos.keys():
            st.write(f"✓ {cap}")
    st.markdown("---")
    nombre_bloque = st.text_input("Nombre bloque", placeholder="Ej: Facelift")
    if st.session_state.capitulos and nombre_bloque:
        caps_sel = st.multiselect("Selecciona", list(st.session_state.capitulos.keys()), key=f"bloque_{nombre_bloque}")
        if st.button("➕ Crear", use_container_width=True):
            if caps_sel:
                st.session_state.bloques[nombre_bloque] = caps_sel
                st.rerun()
    if st.session_state.bloques:
        st.markdown("---")
        for bn, cs in st.session_state.bloques.items():
            st.write(f"**{bn}** ({len(cs)})")

st.markdown("<div style='text-align:center; padding:10px;'><h1 style='font-family:Playfair Display,serif; color:#001F5B;'>HGC — CASOS CLÍNICOS CONSEJO</h1><p style='color:#D4AF37; font-size:12px;'>Ollama Local • Sin límites</p></div><hr style='border:none; border-top:2px solid #D4AF37;'>", unsafe_allow_html=True)

if st.session_state.bloques:
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col1:
        nombre = st.text_input("👤 Residente", placeholder="Dr./Dra. Apellido")
    with col2:
        grado = st.selectbox("🎓 Grado", ["R1", "R2", "R3", "R4"])
    with col3:
        bloque_sel = st.selectbox("📚 Bloque", list(st.session_state.bloques.keys()), key="bloque_selector")
    st.markdown("---")
    num_preg = st.slider("📝 Casos clínicos", min_value=3, max_value=150, value=9, step=3)
    st.markdown("---")
    generar = st.button("🚀 GENERAR", use_container_width=True)

    if generar and bloque_sel and nombre:
        caps_bloque = st.session_state.bloques[bloque_sel]
        textos = [st.session_state.capitulos[cap] for cap in caps_bloque]
        error_msg = None
        base_conocimiento = None
        preguntas = None

        with st.status(f"Generando {num_preg} casos...", expanded=True) as status:
            try:
                st.write(f"📚 Analizando {len(caps_bloque)} capítulos...")
                st.write("🔍 FASE 1: Extrayendo base estructurada...")
                base_conocimiento = crear_base_conocimiento(textos)
                st.write("✅ Base creada")
                st.write(f"📋 FASE 2: Generando {num_preg} casos...")
                preguntas = generar_casos_clinicos(base_conocimiento, num_preg)
                st.write(f"✅ {len(preguntas)} casos generados")
                status.update(label=f"✅ {len(preguntas)} casos", state="complete")
            except Exception as e:
                status.update(label="❌ Error", state="error")
                error_msg = str(e)

        if error_msg:
            st.error(f"❌ {error_msg}")
        elif preguntas:
            st.session_state.examen_data = preguntas
            st.session_state.answers = {}
            st.rerun()

elif st.session_state.capitulos:
    st.info("📋 Crea un bloque")
else:
    st.markdown("<div style='text-align:center; padding:60px;'><div style='font-size:48px;'>🏥</div><p style='font-size:16px; color:#666; margin-top:16px;'><b>Sistema HGC</b><br><br>Carga capítulos, crea bloques,<br>genera casos clínicos Consejo.</p></div>", unsafe_allow_html=True)

if st.session_state.examen_data and not st.session_state.examen_enviado:
    examen_data = st.session_state.examen_data
    total_preg = len(examen_data)
    respondidas = len([a for a in st.session_state.answers.values() if a])

    st.markdown(f"**Progreso:** {respondidas}/{total_preg}")
    st.progress(respondidas / total_preg if total_preg > 0 else 0)

    NIVEL_COLOR = {'Sencilla': '#2E7D32', 'Moderada': '#E65100', 'Difícil': '#C62828'}

    for item in examen_data:
        nivel = item.get('nivel', 'Sencilla')
        color = NIVEL_COLOR.get(nivel, '#001F5B')
        st.markdown(f"<div style='background:white; border:1px solid #E8E8E8; border-left:4px solid #001F5B; border-radius:8px; padding:20px 24px; margin-bottom:8px;'><div style='font-size:11px; color:#D4AF37; font-weight:600; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px;'>Caso {item['id']} de {total_preg}</div><span style='display:inline-block; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600; letter-spacing:1px; text-transform:uppercase; margin-bottom:10px; background:{color}22; color:{color};'>{nivel}</span><div style='font-size:13px; color:#666; line-height:1.6; margin-bottom:12px; padding:12px; background:#F9F9F9; border-radius:4px;'><b>CASO:</b> {item.get('caso', 'Sin caso')}</div><div style='font-size:15px; color:#001F5B; font-weight:600; line-height:1.5;'>{item['pregunta']}</div></div>", unsafe_allow_html=True)
        respuesta = st.radio("Selecciona:", item.get('opciones', []), key=f"radio_{item['id']}", label_visibility="collapsed", index=None)
        if respuesta:
            st.session_state.answers[item['id']] = respuesta
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        finalizar = st.button("📊 FINALIZAR", use_container_width=True)

    if finalizar:
        if respondidas < total_preg:
            st.error("❌ Responde todos")
        else:
            st.session_state.examen_enviado = True
            stats, detalle, nota, total_correctas, total_count = calcular_estadisticas(examen_data, st.session_state.answers)

            if nota >= 8:
                emoji, mensaje, color_nota = "🏆", "EXCELENTE", "#D4AF37"
            elif nota >= 6:
                emoji, mensaje, color_nota = "✅", "APROBADO", "#388E3C"
            else:
                emoji, mensaje, color_nota = "📚", "REFUERZO", "#C62828"

            st.markdown(f"<div style='background:linear-gradient(135deg,#001F5B,#003080); border:2px solid #D4AF37; border-radius:12px; padding:32px; text-align:center; margin:24px 0;'><div style='font-size:48px; margin-bottom:8px;'>{emoji}</div><div style='font-family:Georgia,serif; font-size:72px; color:{color_nota}; font-weight:700;'>{nota}</div><div style='color:#D1D1D1; font-size:14px; letter-spacing:2px; text-transform:uppercase; margin-top:8px;'>/ 10 — {mensaje}</div><div style='color:#D1D1D1; margin-top:12px; font-size:13px;'>{nombre} · {grado} · {total_correctas}/{total_count} correctas</div></div>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            for col, nivel in zip([col1, col2, col3], ['Sencilla', 'Moderada', 'Difícil']):
                s = stats.get(nivel, {"correctas": 0, "total": 0})
                pct = round((s["correctas"] / s["total"]) * 100) if s["total"] > 0 else 0
                with col:
                    st.metric(f"{nivel}", f"{s['correctas']}/{s['total']}", f"{pct}%")

            st.markdown("---")
            with st.spinner("📤 Enviando PDF..."):
                try:
                    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                    pdf_buffer = generar_pdf_examen(nombre, grado, examen_data, detalle, stats, nota, fecha_str)
                    exito, msg = enviar_email_pdf(GMAIL_USER, nombre, grado, nota, pdf_buffer)
                    if exito:
                        st.success(f"✅ PDF enviado a jefatura")
                    else:
                        st.warning(f"⚠️ Error: {msg}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 NUEVO EXAMEN", use_container_width=True):
                    st.session_state.examen_data = None
                    st.session_state.answers = {}
                    st.session_state.examen_enviado = False
                    st.rerun()

elif st.session_state.examen_enviado:
    st.markdown("<div style='text-align:center; padding:60px;'><div style='font-size:48px;'>✅</div><p style='font-size:16px; color:#333;'><b>Examen enviado a Jefatura</b></p></div>", unsafe_allow_html=True)
