import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# ==========================================
# CONFIGURACIÓN Y ESTILO
# ==========================================
EMPRESA = "Distribuciones E y C"
IVA_PORC = 0.19
CELULAR_EMPRESA = "3008756441" 

st.set_page_config(page_title=EMPRESA, page_icon="💰", layout="centered")

st.markdown(f"<h1 style='text-align: center;'>💰 {EMPRESA}</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: gray;'>Facturación TAT con Buscador</h4>", unsafe_allow_html=True)

def f_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return "$ 0"

# --- GENERADOR DE PDF ---
def crear_pdf(df_agrupado, t_nombre, nombre_dueno):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=EMPRESA, ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, txt=f"ESTABLECIMIENTO: {t_nombre}", ln=True)
    pdf.cell(0, 7, txt=f"PROPIETARIO: {nombre_dueno}", ln=True)
    pdf.cell(0, 7, txt=f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 10, "Producto", 1, 0, 'L', True); pdf.cell(25, 10, "Cant", 1, 0, 'C', True); pdf.cell(35, 10, "Unitario", 1, 0, 'C', True); pdf.cell(40, 10, "Subtotal", 1, 1, 'C', True)
    
    total_neto = df_agrupado['Total'].sum()
    pdf.set_font("Arial", '', 10)
    for p, row in df_agrupado.iterrows():
        unit = row['Total'] / row['Cant']
        pdf.cell(90, 10, p, 1); pdf.cell(25, 10, str(int(row['Cant'])), 1, 0, 'C'); pdf.cell(35, 10, f_moneda(unit), 1, 0, 'R'); pdf.cell(40, 10, f_moneda(row['Total']), 1, 1, 'R')
    
    iva_v = total_neto * IVA_PORC
    total_con_iva = total_neto + iva_v
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(150, 8, "SUBTOTAL:", 0, 0, 'R'); pdf.cell(40, 8, f_moneda(total_neto), 0, 1, 'R')
    pdf.cell(150, 8, f"IVA ({int(IVA_PORC*100)}%):", 0, 0, 'R'); pdf.cell(40, 8, f_moneda(iva_v), 0, 1, 'R')
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(150, 10, "TOTAL A PAGAR:", 0, 0, 'R'); pdf.cell(40, 10, f_moneda(total_con_iva), 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# GESTIÓN DE DATOS
# ==========================================
if os.path.exists("clientes_sucre.xlsx"):
    df_c = pd.read_excel("clientes_sucre.xlsx").fillna("S/N")
    df_c.columns = df_c.columns.str.strip() 
    df_c = df_c.astype(str)
else:
    st.error("Archivo clientes_sucre.xlsx no encontrado."); st.stop()

if os.path.exists("pedidos_realizados.csv"):
    df_v = pd.read_csv("pedidos_realizados.csv")
else:
    df_v = pd.DataFrame(columns=["ID", "Fecha", "Tienda", "Producto", "Cant", "Total", "Estado"])

fecha_hoy = datetime.now().strftime("%d/%m/%Y")
df_hoy = df_v[df_v['Fecha'] == fecha_hoy]

# --- RUTA Y BUSCADOR (LUPITA) ---
c1, c2 = st.columns(2)
dia = c1.selectbox("📅 Día", ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"])
zona = c2.selectbox("📍 Zona", sorted(df_c['Zona'].unique()))

# 🔍 NUEVO: BUSCADOR GENERAL (Lupita)
busqueda = st.text_input("🔍 Buscar cliente o tienda...", placeholder="Escribe el nombre aquí...")

# Filtramos la lista de tiendas por día, zona y búsqueda
mask = (df_c['Zona'] == zona) & (df_c['Frecuencia'].str.contains(dia))
if busqueda:
    mask = (df_c['Establecimiento'].str.contains(busqueda, case=False)) | (df_c.apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1))

tiendas_filtradas = sorted(df_c[mask]["Establecimiento"].unique())

opciones = []
for t in tiendas_filtradas:
    estados = df_hoy[df_hoy['Tienda'] == t]['Estado'].values
    if "Venta" in estados: opciones.append(f"✅ {t}")
    elif "No Compro" in estados: opciones.append(f"❌ {t}")
    else: opciones.append(f"⚪ {t}")

t_display = st.selectbox("🏪 Seleccione la Tienda", opciones)
t_sel = t_display[2:] if t_display else None

if t_sel:
    info = df_c[df_c['Establecimiento'] == t_sel].iloc[0]
    
    # BUSCADOR DINÁMICO DEL PROPIETARIO
    nombre_dueno = "No definido"
    for col in df_c.columns:
        if any(x in col.upper() for x in ["NOMBRE", "CLIENTE", "PROP", "DUE"]):
            nombre_dueno = info[col]
            break
    
    st.info(f"👤 **Propietario:** {nombre_dueno} | 📞 **Tel:** {info.get('Telefono', 'S/T')} | 🏠 **Dir:** {info.get('Direccion', 'S/D')}")

    col_v, col_n = st.columns(2)
    if col_n.button("🚫 MARCADO: NO COMPRÓ", use_container_width=True):
        nueva = pd.DataFrame([{"ID": str(datetime.now().timestamp()), "Fecha": fecha_hoy, "Tienda": t_sel, "Producto": "N/A", "Cant": 0, "Total": 0, "Estado": "No Compro"}])
        pd.concat([df_v, nueva]).to_csv("pedidos_realizados.csv", index=False); st.rerun()

    with st.form("registro"):
        p = st.selectbox("📦 Producto", ["Gaseosa Mega 3L", "Agua Mineral 500ml", "Leche Bolsa", "Avena"])
        c = st.number_input("Cantidad", min_value=1, step=1)
        if st.form_submit_button("✅ REGISTRAR PRODUCTO", use_container_width=True):
            precios = {"Gaseosa Mega 3L": 8500, "Agua Mineral 500ml": 1200, "Leche Bolsa": 3200, "Avena": 2500}
            nueva = pd.DataFrame([{"ID": str(datetime.now().timestamp()), "Fecha": fecha_hoy, "Tienda": t_sel, "Producto": p, "Cant": c, "Total": precios[p]*c, "Estado": "Venta"}])
            pd.concat([df_v, nueva]).to_csv("pedidos_realizados.csv", index=False); st.rerun()

    v_tienda = df_hoy[(df_hoy['Tienda'] == t_sel) & (df_hoy['Estado'] == "Venta")]
    if not v_tienda.empty:
        df_agrupado = v_tienda.groupby("Producto").agg({'Cant': 'sum', 'Total': 'sum'})
        st.write("---")
        sub_t = df_agrupado['Total'].sum()
        iva_v = sub_t * IVA_PORC
        total_v = sub_t + iva_v
        st.write(f"Subtotal: {f_moneda(sub_t)} | IVA (19%): {f_moneda(iva_v)}")
        st.markdown(f"### TOTAL CON IVA: {f_moneda(total_v)}")

        ca, cb = st.columns(2)
        pdf_file = crear_pdf(df_agrupado, t_sel, nombre_dueno)
        ca.download_button("🖨️ PDF FACTURA", data=pdf_file, file_name=f"Factura_{t_sel}.pdf", use_container_width=True)
        msg_cli = f"Hola {nombre_dueno}, su pedido es de {f_moneda(total_v)}. ¡Gracias!"
        cb.link_button("📲 WHATSAPP", f"https://wa.me/57{info.get('Telefono')}?text={msg_cli.replace(' ','%20')}", use_container_width=True)

# --- CIERRE DEL DÍA ---
st.divider()
if st.checkbox("⚙️ Cierre de Jornada"):
    ventas_ok = df_hoy[df_hoy['Estado'] == "Venta"]
    if not ventas_ok.empty:
        total_dia = ventas_ok['Total'].sum() * (1 + IVA_PORC)
        st.metric("Ventas Totales Hoy (Con IVA)", f_moneda(total_dia))
        if st.button("🔴 CERRAR DÍA Y LIMPIAR DATOS", use_container_width=True):
            if os.path.exists("pedidos_realizados.csv"): os.remove("pedidos_realizados.csv")
            st.rerun()
