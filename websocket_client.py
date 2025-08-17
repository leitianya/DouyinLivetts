# websocket_client.py
import gzip
import threading
import websocket
import requests
import re
from protobuf.douyin import PushFrame, Response
import config
from utils import generateSignature, generateMsToken
from logger import log

class WebSocketClient:
    def __init__(self, live_id, on_message_callback):
        self.live_id = live_id
        self.on_message_callback = on_message_callback
        self.ws = None
        self.timer = None
        self.reconnect_lock = threading.Lock()
        self.__ttwid = None
        self.__room_id = None

    def start(self):
        threading.Thread(target=self._connect, daemon=True).start()

    def stop(self):
        if self.ws:
            self.ws.close()
        if self.timer:
            self.timer.cancel()

    def _connect(self):
        try:
            wss_url = config.WSS_URL_TEMPLATE.format(room_id=self.room_id)
            signature = generateSignature(wss_url)
            wss_url += f"&signature={signature}"

            headers = {
                "cookie": f"ttwid={self.ttwid}",
                'user-agent': config.USER_AGENT,
            }
            self.ws = websocket.WebSocketApp(
                wss_url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            log.info("Attempting to connect to WebSocket...")
            self.ws.run_forever()
        except Exception as e:
            log.error(f"Failed to connect: {e}")

    def _on_open(self, ws):
        log.info("WebSocket connected.")
        self._reset_timer()

    def _on_message(self, ws, message):
        package = PushFrame().parse(message)
        response = Response().parse(gzip.decompress(package.payload))

        if response.need_ack:
            ack = PushFrame(
                log_id=package.log_id,
                payload_type='ack',
                payload=response.internal_ext.encode('utf-8')
            ).SerializeToString()
            ws.send(ack, websocket.ABNF.OPCODE_BINARY)
            self._reset_timer()

        for msg in response.messages_list:
            self.on_message_callback(msg.method, msg.payload)

    def _on_error(self, ws, error):
        log.error(f"WebSocket error: {error}")

    def _on_close(self, ws, *args):
        log.info("WebSocket connection closed.")
        if self.timer:
            self.timer.cancel()

    def _reset_timer(self):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(config.MESSAGE_TIMEOUT, self._handle_timeout)
        self.timer.start()

    def _handle_timeout(self):
        with self.reconnect_lock:
            log.warning(f"No message received for {config.MESSAGE_TIMEOUT} seconds, reconnecting...")
            if self.ws:
                self.ws.close()
            self._connect()

    @property
    def ttwid(self):
        if self.__ttwid:
            return self.__ttwid
        headers = {"User-Agent": config.USER_AGENT}
        try:
            response = requests.get(config.DOUYIN_LIVE_URL, headers=headers)
            response.raise_for_status()
            self.__ttwid = response.cookies.get('ttwid')
            return self.__ttwid
        except Exception as err:
            log.error(f"Error getting ttwid: {err}")
            return None

    @property
    def room_id(self):
        if self.__room_id:
            return self.__room_id
        url = config.DOUYIN_LIVE_URL + self.live_id
        headers = {
            "User-Agent": config.USER_AGENT,
            "cookie": f"ttwid={self.ttwid}; msToken={generateMsToken()}; __ac_nonce=0123407cc00a9e438deb4",
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            match = re.search(r'roomId\\":\\"(\d+)\\"', response.text)
            if match:
                self.__room_id = match.group(1)
                return self.__room_id
            else:
                log.error("Could not find room_id.")
                return None
        except Exception as err:
            log.error(f"Error getting room_id: {err}")
            return None
