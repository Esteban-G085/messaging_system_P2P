# ◈ P2P Messenger (LAN)

### **Autores:** Esteban Guapacha, David Julian Torres y Kevin Esguerra

Una plataforma de comunicación **Peer-to-Peer (P2P)** de alto rendimiento diseñada para redes locales, actualmente en su **versión 1.3.2**. Este sistema combina una arquitectura asíncrona robusta con cifrado y capacidades avanzadas de transferencia de archivos.

---

## 🌟 Características Principales

- **Descentralización Pura:** Sin servidores centrales. Cada nodo es autónomo, actuando como cliente y servidor simultáneamente.
- **Seguridad End-to-End (E2EE):**
  - **Intercambio de Claves:** Implementación de Diffie-Hellman sobre Curvas Elípticas (ECDH - SECP256R1).
  - **Cifrado Real-Time:** AES-256-GCM para asegurar que solo los participantes puedan leer los mensajes.
- **Mensajería Instantánea:** Chat en tiempo real con historial persistente y notificaciones.
- **Videollamadas en Tiempo Real:**
  - Captura de cámara con resolución de hasta 640x480 @ 30 FPS.
  - Compresión H.264 con opciones de velocidad ultra-baja (ultrafast) para minimizar latencia.
  - Transmisión bidireccional de video sobre WebSocket existente.
  - Soporte para múltiples cámaras del sistema.
- **Transferencia de Archivos Optimizada:**
  - Envío de archivos de cualquier tamaño mediante fragmentación (chunking).
  - Verificación de integridad mediante **SHA-256**.
  - Control de flujo asíncrono para no bloquear la interfaz.
- **Audio (PyAudio):** Captura y transmisión de audio en tiempo real.
- **Interfaz Moderna (PySide6):** UI fluida diseñada con paradigmas modernos, integrada totalmente con `asyncio` mediante `qasync`.
  - Panel de peers con estado de conexión.
  - Diálogos nativos para llamadas entrantes.
  - Widget de transferencia de archivos con barra de progreso.
  - Ventana flotante de video.
- **Detección de Estado (Heartbeat):** Monitoreo constante de la salud de la conexión para detectar desconexiones abruptas en milisegundos.
- **Persistencia Local:** Historial de conversaciones y gestión de contactos mediante **SQLite3**.

---

## � Cambios Recientes (v1.3.2)

- ✅ **Actualización de Dependencias:** Se actualizó `pyaudio >= 0.2.14` para mejorar compatibilidad con sistemas modernos.
- ✅ **Mejoras de Audio:** Soporte mejorado para captura y transmisión de audio con mejor manejo de dispositivos.
- ✅ **Limpieza de Logs:** Gestión automática de archivos de log (logs antiguos se reemplazan con nuevos).

---

## �🛠️ Stack Tecnológico

| Componente | Tecnología | Función |
| :--- | :--- | :--- |
| **Lenguaje** | Python 3.10+ | Lógica de alto nivel y asincronía |
| **Interfaz** | PySide6 (Qt) | Motor gráfico y experiencia de usuario |
| **Network** | WebSockets + Asyncio | Protocolo de transporte bidireccional |
| **Criptografía** | Cryptography.io | Implementación de estándares de seguridad |
| **Video** | OpenCV + PyAV + aiortc | Captura, codificación H.264 y streaming de video |
| **Audio** | PyAudio (>=0.2.14) | Captura y transmisión de audio |
| **Base de Datos** | SQLite3 | Almacenamiento local ligero |
| **Integración** | qasync | Puente entre el loop de Qt y Asyncio |

---

## 🏗️ Arquitectura del Sistema

El sistema se divide en capas especializadas para maximizar la mantenibilidad:

1. **Capa de Presentación (UI):** Componentes basados en Qt que reaccionan a eventos asíncronos sin congelar la ventana.
   - `main_window.py`: Ventana principal.
   - `widgets/`: Componentes especializados (chat, lista de peers, video, transferencias).
