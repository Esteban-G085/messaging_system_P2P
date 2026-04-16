# ◈ P2P Messenger (LAN)

### **Autores:** Esteban Guapacha, David Julian Torres y Kevin Esguerra

Una plataforma de comunicación **Peer-to-Peer (P2P)** de alto rendimiento diseñada para redes locales, actualmente en su **versión 1.3.3**. Este sistema combina una arquitectura asíncrona robusta con cifrado de extremo a extremo y capacidades avanzadas de videollamada, transferencia de archivos y mensajería.

> **v1.3.3** — Audio bidireccional funcional, optimización de video (320×240 @ 20 FPS) para reducir la competencia con el audio en el WebSocket compartido.

---

## 🌟 Características Principales

- **Descentralización Pura:** Sin servidores centrales. Cada nodo es autónomo, actuando como cliente y servidor simultáneamente.
- **Seguridad End-to-End (E2EE):**
  - **Intercambio de Claves:** Diffie-Hellman sobre Curvas Elípticas (ECDH - SECP256R1).
  - **Cifrado Real-Time:** AES-256-GCM para todos los datos: mensajes, archivos, video y audio.
- **Mensajería Instantánea:** Chat en tiempo real con historial persistente y notificaciones de entrega.
- **Videollamadas en Tiempo Real:**
  - Video H.264 (`libx264 ultrafast/zerolatency`) a 320×240 @ 20 FPS — optimizado para compartir el canal con el audio.
  - Audio PCM 16 kHz 16-bit mono bidireccional con baja latencia.
  - Transmisión completa sobre el WebSocket existente — sin WebRTC, sin ICE, sin STUN.
  - Detección automática de cámara entre múltiples dispositivos del sistema.
  - Señal de colgar bidireccional: ambos peers cierran la sesión limpiamente.
  - Resize explícito de frames si la cámara no respeta la resolución solicitada.
- **Transferencia de Archivos Optimizada:**
  - Envío de archivos de cualquier tamaño mediante fragmentación (chunking de 64 KB).
  - Verificación de integridad mediante **SHA-256**.
  - Control de flujo asíncrono para no bloquear la interfaz.
- **Interfaz Moderna (PySide6):** UI fluida integrada con `asyncio` mediante `qasync`.
  - Panel de peers con estado de conexión en tiempo real.
  - Diálogos nativos para llamadas entrantes con aceptar/rechazar.
  - Ventana flotante de video con controles de cámara, micrófono y colgar.
  - Widget de transferencia de archivos con barra de progreso.
- **Detección de Estado (Heartbeat):** Monitoreo constante de la salud de la conexión.
- **Persistencia Local:** Historial de conversaciones y gestión de contactos mediante **SQLite3**.

---

## 🆕 Cambios Recientes (v1.3.3)

- ✅ **Audio bidireccional:** Micrófono y altavoz funcionando en videollamadas.
- ✅ **Botón colgar funcional:** Termina la sesión local y notifica al peer remoto.
- ✅ **Arquitectura de videollamada simplificada:** Eliminado WebRTC/aiortc — video y audio viajan por el WebSocket del chat.
- ✅ **Optimización de video:** Resolución reducida a 320×240 @ 20 FPS — cada frame H.264 pesa ~75% menos, liberando el WebSocket para que el audio pase sin espera.
- ✅ **Event loop no bloqueante:** `cap.read()` y `stream.write()` movidos a `run_in_executor`.
- ✅ **Fix crítico de UI:** El widget de video ahora se agrega correctamente al layout.
- ✅ **Compatibilidad Windows mejorada:** Backend `CAP_DSHOW` para evitar errores de MSMF.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Función |
| :--- | :--- | :--- |
| **Lenguaje** | Python 3.10+ | Lógica de alto nivel y asincronía |
| **Interfaz** | PySide6 (Qt) | Motor gráfico y experiencia de usuario |
| **Network** | WebSockets + Asyncio | Transporte de mensajes, video y audio |
| **Criptografía** | Cryptography.io | ECDH + AES-256-GCM |
| **Video** | OpenCV + PyAV (libx264) | Captura y codificación H.264 |
| **Audio** | PyAudio (>=0.2.14) | Captura PCM y reproducción |
| **Base de Datos** | SQLite3 | Almacenamiento local ligero |
| **Integración** | qasync | Puente entre Qt y Asyncio |

