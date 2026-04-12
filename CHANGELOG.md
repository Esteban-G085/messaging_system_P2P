# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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


