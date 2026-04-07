# Sistema de Mensajería P2P Descentralizado (LAN)

### Autores: Esteban Guapacha, David Julian Torres y Kevin Esguerra

Una plataforma de comunicación **Peer-to-Peer (P2P)** de alto rendimiento para redes locales, ahora en su **versión 1.2.0**. Desarrollada en **Python**, combina una arquitectura asíncrona robusta con seguridad de nivel militar y soporte para intercambio de archivos.

---

## 🌟 Características Destacadas

- **Nodos Autónomos (P2P):** Eliminación total de servidores centrales; cada instancia actúa como cliente y servidor de forma simultánea.
- **Transferencia de Archivos (Nuevo en v1.2.0):** Soporte para el envío de archivos entre peers con verificación de integridad SHA-256 y control de flujo por chunks.
- **Seguridad End-to-End (E2EE):**
  - **Intercambio de Claves:** Diffie-Hellman sobre Curvas Elípticas (ECDH) usando SECP256R1.
  - **Cifrado de Mensajes:** AES-256-GCM para garantizar confidencialidad e integridad.
- **Interfaz Fluida y Reactiva:** UI nativa con **PySide6**, integrada con el event loop asíncrono mediante `qasync`.
- **Resiliencia de Conexión:** Monitoreo mediante **Heartbeats** para detección automática de desconexiones en tiempo real.
- **Persistencia Local Segura:** Historial de chat y contactos almacenados en una base de datos **SQLite** local.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Core** | Python 3.10+ | Lenguaje base |
| **Frontend** | PySide6 (Qt) | Interfaz gráfica y UX |
| **Network** | websockets + asyncio | Comunicación TCP asíncrona |
| **Bridge** | qasync | Integración Qt-Asyncio |
| **Security** | cryptography | ECC + AES-GCM (E2EE) |
| **Persistence** | SQLite3 | Base de datos local |

---

## 🏗️ Arquitectura del Sistema

El proyecto implementa una arquitectura modular de 4 capas para garantizar escalabilidad y mantenimiento simple:

1.  **Capa de Aplicación (UI):** Gestiona la presentación y eventos del usuario. Utiliza `@asyncSlot` para operaciones no bloqueantes.
2.  **Capa de Control (AppController):** Orquesta la comunicación entre la UI, la red y la persistencia. Gestiona el estado de las transferencias.
3.  **Capa de Comunicaciones (P2PNode):** Implementa el servidor/cliente WebSocket y maneja el protocolo de señalización.
4.  **Capa de Seguridad (CryptoSession):** Responsable de la derivación de claves por sesión y el cifrado/descifrado de payloads.

---

## 📂 Estructura del Proyecto

```text
modelo_P2P/
├── config/        # Configuraciones globales (puertos, versión, nombres)
├── controller/    # Lógica de negocio (AppController)
├── database/      # Modelos y controladores de SQLite (DBManager)
├── models/        # Entidades del dominio (Peer, Message, FileTransfer)
├── network/       # Implementación P2P, Protocolo y Handlers
├── ui/            # Layouts, estilos CSS y componentes visuales
├── utils/         # Helpers, validadores, logger y Criptografía
├── main.py        # Punto de entrada principal (Setup + App Loop)
└── requirements.txt
```

---

## ⚙️ Protocolo de Comunicación (JSON over WS)

El intercambio de datos sigue un flujo estrictamente tipado:

- **Handshake:** `HELLO` / `HELLO_ACK` (Intercambio de claves públicas ECC).
- **Mensajería:** `MESSAGE` / `MESSAGE_ACK` (Contenido cifrado AES).
- **Archivos:** `FILE_OFFER` -> `FILE_OFFER_ACK` -> Envío de Chunks binarios.
- **Control:** `HEARTBEAT` (Mantenimiento) y `DISCONNECT` (Cierre ordenado).

---

## 🚀 Instalación y Uso

### 1. Preparar el Entorno

Se recomienda el uso de un entorno virtual (`venv` o `conda`):

```bash
# Crear entorno virtual
python -m venv .venv

# Activar (Windows)
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Lanzar la Aplicación

```bash
python main.py
```

Al iniciar, se abrirá un diálogo de configuración donde deberás ingresar tu **Nickname** y el **Puerto Local** en el que deseas escuchar nuevas conexiones.

---

## 📈 Roadmap Técnico

- [ ] **Grupos (Discovery):** Escaneo automático de red local (mDNS/UDP Broadcast) para encontrar peers.
- [ ] **Avatar Dinámico:** Generación de identificadores visuales únicos basados en el ID del peer.
- [ ] **Búsqueda Global:** Indexación de mensajes antiguos para búsqueda rápida local.
- [ ] **Transferencias en Paralelo:** Soporte para múltiples transferencias simultáneas a diferentes peers.

---

<div align="center">
  <sub>Desarrollado para la asignatura de Sistemas Distribuidos.</sub>
</div>


