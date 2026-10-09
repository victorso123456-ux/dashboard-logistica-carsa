import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import smtplib
from email.message import EmailMessage

# Configuración de la página web
st.set_page_config(page_title="Dashboard Logístico Avanzado - Carsa Ica", layout="wide")

st.title("📊 Dashboard Gerencial de Control Logístico y Trazabilidad - Carsa Ica")
st.markdown("---")

# 1. Base de datos avanzada con Tiempos (Trazabilidad), Rotación y Costos
data_sistema = {
    'SKU': ['TV55BLK', 'TV65SLV', 'COC4HWH', 'REF300SL', 'LIC600RD'],
    'Categoria': ['Línea Marrón', 'Línea Marrón', 'Línea Blanca', 'Línea Blanca', 'Pequeños Electro'],
    'Descripcion': ['Televisor LED 55"', 'Televisor QLED 65"', 'Cocina a Gas 4H', 'Refrigeradora No Frost', 'Licuadora 600W'],
    'Talla_Pulgadas': ['55"', '65"', '4 Hornillas', '300 Litros', '600W'],
    'Color': ['Negro', 'Silver', 'Blanco', 'Acero', 'Rojo'],
    'Stock_Sistema': [10, 4, 5, 3, 15],
    'Costo_Unitario': [1200.0, 1850.0, 850.0, 1500.0, 150.0],
    'Rotacion_Mensual': [25, 12, 18, 5, 40], # Unidades salidas al mes (Mayor rotación)
    'Fecha_Ingreso': ['2026-10-01 08:30', '2026-10-02 10:15', '2026-09-28 14:00', '2026-09-25 09:00', '2026-10-05 11:00'],
    'Fecha_Despacho_Ultimo': ['2026-10-08 16:45', '2026-10-07 11:30', '2026-10-08 17:00', '2026-10-03 15:20', '2026-10-09 10:00']
}

data_fisico = {
    'SKU': ['TV55BLK', 'TV65SLV', 'COC4HWH', 'REF300SL', 'LIC600RD'],
    'Stock_Fisico': [10, 3, 4, 3, 15],
    'Estado_Averia': ['BUENO', 'BUENO', 'BUENO', 'DANADO', 'BUENO']
}

df_sistema = pd.DataFrame(data_sistema)
df_fisico = pd.DataFrame(data_fisico)

# Convertir fechas a formato datetime para trazabilidad de tiempos
df_sistema['Fecha_Ingreso'] = pd.to_datetime(df_sistema['Fecha_Ingreso'])
df_sistema['Fecha_Despacho_Ultimo'] = pd.to_datetime(df_sistema['Fecha_Despacho_Ultimo'])
df_sistema['Tiempo_En_Almacen_Dias'] = (datetime.now() - df_sistema['Fecha_Ingreso']).dt.days

# Cruce logístico exacto
df_merged = pd.merge(df_sistema, df_fisico, on='SKU', how='inner')
df_merged['Diferencia'] = df_merged['Stock_Fisico'] - df_merged['Stock_Sistema']
df_merged['Exacto'] = df_merged['Diferencia'].apply(lambda x: 1 if x == 0 else 0)
df_merged['Impacto_Merma_Soles'] = abs(df_merged['Diferencia']) * df_merged['Costo_Unitario']

# 2. Filtros Dinámicos en Barra Lateral
st.sidebar.header("🔍 Filtros y Analítica")
categoria_filtro = st.sidebar.selectbox("Filtrar por Categoría:", ["Todas"] + list(df_merged['Categoria'].unique()))

if categoria_filtro != "Todas":
    df_filtrado = df_merged[df_merged['Categoria'] == categoria_filtro]
else:
    df_filtrado = df_merged

total_skus = len(df_filtrado)
exactitud_inv = (df_filtrado['Exacto'].sum() / total_skus) * 100 if total_skus > 0 else 0

# 3. KPIs Principales
col1, col2, col3, col4 = st.columns(4)
col1.metric(label="🎯 Exactitud Inventario", value=f"{exactitud_inv:.1f}%", delta="Meta >= 99%")
col2.metric(label="⚠️ SKUs con Desviación", value=len(df_filtrado[df_filtrado['Diferencia'] != 0]))
col3.metric(label="🛑 Pérdida por Mermas", value=f"S/ {df_filtrado['Impacto_Merma_Soles'].sum():,.2f}")
col4.metric(label="⚡ Rotación Promedio", value=f"{df_filtrado['Rotacion_Mensual'].mean():.1f} un/mes")

st.markdown("---")

# 4. Reportes Especiales: Top Rotación y Top Mermas
st.subheader("📊 Analítica de Alto Rendimiento (Rotación y Riesgos)")
col_r1, col_r2 = st.columns(2)

