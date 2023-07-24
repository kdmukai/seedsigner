import io
import time
import threading
import picamera
from seedsigner.gui.components import Fonts, GUIConstants
from seedsigner.gui.renderer import Renderer

from seedsigner.hardware.ST7789 import ST7789
from PIL import Image, ImageDraw
from pyzbar import pyzbar
from seedsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants

from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus


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

                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the available pool
                    with self.owner.lock:
                        self.owner.pool.append(self)



class PyzbarProcessor(threading.Thread):
    def __init__(self, owner, decoder: DecodeQR):
        super(PyzbarProcessor, self).__init__(daemon=True)
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.owner = owner
        self.decoder = decoder

        self.last_update = time.time()
        self.instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)

        self.start_time = time.time()
        self.num_frames = 0
        self.start()


    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(0.1):
                try:
                    self.stream.seek(0)
                    img = Image.open(self.stream)
                    status = self.decoder.add_image(img)

                    self.num_frames += 1
                    print(f"{self.num_frames / (time.time() - self.start_time):.2f} fps (pyzbar)")

                    if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                        print("QR DECODED!")
                        self.owner.done = True
                        break
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

                    if not self.terminated:
                        # Return ourselves to the available pool
                        with self.owner.lock:
                            self.owner.pool.append(self)



class ProcessOutput(object):
    def __init__(self, display: ST7789, decoder: DecodeQR):
        self.done = False
        # Construct a pool of 4 image processors along with a lock
        # to control access between threads
        self.lock = threading.Lock()
        display_lock = threading.Lock()
        self.pool = [
            DisplayProcessor(owner=self, display=display, display_lock=display_lock),
            DisplayProcessor(owner=self, display=display, display_lock=display_lock),
            PyzbarProcessor(owner=self, decoder=decoder),
        ]
        self.processor = None
        self.num_display_updates = 0
        self.start_at = time.time()
        self.hw_inputs = HardwareButtons.get_instance()


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

        if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
            print("HW BUTTON!!")
            self.done = True


    def flush(self):
        # When told to flush (this indicates end of recording), shut
        # down in an orderly fashion. First, add the current processor
        # back to the pool
        print("flush")
        start = time.time()
        if self.processor:
            self.processor.terminated = True
            self.processor.join()

        # Now, empty the pool
        while True:
            with self.lock:
                try:
                    proc = self.pool.pop()
                    if proc:
                        proc.terminated = True
                    proc.join()
                except IndexError:
                    break
        print(f"flushed in {time.time() - start} seconds")



def start(decoder: DecodeQR):
    with picamera.PiCamera(resolution=(480,480)) as camera:
        camera.start_preview()
        display = Renderer.get_instance().disp

        try:
            output = ProcessOutput(display=display, decoder=decoder)
            camera.start_recording(output, format='mjpeg')
            while not output.done:
                camera.wait_recording(0.1)
        finally:
            print("CLEANING UP!")
            output.flush()

            start = time.time()
            camera.stop_recording()
            print(f"stopped recording in {time.time() - start} seconds")

