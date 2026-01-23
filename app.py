import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import os
import tempfile
import re
from pypdf import PdfReader

# Configuración inicial de la página
st.set_page_config(page_title="Facturación Pro", layout="wide")

# --- CONFIGURACIÓN DEL TEMA ---
if 'tema_oscuro' not in st.session_state:
    st.session_state.tema_oscuro = False

def aplicar_tema():
    """Aplica el tema seleccionado a la interfaz"""
    if st.session_state.tema_oscuro:
        st.markdown("""
        <style>
        .stApp {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {
            background-color: #2D2D2D;
            color: #FFFFFF;
            border-color: #555555;
        }
        .stButton > button {
            background-color: #4CAF50;
            color: white;
        }
        .stSelectbox > div > div > select {
            background-color: #2D2D2D;
            color: #FFFFFF;
        }
        .sidebar .sidebar-content {
            background-color: #252525;
        }
        </style>
        """, unsafe_allow_html=True)

# Aplicar tema al inicio
aplicar_tema()

# --- FUNCIONES DE APOYO ---
def fmt(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except:
        return "0"

def agregar_imagen_segura(pdf, uploaded_file, x, y, w):
    if uploaded_file is not None:
        try:
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            pdf.image(tmp_path, x=x, y=y, w=w)
            os.unlink(tmp_path)
        except:
            pass

def limpiar_texto_para_pdf(texto):
    """Reemplaza caracteres problemáticos para PDF"""
    if not isinstance(texto, str):
        texto = str(texto)
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N',
        '´': "'", '`': "'",
    }
    for char, replacement in reemplazos.items():
        texto = texto.replace(char, replacement)
    return texto

def dividir_texto(texto, max_ancho, pdf, font_size=8):
    """Divide un texto en múltiples líneas para que quepa en el ancho especificado"""
    pdf.set_font("Arial", '', font_size)
    palabras = texto.split()
    lineas = []
    linea_actual = ""
    
    for palabra in palabras:
        prueba = f"{linea_actual} {palabra}".strip()
        if pdf.get_string_width(prueba) <= max_ancho:
            linea_actual = prueba
        else:
            if linea_actual:
                lineas.append(linea_actual)
            linea_actual = palabra
    
    if linea_actual:
        lineas.append(linea_actual)
    
    return lineas

def calcular_altura_texto(lineas, altura_linea=4):
    """Calcula la altura total necesaria para un texto con múltiples líneas"""
    return len(lineas) * altura_linea

def importar_datos_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        cliente_match = re.search(r"CLIENTE:\s*(.*)\s*\|", text)
        cliente = cliente_match.group(1).strip() if cliente_match else "Cliente Importado"
        
        patron = r"(\d+)\s+(.*?)\s+(\d+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)"
        matches = re.findall(patron, text)
        
        productos = []
        for m in matches:
            productos.append({
                "Pag": m[0], 
                "Prod": m[1].strip(), 
                "Cant": int(m[2]),
                "Cat_U": int(m[3].replace('.', '')), 
                "List_U": int(m[5].replace('.', ''))
            })
        return {"cliente": cliente, "productos": productos if productos else None}
    except Exception as e:
        st.error(f"Error al leer el PDF: {e}")
        return None

# --- INICIALIZACIÓN DEL ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}
if 'delete_row' not in st.session_state:
    st.session_state.delete_row = None
