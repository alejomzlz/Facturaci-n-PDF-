import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date
import io
import re
from pypdf import PdfReader

# Configuración de página
st.set_page_config(page_title="Sistema Pro Facturación", layout="wide")

# Función para formatear unidades de mil sin decimales
def fmt(valor):
    return f"{int(valor):,}".replace(",", ".")

# --- FUNCIONES DE EXTRACCIÓN (REVERSE ENGINEERING) ---
def extraer_datos_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    # Intentar extraer Cliente y Fecha mediante Regex
    cliente_match = re.search(r"CLIENTE:\s*(.*)", text)
    fecha_match = re.search(r"FECHA:\s*(\d{4}-\d{2}-\d{2})", text)
    pago_match = re.search(r"Pagar a:\s*(.*)", text)
    
    datos = {
        "cliente": cliente_match.group(1).strip() if cliente_match else "Cliente Recuperado",
        "fecha": date.fromisoformat(fecha_match.group(1)) if fecha_match else date.today(),
        "pago": pago_match.group(1).strip() if pago_match else "",
        "productos": []
    }
    
    # Intento simple de extraer filas (esto depende de la estructura del texto extraído)
    # Por simplicidad, si falla la extracción de filas, devolvemos una vacía para que el usuario la llene.
    return datos

# --- ESTADO DE LA SESIÓN ---
if 'lista_facturas' not in st.session_state:
    st.session_state.lista_facturas = [{"id": 0, "cliente": "Nueva Factura"}]
if 'datos_facturas' not in st.session_state:
    st.session_state.datos_facturas = {}

# --- INTERFAZ LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración General")
    logo_revista = st.file_uploader("Logo de la Revista", type=["png", "jpg", "jpeg"])
    nombre_revista = st.text_input("Nombre de la Revista", "Mi Revista")
    
    st.divider()
    st.subheader("💳 Método de Pago")
    logo_pago = st.file_uploader("Logo Método de Pago", type=["png", "jpg", "jpeg"])
    num_pago = st.text_input("Número o Cuenta de pago", key="global_pago")
    qr_pago = st.file_uploader("Imagen QR de pago", type=["png", "jpg", "jpeg"])

    st.divider()
    st.subheader("🔄 Importar Factura")
    archivo_importar = st.file_uploader("Subir PDF para editar", type=["pdf"])
    if archivo_importar:
        if st.button("Cargar Datos del PDF"):
            datos_recuperados = extraer_datos_pdf(archivo_importar)
            nueva_id = len(st.session_state.lista_facturas)
            st.session_state.lista_facturas.append({"id": nueva_id, "cliente": datos_recuperados["cliente"]})
            # Inicializar productos con una fila vacía para editar
            st.session_state.datos_facturas[f"prod_data_{nueva_id}"] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat": 0, "List": 0}]
            st.success("Factura cargada. Ve a la nueva pestaña.")

# --- CUERPO PRINCIPAL ---
st.title("📑 Generador de Facturas Múltiple")

if st.button("➕ Añadir Nueva Factura"):
    nueva_id = len(st.session_state.lista_facturas)
    st.session_state.lista_facturas.append({"id": nueva_id, "cliente": f"Factura {nueva_id + 1}"})
    st.rerun()

titulos_tabs = [f["cliente"] for f in st.session_state.lista_facturas]
tabs = st.tabs(titulos_tabs)

