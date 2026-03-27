# Sistema de Mensajería P2P con PySide y WebSockets

---

## 1. Descripción del sistema

Se desarrollará una aplicación de mensajería **peer-to-peer (P2P)** en Python, donde cada usuario:

- Actúa como cliente y servidor al mismo tiempo  
- Se conecta directamente con otros usuarios en red **LAN**
- Intercambia mensajes en tiempo real con confirmación de entrega
- No depende de un servidor central  
- Mantiene historial de mensajes persistente

La aplicación contará con una interfaz gráfica minimalista, enfocada en facilidad de uso con feedback visual de estado.

---

## 2. Tecnologías del sistema

### Interfaz gráfica
- PySide6 

### Concurrencia 
- `qasync` - Integra asyncio con Qt event loop
- `asyncio` - Manejo asincrónico

### Comunicación en red
- WebSockets (`websockets`)
- asyncio para I/O no bloqueante

### Formato de datos
- JSON

### Persistencia
- SQLite - Historial de mensajes y peers

---

## 3. Arquitectura del sistema

Modelo en capas con separación clara de responsabilidades:

```
┌─────────────────────────────────┐
│   Interfaz Gráfica (PySide)     │
│   - Mostrar chats                │
│   - Capturar eventos usuario     │
│   - Feedback de estado           │
└────────────┬──────────────────────┘
             │
┌────────────▼──────────────────────┐
│   Controlador (App Controller)    │
│   - Orquestar capas               │
│   - Pasar eventos entre capas     │
│   - Manejar sincronización        │
└────────────┬──────────────────────┘
             │
┌────────────▼──────────────────────┐
│   Red P2P (WebSockets + asyncio)  │
│   - Servidor WebSocket            │
│   - Cliente WebSocket             │
│   - Protocolo de comunicación     │
│   - Manejo de conexiones          │
└────────────┬──────────────────────┘
             │
┌────────────▼──────────────────────┐
│   Persistencia (SQLite)           │
│   - Historial de mensajes         │
│   - Datos de peers conocidos      │
└─────────────────────────────────┘
```

### Principios 

-  La interfaz **NO maneja la red directamente**
-  El controlador es el único punto de sincronización
-  La red corre en asyncio (thread-safe con qasync)
-  ser no-bloqueante

---

## 4. Modelo P2P 

Cada nodo del sistema:

- Abre un servidor WebSocket en puerto especificado
- Puede conectarse a múltiples peers simultáneamente
- Mantiene una lista de peers conectados con estado
- Implementa re-intentos automáticos ante fallos
- Detecta desconexiones con heartbeat

### Estados de conexión

```
IDLE → CONNECTING → CONNECTED ↔ AUTHENTICATING ↔ READY
                    ↓
                   ERROR (con re-intentos)
                    ↓
                 DISCONNECTING → IDLE
```

### Flujo general 

1. Usuario inicia la aplicación
2. Define username y puerto local
3. Se levanta el servidor WebSocket (escucha conexiones)
4. Usuario ingresa IP y puerto de destino (peer remoto)
5. **Sistema valida** IP:puerto
6. **Sistema intenta conectar** (con re-intentos)
7. Se intercambian datos de identificación (HELLO)
8. **Peers se autentican mutuamente**
9. Se registran en lista de contactos
10. Se habilita el envío/recepción de mensajes
11. Se mantiene heartbeat para detectar desconexiones

---

## 5. Identidad de usuarios

Cada nodo genera:

```python
import uuid

username = "usuario"
peer_id = str(uuid.uuid4())  # Identificador único persistente
port = 5000  # Puerto local
local_ip = "192.168.1.10"  # IP local (detectada)
```

### Estructura de un peer

```python
Peer = {
    "id": str,              # UUID único
    "username": str,        # Nombre de usuario
    "ip": str,              # Dirección IP
    "port": int,            # Puerto escucha
    "state": str,           # CONNECTING, CONNECTED, ERROR
    "last_seen": datetime,  # Última actividad
    "connection": WebSocket # Conexión WebSocket (si está conectado)
}
```

---

## 6. Conexión entre usuarios (LAN)

### Método utilizado

Conexión manual mediante:
- Dirección IP (validada como formato IPv4)
- Puerto (validado entre 1024-65535)
- Re-intentos automáticos (máx. 3)
- Timeout de conexión: 5 segundos

### Validación de entrada

