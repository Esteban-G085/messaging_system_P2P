# network/videocall.py
import asyncio
import base64
import json
import struct
from fractions import Fraction

import av
import cv2
import numpy as np
import pyaudio

from utils.logger import logger


AUDIO_RATE     = 44100
AUDIO_CHANNELS = 1
AUDIO_CHUNK    = 1024


def _find_camera() -> int:
    """Detecta el primer índice de cámara disponible."""
    for i in range(3):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.release()
            logger.info(f"[VIDEOCALL] Cámara encontrada en índice {i}")
            return i
    return 0


class VideoCallWS:
    """Videollamada H.264 + PCM sobre WebSocket existente."""

    def __init__(self):
        self.running               = False
        self.cap                   = None
        self.on_frame_received     = None   # callback(numpy_bgr) → UI

        # Video codec
        self._codec_ctx_enc        = None
        self._codec_ctx_dec        = None
        self._pts                  = 0

        # PyAudio
        self._pa                   = None
        self._audio_in_stream      = None
        self._audio_out_stream     = None

        # Cola para reproducción sin bloquear el event loop
        self._audio_out_queue: asyncio.Queue = None

        # Tasks
        self._send_video_task      = None
        self._send_audio_task      = None
        self._play_audio_task      = None

    # ── Video encoder / decoder ───────────────────────────────────────────────

    def _build_video_encoder(self, width: int, height: int):
        codec           = av.CodecContext.create("libx264", "w")
        codec.width     = width
        codec.height    = height
        codec.pix_fmt   = "yuv420p"
        codec.time_base = Fraction(1, 30)
        codec.options   = {
            "preset":  "ultrafast",
            "tune":    "zerolatency",
            "profile": "baseline",
        }
        codec.open()
        logger.debug(f"[VIDEOCALL] Encoder H.264 listo: {width}x{height}")
        return codec

    def _build_video_decoder(self):
        codec = av.CodecContext.create("h264", "r")
        codec.open()
        logger.debug("[VIDEOCALL] Decoder H.264 listo")
        return codec

    # ── PyAudio ───────────────────────────────────────────────────────────────

    def _init_audio(self):
        self._pa = pyaudio.PyAudio()

        # Entrada (micrófono)
        try:
            self._audio_in_stream = self._pa.open(
                format            = pyaudio.paInt16,
                channels          = AUDIO_CHANNELS,
                rate              = AUDIO_RATE,
                input             = True,
                frames_per_buffer = AUDIO_CHUNK,
            )
            logger.info("[VIDEOCALL] ✅ Micrófono abierto")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ No se pudo abrir micrófono: {e}")

        # Salida (altavoz)
        try:
            self._audio_out_stream = self._pa.open(
                format            = pyaudio.paInt16,
                channels          = AUDIO_CHANNELS,
                rate              = AUDIO_RATE,
                output            = True,
                frames_per_buffer = AUDIO_CHUNK,
            )
            logger.info("[VIDEOCALL] ✅ Altavoz abierto")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ No se pudo abrir altavoz: {e}")

    # ── Envío principal ───────────────────────────────────────────────────────

    async def start_sending(self, node, peer):
        """Lanza video + audio en paralelo."""
        logger.info("=" * 80)
        logger.info("[VIDEOCALL] 🎥🎤 INICIANDO VIDEOLLAMADA")
        logger.info("=" * 80)

        self.running           = True
        self._audio_out_queue  = asyncio.Queue(maxsize=50)

        self._init_audio()

        loop = asyncio.get_event_loop()
        self._send_video_task = loop.create_task(self._send_video_loop(node, peer))
        self._send_audio_task = loop.create_task(self._send_audio_loop(node, peer))
        self._play_audio_task = loop.create_task(self._play_audio_loop())

        await asyncio.gather(
            self._send_video_task,
            self._send_audio_task,
            self._play_audio_task,
            return_exceptions=True,
        )

    # ── Loop de video ─────────────────────────────────────────────────────────

    async def _send_video_loop(self, node, peer):
        cam_index = _find_camera()
        self.cap  = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            logger.error("[VIDEOCALL] ❌ No se pudo abrir la cámara")
            return

        logger.info(
            f"[VIDEOCALL] Cámara: "
            f"{int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
            f"{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} "
            f"@ {self.cap.get(cv2.CAP_PROP_FPS):.0f} FPS"
        )

        frames_sent = 0
        try:
            while self.running:
                ret, bgr = self.cap.read()
                if not ret:
                    await asyncio.sleep(0.01)
                    continue

                h, w = bgr.shape[:2]
                if self._codec_ctx_enc is None:
                    self._codec_ctx_enc = self._build_video_encoder(w, h)
                    logger.info("[VIDEOCALL] ✅ Transmitiendo video...")

                rgb      = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                frame_av = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                frame_av = frame_av.reformat(format="yuv420p")
                frame_av.pts       = self._pts
                frame_av.time_base = Fraction(1, 30)
                self._pts         += 1

                for pkt in self._codec_ctx_enc.encode(frame_av):
                    if pkt.size == 0:
                        continue
                    await self._ws_send(node, peer, "video_frame", bytes(pkt))
                    frames_sent += 1
                    if frames_sent % 150 == 0:
                        logger.debug(f"[VIDEOCALL] 📡 Frames enviados: {frames_sent}")

                await asyncio.sleep(1 / 30)

        except asyncio.CancelledError:
            logger.info("[VIDEOCALL] ⏹️  Video cancelado")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error en video loop: {e}")
        finally:
            if self._codec_ctx_enc:
                try:
                    self._codec_ctx_enc.encode(None)
                except Exception:
                    pass
            if self.cap:
                self.cap.release()
            logger.info(f"[VIDEOCALL] 🛑 Video detenido | Frames: {frames_sent}")

    # ── Loop de audio (envío) ─────────────────────────────────────────────────

    async def _send_audio_loop(self, node, peer):
        """Lee del micrófono y envía PCM crudo por WebSocket."""
        if not self._audio_in_stream:
            logger.error("[VIDEOCALL] ❌ No hay stream de entrada — audio no enviado")
            return

        logger.info("[VIDEOCALL] ✅ Transmitiendo audio PCM...")
        chunks_sent = 0
        loop        = asyncio.get_event_loop()

        try:
            while self.running:
                # Leer sin bloquear el event loop
                raw = await loop.run_in_executor(
                    None,
                    lambda: self._audio_in_stream.read(
                        AUDIO_CHUNK, exception_on_overflow=False
                    ),
                )
                await self._ws_send(node, peer, "audio_frame", raw)
                chunks_sent += 1
                if chunks_sent % 500 == 0:
                    logger.debug(f"[VIDEOCALL] 🎤 Audio chunks enviados: {chunks_sent}")

        except asyncio.CancelledError:
            logger.info("[VIDEOCALL] ⏹️  Audio TX cancelado")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error en audio loop: {e}")
        finally:
            logger.info(f"[VIDEOCALL] 🛑 Audio TX detenido | Chunks: {chunks_sent}")

    # ── Loop de reproducción ──────────────────────────────────────────────────

    async def _play_audio_loop(self):
        """
        Reproduce audio desde la cola en un executor para no bloquear
        el event loop con stream.write().
        """
        if not self._audio_out_stream:
            logger.error("[VIDEOCALL] ❌ No hay stream de salida — audio no reproducido")
            return

        logger.info("[VIDEOCALL] ✅ Reproductor de audio listo")
        loop = asyncio.get_event_loop()

        try:
            while self.running:
                try:
                    pcm = await asyncio.wait_for(
                        self._audio_out_queue.get(), timeout=1.0
                    )
                    await loop.run_in_executor(
                        None, self._audio_out_stream.write, pcm
                    )
                except asyncio.TimeoutError:
                    continue   # sin datos, seguir esperando
        except asyncio.CancelledError:
            logger.info("[VIDEOCALL] ⏹️  Reproductor cancelado")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error en reproductor: {e}")

    # ── WebSocket send ────────────────────────────────────────────────────────

    async def _ws_send(self, node, peer, msg_type: str, data: bytes):
        try:
            b64        = base64.b64encode(data).decode("utf-8")
            msg        = json.dumps({"type": msg_type, "data": b64})
            encrypted  = node._crypto[peer.id].encrypt(msg)
            from network.protocol import Protocol
            _, payload = Protocol.message(node.username, node.peer_id, encrypted)
            await peer.connection.send(payload)
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ WS send ({msg_type}): {e}")

    # ── Recepción video ───────────────────────────────────────────────────────

    def receive_video_frame(self, b64_data: str):
        try:
            if self._codec_ctx_dec is None:
                self._codec_ctx_dec = self._build_video_decoder()
                logger.info("[VIDEOCALL] ✅ Decoder video listo — recibiendo")

            pkt = av.Packet(base64.b64decode(b64_data))
            for frame_av in self._codec_ctx_dec.decode(pkt):
                bgr = frame_av.to_ndarray(format="bgr24")
                if self.on_frame_received:
                    self.on_frame_received(bgr)
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error decodificando video: {e}")

    # ── Recepción audio ───────────────────────────────────────────────────────

    def receive_audio_frame(self, b64_data: str):
        """Encola PCM para reproducción — no bloquea el event loop."""
        try:
            pcm = base64.b64decode(b64_data)
            if self._audio_out_queue is None:
                # Primer frame antes de que start_sending arranque — ignorar
                return
            # put_nowait descarta si la cola está llena (evita lag acumulado)
            try:
                self._audio_out_queue.put_nowait(pcm)
            except asyncio.QueueFull:
                logger.debug("[VIDEOCALL] Cola de audio llena — frame descartado")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error encolando audio: {e}")

    # ── Stop ──────────────────────────────────────────────────────────────────

    def stop(self):
        logger.info("[VIDEOCALL] ⏹️  Deteniendo videollamada...")
        self.running = False

        for task in (self._send_video_task, self._send_audio_task, self._play_audio_task):
            if task and not task.done():
                task.cancel()
        self._send_video_task = None
        self._send_audio_task = None
        self._play_audio_task = None

        for stream in (self._audio_in_stream, self._audio_out_stream):
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
        self._audio_in_stream  = None
        self._audio_out_stream = None

        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

        if self.cap:
            self.cap.release()
            self.cap = None

        self._codec_ctx_enc = None
        self._codec_ctx_dec = None
        self._pts           = 0

        logger.info("[VIDEOCALL] ✅ Todos los recursos liberados")
