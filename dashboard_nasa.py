# Tablero de Asteroides Cercanos a la Tierra (NASA NeoWs), con token
# Herramientas de Visualización · IDIA22X · Parcial III
#
#     pip install streamlit requests pandas matplotlib seaborn
#     streamlit run dashboard_nasa.py

import os
from datetime import date, datetime, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
import streamlit as st

# ─── Paleta del curso ──────────────────────────────────────────────────
GRIS = "#B9C3D1"
AZUL = "#1C4C9A"
ROJO = "#B2182B"
AZUL_POS = "#2166AC"
CUALI = ["#E69F00", "#56B4E9", "#009E73", "#0072B2"]
sns.set_theme(style="whitegrid")

NEOWS = "https://api.nasa.gov/neo/rest/v1/feed"

st.set_page_config(page_title="Tablero NASA NeoWs", layout="wide")


# ─── El token ──────────────────────────────────────────────────────────
def leer_token():
    try:
        if "nasa_token" in st.secrets:
            return str(st.secrets["nasa_token"]).strip()
    except Exception:
        pass
    if os.environ.get("NASA_TOKEN"):
        return os.environ["NASA_TOKEN"].strip()
    return None


TOKEN = leer_token()

if TOKEN and TOKEN != "DEMO_KEY" and len(TOKEN) < 32:
    st.error(
        f"El token tiene {len(TOKEN)} caracteres y deberían ser 40. "
        "Revisa que esté completo y sin comillas extra."
    )
    st.stop()

if not TOKEN:
    st.error("Falta el token de la NASA.")
    st.markdown(
        "1. Pídelo gratis en https://api.nasa.gov/ (sección *Generate API Key*)\n"
        "2. Crea la carpeta `.streamlit` junto a este archivo.\n"
        "3. Dentro, un archivo `secrets.toml` con la línea:\n"
        '   `nasa_token = "tu-token-de-40-caracteres"`\n'
        "4. Vuelve a cargar esta página."
    )
    st.stop()


# ─── La consulta ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def consultar(inicio, fin, token):
    parametros = {
        "start_date": inicio,
        "end_date": fin,
        "api_key": token,
    }
    respuesta = requests.get(
        NEOWS,
        params=parametros,
        headers={
            "Accept": "application/json",
            "User-Agent": "UPQ-IDIA224/1.0",
        },
        timeout=60,
    )

    if respuesta.status_code in (401, 403):
        raise PermissionError("El token de la NASA no fue aceptado o falta.")
    if respuesta.status_code == 429:
        raise PermissionError("Demasiadas peticiones (límite alcanzado). Espera un momento.")
    respuesta.raise_for_status()

    tipo = respuesta.headers.get("Content-Type") or ""
    if "json" not in tipo:
        raise ValueError(
            f"El servidor no devolvió JSON sino {tipo}. "
            "Suele ser un problema con el token o los parámetros."
        )

    datos = respuesta.json()
    objetos = datos.get("near_earth_objects", {})

    filas = []
    for fecha_str, lista_asteroides in objetos.items():
        for ast in lista_asteroides:
            if not ast.get("close_approach_data"):
                continue
            acercamiento = ast["close_approach_data"][0]
            diametro = ast["estimated_diameter"]["meters"]

            d_min = float(diametro["estimated_diameter_min"])
            d_max = float(diametro["estimated_diameter_max"])

            filas.append({
                "Fecha": pd.to_datetime(fecha_str),
                "Nombre": ast["name"].strip("()"),
                "Diametro_Min_m": d_min,
                "Diametro_Max_m": d_max,
                "Diametro_Prom_m": (d_min + d_max) / 2,
                "Distancia_LD": float(acercamiento["miss_distance"]["lunar"]),
                "Distancia_km": float(acercamiento["miss_distance"]["kilometers"]),
                "Velocidad_kms": float(
                    acercamiento["relative_velocity"]["kilometers_per_second"]
                ),
                "Magnitud_H": float(ast["absolute_magnitude_h"]),
                "Peligroso": "Peligroso"
                if ast["is_potentially_hazardous_asteroid"]
                else "No peligroso",
            })

    if not filas:
        raise ValueError("La NASA no devolvió asteroides en ese rango de fechas.")

    return pd.DataFrame(filas).sort_values("Fecha").reset_index(drop=True)


# ─── Controles ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Qué consultar")
    inicio = st.date_input("Desde", date(2026, 11, 21))
    fin = st.date_input(
        "Hasta (máx. 7 días)",
        value=inicio + timedelta(days=6),
        min_value=inicio,
        max_value=inicio + timedelta(days=7),
    )
    solo_peligrosos = st.checkbox("Mostrar solo potencialmente peligrosos", value=False)
    vel_min = st.slider("Velocidad mínima (km/s)", 0.0, 35.0, 0.0, step=0.5)
    st.caption("Fuente: Near Earth Object Web Service (NASA)")

if inicio > fin:
    st.error("La fecha inicial debe ser anterior o igual a la final.")
    st.stop()

with st.spinner("Consultando la API de la NASA..."):
    try:
        df = consultar(str(inicio), str(fin), TOKEN)
    except PermissionError as e:
        st.error(str(e))
        st.stop()
    except ValueError as e:
        st.warning(str(e))
        st.stop()
    except requests.exceptions.RequestException as e:
        st.error(f"No se pudo consultar la NASA: {e}")
        st.stop()

limpio = df[df["Velocidad_kms"] >= vel_min].copy()
if solo_peligrosos:
    limpio = limpio[limpio["Peligroso"] == "Peligroso"]

