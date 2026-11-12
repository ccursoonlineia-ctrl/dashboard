import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Centro de incidencias UNIOVI",
    page_icon="🛠️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7fb;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .dashboard-header {
        padding: 1.6rem 1.8rem;
        margin-bottom: 1.2rem;
        color: #ffffff;
        border-radius: 16px;
        background: linear-gradient(115deg, #173b65 0%, #2563a6 100%);
    }
    .dashboard-header h1 {
        margin: 0 0 .35rem 0;
        font-size: 2rem;
    }
    .dashboard-header p {
        margin: 0;
        color: #dceaff;
        font-size: 1rem;
    }
    div[data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid #e5eaf2;
        border-radius: 12px;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(27, 52, 82, .04);
    }
    div[data-testid="stMetricLabel"] {
        color: #52657c;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

datos = pd.read_csv("incidencias.csv")
columnas_requeridas = {"fecha", "nombre", "categoria", "titulo", "estado"}
faltantes = columnas_requeridas.difference(datos.columns)
if faltantes:
    st.error(f"Faltan columnas necesarias en incidencias.csv: {', '.join(sorted(faltantes))}")
    st.stop()

datos["fecha"] = pd.to_datetime(datos["fecha"], errors="coerce")
datos["estado"] = datos["estado"].fillna("Sin estado")
datos["categoria"] = datos["categoria"].fillna("Sin categoría")

st.markdown(
    """
    <div class="dashboard-header">
        <h1>Centro de incidencias</h1>
        <p>Resumen operativo y seguimiento de los avisos del servicio técnico.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

fechas_validas = datos["fecha"].dropna()
if fechas_validas.empty:
    st.warning("No hay fechas válidas para mostrar incidencias.")
    st.stop()

fecha_minima = fechas_validas.min().date()
fecha_maxima = fechas_validas.max().date()
categorias = sorted(datos["categoria"].unique().tolist())
estados = sorted(datos["estado"].unique().tolist())

with st.sidebar:
    st.header("Filtros")
    rango_fechas = st.date_input(
        "Periodo",
        value=(fecha_minima, fecha_maxima),
        min_value=fecha_minima,
        max_value=fecha_maxima,
        format="DD/MM/YYYY",
    )
    categorias_seleccionadas = st.multiselect(
        "Categoría",
        options=categorias,
        default=categorias,
    )
    estados_seleccionados = st.multiselect(
        "Estado",
        options=estados,
        default=estados,
    )
    busqueda = st.text_input("Buscar", placeholder="Nombre, título o categoría…")

filtradas = datos.copy()
if isinstance(rango_fechas, tuple):
    inicio, fin = rango_fechas
    if inicio is not None:
        filtradas = filtradas[filtradas["fecha"].dt.date >= inicio]
    if fin is not None:
        filtradas = filtradas[filtradas["fecha"].dt.date <= fin]
filtradas = filtradas[
    filtradas["categoria"].isin(categorias_seleccionadas)
    & filtradas["estado"].isin(estados_seleccionados)
]
if busqueda.strip():
    campos_busqueda = filtradas[["nombre", "titulo", "categoria", "estado"]].fillna("")
    coincide = campos_busqueda.astype(str).apply(
        lambda columna: columna.str.contains(
            busqueda.strip(), case=False, na=False, regex=False
        )
    ).any(axis=1)
    filtradas = filtradas[coincide]

total = len(filtradas)
estados_normalizados = filtradas["estado"].astype(str).str.strip().str.casefold()
resueltas = int(estados_normalizados.isin(["resuelto", "cerrado"]).sum())
activas = int((~estados_normalizados.isin(["resuelto", "cerrado", "cancelado"])).sum())
tasa_resolucion = (resueltas / total * 100) if total else 0

st.subheader("Resumen")
metrica_1, metrica_2, metrica_3, metrica_4 = st.columns(4)
metrica_1.metric("Incidencias", f"{total:,}")
metrica_2.metric("Pendientes / en curso", f"{activas:,}")
metrica_3.metric("Resueltas", f"{resueltas:,}")
metrica_4.metric("Tasa de resolución", f"{tasa_resolucion:.0f}%")

st.subheader("Análisis")
col_tendencia, col_categorias = st.columns((1.3, 1))

with col_tendencia:
    st.markdown("#### Evolución diaria")
    if total:
        tendencia = (
            filtradas.dropna(subset=["fecha"])
            .set_index("fecha")
            .resample("D")
            .size()
            .rename("Incidencias")
        )
        st.line_chart(tendencia, width="stretch")
    else:
        st.info("No hay incidencias para el periodo y los filtros seleccionados.")

with col_categorias:
    st.markdown("#### Por categoría")
    if total:
        por_categoria = (
            filtradas["categoria"]
            .value_counts()
            .rename_axis("Categoría")
            .rename("Incidencias")
        )
        st.bar_chart(por_categoria, width="stretch")
    else:
        st.info("Sin datos para mostrar.")

col_estado, col_detalle = st.columns((1, 1.3))
with col_estado:
    st.markdown("#### Por estado")
    if total:
        por_estado = (
            filtradas["estado"]
            .value_counts()
            .rename_axis("Estado")
            .rename("Incidencias")
        )
        st.bar_chart(por_estado, width="stretch")
    else:
        st.info("Sin datos para mostrar.")

with col_detalle:
    st.markdown("#### Incidencias recientes")
    recientes = filtradas.sort_values("fecha", ascending=False).head(5)
    if recientes.empty:
        st.info("No hay incidencias que coincidan con los filtros.")
    else:
        st.dataframe(
            recientes[["fecha", "titulo", "estado"]],
            hide_index=True,
            width="stretch",
            column_config={
                "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "titulo": st.column_config.TextColumn("Incidencia", width="large"),
                "estado": st.column_config.TextColumn("Estado"),
            },
        )

st.subheader("Listado de incidencias")
if filtradas.empty:
    st.info("Prueba a cambiar los filtros para ver resultados.")
else:
    listado = filtradas.sort_values("fecha", ascending=False).rename(
        columns={
            "fecha": "Fecha",
            "nombre": "Solicitante",
            "categoria": "Categoría",
            "titulo": "Incidencia",
            "estado": "Estado",
        }
    )
    st.dataframe(
        listado,
        hide_index=True,
        width="stretch",
        column_config={
            "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "Solicitante": st.column_config.TextColumn("Solicitante"),
            "Categoría": st.column_config.TextColumn("Categoría"),
            "Incidencia": st.column_config.TextColumn("Incidencia", width="large"),
            "Estado": st.column_config.TextColumn("Estado"),
        },
    )

with st.expander("Registrar una incidencia"):
    with st.form("aviso"):
        nombre = st.text_input("Nombre")
        categoria = st.selectbox("Categoría", options=sorted(set(categorias + ["Otro"])))
        titulo = st.text_input("Título de la incidencia")
        descripcion = st.text_area("Descripción del problema")
        enviado = st.form_submit_button("Enviar aviso", type="primary")

    if enviado:
        if not nombre or not titulo or not descripcion:
            st.error("Por favor, completa el nombre, el título y la descripción.")
        else:
            st.success("Aviso enviado correctamente.")
            st.write("Solicitante:", nombre)
            st.write("Categoría:", categoria)
            st.write("Incidencia:", titulo)
            st.write("Descripción:", descripcion)
