import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# 1. IDENTIDAD
EMPRESA = "Distribuciones E y C"

st.set_page_config(page_title=f"Facturación {EMPRESA}", page_icon="💰", layout="wide")
st.title(f"💰 {EMPRESA} - Facturación TAT")

# FUNCIÓN PARA FORMATO DE MONEDA ($ 8.500)
def f_moneda(valor):
    try:
        return f"$ {int(float(valor)):,}".replace(",", ".")
    except:
        return "$ 0"

# FUNCIÓN PARA EL PDF PROFESIONAL
def crear_pdf(datos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=EMPRESA, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, txt=f"Establecimiento: {datos['Tienda']}", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 7, txt=f"Propietario: {datos['Cliente']}", ln=True)
    pdf.cell(0, 7, txt=f"Tel: {datos['Telefono']} | Dir: {datos['Direccion']}", ln=True)
    pdf.cell(0, 7, txt=f"Fecha: {datos['Fecha']}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(80, 10, "Producto", 1); pdf.cell(25, 10, "Cant", 1); pdf.cell(45, 10, "Total", 1); pdf.ln()
    pdf.set_font("Arial", '', 11)
    pdf.cell(80, 10, datos['Producto'], 1); pdf.cell(25, 10, str(datos['Cant']), 1); pdf.cell(45, 10, f_moneda(datos['Total']), 1); pdf.ln(12)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(105, 8, "Subtotal (Base):", 0); pdf.cell(45, 8, f_moneda(datos['Subtotal']), 0, ln=True)
    pdf.cell(105, 8, "IVA (19%):", 0); pdf.cell(45, 8, f_moneda(datos['IVA']), 0, ln=True)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(105, 10, "TOTAL A COBRAR:", 0); pdf.cell(45, 10, f_moneda(datos['Total']), 0, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# 2. CARGA Y LIMPIEZA EXTREMA
if os.path.exists("clientes_sucre.xlsx"):
    df = pd.read_excel("clientes_sucre.xlsx")
    
    # SOLUCIÓN AL ERROR: Convertir todo a texto y limpiar nulos
    df = df.fillna("").astype(str)
    df.columns = [str(c).strip() for c in df.columns]
    
    col_nombre = 'Nombre Cliente' if 'Nombre Cliente' in df.columns else 'Cliente'

    dia_sel = st.sidebar.selectbox("📅 Día de Ruta", ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"])
    zonas_validas = sorted([z.strip() for z in df['Zona'].unique() if z.strip() != ""])
    zona_sel = st.sidebar.selectbox("👤 Zona", zonas_validas)
    
    df_ruta = df[(df['Zona'] == zona_sel) & (df['Frecuencia'].str.contains(dia_sel, na=False))]
    
    # FILTRO SEGURO PARA TIENDAS (Evita el error de 'float' en L81)
    lista_tiendas = sorted([str(t).strip() for t in df_ruta["Establecimiento"].unique() if str(t).strip() != ""])

    if lista_tiendas:
        t_sel = st.selectbox("🏪 Seleccione la Tienda", lista_tiendas)
        res = df_ruta[df_ruta["Establecimiento"] == t_sel].iloc[0]
        
        v_nom = res[col_nombre] if res[col_nombre] != "" else "No registrado"
        v_tel = res.get('Telefono', 'S/N')
        v_dir = res.get('Direccion', 'S/D')

        st.info(f"👤 **Prop:** {v_nom} | 📞 **Tel:** {v_tel} | 🏠 **Dir:** {v_dir}")

        with st.form("registro"):
            prod = st.selectbox("📦 Producto", ["Gaseosa Mega 3L", "Agua Mineral 500ml", "Leche Bolsa", "Avena"])
            cant = st.number_input("🔢 Cantidad", min_value=1, step=1)
            if st.form_submit_button("✅ REGISTRAR VENTA"):
                precios = {"Gaseosa Mega 3L": 8500, "Agua Mineral 500ml": 1200, "Leche Bolsa": 3200, "Avena": 2500}
                v_total = precios[prod] * cant
                v_sub = v_total / 1.19
                v_iva = v_total - v_sub
                
                venta = {
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Tienda": t_sel, "Cliente": v_nom, "Telefono": v_tel, "Direccion": v_dir,
                    "Producto": prod, "Cant": cant, "Subtotal": int(v_sub), "IVA": int(v_iva), "Total": v_total
                }
                st.session_state.u_v = venta
                pd.DataFrame([venta]).to_csv("pedidos_realizados.csv", mode='a', index=False, header=not os.path.exists("pedidos_realizados.csv"))
                st.rerun()

        if 'u_v' in st.session_state:
            st.download_button("📩 DESCARGAR FACTURA PDF", data=crear_pdf(st.session_state.u_v), file_name=f"Factura_{t_sel}.pdf")

    st.divider()
    if os.path.exists("pedidos_realizados.csv"):
        st.subheader("📋 Resumen de Ventas del Día")
        df_h = pd.read_csv("pedidos_realizados.csv")
        df_v = df_h.copy()
        for c in ['Subtotal', 'IVA', 'Total']:
            df_v[c] = df_v[c].apply(f_moneda)
        st.dataframe(df_v, use_container_width=True)
        st.metric("💰 RECAUDO TOTAL", f_moneda(df_h['Total'].sum()))
        if st.button("🗑️ BORRAR TODO EL HISTORIAL"):
            os.remove("pedidos_realizados.csv")
            if 'u_v' in st.session_state: del st.session_state.u_v
            st.rerun()