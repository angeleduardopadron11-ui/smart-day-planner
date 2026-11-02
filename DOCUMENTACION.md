# 📖 Manual y Documentación Completa — Smart Day Planner

Sistema integral de planificación inteligente de 24 horas con agente conversacional, control por voz, persistencia SQLite, exportación PDF y despliegue multiplataforma.

---

## 📑 Tabla de Contenidos

1. [Despliegue en Vercel (Paso a Paso)](#1-despliegue-en-vercel-paso-a-paso)
2. [Documentación de Todas las Funciones del Sistema](#2-documentación-de-todas-las-funciones-del-sistema)
   - [Motor de Planificación Automática](#21-motor-de-planificación-automática-planner_enginepy)
   - [Agente Conversacional con NLP](#22-agente-conversacional-de-ia-agentpy)
   - [Sistema de Voz y Micrófono](#23-sistema-de-voz-y-micrófono)
   - [Interfaz de Usuario y Timeline](#24-interfaz-de-usuario-y-timeline)
   - [Generador de PDF Profesional](#25-generador-de-pdf-profesional-pdf_generatorpy)
   - [Base de Datos y Persistencia](#26-base-de-datos-sqlite-databasepy)
   - [Catálogo de Endpoints de la API REST](#27-catálogo-de-endpoints-api-rest)
3. [Guía de Descarga e Instalación en Cualquier Equipo](#3-guía-de-descarga-e-instalación-en-cualquier-equipo)
   - [Instalación en Windows](#31-instalación-en-windows)
   - [Instalación en Linux (Ubuntu/Debian/Arch)](#32-instalación-en-linux)
   - [Instalación en macOS](#33-instalación-en-macos)
   - [Acceso desde Móviles en Red Local (LAN)](#34-acceso-desde-el-celular-en-red-local-lan)
   - [Instalación con Docker (1 solo comando)](#35-instalación-con-docker)

---

## 1. Despliegue en Vercel (Paso a Paso)

El proyecto ya incluye la configuración optimizada para Vercel:
- `vercel.json`: Redirige todas las peticiones a la función Serverless.
- `api/index.py`: Punto de entrada ASGI compatible con la infraestructura de Vercel.
- `database.py`: Detecta el entorno Vercel y utiliza `/tmp/planner.db`.
- `.vercelignore`: Excluye entornos virtuales, bases de datos locales y temporales.

### Opción A: Despliegue mediante GitHub y Vercel Dashboard (Recomendado)

1. **Crear repositorio en GitHub**:
   - Ingresa a [github.com](https://github.com) y crea un nuevo repositorio (público o privado), por ejemplo: `smart-day-planner`.
2. **Subir el código desde tu equipo**:
   Abre una terminal en la carpeta del proyecto y ejecuta:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Smart Day Planner listo para Vercel"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/smart-day-planner.git
   git push -u origin main
   ```
3. **Importar en Vercel**:
   - Ingresa a [vercel.com](https://vercel.com) e inicia sesión con tu cuenta de GitHub.
   - Haz clic en **"Add New..."** → **"Project"**.
   - Selecciona el repositorio `smart-day-planner` y haz clic en **"Import"**.
   - En la sección **Framework Preset**, déjalo en **"Other"**.
   - Haz clic en **"Deploy"**.
4. **Listo**:
   En 1 a 2 minutos Vercel te entregará una URL pública segura (ej: `https://smart-day-planner.vercel.app`) para abrir la app desde cualquier celular, tablet o computadora.

---

### Opción B: Despliegue directo mediante Vercel CLI

Si tienes instalado Node.js en tu equipo:
```bash
# 1. Instalar Vercel CLI globalmente
npm i -g vercel

# 2. Iniciar sesión en Vercel
vercel login

# 3. Desplegar a producción
vercel --prod
```

> [!NOTE]
> **Sobre la persistencia en Vercel (Serverless vs Base de datos)**:
> Vercel es una plataforma de funciones Serverless (Edge / AWS Lambda). Las funciones se ejecutan en contenedores efímeros que se suspenden al no recibir tráfico. El sistema de archivos donde se crea `/tmp/planner.db` se reinicia en cada cold start.
> - Si deseas **persistencia 100% permanente multi-dispositivo en la nube**, puedes conectar [Turso](https://turso.tech) (Cloud SQLite gratis) o desplegar con 1 clic en [Render.com](https://render.com) o [Railway.app](https://railway.app), los cuales soportan discos persistentes nativos para SQLite.

---

## 2. Documentación de Todas las Funciones del Sistema

### 2.1. Motor de Planificación Automática (`planner_engine.py`)

El algoritmo genera un horario balanceado de **24 horas (1440 minutos)** a partir de las preferencias del usuario, sin solapamientos ni huecos vacíos.

#### Fases de Planificación:
1. **Fase 1 (Dormir matutino)**: Bloque de sueño desde las `00:00` hasta la hora de despertar (`wake_time`).
2. **Fase 2 (Rutina matutina)**: 30 minutos asignados inmediatamente tras despertar para aseo y preparación.
3. **Fase 3 (Desayuno)**: Comida matutina según la duración fijada en preferencias (por defecto 30 min).
4. **Fase 4 (Ejercicio matutino condicional)**: Si el ejercicio está activado y cabe antes del inicio laboral (`work_start`), se agenda en la mañana.
5. **Fase 5 (Tiempo personal pre-laboral)**: Si sobra tiempo antes de entrar a trabajar, se cubre con tiempo personal/café.
6. **Fase 6 (Jornada laboral y Almuerzo centrado)**: Divide la jornada laboral en dos bloques de trabajo y ubica el almuerzo en el punto medio de la jornada.
7. **Fase 7 (Actividades vespertinas)**:
   - Si el ejercicio no cupo en la mañana, se agenda tras terminar el trabajo.
   - Bloque de estudio/aprendizaje continuo de acuerdo con la duración configurada.
8. **Fase 8 (Tiempo libre y Cena)**: La cena se ubica automáticamente aproximadamente 2 horas antes de dormir para favorecer la digestión y el descanso nocturno.
9. **Fase 9 (Desconexión y Rutina nocturna)**: Ocio ligero (series, lectura) y 20 minutos de preparación antes de acostarse.
10. **Fase 10 (Dormir nocturno)**: Desde `sleep_time` hasta las `24:00` (`00:00`).

---

### 2.2. Agente Conversacional de IA (`agent.py`)

Permite gestionar todo el horario mediante lenguaje natural en español sin necesidad de llenar formularios.

#### Capacidades:
- **Parser de horas flexible**: Interpreta formatos como `15:00`, `3pm`, `3:30 pm`, `3 de la tarde`, `a las 10`, `mediodía` o `medianoche`.
- **Inferencia de categorías automática**:
  - `work` (Trabajo 💼): detecta *reunión, oficina, informe, cliente, proyecto, meeting*.
  - `exercise` (Ejercicio 💪): detecta *gym, gimnasio, correr, yoga, pesas, nadar, bici*.
  - `meal` (Comida 🍽️): detecta *desayuno, almuerzo, comer, cena, merienda, snack*.
  - `study` (Estudio 📚): detecta *estudiar, leer, curso, tarea, examen, libro*.
  - `personal` (Personal 👤): detecta *médico, compras, banco, trámite, cita*.
  - `free` (Tiempo libre 🎮): detecta *ocio, relax, series, pelis, jugar, salir*.
  - `routine` (Rutina 🔄): detecta *ducha, bañarse, vestirse, preparación*.
  - `sleep` (Dormir 🌙): detecta *dormir, siesta, descanso*.

#### Comandos soportados:
- **Agregar**: *"agrega llamada con equipo de 11 a 12"* o *"pon gym a las 7am por 1 hora"*.
- **Modificar**: *"mueve el estudio a las 18:00"* o *"cambia la cena de 20:30 a 21:15"*.
- **Eliminar**: *"elimina el almuerzo"* o *"quita el tiempo libre"*.
- **Consultar**: *"¿qué tengo a las 15:30?"* o *"¿qué me toca hoy?"*.
- **Preferencias**: *"me despierto a las 6:30 y duermo a las 23:30"*.
- **Generar**: *"genera mi horario"* o *"planifica mi día"*.
- **Exportar**: *"descarga el pdf"*.

---

### 2.3. Sistema de Voz y Micrófono

Diseñado con **arquitectura dual** para garantizar funcionamiento sin fallos en cualquier navegador:
1. **Grabación directa con `MediaRecorder`**: Captura audio local en el navegador (formato WebM/Opus) y lo envía al endpoint `/api/agent/voice`. El backend transcribe el audio y ejecuta la acción. Esto previene el clásico error de `network` que provocan Brave y Chromium al bloquear los servidores de Google.
2. **Web Speech API**: Reconocimiento en tiempo real como alternativa.
3. **Respuesta por Voz (Text-to-Speech)**: El asistente lee en voz alta sus confirmaciones con voz natural en español. Incluye botón para silenciar o activar en 1 clic.

---

### 2.4. Interfaz de Usuario y Timeline

- **Timeline interactivo**: Visualización cronológica vertical con indicadores circulares de colores según la categoría de la actividad.
- **Edición inline instantánea**: Clic en cualquier bloque para modificar hora, nombre o categoría en el lugar.
- **Navegación temporal**: Botones de día anterior/siguiente, selector de fecha nativo y botón *"Hoy"*.
- **Memoria de fechas**: Lista los días que ya tienen horarios guardados para consultar históricos.
- **Panel de preferencias**: Desplegable para configurar horarios de sueño, trabajo, comidas y duración de actividades.
- **Chips de 1 clic**: Botones en el chat para ejecutar acciones comunes al instante.

---

### 2.5. Generador de PDF Profesional (`pdf_generator.py`)

- Maquetación en hoja **A4** utilizando la biblioteca nativa `ReportLab`.
- Estilizado profesional con encabezado corporativo, fecha del horario y colores de fila diferenciados por categoría.
- Cálculo automático de duración de cada bloque (ej. `1h 30m`).
- Limpieza automática de emojis en el PDF para garantizar tipografía limpia y compatible.
- Descarga directa con el nombre estructurado: `horario_YYYY-MM-DD.pdf`.

---

### 2.6. Base de Datos SQLite (`database.py`)

- **Asíncrona**: Utiliza `aiosqlite` para no bloquear el bucle de eventos de FastAPI.
- **Modo WAL (`Write-Ahead Logging`)**: Permite lecturas concurrentes sin bloqueos.
- **Tablas**:
  - `preferences`: Almacena la configuración horaria y duraciones del usuario (JSON serializado).
  - `schedule_blocks`: Guarda cada bloque con fecha (`schedule_date`), horas de inicio/fin, título, categoría, descripción y orden de visualización.

---

### 2.7. Catálogo de Endpoints API REST

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Retorna la aplicación web completa (SPA) |
| `GET` | `/api/preferences` | Obtiene las preferencias horarias del usuario |
| `PUT` | `/api/preferences` | Guarda nuevas preferencias horarias |
| `GET` | `/api/schedule/{fecha}` | Obtiene todos los bloques de una fecha |
| `POST` | `/api/schedule/generate` | Genera y guarda automáticamente el horario de un día |
| `POST` | `/api/schedule/block` | Crea manualmente un nuevo bloque |
| `PUT` | `/api/schedule/block/{id}` | Actualiza campos de un bloque específico |
| `DELETE`| `/api/schedule/block/{id}` | Elimina un bloque por su ID |
| `GET` | `/api/dates` | Lista todas las fechas que tienen horarios guardados |
| `GET` | `/api/schedule/{fecha}/pdf` | Genera y descarga el archivo PDF del horario |
| `POST` | `/api/agent/chat` | Procesa comandos de texto con el agente inteligente |
| `POST` | `/api/agent/voice` | Recibe audio grabado por micrófono, transcribe y ejecuta |
| `GET` | `/docs` | Documentación interactiva Swagger UI |

---

## 3. Guía de Descarga e Instalación en Cualquier Equipo

### Requisitos Previos
- **Python 3.10 o superior** instalado ([python.org](https://www.python.org/downloads/)).
- **Git** (opcional, para clonar).

---

### 3.1. Instalación en Windows

1. Abre **PowerShell** o **Símbolo del sistema (CMD)**.
2. Clona o descarga el proyecto:
   ```powershell
   git clone https://github.com/TU_USUARIO/smart-day-planner.git
   cd smart-day-planner
   ```
3. Crea y activa el entorno virtual:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Instala las dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
5. Inicia el servidor:
   ```powershell
   python main.py
   ```
6. Abre tu navegador en: **http://localhost:8000**

---

### 3.2. Instalación en Linux

1. Abre la terminal:
   ```bash
   # Instalar dependencias del sistema (ffmpeg es opcional para procesar audios de voz)
   sudo apt update && sudo apt install -y python3 python3-venv python3-pip ffmpeg
   ```
2. Entra a la carpeta del proyecto:
   ```bash
   cd smart-day-planner
   ```
3. Crea y activa el entorno virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
5. Inicia la aplicación:
   ```bash
   python main.py
   ```
6. Abre tu navegador en: **http://localhost:8000**

---

### 3.3. Instalación en macOS

1. Abre la **Terminal**.
2. Si tienes Homebrew instalado (opcional para ffmpeg):
   ```bash
   brew install ffmpeg python
   ```
3. Entra a la carpeta del proyecto:
   ```bash
   cd smart-day-planner
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Inicia la aplicación:
   ```bash
   python main.py
   ```
5. Abre tu navegador en: **http://localhost:8000**

---

### 3.4. Acceso desde el Celular en Red Local (LAN)

Puedes usar la aplicación en tu celular o tablet sin necesidad de internet ni subirla a servidores externos:

1. Asegúrate de que tu computadora y tu celular estén conectados a la **misma red Wi-Fi**.
2. Inicia la app en tu PC con:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. Averigua la dirección IP local de tu computadora:
   - En Windows: escribe `ipconfig` en CMD (busca la IPv4, ej: `192.168.1.15`).
   - En Linux/Mac: escribe `hostname -I` o `ifconfig`.
4. En el navegador de tu celular (Chrome, Safari), ingresa a:
   `http://192.168.1.15:8000` *(reemplaza con la IP de tu PC)*.
5. Puedes agregar la página a la pantalla de inicio de tu celular ("Agregar a pantalla de inicio") para usarla como una app nativa.

---

### 3.5. Instalación con Docker

Si tienes Docker instalado en tu equipo, no necesitas configurar Python ni librerías:

```bash
# Construir y levantar el contenedor en segundo plano
docker compose up -d
```
La aplicación quedará disponible inmediatamente en **http://localhost:8000** y persistirá los datos en el archivo local `planner.db`.
