"""Self-contained PDF calculation record, generated in memory (no shared files)."""
from io import BytesIO
from pathlib import Path
from functools import lru_cache
import base64
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import math
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Circle, String
from core.hydraulics.system_curve import PipeSegment, evaluate_system
from core.hydraulics.curve_fit import fit_polynomial
from core.hydraulics.minor_losses import FITTING_K_TABLE


@lru_cache(maxsize=1)
def _register_fonts():
    root=Path(__file__).resolve().parents[2] / 'data_sources/report_fonts'
    for name in ('BESBReport','BESBReportBold'):
        pdfmetrics.registerFont(TTFont(name,BytesIO(base64.b64decode((root/(name+'.b64')).read_text()))))


def _chart(figure):
    """Render the actual displayed curve samples as PDF vectors, without a browser."""
    width, height = 490, 315
    d = Drawing(width, height)
    traces = []
    for t in figure.data:
        pts = [(float(x),float(y)) for x,y in zip(t.x,t.y) if math.isfinite(float(x)) and math.isfinite(float(y))]
        if pts:
            traces.append((t,pts))
    if not traces:
        return d
    xs=[x for _,pts in traces for x,_ in pts]; ys=[y for _,pts in traces for _,y in pts]
    xmin=min(0,min(xs)); xmax=max(max(xs),xmin+1)
    ymin=min(0,min(ys)); ymax=max(max(ys),ymin+1)
    ymax += (ymax-ymin)*0.05
    left,bottom,pw,ph=48,91,418,200
    sx=lambda x:left+(x-xmin)/(xmax-xmin)*pw
    sy=lambda y:bottom+(y-ymin)/(ymax-ymin)*ph
    for i in range(6):
        x=xmin+(xmax-xmin)*i/5; y=ymin+(ymax-ymin)*i/5
        d.add(Line(sx(x),bottom,sx(x),bottom+ph,strokeColor=colors.HexColor('#dddddd'),strokeWidth=.4))
        d.add(Line(left,sy(y),left+pw,sy(y),strokeColor=colors.HexColor('#dddddd'),strokeWidth=.4))
        d.add(String(sx(x),bottom-14,f'{x:.1f}',fontName='BESBReport',fontSize=9,textAnchor='middle'))
        d.add(String(left-6,sy(y)-3,f'{y:.1f}',fontName='BESBReport',fontSize=9,textAnchor='end'))
    d.add(Line(left,bottom,left+pw,bottom,strokeColor=colors.black))
    d.add(Line(left,bottom,left,bottom+ph,strokeColor=colors.black))
    d.add(String(left+pw/2,bottom-30,'Caudal (L/s)',fontName='BESBReport',fontSize=11,textAnchor='middle'))
    d.add(String(left,bottom+ph+12,'Altura (m)',fontName='BESBReport',fontSize=11))
    legend=0
    for t,pts in traces:
        is_marker=t.mode == 'markers'
        color=colors.toColor((t.marker.color if is_marker else t.line.color) or '#155A8A')
        if is_marker:
            for x,y in pts:d.add(Circle(sx(x),sy(y),3,fillColor=color,strokeColor=colors.white))
        else:
            d.add(PolyLine([v for x,y in pts for v in (sx(x),sy(y))],strokeColor=color,strokeWidth=1.4))
            lx=48+(legend%2)*215; ly=43-(legend//2)*13
            d.add(Line(lx,ly,lx+17,ly,strokeColor=color,strokeWidth=2))
            d.add(String(lx+22,ly-3,str(t.name)[:36],fontName='BESBReport',fontSize=9))
            legend+=1
    return d


def build_calculation_pdf(case, figure=None):
    _register_fonts()
    buffer=BytesIO()
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodySerif',fontName='BESBReport',fontSize=10,leading=13,spaceAfter=6))
    styles.add(ParagraphStyle(name='HeadingSerif',fontName='BESBReportBold',fontSize=14,leading=17,spaceBefore=12,spaceAfter=8))
    styles.add(ParagraphStyle(name='TitleSerif',fontName='BESBReportBold',fontSize=21,leading=25,alignment=TA_CENTER,spaceAfter=14))
    body=styles['BodySerif']
    def para(value):return Paragraph(escape(str(value)),body)
    story=[]
    def heading(value):story.append(Paragraph(escape(value),styles['HeadingSerif']))
    def text(value):story.append(para(value))
    def table(headers,rows,widths):
        cells=[[para(v) for v in headers]]+[[para('—' if v is None else v) for v in row] for row in rows]
        t=LongTable(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf2')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#526578')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#dddddd')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.extend([t,Spacer(1,9)])
    story.append(Paragraph('Memoria de cálculo de bombeo',styles['TitleSerif']))
    text(case.get('proyecto','Sistema de bombeo'))
    text('Emisión UTC: '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))
    text('Estado: modelo en desarrollo. Los valores iniciales de la aplicación son ejemplos; esta memoria registra los datos ingresados y no certifica el diseño.')
    heading('1. Resultados de operación')
    results=case['resultados_por_escenario']
    table(['Escenario','Q (L/s)','H (m)','P eléctrica (kW)','Estado'],[[r['Escenario'],r.get('Q (L/s)'),r.get('H (m)'),r.get('P electrica (kW)'),r.get('Estado')] for r in results],[118,65,65,85,157])
    if figure is not None:
        text(case['grafica']['titulo'])
        story.append(_chart(figure))
    story.append(PageBreak())
    heading('2. Datos del líquido y la instalación')
    f=case['fluido']
    table(['Parámetro','Valor'],[['Líquido',f['nombre']],['Temperatura (°C)',f['temperatura_c']],['Densidad (kg/m³)',f['densidad_kg_m3']],['Viscosidad dinámica (Pa·s)',f['viscosidad_pa_s']],['Desnivel destino - origen (m)',case['altura_estatica_m']],['Eficiencia del motor (%)',case.get('eficiencia_motor_pct')]], [245,245])
    text('Propiedades del líquido: '+f['fuente'])
    table(['Tramo','L (m)','DI (mm)','Rugosidad (mm)','Clase'],[[r['label'],r['longitud_m'],r['diametro_interior_mm'],r['rugosidad_mm'],r['clase_pn']] for r in case['tramos']],[82,70,75,98,165])
    for r in case['tramos']:
        text(r['label']+' - Accesorios: '+(', '.join(f'{n}: {c} unidades, K unitario = {FITTING_K_TABLE[n]:g}' for n,c in r['accesorios'].items()) or 'ninguno; pérdidas singulares ingresadas = 0'))
        cat=r.get('catalogo')
        if cat:
            prov=cat['provenance']
            text(f"Fuente: {prov['document']}, página {prov['page']}. SDR {cat['sdr']}; DE {cat['outside_diameter_mm']} mm; espesor {cat['wall_thickness_mm']} mm. Transcripción pendiente de revisión.")
            text('Referencia de presión: '+cat.get('pressure_source','No evaluada'))
            for issue in cat.get('issues',[]):text(issue)
    heading('3. Curva de la bomba ingresada')
    curve=case['curva_bomba']
    table(['Q (L/s)','H (m)','Eficiencia (%)'],[[p['Q_L_s'],p['H_m'],p['eta_pct']] for p in curve['puntos']],[160,165,165])
    text('Ajuste por regresión, grado '+str(curve['grado_ajuste'])+'. Las eficiencias usadas en operación se indican en la siguiente tabla.')
    table(['Escenario','Eficiencia bomba (%)','P hidráulica (kW)','P al eje (kW)'],[[r['Escenario'],r.get('eta bomba (%)'),r.get('P hidraulica (kW)'),r.get('P eje (kW)')] for r in results],[145,115,115,115])
    table(['Configuración','N / N nominal','Bombas paralelo','Bombas serie'],[[r['label'],f"{r['phi']:.4f}",r['parallel_n'],r['series_n']] for r in case.get('configuracion_escenarios',[])],[160,110,110,110])
    story.append(PageBreak())
    heading('4. Fórmulas y detalle hidráulico')
    text('Unidades de estas fórmulas: Q en m³/s, D y L en m, densidad rho en kg/m³, viscosidad mu en Pa·s, g = 9,80665 m/s². Q [m³/s] = Q [L/s] / 1000.')
    for formula in ['v = 4 Q / (pi D²); Re = rho v D / mu.', 'Darcy-Weisbach: hf = f (L/D) v²/(2g). Accesorios: hs = suma(K) v²/(2g).', 'Régimen laminar: f = 64/Re. Turbulento: 1/sqrt(f) = -2 log10(epsilon/(3,7D) + 2,51/(Re sqrt(f))).', 'H sistema = desnivel + suma(hf + hs). El equilibrio satisface H bomba(Q) = H sistema(Q).', 'P hidráulica = rho g Q H / 1000 [kW]; P eje = P hidráulica / eta bomba; P eléctrica = P eje / eta motor. Eficiencias en fracción.', 'VDF: Q2 = Q1 (N2/N1); H2 = H1 (N2/N1)². La eficiencia se traslada al punto homólogo.']:
        text(formula)
    fit=fit_polynomial([p['Q_L_s']/1000 for p in curve['puntos']],[p['H_m'] for p in curve['puntos']],curve['grado_ajuste'])
    text('Polinomio nominal H(Q): coeficientes en orden de mayor a menor potencia de Q [m³/s] = '+', '.join(f'{c:.10g}' for c in fit.coefficients)+f'. R² = {fit.r_squared:.6f}.')
    nominal=next((r for r in results if r['Escenario']=='Nominal' and r.get('Q (L/s)') is not None),None)
    if nominal:
        segments=[PipeSegment(label=r['label'],length_m=r['longitud_m'],inside_diameter_mm=r['diametro_interior_mm'],roughness_mm=r['rugosidad_mm'],fitting_counts=r['accesorios']) for r in case['tramos']]
        detail=evaluate_system(segments,nominal['Q (L/s)']/1000,case['altura_estatica_m'],f['densidad_kg_m3'],f['viscosidad_pa_s'])
        table(['Tramo','v (m/s)','Re','f','hf (m)','hs (m)'],[[e.label,f'{e.velocity_m_s:.3f}',f'{e.reynolds:.3g}',f'{e.friction_factor:.5f}',f'{e.friction_head_loss_m:.3f}',f'{e.minor_head_loss_m:.3f}'] for e in detail.segment_evaluations],[95,75,90,80,75,75])
        for e in detail.segment_evaluations:
            text(f'{e.label}: régimen {e.regime.value}. {e.friction_note}')
    else:text('Sin equilibrio nominal: no se evalúan pérdidas por tramo en un punto de operación nominal.')
    heading('5. Verificaciones y límites del modelo')
    pressure=case.get('presion_vs_pn')
    if pressure:
        table(['Tramo','Presión estimada (bar)','Referencia (bar)','Resultado'],[[r['tramo'],f"{r['presion_diseno_bar']:.3f}",r['pn_bar'],'Cumple referencia' if r['passed'] else 'Supera referencia'] for r in pressure],[110,135,115,130])
    else:text('Presión frente a PN: no evaluada para este caso.')
    for name,key in [('NPSH','npsh'),('Golpe de ariete','golpe_de_ariete')]:
        values=case.get(key)
        if values:table([name,'Valor'],[[k,v] for k,v in values.items()],[300,190])
        else:text(name+': no evaluado.')
    text('Modelo de tramos en serie sin ramificaciones. La curva del sistema se muestrea en 60 puntos y se interpola linealmente; fuera de su rango se mantiene el valor extremo. No extrapolar la validez del resultado a otra configuración.')
    text('Perfil de energía y presión: ilustrativo, con pendiente uniforme y pérdidas repartidas; no contiene topografía medida. La comparación de presión usa una condición de cierre de bomba y cotas supuestas; no representa todos los extremos de presión ni sustituye un estudio transiente.')
    text('Los K de accesorios son genéricos. Las tablas de catálogo están pendientes de revisión; las dimensiones no certifican disponibilidad, compatibilidad química ni presión admisible a otras temperaturas. El diámetro HDPE se deriva del espesor mínimo y no incorpora tolerancias.')
    text('Fuentes del motor y supuestos: core/hydraulics, documentación HYDRAULICS_PUMP_OPERATING_POINT. Las propiedades manuales son responsabilidad del dato ingresado. '+case['_aviso'])
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('BESBReport',9)
        canvas.drawString(42,25,'Memoria de cálculo | Modelo en desarrollo')
        canvas.drawRightString(A4[0]-42,25,f'Página {doc.page}')
        canvas.restoreState()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=36,bottomMargin=42,title='Memoria de cálculo de bombeo',author='')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
