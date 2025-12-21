import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import date

# Configuración de página
st.set_page_config(page_title="Facturación Pro", layout="wide")

# Función para formatear números (Unidades de mil sin decimales)
def formato_moneda(valor):
    return f"{int(valor):,}".replace(",", ".")

st.title("📑 Sistema de Facturación Múltiple")
st.markdown("Este sistema permite gestionar varias facturas simultáneamente en pestañas separadas.")

# --- CONFIGURACIÓN GLOBAL (SIDEBAR) ---
with st.sidebar:
    st.header("Configuración General")
    logo = st.file_uploader("Subir Logo de la Revista", type=["png", "jpg", "jpeg"])
    nombre_revista = st.text_input("Nombre de la Revista", "Revista Automática")
    metodo_pago = st.text_input("Método de Pago (Ej: Nequi 300...)", "Nequi")

# Creamos 3 pestañas para manejar 3 facturas al tiempo (puedes aumentar el número)
tab1, tab2, tab3 = st.tabs(["Factura 1", "Factura 2", "Factura 3"])

def renderizar_factura(id_factura):
    st.subheader(f"Datos de la Factura {id_factura}")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cliente = st.text_input(f"Nombre del Cliente", key=f"cli_{id_factura}")
    with col_c2:
        fecha = st.date_input(f"Fecha de Pago", date.today(), key=f"fec_{id_factura}")

    # Estado de la tabla de productos para esta pestaña específica
    key_filas = f"filas_{id_factura}"
    if key_filas not in st.session_state:
        st.session_state[key_filas] = [{"Pag": "", "Producto": "", "Cant": 1, "Cat": 0, "List": 0}]

    def agregar_fila():
        st.session_state[key_filas].append({"Pag": "", "Producto": "", "Cant": 1, "Cat": 0, "List": 0})

    # Interfaz de entrada
    for i, fila in enumerate(st.session_state[key_filas]):
        c1, c2, c3, c4, c5, c6 = st.columns([1, 3, 1, 2, 2, 2])
        with c1:
            fila['Pag'] = st.text_input("Pág", value=fila['Pag'], key=f"p_{id_factura}_{i}")
        with c2:
            fila['Producto'] = st.text_input("Producto", value=fila['Producto'], key=f"pr_{id_factura}_{i}")
        with c3:
            fila['Cant'] = st.number_input("Cant", value=fila['Cant'], min_value=1, key=f"n_{id_factura}_{i}")
        with c4:
            v_cat = st.number_input("Precio Cat. Unitario", value=fila['Cat'], key=f"cat_{id_factura}_{i}")
            fila['Cat'] = v_cat
        with c5:
            v_list = st.number_input("Precio List. Unitario", value=fila['List'], key=f"li_{id_factura}_{i}")
            fila['List'] = v_list
        with c6:
            # Cálculos automáticos: Cantidad * Precio
            total_fila_cat = fila['Cant'] * fila['Cat']
            total_fila_list = fila['Cant'] * fila['List']
            ganancia_fila = total_fila_cat - total_fila_list
            st.write(f"**Ganancia:** {formato_moneda(ganancia_fila)}")

    st.button("➕ Agregar Producto", key=f"btn_{id_factura}", on_click=agregar_fila)

    # Procesar datos para el PDF
    df = pd.DataFrame(st.session_state[key_filas])
    df['Total_Cat'] = df['Cant'] * df['Cat']
    df['Total_List'] = df['Cant'] * df['List']
    df['Ganancia'] = df['Total_Cat'] - df['Total_List']

    t_cat = df['Total_Cat'].sum()
    t_list = df['Total_List'].sum()
    t_gan = df['Ganancia'].sum()

    st.divider()
    st.info(f"Totales Factura {id_factura}: Catálogo: ${formato_moneda(t_cat)} | Lista: ${formato_moneda(t_list)} | Ganancia: ${formato_moneda(t_gan)}")

    # Botón PDF
    if st.button(f"Generar PDF Factura {id_factura}", key=f"pdf_{id_factura}"):
        if not cliente:
            st.warning("Escribe el nombre del cliente.")
        else:
            pdf = FPDF()
            pdf.add_page()
            if logo:
                with open("temp_logo.png", "wb") as f: f.write(logo.getbuffer())
                pdf.image("temp_logo.png", 10, 8, 30)
                pdf.ln(20)
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt=nombre_revista.upper(), ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"Cliente: {cliente}  |  Fecha: {fecha}", ln=True, align='C')
            pdf.cell(200, 10, txt=f"Método de Pago: {metodo_pago}", ln=True, align='C')
            pdf.ln(5)

            # Encabezados de tabla
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(10, 8, "Pág", 1, 0, 'C', True)
            pdf.cell(60, 8, "Producto", 1, 0, 'C', True)
            pdf.cell(10, 8, "Cant", 1, 0, 'C', True)
            pdf.cell(35, 8, "T. Catálogo", 1, 0, 'C', True)
            pdf.cell(35, 8, "T. Lista", 1, 0, 'C', True)
            pdf.cell(35, 8, "Ganancia", 1, 1, 'C', True)

            pdf.set_font("Arial", size=9)
            for _, r in df.iterrows():
                pdf.cell(10, 8, str(r['Pag']), 1)
                pdf.cell(60, 8, str(r['Producto']), 1)
                pdf.cell(10, 8, str(r['Cant']), 1, 0, 'C')
                pdf.cell(35, 8, f"${formato_moneda(r['Total_Cat'])}", 1)
                pdf.cell(35, 8, f"${formato_moneda(r['Total_List'])}", 1)
                pdf.cell(35, 8, f"${formato_moneda(r['Ganancia'])}", 1, 1)

            # Totales Finales
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(80, 10, "TOTALES FINALES", 1, 0, 'R', True)
            pdf.cell(35, 10, f"${formato_moneda(t_cat)}", 1, 0, 'C', True)
            pdf.cell(35, 10, f"${formato_moneda(t_list)}", 1, 0, 'C', True)
            pdf.cell(35, 10, f"${formato_moneda(t_gan)}", 1, 1, 'C', True)

            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("⬇️ Descargar este PDF", data=pdf_out, file_name=f"Factura_{cliente}.pdf")

# Renderizar cada pestaña
with tab1: renderizar_factura(1)
with tab2: renderizar_factura(2)
with tab3: renderizar_factura(3)