---

## 🏗️ Arquitectura del Sistema

El sistema se divide en capas especializadas para maximizar la mantenibilidad:

1. **Capa de Presentación (UI):** Componentes Qt que reaccionan a eventos asíncronos sin congelar la ventana.
   - `main_window.py`: Ventana principal y coordinación de UI.
   - `widgets/`: Componentes especializados (chat, peers, video, transferencias, diálogos).
2. **Capa de Orquestación (Controller):** `AppController` gestiona el flujo de datos entre red, UI y base de datos.
3. **Capa de Red (Network):**
   - `node.py`: Gestor de peers y servidor WebSocket.
   - `protocol.py`: Protocolo de mensajería P2P.
   - `videocall.py`: Captura, codificación H.264 y streaming bidireccional de video/audio.
   - `message_handler.py`: Enrutador de mensajes entrantes.
   - `file_transfer.py`: Logística de transferencia de archivos por chunks.
4. **Capa de Persistencia (Database):** Historial de chats y contactos en SQLite.
5. **Capa de Seguridad (Crypto):** Generación de claves, ECDH y cifrado AES-256-GCM por sesión.

### Flujo de Videollamada

```
Peer A                                         Peer B
  │                                               │
  ├─ [WS] videocall_offer ──────────────────────>│
  │                              Muestra diálogo │
  │  [WS] videocall_answer <────────────────────<┤
  │                                               │
  ├═ Captura cámara (OpenCV CAP_DSHOW)            ╞═ Captura cámara
  ├═ Encode H.264 (libx264 ultrafast)             ╞═ Encode H.264
  ├─ [WS] video_frame (base64) ────────────────>│ Decode H.264 → UI
  │  [WS] video_frame (base64) <────────────────╡ ← lo mismo al revés
  │                                               │
  ├═ Captura micrófono (PyAudio 16 kHz)           ╞═ Captura micrófono
  ├─ [WS] audio_frame (base64 PCM) ────────────>│ Reproduce altavoz
  │  [WS] audio_frame (base64 PCM) <────────────╡
  │                                               │
  ├─ [WS] videocall_end ────────────────────────>│ Cierra sesión
  └═ Cierra sesión                                └═ Cierra ventana
```

Todo el tráfico viaja **cifrado con AES-256-GCM** sobre el WebSocket establecido en el handshake inicial.

---

## 📂 Estructura del Repositorio

```bash
messaging_system_P2P/
├── config/
│   └── settings.py            # Parámetros globales (puertos, timeouts, versión)
├── controller/
│   └── app_controller.py      # Orquestador principal
├── database/
│   ├── db_manager.py          # Gestor de BD
│   └── schema.sql             # Esquema SQLite
├── models/
│   ├── connection_state.py
│   ├── message.py
│   ├── peer.py
│   └── file_transfer.py
├── network/
│   ├── node.py                # Gestor de peers y servidor WebSocket
│   ├── protocol.py            # Protocolo de mensajería P2P
│   ├── server.py              # Servidor WebSocket
│   ├── client.py              # Cliente WebSocket
│   ├── message_handler.py     # Enrutador de mensajes
│   ├── videocall.py           # H.264 + PCM sobre WebSocket
│   └── file_transfer.py       # Transferencia de archivos por chunks
├── ui/
│   ├── main_window.py         # Ventana principal
│   ├── styles.py              # Estilos CSS globales
│   └── widgets/
│       ├── chat_view.py
│       ├── peers_list.py
│       ├── video_window.py        # Ventana de videollamada
│       ├── transfer_widget.py
│       ├── connection_panel.py
│       └── incoming_call_dialog.py
├── utils/
│   ├── crypto.py              # ECDH + AES-256-GCM
│   ├── helpers.py
│   ├── logger.py              # Logging centralizado
│   └── validators.py
├── main.py
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

---

## 🚀 Instalación y Guía de Uso

### 1. Requisitos Previos

- **Python 3.10+**
- **Cámara web** (para videollamadas)
- **Micrófono y altavoces** (para audio en videollamadas)
- **Windows / Linux / macOS**

### 2. Clonar y Configurar Entorno

```bash
# Crear el entorno virtual
python -m venv .venv

