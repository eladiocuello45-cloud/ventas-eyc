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

# --- 1. BARRA LATERAL: LIMPIEZA Y REPORTE ---
st.sidebar.header("⚙️ Panel de Control")

# Botón para borrar el error de la "Fecha" si aparece
if st.sidebar.button("🗑️ REINICIAR (Borrar Error)"):
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
        st.rerun()

# --- 2. FUNCIONES DE FORMATO ---
def f_moneda(valor):
    try:
        return f"$ {int(float(valor)):,}".replace(",", ".")
    except:
        return "$ 0"

def crear_pdf(df_agrupado, t_nombre, nombre_dueno):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=EMPRESA, ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, txt=f"TIENDA: {t_nombre}", ln=True)
    pdf.cell(0, 7, txt=f"PROPIETARIO: {nombre_dueno}", ln=True)
    pdf.cell(0, 7, txt=f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 10, "Producto", 1, 0, 'L', True)
    pdf.cell(20, 10, "Cant", 1, 0, 'C', True)
    pdf.cell(40, 10, "V. Unit", 1, 0, 'C', True)
    pdf.cell(40, 10, "Subtotal", 1, 1, 'C', True)
    
    total_neto = 0
    pdf.set_font("Arial", '', 10)
    for p, row in df_agrupado.iterrows():
        v_unit = row['Total'] / row['Cant']
        total_neto += row['Total']
        pdf.cell(90, 10, p, 1)
        pdf.cell(20, 10, str(int(row['Cant'])), 1, 0, 'C')
        pdf.cell(40, 10, f_moneda(v_unit), 1, 0, 'R')
        pdf.cell(40, 10, f_moneda(row['Total']), 1, 1, 'R')
    
    iva = total_neto * IVA_PORC
    total_f = total_neto + iva
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(150, 8, "VALOR NETO:", 0, 0, 'R'); pdf.cell(40, 8, f_moneda(total_neto), 0, 1, 'R')
    pdf.cell(150, 8, "IVA (19%):", 0, 0, 'R'); pdf.cell(40, 8, f_moneda(iva), 0, 1, 'R')
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(150, 10, "TOTAL A PAGAR:", 0, 0, 'R'); pdf.cell(40, 10, f_moneda(total_f), 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MANEJO DE DATOS ---
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["ID", "Fecha", "Zona", "Tienda", "Producto", "Cant", "Total", "Estado"]).to_csv(CSV_FILE, index=False, sep=';')

df_v = pd.read_csv(CSV_FILE, sep=';')
fecha_hoy = datetime.now().strftime("%d/%m/%Y")
# Filtrar solo pedidos de hoy para los chulitos
pedidos_hoy = df_v[df_v['Fecha'] == fecha_hoy]

# --- 4. INTERFAZ ---
st.markdown(f"<h1 style='text-align: center;'>💰 {EMPRESA}</h1>", unsafe_allow_html=True)

if os.path.exists("clientes_sucre.xlsx"):
    df_c = pd.read_excel("clientes_sucre.xlsx").fillna("S/N").astype(str)
    df_c.columns = df_c.columns.str.strip()
    
    col1, col2 = st.columns(2)
    dia = col1.selectbox("📅 Día", ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"])
    zn = col2.selectbox("📍 Zona", sorted(df_c['Zona'].unique()))
    
    busq = st.text_input("🔍 Buscar tienda...")
    mask = (df_c['Zona'] == zn) & (df_c['Frecuencia'].str.contains(dia))
    if busq: mask = mask & (df_c['Establecimiento'].str.contains(busq, case=False))
    
    # --- LÓGICA DE CHULITOS VERDES ---
    tiendas_base = sorted(df_c[mask]["Establecimiento"].unique())
    opciones_menu = []
    for t in tiendas_base:
        if t in pedidos_hoy['Tienda'].values:
            opciones_menu.append(f"✅ {t}")
        else:
            opciones_menu.append(f"⚪ {t}")
    
    t_display = st.selectbox("🏪 Seleccione la Tienda", opciones_menu)
    t_sel = t_display[2:] if t_display else None

    if t_sel:
        info = df_c[df_c['Establecimiento'] == t_sel].iloc[0]
        col_p = next((c for c in df_c.columns if any(x in c.upper() for x in ["CLIENTE", "PROPIETARIO", "NOMBRE"])), "S/N")
        nombre_dueno = info[col_p]
        st.info(f"👤 Dueño: {nombre_dueno} | 📞 Tel: {info.get('Telefono', 'S/N')}")

        with st.form("pedido"):
            prod = st.selectbox("📦 Producto", ["Gaseosa Mega 3L", "Agua Mineral 500ml", "Leche Bolsa", "Avena"])
            cant = st.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("➕ AGREGAR"):
                precios = {"Gaseosa Mega 3L": 8500, "Agua Mineral 500ml": 1200, "Leche Bolsa": 3200, "Avena": 2500}
                nueva = pd.DataFrame([{"ID": str(datetime.now().timestamp()), "Fecha": fecha_hoy, "Zona": zn, "Tienda": t_sel, "Producto": prod, "Cant": cant, "Total": precios[prod]*cant, "Estado": "Venta"}])
                pd.concat([df_v, nueva]).to_csv(CSV_FILE, index=False, sep=';'); st.rerun()

        # Resumen y Factura
        v_hoy_tienda = df_v[(df_v['Tienda'] == t_sel) & (df_v['Fecha'] == fecha_hoy)]
        if not v_hoy_tienda.empty:
            resumen = v_hoy_tienda.groupby("Producto").agg({'Cant': 'sum', 'Total': 'sum'})
            st.table(resumen.assign(Total=resumen['Total'].apply(f_moneda)))
            
            pdf_f = crear_pdf(resumen, t_sel, nombre_dueno)
            st.download_button("📄 DESCARGAR FACTURA (PDF)", data=pdf_f, file_name=f"Factura_{t_sel}.pdf", use_container_width=True)

# --- 5. REPORTE PARA EL COMPUTADOR ---
st.sidebar.markdown("---")
st.sidebar.subheader("📥 Reporte para Excel")
if not df_v.empty:
    # Este botón te permite bajar todo lo que has hecho desde el celular a tu PC
    csv_data = df_v.to_csv(index=False, sep=';').encode('utf-8')
    st.sidebar.download_button(
        label="Descargar todos los Pedidos",
        data=csv_data,
        file_name=f"Pedidos_{fecha_hoy.replace('/','-')}.csv",
        mime="text/csv",
        use_container_width=True
    )
