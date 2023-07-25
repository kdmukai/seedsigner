import time

from dataclasses import dataclass
from typing import List, Tuple

from seedsigner.gui import renderer
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.hardware.camera import Camera
from seedsigner.models import DecodeQR, DecodeQRStatus
from seedsigner.models.threads import BaseThread

from .screen import BaseScreen, BaseTopNavScreen, ButtonListScreen
from ..components import BaseComponent, Button, GUIConstants, Fonts, IconButton, TextArea, calc_text_centering




@dataclass
class ScanScreen(BaseScreen):
    decoder: DecodeQR = None
    instructions_text: str = "< back  |  Scan a QR code"
    resolution: Tuple[int,int] = (480, 480)
    framerate: int = 12
    render_rect: Tuple[int,int,int,int] = None


    def __post_init__(self):
        from seedsigner.hardware.camera import Camera
        # Initialize the base class
        super().__post_init__()

        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=self.resolution, framerate=self.framerate, format="rgb")

        self.threads.append(ScanScreen.LivePreviewThread(
            camera=self.camera,
            decoder=self.decoder,
            renderer=self.renderer,
            instructions_text=self.instructions_text,
            render_rect=self.render_rect,
        ))


    class LivePreviewThread(BaseThread):
        def __init__(self, camera: Camera, decoder: DecodeQR, renderer: renderer.Renderer, instructions_text: str, render_rect: Tuple[int,int,int,int]):
            self.camera = camera
            self.decoder = decoder
            self.renderer = renderer
            self.instructions_text = instructions_text
            if render_rect:
                self.render_rect = render_rect            
            else:
                self.render_rect = (0, 0, self.renderer.canvas_width, self.renderer.canvas_height)
            self.render_width = self.render_rect[2] - self.render_rect[0]
            self.render_height = self.render_rect[3] - self.render_rect[1]

            self.decoder_fps = "0.0"

            print(f"render_width: {self.render_width}")
            print(f"render_height: {self.render_height}")

            super().__init__()


        def run(self):
            start_time = time.time()
            num_frames = 0
            show_framerate = True  # enable for debugging / testing
            instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)
            while self.keep_running:
                frame = self.camera.read_video_stream(as_image=True)
                if frame is not None:
                    num_frames += 1
                    cur_time = time.time()
                    cur_fps = num_frames / (cur_time - start_time)
                    scan_text = self.instructions_text
                    if self.decoder and self.decoder.get_percent_complete() > 0 and self.decoder.is_psbt:
                        scan_text = str(self.decoder.get_percent_complete()) + "% Complete"

                    if show_framerate:
                            scan_text = f" {cur_fps:0.2f} | {self.decoder_fps}"
                    else:
                        scan_text = self.instructions_text

                    with self.renderer.lock:
                        if frame.width > self.render_width or frame.height > self.render_height:
                            frame = frame.resize(
                                (self.render_width, self.render_height)
                            )
                        self.renderer.canvas.paste(
                            frame,
                            (self.render_rect[0], self.render_rect[1])
                        )

                        if scan_text:
                            self.renderer.draw.text(
                                xy=(
                                    int(self.renderer.canvas_width/2),
                                    self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                                ),
                                text=scan_text,
                                fill=GUIConstants.BODY_FONT_COLOR,
                                font=instructions_font,
                                stroke_width=4,
                                stroke_fill=GUIConstants.BACKGROUND_COLOR,
                                anchor="ms"
                            )

                        self.renderer.show_image()

                    print(f" {cur_fps:0.2f} | {self.decoder_fps}")

                time.sleep(0.05) # turn this up or down to tune performance while decoding psbt
                if self.camera._video_stream is None:
                    break


    def _run(self):
        """
            _render() is mostly meant to be a one-time initial drawing call to set up the
            Screen. Once interaction starts, the display updates have to be managed in
            _run(). The live preview is an extra-complex case.
        """
        num_frames = 0
        start_time = time.time()
        while True:
            frame = self.camera.read_video_stream()
            if frame is not None:
                status = self.decoder.add_image(frame)

                num_frames += 1
                decoder_fps = f"{num_frames / (time.time() - start_time):0.2f}"
                self.threads[0].decoder_fps = decoder_fps
                
                if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                    self.camera.stop_video_stream_mode()
                    break
                
                # TODO: KEY_UP gives control to NavBar; use its back arrow to cancel
                if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                    self.camera.stop_video_stream_mode()
                    break



@dataclass
class SettingsUpdatedScreen(ButtonListScreen):
    config_name: str = None
    title: str = "Settings QR"
    is_bottom_list: bool = True

    def __post_init__(self):
        # Customize defaults
        self.button_data = ["Home"]

        super().__post_init__()

        start_y = self.top_nav.height + 20
        if self.config_name:
            self.config_name_textarea = TextArea(
                text=f'"{self.config_name}"',
                is_text_centered=True,
                auto_line_break=True,
                screen_y=start_y
            )
            self.components.append(self.config_name_textarea)
            start_y = self.config_name_textarea.screen_y + 50
        
        self.components.append(TextArea(
            text="Settings imported successfully!",
            is_text_centered=True,
            auto_line_break=True,
            screen_y=start_y
        ))

