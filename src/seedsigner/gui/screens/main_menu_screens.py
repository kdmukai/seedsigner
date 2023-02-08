
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
