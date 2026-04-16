# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.3.3] - 2026-04-15

### Added
- **Audio bidireccional en videollamadas:** Captura de micrófono y reproducción por altavoz en tiempo real mediante PCM 16 kHz 16-bit mono sobre WebSocket.
- **Señal `videocall_end`:** Cuando un peer cuelga, el otro recibe notificación y la ventana de video se cierra automáticamente.
- **Botón "Colgar" funcional:** Conectado correctamente al controlador — termina la sesión local y notifica al peer remoto.
- **Callback `on_call_ended`:** La UI reacciona al cierre de llamada tanto por acción local como remota.
- **Detección automática de cámara:** `_find_camera()` itera hasta 3 índices para encontrar la primera cámara disponible.
- **Reset automático de `VideoCallWS`:** Después de cada llamada el objeto se reinicia limpiamente para la siguiente.
- **Constantes de video centralizadas:** `VIDEO_WIDTH`, `VIDEO_HEIGHT` y `VIDEO_FPS` en la cabecera de `videocall.py` para facilitar ajustes futuros.
- **Resize explícito de frames:** Si la cámara no respeta la resolución solicitada vía `set()`, se aplica `cv2.resize()` antes de encodear.

### Changed
- **Motor de videollamadas migrado completamente de WebRTC/aiortc a WebSocket + H.264:**
  - Eliminados: `aiortc`, `RTCPeerConnection`, `RTCSessionDescription`, `RTCIceCandidate`, ICE, STUN.
  - El video H.264 y el audio PCM viajan cifrados por el mismo WebSocket del chat.
- **Resolución de video reducida de 640×480 a 320×240:** Reduce los píxeles por frame en un 75%, lo que disminuye el tamaño de cada packet H.264 de ~50–200 KB a ~10–50 KB.
- **FPS reducido de 30 a 20:** Combinado con la reducción de resolución, libera el WebSocket con mayor frecuencia para que los chunks de audio (1 KB) pasen sin espera apreciable.
- **`time_base` y GOP del encoder actualizados a `VIDEO_FPS`:** El encoder H.264 queda consistente con la tasa de captura real.
- **`cap.read()` ahora no bloquea el event loop:** Movido a `run_in_executor` para mantener la UI fluida.
- **`stream.write()` de PyAudio movido a `run_in_executor`:** La reproducción de audio ya no bloquea el event loop.
- **Tasa de audio reducida de 44.1 kHz a 16 kHz:** Suficiente para voz, reduce ancho de banda de ~5.6 Mbps a ~512 Kbps.
- **Cola de audio reducida de 50 a 20 items:** Máximo ~640 ms de buffer; si se llena, descarta el frame más viejo en lugar de bloquear.
- **Conversión BGR→RGB movida a `videocall.py`:** `video_window.py` recibe RGB listo — sin dependencia de OpenCV en la capa UI.
- **`video_label` correctamente agregado al layout:** Corregido bug crítico por el que el widget de video nunca aparecía en pantalla.
- **Backend de cámara forzado a `CAP_DSHOW` en Windows:** Evita errores de MSMF (`can't grab frame`).
- **`app_controller.py` simplificado:** `start_videocall`, `accept_videocall`, `reject_videocall` y `handle_incoming_videocall_message` reescritos sin código muerto de WebRTC.
- **`node.py`:** Tipos `audio_frame` y `videocall_end` añadidos al dispatcher de mensajes de videollamada.

### Removed
- Dependencia `aiortc` eliminada del stack de videollamadas.
- `signaling.py` ya no se usa — la señalización viaja como mensajes JSON cifrados por WebSocket.
- Flag `_videocall_in_progress` eliminado — ya no era necesario con la nueva arquitectura.

### Fixed
- La ventana de videollamada ya no se queda en blanco al recibir video.
- ICE en estado `checking` permanente eliminado (causa raíz: se abandonó WebRTC).
- El audio remoto ya no se escucha distorsionado por overflow del buffer de PyAudio.
- `AttributeError: module 'websockets.asyncio' has no attribute 'ensure_future'` resuelto usando `asyncio.get_event_loop().create_task()`.

---

## [1.3.2] - 2026-04-12

### Added
- Versión actualizada de PyAudio con especificación explícita de versión mínima

### Changed
- **Dependencias:**
  - `pyaudio` → `pyaudio>=0.2.14` para mejorar compatibilidad con sistemas modernos
  - Todos los archivos compilados de Python (`.pyc`) regenerados con optimizaciones

### Fixed
- Mejor manejo de dispositivos de audio en sistemas con múltiples interfaces
- Resolución de conflictos en merge de repositorio
- Dependencias verificadas y pintadas en requirements.txt

---

## [1.3.1] - 2026-04-10

### Added
- Sistema de logging avanzado con archivos rotatorios
- Mejor detección de estado de peers
- Soporte completo para videollamadas con H.264

### Changed
- Migración a arquitectura completamente asíncrona con `asyncio`

---

## [1.1.0] - 2026-03-15

### Added
- Interfaz gráfica con PySide6
- Mensajería instantánea cifrada (AES-256-GCM)
- Descubrimiento básico de peers en LAN

### Changed
- Protocolo P2P mejorado con handshake ECDH

---

## [1.0.0] - 2026-03-01

### Added
- Versión inicial del sistema P2P
- Comunicación básica entre peers
- Cifrado end-to-end (E2EE)
- Intercambio de claves ECDH

---
