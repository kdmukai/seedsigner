from binascii import a2b_base64
import logging
from embit.psbt import PSBT

from seedsigner.gui.components import SeedSignerIconConstants
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen, settings_screens)
from seedsigner.gui.screens.screen import QRDisplayScreen
from seedsigner.hardware.microsd import MicroSD
from seedsigner.models.encode_qr import UrPsbtQrEncoder
from seedsigner.models.settings import Settings, SettingsConstants, SettingsDefinition
from seedsigner.views.view import View, Destination, MainMenuView

logger = logging.getLogger(__name__)



class SettingsMenuView(View):
    IO_TEST = "I/O test"
    ANIMATED_QR_TEST = "Animated QR Test"
    DONATE = "Donate"

    def __init__(self, visibility: str = SettingsConstants.VISIBILITY__GENERAL, selected_attr: str = None, initial_scroll: int = 0):
        super().__init__()
        self.visibility = visibility
        self.selected_attr = selected_attr

        # Used to preserve the rendering position in the list
        self.initial_scroll = initial_scroll


    def run(self):
        settings_entries = SettingsDefinition.get_settings_entries(
            visibility=self.visibility
        )
        button_data=[e.display_name for e in settings_entries]

        selected_button = 0
        if self.selected_attr:
            for i, entry in enumerate(settings_entries):
                if entry.attr_name == self.selected_attr:
                    selected_button = i
                    break

        if self.visibility == SettingsConstants.VISIBILITY__GENERAL:
            title = "Settings"

            # Set up the next nested level of menuing
            button_data.append(("Advanced", None, None, None, SeedSignerIconConstants.CHEVRON_RIGHT))
            next_destination = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__ADVANCED})

            button_data.append(self.IO_TEST)
            button_data.append(self.ANIMATED_QR_TEST)
            button_data.append(self.DONATE)

        elif self.visibility == SettingsConstants.VISIBILITY__ADVANCED:
            title = "Advanced"

            # So far there are no real Developer options; disabling for now
            # button_data.append(("Developer Options", None, None, None, SeedSignerIconConstants.CHEVRON_RIGHT))
            # next_destination = Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__DEVELOPER})
            next_destination = None
        
        elif self.visibility == SettingsConstants.VISIBILITY__DEVELOPER:
            title = "Dev Options"
            next_destination = None

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=title,
            is_button_text_centered=False,
            button_data=button_data,
            selected_button=selected_button,
            scroll_y_initial_offset=self.initial_scroll,
        )

        # Preserve our scroll position in this Screen so we can return
        initial_scroll = self.screen.buttons[0].scroll_y

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            if self.visibility == SettingsConstants.VISIBILITY__GENERAL:
                return Destination(MainMenuView)
            elif self.visibility == SettingsConstants.VISIBILITY__ADVANCED:
                return Destination(SettingsMenuView)
            else:
                return Destination(SettingsMenuView, view_args={"visibility": SettingsConstants.VISIBILITY__ADVANCED})
        
        elif selected_menu_num == len(settings_entries):
            return next_destination

        elif len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.IO_TEST:
            return Destination(IOTestView)

        elif len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.ANIMATED_QR_TEST:
            return Destination(AnimatedQRTestView)

        elif len(button_data) > selected_menu_num and button_data[selected_menu_num] == self.DONATE:
            return Destination(DonateView)

        else:
            return Destination(SettingsEntryUpdateSelectionView, view_args=dict(attr_name=settings_entries[selected_menu_num].attr_name, parent_initial_scroll=initial_scroll))



