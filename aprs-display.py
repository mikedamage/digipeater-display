#!/usr/bin/env python3

import time
import ax25
import kiss
import signal
import sys
import queue
from pathlib import Path
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import Image, ImageFont

class Application:
    def __init__(self, host, port):
        self._display = ssd1306(i2c(port=1, address=0x3c), width=128, height=64, rotate=0)
        self._font_size = 16
        self._font_path = str(Path(__file__).resolve().parent.joinpath('fonts', 'ProggyCleanNerdFontMono-Regular.ttf'))
        self._font = ImageFont.truetype(self._font_path, self._font_size)
        self._connection = None
        # self._frame_queue = queue.Queue()
        self._received_count = 0
        self._transmitted_count = 0
        self._last_rx_at = None
        self._last_packet = None
        self._last_rx_from = None
        self._connected_to_kiss = False
        self._connection_status = 'Connecting'

        # Connect to KISS server to receive packets
        self._init_display()
        self._start_receiving(host, port)

    def render(self):
        current_time = time.strftime('%H:%M:%S')
        rows = [
            f'\U0000EB34 KR4BVP-10',
            f'\U0000F017 {current_time}',
        ]

        if self._connected_to_kiss:
            rows.append(f'\U000F00FA: {self._received_count}')
            # rows.append(f'\U0000F2F5 {self._last_rx_from} {self._last_rx_at}')
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

    def cleanup(self):
        self._stop_receiving()

    def _init_display(self):
        self._display.contrast(1)

    def _start_receiving(self, host, port):
        def receive_callback(kiss_port, data):
            print('received packet')
            self._received_count += 1
            extracted_data = self._extract_frame(data)
            if not extracted_data:
                return
            frame = ax25.Frame.unpack(extracted_data)
            self._last_rx_at = time.strftime('%H:%M:%S')
            self._last_rx_from = str(frame.src)
        try:
            self._connection = kiss.Connection(receive_callback)
            self._connection.connect_to_server(host, port)
            self._connection_status = f'{host}:{port}'
            self._connected_to_kiss = True
        except:
            self._connection_status = 'Not connected'

    def _stop_receiving(self):
        if self._connection:
            self._connection.disconnect_from_server()
            self._connection = None

    def _extract_frame(self, data):
        if not (data[0] == 0xC0 and data[1] == 0x00 and data[-1] == 0xC0):
            return None
        return data[2:-1].replace(
            b'\xDB\xDD', b'\xDB').replace(b'\xDB\xDC', b'\xC0')
    
    def _process_frames(self):
        while not self._frame_queue.empty():
            (frame, timestamp) = self._frame_queue.get()

def main():
    try:
        app = Application('127.0.0.1', 8001)

        while True:
            app.render()
            time.sleep(1)
    except KeyboardInterrupt:
        app.cleanup()
        sys.exit()

if __name__ == "__main__":
    main()
