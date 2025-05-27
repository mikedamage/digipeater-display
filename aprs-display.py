#!/usr/bin/env python3

import asyncio
import attrs
import time
import signal
import sys
import queue
import logging
from pathlib import Path
from pprint import pformat

# oled display control
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import Image, ImageFont

# KISS TNC + APRS packet parsing
import aprs


class Application:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._logger = self._setupLogger()
        self._display = ssd1306(i2c(port=1, address=0x3c), width=128, height=64, rotate=0)
        self._font_size = 16
        self._font_path = str(Path(__file__).resolve().parent.joinpath('fonts', 'ProggyCleanNerdFontMono-Regular.ttf'))
        self._font = ImageFont.truetype(self._font_path, self._font_size)
        self._connection = None
        self._received_count = 0
        self._transmitted_count = 0
        self._last_rx_at = None
        self._last_packet = None
        self._last_rx_from = None
        self._connected_to_kiss = False
        self._connection_status = 'Connecting'

        self._init_display()

    def _setupLogger(self):
        logger = logging.getLogger('aprs_display')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _init_display(self):
        self._display.contrast(1)

    async def _connect(self):
        self._logger.info('Connecting to KISS TNC')

        transport, protocol = await aprs.create_tcp_connection(self._host, self._port)
        self._connection = protocol
        self._connection_status = "Connected"
        self._connected_to_kiss = True

    async def render(self):
        while True:
            current_time = time.strftime('%H:%M:%S')
            rows = [
                f'\U0000EB34 KR4BVP-10',
                f'\U0000F017 {current_time}',
            ]

            if self._connected_to_kiss:
                rows.append(f'\U000F00FA: {self._received_count}')
                rows.append(f'\U0000F2F5 {self._last_rx_from} {self._last_rx_at}')
            else:
                rows.append(f'{self._connection_status}')

            with canvas(self._display) as draw:
                for i, line in enumerate(rows):
                    draw.text(
                        (0, 2 + (i * self._font_size)),
                        text=line,
                        font=self._font,
                        fill="white"
                    )
            await asyncio.sleep(1)

    async def receive(self):
        if not self._connected_to_kiss:
            await self._connect()

        loop = asyncio.get_running_loop()
        loop.create_task(self.render())

        while True:
            async for frame in self._connection.read():
                self._logger.info("Packet received: %s", pformat(attrs.asdict(frame)))
                self._received_count += 1
                self._last_rx_at = time.strftime("%H:%M:%S")
                self._last_rx_from = frame.source

async def main():
    app = Application("localhost", 8001)
    loop = asyncio.get_running_loop()
    loop.create_task(app.render())
    loop.create_task(app.receive())
    loop.run_forever()

if __name__ == "__main__":
    app = Application("localhost", 8001)
    asyncio.run(app.receive())
