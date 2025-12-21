import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import io
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
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            pdf.image(tmp_path, x=x, y=y, w=w)
            os.unlink(tmp_path)
        except Exception:
            pass

# --- FUNCIÓN DE IMPORTACIÓN MEJORADA ---
def importar_datos_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        cliente_match = re.search(r"CLIENTE:\s*(.*)", text)
        cliente = cliente_match.group(1).strip() if cliente_match else "Cliente Recuperado"
        
        # Patron para capturar: Pág, Nombre, Cant, Precio Cat, Total Cat, Precio List...
        patron = r"(\d+)\s+(.*?)\s+(\d+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)"
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

# --- SIDEBAR RETRAÍBLE ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    with st.expander("🖼️ Cargar Logos y Marca", expanded=False):
        logo_rev = st.file_uploader("Logo Revista", type=["png", "jpg", "jpeg"])
        nombre_rev = st.text_input("Nombre de la Revista", "REVISTA PRO")
    
    with st.expander("💳 Configurar Pago", expanded=False):
        num_pago = st.text_input("Número de cuenta / Nequi")
        logo_pago = st.file_uploader("Logo Pago", type=["png", "jpg", "jpeg"])
        qr_pago = st.file_uploader("QR Pago", type=["png", "jpg", "jpeg"])

    st.divider()
    st.subheader("🔄 Re-editar Factura")
    archivo_pdf = st.file_uploader("Subir factura PDF para editar", type=["pdf"])
    if archivo_pdf and st.button("Cargar Datos Completos"):
        res = importar_datos_pdf(archivo_pdf)
        if res:
            nid = len(st.session_state.facturas)
            st.session_state.facturas.append({"id": nid, "name": res["cliente"]})
            st.session_state.datos[f"f_{nid}"] = res["productos"]
            st.rerun()

# --- CUERPO PRINCIPAL ---
st.title("📑 Sistema de Facturación")

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
            nom_cli = st.text_input("Cliente", key=f"n_{fid}", value=st.session_state.facturas[idx]["name"] if st.session_state.facturas[idx]["name"] != "Nueva Factura" else "")
            if nom_cli: st.session_state.facturas[idx]["name"] = nom_cli
        with c2:
            fec_p = st.date_input("Fecha de pago", date.today(), key=f"d_{fid}")

        indices_a_borrar = []
        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([0.5, 3, 0.8, 1.5, 1.5, 1.5, 1.5, 1.5, 0.5])
            fila['Pag'] = cols[0].text_input("Pág", value=fila['Pag'], key=f"pg_{fid}_{i}")
            fila['Prod'] = cols[1].text_area("Producto", value=fila['Prod'], key=f"pr_{fid}_{i}", height=68)
            fila['Cant'] = cols[2].number_input("Cant", value=fila['Cant'], min_value=1, key=f"ct_{fid}_{i}")
            fila['Cat_U'] = cols[3].number_input("Unit Cat", value=int(fila['Cat_U']), key=f"uc_{fid}_{i}")
            
            t_cat = fila['Cant'] * fila['Cat_U']
            cols[4].metric("Total Cat", f"${fmt(t_cat)}")
            
            fila['List_U'] = cols[5].number_input("Unit List", value=int(fila['List_U']), key=f"ul_{fid}_{i}")
            t_list = fila['Cant'] * fila['List_U']
            cols[6].metric("Total List", f"${fmt(t_list)}")
            
            gan = t_cat - t_list
            cols[7].metric("Ganancia", f"${fmt(gan)}")
            
            if cols[8].button("🗑️", key=f"del_{fid}_{i}"):
                indices_a_borrar.append(i)

        if indices_a_borrar:
            for index in sorted(indices_a_borrar, reverse=True):
                st.session_state.datos[key_f].pop(index)
            st.rerun()

        if st.button("➕ Agregar fila", key=f"add_row_{fid}"):
            st.session_state.datos[key_f].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
            st.rerun()

        df_v = pd.DataFrame(st.session_state.datos[key_f])
        df_v = df_v[df_v['Prod'].str.strip() != ""].copy()

        if not df_v.empty:
            df_v['TC'] = df_v['Cant'] * df_v['Cat_U']
            df_v['TL'] = df_v['Cant'] * df_v['List_U']
            df_v['TG'] = df_v['TC'] - df_v['TL']
            
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

                # Encabezados PDF
                pdf.set_fill_color(40, 40, 40)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", 'B', 8)
                w_col = [10, 55, 10, 23, 23, 23, 23, 23]
                headers = ["Pág", "Producto", "Cant", "U. Cat", "T. Cat", "U. List", "T. List", "Gan."]
                for i in range(len(headers)): pdf.cell(w_col[i], 10, headers[i], 1, 0, 'C', True)
                pdf.ln()

                # Filas con Colores (SOLO EN EL PDF)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 8)
                for _, r in df_v.iterrows():
                    # Cálculo de alto para multi_cell
                    texto_prod = str(r['Prod'])
                    ancho_prod = 55
                    lineas = (pdf.get_string_width(texto_prod) // ancho_prod) + 1
                    alto_celda = max(8, lineas * 5)
                    
                    curr_x, curr_y = pdf.get_x(), pdf.get_y()
                    
                    pdf.cell(10, alto_celda, str(r['Pag']), 1, 0, 'C')
                    pdf.multi_cell(ancho_prod, 5 if lineas > 1 else alto_celda, texto_prod, 1, 'L')
                    
                    pdf.set_xy(curr_x + 65, curr_y)
                    pdf.cell(10, alto_celda, str(r['Cant']), 1, 0, 'C')
                    pdf.cell(23, alto_celda, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                    
                    pdf.set_fill_color(225, 245, 254) # Azul
                    pdf.cell(23, alto_celda, f"${fmt(r['TC'])}", 1, 0, 'R', True)
                    
                    pdf.cell(23, alto_celda, f"${fmt(r['List_U'])}", 1, 0, 'R')
                    
                    pdf.set_fill_color(255, 243, 224) # Naranja
                    pdf.cell(23, alto_celda, f"${fmt(r['TL'])}", 1, 0, 'R', True)
                    
                    pdf.set_fill_color(232, 245, 233) # Verde
                    pdf.set_font("Arial", 'B', 8)
                    pdf.cell(23, alto_celda, f"${fmt(r['TG'])}", 1, 1, 'R', True)
                    pdf.set_font("Arial", '', 8)

                # Totales Finales
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(75, 12, "TOTALES FINALES", 1, 0, 'R', True)
                pdf.cell(33, 12, "", 1, 0, '', True)
                pdf.cell(23, 12, f
