import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import os
import tempfile
import re
from pypdf import PdfReader

st.set_page_config(page_title="Facturación Pro", layout="wide")

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
        cliente_match = re.search(r"CLIENTE:\s*(.*)", text)
        cliente = cliente_match.group(1).strip() if cliente_match else "Cliente Nuevo"
        # Patrón para extraer filas: Pág, Producto, Cant, Precio Cat...
        patron = r"(\d+)\s+(.*?)\s+(\d+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)"
        matches = re.findall(patron, text)
        productos = []
        for m in matches:
            productos.append({
                "Pag": m[0], "Prod": m[1].strip(), "Cant": int(m[2]),
                "Cat_U": int(m[3].replace('.', '')), "List_U": int(m[5].replace('.', ''))
            })
        return {"cliente": cliente, "productos": productos if productos else None}
    except:
        return None

# --- ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    with st.expander("🖼️ Logos y Marca", expanded=False):
        logo_rev = st.file_uploader("Logo Revista", type=["png", "jpg", "jpeg"])
        nombre_rev = st.text_input("Nombre Revista", "MI REVISTA")
    with st.expander("💳 Datos de Pago", expanded=False):
        num_pago = st.text_input("Cuenta / Nequi")
        logo_pago = st.file_uploader("Logo Pago", type=["png", "jpg", "jpeg"])
        qr_pago = st.file_uploader("QR Pago", type=["png", "jpg", "jpeg"])
    st.divider()
    archivo_pdf = st.file_uploader("🔄 Re-editar PDF", type=["pdf"])
    if archivo_pdf and st.button("Importar Datos"):
        res = importar_datos_pdf(archivo_pdf)
        if res and res["productos"]:
            nid = len(st.session_state.facturas)
            st.session_state.facturas.append({"id": nid, "name": res["cliente"]})
            st.session_state.datos[f"f_{nid}"] = res["productos"]
            st.rerun()

# --- PANEL PRINCIPAL ---
st.title("📑 Facturación Inteligente")

if st.button("➕ Crear Nueva Factura"):
    nid = len(st.session_state.facturas)
    st.session_state.facturas.append({"id": nid, "name": f"Factura {nid+1}"})
    st.rerun()

tabs = st.tabs([f["name"] for f in st.session_state.facturas])

