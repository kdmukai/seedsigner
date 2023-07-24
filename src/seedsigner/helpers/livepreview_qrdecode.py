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
    def __init__(self, owner, renderer: Renderer):
        super(DisplayProcessor, self).__init__(daemon=True)
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.owner = owner
        self.renderer = renderer
        self.cur_fps = 0.0
        self.num_frames = 0
        self.instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)
        self.debug_display = ""

        self.start()


    def run(self):
        # This method runs in a separate thread
        start_time = time.time()
        while not self.terminated:
            # Wait for an image to be written to the stream
            try:
                img = None
                with self.owner.cur_frame_lock:
                    print("display")
                    if self.owner.cur_frame:
                        img = self.owner.cur_frame.copy()
                    print("display DONE")
                if not img:
                    time.sleep(0.1)
                    continue
                    
                img = img.resize(size=(240,240), resample=Image.NEAREST).rotate(90 + 180)
                self.num_frames += 1
                self.cur_fps = self.num_frames / (time.time() - start_time)
                img = img
                draw = ImageDraw.Draw(img)
                draw.text(
                            xy=(
                                int(240/2),
                                240 - 8
                            ),
                            text=self.debug_display,
                            fill=GUIConstants.BODY_FONT_COLOR,
                            font=self.instructions_font,
                            # stroke_width=4,
                            # stroke_fill=GUIConstants.BACKGROUND_COLOR,
                            anchor="ms"
                        )
                
                with self.renderer.lock:
                    self.renderer.show_image(img, show_direct=True)

            finally:
                pass



class PyzbarProcessor(threading.Thread):
    def __init__(self, owner, decoder: DecodeQR):
        super(PyzbarProcessor, self).__init__(daemon=True)
        self.event = threading.Event()
        self.terminated = False
        self.owner = owner
        self.decoder = decoder

        self.instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)
        self.num_frames = 0
        self.cur_fps = 0.0

        self.start()


    def run(self):
        # This method runs in a separate thread
        start_time = time.time()
        while not self.terminated:
            # Wait for an image to be written to the stream
            try:
                img = None
                with self.owner.cur_frame_lock:
                    print("decoder")
                    if self.owner.cur_frame:
                        img = self.owner.cur_frame.copy()
                    print("decoder DONE")
                if not img:
                    time.sleep(0.1)
                    continue
                status = self.decoder.add_image(img)

                self.num_frames += 1
                self.cur_fps = self.num_frames / (time.time() - start_time)

                if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                    print("QR DECODED!")
                    self.owner.done = True
                    break
            finally:
                pass



class ProcessOutput(object):
    def __init__(self, decoder: DecodeQR):
        self.renderer = Renderer.get_instance()
        self.done = False

        self.num_display_updates = 0
        self.num_pyzbar_updates = 0
        self.start_at = time.time()
        self.hw_inputs = HardwareButtons.get_instance()

        self.cur_frame_lock = threading.Lock()
        self.cur_frame = None
        self.framebuffer = io.BytesIO()

        self.display_processor = DisplayProcessor(owner=self, renderer=self.renderer)
        self.decoder_processor = PyzbarProcessor(owner=self, decoder=decoder)


    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            with self.cur_frame_lock:
                print("Update cur_frame")
                self.framebuffer.seek(0)
                self.framebuffer.truncate()
                self.framebuffer.write(buf)
                self.cur_frame = Image.open(self.framebuffer)
                print("Update cur_frame DONE")

            if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                print("HW BUTTON!!")
                self.done = True
            
            self.display_processor.debug_display = f"{self.display_processor.cur_fps:0.2f} | {self.decoder_processor.cur_fps:0.2f}"


    def flush(self):
        # When told to flush (this indicates end of recording), shut
        # down in an orderly fashion. First, add the current processor
        # back to the pool
        print("flush")
        start = time.time()
        self.display_processor.terminated = True
        self.decoder_processor.terminated = True
        self.display_processor.join()
        self.decoder_processor.join()
        self.renderer.clear()
        print(f"flushed in {time.time() - start} seconds")



def start(decoder: DecodeQR):
    with picamera.PiCamera(resolution=(480,480), framerate=5) as camera:
        camera.start_preview()

        try:
            output = ProcessOutput(decoder=decoder)
            camera.start_recording(output, format='mjpeg')
            while not output.done:
                camera.wait_recording(0.1)
        finally:
            print("CLEANING UP!")
            start = time.time()
            camera.stop_recording()
            print(f"stopped recording in {time.time() - start} seconds")

