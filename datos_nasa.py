import requests
import pandas as pd
import matplotlib.pyplot as plt

# 1. URL y parámetros (aquí va tu token en "api_key")
url = "https://api.nasa.gov/neo/rest/v1/feed"
parametros = {
    "start_date": "2026-11-21",
    "end_date": "2026-11-27",
    "api_key": "DEMO_KEY",  # <-- Token oficial gratuito (o el tuyo de api.nasa.gov)
}

# 2. Petición idéntica a tu plantilla
respuesta = requests.get(url, params=parametros, timeout=30)
print(respuesta.status_code)          # 200 = salió bien
datos = respuesta.json()              # de texto JSON a diccionario

# 3. Aplanar el JSON de la NASA para convertirlo a tabla (DataFrame)
filas = []
for fecha, lista_asteroides in datos["near_earth_objects"].items():
    for ast in lista_asteroides:
        acercamiento = ast["close_approach_data"][0]
        diametro = ast["estimated_diameter"]["meters"]
        
        filas.append({
            "fecha": fecha,
            "nombre": ast["name"].strip("()"),
            "diametro_min_m": float(diametro["estimated_diameter_min"]),
            "diametro_max_m": float(diametro["estimated_diameter_max"]),
            "distancia_lunar": float(acercamiento["miss_distance"]["lunar"]),
            "velocidad_kms": float(acercamiento["relative_velocity"]["kilometers_per_second"]),
            "magnitud_h": float(ast["absolute_magnitude_h"]),
        })

df = pd.DataFrame(filas)              # de lista de diccionarios a tabla
df["diametro_prom_m"] = (df["diametro_min_m"] + df["diametro_max_m"]) / 2

# 4. Inspección igual que en tu código
print(df.shape)
print(df.head())
print(df.dtypes)
