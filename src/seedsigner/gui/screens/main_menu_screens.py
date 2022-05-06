
from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import GUIConstants, TextArea
from seedsigner.gui.screens.screen import BaseTopNavScreen, LargeButtonScreen


@dataclass
class MainMenuScreen(LargeButtonScreen):
    def __post_init__(self):
        self.title = _("Home")
        self.title_font_size = GUIConstants.get_top_nav_title_font_size() + 6
        self.show_back_button=False
        self.show_power_button=True

        super().__post_init__()



@dataclass
class ResetScreen(BaseTopNavScreen):
    def __post_init__(self):
        self.title = _("Restarting")
        self.show_back_button = False
        super().__post_init__()

        self.components.append(TextArea(
            text=_("SeedSigner is restarting.\n\nAll in-memory data will be wiped."),
            screen_y=self.top_nav.height,
            height=self.canvas_height - self.top_nav.height,
        ))



@dataclass
class PowerOffScreen(BaseTopNavScreen):
    def __post_init__(self):
        self.title = _("Powering Off")
        self.show_back_button = False
        super().__post_init__()

        self.components.append(TextArea(
            text=_("Please wait about 30 seconds before disconnecting power."),
            screen_y=self.top_nav.height,
            height=self.canvas_height - self.top_nav.height,
        ))
