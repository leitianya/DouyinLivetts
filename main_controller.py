# main_controller.py
import queue
import threading
from gui import AppGUI
from websocket_client import WebSocketClient
from message_handler import MessageHandler
from tts_manager import TTSManager, consumer_thread_worker
from logger import log

class MainController:
    def __init__(self):
        self.task_queue = queue.Queue(maxsize=100)
        self.tts_manager = TTSManager(self.task_queue)
        self.message_handler = MessageHandler(self.tts_manager, self.update_gui_viewers)
        self.ws_client = None
        
        toggle_callbacks = {
            "chat": self.toggle_speech,
            "gift": self.toggle_gift,
            "follow": self.toggle_follow,
            "welcome": self.toggle_welcome,
        }
        self.gui = AppGUI(self.start, self.stop, toggle_callbacks)
        
        self.consumer_thread = threading.Thread(target=consumer_thread_worker, args=(self.task_queue,), daemon=True)
        self.consumer_thread.start()

    def start(self, live_id):
        if self.ws_client:
            self.ws_client.stop()
        
        self.ws_client = WebSocketClient(live_id, self.message_handler.handle_message)
        self.ws_client.start()
        log.info(f"Started connection for live ID: {live_id}")

    def stop(self):
        if self.ws_client:
            self.ws_client.stop()
            self.ws_client = None
            log.info("Stopped connection.")
        
        with self.task_queue.mutex:
            self.task_queue.queue.clear()

    def update_gui_viewers(self, count):
        self.gui.after(0, self.gui.update_viewers_count, count)

    def toggle_speech(self):
        self.message_handler.speech_enabled = not self.message_handler.speech_enabled
        log.info(f"Speech {'enabled' if self.message_handler.speech_enabled else 'disabled'}")

    def toggle_gift(self):
        self.message_handler.gift_enabled = not self.message_handler.gift_enabled
        log.info(f"Gift speech {'enabled' if self.message_handler.gift_enabled else 'disabled'}")

    def toggle_follow(self):
        self.message_handler.follow_enabled = not self.message_handler.follow_enabled
        log.info(f"Follow speech {'enabled' if self.message_handler.follow_enabled else 'disabled'}")

    def toggle_welcome(self):
        self.message_handler.welcome_enabled = not self.message_handler.welcome_enabled
        log.info(f"Welcome speech {'enabled' if self.message_handler.welcome_enabled else 'disabled'}")

    def run(self):
        self.gui.run()
