import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import io
import os
import tempfile
import re
from pypdf import PdfReader

st.set_page_config(page_title="Facturación Inteligente", layout="wide")

# --- FUNCIONES DE APOYO ---
def fmt(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except:
        return "0"

def agregar_imagen_segura(pdf, uploaded_file, x, y, w):
    if uploaded_file is not None:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            pdf.image(tmp_path, x=x, y=y, w=w)
            os.unlink(tmp_path)
        except Exception:
            pass

# --- FUNCIÓN PARA RE-EDITAR PDF ---
def importar_datos_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        cliente_match = re.search(r"CLIENTE:\s*(.*)", text)
        cliente = cliente_match.group(1).strip() if cliente_match else "Cliente Recuperado"
        
        lineas = text.split('\n')
        productos = []
        for l in lineas:
            match = re.match(r"^(\d+)\s+(.*?)\s+(\d+)\s+\$", l)
            if match:
                productos.append({
                    "Pag": match.group(1),
                    "Prod": match.group(2),
                    "Cant": int(match.group(3)),
                    "Cat_U": 0, "List_U": 0 
                })
        
        if not productos:
            productos = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]
            
        return {"cliente": cliente, "productos": productos}
    except Exception:
        return None

# --- ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎨 Configuración")
    logo_rev = st.file_uploader("Logo Revista", type=["png", "jpg", "jpeg"])
    nombre_rev = st.text_input("Nombre de la Revista", "REVISTA PRO")
    
    st.divider()
    st.subheader("💳 Información de Pago")
    num_pago = st.text_input("Número de cuenta / Nequi")
    logo_pago = st.file_uploader("Logo Pago", type=["png", "jpg", "jpeg"])
    qr_pago = st.file_uploader("QR Pago", type=["png", "jpg", "jpeg"])

    st.divider()
    st.subheader("🔄 Re-editar Factura")
    archivo_pdf = st.file_uploader("Subir factura PDF", type=["pdf"])
    if archivo_pdf and st.button("Cargar datos del PDF"):
        res = importar_datos_pdf(archivo_pdf)
        if res:
            nid = len(st.session_state.facturas)
            st.session_state.facturas.append({"id": nid, "name": res["cliente"]})
            st.session_state.datos[f"f_{nid}"] = res["productos"]
            st.rerun()

