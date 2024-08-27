import logging

import uvicorn
from fastapi import FastAPI, WebSocket
import asyncio
from process_message import process_message
from Tools import build_reply_json, build_group_reply_json


class BotWebSocket:
    def __init__(self, muice):
        self.app = FastAPI()
        self.received_messages_queue = asyncio.Queue()
        self.messages_to_send_queue = asyncio.Queue()
        self.process_message_func = process_message(muice)

        @self.app.websocket("/ws/api")
        async def websocket_endpoint(websocket: WebSocket):

            await websocket.accept()
            asyncio.create_task(self.reply_messages())
            asyncio.create_task(self.send_messages(websocket))

            try:
                async for message in websocket.iter_text():
                    await self.received_messages_queue.put(message)
                    print(f"Received: {message}")
            except Exception as e:
                print(f"WebSocket disconnected: {e}")

    async def reply_messages(self):
        while True:
            try:
                print("reply_messages")
                data = await self.received_messages_queue.get()
                processed_message = self.process_message_func.reply_message(data)
                if processed_message is not None:
                    await self.messages_to_send_queue.put(processed_message)
                self.received_messages_queue.task_done()
            except:
                continue

    async def send_messages(self, websocket: WebSocket):
        while True:
            print("send_messages")
            data = await self.messages_to_send_queue.get()
            logging.debug(f'data:{data}')
            if data is None or data is not list:
                continue
            group_id = data.get('group_id', -1)
            message_list = data.get('message_list', [])
            if group_id == -1:
                for key in message_list:
                    message_json = await build_reply_json(key, data['sender_user_id'])
                    logging.info(f'send message{key}')
                    await websocket.send_text(message_json)
            else:
                for key in message_list:
                    message_json = await build_group_reply_json(key, data['group_id'])
                    logging.info(f'send message{key}')
                    await websocket.send_text(message_json)

            self.messages_to_send_queue.task_done()

    def run(self):
        uvicorn.run(self.app, host="127.0.0.1", port=22050)


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)
    logging.warning("用户请勿直接运行此文件，请使用main.py运行")
    muice = None
    ws = BotWebSocket(muice)
    ws.run()
