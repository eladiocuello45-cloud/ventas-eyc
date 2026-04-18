import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
EMPRESA = "Distribuciones E y C"
CSV_FILE = "pedidos_realizados.csv"
IVA_PORC = 0.19

st.set_page_config(page_title=EMPRESA, page_icon="💰")

# --- 1. BOTÓN DE EMERGENCIA PARA BORRAR EL ERROR (EN EL CELULAR) ---
if st.sidebar.button("🗑️ REINICIAR SISTEMA (Borrar Error)"):
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
        st.sidebar.success("Archivo borrado. La página se recargará.")
        st.rerun()

# --- 2. FUNCIÓN PARA PUNTOS DE MILES ($ 59.500) ---
def f_moneda(valor):
    try:
        return f"$ {int(float(valor)):,}".replace(",", ".")
    except:
        return "$ 0"

# --- 3. GENERADOR DE PDF (FACTURA CON IVA Y PUNTOS) ---
def crear_pdf(df_agrupado, t_nombre, nombre_dueno):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=EMPRESA, ln=True, align='C')
    pdf.ln(5)
    
    # Info Cliente
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, txt=f"TIENDA: {t_nombre}", ln=True)
    pdf.cell(0, 7, txt=f"PROPIETARIO: {nombre_dueno}", ln=True)
    pdf.cell(0, 7, txt=f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    
    # Tabla de Productos
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(85, 10, "Producto", 1, 0, 'L', True)
    pdf.cell(25, 10, "Cant", 1, 0, 'C', True)
    pdf.cell(40, 10, "V. Unit", 1, 0, 'C', True)
    pdf.cell(40, 10, "Subtotal", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 10)
    total_neto = 0
    for p, row in df_agrupado.iterrows():
        v_unitario = row['Total'] / row['Cant']
        total_neto += row['Total']
        pdf.cell(85, 10, p, 1)
        pdf.cell(25, 10, str(int(row['Cant'])), 1, 0, 'C')
        pdf.cell(40, 10, f_moneda(v_unitario), 1, 0, 'R')
        pdf.cell(40, 10, f_moneda(row['Total']), 1, 1, 'R')
    
    # Totales
    valor_iva = total_neto * IVA_PORC
    total_factura = total_neto + valor_iva
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(150, 8, "VALOR NETO:", 0, 0, 'R')
    pdf.cell(40, 8, f_moneda(total_neto), 0, 1, 'R')
    pdf.cell(150, 8, f"IVA ({int(IVA_PORC*100)}%):", 0, 0, 'R')
    pdf.cell(40, 8, f_moneda(valor_iva), 0, 1, 'R')
    
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(150, 10, "TOTAL A PAGAR:", 0, 0, 'R')
    pdf.cell(40, 10, f_moneda(total_factura), 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. LÓGICA DE LA APP ---
st.markdown(f"<h1 style='text-align: center;'>💰 {EMPRESA}</h1>", unsafe_allow_html=True)

# Crear archivo si no existe con todas las columnas
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["ID", "Fecha", "Zona", "Tienda", "Producto", "Cant", "Total", "Estado"]).to_csv(CSV_FILE, index=False, sep=';')

df_v = pd.read_csv(CSV_FILE, sep=';')
fecha_hoy = datetime.now().strftime("%d/%m/%Y")

if os.path.exists("clientes_sucre.xlsx"):
    df_c = pd.read_excel("clientes_sucre.xlsx").fillna("S/N").astype(str)
    df_c.columns = df_c.columns.str.strip()
    
    # Filtros
    col1, col2 = st.columns(2)
    dia_sel = col1.selectbox("📅 Día", ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"])
    zona_sel = col2.selectbox("📍 Zona", sorted(df_c['Zona'].unique()))
    
    busqueda = st.text_input("🔍 Buscar cliente...")
    mask = (df_c['Zona'] == zona_sel) & (df_c['Frecuencia'].str.contains(dia_sel))
    if busqueda: mask = mask & (df_c['Establecimiento'].str.contains(busqueda, case=False))
    
    tiendas = sorted(df_c[mask]["Establecimiento"].unique())
    t_sel = st.selectbox("🏪 Tienda", tiendas)
    
    if t_sel:
        info = df_c[df_c['Establecimiento'] == t_sel].iloc[0]
        # Buscar nombre del dueño automáticamente
        col_p = next((c for c in df_c.columns if any(x in c.upper() for x in ["CLIENTE", "PROPIETARIO", "NOMBRE"])), "S/N")
        nombre_dueno = info[col_p]
        st.info(f"👤 Dueño: {nombre_dueno} | 📞 Tel: {info.get('Telefono', 'S/N')}")

        with st.form("pedido"):
            prod = st.selectbox("📦 Producto", ["Gaseosa Mega 3L", "Agua Mineral 500ml", "Leche Bolsa", "Avena"])
            cant = st.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("➕ AGREGAR"):
                precios = {"Gaseosa Mega 3L": 8500, "Agua Mineral 500ml": 1200, "Leche Bolsa": 3200, "Avena": 2500}
                nueva = pd.DataFrame([{"ID": str(datetime.now().timestamp()), "Fecha": fecha_hoy, "Zona": zona_sel, "Tienda": t_sel, "Producto": prod, "Cant": cant, "Total": precios[prod]*cant, "Estado": "Venta"}])
                pd.concat([df_v, nueva]).to_csv(CSV_FILE, index=False, sep=';'); st.rerun()

        # Resumen y Factura
        ventas_hoy = df_v[(df_v['Tienda'] == t_sel) & (df_v['Fecha'] == fecha_hoy) & (df_v['Estado'] == "Venta")]
        if not ventas_hoy.empty:
            resumen = ventas_hoy.groupby("Producto").agg({'Cant': 'sum', 'Total': 'sum'})
            st.table(resumen.assign(Total=resumen['Total'].apply(f_moneda)))
            
            pdf_f = crear_pdf(resumen, t_sel, nombre_dueno)
            st.download_button("📄 DESCARGAR FACTURA (PDF)", data=pdf_f, file_name=f"Factura_{t_sel}.pdf", use_container_width=True)

            if st.button("🚀 ENVIAR A LOGÍSTICA", type="primary", use_container_width=True):
                df_v.loc[(df_v['Tienda'] == t_sel) & (df_v['Fecha'] == fecha_hoy), 'Estado'] = "Enviado"
                df_v.to_csv(CSV_FILE, index=False, sep=';'); st.success("✅ Pedido enviado correctamente"); st.rerun()
else:
    st.error("⚠️ No se encontró el archivo de clientes.")
