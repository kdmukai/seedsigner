import pytest
from mock import Mock, patch

from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.hardware.buttons import HardwareButtons
from seedsigner.hardware.camera import Camera
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views import main_menu_views, scan_views, seed_views, settings_views, tools_views
from seedsigner.views.view import View

from .utils import ScreenshotComplete, ScreenshotRenderer


def test_generate_screenshots():
    """
        The `Renderer` class is mocked so that calls in the normal code are ignored
        (necessary to avoid having it trying to wire up hardware dependencies).

        When the `Renderer` instance is needed, we patch in our own test-only
        `ScreenshotRenderer`.
    """
    # Disable hardware dependencies by essentially wiping out this class
    HardwareButtons.get_instance = Mock()
    Camera.get_instance = Mock()

    # Prep the ScreenshotRenderer that will be patched over the normal Renderer
    ScreenshotRenderer.configure_instance(screenshot_path="/Users/kdmukai/Downloads")
    screenshot_renderer: ScreenshotRenderer = ScreenshotRenderer.get_instance()

    # Replace the core `Singleton` calls so that only our ScreenshotRenderer is used.
    Renderer.configure_instance = Mock()
    Renderer.get_instance = Mock(return_value=screenshot_renderer)

    Settings.get_instance().set_value(SettingsConstants.SETTING__LOCALE, value=SettingsConstants.LOCALE__ARABIC)

    def screencap_view(view_cls: View, view_args: dict={}):
        screenshot_renderer.set_screenshot_filename(view_cls.__name__ + ".png")

        with pytest.raises(ScreenshotComplete):
            view_cls(**view_args).run()

    screenshot_list = [
        main_menu_views.MainMenuView,
        main_menu_views.PowerOffView,

        (scan_views.SettingsUpdatedView, dict(config_name="Keith's Settings")),

        seed_views.LoadSeedView,
        seed_views.SeedMnemonicEntryView,
        seed_views.SeedMnemonicInvalidView,
        (seed_views.SeedWordsWarningView, dict(seed_num=0)),

        settings_views.SettingsMenuView,
        (settings_views.SettingsEntryUpdateSelectionView, dict(attr_name=SettingsConstants.SETTING__BTC_DENOMINATION)),
        settings_views.IOTestView,
        settings_views.DonateView,

        tools_views.ToolsMenuView,
        tools_views.ToolsDiceEntropyMnemonicLengthView,
        (tools_views.ToolsDiceEntropyEntryView, dict(total_rolls=50)),
    ]

    for screenshot in screenshot_list:
        if type(screenshot) == tuple:
            view_cls, view_args = screenshot
        else:
            view_cls = screenshot
            view_args = {}
        screencap_view(view_cls, view_args)
