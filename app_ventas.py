import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
EMPRESA = "Distribuciones E y C"
IVA_PORC = 0.19
CSV_FILE = "pedidos_realizados.csv"

st.set_page_config(page_title=EMPRESA, page_icon="💰")
st.markdown(f"<h1 style='text-align: center;'>💰 {EMPRESA}</h1>", unsafe_allow_html=True)

# --- FUNCIÓN PARA PUNTOS DE MILES ($ 1.000) ---
def f_moneda(valor):
    try: 
        return f"$ {int(float(valor)):,}".replace(",", ".")
    except: 
        return "$ 0"

# --- GENERADOR DE PDF CORREGIDO CON IVA Y PUNTOS ---
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
    
    # Encabezados
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 10, "Producto", 1, 0, 'L', True)
    pdf.cell(25, 10, "Cant", 1, 0, 'C', True)
    pdf.cell(35, 10, "Unit", 1, 0, 'C', True)
    pdf.cell(40, 10, "Subtotal", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 10)
    total_neto = 0
    for p, row in df_agrupado.iterrows():
        unit = row['Total'] / row['Cant']
        total_neto += row['Total']
        pdf.cell(90, 10, p, 1)
        pdf.cell(25, 10, str(int(row['Cant'])), 1, 0, 'C')
        pdf.cell(35, 10, f_moneda(unit), 1, 0, 'R')
        pdf.cell(40, 10, f_moneda(row['Total']), 1, 1, 'R')
    
    # --- CÁLCULOS DE IVA ---
    valor_iva = total_neto * IVA_PORC
    total_final = total_neto + valor_iva
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(150, 8, "VALOR NETO:", 0, 0, 'R')
    pdf.cell(40, 8, f_moneda(total_neto), 0, 1, 'R')
    
    pdf.cell(150, 8, f"IVA ({int(IVA_PORC*100)}%):", 0, 0, 'R')
    pdf.cell(40, 8, f_moneda(valor_iva), 0, 1, 'R')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "TOTAL CON IVA:", 0, 0, 'R')
    pdf.cell(40, 10, f_moneda(total_final), 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- CARGA DE DATOS ---
if os.path.exists("clientes_sucre.xlsx"):
    df_c = pd.read_excel("clientes_sucre.xlsx").fillna("S/N").astype(str)
    df_c.columns = df_c.columns.str.strip()
else:
    st.error("⚠️ No se encuentra el archivo Excel"); st.stop()

if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["ID", "Fecha", "Zona", "Tienda", "Producto", "Cant", "Total", "Estado"]).to_csv(CSV_FILE, index=False, sep=';')

df_v = pd.read_csv(CSV_FILE, sep=';')
fecha_hoy = datetime.now().strftime("%d/%m/%Y")
df_hoy = df_v[df_v['Fecha'] == fecha_hoy]

# --- INTERFAZ ---
col_a, col_b = st.columns(2)
dia_sel = col_a.selectbox("📅 Día", ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"])
zona_sel = col_b.selectbox("📍 Zona", sorted(df_c['Zona'].unique()))

busqueda = st.text_input("🔍 Buscar por nombre...")
mask = (df_c['Zona'] == zona_sel) & (df_c['Frecuencia'].str.contains(dia_sel))
if busqueda: mask = mask & (df_c['Establecimiento'].str.contains(busqueda, case=False))

tiendas_disponibles = sorted(df_c[mask]["Establecimiento"].unique())
opciones_est = []
for t in tiendas_disponibles:
    if not df_hoy.empty and t in df_hoy['Tienda'].values:
        icono = "✅" if df_hoy[df_hoy['Tienda'] == t]['Estado'].iloc[-1] in ["Enviado", "Venta"] else "❌"
        opciones_est.append(f"{icono} {t}")
    else: opciones_est.append(f"⚪ {t}")

t_display = st.selectbox("🏪 Seleccione la Tienda", opciones_est)
t_sel = t_display[2:] if t_display else None

if t_sel:
    info = df_c[df_c['Establecimiento'] == t_sel].iloc[0]
    col_p = next((c for c in df_c.columns if any(x in c.upper() for x in ["PROPIETARIO", "CLIENTE", "NOMBRE"])), None)
    nombre_dueno = info[col_p] if col_p else "S/N"
    st.info(f"👤 **Dueño:** {nombre_dueno} | 📞 **Tel:** {info.get('Telefono', 'S/N')}")

    if st.button("🚫 NO COMPRÓ", use_container_width=True):
        nueva = pd.DataFrame([{"ID": str(datetime.now().timestamp()), "Fecha": fecha_hoy, "Zona": zona_sel, "Tienda": t_sel, "Producto": "N/A", "Cant": 0, "Total": 0, "Estado": "No Compro"}])
        pd.concat([df_v, nueva]).to_csv(CSV_FILE, index=False, sep=';'); st.rerun()

    with st.form("compra"):
        prod = st.selectbox("📦 Producto", ["Gaseosa Mega 3L", "Agua Mineral 500ml", "Leche Bolsa", "Avena"])
        cant = st.number_input("Cantidad", min_value=1, step=1)
        if st.form_submit_button("➕ AGREGAR"):
            precios = {"Gaseosa Mega 3L": 8500, "Agua Mineral 500ml": 1200, "Leche Bolsa": 3200, "Avena": 2500}
            nueva = pd.DataFrame([{"ID": str(datetime.now().timestamp()), "Fecha": fecha_hoy, "Zona": zona_sel, "Tienda": t_sel, "Producto": prod, "Cant": cant, "Total": precios[prod]*cant, "Estado": "Venta"}])
            pd.concat([df_v, nueva]).to_csv(CSV_FILE, index=False, sep=';'); st.rerun()

    ventas_t = df_v[(df_v['Tienda'] == t_sel) & (df_v['Fecha'] == fecha_hoy) & (df_v['Estado'] == "Venta")]
    if not ventas_t.empty:
        resumen = ventas_t.groupby("Producto").agg({'Cant': 'sum', 'Total': 'sum'})
        
        # Tabla en pantalla con puntos
        resumen_p = resumen.copy()
        resumen_p['Total'] = resumen_p['Total'].apply(f_moneda)
        st.table(resumen_p)
        
        if st.button("🚀 ENVIAR A LOGÍSTICA", type="primary", use_container_width=True):
            df_v.loc[(df_v['Tienda'] == t_sel) & (df_v['Fecha'] == fecha_hoy), 'Estado'] = "Enviado"
            df_v.to_csv(CSV_FILE, index=False, sep=';'); st.success("✅ Enviado"); st.rerun()
        
        # PDF con IVA y puntos
        pdf_bits = crear_pdf(resumen, t_sel, nombre_dueno)
        st.download_button("📄 PDF FACTURA", data=pdf_bits, file_name=f"Factura_{t_sel}.pdf", use_container_width=True)
