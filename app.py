"""
The real-time voice bridge: Twilio Media Streams <-> Google STT (streaming)
<-> Gemini (llm_agent.ConversationSession) <-> Google TTS <-> back to Twilio.

NOT YET LIVE-TESTED — written against documented, stable APIs (Twilio Media
Streams protocol, google-cloud-speech StreamingRecognize, google-cloud-tts
MULAW/8kHz telephony output) but no Twilio/Google Cloud credentials were
available to run this end-to-end while writing it. Test STT and TTS
standalone first (see test_stt.py / test_tts.py) before a live call.

Run: uvicorn app:app --host 0.0.0.0 --port 8000
Then tunnel with: ngrok http 8000
"""

import asyncio
import base64
import json
import queue
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import Response
from google.cloud import speech, texttospeech

from llm_agent import ConversationSession

app = FastAPI()

speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()
executor = ThreadPoolExecutor(max_workers=4)

STREAMING_CONFIG = speech.StreamingRecognitionConfig(
    config=speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
        sample_rate_hertz=8000,
        language_code="hi-IN",
        alternative_language_codes=["te-IN", "en-IN"],
        model="phone_call",
        use_enhanced=True,
    ),
    interim_results=True,
)


@app.post("/twiml")
async def twiml(request: Request):
    """Twilio fetches this when the outbound call connects. Embeds the
    called number as a custom Stream parameter so /media-stream knows who
    to send WhatsApp messages to."""
    form = await request.form()
    to_number = form.get("To", "")
    host = request.headers.get("host")
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect><Stream url=\"wss://{host}/media-stream\">"
        '<Parameter name="caller_number" value="{to}" />'
        "</Stream></Connect></Response>"
    ).format(host=host, to=to_number)
    return Response(content=body, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()

    audio_queue: "queue.Queue" = queue.Queue()
    result_queue: "asyncio.Queue" = asyncio.Queue()
    state = {"stream_sid": None, "session": None}

    def audio_request_generator():
        while True:
            chunk = audio_queue.get()
            if chunk is None:
                return
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def stt_worker():
        try:
            responses = speech_client.streaming_recognize(
                STREAMING_CONFIG, audio_request_generator()
            )
            for response in responses:
                for result in response.results:
                    if result.is_final and result.alternatives:
                        transcript = result.alternatives[0].transcript
                        loop.call_soon_threadsafe(result_queue.put_nowait, transcript)
        except Exception as exc:  # noqa: BLE001
            print("STT worker error:", exc)
        finally:
            loop.call_soon_threadsafe(result_queue.put_nowait, None)

    stt_task = loop.run_in_executor(executor, stt_worker)

    async def poll_transcripts():
        while True:
            transcript = await result_queue.get()
            if transcript is None:
                return
            session = state["session"]
            if session is None:
                continue
            reply_text = await loop.run_in_executor(executor, session.respond, transcript)
            audio_bytes = await loop.run_in_executor(executor, synthesize, reply_text)
            if state["stream_sid"]:
                await send_media(websocket, state["stream_sid"], audio_bytes)

    poll_task = asyncio.create_task(poll_transcripts())

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                start = data["start"]
                state["stream_sid"] = start["streamSid"]
                caller_number = start.get("customParameters", {}).get("caller_number", "")
                state["session"] = ConversationSession(caller_number)
                opening_audio = await loop.run_in_executor(
                    executor, synthesize, state["session"].opening_line()
                )
                await send_media(websocket, state["stream_sid"], opening_audio)

            elif event == "media":
                chunk = base64.b64decode(data["media"]["payload"])
                audio_queue.put(chunk)

            elif event == "stop":
                audio_queue.put(None)
                break
    except Exception as exc:  # noqa: BLE001
        print("media_stream closed:", exc)
    finally:
        poll_task.cancel()
        audio_queue.put(None)


def synthesize(text: str) -> bytes:
    input_text = texttospeech.SynthesisInput(text=text)
    # hi-IN covers Hindi/English reasonably; swap dynamically per detected
    # language once that signal is available from Gemini's response if
    # quality on Telugu/mixed input needs it (te-IN voice exists too).
    voice = texttospeech.VoiceSelectionParams(
        language_code="hi-IN", name="hi-IN-Wavenet-A"
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MULAW,
        sample_rate_hertz=8000,
    )
    response = tts_client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )
    return response.audio_content


async def send_media(websocket: WebSocket, stream_sid: str, audio_bytes: bytes):
    payload = base64.b64encode(audio_bytes).decode("ascii")
    await websocket.send_text(
        json.dumps({"event": "media", "streamSid": stream_sid, "media": {"payload": payload}})
    )
