# network/videocall.py
import asyncio
import base64
import json
from fractions import Fraction

import av
import cv2
import numpy as np
import pyaudio
import sys
import os
import ctypes

from utils.logger import logger


# ── Constantes de audio ───────────────────────────────────────────────────────
# 16 kHz es suficiente para voz y usa la mitad de ancho de banda que 44.1 kHz
AUDIO_RATE     = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK    = 512

VIDEO_WIDTH    = 320    
VIDEO_HEIGHT   = 240    
VIDEO_FPS      = 20  


def _find_camera() -> tuple[int, int]:
    """
    Retorna (índice, backend) según el SO.
    Windows → CAP_DSHOW, Linux/Mac → CAP_V4L2 o automático.
    """
    if sys.platform == "win32":
        backend = cv2.CAP_DSHOW
    elif sys.platform.startswith("linux"):
        backend = cv2.CAP_V4L2
    else:
        backend = cv2.CAP_ANY   # macOS y otros

    for i in range(3):
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            cap.release()
            logger.info(f"[VIDEOCALL] Cámara encontrada en índice {i} (backend: {backend})")
            return i, backend

    logger.warning("[VIDEOCALL] No se encontró cámara — usando índice 0 automático")
    return 0, cv2.CAP_ANY

def _suppress_alsa_errors():
    """Suprime el spam de ALSA/JACK en Linux."""
    if not sys.platform.startswith("linux"):
        return
    try:
        # Redirigir stderr de las librerías C de ALSA a /dev/null
        asound = ctypes.cdll.LoadLibrary("libasound.so.2")
        asound.snd_lib_error_set_handler(None)
    except Exception:
        pass