```python
def validar_conexion(ip: str, puerto: int) -> bool:
    # Validar formato IP
    if not es_ip_valida(ip):
        return False
    
    # Validar rango de puerto
    if not (1024 <= puerto <= 65535):
        return False
    
    # No conectar a localhost del mismo dispositivo
    if ip == "127.0.0.1":
        return False
    
    return True
```


## 7. Protocolo de comunicación 

Todos los mensajes se envían en formato JSON. Incluye:
- Tipo de mensaje
- ID del mensaje (para ACK)
- Timestamp
- Datos

### Tipos de mensajes

```
HELLO           - Inicio de sesión y presentación
HELLO_ACK       - Confirmación de HELLO
MESSAGE         - Mensaje de chat
MESSAGE_ACK     - Confirmación de entrega
HEARTBEAT       - Mantener conexión viva
DISCONNECT      - Desconexión ordenada
ERROR           - Notificación de error
```

---

### HELLO (inicio de conexión)

```json
{
  "type": "HELLO",
  "msg_id": "a1b2c3d4-e5f6-7890",
  "timestamp": "2026-03-26T10:30:45.123Z",
  "data": {
    "username": "usuario",
    "peer_id": "550e8400-e29b-41d4-a716-446655440000",
    "port": 5000
  }
}
```

---

### HELLO_ACK (confirmación de HELLO)

```json
{
  "type": "HELLO_ACK",
  "msg_id": "b2c3d4e5-f678-9012",
  "timestamp": "2026-03-26T10:30:46.000Z",
  "data": {
    "status": "accepted",
    "peer_id": "660f9511-f3ac-52e5-b8g7-557766551111"
  }
}
```

---

### MESSAGE (mensaje de chat)

```json
{
  "type": "MESSAGE",
  "msg_id": "c3d4e5f6-7890-1234",
  "timestamp": "2026-03-26T10:30:50.500Z",
  "data": {
    "sender": "usuario",
    "sender_id": "550e8400-e29b-41d4-a716-446655440000",
    "content": "hola, ¿cómo estás?"
  }
}
```

---

### MESSAGE_ACK (confirmación de entrega)

```json
{
  "type": "MESSAGE_ACK",
  "msg_id": "d4e5f678-9012-5678",
  "timestamp": "2026-03-26T10:30:50.800Z",
  "data": {
    "original_msg_id": "c3d4e5f6-7890-1234",
    "status": "delivered"
  }
}
```

---

### HEARTBEAT (mantener viva la conexión)

```json
{
  "type": "HEARTBEAT",
  "msg_id": "e5f67890-1234-9abc",
  "timestamp": "2026-03-26T10:30:55.000Z",
  "data": {
    "peer_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

### DISCONNECT (desconexión ordenada)

```json
{
  "type": "DISCONNECT",
  "msg_id": "f6789012-3456-bcde",
  "timestamp": "2026-03-26T10:31:00.000Z",
  "data": {
    "reason": "user_logout"
  }
}
```

---

## 8. Flujo de comunicación mejorado

### Conexión exitosa

```
Peer A (Cliente)          Peer B (Servidor)
    │                           │
    ├──── HELLO ───────────────→ │
    │                           │
    │                           ├─ Validar
    │                           │
    │ ←────── HELLO_ACK ────────┤
    │                           │
    ├──── MESSAGE ACK ─────────→ │
    │                           │
    │                    (READY) │
    ├──── HEARTBEAT (cada 30s)─→ │
    │                           │
```

---

### Envío de mensaje

```
Usuario         Interfaz      Controlador      Red          Peer Remoto
  │                │              │            │              │
  ├─Escribe msg.──→│              │            │              │
  │                ├─Envía a──────→│           │              │
  │                │              ├─Envía────→│              │
  │                │              │           ├─MESSAGE─────→│
  │                │              │           │              ├─Procesa
  │                │              │           ←─MESSAGE_ACK──┤
  │                │              ←─ACK───────┤              │
  │ ←─Confirmado──┬┤              │           │              │
  │                │              │           │              │
```

---

### Manejo de desconexión no ordenada

```
Peer A              Peer B
   │                  │
   ├─ HEARTBEAT ──→ │
   │                  │ (procesa)
   ├─ HEARTBEAT ──→ │
   │                  │ (procesa)
   ├─ HEARTBEAT ──→ │
   │                  │ (sin respuesta)
   │                  │ (timeout: 10s)
   │                  │
   ├─ HEARTBEAT ──→ │ (conexión cerrada)
   │                  ✗ ERROR
   │              
  (Detecta ausencia)
   │
   └─ Re-intentar conexión (máx 3)