class SettingsEntryUpdateSelectionView(View):
    """
        Handles changes to all selection-type settings (Multiselect, SELECT_1,
        Enabled/Disabled, etc).
    """
    def __init__(self, attr_name: str, parent_initial_scroll: int = 0, selected_button: int = None):
        super().__init__()
        self.settings_entry = SettingsDefinition.get_settings_entry(attr_name)
        self.selected_button = selected_button
        self.parent_initial_scroll = parent_initial_scroll


    def run(self):
        initial_value = self.settings.get_value(self.settings_entry.attr_name)
        button_data = []
        checked_buttons = []
        for i, value in enumerate(self.settings_entry.selection_options):
            if type(value) == tuple:
                value, display_name = value
            else:
                display_name = value

            button_data.append(display_name)

            if (type(initial_value) == list and value in initial_value) or value == initial_value:
                checked_buttons.append(i)

                if self.selected_button is None:
                    # Highlight the selection (for multiselect highlight the first
                    # selected option).
                    self.selected_button = i
        
        if self.selected_button is None:
            self.selected_button = 0
            
        ret_value = self.run_screen(
            settings_screens.SettingsEntryUpdateSelectionScreen,
            display_name=self.settings_entry.display_name,
            help_text=self.settings_entry.help_text,
            button_data=button_data,
            selected_button=self.selected_button,
            checked_buttons=checked_buttons,
            settings_entry_type=self.settings_entry.type,
        )

        destination = None
        settings_menu_view_destination = Destination(
            SettingsMenuView,
            view_args={
                "visibility": self.settings_entry.visibility,
                "selected_attr": self.settings_entry.attr_name,
                "initial_scroll": self.parent_initial_scroll,
            }
        )

        if ret_value == RET_CODE__BACK_BUTTON:
            return settings_menu_view_destination

        value = self.settings_entry.get_selection_option_value(ret_value)

        if self.settings_entry.type == SettingsConstants.TYPE__FREE_ENTRY:
            updated_value = ret_value
            destination = settings_menu_view_destination

        elif self.settings_entry.type == SettingsConstants.TYPE__MULTISELECT:
            updated_value = list(initial_value)
            if ret_value not in checked_buttons:
                # This is a new selection to add
                updated_value.append(value)
            else:
                # This is a de-select to remove
                updated_value.remove(value)

        else:
            # All other types are single selects (e.g. Enabled/Disabled, SELECT_1)
            if value == initial_value:
                # No change, return to menu
                return settings_menu_view_destination
            else:
                updated_value = value

        self.settings.set_value(
            attr_name=self.settings_entry.attr_name,
            value=updated_value
        )

        if destination:
            return destination

        # All selects stay in place; re-initialize where in the list we left off
        self.selected_button = ret_value

        return Destination(SettingsEntryUpdateSelectionView, view_args=dict(attr_name=self.settings_entry.attr_name, parent_initial_scroll=self.parent_initial_scroll, selected_button=self.selected_button), skip_current_view=True)



class SettingsIngestSettingsQRView(View):
    def __init__(self, data: str):
        super().__init__()

        # May raise an Exception which will bubble up to the Controller to display to the
        # user.
        self.config_name, settings_update_dict = Settings.parse_settingsqr(data)
            
        self.settings.update(settings_update_dict)

        if MicroSD.get_instance().is_inserted and self.settings.get_value(SettingsConstants.SETTING__PERSISTENT_SETTINGS) == SettingsConstants.OPTION__ENABLED:
            self.status_message = "Persistent Settings enabled. Settings saved to SD card."
        else:
            self.status_message = "Settings updated in temporary memory"


    def run(self):
        from seedsigner.gui.screens.settings_screens import SettingsQRConfirmationScreen
        self.run_screen(
            SettingsQRConfirmationScreen,
            config_name=self.config_name,
            status_message=self.status_message,
        )

        # Only one exit point
        return Destination(MainMenuView)



"""****************************************************************************
    Misc
****************************************************************************"""
class IOTestView(View):
    def run(self):
        self.run_screen(settings_screens.IOTestScreen)

        return Destination(SettingsMenuView)


class AnimatedQRTestView(View):
    def run(self):
        base64_psbt = "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"
        psbt = PSBT.parse(a2b_base64(base64_psbt))

        qr_encoder = UrPsbtQrEncoder(
            psbt=psbt,
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
        )
        self.run_screen(QRDisplayScreen, qr_encoder=qr_encoder)

        return Destination(SettingsMenuView)


class DonateView(View):
    def run(self):
        self.run_screen(settings_screens.DonateScreen)

        return Destination(SettingsMenuView)
