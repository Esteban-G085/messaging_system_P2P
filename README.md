# Sistema de Mensajería P2P

### Autores: Esteban Guapacha, David Julian Torres y [Kevin Esguerra](mailto:kevin.esguerra@utp.edu.co)

Una aplicación de mensajería descentralizada **Peer-to-Peer (P2P)** diseñada para funcionar en redes locales (LAN). Desarrollada en Python, combina una interfaz gráfica reactiva, manejo de red asíncrono y persistencia de datos local, sin depender de un servidor central.

## 🚀 Características Principales

- **Descentralizado (P2P):** Cada instancia actúa simultáneamente como cliente y servidor, permitiendo la comunicación directa entre nodos.
- **Interfaz Gráfica Moderna:** UI de escritorio nativa y estilizada construida con PySide6.
- **Mensajería en Tiempo Real:** Comunicación bidireccional mediante WebSockets y `asyncio`.
- **Persistencia Local:** Historial de mensajes, lista de contactos (peers) y registro de conexiones almacenados localmente de forma segura en SQLite.
- **Concurrencia Fluida:** Integración impecable entre el hilo de la UI (Qt) y el hilo asíncrono de red gracias a `qasync`.

## 🛠️ Tecnologías Utilizadas

- **Python 3.10+**
- **PySide6** (Qt for Python) para la interfaz gráfica.
- **websockets** + **asyncio** para la red TCP no bloqueante.
- **qasync** para acoplar los event loops de Qt y asyncio.
- **sqlite3** para la base de datos local.

## 🏗️ Arquitectura del Sistema

El proyecto sigue una arquitectura altamente cohesiva basada en capas / MVC, asegurando una separación estricta de responsabilidades:

1.  **Capa de Interfaz (UI):** Componentes visuales (`MainWindow`, `ChatView`, `PeersList`, etc.) que reaccionan de manera asíncrona a los eventos mediante `@asyncSlot()`. Se mantiene completamente agnóstica de la lógica de red o persistencia.
2.  **Controlador Central (`AppController`):** Ejerce de núcleo unificador en la aplicación. Orquesta la comunicación entre la Interfaz Visual, la Red y la Base de Datos sin que éstas se conozcan entre sí.
3.  **Capa de Red (`P2PNode` & Protocolo):** Encapsula un `WebSocketServer` (para escuchar conexiones entrantes) y un `WebSocketClient` (para salidas). Utiliza un protocolo estandarizado en JSON (`HELLO`, `MESSAGE`, `MESSAGE_ACK`, `HEARTBEAT`) para interactuar con otros nodos en la LAN.
4.  **Capa de Persistencia (`DBManager`):** Centraliza las transacciones SQL en modo *thread-safe*, guardando mensajes, logs y contactos. Interactúa de forma eficiente manteniendo los flujos no bloqueantes de `qasync`.

## ⚙️ Flujo de Operación

1.  **Arranque:** Al iniciar, se define un puerto local y un nickname. El `WebSocketServer` comienza a escuchar en el backend.
2.  **Conexión P2P:** Para chatear, se ingresa la IP y el puerto de un peer destino. Se efectúa un proceso de handshake (`HELLO`/`HELLO_ACK`). Tras autenticarse mutuamente, los nodos establecen la conexión y se registran sus perfiles localmente.
3.  **Chat en Tiempo Real:** Los mensajes de texto se envían de forma asíncrona por WebSocket a los destinatarios empaquetados en un formato JSON ordenado.
4.  **Acuses de Recibo (ACK):** Cada mensaje remitido recibe un acuse (`MESSAGE_ACK`) confirmando que el paquete alcanzó y fue procesado por el destinatario, repercutiendo visualmente en el cliente UI del emisor.

## 📈 Consideraciones y Roadmap Técnico

El sistema actual cuenta con un diseño muy limpio que garantiza la estabilidad bajo la exigencia multi-hilo o asíncrona de las librerías nativas. Sin embargo, en bases a estudios arquitectónicos, se presentan dos áreas clave identificadas para la futura evolución del proyecto:

- **Loop de Heartbeat Autónomo:** Implementar o asegurar el circuito cíclico del pulso `HEARTBEAT` constante, emitiéndose cada X segundos desde la capa P2P de forma cronometrada, permitiendo así detectar desconexiones abruptas o cierres silenciosos por inactividad de red.
- **Capa de Seguridad y Cifrado:** Dado que actualmente el MVP transmite en texto claro JSON ideal para pruebas LAN, el próximo paso natural para la madurez de seguridad será la aplicación de cifrado en tránsito, montando los WebSockets bajo SSL/TLS nativos, u optando por métodos matemáticos integrados de encriptación de extremo a extremo (E2EE/RSA).

## 📄 Requisitos e Instrucciones de Uso

Para preparar el entorno de trabajo, se deben instalar las dependencias señaladas en su virtualenv:

```bash
pip install -r requirements.txt
```

Para arrancar y utilizar la aplicación (nodo):
```bash
python main.py
```
