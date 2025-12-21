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
    try:
        return f"{int(valor):,}".replace(",", ".")
    except:
        return "0"

# --- FUNCIÓN PARA RECUPERAR DATOS DEL PDF ---
def extraer_datos_completos_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    # Extraer Cliente, Fecha y Pago
    cliente_match = re.search(r"CLIENTE:\s*(.*)", text)
    fecha_match = re.search(r"FECHA:\s*(\d{4}-\d{2}-\d{2})", text)
    pago_match = re.search(r"Pagar a:\s*(.*)", text)
    
    # Intentar recuperar filas de la tabla (Basado en el formato que generamos)
    # Buscamos patrones de líneas que empiecen por un número (Página)
    lineas = text.split('\n')
    productos_recuperados = []
    
    for linea in lineas:
        # Regex para detectar: Pag, Producto (texto), Cant, y luego valores monetarios
        parts = linea.split()
        if len(parts) >= 5 and parts[0].isdigit():
            try:
                # Intento de reconstrucción simple
                productos_recuperados.append({
                    "Pag": parts[0],
                    "Prod": " ".join(parts[1:-5]),
                    "Cant": int(parts[-5]),
                    "Cat_Unit": 0, # Los unitarios se recalculan manual al editar
                    "List_Unit": 0
                })
            except:
                continue

    return {
        "cliente": cliente_match.group(1).strip() if cliente_match else "Cliente Editado",
        "fecha": date.fromisoformat(fecha_match.group(1)) if fecha_match else date.today(),
        "pago": pago_match.group(1).strip() if pago_match else "",
        "productos": productos_recuperados if productos_recuperados else [{"Pag": "", "Prod": "", "Cant": 1, "Cat_Unit": 0, "List_Unit": 0}]
    }

# --- ESTADO DE LA SESIÓN ---
if 'lista_facturas' not in st.session_state:
    st.session_state.lista_facturas = [{"id": 0, "cliente": "Nueva Factura"}]
if 'datos_facturas' not in st.session_state:
    st.session_state.datos_facturas = {}

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    logo_revista = st.file_uploader("Logo Revista", type=["png", "jpg", "jpeg"])
    nombre_revista = st.text_input("Nombre Revista", "Mi Revista")
    
    st.divider()
    st.subheader("💳 Pago")
    logo_pago = st.file_uploader("Logo Pago", type=["png", "jpg", "jpeg"])
    num_pago = st.text_input("Número de cuenta")
    qr_pago = st.file_uploader("QR de pago", type=["png", "jpg", "jpeg"])

    st.divider()
    st.subheader("🔄 Editar PDF Existente")
    archivo_importar = st.file_uploader("Sube factura para editar", type=["pdf"])
    if archivo_importar:
        if st.button("Cargar datos para corregir"):
            d = extraer_datos_completos_pdf(archivo_importar)
            n_id = len(st.session_state.lista_facturas)
            st.session_state.lista_facturas.append({"id": n_id, "cliente": d["cliente"]})
            st.session_state.datos_facturas[f"p_{n_id}"] = d["productos"]
            st.success("Cargado en nueva pestaña")

# --- CUERPO ---
st.title("📑 Facturación Automática")

if st.button("➕ Crear Nueva Factura"):
    n_id = len(st.session_state.lista_facturas)
    st.session_state.lista_facturas.append({"id": n_id, "cliente": f"Factura {n_id+1}"})
    st.rerun()

tabs = st.tabs([f["cliente"] for f in st.session_state.lista_facturas])