for index, tab in enumerate(tabs):
    with tab:
        factura_id = st.session_state.lista_facturas[index]["id"]
        
        col_a, col_b = st.columns(2)
        with col_a:
            nombre_cli = st.text_input("Nombre del Cliente", key=f"ncli_{factura_id}")
            if nombre_cli:
                st.session_state.lista_facturas[index]["cliente"] = nombre_cli
        with col_b:
            fecha_pago = st.date_input("Fecha de Pago", date.today(), key=f"fec_{factura_id}")

        key_p = f"prod_data_{factura_id}"
        if key_p not in st.session_state.datos_facturas:
            st.session_state.datos_facturas[key_p] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat": 0, "List": 0}]

        for i, fila in enumerate(st.session_state.datos_facturas[key_p]):
            c1, c2, c3, c4, c5, c6 = st.columns([1, 3, 1, 2, 2, 2])
            fila['Pag'] = c1.text_input("Pág", value=fila['Pag'], key=f"p_{factura_id}_{i}")
            fila['Prod'] = c2.text_input("Producto", value=fila['Prod'], key=f"pr_{factura_id}_{i}")
            fila['Cant'] = c3.number_input("Cant", value=fila['Cant'], min_value=1, key=f"c_{factura_id}_{i}")
            fila['Cat'] = c4.number_input("Precio Cat. Unit", value=fila['Cat'], key=f"ct_{factura_id}_{i}")
            fila['List'] = c5.number_input("Precio List. Unit", value=fila['List'], key=f"ls_{factura_id}_{i}")
            
            tot_cat = fila['Cant'] * fila['Cat']
            tot_list = fila['Cant'] * fila['List']
            ganancia = tot_cat - tot_list
            c6.write(f"**Ganancia**")
            c6.info(f"$ {fmt(ganancia)}")

        col_btns = st.columns(5)
        if col_btns[0].button("➕ Producto", key=f"add_{factura_id}"):
            st.session_state.datos_facturas[key_p].append({"Pag": "", "Prod": "", "Cant": 1, "Cat": 0, "List": 0})
            st.rerun()
        
        if col_btns[1].button("🗑️ Quitar Último", key=f"del_{factura_id}"):
            if len(st.session_state.datos_facturas[key_p]) > 1:
                st.session_state.datos_facturas[key_p].pop()
                st.rerun()

        df = pd.DataFrame(st.session_state.datos_facturas[key_p])
        df['TotalCat'] = df['Cant'] * df['Cat']
        df['TotalList'] = df['Cant'] * df['List']
        df['Gan'] = df['TotalCat'] - df['TotalList']
        t_c, t_l, t_g = df['TotalCat'].sum(), df['TotalList'].sum(), df['Gan'].sum()

        st.divider()
        st.subheader(f"Total a Cobrar: $ {fmt(t_c)}")
        
        if st.button("🚀 Exportar a PDF", key=f"pdf_{factura_id}"):
            if not nombre_cli:
                st.error("Escribe el nombre del cliente.")
            else:
                pdf = FPDF()
                pdf.add_page()
                if logo_revista:
                    pdf.image(io.BytesIO(logo_revista.getvalue()), 10, 8, 30)
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt=nombre_revista.upper(), ln=True, align='C')
                pdf.ln(5)
                pdf.set_font("Arial", size=11)
                pdf.cell(100, 8, f"CLIENTE: {nombre_cli}")
                pdf.cell(100, 8, f"FECHA: {fecha_pago}", ln=True)
                pdf.ln(5)
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Arial", 'B', 9)
                headers = [("Pág", 12), ("Producto", 65), ("Cant", 13), ("T. Catálogo", 35), ("T. Lista", 35), ("Ganancia", 30)]
                for h, w in headers: pdf.cell(w, 8, h, 1, 0, 'C', True)
                pdf.ln()
                pdf.set_font("Arial", size=9)
                for _, r in df.iterrows():
                    pdf.cell(12, 8, str(r['Pag']), 1)
                    pdf.cell(65, 8, str(r['Prod']), 1)
                    pdf.cell(13, 8, str(r['Cant']), 1, 0, 'C')
                    pdf.cell(35, 8, f"${fmt(r['TotalCat'])}", 1)
                    pdf.cell(35, 8, f"${fmt(r['TotalList'])}", 1)
                    pdf.cell(30, 8, f"${fmt(r['Gan'])}", 1, 1)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(90, 10, "TOTALES FINALES", 1, 0, 'R', True)
                pdf.cell(35, 10, f"${fmt(t_c)}", 1, 0, 'C', True)
                pdf.cell(35, 10, f"${fmt(t_l)}", 1, 0, 'C', True)
                pdf.cell(30, 10, f"${fmt(t_g)}", 1, 1, 'C', True)
                pdf.ln(10)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(200, 10, "INFORMACIÓN DE PAGO", ln=True)
                y_pos = pdf.get_y()
                if logo_pago:
                    pdf.image(io.BytesIO(logo_pago.getvalue()), 10, y_pos, 15)
                    pdf.set_x(30)
                pdf.cell(100, 10, f"Pagar a: {num_pago}")
                if qr_pago:
                    pdf.image(io.BytesIO(qr_pago.getvalue()), 150, y_pos - 5, 30)
                output = pdf.output(dest='S').encode('latin-1')
                st.download_button(f"⬇️ Descargar PDF {nombre_cli}", data=output, file_name=f"Factura_{nombre_cli}.pdf")
