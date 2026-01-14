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

def importar_datos_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        # Buscar Cliente
        cliente_match = re.search(r"CLIENTE:\s*(.*)\s*\|", text)
        cliente = cliente_match.group(1).strip() if cliente_match else "Cliente Importado"
        
        # Buscar Filas de productos (Pág, Prod, Cant, UC, TC, UL, TL, Gan)
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

# --- ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Botón para cambiar tema
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
    
    # SECCIÓN RESTAURADA: IMPORTAR PDF
    st.subheader("🔄 Re-editar")
    archivo_pdf = st.file_uploader("Subir factura PDF anterior", type=["pdf"])
    if archivo_pdf and st.button("📥 Cargar Datos del PDF"):
        res = importar_datos_pdf(archivo_pdf)
        if res and res["productos"]:
            nid = len(st.session_state.facturas)
            st.session_state.facturas.append({"id": nid, "name": res["cliente"]})
            st.session_state.datos[f"f_{nid}"] = res["productos"]
            st.success("¡Datos cargados en una nueva pestaña!")
            st.rerun()
        else:
            st.warning("No se detectaron productos legibles en el PDF.")

# --- PANEL PRINCIPAL ---
st.title("📑 Facturación Profesional")

if st.button("➕ Crear Nueva Factura"):
    nid = len(st.session_state.facturas)
    st.session_state.facturas.append({"id": nid, "name": f"Factura {nid+1}"})
    st.rerun()

tabs = st.tabs([f["name"] for f in st.session_state.facturas])

