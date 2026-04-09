# network/videocall.py
from aiortc import RTCPeerConnection
from aiortc.contrib.media import MediaPlayer, MediaRecorder

class VideoCall:
    def __init__(self):
        self.pc = RTCPeerConnection()
        self.recorder = MediaRecorder("received_call.mp4")

    def add_local_tracks(self):
        # Captura cámara y micrófono
        player = MediaPlayer(0)  # 0 = cámara/micrófono por defecto
        if player.video:
            self.pc.addTrack(player.video)
        if player.audio:
            self.pc.addTrack(player.audio)

    async def create_offer(self):
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        return offer

    async def create_answer(self):
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        return answer

    async def set_remote_description(self, sdp):
        await self.pc.setRemoteDescription(sdp)

    async def add_ice_candidate(self, candidate):
        await self.pc.addIceCandidate(candidate)

    def on_track(self):
        @self.pc.on("track")
        async def handle_track(track):
            await self.recorder.addTrack(track)