if limpio.empty:
    st.warning("Ningún asteroide cumple con los filtros seleccionados.")
    st.stop()


# ─── Encabezado e indicadores ──────────────────────────────────────────
st.title("Tablero de Asteroides Cercanos a la Tierra")
st.caption(
    f"NASA NeoWs · del {inicio} al {fin} · "
    f"consultado el {datetime.now():%d/%m/%Y %H:%M}"
)

mas_cercano = limpio.loc[limpio["Distancia_LD"].idxmin()]
mas_grande = limpio.loc[limpio["Diametro_Max_m"].idxmax()]
peligrosos_n = int((limpio["Peligroso"] == "Peligroso").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Asteroides detectados", len(limpio), delta=f"{peligrosos_n} peligrosos")
c2.metric(
    "Mayor diámetro estimado",
    f"{mas_grande['Diametro_Max_m']:,.1f} m",
    delta=mas_grande["Nombre"],
    delta_color="off",
)
c3.metric(
    "Acercamiento más próximo",
    f"{mas_cercano['Distancia_LD']:,.2f} LD",
    delta=mas_cercano["Nombre"],
    delta_color="off",
)
c4.metric(
    "Rango de velocidad",
    f"{limpio['Velocidad_kms'].min():,.1f} – {limpio['Velocidad_kms'].max():,.1f} km/s",
)

st.divider()


# ─── Gráficas ──────────────────────────────────────────────────────────
izquierda, derecha = st.columns(2)

with izquierda:
    st.subheader("Acercamientos por fecha")
    por_dia = (
        limpio.groupby(["Fecha", "Peligroso"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["No peligroso", "Peligroso"], fill_value=0)
    )
    etiquetas_fecha = por_dia.index.strftime("%d/%m")

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(etiquetas_fecha, por_dia["No peligroso"], color=AZUL, label="No peligroso")
    ax.bar(
        etiquetas_fecha,
        por_dia["Peligroso"],
        bottom=por_dia["No peligroso"],
        color=ROJO,
        label="Potencialmente peligroso",
    )
    ax.set_xlabel("Fecha de máxima aproximación")
    ax.set_ylabel("Cantidad de asteroides")
    ax.legend(frameon=False)
    st.pyplot(fig)
    st.caption(
        "Barras apiladas por clasificación de riesgo de la NASA. "
        "Rojo indica objetos que cumplen criterios de órbita cercana y tamaño."
    )

with derecha:
    st.subheader("Top 8 por diámetro máximo estimado")
    top8 = limpio.sort_values("Diametro_Max_m", ascending=True).tail(8)
    colores_top = [
        ROJO if p == "Peligroso" else AZUL_POS for p in top8["Peligroso"]
    ]

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.barh(top8["Nombre"], top8["Diametro_Max_m"], color=colores_top)
    ax.set_xlabel("Diámetro máximo estimado (metros)")
    ax.set_ylabel("Designación")
    st.pyplot(fig)
    st.caption(
        "Comparación de magnitud física entre los objetos mayores del periodo. "
        "Azul: órbita sin riesgo inmediato; Rojo: potencialmente peligroso."
    )

abajo_izq, abajo_der = st.columns(2)

with abajo_izq:
    st.subheader("Distancia mínima vs. velocidad relativa")
    fig, ax = plt.subplots(figsize=(6, 3.4))

    for estado, color in [("No peligroso", CUALI[3]), ("Peligroso", ROJO)]:
        sub = limpio[limpio["Peligroso"] == estado]
        if sub.empty:
            continue
        ax.scatter(
            sub["Distancia_LD"],
            sub["Velocidad_kms"],
            s=sub["Diametro_Prom_m"] * 3.5,
            color=color,
            alpha=0.8,
            edgecolors="white",
            linewidth=0.8,
            label=estado,
        )

    ax.axvline(1.0, color="gray", linestyle="--", linewidth=0.9)
    ax.set_xlabel("Distancia mínima (Distancias Lunares · 1 LD ≈ 384,400 km)")
    ax.set_ylabel("Velocidad relativa (km/s)")
    ax.legend(frameon=False)
    st.pyplot(fig)
    st.caption(
        "El tamaño de cada punto es proporcional al diámetro promedio (m). "
        "La línea punteada marca la órbita de la Luna (1 LD)."
    )

with abajo_der:
    st.subheader("Distribución de velocidades relativas")
    media_vel = limpio["Velocidad_kms"].mean()

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.hist(
        limpio["Velocidad_kms"],
        bins=7,
        color=CUALI[1],
        edgecolor="white",
        alpha=0.9,
    )
    ax.axvline(
        media_vel,
        color=ROJO,
        linestyle="--",
        linewidth=1.8,
        label=f"Media: {media_vel:.1f} km/s",
    )
    ax.set_xlabel("Velocidad relativa (km/s)")
    ax.set_ylabel("Frecuencia (asteroides)")
    ax.legend(frameon=False)
    st.pyplot(fig)
    st.caption(
        "Histograma de velocidades de paso respecto a la Tierra; "
        "la línea roja punteada señala el promedio del periodo."
    )


# ─── Datos ─────────────────────────────────────────────────────────────
with st.expander("Ver y descargar los datos"):
    st.write(f"Registros mostrados: {len(limpio)} de {len(df)} totales.")
    st.dataframe(limpio, use_container_width=True)
    st.download_button(
        "Descargar CSV",
        limpio.to_csv(index=False).encode("utf-8"),
        file_name=f"nasa_neows_{inicio}_{fin}.csv",
        mime="text/csv",
    )