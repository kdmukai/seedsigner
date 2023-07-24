import io
import time
import threading
import picamera
from seedsigner.gui.components import Fonts, GUIConstants

from seedsigner.hardware.ST7789 import ST7789
from PIL import Image, ImageDraw
from pyzbar import pyzbar


class DisplayProcessor(threading.Thread):
    def __init__(self, owner, display: ST7789, display_lock: threading.Lock):
        super(DisplayProcessor, self).__init__(daemon=True)
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.owner = owner
        self.display = display
        self.display_lock = display_lock
        self.cur_fps = "0"
        self.instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)
        self.start()


    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(0.1):
                try:
                    print("display")
                    self.stream.seek(0)
                    # Read the image and do some processing on it
                    img = Image.open(self.stream).resize(size=(240,240), resample=Image.NEAREST).rotate(90 + 180)
                    draw = ImageDraw.Draw(img)
                    draw.text(
                                xy=(
                                    int(240/2),
                                    240 - 8
                                ),
                                text=f"{self.cur_fps:.2f} fps",
                                fill=GUIConstants.BODY_FONT_COLOR,
                                font=self.instructions_font,
                                stroke_width=4,
                                stroke_fill=GUIConstants.BACKGROUND_COLOR,
                                anchor="ms"
                            )
                    
                    with self.display_lock:
                        self.display.ShowImage(img, 0, 0)
                    #...
                    #...
                    # Set done to True if you want the script to terminate
                    # at some point
                    #self.owner.done=True
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the available pool
                    with self.owner.lock:
                        self.owner.pool.append(self)



class PyzbarProcessor(threading.Thread):
    def __init__(self, owner, display: ST7789):
        super(PyzbarProcessor, self).__init__(daemon=True)
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.owner = owner
        self.display = display
        self.last_update = time.time()
        self.instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)
        self.start()


    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(0.1):
                try:
                    print("pyzbar")
                    self.stream.seek(0)
                    # Read the image and do some processing on it
                    img = Image.open(self.stream)

                    result = pyzbar.decode(img, symbols=[pyzbar.ZBarSymbol.QRCODE])
                    print(result)

                    #...
                    #...
                    # Set done to True if you want the script to terminate
                    # at some point
                    #self.owner.done=True
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the available pool
                    with self.owner.lock:
                        self.owner.pool.append(self)



class ProcessOutput(object):
    def __init__(self, display: ST7789):
        self.done = False
        # Construct a pool of 4 image processors along with a lock
        # to control access between threads
        self.lock = threading.Lock()
        display_lock = threading.Lock()
        self.pool = [
            DisplayProcessor(owner=self, display=display, display_lock=display_lock),
            DisplayProcessor(owner=self, display=display, display_lock=display_lock),
            PyzbarProcessor(owner=self, display=display),
        ]
        self.processor = None
        self.num_display_updates = 0
        self.start_at = time.time()


    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame; set the current processor going and grab
            # a spare one
            if self.processor:
                self.processor.event.set()
            with self.lock:
                if self.pool:
                    self.processor = self.pool.pop()
                else:
                    # No processor's available, we'll have to skip
                    # this frame; you may want to print a warning
                    # here to see whether you hit this case
                    print("SKIP")
                    self.processor = None
        if self.processor:
            if type(self.processor) == DisplayProcessor:
                cur_time = time.time()
                self.num_display_updates += 1
                self.processor.cur_fps = self.num_display_updates / (cur_time - self.start_at)
            self.processor.stream.write(buf)


    def flush(self):
        # When told to flush (this indicates end of recording), shut
        # down in an orderly fashion. First, add the current processor
        # back to the pool
        print("flush")
        if self.processor:
            with self.lock:
                self.pool.append(self.processor)
                self.processor = None
        # Now, empty the pool, joining each thread as we go
        while True:
            with self.lock:
                try:
                    proc = self.pool.pop()
                    proc.terminated = True
                    proc.join()
                except IndexError:
                    break



with picamera.PiCamera(resolution=(480,480)) as camera:
    camera.start_preview()
    display = ST7789()

    try:
        output = ProcessOutput(display=display)
        camera.start_recording(output, format='mjpeg')
        while not output.done:
            camera.wait_recording(0.1)
    finally:
        output.flush()
        camera.stop_recording()