class VideoCallWS:
    """
    Videollamada H.264 + PCM sobre el WebSocket existente.
    - Video: H.264 (libx264 ultrafast/zerolatency) → base64 → WS
    - Audio: PCM 16 kHz 16-bit mono               → base64 → WS
    """

    def __init__(self):
        self.running               = False

        # Callbacks
        self.on_frame_received     = None   # (numpy_bgr) → UI
        self.on_call_ended         = None   # ()          → UI

        # Video
        self.cap                   = None
        self._enc                  = None   # encoder H.264
        self._dec                  = None   # decoder H.264
        self._pts                  = 0

        # Audio
        self._pa                   = None
        self._mic_stream           = None
        self._spk_stream           = None
        self._audio_queue          = None   # asyncio.Queue — salida

        # Tasks
        self._task_video_tx        = None
        self._task_audio_tx        = None
        self._task_audio_rx        = None

    # ── Codecs ────────────────────────────────────────────────────────────────

    def _build_encoder(self, w: int, h: int) -> av.CodecContext:
        ctx           = av.CodecContext.create("libx264", "w")
        ctx.width     = w
        ctx.height    = h
        ctx.pix_fmt   = "yuv420p"
        ctx.time_base = Fraction(1, VIDEO_FPS)
        ctx.options   = {
            "preset":  "ultrafast",
            "tune":    "zerolatency",
            "profile": "baseline",
            # Limitar tamaño de GOP → menor latencia en el receptor
            "g":       str(VIDEO_FPS),
        }
        ctx.open()
        logger.debug(f"[VIDEOCALL] Encoder H.264 listo {w}x{h} @ {VIDEO_FPS}FPS")
        return ctx

    def _build_decoder(self) -> av.CodecContext:
        ctx = av.CodecContext.create("h264", "r")
        ctx.open()
        logger.debug("[VIDEOCALL] Decoder H.264 listo")
        return ctx

    # ── Audio I/O ─────────────────────────────────────────────────────────────

    def _init_audio(self) -> bool:
        """Abre micrófono y altavoz. Retorna False si ambos fallan."""
        _suppress_alsa_errors()
        self._pa = pyaudio.PyAudio()
        ok = False

        # Listar dispositivos disponibles para debug
        logger.info("[VIDEOCALL] Dispositivos de audio disponibles:")
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0 or info["maxOutputChannels"] > 0:
                logger.info(
                    f"[VIDEOCALL]   [{i}] {info['name']} "
                    f"(in:{info['maxInputChannels']} out:{info['maxOutputChannels']})"
                )

        # Buscar índices del dispositivo de entrada y salida por defecto
        try:
            input_idx  = self._pa.get_default_input_device_info()["index"]
            output_idx = self._pa.get_default_output_device_info()["index"]
            logger.info(f"[VIDEOCALL] Dispositivo entrada default: {input_idx}")
            logger.info(f"[VIDEOCALL] Dispositivo salida default:  {output_idx}")
        except Exception as e:
            logger.warning(f"[VIDEOCALL] No se pudo obtener dispositivo default: {e}")
            input_idx  = None
            output_idx = None

        try:
            kwargs = dict(
                format            = pyaudio.paInt16,
                channels          = AUDIO_CHANNELS,
                rate              = AUDIO_RATE,
                input             = True,
                frames_per_buffer = AUDIO_CHUNK,
            )
            if input_idx is not None:
                kwargs["input_device_index"] = input_idx

            self._mic_stream = self._pa.open(**kwargs)
            logger.info("[VIDEOCALL] [OK] Micrófono abierto")
            ok = True
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] Micrófono: {e}")

        try:
            kwargs = dict(
                format            = pyaudio.paInt16,
                channels          = AUDIO_CHANNELS,
                rate              = AUDIO_RATE,
                output            = True,
                frames_per_buffer = AUDIO_CHUNK,
            )
            if output_idx is not None:
                kwargs["output_device_index"] = output_idx

            self._spk_stream = self._pa.open(**kwargs)
            logger.info("[VIDEOCALL] [OK] Altavoz abierto")
            ok = True
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] Altavoz: {e}")

        return ok

    # ── Arranque ──────────────────────────────────────────────────────────────

    async def start_sending(self, node, peer):
        """
        Punto de entrada. Lanza los tres loops en paralelo.
        Si alguno falla, los demás siguen funcionando.
        """
        logger.info("=" * 80)
        logger.info("[VIDEOCALL] INICIANDO VIDEOLLAMADA")
        logger.info(f"[VIDEOCALL]    Peer: {peer.username} ({peer.ip}:{peer.port})")
        logger.info("=" * 80)

        self.running      = True
        self._audio_queue = asyncio.Queue(maxsize=20)  # ~640 ms máximo de buffer

        self._init_audio()

        loop = asyncio.get_event_loop()
        self._task_video_tx = loop.create_task(
            self._loop_video_tx(node, peer), name="video_tx"
        )
        self._task_audio_tx = loop.create_task(
            self._loop_audio_tx(node, peer), name="audio_tx"
        )
        self._task_audio_rx = loop.create_task(
            self._loop_audio_rx(), name="audio_rx"
        )

        # Esperar sin propagar excepciones — cada loop se gestiona solo
        results = await asyncio.gather(
            self._task_video_tx,
            self._task_audio_tx,
            self._task_audio_rx,
            return_exceptions=True,
        )

        for r in results:
            if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError):
                logger.error(f"[VIDEOCALL] Loop terminó con error: {r}")

        logger.info("[VIDEOCALL] Todos los loops terminados")

    # ── Loop: envío de video ──────────────────────────────────────────────────

    async def _loop_video_tx(self, node, peer):
        cam_idx, backend = _find_camera()
        self.cap = cv2.VideoCapture(cam_idx, backend)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  VIDEO_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS,          VIDEO_FPS)

        if not self.cap.isOpened():
            logger.error("[VIDEOCALL] [ERR] Cámara no disponible")
            return

        logger.info(
            f"[VIDEOCALL] Cámara: {VIDEO_WIDTH}x{VIDEO_HEIGHT} @ {VIDEO_FPS} FPS"
        )

        loop        = asyncio.get_event_loop()
        frames_sent = 0

        try:
            while self.running:
                ret, bgr = await loop.run_in_executor(None, self.cap.read)
                if not ret:
                    await asyncio.sleep(0.01)
                    continue

                h, w = bgr.shape[:2]

                # Resize explícito por si la cámara no respeta el set()
                if w != VIDEO_WIDTH or h != VIDEO_HEIGHT:
                    bgr = cv2.resize(bgr, (VIDEO_WIDTH, VIDEO_HEIGHT))

                if self._enc is None:
                    self._enc = self._build_encoder(VIDEO_WIDTH, VIDEO_HEIGHT)
                    logger.info("[VIDEOCALL] [OK] Transmitiendo video H.264...")

                rgb      = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                frame_av = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                frame_av = frame_av.reformat(format="yuv420p")
                frame_av.pts       = self._pts
                frame_av.time_base = Fraction(1, VIDEO_FPS)   # antes era Fraction(1, 30)
                self._pts         += 1

                for pkt in self._enc.encode(frame_av):
                    if pkt.size > 0:
                        await self._ws_send(node, peer, "video_frame", bytes(pkt))
                        frames_sent += 1

                if frames_sent % 100 == 0 and frames_sent:
                    logger.debug(f"[VIDEOCALL] Video frames enviados: {frames_sent}")

                await asyncio.sleep(1 / VIDEO_FPS)   # antes era 1/30



        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] Error video TX: {e}")
        finally:
            # Vaciar buffer del encoder
            if self._enc:
                try:
                    self._enc.encode(None)
                except Exception:
                    pass
            if self.cap:
                self.cap.release()
                self.cap = None
            logger.info(f"[VIDEOCALL] [STOP] Video TX detenido | Frames: {frames_sent}")

    # ── Loop: envío de audio ──────────────────────────────────────────────────

    async def _loop_audio_tx(self, node, peer):
        if not self._mic_stream:
            logger.warning("[VIDEOCALL] [WARN]  Sin micrófono — audio TX desactivado")
            return

        logger.info("[VIDEOCALL] [OK] Transmitiendo audio PCM 16 kHz...")
        loop        = asyncio.get_event_loop()
        chunks_sent = 0

        try:
            while self.running:
                raw = await loop.run_in_executor(
                    None,
                    lambda: self._mic_stream.read(AUDIO_CHUNK, exception_on_overflow=False),
                )
                await self._ws_send(node, peer, "audio_frame", raw)
                chunks_sent += 1

                if chunks_sent % 500 == 0:
                    logger.debug(f"[VIDEOCALL] Audio chunks TX: {chunks_sent}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] Error audio TX: {e}")
        finally:
            logger.info(f"[VIDEOCALL] [STOP] Audio TX detenido | Chunks: {chunks_sent}")

    # ── Loop: reproducción de audio ───────────────────────────────────────────

    async def _loop_audio_rx(self):
        if not self._spk_stream:
            logger.warning("[VIDEOCALL] [WARN]  Sin altavoz — audio RX desactivado")
            return

        logger.info("[VIDEOCALL] [OK] Reproductor de audio listo")
        loop = asyncio.get_event_loop()

        try:
            while self.running:
                try:
                    pcm = await asyncio.wait_for(
                        self._audio_queue.get(), timeout=0.5
                    )
                    # write() es bloqueante — fuera del event loop
                    await loop.run_in_executor(None, self._spk_stream.write, pcm)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] Error audio RX: {e}")
        finally:
            logger.info("[VIDEOCALL] [STOP] Reproductor detenido")

    # ── WS send ───────────────────────────────────────────────────────────────

    async def _ws_send(self, node, peer, msg_type: str, data: bytes):
        try:
            b64        = base64.b64encode(data).decode("utf-8")
            msg        = json.dumps({"type": msg_type, "data": b64})
            encrypted  = node._crypto[peer.id].encrypt(msg)
            from network.protocol import Protocol
            _, payload = Protocol.message(node.username, node.peer_id, encrypted)
            await peer.connection.send(payload)
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] WS send ({msg_type}): {e}")

    # ── Recepción video ───────────────────────────────────────────────────────

    def receive_video_frame(self, b64_data: str):
        try:
            if self._dec is None:
                self._dec = self._build_decoder()
                logger.info("[VIDEOCALL] [OK] Decoder video listo — recibiendo")

            pkt = av.Packet(base64.b64decode(b64_data))
            for frame_av in self._dec.decode(pkt):
                # Entregar ya en RGB — la UI no necesita saber nada de cv2
                rgb = frame_av.to_ndarray(format="rgb24")
                if self.on_frame_received:
                    self.on_frame_received(rgb)
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] Error decode video: {e}")

    # ── Recepción audio ───────────────────────────────────────────────────────

    def receive_audio_frame(self, b64_data: str):
        """Encola PCM para reproducción. Descarta si hay lag acumulado."""
        if self._audio_queue is None:
            return
        try:
            pcm = base64.b64decode(b64_data)
            self._audio_queue.put_nowait(pcm)
        except asyncio.QueueFull:
            # Cola llena → descartar el frame más viejo y meter el nuevo
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(pcm)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"[VIDEOCALL] [ERR] Error encolando audio: {e}")

    # ── Stop ──────────────────────────────────────────────────────────────────

    def stop(self):
        """Para todos los loops y libera recursos."""
        if not self.running:
            return

        logger.info("[VIDEOCALL] [STOP]  Deteniendo videollamada...")
        self.running = False

        for task in (self._task_video_tx, self._task_audio_tx, self._task_audio_rx):
            if task and not task.done():
                task.cancel()

        self._task_video_tx = None
        self._task_audio_tx = None
        self._task_audio_rx = None

        for stream in (self._mic_stream, self._spk_stream):
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
        self._mic_stream = None
        self._spk_stream = None

        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

        if self.cap:
            self.cap.release()
            self.cap = None

        self._enc     = None
        self._dec     = None
        self._pts     = 0
        self._audio_queue = None

        logger.info("[VIDEOCALL] [OK] Recursos liberados")
        if self.on_call_ended:
            self.on_call_ended()