for idx, tab in enumerate(tabs):
    with tab:
        fid = st.session_state.facturas[idx]["id"]
        key_f = f"f_{fid}"
        if key_f not in st.session_state.datos:
            st.session_state.datos[key_f] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]

        c1, c2 = st.columns(2)
        nom_cli = c1.text_input("Cliente", key=f"n_{fid}", value=st.session_state.facturas[idx]["name"] if st.session_state.facturas[idx]["name"] != "Nueva Factura" else "")
        fec_p = c2.date_input("Fecha de pago", date.today(), key=f"d_{fid}")
        st.session_state.facturas[idx]["name"] = nom_cli if nom_cli else "Nueva Factura"

        indices_a_borrar = []
        s_tc, s_tl, s_tg = 0, 0, 0

        # Etiquetas de columnas (más pequeñas)
        st.markdown("<div style='font-size:0.8rem; color:gray; margin-bottom:5px;'>Pág | Producto | Cant | Unit. Cat | Total Cat | Unit. List | Total List | Ganancia</div>", unsafe_allow_html=True)

        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([0.5, 2.5, 0.6, 1.2, 1.2, 1.2, 1.2, 1.2, 0.4])
            fila['Pag'] = cols[0].text_input("P", value=fila['Pag'], key=f"pg_{fid}_{i}", label_visibility="collapsed")
            fila['Prod'] = cols[1].text_input("Pr", value=fila['Prod'], key=f"pr_{fid}_{i}", label_visibility="collapsed")
            fila['Cant'] = cols[2].number_input("C", value=int(fila['Cant']), min_value=1, key=f"ct_{fid}_{i}", label_visibility="collapsed")
            fila['Cat_U'] = cols[3].number_input("UC", value=int(fila['Cat_U']), key=f"uc_{fid}_{i}", label_visibility="collapsed")
            
            tc_val = fila['Cant'] * fila['Cat_U']
            cols[4].markdown(f"<p style='font-size:0.9rem; margin-top:5px;'>${fmt(tc_val)}</p>", unsafe_allow_html=True)
            
            fila['List_U'] = cols[5].number_input("UL", value=int(fila['List_U']), key=f"ul_{fid}_{i}", label_visibility="collapsed")
            tl_val = fila['Cant'] * fila['List_U']
            cols[6].markdown(f"<p style='font-size:0.9rem; margin-top:5px;'>${fmt(tl_val)}</p>", unsafe_allow_html=True)
            
            gan_val = tc_val - tl_val
            cols[7].markdown(f"<p style='font-size:0.9rem; margin-top:5px; color:#2e7d32; font-weight:bold;'>${fmt(gan_val)}</p>", unsafe_allow_html=True)
            
            s_tc += tc_val; s_tl += tl_val; s_tg += gan_val
            
            if cols[8].button("🗑️", key=f"del_{fid}_{i}"):
                indices_a_borrar.append(i)

        if indices_a_borrar:
            for index in sorted(indices_a_borrar, reverse=True):
                st.session_state.datos[key_f].pop(index)
            st.rerun()

        # BARRA DE TOTALES EN VIVO (SISTEMA)
        st.markdown(f"""
            <div style="background-color:#f8f9fa; border:1px solid #dee2e6; padding:15px; border-radius:10px; margin:20px 0;">
                <div style="display:flex; justify-content:space-around; align-items:center;">
                    <div style="text-align:center;"><small>TOTAL CAT</small><br><strong style="font-size:1.2rem;">${fmt(s_tc)}</strong></div>
                    <div style="text-align:center;"><small>TOTAL LIST</small><br><strong style="font-size:1.2rem;">${fmt(s_tl)}</strong></div>
                    <div style="text-align:center; color:#1b5e20;"><small>GANANCIA TOTAL</small><br><strong style="font-size:1.4rem;">${fmt(s_tg)}</strong></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_bot = st.columns([1.5, 8.5])
        if col_bot[0].button("➕ Agregar Fila", key=f"add_{fid}"):
            st.session_state.datos[key_f].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
            st.rerun()

        # GENERACIÓN DEL PDF
        df_pdf = pd.DataFrame(st.session_state.datos[key_f])
        df_pdf = df_pdf[df_pdf['Prod'].str.strip() != ""].copy()

        if not df_pdf.empty:
            if st.button("🚀 GENERAR PDF PROFESIONAL", key=f"pdf_bt_{fid}"):
                pdf = FPDF()
                pdf.add_page()
                if logo_rev: agregar_imagen_segura(pdf, logo_rev, 10, 10, 35)
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 15, txt=nombre_rev.upper(), ln=True, align='R')
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 5, f"CLIENTE: {nom_cli.upper()} | FECHA: {fec_p.strftime('%d-%m-%Y')}", ln=True, align='R')
                pdf.ln(10)

                # Encabezados
                pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 8)
                cols_w = [10, 55, 10, 23, 23, 23, 23, 23]
                h_txt = ["Pág", "Producto", "Cant", "U. Cat", "T. Cat", "U. List", "T. List", "Gan."]
                for i in range(len(h_txt)): pdf.cell(cols_w[i], 10, h_txt[i], 1, 0, 'C', True)
                pdf.ln()

                # Filas con MultiCell alineado
                pdf.set_font("Arial", '', 8)
                for _, r in df_pdf.iterrows():
                    l_nombre = (pdf.get_string_width(str(r['Prod'])) // 53) + 1
                    h_fila = max(8, l_nombre * 5)
                    x_pos, y_pos = pdf.get_x(), pdf.get_y()
                    
                    pdf.cell(10, h_fila, str(r['Pag']), 1, 0, 'C')
                    pdf.multi_cell(55, 5 if l_nombre > 1 else h_fila, str(r['Prod']), 1, 'L')
                    
                    # RETORNO DE POSICIÓN PARA EVITAR DESFASES
                    pdf.set_xy(x_pos + 65, y_pos)
                    
                    tc_row = r['Cant'] * r['Cat_U']
                    tl_row = r['Cant'] * r['List_U']
                    
                    pdf.cell(10, h_fila, str(r['Cant']), 1, 0, 'C')
                    pdf.cell(23, h_fila, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                    pdf.set_fill_color(225, 245, 254); pdf.cell(23, h_fila, f"${fmt(tc_row)}", 1, 0, 'R', True)
                    pdf.cell(23, h_fila, f"${fmt(r['List_U'])}", 1, 0, 'R')
                    pdf.set_fill_color(255, 243, 224); pdf.cell(23, h_fila, f"${fmt(tl_row)}", 1, 0, 'R', True)
                    pdf.set_fill_color(232, 245, 233); pdf.set_font("Arial", 'B', 8)
                    pdf.cell(23, h_fila, f"${fmt(tc_row - tl_row)}", 1, 1, 'R', True)
                    pdf.set_font("Arial", '', 8)

                # TOTALES FINALES PDF (FIXED ALIGNMENT)
                pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 9)
                pdf.cell(75, 12, "TOTALES FINALES", 1, 0, 'R', True)
                pdf.cell(33, 12, "", 1, 0, 'C', True)
                pdf.cell(23, 12, f"${fmt(s_tc)}", 1, 0, 'R', True)
                pdf.cell(23, 12, "", 1, 0, 'C', True)
                pdf.cell(23, 12, f"${fmt(s_tl)}", 1, 0, 'R', True)
                pdf.cell(23, 12, f"${fmt(s_tg)}", 1, 1, 'R', True)

                # Pie de página / Pago
                pdf.ln(8)
                y_pie = pdf.get_y()
                if logo_pago: agregar_imagen_segura(pdf, logo_pago, 10, y_pie, 15)
                pdf.set_xy(30, y_pie + 5); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 5, f"Pagar a: {num_pago}")
                if qr_pago: agregar_imagen_segura(pdf, qr_pago, 160, y_pie, 28)

                res_p = pdf.output(dest='S').encode('latin-1')
                st.download_button("⬇️ Descargar Factura PDF", res_p, file_name=f"Factura_{nom_cli}.pdf")

