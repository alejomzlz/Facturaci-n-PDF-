import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import io
import os
import tempfile
from pypdf import PdfReader

st.set_page_config(page_title="Facturación Pro", layout="wide")

# Función para formatear números con separador de miles
def fmt(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except:
        return "0"

# Función segura para manejar imágenes en FPDF
def agregar_imagen_segura(pdf, uploaded_file, x, y, w):
    if uploaded_file is not None:
        try:
            # Creamos un archivo temporal para que FPDF no falle al leer bytes
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            pdf.image(tmp_path, x=x, y=y, w=w)
            os.unlink(tmp_path) # Borramos el temporal después de usarlo
        except Exception as e:
            st.error(f"Error con imagen {uploaded_file.name}: {e}")

# --- ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🎨 Personalización")
    logo_rev = st.file_uploader("Logo Revista", type=["png", "jpg", "jpeg"])
    nombre_rev = st.text_input("Nombre de la Revista", "REVISTA AUTOMÁTICA")
    
    st.divider()
    st.subheader("💳 Información de Pago")
    num_pago = st.text_input("Número de cuenta / Celular")
    logo_pago = st.file_uploader("Logo Medio de Pago", type=["png", "jpg", "jpeg"])
    qr_pago = st.file_uploader("Imagen QR de Pago", type=["png", "jpg", "jpeg"])

# --- CUERPO PRINCIPAL ---
st.title("📑 Generador de Facturas Profesional")

if st.button("➕ Crear nueva factura en otra pestaña"):
    nid = len(st.session_state.facturas)
    st.session_state.facturas.append({"id": nid, "name": f"Factura {nid+1}"})
    st.rerun()

tabs = st.tabs([f["name"] for f in st.session_state.facturas])

for idx, tab in enumerate(tabs):
    with tab:
        fid = st.session_state.facturas[idx]["id"]
        c1, c2 = st.columns(2)
        with c1:
            nom_cli = st.text_input("Nombre del Cliente", key=f"n_{fid}")
            if nom_cli: st.session_state.facturas[idx]["name"] = nom_cli
        with c2:
            fec_p = st.date_input("Fecha de pago", date.today(), key=f"d_{fid}")

        key_f = f"f_{fid}"
        if key_f not in st.session_state.datos:
            st.session_state.datos[key_f] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]

        # INTERFAZ DE CARGA DE PRODUCTOS
        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([1, 3, 1, 2, 2, 2, 2, 2])
            fila['Pag'] = cols[0].text_input("Pág", value=fila['Pag'], key=f"pg_{fid}_{i}")
            fila['Prod'] = cols[1].text_input("Producto", value=fila['Prod'], key=f"pr_{fid}_{i}")
            fila['Cant'] = cols[2].number_input("Cant", value=fila['Cant'], min_value=1, key=f"ct_{fid}_{i}")
            fila['Cat_U'] = cols[3].number_input("P. Unit Cat", value=fila['Cat_U'], key=f"uc_{fid}_{i}")
            
            t_cat = fila['Cant'] * fila['Cat_U']
            cols[4].write("Total Cat")
            cols[4].info(fmt(t_cat))
            
            fila['List_U'] = cols[5].number_input("P. Unit List", value=fila['List_U'], key=f"ul_{fid}_{i}")
            t_list = fila['Cant'] * fila['List_U']
            cols[6].write("Total List")
            cols[6].info(fmt(t_list))
            
            gan = t_cat - t_list
            cols[7].write("Ganancia")
            cols[7].success(fmt(gan))

        if st.button("➕ Añadir fila de producto", key=f"add_{fid}"):
            st.session_state.datos[key_f].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
            st.rerun()

        df_f = pd.DataFrame(st.session_state.datos[key_f])
        df_f['TC'] = df_f['Cant'] * df_f['Cat_U']
        df_f['TL'] = df_f['Cant'] * df_f['List_U']
        df_f['TG'] = df_f['TC'] - df_f['TL']

        st.divider()
        if st.button("🚀 GENERAR PDF PROFESIONAL", key=f"btn_pdf_{fid}"):
            pdf = FPDF()
            pdf.add_page()
            
            # --- DISEÑO ENCABEZADO ---
            if logo_rev:
                agregar_imagen_segura(pdf, logo_rev, 10, 10, 40)
            
            pdf.set_font("Arial", 'B', 22)
            pdf.set_text_color(33, 33, 33)
            pdf.cell(0, 15, txt=nombre_rev.upper(), ln=True, align='R')
            
            pdf.set_font("Arial", '', 11)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 7, f"CLIENTE: {nom_cli.upper()}", ln=True, align='R')
            # FECHA FORMATEADA DD-MM-YYYY
            pdf.cell(0, 7, f"FECHA DE PAGO: {fec_p.strftime('%d-%m-%Y')}", ln=True, align='R')
            pdf.ln(15)

            # --- TABLA DE PRODUCTOS ---
            # Color de fondo para encabezados (Gris Azulado)
            pdf.set_fill_color(44, 62, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 8)
            
            headers = [("Pág", 10), ("Nombre del Producto", 55), ("Cant", 10), ("U. Cat", 23), ("T. Cat", 23), ("U. List", 23), ("T. List", 23), ("Gan.", 23)]
            for h, w in headers:
                pdf.cell(w, 10, h, 1, 0, 'C', True)
            pdf.ln()

            # Filas de la tabla
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 8)
            for _, r in df_f.iterrows():
                pdf.cell(10, 8, str(r['Pag']), 1, 0, 'C')
                pdf.cell(55, 8, str(r['Prod']), 1)
                pdf.cell(10, 8, str(r['Cant']), 1, 0, 'C')
                pdf.cell(23, 8, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                pdf.cell(23, 8, f"${fmt(r['TC'])}", 1, 0, 'R')
                pdf.cell(23, 8, f"${fmt(r['List_U'])}", 1, 0, 'R')
                pdf.cell(23, 8, f"${fmt(r['TL'])}", 1, 0, 'R')
                pdf.set_font("Arial", 'B', 8) # Ganancia en negrita
                pdf.cell(23, 8, f"${fmt(r['TG'])}", 1, 1, 'R')
                pdf.set_font("Arial", '', 8)

            # --- TOTALES FINALES ---
            pdf.set_fill_color(245, 245, 245)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(75, 12, "TOTALES DE FACTURA", 1, 0, 'R', True)
            pdf.cell(23, 12, "", 1, 0, '', True) # Espacio Unit Cat
            pdf.cell(23, 12, f"${fmt(df_f['TC'].sum())}", 1, 0, 'C', True)
            pdf.cell(23, 12, "", 1, 0, '', True) # Espacio Unit List
            pdf.cell(23, 12, f"${fmt(df_f['TL'].sum())}", 1, 0, 'C', True)
            pdf.cell(23, 12, f"${fmt(df_f['TG'].sum())}", 1, 1, 'C', True)

            # --- SECCIÓN DE PAGO ---
            pdf.ln(12)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 10, "MÉTODO DE PAGO", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Línea decorativa
            pdf.ln(5)
            
            y_pago = pdf.get_y()
            # Logo de pago (Nequi/Banco)
            if logo_pago:
                agregar_imagen_segura(pdf, logo_pago, 10, y_pago, 18)
            
            pdf.set_xy(32, y_pago + 5)
            pdf.set_font("Arial", '', 14)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(100, 10, f"Pagar a: {num_pago}")
            
            # QR de pago a la derecha
            if qr_pago:
                agregar_imagen_segura(pdf, qr_pago, 160, y_pago - 10, 35)

            # --- DESCARGA ---
            res_pdf = pdf.output(dest='S').encode('latin-1')
            st.download_button(f"⬇️ Descargar PDF - {nom_cli}", res_pdf, file_name=f"Factura_{nom_cli}.pdf")