with col_r1:
    st.markdown("**🔥 Top SKUs con Mayor Rotación (Alta Salida)**")
    df_top_rotacion = df_filtrado.sort_values(by='Rotacion_Mensual', ascending=False).head(3)
    st.dataframe(df_top_rotacion[['SKU', 'Descripcion', 'Rotacion_Mensual']], use_container_width=True)

with col_r2:
    st.markdown("**⚠️ SKUs con Mayor Riesgo o Desviación Económica**")
    df_top_mermas = df_filtrado.sort_values(by='Impacto_Merma_Soles', ascending=False).head(3)
    st.dataframe(df_top_mermas[['SKU', 'Descripcion', 'Diferencia', 'Impacto_Merma_Soles']], use_container_width=True)

st.markdown("---")

# 5. Buscador Abierto por Texto (Escribir SKU o Descripción específica)
st.subheader("🔍 Buscador Inteligente de Trazabilidad por SKU")
busqueda_texto = st.text_input("Escribe el código SKU o parte de la descripción (Ej: 'TV55' o 'Refrigeradora'):", "")

if busqueda_texto:
    # Filtrar el dataframe según lo que escriba el usuario (coincidencia parcial)
    df_busqueda = df_filtrado[
        df_filtrado['SKU'].str.contains(busqueda_texto, case=False, na=False) | 
        df_filtrado['Descripcion'].str.contains(busqueda_texto, case=False, na=False)
    ]
else:
    df_busqueda = df_filtrado

if not df_busqueda.empty:
    sku_seleccionado = st.selectbox("Seleccione de los resultados encontrados:", df_busqueda['SKU'].unique())
    df_sku_detalle = df_merged[df_merged['SKU'] == sku_seleccionado].iloc[0]

    # Mostrar ficha de trazabilidad con tiempos
    st.markdown(f"### 📋 Ficha de Trazabilidad: `{df_sku_detalle['SKU']}` - {df_sku_detalle['Descripcion']}")
    
    ts1, ts2, ts3, ts4 = st.columns(4)
    ts1.metric("📦 Categoría / Atributo", f"{df_sku_detalle['Categoria']} ({df_sku_detalle['Talla_Pulgadas']})")
    ts2.metric("💻 Sistema vs 📊 Físico", f"{df_sku_detalle['Stock_Sistema']} vs {df_sku_detalle['Stock_Fisico']}")
    ts3.metric("⏱️ Días en Almacén", f"{df_sku_detalle['Tiempo_En_Almacen_Dias']} días")
    ts4.metric("🕒 Último Despacho", df_sku_detalle['Fecha_Despacho_Ultimo'].strftime('%Y-%m-%d %H:%M'))

    if df_sku_detalle['Diferencia'] != 0:
        st.error(f"🚨 ALERTA CRÍTICA: Discrepancia detectada de {df_sku_detalle['Diferencia']} unidades (Impacto: S/ {df_sku_detalle['Impacto_Merma_Soles']:,.2f})")
    else:
        st.success("✅ Producto con trazabilidad limpia y sin diferencias de inventario.")
else:
    st.warning("⚠️ No se encontraron productos que coincidan con tu búsqueda.")

st.markdown("---")

# 6. Tabla General con Tiempos y Trazabilidad
st.subheader("📋 Base General de Inventario y Tiempos Logísticos")
st.dataframe(df_filtrado[['SKU', 'Descripcion', 'Categoria', 'Stock_Sistema', 'Stock_Fisico', 'Diferencia', 'Rotacion_Mensual', 'Tiempo_En_Almacen_Dias']], use_container_width=True)

st.markdown("---")

# 7. Módulo de Envío de Correos a Jefaturas
st.subheader("📧 Enviar Reporte Ejecutivo por Correo a Jefatura")

with st.form("form_correo"):
    email_destino = st.text_input("Correo de la Jefatura / Gerente:", "jefatura.logistica@carsa.com.pe")
    mensaje_extra = st.text_area("Observaciones:", "Se adjunta reporte con análisis de rotación, mermas y tiempos de trazabilidad.")
    boton_enviar = st.form_submit_button("🚀 Enviar Reporte por Email")
    
    if boton_enviar:
        remitente = "tu_correo@gmail.com"
        password = "tu_contraseña_de_aplicacion"
        
        msg = EmailMessage()
        msg['Subject'] = f"Reporte Gerencial Logístico Avanzado - Carsa Ica - {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = remitente
        msg['To'] = email_destino
        msg.set_content(f"Hola,\n\n{mensaje_extra}\n\n- Exactitud: {exactitud_inv:.1f}%\n- Rotación Promedio: {df_filtrado['Rotacion_Mensual'].mean():.1f} un/mes\n\nAtentamente,\nControl Logístico - Ica")
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(remitente, password)
                smtp.send_message(msg)
            st.success(f"✅ ¡Correo enviado exitosamente a {email_destino}!")
        except Exception as e:
            st.error(f"⚠️ Error al enviar correo: {e}")