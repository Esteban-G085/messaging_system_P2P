# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.2.2] - 2026-04-12

### Added
- Versión actualizada de PyAudio con especificación explícita de versión mínima

### Changed
- **Dependencias:**
  - `pyaudio` → `pyaudio>=0.2.14` para mejorar compatibilidad con sistemas modernos
  - Todos los archivos compilados de Python (`.pyc`) regenerados con optimizaciones

### Fixed
- Mejor manejo de dispositivos de audio en sistemas con múltiples interfaces
- Resolución de conflictos en merge de repositorio

### Security
- Dependencias verificadas y pintadas en requirements.txt

---

## [1.2.1] - 2026-04-10

### Added
- Sistema de logging avanzado con archivos rotatorios
- Mejor detección de estado de peers

### Fixed
- Mejoras en la estabilidad de videollamadas
- Optimización de memoria en transferencias de archivos

---

## [1.2.0] - 2026-04-01

### Added
- Soporte completo para videollamadas con H.264
- Transferencia de archivos con verificación SHA-256
- Historial persistente de mensajes con SQLite

### Changed
- Refactorización completa del sistema de red
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

## Notas de Desarrollo

**Próximas versiones planeadas:**
- [1.3.0] - Descubrimiento automático con mDNS
- [1.4.0] - Soporte para chats grupales
- [2.0.0] - Protocolo mejorado con mejor tolerancia a fallos

Para más detalles sobre características y cambios, consulta [README.md](README.md).
