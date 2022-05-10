import os
import pathlib
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
    screenshot_root = "/Users/kdmukai/dev/seedsigner_screenshots"
    ScreenshotRenderer.configure_instance()
    screenshot_renderer: ScreenshotRenderer = ScreenshotRenderer.get_instance()

    # Replace the core `Singleton` calls so that only our ScreenshotRenderer is used.
    Renderer.configure_instance = Mock()
    Renderer.get_instance = Mock(return_value=screenshot_renderer)

    # Parse the main `babel/messages.pot` for overall stats
    messages_source_path = os.path.join(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve(), "babel", "messages.pot")
    with open(messages_source_path, 'r') as messages_source_file:
        num_source_messages = messages_source_file.read().count("msgid \"") - 1

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

    main_readme = """# SeedSigner Screenshots \n\n"""

    for locale, display_name in SettingsConstants.ALL_LOCALES:
        Settings.get_instance().set_value(SettingsConstants.SETTING__LOCALE, value=locale)
        screenshot_renderer.set_screenshot_path(os.path.join(screenshot_root, locale))

        main_readme += f"* [{display_name}]({locale}/README.md)\n"
        locale_readme = f"""# SeedSigner Screenshots: {display_name}\n"""

        # Report the translation progress
        if locale != SettingsConstants.LOCALE__ENGLISH:
            translated_messages_path = os.path.join(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve(), "src", "seedsigner", "resources", "babel", locale, "LC_MESSAGES", "messages.po") 
            with open(translated_messages_path, 'r') as translation_file:
                locale_translations = translation_file.read()
                num_locale_translations = locale_translations.count("msgid \"") - locale_translations.count("""msgstr ""\n\n""") - 1

            locale_readme += f"Translation progress: {num_locale_translations / num_source_messages:.1%}\n\n"
            locale_readme += "---\n\n"

        for screenshot in screenshot_list:
            if type(screenshot) == tuple:
                view_cls, view_args = screenshot
            else:
                view_cls = screenshot
                view_args = {}
            screencap_view(view_cls, view_args)
            locale_readme += f"{view_cls.__name__}:\n\n"
            locale_readme += f"""<img src="{view_cls.__name__}.png">\n\n"""
            locale_readme += "---\n\n"

        with open(os.path.join(screenshot_renderer.screenshot_path, "README.md"), 'w') as readme_file:
            readme_file.write(locale_readme)

    with open(os.path.join(screenshot_root, "README.md"), 'w') as readme_file:
        readme_file.write(main_readme)
