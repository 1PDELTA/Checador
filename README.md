# Checador facial

Sistema de asistencia automática con reconocimiento facial (Proyecto 1). Usa la cámara web para reconocer a las personas registradas con **DeepFace** y guarda la hora de llegada en un archivo CSV. Backend con **FastAPI** y una interfaz web sencilla.

## Cómo funciona

1. **Registrar persona:** se escribe un nombre y se toma su foto con la cámara. La foto se guarda en la carpeta `faces/`.
2. **Marcar asistencia:** se captura una imagen, DeepFace (modelo Facenet) la compara con las fotos de `faces/` y, si encuentra coincidencia, guarda nombre, fecha y hora en `asistencia.csv`. Cada persona se registra una sola vez por día.
3. **Modo automático:** revisa la cámara cada 4 segundos sin pulsar el botón.

## Requisitos

- Python 3.10 a 3.12
- Cámara web
- Conexión a internet en la primera ejecución (DeepFace descarga los pesos del modelo, unos 90 MB)

## Instalación y ejecución

```bash
# 1. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar el servidor
uvicorn main:app --reload
```

Abre **http://127.0.0.1:8000** en el navegador y permite el acceso a la cámara. La cámara solo funciona desde `localhost` o `127.0.0.1`.

## Uso

1. Escribe un nombre, mira de frente a la cámara y pulsa **Registrar con la cámara**.
2. Pulsa **Marcar asistencia** (o activa el modo automático). Aparece el nombre y la hora, y se agrega a la tabla "Asistencias de hoy".
3. El historial completo queda en `asistencia.csv`.

La primera vez que marques asistencia tarda más, porque DeepFace descarga el modelo y calcula los rostros registrados.

## Estructura

```
checador/
├── main.py              # API con FastAPI y lógica de DeepFace
├── templates/index.html # Interfaz web
├── faces/               # Fotos registradas (se crea sola)
├── asistencia.csv       # Registro de asistencia (se crea sola)
└── requirements.txt
```

## Privacidad

Las fotos y el registro de asistencia se guardan solo en tu computadora y están excluidos de Git (`.gitignore`). Registra únicamente a personas que hayan dado su consentimiento.
