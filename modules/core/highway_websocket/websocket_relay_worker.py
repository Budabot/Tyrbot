import asyncio
import json

from websocket import create_connection, WebSocketConnectionClosedException, WebSocketTimeoutException

from core.logger import Logger
from core.dict_object import DictObject


class WebsocketRelayWorker:
    def __init__(self, url, user_agent):
        self.logger = Logger(__name__)
        self.inbound_queue = []
        self.url = url
        self.ws = None
        self.user_agent = user_agent
        self.is_running = False

    async def run_loop(self):
        loop = asyncio.get_running_loop()
        try:
            self.ws = await loop.run_in_executor(None, lambda: create_connection(self.url, header={"User-Agent": self.user_agent}, timeout=5))
            self.ws.settimeout(1.0)
            self.logger.info("Connected to Websocket Relay via asyncio loop!")
            self.is_running = True
        except Exception as e:
            self.logger.error("Failed to connect to Websocket Relay", e)
            self.is_running = False
            self.inbound_queue.append(DictObject({"type": "disconnect"}))
            return

        while self.is_running and self.ws:
            try:
                result = await loop.run_in_executor(None, self._safe_recv)
                if result:
                    obj = DictObject(json.loads(result))
                    self.inbound_queue.append(obj)
                else:
                    await asyncio.sleep(0.05)
            except WebSocketConnectionClosedException as e:
                if self.is_running:
                    self.logger.error("Websocket connection closed", e)
                break
            except Exception as e:
                if self.is_running:
                    self.logger.error("Error reading from websocket", e)
                break

        self.is_running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
            self.inbound_queue.append(DictObject({"type": "disconnect"}))

    def _safe_recv(self):
        if not self.ws:
            return None
        try:
            return self.ws.recv()
        except WebSocketTimeoutException:
            return None

    def send_message(self, message):
        if self.ws and self.is_running:
            try:
                self.ws.send(message)
            except Exception as e:
                self.logger.error("Error sending message to websocket", e)

    def get_message_from_queue(self):
        if self.inbound_queue:
            return self.inbound_queue.pop(0)
        else:
            return None

    def send_ping(self):
        try:
            if self.ws and self.is_running:
                self.ws.ping()
        except WebSocketConnectionClosedException as e:
            self.logger.error("Ping failed, closing websocket", e)
            self.close()
        except Exception as e:
            self.logger.error("Error sending ping", e)

    def close(self):
        self.is_running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
