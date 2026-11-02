# 🧠 Smart Day Planner — Asistente Inteligente de 24 Horas

Aplicación web integral para la planificación automática y personalizada de las 24 horas del día con agente conversacional de Inteligencia Artificial en español, dictado y respuesta por voz, edición interactiva, persistencia en SQLite y descarga de horario en PDF.

---

## 🚀 Despliegue en Vercel

El proyecto está preparado para desplegarse directamente en Vercel con arquitectura Serverless:

1. Sube este proyecto a tu repositorio de **GitHub**.
2. Ingresa a [Vercel.com](https://vercel.com) y selecciona **Add New Project**.
3. Importa el repositorio y haz clic en **Deploy**.
4. ¡Listo! Vercel te dará un enlace público HTTPS para usar la app desde cualquier dispositivo móvil o computadora.

> 📖 Consulta la [Guía Detallada de Despliegue y Funciones](DOCUMENTACION.md) para ver la guía paso a paso y opciones de persistencia en la nube.

---

## 💻 Ejecución Rápida en Cualquier Equipo

### Requisitos: Python 3.10+

```bash
# 1. Clonar o entrar a la carpeta
cd smart-planner

# 2. Crear y activar entorno virtual
python -m venv .venv

# En Linux / macOS:
source .venv/bin/activate
# En Windows (PowerShell):
# .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar la aplicación
python main.py
```
Abre en tu navegador: **http://localhost:8000**

### O con Docker (1 solo comando):
```bash
docker compose up -d
```

---

## ✨ Características Principales

| Módulo | Descripción |
|---|---|
| **Motor de Planificación 24h** | Algoritmo inteligente en 10 fases que calcula sueño, comidas, trabajo, estudio, ejercicio y tiempo libre sin huecos ni solapamientos. |
| **Agente de IA en Español** | Interpreta órdenes en lenguaje natural: *"agrega reunión de 10 a 11"*, *"elimina el almuerzo"*, *"mueve el estudio a las 6pm"*, *"¿qué tengo hoy?"*. |
| **Micrófono y Respuestas por Voz** | Grabación de audio directa con `MediaRecorder` para evitar fallos de red en el navegador + lectura de respuestas por voz (Text-to-Speech). |
| **Edición en Línea** | Clic en cualquier bloque del timeline para editar en vivo su título, horas o categoría. |
| **Exportación a PDF** | Generación nativa con `ReportLab` de tu agenda de 24 horas maquetada con código de colores por categoría. |
| **Base de Datos SQLite Asíncrona** | Archivo único `planner.db` con `aiosqlite`, modo WAL y cero dependencias de servidores externos. |

---

## 📚 Documentación Completa

Para una explicación exhaustiva de cada función matemática, el algoritmo en 10 fases, la arquitectura del agente y la instalación en Windows/Mac/Linux, revisa:
👉 **[DOCUMENTACION.md](DOCUMENTACION.md)**