2. **Capa de Orquestación (Controller):** El `AppController` gestiona el flujo de datos entre la red, la interfaz y la base de datos.
3. **Capa de Red (Network):**
   - `node.py`: Gestor de peers y servidor WebSocket.
   - `protocol.py`: Protocolo de mensajería P2P.
   - `videocall.py`: Captura y streaming de video H.264.
   - `message_handler.py`: Enrutador de mensajes entrantes.
4. **Capa de Persistencia (Database):** Almacenamiento de historial de chats y contactos.
5. **Capa de Seguridad (Crypto):** Gestiona la generación de secretos, derivación de claves y cifrado simétrico/asimétrico.

---

## 📂 Estructura del Repositorio

```bash
messaging_system_P2P/
├── config/        # Parámetros globales (puertos, timeouts, versión)
│   └── settings.py        # Configuración centralizada
├── controller/    # Orquestador principal
│   └── app_controller.py  # Lógica central de orquestación
├── database/      # Persistencia y modelos SQL
│   ├── db_manager.py      # Gestor de BD
│   └── schema.sql         # Esquema de BD (mensajes, contactos)
├── models/        # Estructuras de datos
│   ├── connection_state.py    # Estados de conexión
│   ├── message.py             # Modelo de mensaje
│   ├── peer.py                # Modelo de peer
│   └── file_transfer.py       # Modelo de transferencia
├── network/       # Implementación del protocolo P2P
│   ├── node.py            # Gestor de peers y servidor WebSocket
│   ├── protocol.py        # Protocolo de mensajería
│   ├── server.py          # Servidor WebSocket
│   ├── client.py          # Cliente WebSocket
│   ├── message_handler.py # Enrutador de mensajes
│   ├── videocall.py       # Captura y streaming H.264
│   ├── file_transfer.py   # Logística de transferencia de archivos
│   └── signaling.py       # Señalización de conexiones
├── ui/            # Interfaz gráfica (PySide6)
│   ├── main_window.py     # Ventana principal
│   ├── styles.py          # Estilos CSS globales
│   └── widgets/           # Componentes reutilizables
│       ├── chat_view.py          # Vista de chat
│       ├── peers_list.py         # Lista de peers
│       ├── video_window.py       # Ventana de video
│       ├── transfer_widget.py    # Widget de transferencia
│       ├── connection_panel.py   # Panel de conexión
│       └── incoming_call_dialog.py # Diálogo de llamada entrante
├── utils/         # Utilidades
│   ├── crypto.py      # Criptografía (ECDH, AES-256-GCM)
│   ├── helpers.py     # Funciones auxiliares
│   ├── logger.py      # Sistema de logging
│   └── validators.py  # Validaciones de entrada
├── main.py            # Punto de entrada de la aplicación
├── requirements.txt   # Dependencias del proyecto
└── README.md          # Este archivo
```

---

## 🚀 Instalación y Guía de Uso

### 1. Requisitos Previos

- **Python 3.10+**
- **Cámara web** (para videollamadas)
- **Micrófono** (para audio en tiempo real)
- **Windows/Linux/Mac**

### 2. Clonar y Configurar Entorno

Se recomienda usar un entorno virtual para mantener las dependencias aisladas:

