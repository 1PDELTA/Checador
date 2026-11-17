import os
import re
import csv
import time
import base64
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from deepface import DeepFace

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, "faces")           # fotos de personas registradas
TEMP_DIR = os.path.join(BASE_DIR, "data", "temp")     # capturas temporales
CSV_PATH = os.path.join(BASE_DIR, "asistencia.csv")   # registro de asistencia
INDEX_PATH = os.path.join(BASE_DIR, "templates", "index.html")

MODELO = "Facenet"      # modelo ligero (~90 MB)
DETECTOR = "opencv"     # detector de rostros rápido

os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

app = FastAPI(title="Checador facial", description="Asistencia automática con DeepFace")


class Captura(BaseModel):
    image: str


class Registro(BaseModel):
    nombre: str
    image: str


def guardar_imagen(b64: str, ruta: str):
    """Decodifica una imagen base64 (con o sin encabezado DataURL) y la guarda."""
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    try:
        datos = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="La imagen no es un Base64 válido.")
    with open(ruta, "wb") as f:
        f.write(datos)


def borrar_cache_deepface():
    """DeepFace guarda un .pkl con los rostros; se borra al registrar a alguien nuevo."""
    for archivo in os.listdir(FACES_DIR):
        if archivo.endswith(".pkl"):
            os.remove(os.path.join(FACES_DIR, archivo))


def leer_asistencia_hoy():
    if not os.path.exists(CSV_PATH):
        return []
    hoy = datetime.now().strftime("%Y-%m-%d")
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["fecha"] == hoy]


def registrar_asistencia(nombre: str):
    """Guarda la asistencia una sola vez por día. Devuelve (es_nuevo, hora)."""
    for r in leer_asistencia_hoy():
        if r["nombre"] == nombre:
            return False, r["hora"]
    ahora = datetime.now()
    existe = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not existe:
            w.writerow(["nombre", "fecha", "hora"])
        w.writerow([nombre, ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S")])
    return True, ahora.strftime("%H:%M:%S")


@app.get("/", response_class=HTMLResponse)
def inicio():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/registrar")
def registrar(datos: Registro):
    """Guarda la foto de una persona en faces/ para poder reconocerla después."""
    nombre = re.sub(r"[^A-Za-z0-9ÁÉÍÓÚáéíóúÑñ ]", "", datos.nombre).strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Escribe un nombre válido.")
    ruta = os.path.join(FACES_DIR, nombre.replace(" ", "_") + ".jpg")
    guardar_imagen(datos.image, ruta)
    try:
        DeepFace.extract_faces(img_path=ruta, detector_backend=DETECTOR, enforce_detection=True)
    except Exception:
        os.remove(ruta)
        raise HTTPException(
            status_code=422,
            detail="No se detectó un rostro. Mira de frente a la cámara con buena luz e inténtalo de nuevo.",
        )
    borrar_cache_deepface()
    return {"mensaje": f"{nombre} quedó registrado."}


@app.post("/api/checar")
def checar(captura: Captura):
    """Busca el rostro de la cámara entre los registrados y marca la asistencia."""
    hay_rostros = any(a.lower().endswith((".jpg", ".jpeg", ".png")) for a in os.listdir(FACES_DIR))
    if not hay_rostros:
        raise HTTPException(status_code=400, detail="Aún no hay personas registradas.")

    ruta = os.path.join(TEMP_DIR, f"cap_{int(time.time() * 1000)}.jpg")
    guardar_imagen(captura.image, ruta)
    try:
        resultados = DeepFace.find(
            img_path=ruta,
            db_path=FACES_DIR,
            model_name=MODELO,
            detector_backend=DETECTOR,
            enforce_detection=True,
            silent=True,
        )
    except Exception as e:
        if "Face could not be detected" in str(e):
            raise HTTPException(status_code=422, detail="No se detectó ningún rostro.")
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {e}")
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)

    if not resultados or resultados[0].empty:
        return {"reconocido": False, "mensaje": "Rostro no reconocido."}

    mejor = resultados[0].sort_values("distance").iloc[0]
    archivo = os.path.splitext(os.path.basename(mejor["identity"]))[0]
    nombre = archivo.replace("_", " ")
    es_nuevo, hora = registrar_asistencia(nombre)
    return {"reconocido": True, "nombre": nombre, "nuevo": es_nuevo, "hora": hora}


@app.get("/api/asistencia")
def asistencia():
    """Lista las asistencias de hoy."""
    return leer_asistencia_hoy()