# Activar en Windows
.venv\Scripts\activate

# Activar en macOS/Linux
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Ejecución

```bash
python main.py
```

Al abrirse configura:
- **Nickname:** Tu identidad visible en la red (máx. 32 caracteres).
- **Puerto Local:** Puerto de escucha (default: 5000, rango: 1024–65535).

### 4. Uso de la Aplicación

#### 📱 Conectarse a un Peer
1. Ingresa la IP del peer en el panel de conexión.
2. Presiona **Conectar**.
3. Aguarda confirmación del handshake ECDH.

#### 💬 Enviar Mensajes
1. Selecciona un peer de la lista.
2. Escribe y presiona **Enter** o **Enviar**.
3. El mensaje se cifra con AES-256-GCM automáticamente.

#### 📹 Iniciar Videollamada
1. Selecciona un peer conectado y haz clic en el botón 📹.
2. El peer remoto verá un diálogo para aceptar o rechazar.
3. Al aceptar, ambos lados inician captura de cámara (320×240 @ 20 FPS) y micrófono (PCM 16 kHz).
4. Usa el botón **📞 Colgar** para terminar — ambos peers cierran la sesión.

#### 📂 Transferir Archivos
1. Haz clic en el botón 📎 o arrastra un archivo sobre el chat.
2. El receptor verá un diálogo para aceptar o rechazar.
3. Se muestra barra de progreso con verificación SHA-256 al finalizar.

#### 🔐 Seguridad
- Claves ECDH generadas por sesión, nunca persisten en disco.
- Todos los datos (mensajes, archivos, video, audio) cifrados con AES-256-GCM.
- Nonces únicos por mensaje — sin posibilidad de ataques de repetición.

---

## 🔒 Modelo de Seguridad

### Intercambio de Claves

```
Peer A                              Peer B
  │                                   │
  ├─ Genera clave privada ECDH ──────>│
  │  Envía clave pública A            │ Genera clave privada ECDH
  │<── Recibe clave pública B ────────┤
  │                                   │
  └─ Deriva secreto compartido ───────┘
       ↓                                   ↓
  AES-256-GCM key + nonces únicos (ambos lados)
```

### Garantías

| Propiedad | Estado |
|---|---|
| Confidencialidad (AES-256-GCM) | ✅ |
| Integridad (GCM auth tag + SHA-256) | ✅ |
| Sin replay (nonces únicos) | ✅ |
| Forward Secrecy (claves por sesión) | ✅ |
| Resistencia a MITM sin verificación manual | ⚠️ |

---

## 🐛 Solución de Problemas

### La cámara no funciona en Windows
- La app usa `CAP_DSHOW` (DirectShow) automáticamente.
- Si hay varias cámaras, prueba desconectar las secundarias.
- Verifica que ninguna otra app esté usando la cámara.

### No hay audio en videollamadas
- Verifica que el micrófono y altavoces no estén muteados en el SO.
- En Windows, comprueba permisos de micrófono en Configuración → Privacidad.
- Reinicia la app si los dispositivos de audio cambiaron.

### La conexión se cae
- Verifica conectividad (ping entre peers).
- Asegúrate de que el puerto no esté bloqueado por el firewall.
- Aumenta `HEARTBEAT_INTERVAL` en `config/settings.py` en redes lentas.

### Error al transferir archivos
- Verifica permisos de escritura en la carpeta de destino.
- Comprueba espacio disponible en disco.

---

## 📈 Roadmap

- [ ] **mDNS Discovery:** Detección automática de peers sin IP manual.
- [ ] **Grupos:** Salas de chat con intercambio de claves de grupo.
- [ ] **Emojis & Markdown:** Renderizado rico en el chat.
- [ ] **Compresión adaptativa:** Ajustar calidad de video según ancho de banda.
- [ ] **Sincronización de contactos:** Guardar favoritos localmente.

---

## 📖 Documentación

- [CHANGELOG](CHANGELOG.md) — Historial completo de versiones
- [README.md](README.md) — Este archivo

---

## 👥 Autores

- **Esteban Guapacha**
- **David Julian Torres**
- **Kevin Esguerra**

---

<div align="center">
  <sub>Sistemas Distribuidos — Universidad</sub>
</div>
