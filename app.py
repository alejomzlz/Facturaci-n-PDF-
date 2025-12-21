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
        cliente = cliente_match.group(1).strip() if cliente_match else "Cliente Recuperado"
        
        # Patrón mejorado para capturar filas con números
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
        
        return {"cliente": cliente, "productos": productos if productos else None}
    except:
        return None

# --- ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}

# --- SIDEBAR RETRAÍBLE ---
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
    st.subheader("🔄 Re-editar PDF")
    archivo_pdf = st.file_uploader("Cargar factura previa", type=["pdf"])
    if archivo_pdf and st.button("Importar Datos"):
        res = importar_datos_pdf(archivo_pdf)
        if res and res["productos"]:
            nid = len(st.session_state.facturas)
            st.session_state.facturas.append({"id": nid, "name": res["cliente"]})
            st.session_state.datos[f"f_{nid}"] = res["productos"]
            st.success("¡Datos cargados!")

# --- CUERPO PRINCIPAL ---
st.title("📑 Generador de Facturas")

if st.button("➕ Nueva Pestaña de Factura"):
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
            st.session_state.facturas[idx]["name"] = nom_cli if nom_cli else "Nueva Factura"
        with c2:
            fec_p = st.date_input("Fecha de pago", date.today(), key=f"d_{fid}")

        indices_a_borrar = []
        for i, fila in enumerate(st.session_state.datos[key_f]):
            cols = st.columns([0.6, 3, 0.8, 1.5, 1.5, 1.5, 1.5, 1.5, 0.5])
            fila['Pag'] = cols[0].text_input("Pág", value=fila['Pag'], key=f"pg_{fid}_{i}")
            fila['Prod'] = cols[1].text_area("Producto", value=fila['Prod'], key=f"pr_{fid}_{i}", height=68)
            fila['Cant'] = cols[2].number_input("Cant", value=int(fila['Cant']), min_value=1, key=f"ct_{fid}_{i}")
            fila['Cat_U'] = cols[3].number_input("Unit Cat", value=int(fila['Cat_U']), key=f"uc_{fid}_{i}")
            
            tc = fila['Cant'] * fila['Cat_U']
            cols[4].metric("Total Cat", f"${fmt(tc)}")
            
            fila['List_U'] = cols[5].number_input("Unit List", value=int(fila['List_U']), key=f"ul_{fid}_{i}")
            tl = fila['Cant'] * fila['List_U']
            cols[6].metric("Total List", f"${fmt(tl)}")
            
            cols[7].metric("Ganancia", f"${fmt(tc - tl)}")
            
            if cols[8].button("🗑️", key=f"del_{fid}_{i}"):
                indices_a_borrar.append(i)

        if indices_a_borrar:
            for index in sorted(indices_a_borrar, reverse=True):
                st.session_state.datos[key_f].pop(index)
            st.rerun()

        if st.button("➕ Agregar fila", key=f"add_{fid}"):
            st.session_state.datos[key_f].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
            st.rerun()

        # Solo procesar filas con nombre para el PDF
        df_final = pd.DataFrame(st.session_state.datos[key_f])
        df_final = df_final[df_final['Prod'].str.strip() != ""].copy()

        if not df_final.empty:
            st.divider()
            if st.button("🚀 GENERAR PDF PROFESIONAL", key=f"btn_pdf_{fid}"):
                pdf = FPDF()
                pdf.add_page()
                
                # Encabezado
                if logo_rev: agregar_imagen_segura(pdf, logo_rev, 10, 10, 35)
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 15, txt=nombre_rev.upper(), ln=True, align='R')
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 5, f"CLIENTE: {nom_cli.upper()}", ln=True, align='R')
                pdf.cell(0, 5, f"FECHA DE PAGO: {fec_p.strftime('%d-%m-%Y')}", ln=True, align='R')
                pdf.ln(10)

                # Tabla
                pdf.set_fill_color(40, 40, 40)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", 'B', 8)
                headers = [("Pág", 10), ("Producto", 55), ("Cant", 10), ("U. Cat", 23), ("T. Cat", 23), ("U. List", 23), ("T. List", 23), ("Gan.", 23)]
                for h, w in headers:
                    pdf.cell(w, 10, h, 1, 0, 'C', True)
                pdf.ln()

                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 8)
                
                t_tc, t_tl, t_tg = 0, 0, 0
                for _, r in df_final.iterrows():
                    # Ajuste de alto por texto largo
                    lineas = (pdf.get_string_width(str(r['Prod'])) // 53) + 1
                    alto = max(8, lineas * 5)
                    
                    x, y = pdf.get_x(), pdf.get_y()
                    pdf.cell(10, alto, str(r['Pag']), 1, 0, 'C')
                    pdf.multi_cell(55, 5 if lineas > 1 else alto, str(r['Prod']), 1, 'L')
                    pdf.set_xy(x + 65, y)
                    
                    v_tc = r['Cant'] * r['Cat_U']
                    v_tl = r['Cant'] * r['List_U']
                    v_tg = v_tc - v_tl
                    t_tc += v_tc; t_tl += v_tl; t_tg += v_tg
                    
                    pdf.cell(10, alto, str(r['Cant']), 1, 0, 'C')
                    pdf.cell(23, alto, f"${fmt(r['Cat_U'])}", 1, 0, 'R')
                    pdf.set_fill_color(225, 245, 254)
                    pdf.cell(23, alto, f"${fmt(v_tc)}", 1, 0, 'R', True)
                    pdf.cell(23, alto, f"${fmt(r['List_U'])}", 1, 0, 'R')
                    pdf.set_fill_color(255, 243, 224)
                    pdf.cell(23, alto, f"${fmt(v_tl)}", 1, 0, 'R', True)
                    pdf.set_fill_color(232, 245, 233)
                    pdf.set_font("Arial", 'B', 8)
                    pdf.cell(23, alto, f"${fmt(v_tg)}", 1, 1, 'R', True)
                    pdf.set_font("Arial", '', 8)

                # Totales
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(75, 12, "TOTALES FINALES", 1, 0, 'R', True)
                pdf.cell(33, 12, "", 1, 0, '', True)
                pdf.cell(23, 12, f"${fmt(t_tc)}", 1, 0, 'C', True)
                pdf.cell(23, 12, "", 1, 0, '', True)
                pdf.cell(23, 12, f"${fmt(t_tl)}", 1, 0, 'C', True)
                pdf.cell(23, 12, f"${fmt(t_tg)}", 1, 1, 'C', True)

                # Pago
                pdf.ln(10)
                y_p = pdf.get_y()
                if logo_pago: agregar_imagen_segura(pdf, logo_pago, 10, y_p, 15)
                pdf.set_xy(30, y_p + 5)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 5, f"Pagar a: {num_pago}")
                if qr_pago: agregar_imagen_segura(pdf, qr_pago, 160, y_p - 10, 30)

                output = pdf.output(dest='S').encode('latin-1')
                st.download_button("⬇️ Descargar PDF", output, file_name=f"Factura_{nom_cli}.pdf")