# --- MAIN ---
st.title("📑 Sistema de Facturación Múltiple")

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
        with c1:
            nom_cli = st.text_input("Cliente", key=f"n_{fid}")
            if nom_cli: st.session_state.facturas[idx]["name"] = nom_cli
        with c2:
            fec_p = st.date_input("Fecha de pago", date.today(), key=f"d_{fid}")

        indices_a_borrar = []
        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([0.5, 3, 0.8, 1.5, 1.5, 1.5, 1.5, 1.5, 0.5])
            fila['Pag'] = cols[0].text_input("Pág", value=fila['Pag'], key=f"pg_{fid}_{i}")
            fila['Prod'] = cols[1].text_area("Producto", value=fila['Prod'], key=f"pr_{fid}_{i}", height=68)
            fila['Cant'] = cols[2].number_input("Cant", value=fila['Cant'], min_value=1, key=f"ct_{fid}_{i}")
            fila['Cat_U'] = cols[3].number_input("Unit Cat", value=fila['Cat_U'], key=f"uc_{fid}_{i}")
            
            t_cat = fila['Cant'] * fila['Cat_U']
            cols[4].markdown(f"<div style='background-color:#e1f5fe; padding:5px; border-radius:5px; text-align:center;'><b>Total Cat</b><br>${fmt(t_cat)}</div>", unsafe_allow_html=True)
            
            fila['List_U'] = cols[5].number_input("Unit List", value=fila['List_U'], key=f"ul_{fid}_{i}")
            t_list = fila['Cant'] * fila['List_U']
            cols[6].markdown(f"<div style='background-color:#fff3e0; padding:5px; border-radius:5px; text-align:center;'><b>Total List</b><br>${fmt(t_list)}</div>", unsafe_allow_html=True)
            
            gan = t_cat - t_list
            cols[7].markdown(f"<div style='background-color:#e8f5e9; padding:5px; border-radius:5px; text-align:center;'><b>Ganancia</b><br>${fmt(gan)}</div>", unsafe_allow_html=True)
            
            if cols[8].button("🗑️", key=f"del_{fid}_{i}"):
                indices_a_borrar.append(i)

        if indices_a_borrar:
            for index in sorted(indices_a_borrar, reverse=True):
                st.session_state.datos[key_f].pop(index)
            st.rerun()

        if st.button("➕ Agregar fila", key=f"add_row_{fid}"):
            st.session_state.datos[key_f].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
            st.rerun()

        df_completo = pd.DataFrame(st.session_state.datos[key_f])
        df_validos = df_completo[df_completo['Prod'].str.strip() != ""].copy()

        if not df_validos.empty:
            df_validos['TC'] = df_validos['Cant'] * df_validos['Cat_U']
            df_validos['TL'] = df_validos['Cant'] * df_validos['List_U']
            df_validos['TG'] = df_validos['TC'] - df_validos['TL']
            
            st.divider()
            if st.button("🚀 GENERAR PDF PROFESIONAL", key=f"pdf_btn_{fid}"):
                pdf = FPDF()
                pdf.add_page()
                
                if logo_rev: agregar_imagen_segura(pdf, logo_rev, 10, 10, 35)
                
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 15, txt=nombre_rev.upper(), ln=True, align='R')
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 5, f"CLIENTE: {nom_cli.upper()}", ln=True, align='R')
                pdf.cell(0, 5, f"FECHA DE PAGO: {fec_p.strftime('%d-%m-%Y')}", ln=True, align='R')
                pdf.ln(10)

                # Encabezados
                pdf.set_fill_color(40, 40, 40)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", 'B', 8)
                w_col = [10, 55, 10, 23, 23, 23, 23, 23]
                headers = ["Pág", "Producto", "Cant", "U. Cat", "T. Cat", "U. List", "T. List", "Gan."]
                for i in range(len(headers)):
                    pdf.cell(w_col[i], 10, headers[i], 1, 0, 'C', True)
                pdf.ln()

                # Filas con Multi-Cell para nombres largos
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 8)
                
                for _, r in df_validos.iterrows():
                    # Calculamos el alto necesario basado en el nombre del producto
                    # El ancho de la columna de producto es 55
                    lineas_nombre = pdf.get_string_width(str(r['Prod'])) / 53
                    alto_fila = 8 if lineas_nombre < 1 else (int(lineas_nombre) + 1) * 5
                    
                    x_start = pdf.get_x()
                    y_start = pdf.get_y()
                    
                    pdf.cell(10, alto_fila, str(r['Pag']), 1, 0, 'C')
                    
                    # Columna Producto con MultiCell
                    pdf.multi_cell(55, 5 if lineas_nombre > 1 else alto_fila, str(r['Prod']), 1, 'L')
                    
                    # Volvemos a la posición para las celdas siguientes
                    pdf.set_xy(x_start + 65, y_start)
                    
                    pdf.cell(10, alto_fila, str(r['Cant']), 1, 0, 'C')
                    pdf.cell(23, alto_fila, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                    
                    pdf.set_fill_color(225, 245, 254)
                    pdf.cell(23, alto_fila, f"${fmt(r['TC'])}", 1, 0, 'R', True)
                    
                    pdf.cell(23, alto_fila, f"${fmt(r['List_U'])}", 1, 0, 'R')
                    
                    pdf.set_fill_color(255, 243, 224)
                    pdf.cell(23, alto_fila, f"${fmt(r['TL'])}", 1, 0, 'R', True)
                    
                    pdf.set_fill_color(232, 245, 233)
                    pdf.set_font("Arial", 'B', 8)
                    pdf.cell(23, alto_fila, f"${fmt(r['TG'])}", 1, 1, 'R', True)
                    pdf.set_font("Arial", '', 8)

                # Totales
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(75, 12, "TOTALES FINALES", 1, 0, 'R', True)
                pdf.cell(33, 12, "", 1, 0, '', True)
                pdf.cell(23, 12, f"${fmt(df_validos['TC'].sum())}", 1, 0, 'C', True)
                pdf.cell(23, 12, "", 1, 0, '', True)
                pdf.cell(23, 12, f"${fmt(df_validos['TL'].sum())}", 1, 0, 'C', True)
                pdf.cell(23, 12, f"${fmt(df_validos['TG'].sum())}", 1, 1, 'C', True)

                # Pago
                pdf.ln(10)
                y_p = pdf.get_y()
                if logo_pago: agregar_imagen_segura(pdf, logo_pago, 10, y_p, 15)
                pdf.set_xy(30, y_p + 5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 5, f"Pagar a: {num_pago}")
                if qr_pago: agregar_imagen_segura(pdf, qr_pago, 160, y_p - 10, 30)

                res_pdf = pdf.output(dest='S').encode('latin-1')
                st.download_button(f"⬇️ Descargar Factura", res_pdf, file_name=f"Factura_{nom_cli}.pdf")


