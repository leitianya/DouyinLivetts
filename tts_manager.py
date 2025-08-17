# tts_manager.py
import asyncio
import os
import threading
import uuid
from queue import Queue
import edge_tts
from playsound import playsound
import config
from logger import log

class TTSManager:
    def __init__(self, task_queue: Queue):
        self.task_queue = task_queue
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_event_loop, daemon=True)
        self.thread.start()

    def _start_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _text_to_speech_async(self, text, voice, output_path):
        for attempt in range(config.TTS_MAX_RETRIES):
            try:
                tts = edge_tts.Communicate(
                    text,
                    voice,
                    proxy=config.TTS_PROXY if config.USE_TTS_PROXY else None,
                )
                await tts.save(output_path)
                if os.path.exists(output_path):
                    return
                else:
                    raise FileNotFoundError(f"Failed to generate audio file: {output_path}")
            except Exception as e:
                log.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < config.TTS_MAX_RETRIES - 1:
                    await asyncio.sleep(config.TTS_RETRY_DELAY)
                else:
                    raise

    def _play_speech(self, text, voice_index):
        try:
            os.makedirs(config.AUDIO_OUTPUT_DIR, exist_ok=True)
            unique_id = str(uuid.uuid4())
            output_file = os.path.join(config.AUDIO_OUTPUT_DIR, f"speech_{unique_id}.mp3")
            voice = config.TTS_VOICES[voice_index]

            future = asyncio.run_coroutine_threadsafe(
                self._text_to_speech_async(text, voice, output_file), self.loop
            )
            future.result()  # Wait for the async function to complete

            playsound(output_file)
            log.info(f"Speech generated and played: {output_file}")
        except Exception as e:
            log.error(f"Error during speech playback: {e}")
        finally:
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError as e:
                    log.error(f"Error deleting file: {e}")

    def add_task(self, text, voice_index):
        try:
            self.task_queue.put(lambda: self._play_speech(text, voice_index), timeout=1)
        except Queue.Full:
            log.warning(f"Task queue is full, discarding TTS task: {text}")

def consumer_thread_worker(task_queue: Queue):
    """A worker function for the consumer thread to process tasks from the queue."""
    while True:
        try:
            task = task_queue.get()
            if task is None:
                break
            task()
            task_queue.task_done()
        except Exception as e:
            log.error(f"Error processing task: {e}")
