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
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

st.set_page_config(page_title="HGC - Cirugía Plástica", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    GMAIL_USER = st.secrets.get("GMAIL_USER", "")
    GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD", "")
except:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GMAIL_USER = os.environ.get("GMAIL_USER", "")
    GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")

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

URL_SHEET = "https://script.google.com/macros/s/AKfycbzcPskzds81UQjWfa1BEQpZZgeCB2vwQ-PajzYEpn31ynQ8-obawAnVIn9018uDh5o5/exec"

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
    """Limpia agresivamente el JSON para parsing"""
    # Quitar backticks
    texto = re.sub(r'```json\s*', '', texto)
    texto = re.sub(r'```\s*', '', texto)
    
    # Intentar encontrar JSON array [...]
    inicio_array = texto.find('[')
    if inicio_array >= 0:
        # Encontrar el último ] que cierre el array
        contador = 0
        for i in range(inicio_array, len(texto)):
            if texto[i] == '[':
                contador += 1
            elif texto[i] == ']':
                contador -= 1
                if contador == 0:
                    return texto[inicio_array:i+1].strip()
    
    # Si no hay array, buscar objeto {...}
    inicio = texto.find('{')
    if inicio >= 0:
        contador = 0
        for i in range(inicio, len(texto)):
            if texto[i] == '{':
                contador += 1
            elif texto[i] == '}':
                contador -= 1
                if contador == 0:
                    return texto[inicio:i+1].strip()
    
    return texto.strip()

def crear_base_conocimiento(textos_capitulos):
    """FASE 1: Crea base de conocimiento estructurada de TODOS los capítulos"""
    texto_completo = "\n\n===== NUEVO CAPÍTULO =====\n\n".join(textos_capitulos)
    
    prompt = f"""ERES UN EXPERTO EN CIRUGÍA PLÁSTICA.

CONTENIDO A ANALIZAR (PRIMERAS 15000 PALABRAS):
{texto_completo[:15000]}

EXTRAE INFORMACIÓN EN ESTOS 8 APARTADOS Y RESPONDE ÚNICAMENTE EN JSON VÁLIDO:

{{
  "definicion": "[Qué es, términos clínicos exactos]",
  "anatomia": "[Estructuras anatómicas, relaciones vasculonerviosas, planos]",
  "fisiopatologia": "[Mecanismos de enfermedad, cambios tisulares]",
  "clasificaciones": "[Sistemas de clasificación (Matarasso, Huger, etc.)]",
  "tratamiento_quirurgico": "[Indicaciones, contraindicaciones, técnicas]",
  "tratamiento_no_quirurgico": "[Alternativas médicas, cuándo NO operar]",
  "pronostico_complicaciones": "[Resultados esperados, complicaciones, resolución]",
  "procedimientos_secundarios": "[Complementos quirúrgicos, timing, aplicación]"
}}

SIN BACKTICKS. SIN TEXTO ADICIONAL. SOLO JSON."""

    client = Groq(api_key=GROQ_API_KEY)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        raw = response.choices[0].message.content
        limpio = limpiar_json(raw)
        
        # Intentar parsear
        base = json.loads(limpio)
        
        # Validar que tenga los campos esperados
        campos = ['definicion', 'anatomia', 'fisiopatologia', 'clasificaciones', 
                 'tratamiento_quirurgico', 'tratamiento_no_quirurgico', 
                 'pronostico_complicaciones', 'procedimientos_secundarios']
        
        for campo in campos:
            if campo not in base:
                base[campo] = "Información no disponible"
        
        return base
    except json.JSONDecodeError as e:
        raise Exception(f"JSON inválido: {str(e)[:100]}")
    except Exception as e:
        raise Exception(f"Error análisis: {str(e)}")

def generar_casos_clinicos(base_conocimiento, num_preguntas):
    """FASE 2: Genera casos clínicos tipo CONSEJO basados en la base estructurada"""
    
    base = num_preguntas // 3
    resto = num_preguntas % 3
    n_sencilla = base + (1 if resto >= 1 else 0)
    n_moderada = base + (1 if resto >= 2 else 0)
    n_dificil = base

    contexto = f"""
DEFINICIÓN: {base_conocimiento.get('definicion', '')}
ANATOMÍA: {base_conocimiento.get('anatomia', '')}
FISIOPATOLOGÍA: {base_conocimiento.get('fisiopatologia', '')}
CLASIFICACIONES: {base_conocimiento.get('clasificaciones', '')}
TTO QUIRÚRGICO: {base_conocimiento.get('tratamiento_quirurgico', '')}
TTO NO QUIRÚRGICO: {base_conocimiento.get('tratamiento_no_quirurgico', '')}
PRONÓSTICO/COMPLICACIONES: {base_conocimiento.get('pronostico_complicaciones', '')}
PROCEDIMIENTOS SECUNDARIOS: {base_conocimiento.get('procedimientos_secundarios', '')}
"""

    prompt = f"""ERES EXAMINADOR DEL CONSEJO MEXICANO DE CIRUGÍA PLÁSTICA.

BASE DE CONOCIMIENTO ESTRUCTURADA:
{contexto}

GENERA EXACTAMENTE {num_preguntas} CASOS CLÍNICOS TIPO CONSEJO.

ESTOS SON LOS TIPOS DE PREGUNTAS DEL CONSEJO - DEBES INCLUIR TODOS:

SENCILLA ({n_sencilla} preguntas):
- Diagnosis clínica directa (síntomas → patología)
- Identificar hallazgos anatomopatológicos
- Aplicar clasificaciones
Ejemplo: "Paciente con laxitud abdominal post parto con diástasis de rectos, hernia y flacidez SMAS. ¿Cuál es la clasificación de Matarasso?"

MODERADA ({n_moderada} preguntas):
- Caso clínico que requiere: diagnóstico + fisiopatología + decisión terapéutica
- Escoger entre quirúrgico vs no quirúrgico
- Identificar indicaciones vs contraindicaciones
Ejemplo: "Mujer 45 años, candidata a abdominoplastía pero con IMC 32, fumadora activa. ¿Cuál es la decisión correcta?"

DIFÍCIL ({n_dificil} preguntas):
- Caso complejo: diagnóstico + fisiopatología + anatomía + decisión quirúrgica + complicación
- Aplicar procedimientos secundarios
- Resolver complicaciones
- Múltiples variables clínicas
Ejemplo: "Paciente post abdominoplastía con dehiscencia de línea media, seroma y dolor persistente. ¿Cuál es la fisiopatología y el manejo?"

REQUISITOS OBLIGATORIOS:

1. CADA PREGUNTA DEBE INTEGRAR MÍNIMO 3 ELEMENTOS:
   - Diagnóstico o identificación de patología
   - Fisiopatología o anatomía pertinente
   - Decisión terapéutica o complicación

2. OPCIONES DEBEN SER CLÍNICAMENTE DISTINTAS (no triviales)

3. JUSTIFICACIÓN DEBE CITAR:
   - Definición/concepto aplicado
   - Fisiopatología por qué es correcta
   - Clasificación si aplica
   - Por qué las otras opciones son incorrectas

4. IDIOMA: ESPAÑOL PURO, SIN INGLÉS

RESPONDE ÚNICAMENTE EN JSON VÁLIDO:

[
  {{
    "id": 1,
    "nivel": "Sencilla",
    "caso": "DESCRIBE EL CASO CLÍNICO COMPLETO (edad, síntomas, hallazgos, historia)",
    "pregunta": "¿CUÁL ES LA DIAGNOSIS O CLASIFICACIÓN CORRECTA?",
    "opciones": ["A) [opción clínicamente diferente]", "B) [opción clínicamente diferente]", "C) [opción clínicamente diferente]", "D) [opción clínicamente diferente]"],
    "correcta": "A",
    "justificacion": "JUSTIFICACIÓN COMPLETA: [Definición/concepto]. [Fisiopatología por qué es correcta]. [Clasificación]. [Por qué A es correcta y las otras son incorrectas]."
  }}
]"""

    client = Groq(api_key=GROQ_API_KEY)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=8000
        )
        raw = response.choices[0].message.content
        limpio = limpiar_json(raw)
        return json.loads(limpio)
    except Exception as e:
        raise Exception(f"Error generación casos: {str(e)}")