```

---

## 9. Diseño de la interfaz 

### Estilo visual

- Fondo: #121212  
- Panel: #1E1E1E  
- Texto: #FFFFFF
- Accent (estados): #00FF88 (conectado), #FF6B6B (error), #FFB800 (conectando)
- Diseño minimalista  
- Fuente: Segoe UI, 10pt

---

### Layout 

```
╔═════════════════════════════════════════╗
║ Peers Conectados                        ║
╠═════════════════════════════════════════╣
║ ● usuario1          (conectado)         ║
║ ○ usuario2          (desconectado)      ║
║ ⟳ usuario3          (conectando...)     ║
╠═════════════════════════════════════════╣
║ Chat con: usuario1                      ║
╠═════════════════════════════════════════╣
║ [10:30] usuario1: hola                  ║
║ [10:31] Yo: ¡hola! ✓✓                   ║
║ [10:32] usuario1: ¿cómo estás?          ║
║ [10:33] Yo: bien, ¿y tú?                ║
╠═════════════════════════════════════════╣
║ [ escribe tu mensaje...          ]      ║
║                            [Enviar] [+] ║
╠═════════════════════════════════════════╣
║ Conectar a nuevo peer                   ║
║ IP:   [192.168.1.   ] Puerto: [5000]    ║
║                                [Conectar]║
║ Estado: ● Escuchando en 192.168.1.5:5001║
╚═════════════════════════════════════════╝
```

## 10. Manejo de concurrencia

### Problema

- PySide usa su propio event loop de Qt
- WebSockets y asyncio usan event loop de asyncio
- No pueden coexistir sin adaptor

### Solución: qasync

Usa la librería `qasync` que integra asyncio con Qt:

```python
from qasync import QEventLoop, asyncSlot
from PySide6.QtWidgets import QApplication

# Event loop único que maneja ambos
app = QApplication([])
loop = QEventLoop(app)
asyncio.set_event_loop(loop)

# Ahora puedes usar async/await en Qt
@asyncSlot()
async def conectar_a_peer():
    await red.conectar(ip, puerto)
```

### Implementación

```
┌─ QApplication ──────────────────┐
│  ┌─ QEventLoop (qasync) ───────┐│
│  │  ┌─ asyncio tasks ────────┐││
│  │  │  - WebSocket server    │││
│  │  │  - WebSocket clients   │││
│  │  │  - Handlers de eventos │││
│  │  │  - Timers (heartbeat)  │││
│  │  └────────────────────────┘││
│  │  ┌─ Qt signals/slots ─────┐││
│  │  │  - UI updates          │││
│  │  └────────────────────────┘││
│  └──────────────────────────────┘│
└──────────────────────────────────┘
```

---

## 11. Persistencia  (SQLite)

### Tablas de base de datos

#### Tabla: peers
```sql
CREATE TABLE peers (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    ip TEXT,
    port INTEGER,
    last_connected DATETIME,
    is_favorite BOOLEAN DEFAULT 0
);
```

#### Tabla: messages
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL,
    receiver_id TEXT,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_delivered BOOLEAN DEFAULT 0,
    is_read BOOLEAN DEFAULT 0,
    FOREIGN KEY(sender_id) REFERENCES peers(id)
);
```

#### Tabla: connection_log
```sql
CREATE TABLE connection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_id TEXT,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(peer_id) REFERENCES peers(id)
);
```

### Características

- Historial de mensajes persistente
- Registro de conexiones
- Peers favoritos
- Recuperar estado ante reinicio

---

## 12. Detección de desconexión y re-intentos

### Heartbeat

- **Intervalo**: 30 segundos
- **Timeout**: 10 segundos
- **Re-intentos**: 3 (después se marca como desconectado)

### Lógica de re-intentos

```
Intento 1 ─→ Falla
  ↓
Esperar 2s
  ↓
Intento 2 ─→ Falla
  ↓
Esperar 5s
  ↓
Intento 3 ─→ Falla
  ↓
Marcar como ERROR
Notificar usuario
```

---

## 13. Estructura del proyecto 

