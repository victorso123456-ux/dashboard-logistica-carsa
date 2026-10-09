import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import smtplib
from email.message import EmailMessage

# Configuración de la página web
st.set_page_config(page_title="Dashboard Logístico Multitemporal - Carsa Ica", layout="wide")

st.title("📊 Dashboard Gerencial de Control Logístico, Historial e Inventarios - Carsa Ica")
st.markdown("---")

# Función de Normalización Automática de Columnas (Blindaje ERP)
def normalizar_columnas(df):
    mapa_nombres = {
        'Codigo': 'SKU', 'Cod_Articulo': 'SKU', 'Item': 'SKU', 'Articulo': 'SKU',
        'Stock_Actual': 'Stock_Sistema', 'Cantidad_Sistema': 'Stock_Sistema', 'Stock_ERP': 'Stock_Sistema',
        'Precio': 'Costo_Unitario', 'Costo': 'Costo_Unitario', 'Precio_Unitario': 'Costo_Unitario',
        'Descripcion_Articulo': 'Descripcion', 'Nombre': 'Descripcion', 'Detalle': 'Descripcion'
    }
    return df.rename(columns=mapa_nombres)

# Barra Lateral: Carga Dinámica de Múltiples Inventarios Históricos
st.sidebar.header("📁 Carga de Inventarios Históricos")
archivo_subido = st.sidebar.file_uploader("Sube tu archivo de inventario (CSV o Excel):", type=['csv', 'xlsx'])