if 'next_factura_id' not in st.session_state:
    st.session_state.next_factura_id = 1

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("🎨 Tema de Interfaz")
    if st.button("🌙 Cambiar a Tema Oscuro" if not st.session_state.tema_oscuro else "☀️ Cambiar a Tema Normal"):
        st.session_state.tema_oscuro = not st.session_state.tema_oscuro
        aplicar_tema()
        st.rerun()
    
    with st.expander("🖼️ Marca", expanded=False):
        logo_rev = st.file_uploader("Logo Revista", type=["png", "jpg", "jpeg"])
        nombre_rev = st.text_input("Nombre Revista", "MI REVISTA")
        
    with st.expander("💳 Pago", expanded=False):
        num_pago = st.text_input("Cuenta / Nequi")
        logo_pago = st.file_uploader("Logo Pago", type=["png", "jpg", "jpeg"])
        qr_pago = st.file_uploader("QR Pago", type=["png", "jpg", "jpeg"])
    
    st.divider()
    
    st.subheader("🔄 Re-editar")
    archivo_pdf = st.file_uploader("Subir factura PDF anterior", type=["pdf"])
    if archivo_pdf and st.button("📥 Cargar Datos del PDF"):
        res = importar_datos_pdf(archivo_pdf)
        if res and res["productos"]:
            nid = st.session_state.next_factura_id
            st.session_state.facturas.append({"id": nid, "name": res["cliente"]})
            st.session_state.datos[f"f_{nid}"] = res["productos"]
            st.session_state.next_factura_id += 1
            st.success("¡Datos cargados en una nueva pestaña!")
            st.rerun()
        else:
            st.warning("No se detectaron productos legibles en el PDF.")

# --- PANEL PRINCIPAL ---
st.title("📑 Facturación Profesional")

if st.button("➕ Crear Nueva Factura"):
    nid = st.session_state.next_factura_id
    st.session_state.facturas.append({"id": nid, "name": f"Factura {nid}"})
    st.session_state.next_factura_id += 1
    st.rerun()

if st.session_state.delete_row is not None:
    delete_fid, delete_i = st.session_state.delete_row
    if delete_fid in st.session_state.datos and delete_i < len(st.session_state.datos[delete_fid]):
        st.session_state.datos[delete_fid].pop(delete_i)
        if len(st.session_state.datos[delete_fid]) == 0:
            st.session_state.datos[delete_fid].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
    st.session_state.delete_row = None
    st.rerun()

tab_titles = [f["name"] for f in st.session_state.facturas]
tabs = st.tabs(tab_titles)

