import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date

# Configuración de la página
st.set_page_config(page_title="Sistema de Facturación Revista", layout="wide")

st.title("📄 Generador de Facturas Automático")
st.markdown("Introduce los datos abajo. Las sumas se realizan de forma automática.")

# --- SECCIÓN DE DATOS GENERALES ---
with st.sidebar:
    st.header("Configuración")
    logo = st.file_uploader("Cargar Logo de la Revista", type=["png", "jpg", "jpeg"])
    nombre_revista = st.text_input("Nombre de la Revista", "Revista Ejemplo")

col1, col2 = st.columns(2)
with col1:
    cliente = st.text_input("Nombre del Cliente")
with col2:
    fecha_pago = st.date_input("Fecha de Pago", date.today())

# --- SECCIÓN DE PRODUCTOS DINÁMICOS ---
st.subheader("Productos / Artículos")

if 'filas' not in st.session_state:
    st.session_state.filas = [{"Pag": "", "Producto": "", "Catalogo": 0.0, "Lista": 0.0, "Ganancia": 0.0}]

def agregar_fila():
    st.session_state.filas.append({"Pag": "", "Producto": "", "Catalogo": 0.0, "Lista": 0.0, "Ganancia": 0.0})

def eliminar_fila():
    if len(st.session_state.filas) > 1:
        st.session_state.filas.pop()

# Crear tabla de entrada de datos
for i, fila in enumerate(st.session_state.filas):
    c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 2])
    with c1:
        fila['Pag'] = st.text_input(f"Pág", value=fila['Pag'], key=f"pag_{i}")
    with c2:
        fila['Producto'] = st.text_input(f"Producto {i+1}", value=fila['Producto'], key=f"prod_{i}")
    with c3:
        fila['Catalogo'] = st.number_input(f"Precio Catálogo", value=fila['Catalogo'], key=f"cat_{i}", step=0.1)
    with c4:
        fila['Lista'] = st.number_input(f"Precio Lista", value=fila['Lista'], key=f"list_{i}", step=0.1)
    with c5:
        # Cálculo automático de ganancia
        fila['Ganancia'] = round(fila['Catalogo'] - fila['Lista'], 2)
        st.write(f"**Ganancia:** {fila['Ganancia']}")

st.button("➕ Agregar Producto", on_click=agregar_fila)
st.button("🗑️ Eliminar Último", on_click=eliminar_fila)

# --- CÁLCULOS TOTALES ---
df = pd.DataFrame(st.session_state.filas)
total_cat = df['Catalogo'].sum()
total_list = df['Lista'].sum()
total_gan = df['Ganancia'].sum()

st.divider()
st.subheader(f"Totales: Catálogo: ${total_cat} | Lista: ${total_list} | Ganancia: ${total_gan}")

# --- GENERACIÓN DE PDF ---
def crear_pdf(logo_file, cliente, fecha, dataframe, t_cat, t_list, t_gan):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Logo
    if logo_file:
        # Guardar temporalmente el logo
        with open("temp_logo.png", "wb") as f:
            f.write(logo_file.getbuffer())
        pdf.image("temp_logo.png", 10, 8, 33)
        pdf.ln(25)
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"FACTURA: {nombre_revista}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    pdf.cell(100, 10, txt=f"Cliente: {cliente}", ln=False)
    pdf.cell(100, 10, txt=f"Fecha de Pago: {fecha}", ln=True)
    pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(15, 10, "Pág", 1, 0, 'C', True)
    pdf.cell(75, 10, "Producto", 1, 0, 'C', True)
    pdf.cell(30, 10, "Catálogo", 1, 0, 'C', True)
    pdf.cell(30, 10, "Lista", 1, 0, 'C', True)
    pdf.cell(35, 10, "Ganancia", 1, 1, 'C', True)
    
    pdf.set_font("Arial", size=10)
    for index, row in dataframe.iterrows():
        pdf.cell(15, 10, str(row['Pag']), 1)
        pdf.cell(75, 10, str(row['Producto']), 1)
        pdf.cell(30, 10, f"${row['Catalogo']}", 1)
        pdf.cell(30, 10, f"${row['Lista']}", 1)
        pdf.cell(35, 10, f"${row['Ganancia']}", 1, 1)
        
    # Totales
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(90, 10, "TOTALES", 1, 0, 'R', True)
    pdf.cell(30, 10, f"${t_cat}", 1, 0, 'C', True)
    pdf.cell(30, 10, f"${t_list}", 1, 0, 'C', True)
    pdf.cell(35, 10, f"${t_gan}", 1, 1, 'C', True)
    
    return pdf.output(dest='S').encode('latin-1')

if st.button("🚀 Generar Factura PDF"):
    if not cliente:
        st.error("Por favor, pon el nombre del cliente.")
    else:
        pdf_bytes = crear_pdf(logo, cliente, fecha_pago, df, total_cat, total_list, total_gan)
        st.download_button(label="⬇️ Descargar PDF", data=pdf_bytes, file_name=f"Factura_{cliente}.pdf", mime="application/pdf")