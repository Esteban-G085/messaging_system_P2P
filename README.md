# ◈ P2P Messenger (LAN)

### **Autores:** Esteban Guapacha, David Julian Torres y Kevin Esguerra

Una plataforma de comunicación **Peer-to-Peer (P2P)** de alto rendimiento diseñada para redes locales, actualmente en su **versión 1.2.2**. Este sistema combina una arquitectura asíncrona robusta con cifrado y capacidades avanzadas de transferencia de archivos.

---

## 🌟 Características Principales

- **Descentralización Pura:** Sin servidores centrales. Cada nodo es autónomo, actuando como cliente y servidor simultáneamente.
- **Seguridad End-to-End (E2EE):**
  - **Intercambio de Claves:** Implementación de Diffie-Hellman sobre Curvas Elípticas (ECDH - SECP256R1).
  - **Cifrado Real-Time:** AES-256-GCM para asegurar que solo los participantes puedan leer los mensajes.
- **Transferencia de Archivos Optimizada:**
  - Envío de archivos de cualquier tamaño mediante fragmentación (chunking).
  - Verificación de integridad mediante **SHA-256**.
  - Control de flujo asíncrono para no bloquear la interfaz.
- **Interfaz Moderna (PySide6):** UI fluida diseñada con paradigmas modernos, integrada totalmente con `asyncio` mediante `qasync`.
- **Detección de Estado (Heartbeat):** Monitoreo constante de la salud de la conexión para detectar desconexiones abruptas en milisegundos.
- **Persistencia Local:** Historial de conversaciones y gestión de contactos mediante **SQLite3**.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Función |
| :--- | :--- | :--- |
| **Lenguaje** | Python 3.10+ | Lógica de alto nivel y asincronía |
| **Interfaz** | PySide6 (Qt) | Motor gráfico y experiencia de usuario |
| **Network** | WebSockets + Asyncio | Protocolo de transporte bidireccional |
| **Criptografía** | Cryptography.io | Implementación de estándares de seguridad |
| **Base de Datos** | SQLite3 | Almacenamiento local ligero |
| **Integración** | qasync | Puente entre el loop de Qt y Asyncio |

---

## 🏗️ Arquitectura del Sistema

El sistema se divide en capas especializadas para maximizar la mantenibilidad:

1. **Capa de Presentación (UI):** Componentes basados en Qt que reaccionan a eventos asíncronos sin congelar la ventana.
2. **Capa de Orquestación (Controller):** El `AppController` gestiona el flujo de datos entre la red, la interfaz y la base de datos.
3. **Capa de Red (Network/Node):** Maneja el servidor WebSocket y el protocolo de señalización P2P.
4. **Capa de Seguridad (Crypto):** Gestiona la generación de secretos, derivación de claves y cifrado simétrico.

---

## 📂 Estructura del Repositorio

```bash
modelo_P2P/
├── config/        # Parámetros globales (puertos, timeouts, versión)
├── controller/    # Orquestador principal (AppController)
├── database/      # Lógica de persistencia y modelos SQL
├── models/        # Estructuras de datos (Peer, ChatMessage, FileTransfer)
├── network/       # Implementación del protocolo P2P y WebSockets
├── ui/            # Vistas, widgets personalizados y estilos CSS
├── utils/         # Utilidades de criptografía, logging y validación
├── main.py        # Punto de entrada de la aplicación
└── requirements.txt
```

---

## 🚀 Instalación y Guía de Uso

### 1. Clonar y Configurar Entorno

Se recomienda usar un entorno virtual para mantener las dependencias aisladas:

```bash
# Crear el entorno
python -m venv .venv

# Activar en Windows
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Ejecución

Inicia la aplicación ejecutando el script principal:

```bash
python main.py
```

Al abrirse, deberás configurar:

- **Nickname:** Tu identidad visible en la red.
- **Puerto Local:** El puerto por donde escucharás nuevas conexiones (default: 5000).

---

## 📈 Próximos Pasos (Roadmap)

- [ ] **mDNS Discovery:** Detección automática de peers en la misma subred sin necesidad de IP manual.
- [ ] **Soporte de Grupos:** Creación de salas de chat grupales con intercambio de llaves de grupo.
- [ ] **Emojis & Markdown:** Soporte para renderizado rico de mensajes.

---

<div align="center">
  <sub>Sistemas Distribuidos - Universidad</sub>
</div>
