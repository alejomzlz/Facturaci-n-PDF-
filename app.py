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

def truncar_texto(texto, max_caracteres=40):
    """Trunca texto largo para que quepa en el PDF"""
    if not isinstance(texto, str):
        texto = str(texto)
    if len(texto) > max_caracteres:
        return texto[:max_caracteres-3] + "..."
    return texto

def calcular_altura_fila(pdf, texto, ancho_columna, fuente_tamano=8):
    """Calcula la altura necesaria para una fila basada en el texto del producto"""
    pdf.set_font("Arial", '', fuente_tamano)
    
    # Dividir el texto en palabras
    palabras = texto.split()
    lineas = []
    linea_actual = ""
    
    for palabra in palabras:
        prueba = f"{linea_actual} {palabra}".strip()
        if pdf.get_string_width(prueba) < ancho_columna - 2:  # -2 para margen
            linea_actual = prueba
        else:
            if linea_actual:
                lineas.append(linea_actual)
            linea_actual = palabra
    
    if linea_actual:
        lineas.append(linea_actual)
    
    # Si no cabe en una línea, usar el cálculo original
    if not lineas or len(lineas) == 0:
        lineas = [texto]
    
    # Calcular altura (cada línea ~4mm)
    num_lineas = len(lineas)
    altura = max(6, num_lineas * 4)  # Mínimo 6mm, más si hay múltiples líneas
    
    return altura, lineas

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
        
        # GENERACIÓN DE PDF MEJORADA CON AJUSTE DINÁMICO DE FILAS
        if st.session_state.datos[key_f]:
            filas_validas = [f for f in st.session_state.datos[key_f] if f.get('Prod', '').strip() != ""]
            
            if filas_validas:
                df_pdf = pd.DataFrame(filas_validas)
                
                if st.button("🚀 GENERAR PDF", key=f"pdf_{fid}_{idx}", type="primary", use_container_width=True):
                    with st.spinner("Generando PDF..."):
                        try:
                            pdf = FPDF(orientation='P')
                            pdf.add_page()
                            
                            pdf.set_left_margin(10)
                            pdf.set_right_margin(10)
                            pdf.set_top_margin(15)
                            
                            if logo_rev:
                                try:
                                    agregar_imagen_segura(pdf, logo_rev, 10, 15, 30)
                                except:
                                    pass
                            
                            pdf.set_font("Arial", 'B', 18)
                            pdf.set_xy(0, 15)
                            pdf.cell(0, 10, txt=nombre_rev.upper(), ln=True, align='C')
                            
                            pdf.set_font("Arial", '', 11)
                            pdf.cell(0, 7, f"CLIENTE: {nom_cli.upper()} | FECHA DE PAGO: {fec_p.strftime('%d-%m-%Y')}", ln=True, align='C')
                            pdf.ln(8)
                            
                            # ANCHOS OPTIMIZADOS - columna de producto MÁS ANCHA
                            cw = [12, 85, 12, 20, 20, 20, 20, 20]  # Producto: 85mm, otras: 20mm
                            
                            # Encabezados
                            pdf.set_fill_color(240, 240, 240)
                            pdf.set_font("Arial", 'B', 9)
                            
                            headers = ["Pág", "Producto", "Cant", "P.Cat", "T.Cat", "P.List", "T.List", "Gan."]
                            for i, header in enumerate(headers):
                                pdf.cell(cw[i], 8, header, 1, 0, 'C', True)
                            pdf.ln()
                            
                            pdf.set_font("Arial", '', 8)
                            
                            for _, r in df_pdf.iterrows():
                                # Prepara texto del producto (sin truncar mucho)
                                prod_text = limpiar_texto_para_pdf(str(r['Prod']))
                                
                                # Calcular valores
                                v_tc = r['Cant'] * r['Cat_U']
                                v_tl = r['Cant'] * r['List_U']
                                gan_fila = v_tc - v_tl
                                
                                # CALCULAR ALTURA DINÁMICA usando la nueva función
                                altura_fila, lineas_producto = calcular_altura_fila(pdf, prod_text, cw[1])
                                
                                # Guardar posición
                                x, y = pdf.get_x(), pdf.get_y()
                                
                                # Verificar si cabe en la página actual
                                if y + altura_fila > 270:  # Cerca del final
                                    pdf.add_page()
                                    # Reimprimir encabezados en nueva página
                                    pdf.set_fill_color(240, 240, 240)
                                    pdf.set_font("Arial", 'B', 9)
                                    for i, header in enumerate(headers):
                                        pdf.cell(cw[i], 8, header, 1, 0, 'C', True)
                                    pdf.ln()
                                    pdf.set_font("Arial", '', 8)
                                    x, y = pdf.get_x(), pdf.get_y()  # Actualizar posición
                                
                                # Columna 1: Página
                                pdf.cell(cw[0], altura_fila, str(r['Pag']), 1, 0, 'C')
                                
                                # Columna 2: Producto - IMPLEMENTACIÓN MEJORADA
                                pdf.set_xy(x + cw[0], y)
                                
                                if len(lineas_producto) > 1:
                                    # Si necesita múltiples líneas
                                    altura_por_linea = altura_fila / len(lineas_producto)
                                    for j, linea in enumerate(lineas_producto):
                                        linea_y = y + (j * altura_por_linea)
                                        pdf.set_xy(x + cw[0], linea_y)
                                        pdf.cell(cw[1], altura_por_linea, linea, 1, 0, 'L')
                                else:
                                    # Si cabe en una línea
                                    pdf.cell(cw[1], altura_fila, lineas_producto[0], 1, 0, 'L')
                                
                                # Reposicionar para columnas 3-8
                                pdf.set_xy(x + cw[0] + cw[1], y)
                                
                                # Columnas restantes
                                pdf.cell(cw[2], altura_fila, str(r['Cant']), 1, 0, 'C')
                                
                                # Precio Catálogo
                                pdf.cell(cw[3], altura_fila, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                                
                                # Total Catálogo
                                pdf.set_fill_color(225, 245, 254)
                                pdf.cell(cw[4], altura_fila, f"${fmt(v_tc)}", 1, 0, 'R', True)
                                
                                # Precio Lista
                                pdf.set_fill_color(255, 255, 255)
                                pdf.cell(cw[5], altura_fila, f"${fmt(r['List_U'])}", 1, 0, 'R')
                                
                                # Total Lista
                                pdf.set_fill_color(255, 243, 224)
                                pdf.cell(cw[6], altura_fila, f"${fmt(v_tl)}", 1, 0, 'R', True)
                                
                                # Ganancia
                                if gan_fila >= 0:
                                    pdf.set_fill_color(232, 245, 233)
                                else:
                                    pdf.set_fill_color(255, 230, 230)
                                
                                pdf.set_font("Arial", 'B', 8)
                                pdf.cell(cw[7], altura_fila, f"${fmt(gan_fila)}", 1, 1, 'R', True)
                                pdf.set_font("Arial", '', 8)
                            
                            # Línea de totales
                            pdf.set_fill_color(230, 230, 230)
                            pdf.set_font("Arial", 'B', 10)
                            
                            # Calcular ancho para alineación
                            total_cell_width = cw[0] + cw[1] + cw[2] + cw[3]
                            
                            pdf.cell(total_cell_width, 10, "TOTALES FINALES", 1, 0, 'R', True)
                            pdf.cell(cw[4], 10, f"${fmt(s_tc)}", 1, 0, 'R', True)
                            pdf.cell(cw[5], 10, "", 1, 0, 'C', True)  # Celda vacía
                            pdf.cell(cw[6], 10, f"${fmt(s_tl)}", 1, 0, 'R', True)
                            
                            if s_tg >= 0:
                                pdf.set_fill_color(232, 245, 233)
                            else:
                                pdf.set_fill_color(255, 230, 230)
                            
                            pdf.cell(cw[7], 10, f"${fmt(s_tg)}", 1, 1, 'R', True)
                            
                            # Información de pago
                            pdf.ln(8)
                            
                            if logo_pago:
                                try:
                                    agregar_imagen_segura(pdf, logo_pago, 10, pdf.get_y(), 15)
                                except:
                                    pass
                            
                            pdf.set_xy(30, pdf.get_y() + 5)
                            pdf.set_font("Arial", 'B', 12)
                            if num_pago:
                                pdf.cell(0, 5, f"Pagar a: {num_pago}")
                            else:
                                pdf.cell(0, 5, "Información de pago no configurada")
                            
                            if qr_pago:
                                try:
                                    agregar_imagen_segura(pdf, qr_pago, 160, pdf.get_y() - 5, 25)
                                except:
                                    pass
                            
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
                            
                            # Método alternativo ultra simple
                            try:
                                pdf = FPDF()
                                pdf.add_page()
                                
                                pdf.set_font("Arial", 'B', 16)
                                pdf.cell(0, 10, f"FACTURA: {nom_cli}", 0, 1, 'C')
                                pdf.set_font("Arial", '', 10)
                                pdf.cell(0, 5, f"Fecha: {fec_p.strftime('%d-%m-%Y')}", 0, 1, 'C')
                                pdf.ln(5)
                                
                                # Tabla más simple con menos columnas
                                pdf.set_font("Arial", 'B', 8)
                                pdf.cell(15, 6, "Pág", 1, 0, 'C')
                                pdf.cell(100, 6, "Producto", 1, 0, 'C')
                                pdf.cell(20, 6, "Cant", 1, 0, 'C')
                                pdf.cell(30, 6, "Total", 1, 0, 'R')
                                pdf.cell(30, 6, "Gan.", 1, 1, 'R')
                                
                                pdf.set_font("Arial", '', 7)
                                for _, r in df_pdf.iterrows():
                                    prod_text = truncar_texto(limpiar_texto_para_pdf(str(r['Prod'])), 40)
                                    v_tc = r['Cant'] * r['Cat_U']
                                    v_tl = r['Cant'] * r['List_U']
                                    gan_fila = v_tc - v_tl
                                    
                                    pdf.cell(15, 5, str(r['Pag']), 1, 0, 'C')
                                    pdf.cell(100, 5, prod_text, 1, 0, 'L')
                                    pdf.cell(20, 5, str(r['Cant']), 1, 0, 'C')
                                    pdf.cell(30, 5, f"${fmt(v_tc)}", 1, 0, 'R')
                                    pdf.cell(30, 5, f"${fmt(gan_fila)}", 1, 1, 'R')
                                
                                # Totales
                                pdf.set_font("Arial", 'B', 9)
                                pdf.cell(135, 8, "TOTALES:", 1, 0, 'R')
                                pdf.cell(30, 8, f"${fmt(s_tc)}", 1, 0, 'R')
                                pdf.cell(30, 8, f"${fmt(s_tg)}", 1, 1, 'R')
                                
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

