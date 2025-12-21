import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import io
import re
from pypdf import PdfReader

st.set_page_config(page_title="Facturación Pro", layout="wide")

# Función para formatear moneda
def fmt(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except:
        return "0"

# --- LÓGICA DE IMPORTACIÓN ---
def extraer_datos_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        cliente = re.search(r"CLIENTE:\s*(.*)", text)
        return {
            "cliente": cliente.group(1).strip() if cliente else "Copia Editada",
            "productos": [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]
        }
    except:
        return None

# --- ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}

# --- SIDEBAR (CONFIGURACIÓN) ---
with st.sidebar:
    st.header("⚙️ Configuración Visual")
    logo_rev = st.file_uploader("Logo Revista (PNG/JPG)", type=["png", "jpg", "jpeg"])
    nombre_rev = st.text_input("Nombre Revista", "MI REVISTA")
    
    st.divider()
    st.subheader("💳 Datos de Pago")
    num_pago = st.text_input("Número de cuenta/Nequi")
    logo_metodo = st.file_uploader("Logo Medio de Pago", type=["png", "jpg", "jpeg"])
    qr_img = st.file_uploader("Imagen QR de Pago", type=["png", "jpg", "jpeg"])

    st.divider()
    archivo_in = st.file_uploader("🔄 Corregir PDF existente", type=["pdf"])
    if archivo_in and st.button("Cargar datos"):
        res = extraer_datos_pdf(archivo_in)
        if res:
            nid = len(st.session_state.facturas)
            st.session_state.facturas.append({"id": nid, "name": res["cliente"]})
            st.session_state.datos[f"f_{nid}"] = res["productos"]
            st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("📑 Generador de Facturas Profesional")

if st.button("➕ Crear otra factura al tiempo"):
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

        # TABLA DINÁMICA
        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([1, 3, 1, 2, 2, 2, 2, 2])
            fila['Pag'] = cols[0].text_input("Pág", value=fila['Pag'], key=f"pg_{fid}_{i}")
            fila['Prod'] = cols[1].text_input("Producto", value=fila['Prod'], key=f"pr_{fid}_{i}")
            fila['Cant'] = cols[2].number_input("Cant", value=fila['Cant'], min_value=1, key=f"ct_{fid}_{i}")
            fila['Cat_U'] = cols[3].number_input("Unit. Cat", value=fila['Cat_U'], key=f"uc_{fid}_{i}")
            
            t_cat = fila['Cant'] * fila['Cat_U']
            cols[4].write("Total Cat")
            cols[4].info(fmt(t_cat))
            
            fila['List_U'] = cols[5].number_input("Unit. List", value=fila['List_U'], key=f"ul_{fid}_{i}")
            t_list = fila['Cant'] * fila['List_U']
            cols[6].write("Total List")
            cols[6].info(fmt(t_list))
            
            gan = t_cat - t_list
            cols[7].write("Ganancia")
            cols[7].success(fmt(gan))

        if st.button("➕ Agregar fila", key=f"add_{fid}"):
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
            
            # --- ENCABEZADO Y LOGO ---
            if logo_rev:
                # Detectamos formato para evitar el AttributeError
                fmt_img = logo_rev.name.split('.')[-1].upper()
                pdf.image(io.BytesIO(logo_rev.getvalue()), 10, 10, 35, type=fmt_img)
            
            pdf.set_font("Arial", 'B', 20)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 15, txt=nombre_rev.upper(), ln=1, align='R')
            
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(100, 100, 100)
            # Fecha formateada DD-MM-YYYY
            fecha_fmt = fec_p.strftime("%d-%m-%Y")
            pdf.cell(0, 5, f"CLIENTE: {nom_cli.upper()}", ln=1, align='R')
            pdf.cell(0, 5, f"FECHA DE PAGO: {fecha_fmt}", ln=1, align='R')
            pdf.ln(10)

            # --- TABLA ---
            pdf.set_fill_color(50, 50, 50) # Gris oscuro para encabezado
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 8)
            
            headers = [("Pág", 10), ("Nombre del Producto", 55), ("Cant", 10), ("U. Cat", 23), ("T. Cat", 23), ("U. List", 23), ("T. List", 23), ("Gan.", 23)]
            for h, w in headers:
                pdf.cell(w, 10, h, 1, 0, 'C', True)
            pdf.ln()

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
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(23, 8, f"${fmt(r['TG'])}", 1, 1, 'R')
                pdf.set_font("Arial", '', 8)

            # --- TOTALES ---
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(75, 12, "TOTALES GENERALES", 1, 0, 'R', True)
            pdf.cell(23, 12, "", 1, 0, '', True) # Espacio U. Cat
            pdf.cell(23, 12, f"${fmt(df_f['TC'].sum())}", 1, 0, 'C', True)
            pdf.cell(23, 12, "", 1, 0, '', True) # Espacio U. List
            pdf.cell(23, 12, f"${fmt(df_f['TL'].sum())}", 1, 0, 'C', True)
            pdf.cell(23, 12, f"${fmt(df_f['TG'].sum())}", 1, 1, 'C', True)

            # --- PIE DE PÁGINA (PAGO) ---
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 10, "INFORMACIÓN DE PAGO", ln=1)
            
            y_final = pdf.get_y()
            if logo_metodo:
                fmt_p = logo_metodo.name.split('.')[-1].upper()
                pdf.image(io.BytesIO(logo_metodo.getvalue()), 10, y_final, 15, type=fmt_p)
            
            pdf.set_xy(30, y_final + 5)
            pdf.set_font("Arial", '', 12)
            pdf.cell(100, 5, f"Pagar a: {num_pago}")
            
            if qr_img:
                fmt_q = qr_img.name.split('.')[-1].upper()
                pdf.image(io.BytesIO(qr_img.getvalue()), 160, y_final - 10, 30, type=fmt_q)

            res_pdf = pdf.output(dest='S').encode('latin-1')
            st.download_button(f"⬇️ Descargar Factura {nom_cli}", res_pdf, file_name=f"Factura_{nom_cli}.pdf")