```bash
# Crear el entorno
python -m venv .venv

# Activar en Windows
.venv\Scripts\activate

# Activar en macOS/Linux
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Ejecución

Inicia la aplicación ejecutando el script principal:

```bash
python main.py
```

Al abrirse, deberás configurar:

- **Nickname:** Tu identidad visible en la red (máx. 32 caracteres).
- **Puerto Local:** El puerto por donde escucharás nuevas conexiones (default: 5000, rango: 1024-65535).

### 4. Uso de la Aplicación

#### 📱 Conectarse a un Peer
1. Ingresa la IP del peer en el panel de conexión.
2. Presiona **Conectar**.
3. Aguarda confirmación (con heartbeat automático).

#### 💬 Enviar Mensajes
1. Selecciona un peer de la lista.
2. Escribe tu mensaje en el campo de texto.
3. Presiona **Enter** o **Enviar**.
4. El mensaje se cifra automáticamente (AES-256-GCM) antes de transmitirse.

#### 📹 Iniciar Videollamada
1. Haz clic derecho en un peer conectado.
2. Selecciona **Iniciar Videollamada**.
3. La cámara se enciende automáticamente (resolución: 640x480 @ 30 FPS).
4. La llamada se termina automáticamente si la conexión se pierde.

#### 📂 Transferir Archivos
1. Arrastra un archivo sobre la ventana de chat.
2. El archivo se fragmenta y se envía con verificación SHA-256.
3. Se muestra una barra de progreso en tiempo real.

#### 🔐 Seguridad
- Las claves se intercambian automáticamente mediante **ECDH** al conectar.
- Todos los mensajes, archivos y video se cifran con **AES-256-GCM**.
- Las claves se regeneran por sesión (no persisten en disco).

---

---

## 🔒 Modelo de Seguridad Detallado

### Intercambio de Claves (Key Exchange)

```
Peer A                              Peer B
  │                                   │
  ├─ Genera privada ECDH (secp256r1) │
  ├─ Envía pública A ───────────────>│
  │                    Genera privada│
  │  Recibe pública B │ Envía pública│
  │<─────────────────<────────────────┤
  │                                   │
  └─ Calcula secreto compartido (ECDH)
                                     └─ Calcula secreto compartido
  
Ambos derivan: clave AES-256 | nonces únicos
```

### Cifrado en Tránsito

- **Mensajes:** AES-256-GCM con autenticación
- **Archivos:** Fragmentos de 64KB cifrados + SHA-256 por chunk
- **Video:** Frames H.264 comprimidos + cifrados
- **Cada sesión:** Pares de claves diferentes por peer

### Garantías de Seguridad

✅ **Confidencialidad:** Solo emisor y receptor leen contenido.  
✅ **Integridad:** SHA-256 verifica archivos; GCM autentifica mensajes.  
✅ **Sin reproducción:** Nonces únicos + timestamps en protocolo.  
✅ **Forward Secrecy:** Claves por sesión, no reutilizadas.  
⚠️ **No previene:** Análisis de tráfico, ataques MITM sin verificación manual.

---

## 🐛 Solución de Problemas

### La cámara no funciona
- Verifica permisos de acceso a hardware.
- Intenta conectar otra aplicación a la cámara.
- Reinicia la aplicación.

### La conexión se cae
- Verifica conectividad de red (ping a peer).
- Aumenta `HEARTBEAT_INTERVAL` en [config/settings.py](config/settings.py) si es lenta.
- Asegúrate de abrir el puerto en firewall.

### Error al transferir archivos
- Verifica permisos de escritura en la carpeta.
- Comprueba espacio en disco disponible.
- Intenta con un archivo más pequeño.

### Los logs no aparecen
- Revisa [utils/logger.py](utils/logger.py) para cambiar nivel de logging.
- Por defecto se registra en `p2p_chat.log`.

---

## 📈 Próximos Pasos (Roadmap)

- [ ] **mDNS Discovery:** Detección automática de peers en la misma subred sin necesidad de IP manual.
- [ ] **Soporte de Grupos:** Creación de salas de chat grupales con intercambio de llaves de grupo.
- [ ] **Emojis & Markdown:** Soporte para renderizado rico de mensajes.
- [ ] **Audio bidireccional:** Sistema de audio de baja latencia.
- [ ] **Compresión adaptativa:** Ajustar calidad de video según ancho de banda.
- [ ] **Sincronización de contactos:** Guardar favoritos en la nube (opcional).

---

## � Documentación

- [CHANGELOG](CHANGELOG.md) - Historial de cambios y versiones
- [README.md](README.md) - Este archivo (guía principal)

---

## �👥 Contribuciones

Este proyecto es desarrollado como parte del curso de **Sistemas Distribuidos**.

### Autores
- **Esteban Guapacha**
- **David Julian Torres**
- **Kevin Esguerra**

---

<div align="center">
  <sub>Sistemas Distribuidos - Universidad</sub>
</div>
