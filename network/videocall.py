# network/videocall.py
import cv2
import asyncio
import base64
import json
import av
from fractions import Fraction
from utils.logger import logger


class VideoCallWS:
    """Videollamada H.264 sobre WebSocket existente."""

    def __init__(self):
        self.running         = False
        self.cap             = None
        self.on_frame_received = None   # callback(numpy_bgr) → UI
        self._codec_ctx_enc  = None
        self._codec_ctx_dec  = None
        self._pts            = 0
        self._send_task      = None

    # ── Encoder / Decoder ────────────────────────────────────────────────────

    def _build_encoder(self, width: int, height: int):
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

    def _build_decoder(self):
        codec = av.CodecContext.create("h264", "r")
        codec.open()
        logger.debug("[VIDEOCALL] Decoder H.264 creado")
        return codec

    # ── Envío ─────────────────────────────────────────────────────────────────

    async def start_sending(self, node, peer):
        """Captura cámara, codifica H.264 y envía frames por WebSocket."""
        logger.info("=" * 80)
        logger.info("[VIDEOCALL] 🎥 INICIANDO CAPTURA DE CÁMARA")
        logger.info("=" * 80)

        self.running = True
        self.cap     = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            logger.error("[VIDEOCALL] ❌ No se pudo abrir la cámara")
            return

        real_w   = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        real_h   = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        real_fps = self.cap.get(cv2.CAP_PROP_FPS)
        logger.info(f"[VIDEOCALL]    Resolución: {real_w}x{real_h} @ {real_fps:.0f} FPS")
        logger.info(f"[VIDEOCALL]    Destino: {peer.username} ({peer.ip}:{peer.port})")

        frames_sent  = 0
        frames_error = 0

        try:
            while self.running:
                ret, bgr = self.cap.read()
                if not ret:
                    logger.warning("[VIDEOCALL] ⚠️  Frame vacío de la cámara, reintentando...")
                    await asyncio.sleep(0.01)
                    continue

                h, w = bgr.shape[:2]

                # Crear encoder al primer frame
                if self._codec_ctx_enc is None:
                    self._codec_ctx_enc = self._build_encoder(w, h)
                    logger.info(f"[VIDEOCALL] ✅ Encoder listo — comenzando transmisión")

                # BGR → YUV420p para H.264
                rgb      = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                frame_av = av.VideoFrame.from_ndarray(rgb, format="rgb24")
                frame_av = frame_av.reformat(format="yuv420p")
                frame_av.pts       = self._pts
                frame_av.time_base = Fraction(1, 30)
                self._pts += 1

                for pkt in self._codec_ctx_enc.encode(frame_av):
                    if pkt.size == 0:
                        continue

                    b64 = base64.b64encode(bytes(pkt)).decode("utf-8")
                    msg = json.dumps({"type": "video_frame", "data": b64})

                    try:
                        encrypted = node._crypto[peer.id].encrypt(msg)
                        from network.protocol import Protocol
                        _, payload = Protocol.message(
                            node.username, node.peer_id, encrypted
                        )
                        await peer.connection.send(payload)
                        frames_sent += 1

                        if frames_sent % 150 == 0:   # log cada ~5 seg a 30 FPS
                            logger.debug(
                                f"[VIDEOCALL] 📡 Frames enviados: {frames_sent} "
                                f"| Errores: {frames_error}"
                            )

                    except Exception as e:
                        frames_error += 1
                        logger.error(f"[VIDEOCALL] ❌ Error enviando frame #{self._pts}: {e}")
                        if frames_error > 10:
                            logger.error("[VIDEOCALL] ❌ Demasiados errores consecutivos — deteniendo")
                            self.running = False
                            break

                await asyncio.sleep(1 / 30)

        except asyncio.CancelledError:
            logger.info("[VIDEOCALL] ⏹️  Envío cancelado por el usuario")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error fatal en captura: {e}")
        finally:
            # Vaciar buffer del encoder
            if self._codec_ctx_enc:
                try:
                    self._codec_ctx_enc.encode(None)
                except Exception:
                    pass

            if self.cap:
                self.cap.release()

            logger.info("=" * 80)
            logger.info(
                f"[VIDEOCALL] 🛑 CAPTURA DETENIDA  |  "
                f"Frames enviados: {frames_sent}  |  Errores: {frames_error}"
            )
            logger.info("=" * 80)

    # ── Recepción ─────────────────────────────────────────────────────────────

    def receive_frame(self, b64_data: str):
        """Decodifica un packet H.264 entrante y lo manda a la UI."""
        try:
            if self._codec_ctx_dec is None:
                self._codec_ctx_dec = self._build_decoder()
                logger.info("[VIDEOCALL] ✅ Decoder listo — recibiendo video")

            raw = base64.b64decode(b64_data)
            pkt = av.Packet(raw)

            for frame_av in self._codec_ctx_dec.decode(pkt):
                bgr = frame_av.to_ndarray(format="bgr24")
                if self.on_frame_received:
                    self.on_frame_received(bgr)

        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error decodificando frame: {e}")

    # ── Control ───────────────────────────────────────────────────────────────

    def stop(self):
        """Detiene la llamada y libera todos los recursos."""
        logger.info("[VIDEOCALL] ⏹️  Deteniendo videollamada...")
        self.running = False

        if self._send_task:
            self._send_task.cancel()
            self._send_task = None
            logger.debug("[VIDEOCALL] Tarea de envío cancelada")

        if self.cap:
            self.cap.release()
            self.cap = None
            logger.debug("[VIDEOCALL] Cámara liberada")

        self._codec_ctx_enc = None
        self._codec_ctx_dec = None
        self._pts           = 0

        logger.info("[VIDEOCALL] ✅ Recursos liberados correctamente")