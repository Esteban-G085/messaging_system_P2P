# network/videocall.py
import cv2
import asyncio
import base64
import json
import av
import numpy as np
import pyaudio
from fractions import Fraction
from utils.logger import logger


AUDIO_RATE       = 48000
AUDIO_CHANNELS   = 1
AUDIO_CHUNK      = 960   # 20ms a 48kHz — tamaño estándar para Opus


class VideoCallWS:
    """Videollamada H.264 + Opus sobre WebSocket existente."""

    def __init__(self):
        self.running              = False
        self.cap                  = None
        self.on_frame_received    = None   # callback(numpy_bgr) → UI

        # Encoder/decoder video
        self._codec_ctx_enc       = None
        self._codec_ctx_dec       = None
        self._pts                 = 0

        # Encoder/decoder audio
        self._audio_enc           = None
        self._audio_dec           = None
        self._audio_pts           = 0

        # PyAudio
        self._pa                  = None
        self._audio_in_stream     = None
        self._audio_out_stream    = None

        # Tasks
        self._send_video_task     = None
        self._send_audio_task     = None

    # ── Encoder / Decoder video ───────────────────────────────────────────────

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
        logger.debug(f"[VIDEOCALL] Encoder H.264 creado: {width}x{height}")
        return codec

    def _build_video_decoder(self):
        codec = av.CodecContext.create("h264", "r")
        codec.open()
        logger.debug("[VIDEOCALL] Decoder H.264 creado")
        return codec

    # ── Encoder / Decoder audio ───────────────────────────────────────────────

    def _build_audio_encoder(self):
        codec                  = av.CodecContext.create("libopus", "w")
        codec.sample_rate      = AUDIO_RATE
        codec.channels         = AUDIO_CHANNELS
        codec.format           = av.AudioFormat("s16")
        codec.time_base        = Fraction(1, AUDIO_RATE)
        codec.options          = {"application": "voip"}
        codec.open()
        logger.debug("[VIDEOCALL] Encoder Opus creado")
        return codec

    def _build_audio_decoder(self):
        codec             = av.CodecContext.create("libopus", "r")
        codec.sample_rate = AUDIO_RATE
        codec.channels    = AUDIO_CHANNELS
        codec.format      = av.AudioFormat("s16")
        codec.open()
        logger.debug("[VIDEOCALL] Decoder Opus creado")
        return codec

    # ── PyAudio helpers ───────────────────────────────────────────────────────

    def _init_pyaudio(self):
        self._pa = pyaudio.PyAudio()
        logger.info("[VIDEOCALL] PyAudio inicializado")

    def _open_input_stream(self):
        self._audio_in_stream = self._pa.open(
            format            = pyaudio.paInt16,
            channels          = AUDIO_CHANNELS,
            rate              = AUDIO_RATE,
            input             = True,
            frames_per_buffer = AUDIO_CHUNK,
        )
        logger.info("[VIDEOCALL] ✅ Stream de entrada de audio abierto (micrófono)")

    def _open_output_stream(self):
        self._audio_out_stream = self._pa.open(
            format            = pyaudio.paInt16,
            channels          = AUDIO_CHANNELS,
            rate              = AUDIO_RATE,
            output            = True,
            frames_per_buffer = AUDIO_CHUNK,
        )
        logger.info("[VIDEOCALL] ✅ Stream de salida de audio abierto (altavoz)")

    # ── Envío video ───────────────────────────────────────────────────────────

    async def start_sending(self, node, peer):
        """Lanza video y audio en paralelo."""
        logger.info("=" * 80)
        logger.info("[VIDEOCALL] 🎥🎤 INICIANDO VIDEOLLAMADA (video + audio)")
        logger.info("=" * 80)

        self.running = True
        self._init_pyaudio()

        self._send_video_task = asyncio.get_event_loop().create_task(
            self._send_video_loop(node, peer)
        )
        self._send_audio_task = asyncio.get_event_loop().create_task(
            self._send_audio_loop(node, peer)
        )

        # Esperar ambas tareas
        await asyncio.gather(
            self._send_video_task,
            self._send_audio_task,
            return_exceptions=True,
        )

    async def _send_video_loop(self, node, peer):
        """Captura y envía video H.264."""
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            logger.error("[VIDEOCALL] ❌ No se pudo abrir la cámara")
            return

        logger.info(f"[VIDEOCALL] Cámara: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
                    f"{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} "
                    f"@ {self.cap.get(cv2.CAP_PROP_FPS):.0f} FPS")

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
                    logger.info("[VIDEOCALL] ✅ Encoder video listo — transmitiendo")

                rgb      = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                frame_av = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                frame_av = frame_av.reformat(format="yuv420p")
                frame_av.pts       = self._pts
                frame_av.time_base = Fraction(1, 30)
                self._pts += 1

                for pkt in self._codec_ctx_enc.encode(frame_av):
                    if pkt.size == 0:
                        continue
                    await self._ws_send(node, peer, "video_frame", bytes(pkt))
                    frames_sent += 1
                    if frames_sent % 150 == 0:
                        logger.debug(f"[VIDEOCALL] 📡 Video frames enviados: {frames_sent}")

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

    async def _send_audio_loop(self, node, peer):
        """Captura micrófono y envía audio Opus."""
        try:
            self._open_input_stream()
            self._audio_enc = self._build_audio_encoder()
            logger.info("[VIDEOCALL] ✅ Encoder audio listo — transmitiendo")

            chunks_sent = 0
            loop = asyncio.get_event_loop()

            while self.running:
                # Leer del micrófono sin bloquear el event loop
                raw = await loop.run_in_executor(
                    None,
                    lambda: self._audio_in_stream.read(
                        AUDIO_CHUNK, exception_on_overflow=False
                    )
                )

                audio_np = np.frombuffer(raw, dtype=np.int16)

                frame_av              = av.AudioFrame.from_ndarray(
                    audio_np.reshape(1, -1), format="s16", layout="mono"
                )
                frame_av.sample_rate  = AUDIO_RATE
                frame_av.pts          = self._audio_pts
                frame_av.time_base    = Fraction(1, AUDIO_RATE)
                self._audio_pts      += AUDIO_CHUNK

                for pkt in self._audio_enc.encode(frame_av):
                    if pkt.size == 0:
                        continue
                    await self._ws_send(node, peer, "audio_frame", bytes(pkt))
                    chunks_sent += 1
                    if chunks_sent % 500 == 0:
                        logger.debug(f"[VIDEOCALL] 🎤 Audio chunks enviados: {chunks_sent}")

        except asyncio.CancelledError:
            logger.info("[VIDEOCALL] ⏹️  Audio cancelado")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error en audio loop: {e}")
        finally:
            if self._audio_in_stream:
                self._audio_in_stream.stop_stream()
                self._audio_in_stream.close()
            logger.info("[VIDEOCALL] 🛑 Audio de entrada detenido")

    # ── Envío genérico ────────────────────────────────────────────────────────

    async def _ws_send(self, node, peer, msg_type: str, data: bytes):
        """Cifra y envía un paquete (video o audio) por WebSocket."""
        try:
            b64       = base64.b64encode(data).decode("utf-8")
            msg       = json.dumps({"type": msg_type, "data": b64})
            encrypted = node._crypto[peer.id].encrypt(msg)
            from network.protocol import Protocol
            _, payload = Protocol.message(node.username, node.peer_id, encrypted)
            await peer.connection.send(payload)
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error WS send ({msg_type}): {e}")

    # ── Recepción video ───────────────────────────────────────────────────────

    def receive_video_frame(self, b64_data: str):
        """Decodifica H.264 y manda el frame BGR a la UI."""
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
        """Decodifica Opus y reproduce por el altavoz."""
        try:
            if self._audio_dec is None:
                self._audio_dec = self._build_audio_decoder()
                self._open_output_stream()
                logger.info("[VIDEOCALL] ✅ Decoder audio listo — reproduciendo")

            pkt = av.Packet(base64.b64decode(b64_data))
            for frame_av in self._audio_dec.decode(pkt):
                # Convertir a s16 plano y escribir al altavoz
                audio = frame_av.to_ndarray(format="s16")
                self._audio_out_stream.write(audio.tobytes())
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error reproduciendo audio: {e}")

    # ── Control ───────────────────────────────────────────────────────────────

    def stop(self):
        """Detiene video, audio y libera todos los recursos."""
        logger.info("[VIDEOCALL] ⏹️  Deteniendo videollamada...")
        self.running = False

        for task in (self._send_video_task, self._send_audio_task):
            if task and not task.done():
                task.cancel()
        self._send_video_task = None
        self._send_audio_task = None

        if self._audio_in_stream:
            try:
                self._audio_in_stream.stop_stream()
                self._audio_in_stream.close()
            except Exception:
                pass

        if self._audio_out_stream:
            try:
                self._audio_out_stream.stop_stream()
                self._audio_out_stream.close()
            except Exception:
                pass

        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass

        if self.cap:
            self.cap.release()
            self.cap = None

        self._codec_ctx_enc = None
        self._codec_ctx_dec = None
        self._audio_enc     = None
        self._audio_dec     = None
        self._pts           = 0
        self._audio_pts     = 0

        logger.info("[VIDEOCALL] ✅ Todos los recursos liberados")