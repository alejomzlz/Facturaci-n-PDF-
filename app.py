import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import io
import re
from pypdf import PdfReader

st.set_page_config(page_title="Facturación Pro", layout="wide")

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
        fecha = re.search(r"FECHA:\s*(\d{4}-\d{2}-\d{2})", text)
        
        return {
            "cliente": cliente.group(1).strip() if cliente else "Copia Editada",
            "fecha": date.fromisoformat(fecha.group(1)) if fecha else date.today(),
            "productos": [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]
        }
    except:
        return None

# --- ESTADO DE SESIÓN ---
if 'facturas' not in st.session_state:
    st.session_state.facturas = [{"id": 0, "name": "Nueva Factura"}]
if 'datos' not in st.session_state:
    st.session_state.datos = {}

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    logo_rev = st.file_uploader("Logo Revista (Opcional)", type=["png", "jpg", "jpeg"])
    nombre_rev = st.text_input("Nombre Revista", "Mi Revista")
    
    st.divider()
    st.subheader("💳 Pago")
    logo_metodo = st.file_uploader("Logo Pago (Opcional)", type=["png", "jpg", "jpeg"])
    num_pago = st.text_input("Número de cuenta")
    qr_img = st.file_uploader("QR (Opcional)", type=["png", "jpg", "jpeg"])

    st.divider()
    archivo_in = st.file_uploader("🔄 Editar PDF anterior", type=["pdf"])
    if archivo_in and st.button("Cargar para editar"):
        res = extraer_datos_pdf(archivo_in)
        if res:
            new_id = len(st.session_state.facturas)
            st.session_state.facturas.append({"id": new_id, "name": res["cliente"]})
            st.session_state.datos[f"f_{new_id}"] = res["productos"]
            st.rerun()

# --- MAIN ---
st.title("📑 Sistema de Facturación")

if st.button("➕ Nueva Factura"):
    nid = len(st.session_state.facturas)
    st.session_state.facturas.append({"id": nid, "name": f"Factura {nid+1}"})
    st.rerun()

tabs = st.tabs([f["name"] for f in st.session_state.facturas])

for idx, tab in enumerate(tabs):
    with tab:
        fid = st.session_state.facturas[idx]["id"]
        c1, c2 = st.columns(2)
        
        with c1:
            nom_cli = st.text_input("Cliente", key=f"n_{fid}")
            if nom_cli: st.session_state.facturas[idx]["name"] = nom_cli
        with c2:
            fec_p = st.date_input("Fecha", date.today(), key=f"d_{fid}")

        key_f = f"f_{fid}"
        if key_f not in st.session_state.datos:
            st.session_state.datos[key_f] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0}]

        # TABLA DE EDICIÓN
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

        if st.button("➕ Añadir Fila", key=f"add_{fid}"):
            st.session_state.datos[key_f].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_U": 0, "List_U": 0})
            st.rerun()

        df_f = pd.DataFrame(st.session_state.datos[key_f])
        df_f['TC'] = df_f['Cant'] * df_f['Cat_U']
        df_f['TL'] = df_f['Cant'] * df_f['List_U']
        df_f['TG'] = df_f['TC'] - df_f['TL']

        st.divider()
        st.subheader(f"Total Factura: $ {fmt(df_f['TC'].sum())}")

        if st.button("🚀 Exportar a PDF", key=f"btn_pdf_{fid}"):
            pdf = FPDF()
            pdf.add_page()
            
            # Manejo seguro de imágenes opcionales
            if logo_rev:
                try:
                    pdf.image(io.BytesIO(logo_rev.getvalue()), 10, 8, 30)
                except: pass
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt=nombre_rev.upper(), ln=1, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, f"CLIENTE: {nom_cli} | FECHA: {fec_p}", ln=1, align='C')
            pdf.ln(5)

            # Encabezados
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", 'B', 7)
            # Reorganización: Pag, Producto, Cant, Unit Cat, Total Cat, Unit List, Total List, Ganancia
            headers = [("Pág", 8), ("Producto", 50), ("Cant", 10), ("U. Cat", 25), ("T. Cat", 25), ("U. List", 23), ("T. List", 23), ("Gan.", 22)]
            for h, w in headers:
                pdf.cell(w, 8, h, 1, 0, 'C', True)
            pdf.ln()

            pdf.set_font("Arial", size=7)
            for _, r in df_f.iterrows():
                pdf.cell(8, 8, str(r['Pag']), 1)
                pdf.cell(50, 8, str(r['Prod']), 1)
                pdf.cell(10, 8, str(r['Cant']), 1, 0, 'C') # Corrección de TypeError aquí
                pdf.cell(25, 8, f"${fmt(r['Cat_U'])}", 1)
                pdf.cell(25, 8, f"${fmt(r['TC'])}", 1)
                pdf.cell(23, 8, f"${fmt(r['List_U'])}", 1)
                pdf.cell(23, 8, f"${fmt(r['TL'])}", 1)
                pdf.cell(22, 8, f"${fmt(r['TG'])}", 1, 1)

            # Totales
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(68, 10, "TOTALES", 1, 0, 'R', True)
            pdf.cell(35, 10, "", 1, 0, '', True) # Espacio cant/unit
            pdf.cell(25, 10, f"${fmt(df_f['TC'].sum())}", 1, 0, 'C', True)
            pdf.cell(23, 10, "", 1, 0, '', True)
            pdf.cell(23, 10, f"${fmt(df_f['TL'].sum())}", 1, 0, 'C', True)
            pdf.cell(22, 10, f"${fmt(df_f['TG'].sum())}", 1, 1, 'C', True)

            # Pie de página opcional
            pdf.ln(5)
            y_now = pdf.get_y()
            if logo_metodo:
                try: pdf.image(io.BytesIO(logo_metodo.getvalue()), 10, y_now, 12)
                except: pass
            pdf.set_x(25)
            pdf.cell(100, 10, f"Pagar a: {num_pago}")
            if qr_img:
                try: pdf.image(io.BytesIO(qr_img.getvalue()), 160, y_now - 5, 25)
                except: pass

            res_pdf = pdf.output(dest='S').encode('latin-1')
            st.download_button("⬇️ Descargar PDF", res_pdf, file_name=f"Factura_{nom_cli}.pdf")


