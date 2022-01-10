import os
import random
import time

from PIL import Image, ImageDraw

from .view import View

from seedsigner.helpers import B
from seedsigner.gui.components import Fonts



class LogoView:
    def __init__(self):
        from seedsigner.gui import Renderer
        self.renderer: Renderer = Renderer.get_instance()
        dirname = os.path.dirname(__file__)
        logo_url = os.path.join(dirname, "../../", "seedsigner", "resources", "logo_black_crop.png")
        self.logo = Image.open(logo_url)

        self.partners = [
            "hodlhodl",
            "hrf",
            "river",
            "strike",
            "swan",
            "unchained",
        ]

        self.partner_logos = {}
        for partner in self.partners:
            logo_url = os.path.join(dirname, "../../", "seedsigner", "resources", "img", "partners", f"{partner}_logo.png")
            self.partner_logos[partner] = Image.open(logo_url)
    

    def get_random_partner(self):
        return self.partners[random.randrange(len(self.partners))]



class OpeningSplashView(LogoView):
    def start(self):
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        logo_offset_y = -5

        # Fade in alpha
        for i in range(250, -1, -25):
            self.logo.putalpha(255 - i)
            background = Image.new("RGBA", size=self.logo.size, color="black")
            self.renderer.canvas.paste(Image.alpha_composite(background, self.logo), (0, logo_offset_y))
            self.renderer.show_image()

        # Display version num below SeedSigner logo
        font = Fonts.get_font("OpenSans-Regular", 16)
        version = f"v{controller.VERSION}"
        version_tw, version_th = font.getsize(version)
        version_x = int((self.renderer.canvas_width - version_tw) / 2)
        version_y = self.logo.height - logo_offset_y - 25
        self.renderer.draw.text((version_x, version_y), version, fill="orange", font=font)

        # Set up the partner logo
        partner_logo = self.partner_logos[self.get_random_partner()]
        font = Fonts.get_font("OpenSans-SemiBold", 16)
        sponsor_text = "With support from:"
        tw, th = font.getsize(sponsor_text)
        x = int((self.renderer.canvas_width - tw) / 2)
        y = version_y + version_th + int((self.renderer.canvas_height - (version_y + version_th) - th - partner_logo.height ) / 2)
        self.renderer.draw.text((x, y), sponsor_text, fill="#ccc", font=font)
        self.renderer.canvas.paste(partner_logo, (int((self.renderer.canvas_width - partner_logo.width) / 2), y + th))

        self.renderer.show_image()
        time.sleep(5)



class ScreensaverView(LogoView):
    def __init__(self, buttons):
        super().__init__()

        self.buttons = buttons

        # Paste the logo in a bigger image that is 2x the size of the logo
        self.image = Image.new("RGB", size=(2 * self.renderer.canvas_width, 2 * self.renderer.canvas_height), color="black")
        self.image.paste(self.logo, (int((self.image.width - self.logo.size[0]) / 2), int((self.image.height - self.logo.size[1]) / 2)))

        self.partner_images = {}
        for partner, partner_logo in self.partner_logos.items():
            partner_image = Image.new("RGB", size=self.image.size, color="black")
            partner_image.paste(partner_logo, (int((self.image.width - partner_logo.size[0]) / 2), int((self.image.height - partner_logo.size[1]) / 2)))
            self.partner_images[partner] = partner_image

        self.min_coords = (0, 0)
        self.max_coords = (self.renderer.canvas_width, self.renderer.canvas_height)

        self.increment_x = self.rand_increment()
        self.increment_y = self.rand_increment()
        self.cur_x = int((self.renderer.canvas_width - self.logo.size[0]) / 2)
        self.cur_y = int((self.renderer.canvas_height - self.logo.size[1]) / 2)

        self._is_running = False
        self.last_screen = None


    @property
    def is_running(self):
        return self._is_running
    

    def rand_increment(self):
        max_increment = 10.0
        min_increment = 3.0
        increment = random.uniform(min_increment, max_increment)
        if random.uniform(-1.0, 1.0) < 0.0:
            return -1.0 * increment
        return increment


    def start(self):
        if self.is_running:
            return

        self._is_running = True

        # Store the current screen in order to restore it later
        self.last_screen = self.renderer.canvas.copy()

        screensaver_start = int(time.time() * 1000)

        is_main_logo = True

        while True:
            if self.buttons.has_any_input():
                return self.stop()
            
            if is_main_logo:
                cur_image = self.image
            else:
                if cur_image == self.image:
                    cur_image = self.partner_images[self.get_random_partner()]

            # Must crop the image to the exact display size
            crop = cur_image.crop((
                self.cur_x, self.cur_y,
                self.cur_x + self.renderer.canvas_width, self.cur_y + self.renderer.canvas_height))
            self.renderer.disp.ShowImage(crop, 0, 0)

            self.cur_x += self.increment_x
            self.cur_y += self.increment_y

            # At each edge bump, calculate a new random rate of change for that axis
            if self.cur_x < self.min_coords[0]:
                is_main_logo = not is_main_logo
                self.cur_x = self.min_coords[0]
                self.increment_x = self.rand_increment()
                if self.increment_x < 0.0:
                    self.increment_x *= -1.0
            elif self.cur_x > self.max_coords[0]:
                is_main_logo = not is_main_logo
                self.cur_x = self.max_coords[0]
                self.increment_x = self.rand_increment()
                if self.increment_x > 0.0:
                    self.increment_x *= -1.0

            if self.cur_y < self.min_coords[1]:
                is_main_logo = not is_main_logo
                self.cur_y = self.min_coords[1]
                self.increment_y = self.rand_increment()
                if self.increment_y < 0.0:
                    self.increment_y *= -1.0
            elif self.cur_y > self.max_coords[1]:
                is_main_logo = not is_main_logo
                self.cur_y = self.max_coords[1]
                self.increment_y = self.rand_increment()
                if self.increment_y > 0.0:
                    self.increment_y *= -1.0


    def stop(self):
        # Restore the original screen
        self.renderer.show_image(self.last_screen)

        self._is_running = False