for idx, tab in enumerate(tabs):
    with tab:
        f_id = st.session_state.lista_facturas[idx]["id"]
        col_1, col_2 = st.columns(2)
        
        with col_1:
            nom = st.text_input("Cliente", key=f"cli_{f_id}")
            if nom: st.session_state.lista_facturas[idx]["cliente"] = nom
        with col_2:
            fec = st.date_input("Fecha Pago", date.today(), key=f"dt_{f_id}")

        k_data = f"p_{f_id}"
        if k_data not in st.session_state.datos_facturas:
            st.session_state.datos_facturas[k_data] = [{"Pag": "", "Prod": "", "Cant": 1, "Cat_Unit": 0, "List_Unit": 0}]

        # TABLA DE PRODUCTOS
        for i, fila in enumerate(st.session_state.datos_facturas[k_data]):
            c = st.columns([1, 3, 1, 2, 2, 2, 2, 2])
            fila['Pag'] = c[0].text_input("Pág", value=fila['Pag'], key=f"pg_{f_id}_{i}")
            fila['Prod'] = c[1].text_input("Producto", value=fila['Prod'], key=f"pr_{f_id}_{i}")
            fila['Cant'] = c[2].number_input("Cant", value=fila['Cant'], min_value=1, key=f"ct_{f_id}_{i}")
            fila['Cat_Unit'] = c[3].number_input("P. Unit Cat", value=fila['Cat_Unit'], key=f"puc_{f_id}_{i}")
            
            # Cálculos en tiempo real para visualización
            t_cat_fila = fila['Cant'] * fila['Cat_Unit']
            c[4].write("**Total Cat**")
            c[4].info(fmt(t_cat_fila))
            
            fila['List_Unit'] = c[5].number_input("P. Unit List", value=fila['List_Unit'], key=f"pul_{f_id}_{i}")
            
            t_list_fila = fila['Cant'] * fila['List_Unit']
            c[6].write("**Total List**")
            c[6].info(fmt(t_list_fila))
            
            gan_fila = t_cat_fila - t_list_fila
            c[7].write("**Ganancia**")
            c[7].success(fmt(gan_fila))

        if st.button("➕ Añadir Producto", key=f"btn_a_{f_id}"):
            st.session_state.datos_facturas[k_data].append({"Pag": "", "Prod": "", "Cant": 1, "Cat_Unit": 0, "List_Unit": 0})
            st.rerun()

        # Resumen final
        df = pd.DataFrame(st.session_state.datos_facturas[k_data])
        df['TCat'] = df['Cant'] * df['Cat_Unit']
        df['TList'] = df['Cant'] * df['List_Unit']
        df['TGan'] = df['TCat'] - df['TList']
        
        st.divider()
        st.subheader(f"Total Factura: $ {fmt(df['TCat'].sum())}")

        # GENERAR PDF
        if st.button("🚀 Exportar a PDF", key=f"pdf_btn_{f_id}"):
            pdf = FPDF()
            pdf.add_page()
            
            # Arreglo del error de imagen: se usa BytesIO y se especifica formato
            if logo_revista:
                ext = logo_revista.name.split('.')[-1].upper()
                pdf.image(io.BytesIO(logo_revista.getvalue()), 10, 8, 30, type=ext)
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt=nombre_revista.upper(), ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, f"CLIENTE: {nom} | FECHA: {fec}", ln=True, align='C')
            pdf.ln(5)

            # Encabezados (ajustados a las nuevas columnas)
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", 'B', 7)
            pdf.cell(8, 8, "Pág", 1, 0, 'C', True)
            pdf.cell(50, 8, "Producto", 1, 0, 'C', True)
            pdf.cell(10, 8, "Cant", 1, 0, 'C', True)
            pdf.cell(28, 8, "U. Catál.", 1, 0, 'C', True)
            pdf.cell(28, 8, "T. Catál.", 1, 0, 'C', True)
            pdf.cell(23, 8, "U. Lista", 1, 0, 'C', True)
            pdf.cell(23, 8, "T. Lista", 1, 0, 'C', True)
            pdf.cell(22, 8, "Ganancia", 1, 1, 'C', True)

            pdf.set_font("Arial", size=7)
            for _, r in df.iterrows():
                pdf.cell(8, 8, str(r['Pag']), 1)
                pdf.cell(50, 8, str(r['Prod']), 1)
                pdf.cell(10, 8, str(r['Cant']), 1, 'C')
                pdf.cell(28, 8, f"${fmt(r['Cat_Unit'])}", 1)
                pdf.cell(28, 8, f"${fmt(r['TCat'])}", 1)
                pdf.cell(23, 8, f"${fmt(r['List_Unit'])}", 1)
                pdf.cell(23, 8, f"${fmt(r['TList'])}", 1)
                pdf.cell(22, 8, f"${fmt(r['TGan'])}", 1, 1)

            # Fila de Totales
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(68, 10, "TOTALES", 1, 0, 'R', True)
            pdf.cell(10, 10, "", 1, 0, '', True) # Espacio cant
            pdf.cell(28, 10, "", 1, 0, '', True) # Espacio unit
            pdf.cell(28, 10, f"${fmt(df['TCat'].sum())}", 1, 0, 'C', True)
            pdf.cell(23, 10, "", 1, 0, '', True) # Espacio unit list
            pdf.cell(23, 10, f"${fmt(df['TList'].sum())}", 1, 0, 'C', True)
            pdf.cell(22, 10, f"${fmt(df['TGan'].sum())}", 1, 1, 'C', True)

            # Pie de página
            pdf.ln(5)
            y_p = pdf.get_y()
            if logo_pago:
                ext_p = logo_pago.name.split('.')[-1].upper()
                pdf.image(io.BytesIO(logo_pago.getvalue()), 10, y_p, 12, type=ext_p)
            pdf.set_x(25)
            pdf.cell(100, 10, f"Pagar a: {num_pago}")
            if qr_pago:
                ext_q = qr_pago.name.split('.')[-1].upper()
                pdf.image(io.BytesIO(qr_pago.getvalue()), 160, y_p - 5, 25, type=ext_q)

            out = pdf.output(dest='S').encode('latin-1')
            st.download_button("⬇️ Bajar PDF", out, file_name=f"Factura_{nom}.pdf")