def enviar_email_pdf(destinatario, nombre_residente, grado, nota, pdf_buffer):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = destinatario
        msg['Subject'] = f"Examen HGC - {nombre_residente} ({grado}) - Calificación: {nota}/10"

        body = f"""Examen generado automáticamente por el Sistema de Evaluación HGC

Residente: {nombre_residente}
Grado: {grado}
Calificación: {nota}/10
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

El PDF adjunto contiene el examen completo con casos clínicos, soluciones y justificaciones profundas.

---
HGC - Hospital General de Culiacán
División de Cirugía Plástica, Estética y Reconstructiva
"""

        msg.attach(MIMEText(body, 'plain'))

        attachment = MIMEApplication(pdf_buffer.read(), _subtype="pdf")
        attachment.add_header('Content-Disposition', 'attachment',
                             filename=f"HGC_{nombre_residente.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        msg.attach(attachment)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)

        return True, "PDF enviado correctamente"
    except Exception as e:
        return False, str(e)

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
            "caso": item.get('caso', ''),
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

    titulo = ParagraphStyle('Titulo', fontName='Helvetica-Bold', fontSize=16, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4)
    subtitulo = ParagraphStyle('Sub', fontName='Helvetica', fontSize=10, textColor=DORADO, alignment=TA_CENTER, spaceAfter=2)

    historia.append(Paragraph("HGC — EVALUACIÓN DE ALTA ESPECIALIDAD", titulo))
    historia.append(Paragraph("División de Cirugía Plástica, Estética y Reconstructiva", subtitulo))
    historia.append(Paragraph("Casos Clínicos Nivel Consejo", subtitulo))
    historia.append(Spacer(1, 6))
    historia.append(HRFlowable(width="100%", thickness=2, color=DORADO))
    historia.append(Spacer(1, 8))

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

    historia.append(Paragraph("RESUMEN DE DESEMPEÑO", 
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

    historia.append(Paragraph("CASOS CLÍNICOS CON SOLUCIONES", 
                             ParagraphStyle('Sec', fontName='Helvetica-Bold', fontSize=14, textColor=NAVY, spaceBefore=14, spaceAfter=6)))
    historia.append(HRFlowable(width="100%", thickness=2, color=DORADO))
    historia.append(Spacer(1, 10))

    estilo_caso = ParagraphStyle('Caso', fontName='Helvetica-Oblique', fontSize=10, textColor=NEGRO, leftIndent=12, spaceBefore=6, spaceAfter=4, leading=13, backColor=colors.HexColor('#F0F0F0'), borderPadding=6)
    estilo_preg = ParagraphStyle('Preg', fontName='Helvetica-Bold', fontSize=11, textColor=NEGRO, spaceBefore=8, spaceAfter=4, leading=14)
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
        
        # CASO CLÍNICO
        if r['caso']:
            historia.append(Paragraph(f"<b>CASO CLÍNICO:</b> {r['caso']}", estilo_caso))
        
        # PREGUNTA
        historia.append(Paragraph(r['pregunta'], estilo_preg))

        # OPCIONES
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
        historia.append(Paragraph(f"<b>JUSTIFICACIÓN DETALLADA:</b> {r['justificacion']}", estilo_just))
        historia.append(Spacer(1, 8))
        historia.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#DDDDDD')))
        historia.append(Spacer(1, 4))

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
for key, val in {
    'capitulos': {},
    'bloques': {},
    'base_conocimiento': None,
    'examen_data': None,
    'answers': {},
    'examen_enviado': False,
    'detalle_resultados': None,
    'stats_resultados': None,
    'nota_final': None
}.items():
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
    st.markdown("## GESTIÓN DE CAPÍTULOS")
    st.markdown("---")

    st.markdown("### 📚 Cargar Capítulos")
    archivos_cargados = st.file_uploader(
        "Carga PDFs de capítulos",
        type="pdf",
        accept_multiple_files=True,
        help="Carga TODOS los capítulos del bloque"
    )

    if archivos_cargados:
        for pdf in archivos_cargados:
            nombre_cap = st.text_input(
                f"Nombre: {pdf.name[:25]}",
                value=pdf.name.replace('.pdf', ''),
                key=f"nombre_{pdf.name}"
            )
            if nombre_cap and pdf.name not in st.session_state.capitulos:
                texto = extraer_texto_pdf(pdf)
                if texto:
                    st.session_state.capitulos[nombre_cap] = texto
                    st.success(f"✅ {nombre_cap}")

    if st.session_state.capitulos:
        st.markdown("---")
        st.markdown("### 📋 Capítulos")
        for cap_name in st.session_state.capitulos.keys():
            st.write(f"✓ {cap_name}")

    st.markdown("---")
    st.markdown("### 🎯 Bloques")
    
    nombre_bloque = st.text_input("Nombre del bloque", placeholder="Ej: Facelift")
    
    if st.session_state.capitulos and nombre_bloque:
        capitulos_disponibles = list(st.session_state.capitulos.keys())
        capitulos_seleccionados = st.multiselect(
            "Selecciona capítulos",
            capitulos_disponibles,
            key=f"bloque_{nombre_bloque}"
        )

        if st.button("➕ Crear Bloque", use_container_width=True):
            if capitulos_seleccionados:
                st.session_state.bloques[nombre_bloque] = capitulos_seleccionados
                st.success(f"✅ '{nombre_bloque}' creado")
                st.rerun()

    if st.session_state.bloques:
        st.markdown("---")
        st.markdown("### ✅ Bloques")
        for bloque_name, caps in st.session_state.bloques.items():
            st.write(f"**{bloque_name}** ({len(caps)})")

    if not GROQ_API_KEY:
        st.error("⚙️ API Key no configurada")

# ENCABEZADO
st.markdown("""
<div style="text-align:center; padding: 10px 0;">
    <h1 style="font-family:'Playfair Display',serif; color:#001F5B; font-size:26px; margin-bottom:4px;">
        HGC — EVALUACIÓN DE ALTA ESPECIALIDAD
    </h1>
    <p style="color:#D4AF37; font-size:13px; letter-spacing:2px; text-transform:uppercase; margin:0;">
        Sistema de Casos Clínicos Nivel Consejo
    </p>
</div>
<hr style="border:none; border-top:2px solid #D4AF37; margin:12px 0;">
""", unsafe_allow_html=True)

# ÁREA PRINCIPAL
if st.session_state.bloques:
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    
    with col1:
        nombre = st.text_input("👤 Residente", placeholder="Dr./Dra. Apellido Nombre")
    
    with col2:
        grado = st.selectbox("🎓 Grado", ["R1", "R2", "R3", "R4"])
    
    with col3:
        bloque_seleccionado = st.selectbox(
            "📚 Bloque",
            list(st.session_state.bloques.keys()),
            key="bloque_selector"
        )

    st.markdown("---")

    num_preguntas = st.slider(
        "📝 Número de casos clínicos",
        min_value=3, max_value=150, value=9, step=3,
        help="Casos clínicos tipo Consejo"
    )

    st.markdown("---")

    generar = st.button("🚀 GENERAR CASOS CLÍNICOS CONSEJO", use_container_width=True)

    if generar and bloque_seleccionado and nombre and GROQ_API_KEY:
        capitulos_bloque = st.session_state.bloques[bloque_seleccionado]
        textos_capitulos = [st.session_state.capitulos[cap] for cap in capitulos_bloque]

        error_msg = None
        base_conocimiento = None
        preguntas = None

        with st.status(f"Generando {num_preguntas} casos clínicos...", expanded=True) as status:
            try:
                st.write(f"📚 Analizando {len(capitulos_bloque)} capítulos...")
                st.write("🔍 FASE 1: Extrayendo base de conocimiento estructurada...")
                st.write("  • Definición y conceptos clave")
                st.write("  • Anatomía pertinente")
                st.write("  • Fisiopatología")
                st.write("  • Clasificaciones")
                st.write("  • Tratamiento quirúrgico y no quirúrgico")
                st.write("  • Pronóstico y complicaciones")
                st.write("  • Procedimientos secundarios")
                
                base_conocimiento = crear_base_conocimiento(textos_capitulos)
                st.write("✅ Base de conocimiento creada")

                st.write(f"📋 FASE 2: Generando {num_preguntas} casos clínicos tipo Consejo...")
                
                for intento in range(3):
                    try:
                        preguntas = generar_casos_clinicos(base_conocimiento, num_preguntas)
                        if isinstance(preguntas, list) and len(preguntas) > 0:
                            st.write(f"✅ {len(preguntas)} casos clínicos generados")
                            break
                        else:
                            raise ValueError("JSON inválido")
                    except Exception as e:
                        if intento < 2:
                            st.write(f"⚠️ Reintentando... ({intento+2}/3)")
                            time.sleep(2)
                        else:
                            raise Exception(f"Error después de 3 intentos: {e}")

                status.update(label=f"✅ {len(preguntas)} casos generados", state="complete")

            except Exception as e:
                status.update(label="❌ Error", state="error")
                error_msg = str(e)

        if error_msg:
            st.error(f"❌ {error_msg}")
        elif preguntas:
            st.session_state.examen_data = preguntas
            st.session_state.answers = {}
            st.session_state.base_conocimiento = base_conocimiento
            st.rerun()

elif st.session_state.capitulos:
    st.info("📋 Crea un bloque para comenzar")
else:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:48px;">🏥</div>
        <p style="font-size:16px; color:#666; margin-top:16px;">
            <strong>Sistema de Evaluación HGC</strong><br><br>
            Carga capítulos, organízalos en bloques,<br>
            y genera casos clínicos tipo Consejo Mexicano.
        </p>
    </div>
    """, unsafe_allow_html=True)

# EXAMEN
if st.session_state.examen_data and not st.session_state.examen_enviado:

    examen_data = st.session_state.examen_data
    total_preg = len(examen_data)
    respondidas = len([a for a in st.session_state.answers.values() if a])

    st.markdown(f"**Progreso:** {respondidas}/{total_preg} casos respondidos")
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
                Caso {item['id']} de {total_preg}
            </div>
            <span style="display:inline-block; padding:2px 10px; border-radius:12px;
                         font-size:11px; font-weight:600; letter-spacing:1px;
                         text-transform:uppercase; margin-bottom:10px;
                         background:{color}22; color:{color};">
                {nivel}
            </span>
            <div style="font-size:13px; color:#666; line-height:1.6; margin-bottom:12px; padding:12px; background:#F9F9F9; border-radius:4px;">
                <b>CASO CLÍNICO:</b> {item.get('caso', 'Sin caso disponible')}
            </div>
            <div style="font-size:15px; color:#001F5B; font-weight:600; line-height:1.5;">
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
        st.warning(f"⚠️ {total_preg - respondidas} caso(s) sin responder")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        finalizar = st.button("📊 FINALIZAR Y ENVIAR", use_container_width=True)

    if finalizar:
        if respondidas < total_preg:
            st.error("❌ Responde todos los casos antes de enviar")
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

            st.markdown("### 📊 Desempeño")
            col1, col2, col3 = st.columns(3)
            for col, nivel in zip([col1, col2, col3], ['Sencilla', 'Moderada', 'Difícil']):
                s = stats.get(nivel, {"correctas": 0, "total": 0})
                pct = round((s["correctas"] / s["total"]) * 100) if s["total"] > 0 else 0
                with col:
                    st.metric(f"{nivel}", f"{s['correctas']}/{s['total']}", f"{pct}%")

            st.markdown("---")

            with st.spinner("📤 Enviando PDF a jefatura..."):
                try:
                    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                    pdf_buffer = generar_pdf_examen(
                        nombre, grado, examen_data,
                        detalle, stats, nota, fecha_str
                    )
                    exito, msg = enviar_email_pdf(GMAIL_USER, nombre, grado, nota, pdf_buffer)
                    
                    if exito:
                        st.success(f"✅ **PDF enviado a jefatura**")
                    else:
                        st.warning(f"⚠️ Error al enviar: {msg}")

                except Exception as e:
                    st.error(f"❌ Error: {e}")

            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 NUEVO EXAMEN", use_container_width=True):
                    st.session_state.examen_data = None
                    st.session_state.answers = {}
                    st.session_state.examen_enviado = False
                    st.rerun()

elif st.session_state.examen_enviado:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:48px;">✅</div>
        <p style="font-size:16px; color:#333; margin-top:16px;">
            <strong>Examen enviado a Jefatura</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