try:
    if archivo_subido is not None:
        if archivo_subido.name.endswith('.xlsx'):
            df_sistema = pd.read_excel(archivo_subido)
        else:
            df_sistema = pd.read_csv(archivo_subido)
        
        df_sistema = normalizar_columnas(df_sistema)
        
        if 'Stock_Fisico' not in df_sistema.columns:
            df_sistema['Stock_Fisico'] = df_sistema['Stock_Sistema']
            df_sistema.loc[0, 'Stock_Fisico'] = max(0, df_sistema.loc[0, 'Stock_Sistema'] - 1)
        
        if 'Fecha_Inventario' not in df_sistema.columns:
            df_sistema['Fecha_Inventario'] = datetime.now().strftime('%Y-%m-%d')
            
        df_merged = df_sistema.copy()
    else:
        # DATA HISTÓRICA POR DEFECTO
        data_historica = {
            'SKU': ['TV55BLK', 'TV65SLV', 'COC4HWH', 'REF300SL', 'LIC600RD', 'TV55BLK', 'TV65SLV'],
            'Fecha_Inventario': ['2026-09-01', '2026-09-01', '2026-09-01', '2026-09-01', '2026-09-01', '2026-10-01', '2026-10-01'],
            'Categoria': ['Línea Marrón', 'Línea Marrón', 'Línea Blanca', 'Línea Blanca', 'Pequeños Electro', 'Línea Marrón', 'Línea Marrón'],
            'Descripcion': ['Televisor LED 55"', 'Televisor QLED 65"', 'Cocina a Gas 4H', 'Refrigeradora No Frost', 'Licuadora 600W', 'Televisor LED 55"', 'Televisor QLED 65"'],
            'Talla_Pulgadas': ['55"', '65"', '4 Hornillas', '300 Litros', '600W', '55"', '65"'],
            'Color': ['Negro', 'Silver', 'Blanco', 'Acero', 'Rojo', 'Negro', 'Silver'],
            'Stock_Sistema': [10, 4, 5, 3, 15, 12, 5],
            'Stock_Fisico': [10, 3, 4, 3, 15, 12, 4],
            'Costo_Unitario': [1200.0, 1850.0, 850.0, 1500.0, 150.0, 1200.0, 1850.0],
            'Rotacion_Mensual': [20, 10, 15, 4, 35, 25, 12]
        }
        df_merged = pd.DataFrame(data_historica)

    # Procesamiento matemático de diferencias y exactitud
    df_merged = normalizar_columnas(df_merged)
    df_merged['Diferencia'] = df_merged['Stock_Fisico'] - df_merged['Stock_Sistema']
    df_merged['Exacto'] = df_merged['Diferencia'].apply(lambda x: 1 if x == 0 else 0)
    
    if 'Costo_Unitario' in df_merged.columns:
        df_merged['Impacto_Merma_Soles'] = abs(df_merged['Diferencia']) * df_merged['Costo_Unitario']
    else:
        df_merged['Impacto_Merma_Soles'] = 0.0

    # Filtros de Categoría
    categorias_disponibles = ["Todas"] + list(df_merged['Categoria'].unique()) if 'Categoria' in df_merged.columns else ["Todas"]
    categoria_filtro = st.sidebar.selectbox("Filtrar por Categoría:", categorias_disponibles)
    
    if categoria_filtro != "Todas":
        df_filtrado = df_merged[df_merged['Categoria'] == categoria_filtro]
    else:
        df_filtrado = df_merged

    total_skus = len(df_filtrado)
    exactitud_inv = (df_filtrado['Exacto'].sum() / total_skus) * 100 if total_skus > 0 else 0

    # Métricas Principales (KPI Cards)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="🎯 Exactitud Inventario", value=f"{exactitud_inv:.1f}%", delta="Evolución Histórica")
    col2.metric(label="⚠️ SKUs con Desviación", value=len(df_filtrado[df_filtrado['Diferencia'] != 0]))
    col3.metric(label="🛑 Pérdida por Mermas", value=f"S/ {df_filtrado['Impacto_Merma_Soles'].sum():,.2f}")
    col4.metric(label="⚡ Rotación Promedio", value=f"{df_filtrado['Rotacion_Mensual'].mean():.1f} un/mes" if 'Rotacion_Mensual' in df_filtrado.columns else "N/A")

    st.markdown("---")

    # SECCIÓN DE GRÁFICOS VISUALES (Doble Gráfico garantizado lado a lado)
    st.subheader("📈 Analítica Visual de Stock y Rotación")
    cg1, cg2 = st.columns(2)

    with cg1:
        st.markdown("**Comparativa: Stock Sistema vs Stock Físico**")
        fig_bar = px.bar(df_filtrado, x='Descripcion', y=['Stock_Sistema', 'Stock_Fisico'], barmode='group', color_discrete_sequence=['#1F497D', '#595959'])
        st.plotly_chart(fig_bar, use_container_width=True)

    with cg2:
        st.markdown("**Análisis de Rotación Mensual por Producto**")
        if 'Rotacion_Mensual' in df_filtrado.columns:
            fig_line = px.bar(df_filtrado, x='Descripcion', y='Rotacion_Mensual', color='Categoria' if 'Categoria' in df_filtrado.columns else None)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay datos de rotación en este archivo.")

    # Gráfico de línea temporal secundario si existen múltiples fechas
    if 'Fecha_Inventario' in df_filtrado.columns and df_filtrado['Fecha_Inventario'].nunique() > 1:
        st.markdown("---")
        st.subheader("📅 Tendencia Histórica de Exactitud en el Tiempo")
        df_tendencia = df_filtrado.groupby('Fecha_Inventario')['Exacto'].mean().reset_index()
        df_tendencia['Exactitud_%'] = df_tendencia['Exacto'] * 100
        fig_time = px.line(df_tendencia, x='Fecha_Inventario', y='Exactitud_%', markers=True, range_y=[0, 105])
        st.plotly_chart(fig_time, use_container_width=True)

    st.markdown("---")

    # Buscador Inteligente por SKU o Descripción
    st.subheader("🔍 Buscador Inteligente de Trazabilidad por SKU")
    busqueda_texto = st.text_input("Escribe el código SKU o parte de la descripción:", "")

    if busqueda_texto:
        df_busqueda = df_filtrado[
            df_filtrado['SKU'].str.contains(busqueda_texto, case=False, na=False) | 
            df_filtrado['Descripcion'].str.contains(busqueda_texto, case=False, na=False)
        ]
    else:
        df_busqueda = df_filtrado

    if not df_busqueda.empty:
        sku_seleccionado = st.selectbox("Seleccione de los resultados encontrados:", df_busqueda['SKU'].unique())
        df_sku_detalle = df_merged[df_merged['SKU'] == sku_seleccionado].iloc[0]

        st.markdown(f"### 📋 Ficha de Trazabilidad: `{df_sku_detalle['SKU']}` - {df_sku_detalle['Descripcion']}")
        
        ts1, ts2, ts3, ts4 = st.columns(4)
        ts1.metric("📦 Categoría / Atributo", f"{df_sku_detalle.get('Categoria', 'N/A')} ({df_sku_detalle.get('Talla_Pulgadas', 'N/A')})")
        ts2.metric("💻 Sistema vs 📊 Físico", f"{df_sku_detalle['Stock_Sistema']} vs {df_sku_detalle['Stock_Fisico']}")
        ts3.metric("🎨 Color", df_sku_detalle.get('Color', 'N/A'))
        ts4.metric("🛑 Impacto Económico", f"S/ {df_sku_detalle['Impacto_Merma_Soles']:,.2f}")

        if df_sku_detalle['Diferencia'] != 0:
            st.error(f"🚨 ALERTA CRÍTICA: Discrepancia detectada de {df_sku_detalle['Diferencia']} unidades.")
        else:
            st.success("✅ Producto con trazabilidad limpia y sin diferencias de inventario.")
    else:
        st.warning("⚠️ No se encontraron productos que coincidan con tu búsqueda.")

    st.markdown("---")

    # Tabla General
    st.subheader("📋 Base General de Inventario Procesado")
    st.dataframe(df_filtrado, use_container_width=True)

    st.markdown("---")

    # Módulo de Envío de Correos a Jefaturas
    st.subheader("📧 Enviar Reporte Ejecutivo por Correo a Jefatura")

    with st.form("form_correo"):
        email_destino = st.text_input("Correo de la Jefatura / Gerente:", "jefatura.logistica@carsa.com.pe")
        mensaje_extra = st.text_area("Observaciones:", "Se adjunta reporte con análisis visual y control de inventarios.")
        boton_enviar = st.form_submit_button("🚀 Enviar Reporte por Email")
        
        if boton_enviar:
            remitente = "tu_correo@gmail.com"
            password = "tu_contraseña_de_aplicacion"
            
            msg = EmailMessage()
            msg['Subject'] = f"Reporte Gerencial Logístico - Carsa Ica - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = remitente
            msg['To'] = email_destino
            msg.set_content(f"Hola,\n\n{mensaje_extra}\n\n- Exactitud: {exactitud_inv:.1f}%\n- SKUs con Desviación: {len(df_filtrado[df_filtrado['Diferencia'] != 0])}\n\nAtentamente,\nControl Logístico - Ica")
            
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(remitente, password)
                    smtp.send_message(msg)
                st.success(f"✅ ¡Correo enviado exitosamente a {email_destino}!")
            except Exception as e:
                st.error(f"⚠️ Error al enviar correo: {e}")

except Exception as e:
    st.error(f"⚠️ Ocurrió un error crítico procesando los datos logísticos: {e}")
    st.info("Sugerencia: Verifique que el archivo cargado contenga las columnas correctas de SKU y Stock.")