```
p2p-chat/
│
├── main.py                  # Entrada de la aplicación
│
├── requirements.txt         # Dependencias
│
├── config/
│   └── settings.py          # Configuración global
│
├── models/
│   ├── peer.py              # Modelo Peer
│   ├── message.py           # Modelo Message
│   └── connection_state.py  # Estados de conexión (Enum)
│
├── ui/
│   ├── main_window.py       # Ventana principal
│   ├── styles.py            # Estilos CSS
│   └── widgets/
│       ├── peers_list.py    # Lista de peers
│       ├── chat_view.py     # Vista de chat
│       └── connection_panel.py  # Panel de conexión
│
├── controller/
│   └── app_controller.py    # Controlador principal
│
├── network/
│   ├── protocol.py          # Protocolo JSON
│   ├── node.py              # Nodo P2P (orquestador)
│   ├── server.py            # Servidor WebSocket
│   ├── client.py            # Cliente WebSocket
│   └── message_handler.py   # Procesamiento de mensajes
│
├── database/
│   ├── db_manager.py        # Gestor SQLite
│   └── schema.sql           # Esquema de BD
│
└── utils/
    ├── logger.py            # Logging
    ├── validators.py        # Validación (IP, puerto, etc)
    └── helpers.py           # Funciones auxiliares
```

---

## 14. Funcionalidades 

### Fase 1: Core
-  Crear usuario (username + puerto)  
-  Iniciar servidor WebSocket  
-  Validar conexión (IP:puerto)
-  Conectarse a otro peer
-  Protocolo HELLO/HELLO_ACK
-  Visualizar peers conectados con estado

### Fase 2: Mensajería
-  Enviar mensajes
-  Recibir mensajes
-  Confirmación de entrega (ACK)
-  Mostrar estado del mensaje (⚪ enviado, ✓ entregado, ✓✓ leído)

### Fase 3: Robustez
-  Heartbeat y detección de desconexión
-  Re-intentos automáticos
-  Historial en SQLite
-  Logging de actividad

### Fase 4: Polish (futuro)
-  Múltiples chats simultáneos
-  Notificaciones
-  Buscar en historial
-  Exportar chat
-  seguridad (encriptación, autenticación)

---

## 15. Decisiones de diseño aclaradas

### ¿Múltiples conexiones simultáneas?
**SÍ**. Un usuario puede chatear con varios peers a la vez.
- Cada peer tiene su propia conexión WebSocket
- El servidor maneja múltiples clientes simultáneamente
- El controlador distribuye mensajes según el destinatario

### ¿Encriptación?
**NO en MVP**. La red es local (LAN) y académica.
- En futuro: agregar `wss://` (WebSocket Secure) + SSL/TLS
- Certificados autofirmados para desarrollo

### ¿Autenticación?
**Básica en MVP**: solo username y peer_id.
- En futuro: agregar contraseña con hash (bcrypt)
- Sistema de permisos si es necesario

### ¿Timeout de conexión?
**5 segundos** para conexión inicial.
**10 segundos** para heartbeat.
**3 re-intentos** antes de marcar como error.

---

## 16. Características clave del sistema final

-  Arquitectura distribuida P2P
-  Sin servidor central
-  Interfaz gráfica minimalista con feedback visual
-  Comunicación en tiempo real con confirmación
-  Uso de tecnologías modernas (PySide6 + WebSockets + qasync)
-  Histórico persistente en SQLite
-  Manejo robusto de errores y desconexiones
-  Re-intentos automáticos
-  Detección de peers inactivos con heartbeat
-  Validación de entrada
-  Logging y debugging
-  Escalable a múltiples conexiones simultáneas

---

## 17. Dependencias requeridas

```
PySide6>=6.4.0
websockets>=11.0
qasync>=0.27.0
asyncio (incluido en Python 3.10+)
sqlite3 (incluido en Python)
```

---

## 18. Próximos pasos

1. **Crear estructura base** del proyecto
2. **Implementar modelos** (Peer, Message, ConnectionState)
3. **Desarrollar capa de red** (protocol, server, client, node)
4. **Crear interfaz básica** con PySide6
5. **Integrar con qasync**
6. **Pruebas en LAN** con múltiples dispositivos
7. **Agregar persistencia** SQLite
8. **Optimización y pulido** final

---

**Documento actualizado**: 26 de Marzo 2026
**Contexto**: Proyecto académico - Red LAN