for idx, tab in enumerate(tabs):
    with tab:
        fid = st.session_state.facturas[idx]["id"]
        key_f = f"f_{fid}"
        
        # Inicializar datos si la pestaña es nueva
        if key_f not in st.session_state.datos:
            st.session_state.datos[key_f] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]

        c1, c2 = st.columns(2)
        nom_cli = c1.text_input("Cliente", key=f"n_{fid}", value=st.session_state.facturas[idx]["name"] if st.session_state.facturas[idx]["name"] != "Nueva Factura" else "")
        fec_p = c2.date_input("Fecha de Pago", date.today(), key=f"d_{fid}")
        st.session_state.facturas[idx]["name"] = nom_cli if nom_cli else "Nueva Factura"

        s_tc, s_tl, s_tg = 0, 0, 0
        
        # ENCABEZADOS CLAROS
        st.markdown("<small style='color:gray;'>Pág | Producto | Cant | Precio Catálogo | Total Catálogo | Precio Lista | Total Lista | Ganancia (Cat-List)</small>", unsafe_allow_html=True)

        # Renderizar filas
        filas_a_eliminar = None
        
        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([0.5, 2.5, 0.6, 1.2, 1.2, 1.2, 1.2, 1.2, 0.4])
            
            fila['Pag'] = cols[0].text_input("P", value=fila['Pag'], key=f"pg_{fid}_{i}", label_visibility="collapsed")
            fila['Prod'] = cols[1].text_input("Pr", value=fila['Prod'], key=f"pr_{fid}_{i}", label_visibility="collapsed")
            fila['Cant'] = cols[2].number_input("C", value=int(fila['Cant']), min_value=1, key=f"ct_{fid}_{i}", label_visibility="collapsed")
            fila['Cat_U'] = cols[3].number_input("PC", value=int(fila['Cat_U']), key=f"uc_{fid}_{i}", label_visibility="collapsed")
            
            tc = fila['Cant'] * fila['Cat_U']
            cols[4].markdown(f"**${fmt(tc)}**")
            
            fila['List_U'] = cols[5].number_input("PL", value=int(fila['List_U']), key=f"ul_{fid}_{i}", label_visibility="collapsed")
            tl = fila['Cant'] * fila['List_U']
            cols[6].markdown(f"**${fmt(tl)}**")
            
            # GANANCIA = Total Catálogo - Total Lista
            gan = tc - tl
            color_gan = "#2e7d32" if gan >= 0 else "#d32f2f"
            cols[7].markdown(f"<span style='color:{color_gan}; font-weight:bold;'>${fmt(gan)}</span>", unsafe_allow_html=True)
            
            s_tc += tc
            s_tl += tl
            s_tg += gan
            
            # Botón de eliminar
            if cols[8].button("🗑️", key=f"del_{fid}_{i}"):
                filas_a_eliminar = i

        # Eliminar fila después del loop
        if filas_a_eliminar is not None:
            st.session_state.datos[key_f].pop(filas_a_eliminar)
            st.rerun()

        # BARRA DE TOTALES (SISTEMA)
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

        if st.button("➕ Agregar Fila", key=f"add_{fid}"):
            st.session_state.datos[key_f].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
            st.rerun()

        # GENERACIÓN DE PDF
        df_pdf = pd.DataFrame(st.session_state.datos[key_f])
        df_pdf = df_pdf[df_pdf['Prod'].str.strip() != ""].copy()

        if not df_pdf.empty:
            if st.button("🚀 GENERAR PDF", key=f"pdf_{fid}"):
                pdf = FPDF()
                pdf.add_page()
                if logo_rev:
                    agregar_imagen_segura(pdf, logo_rev, 10, 10, 35)
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 15, txt=nombre_rev.upper(), ln=True, align='R')
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 5, f"CLIENTE: {nom_cli.upper()} | FECHA DE PAGO: {fec_p.strftime('%d-%m-%Y')}", ln=True, align='R')
                pdf.ln(10)

                cw = [10, 55, 10, 23, 23, 23, 23, 23]
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Arial", 'B', 8)
                # ENCABEZADOS CLAROS EN EL PDF
                h_txt = ["Pág", "Producto", "Cant", "P. Cat", "T. Cat", "P. List", "T. List", "Gan."]
                for i in range(len(h_txt)):
                    pdf.cell(cw[i], 10, h_txt[i], 1, 0, 'C', True)
                pdf.ln()

                pdf.set_font("Arial", '', 8)
                for _, r in df_pdf.iterrows():
                    l_n = (pdf.get_string_width(str(r['Prod'])) // 53) + 1
                    h_f = max(8, l_n * 5)
                    x, y = pdf.get_x(), pdf.get_y()
                    pdf.cell(cw[0], h_f, str(r['Pag']), 1, 0, 'C')
                    pdf.multi_cell(cw[1], 5 if l_n > 1 else h_f, str(r['Prod']), 1, 'L')
                    pdf.set_xy(x + cw[0] + cw[1], y)
                    
                    v_tc, v_tl = r['Cant'] * r['Cat_U'], r['Cant'] * r['List_U']
                    gan_fila = v_tc - v_tl  # Catálogo - Lista
                    
                    pdf.cell(cw[2], h_f, str(r['Cant']), 1, 0, 'C')
                    pdf.cell(cw[3], h_f, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                    pdf.set_fill_color(225, 245, 254)
                    pdf.cell(cw[4], h_f, f"${fmt(v_tc)}", 1, 0, 'R', True)
                    pdf.cell(cw[5], h_f, f"${fmt(r['List_U'])}", 1, 0, 'R')
                    pdf.set_fill_color(255, 243, 224)
                    pdf.cell(cw[6], h_f, f"${fmt(v_tl)}", 1, 0, 'R', True)
                    
                    # Color de ganancia según resultado
                    if gan_fila >= 0:
                        pdf.set_fill_color(232, 245, 233)  # Verde para ganancia positiva
                    else:
                        pdf.set_fill_color(255, 230, 230)  # Rojo claro para pérdida
                    
                    pdf.set_font("Arial", 'B', 8)
                    pdf.cell(cw[7], h_f, f"${fmt(gan_fila)}", 1, 1, 'R', True)
                    pdf.set_font("Arial", '', 8)

                # Fila de Totales Alineada
                pdf.set_fill_color(230, 230, 230)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(75, 12, "TOTALES FINALES", 1, 0, 'R', True)
                pdf.cell(23, 12, "", 1, 0, 'C', True)
                pdf.cell(23, 12, f"${fmt(s_tc)}", 1, 0, 'R', True)
                pdf.cell(23, 12, "", 1, 0, 'C', True)
                pdf.cell(23, 12, f"${fmt(s_tl)}", 1, 0, 'R', True)
                
                # Color del total de ganancia
                if s_tg >= 0:
                    pdf.set_fill_color(232, 245, 233)
                else:
                    pdf.set_fill_color(255, 230, 230)
                
                pdf.cell(23, 12, f"${fmt(s_tg)}", 1, 1, 'R', True)

                pdf.ln(5)
                y_p = pdf.get_y()
                if logo_pago:
                    agregar_imagen_segura(pdf, logo_pago, 10, y_p, 15)
                pdf.set_xy(30, y_p + 5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 5, f"Pagar a: {num_pago}")
                if qr_pago:
                    agregar_imagen_segura(pdf, qr_pago, 160, y_p, 25)

                res_pdf = pdf.output(dest='S').encode('latin-1')
                st.download_button("⬇️ Descargar PDF", res_pdf, file_name=f"Factura_{nom_cli}.pdf")