for idx, tab in enumerate(tabs):
    with tab:
        factura_actual = st.session_state.facturas[idx]
        fid = factura_actual["id"]
        key_f = f"f_{fid}"
        
        if key_f not in st.session_state.datos:
            st.session_state.datos[key_f] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]
        
        c1, c2 = st.columns(2)
        with c1:
            nom_cli = st.text_input(
                "Cliente", 
                value=factura_actual["name"] if factura_actual["name"] != "Nueva Factura" else "",
                key=f"cliente_{fid}_{idx}"
            )
        
        with c2:
            fec_p = st.date_input(
                "Fecha de Pago", 
                date.today(), 
                key=f"fecha_{fid}_{idx}"
            )
        
        if nom_cli and nom_cli != factura_actual["name"]:
            st.session_state.facturas[idx]["name"] = nom_cli
        
        s_tc, s_tl, s_tg = 0, 0, 0
        
        st.markdown("<small style='color:gray;'>Pág | Producto | Cant | Precio Catálogo | Total Catálogo | Precio Lista | Total Lista | Ganancia (Cat-List) | </small>", unsafe_allow_html=True)
        
        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([0.5, 2.5, 0.6, 1.2, 1.2, 1.2, 1.2, 1.2, 0.4])
            
            with cols[0]:
                fila['Pag'] = st.text_input(
                    "P", 
                    value=fila.get('Pag', ''),
                    key=f"pag_{fid}_{idx}_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[1]:
                fila['Prod'] = st.text_input(
                    "Pr", 
                    value=fila.get('Prod', ''),
                    key=f"prod_{fid}_{idx}_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[2]:
                fila['Cant'] = st.number_input(
                    "C", 
                    value=int(fila.get('Cant', 1)),
                    min_value=1,
                    key=f"cant_{fid}_{idx}_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[3]:
                fila['Cat_U'] = st.number_input(
                    "PC", 
                    value=int(fila.get('Cat_U', 0)),
                    min_value=0,
                    key=f"cat_u_{fid}_{idx}_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[4]:
                tc = fila['Cant'] * fila['Cat_U']
                st.markdown(f"<div style='text-align: right;'><strong>${fmt(tc)}</strong></div>", unsafe_allow_html=True)
            
            with cols[5]:
                fila['List_U'] = st.number_input(
                    "PL", 
                    value=int(fila.get('List_U', 0)),
                    min_value=0,
                    key=f"list_u_{fid}_{idx}_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[6]:
                tl = fila['Cant'] * fila['List_U']
                st.markdown(f"<div style='text-align: right;'><strong>${fmt(tl)}</strong></div>", unsafe_allow_html=True)
            
            with cols[7]:
                gan = tc - tl
                color_gan = "#2e7d32" if gan >= 0 else "#d32f2f"
                st.markdown(f"<div style='text-align: right; color:{color_gan};'><strong>${fmt(gan)}</strong></div>", unsafe_allow_html=True)
            
            with cols[8]:
                if st.button("🗑️", key=f"del_{fid}_{idx}_{i}", type="secondary"):
                    st.session_state.delete_row = (key_f, i)
                    st.rerun()
            
            s_tc += tc
            s_tl += tl
            s_tg += gan
        
        color_total_gan = "#2e7d32" if s_tg >= 0 else "#d32f2f"
        st.markdown(f"""
            <div style="background-color:#ffffff; border:1px solid #cccccc; padding:15px; border-radius:10px; margin:20px 0; color:#000000;">
                <div style="display:flex; justify-content:space-around; text-align:center;">
                    <div><p style="margin:0; font-size:0.8rem; color:#616161;">TOTAL CATÁLOGO</p><strong style="font-size:1.2rem;">${fmt(s_tc)}</strong></div>
                    <div><p style="margin:0; font-size:0.8rem; color:#616161;">TOTAL LISTA</p><strong style="font-size:1.2rem;">${fmt(s_tl)}</strong></div>
                    <div><p style="margin:0; font-size:0.8rem; color:{color_total_gan};">GANANCIA TOTAL</p><strong style="font-size:1.5rem; color:{color_total_gan};">${fmt(s_tg)}</strong></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("➕ Agregar Nueva Fila", key=f"add_{fid}_{idx}", use_container_width=True):
                nueva_fila = {"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}
                st.session_state.datos[key_f].append(nueva_fila)
                st.rerun()
        
        with col2:
            if st.button("🧹 Limpiar Todo", key=f"clear_{fid}_{idx}", type="secondary", use_container_width=True):
                st.session_state.datos[key_f] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]
                st.rerun()
        
        # GENERACIÓN DE PDF CON CELDAS QUE SE AJUSTAN AL CONTENIDO
        if st.session_state.datos[key_f]:
            filas_validas = [f for f in st.session_state.datos[key_f] if f.get('Prod', '').strip() != ""]
            
            if filas_validas:
                df_pdf = pd.DataFrame(filas_validas)
                
                if st.button("🚀 GENERAR PDF", key=f"pdf_{fid}_{idx}", type="primary", use_container_width=True):
                    with st.spinner("Generando PDF..."):
                        try:
                            # PDF en formato vertical con celdas ajustables
                            pdf = FPDF(orientation='P', unit='mm', format='A4')
                            pdf.add_page()
                            
                            # Márgenes pequeños
                            pdf.set_left_margin(8)
                            pdf.set_right_margin(8)
                            pdf.set_top_margin(10)
                            
                            # Logo
                            if logo_rev:
                                try:
                                    agregar_imagen_segura(pdf, logo_rev, 8, 10, 25)
                                except:
                                    pass
                            
                            # Título
                            pdf.set_font("Arial", 'B', 14)
                            pdf.set_xy(0, 10)
                            pdf.cell(0, 8, txt=nombre_rev.upper(), ln=True, align='C')
                            
                            # Información del cliente
                            pdf.set_font("Arial", '', 10)
                            cliente_text = f"CLIENTE: {nom_cli.upper()} | FECHA: {fec_p.strftime('%d-%m-%Y')}"
                            pdf.cell(0, 6, cliente_text, ln=True, align='C')
                            pdf.ln(5)
                            
                            # ANCHOS FIJOS PARA COLUMNAS (excepto producto)
                            # Ancho total: 210mm - 16mm márgenes = 194mm
                            # Distribución: Pág(12) + Producto(AUTO) + Cant(12) + P.Cat(20) + T.Cat(20) + P.List(20) + T.List(20) + Gan(20) = 124mm + Producto
                            # Producto tomará el espacio restante: 194mm - 124mm = 70mm mínimo
                            
                            # Definir anchos fijos
                            ancho_fijos = [12, 12, 20, 20, 20, 20, 20]  # Pág, Cant, P.Cat, T.Cat, P.List, T.List, Gan
                            ancho_total_fijos = sum(ancho_fijos)  # 124mm
                            ancho_disponible = 194  # 210 - 16 márgenes
                            ancho_producto = ancho_disponible - ancho_total_fijos  # Lo que sobra para producto
                            
                            # Encabezados
                            pdf.set_fill_color(240, 240, 240)
                            pdf.set_font("Arial", 'B', 8)
                            
                            # Primera fila de encabezados
                            pdf.cell(12, 6, "Pág", 1, 0, 'C', True)
                            pdf.cell(ancho_producto, 6, "Producto", 1, 0, 'C', True)
                            pdf.cell(12, 6, "Cant", 1, 0, 'C', True)
                            pdf.cell(20, 6, "P.Cat", 1, 0, 'C', True)
                            pdf.cell(20, 6, "T.Cat", 1, 0, 'C', True)
                            pdf.cell(20, 6, "P.List", 1, 0, 'C', True)
                            pdf.cell(20, 6, "T.List", 1, 0, 'C', True)
                            pdf.cell(20, 6, "Gan.", 1, 1, 'C', True)
                            
                            pdf.set_font("Arial", '', 7)
                            
                            # Variables para totales
                            total_tc = 0
                            total_tl = 0
                            total_gan = 0
                            
                            for _, r in df_pdf.iterrows():
                                # Calcular valores
                                v_tc = r['Cant'] * r['Cat_U']
                                v_tl = r['Cant'] * r['List_U']
                                gan_fila = v_tc - v_tl
                                
                                # Actualizar totales
                                total_tc += v_tc
                                total_tl += v_tl
                                total_gan += gan_fila
                                
                                # Preparar texto del producto
                                prod_text = limpiar_texto_para_pdf(str(r['Prod']))
                                
                                # DIVIDIR EL TEXTO DEL PRODUCTO EN MÚLTIPLES LÍNEAS
                                lineas_producto = dividir_texto(prod_text, ancho_producto - 2, pdf, 7)
                                num_lineas = len(lineas_producto)
                                altura_fila = max(6, num_lineas * 3.5)  # Altura mínima 6mm
                                
                                # Verificar si necesitamos nueva página
                                if pdf.get_y() + altura_fila > 270:
                                    pdf.add_page()
                                    # Reimprimir encabezados
                                    pdf.set_fill_color(240, 240, 240)
                                    pdf.set_font("Arial", 'B', 8)
                                    pdf.cell(12, 6, "Pág", 1, 0, 'C', True)
                                    pdf.cell(ancho_producto, 6, "Producto", 1, 0, 'C', True)
                                    pdf.cell(12, 6, "Cant", 1, 0, 'C', True)
                                    pdf.cell(20, 6, "P.Cat", 1, 0, 'C', True)
                                    pdf.cell(20, 6, "T.Cat", 1, 0, 'C', True)
                                    pdf.cell(20, 6, "P.List", 1, 0, 'C', True)
                                    pdf.cell(20, 6, "T.List", 1, 0, 'C', True)
                                    pdf.cell(20, 6, "Gan.", 1, 1, 'C', True)
                                    pdf.set_font("Arial", '', 7)
                                
                                # Guardar posición X inicial
                                x_inicial = pdf.get_x()
                                y_inicial = pdf.get_y()
                                
                                # Columna 1: Página
                                pdf.cell(12, altura_fila, str(r['Pag']), 1, 0, 'C')
                                
                                # Columna 2: Producto (MÚLTIPLES LÍNEAS)
                                # Escribir cada línea del producto
                                for i, linea in enumerate(lineas_producto):
                                    if i == 0:
                                        # Primera línea
                                        pdf.cell(ancho_producto, altura_fila/num_lineas, linea, 'LR', 0, 'L')
                                    else:
                                        # Líneas adicionales
                                        pdf.set_xy(x_inicial + 12, y_inicial + (i * altura_fila/num_lineas))
                                        pdf.cell(ancho_producto, altura_fila/num_lineas, linea, 'LR', 0, 'L')
                                
                                # Volver a la posición correcta para continuar
                                pdf.set_xy(x_inicial + 12 + ancho_producto, y_inicial)
                                
                                # Columna 3: Cantidad
                                pdf.cell(12, altura_fila, str(r['Cant']), 1, 0, 'C')
                                
                                # Columna 4: Precio Catálogo
                                pdf.cell(20, altura_fila, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                                
                                # Columna 5: Total Catálogo
                                pdf.set_fill_color(225, 245, 254)
                                pdf.cell(20, altura_fila, f"${fmt(v_tc)}", 1, 0, 'R', True)
                                
                                # Columna 6: Precio Lista
                                pdf.set_fill_color(255, 255, 255)
                                pdf.cell(20, altura_fila, f"${fmt(r['List_U'])}", 1, 0, 'R')
                                
                                # Columna 7: Total Lista
                                pdf.set_fill_color(255, 243, 224)
                                pdf.cell(20, altura_fila, f"${fmt(v_tl)}", 1, 0, 'R', True)
                                
                                # Columna 8: Ganancia
                                if gan_fila >= 0:
                                    pdf.set_fill_color(232, 245, 233)
                                else:
                                    pdf.set_fill_color(255, 230, 230)
                                
                                pdf.cell(20, altura_fila, f"${fmt(gan_fila)}", 1, 1, 'R', True)
                                
                                # Restaurar color de fondo
                                pdf.set_fill_color(255, 255, 255)
                            
                            # Línea de totales
                            pdf.set_fill_color(230, 230, 230)
                            pdf.set_font("Arial", 'B', 9)
                            
                            # Calcular ancho para "TOTALES"
                            ancho_totales = 12 + ancho_producto + 12  # Pág + Producto + Cant
                            
                            pdf.cell(ancho_totales, 7, "TOTALES:", 1, 0, 'R', True)
                            pdf.cell(20, 7, "", 1, 0, 'C', True)  # Celda vacía (P.Cat)
                            pdf.cell(20, 7, f"${fmt(total_tc)}", 1, 0, 'R', True)
                            pdf.cell(20, 7, "", 1, 0, 'C', True)  # Celda vacía (P.List)
                            pdf.cell(20, 7, f"${fmt(total_tl)}", 1, 0, 'R', True)
                            
                            if total_gan >= 0:
                                pdf.set_fill_color(232, 245, 233)
                            else:
                                pdf.set_fill_color(255, 230, 230)
                            
                            pdf.cell(20, 7, f"${fmt(total_gan)}", 1, 1, 'R', True)
                            
                            # Información de pago
                            pdf.ln(5)
                            
                            if logo_pago:
                                try:
                                    agregar_imagen_segura(pdf, logo_pago, 8, pdf.get_y(), 12)
                                except:
                                    pass
                            
                            pdf.set_font("Arial", 'B', 10)
                            if num_pago:
                                pdf.cell(0, 5, f"Pagar a: {num_pago}")
                            else:
                                pdf.cell(0, 5, "Información de pago no configurada")
                            
                            if qr_pago:
                                try:
                                    agregar_imagen_segura(pdf, qr_pago, 150, pdf.get_y() - 2, 25)
                                except:
                                    pass
                            
                            # Generar PDF
                            res_pdf = pdf.output(dest='S').encode('latin-1')
                            
                            st.success("✅ PDF generado exitosamente")
                            st.download_button(
                                label="⬇️ Descargar PDF",
                                data=res_pdf,
                                file_name=f"Factura_{nom_cli.replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key=f"download_{fid}_{idx}"
                            )
                            
                        except Exception as e:
                            st.error(f"Error al generar el PDF: {str(e)}")
                            
                            # Método alternativo SIMPLE
                            try:
                                pdf = FPDF(orientation='P', unit='mm', format='A4')
                                pdf.add_page()
                                
                                pdf.set_font("Arial", 'B', 14)
                                pdf.cell(0, 10, f"FACTURA: {nom_cli}", 0, 1, 'C')
                                pdf.set_font("Arial", '', 10)
                                pdf.cell(0, 5, f"Fecha: {fec_p.strftime('%d-%m-%Y')}", 0, 1, 'C')
                                pdf.ln(5)
                                
                                # Tabla simplificada
                                pdf.set_font("Arial", 'B', 8)
                                encabezados = ["Pág", "Producto", "Cant", "Total", "Gan."]
                                anchos = [15, 120, 15, 25, 25]
                                
                                for i, header in enumerate(encabezados):
                                    pdf.cell(anchos[i], 6, header, 1, 0, 'C', True)
                                pdf.ln()
                                
                                pdf.set_font("Arial", '', 7)
                                
                                for _, r in df_pdf.iterrows():
                                    v_tc = r['Cant'] * r['Cat_U']
                                    v_tl = r['Cant'] * r['List_U']
                                    gan_fila = v_tc - v_tl
                                    
                                    # Dividir producto
                                    prod_text = str(r['Prod'])
                                    lineas = dividir_texto(prod_text, anchos[1] - 2, pdf, 7)
                                    altura = max(5, len(lineas) * 3)
                                    
                                    # Página
                                    pdf.cell(anchos[0], altura, str(r['Pag']), 1, 0, 'C')
                                    
                                    # Producto (múltiples líneas)
                                    x = pdf.get_x()
                                    y = pdf.get_y()
                                    for j, linea in enumerate(lineas):
                                        if j == 0:
                                            pdf.cell(anchos[1], altura/len(lineas), linea, 'LR', 0, 'L')
                                        else:
                                            pdf.set_xy(x, y + (j * altura/len(lineas)))
                                            pdf.cell(anchos[1], altura/len(lineas), linea, 'LR', 0, 'L')
                                    
                                    pdf.set_xy(x + anchos[1], y)
                                    
                                    # Cantidad
                                    pdf.cell(anchos[2], altura, str(r['Cant']), 1, 0, 'C')
                                    
                                    # Total
                                    pdf.cell(anchos[3], altura, f"${fmt(v_tc)}", 1, 0, 'R')
                                    
                                    # Ganancia
                                    pdf.cell(anchos[4], altura, f"${fmt(gan_fila)}", 1, 1, 'R')
                                
                                # Totales simples
                                pdf.set_font("Arial", 'B', 9)
                                pdf.cell(150, 7, "TOTALES:", 1, 0, 'R', True)
                                pdf.cell(25, 7, f"${fmt(s_tc)}", 1, 0, 'R', True)
                                pdf.cell(25, 7, f"${fmt(s_tg)}", 1, 1, 'R', True)
                                
                                res_pdf_simple = pdf.output(dest='S').encode('latin-1')
                                
                                st.download_button(
                                    label="⬇️ Descargar PDF Simplificado",
                                    data=res_pdf_simple,
                                    file_name=f"Factura_{nom_cli.replace(' ', '_')}_simple.pdf",
                                    mime="application/pdf"
                                )
                                
                            except Exception as e2:
                                st.error(f"Error crítico: {str(e2)}")
            else:
                st.warning("Agrega al menos un producto con nombre para generar el PDF.")
        else:
            st.warning("Agrega al menos un producto con nombre para generar el PDF.")
