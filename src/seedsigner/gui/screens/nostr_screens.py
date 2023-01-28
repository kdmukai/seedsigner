from dataclasses import dataclass
from datetime import datetime
from typing import List
from seedsigner.gui.components import Button, CheckboxButton, FontAwesomeIconConstants, GUIConstants, Icon, IconButton, TextArea

from seedsigner.gui.screens.screen import BaseTopNavScreen, ButtonListScreen, WarningEdgesMixin
from seedsigner.hardware.buttons import HardwareButtonsConstants



NOSTR_BACKGROUND_COLOR = "#5d006f"
NOSTR_ACCENT_COLOR = "#dd23ef"



@dataclass
class NostrButtonListScreen(ButtonListScreen):
    def __post_init__(self):
        # Lock in overrided defaults
        self.top_nav_background_color = NOSTR_BACKGROUND_COLOR
        self.top_nav_button_selected_color = NOSTR_ACCENT_COLOR
        self.button_selected_color = NOSTR_ACCENT_COLOR
        super().__post_init__()



@dataclass
class NostrBaseTopNavScreen(BaseTopNavScreen):
    def __post_init__(self):
        # Lock in overrided defaults
        self.top_nav_background_color = NOSTR_BACKGROUND_COLOR
        self.top_nav_button_selected_color = NOSTR_ACCENT_COLOR
        super().__post_init__()



"""****************************************************************************
    NIP-26 Delegation
****************************************************************************"""
@dataclass
class NostrNIP26DelegationStartScreen(NostrButtonListScreen):
    npub: str = None

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        super().__post_init__()

        keytype = TextArea(
            text="Delegate on behalf of:",
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        self.components.append(keytype)

        key_display = TextArea(
            text=self.npub,
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_color=NOSTR_ACCENT_COLOR,
            font_size=GUIConstants.BODY_FONT_SIZE + 10,
            is_text_centered=True,
        )
        key_display.screen_y = keytype.screen_y + keytype.height + int((self.buttons[0].screen_y - (keytype.screen_y + keytype.height) - key_display.height)/2)
        self.components.append(key_display)



@dataclass
class NostrNIP26TokenKindsScreen(NostrButtonListScreen):
    """
        Simplified version of the SettingsEntryUpdateSelectionScreen
    """
    checked_buttons: List[int] = None
    selected_button: int = 0

    def __post_init__(self):
        self.is_bottom_list = True
        self.use_checked_selection_buttons = True
        self.Button_cls = CheckboxButton
        super().__post_init__()

        button = Button(
            text="Next",
            screen_x=GUIConstants.EDGE_PADDING,
            scroll_y=self.buttons[-1].scroll_y,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        button.screen_y = self.buttons[-1].screen_y + GUIConstants.BUTTON_HEIGHT + GUIConstants.LIST_ITEM_PADDING

        self.buttons.append(button)



@dataclass
class NostrNIP26CreateTokenCreatedAtScreen(NostrBaseTopNavScreen):
    initial_date: datetime = None

    def __post_init__(self):
        super().__post_init__()

        self.digit_buttons: List[List[Button]] = [
            [],  # UP row
            [],  # DOWN row
        ]
        self.cur_digit_button = [0, 1]

        self.year = self.initial_date.year
        self.month = self.initial_date.month
        self.day = self.initial_date.day

        digit_font_size = GUIConstants.BODY_FONT_MAX_SIZE + 12

        self.year_display = TextArea(
            text=str(self.year),
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=digit_font_size,
            font_color=NOSTR_ACCENT_COLOR,
            is_text_centered=True,
            background_color="#080808",
            width=int(digit_font_size * 2.5),
            height=int(1.5*digit_font_size),
            edge_padding=0,
            screen_x=GUIConstants.EDGE_PADDING + int(0.5*digit_font_size),
            screen_y=self.top_nav.height + int(1.5*digit_font_size),
        )
        self.components.append(self.year_display)

        self.month_display = TextArea(
            text=f"{self.month:02}",
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=digit_font_size,
            font_color=NOSTR_ACCENT_COLOR,
            is_text_centered=True,
            background_color="#080808",
            width=int(digit_font_size * 1.5),
            height=int(1.5*digit_font_size),
            edge_padding=0,
            screen_x=self.year_display.screen_x + int(digit_font_size * 2.5) + GUIConstants.COMPONENT_PADDING,
            screen_y=self.year_display.screen_y,
        )
        self.components.append(self.month_display)

        self.day_display = TextArea(
            text=f"{self.day:02}",
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=digit_font_size,
            font_color=NOSTR_ACCENT_COLOR,
            is_text_centered=True,
            background_color="#080808",
            width=int(digit_font_size * 1.5),
            height=int(1.5*digit_font_size),
            edge_padding=0,
            screen_x=self.month_display.screen_x + int(digit_font_size * 1.5) + GUIConstants.COMPONENT_PADDING,
            screen_y=self.year_display.screen_y,
        )
        self.components.append(self.day_display)


        self.next_button = Button(
            text="Next",
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=self.canvas_height - GUIConstants.BUTTON_HEIGHT - GUIConstants.EDGE_PADDING,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        self.components.append(self.next_button)


        digit_button_width = digit_font_size
        self.year_up_button = IconButton(
            icon_name=FontAwesomeIconConstants.CARET_UP,
            width=digit_button_width,
            screen_x=self.year_display.screen_x + int(0.75*digit_font_size),
            screen_y=self.year_display.screen_y - GUIConstants.BUTTON_HEIGHT - GUIConstants.COMPONENT_PADDING,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        self.components.append(self.year_up_button)
        self.digit_buttons[0].append(self.year_up_button)

        self.year_down_button = IconButton(
            icon_name=FontAwesomeIconConstants.CARET_DOWN,
            width=digit_button_width,
            screen_x=self.year_up_button.screen_x,
            screen_y=self.year_display.screen_y + self.year_display.height + GUIConstants.COMPONENT_PADDING,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        self.components.append(self.year_down_button)
        self.digit_buttons[1].append(self.year_down_button)


        self.month_up_button = IconButton(
            icon_name=FontAwesomeIconConstants.CARET_UP,
            width=digit_button_width,
            screen_x=self.month_display.screen_x + int(0.25*digit_font_size),
            screen_y=self.year_up_button.screen_y,
            is_selected=True,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        self.components.append(self.month_up_button)
        self.digit_buttons[0].append(self.month_up_button)

        self.month_down_button = IconButton(
            icon_name=FontAwesomeIconConstants.CARET_DOWN,
            width=digit_button_width,
            screen_x=self.month_up_button.screen_x,
            screen_y=self.year_down_button.screen_y,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        self.components.append(self.month_down_button)
        self.digit_buttons[1].append(self.month_down_button)


        self.day_up_button = IconButton(
            icon_name=FontAwesomeIconConstants.CARET_UP,
            width=digit_button_width,
            screen_x=self.day_display.screen_x + int(0.25*digit_font_size),
            screen_y=self.year_up_button.screen_y,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        self.components.append(self.day_up_button)
        self.digit_buttons[0].append(self.day_up_button)

        self.day_down_button = IconButton(
            icon_name=FontAwesomeIconConstants.CARET_DOWN,
            width=digit_button_width,
            screen_x=self.day_up_button.screen_x,
            screen_y=self.year_down_button.screen_y,
            selected_color=NOSTR_ACCENT_COLOR,
        )
        self.components.append(self.day_down_button)
        self.digit_buttons[1].append(self.day_down_button)


    def get_cur_selected_button(self) -> Button:
        if self.cur_digit_button is not None:
            return self.digit_buttons[self.cur_digit_button[0]][self.cur_digit_button[1]]
        elif self.next_button.is_selected:
            return self.next_button
    
    @property
    def is_in_up_row(self):
        return self.cur_digit_button is not None and self.cur_digit_button[0] == 0

    @property
    def is_in_down_row(self):
        return self.cur_digit_button is not None and self.cur_digit_button[0] == 1

    @property
    def is_in_year_col(self):
        return self.cur_digit_button is not None and self.cur_digit_button[1] == 0

    @property
    def is_in_month_col(self):
        return self.cur_digit_button is not None and self.cur_digit_button[1] == 1

    @property
    def is_in_day_col(self):
        return self.cur_digit_button is not None and self.cur_digit_button[1] == 2



    def _run(self):
        while True:
            user_input = self.hw_inputs.wait_for(
                [
                    HardwareButtonsConstants.KEY_UP,
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY_LEFT,
                    HardwareButtonsConstants.KEY_RIGHT,
                ] + HardwareButtonsConstants.KEYS__ANYCLICK,
                check_release=True,
                release_keys=HardwareButtonsConstants.KEYS__ANYCLICK
            )

            with self.renderer.lock:
                if user_input == HardwareButtonsConstants.KEY_UP:
                    if self.top_nav.is_selected:
                        # Can't go up any further
                        continue
                    elif self.is_in_up_row:
                        self.get_cur_selected_button().is_selected = False
                        self.get_cur_selected_button().render()

                        self.cur_digit_button[0] = None

                        self.top_nav.is_selected = True
                        self.top_nav.render_buttons()

                    elif self.is_in_down_row:
                        self.get_cur_selected_button().is_selected = False
                        self.get_cur_selected_button().render()

                        # enter the increment row
                        self.cur_digit_button[0] = 0
                        self.get_cur_selected_button().is_selected = True
                        self.get_cur_selected_button().render()

                    elif self.next_button.is_selected:
                        # "Next" button is selected
                        self.next_button.is_selected = False
                        self.next_button.render()

                        # enter the decrement row
                        self.cur_digit_button[0] = 1
                        self.get_cur_selected_button().is_selected = True
                        self.get_cur_selected_button().render()

                elif user_input == HardwareButtonsConstants.KEY_DOWN:
                    if self.next_button.is_selected:
                        # Already at the bottom of the list. Nowhere to go. 
                        continue

                    if self.top_nav.is_selected:
                        self.top_nav.is_selected = False
                        self.top_nav.render_buttons()

                        # The previous increment row cur_digit_button should be re-selected
                        self.cur_digit_button[0] = 0

                        self.get_cur_selected_button().is_selected = True
                        self.get_cur_selected_button().render()

                    elif self.is_in_up_row:
                        self.get_cur_selected_button().is_selected = False
                        self.get_cur_selected_button().render()

                        # enter the decrement row
                        self.cur_digit_button[0] = 1
                        self.get_cur_selected_button().is_selected = True
                        self.get_cur_selected_button().render()
                    
                    elif self.is_in_down_row:
                        self.get_cur_selected_button().is_selected = False
                        self.get_cur_selected_button().render()

                        self.cur_digit_button[0] = None

                        self.next_button.is_selected = True
                        self.next_button.render()
                
                elif user_input == HardwareButtonsConstants.KEY_LEFT:
                    if self.top_nav.is_selected or self.next_button.is_selected or self.is_in_year_col:
                        # Nowhere to go left
                        continue

                    else:
                        self.get_cur_selected_button().is_selected = False
                        self.get_cur_selected_button().render()

                        # move left
                        self.cur_digit_button[1] -= 1
                        self.get_cur_selected_button().is_selected = True
                        self.get_cur_selected_button().render()

                elif user_input == HardwareButtonsConstants.KEY_RIGHT:
                    if self.top_nav.is_selected or self.next_button.is_selected or self.is_in_day_col:
                        # Nowhere to go right
                        continue

                    else:
                        self.get_cur_selected_button().is_selected = False
                        self.get_cur_selected_button().render()

                        # move right
                        self.cur_digit_button[1] += 1
                        self.get_cur_selected_button().is_selected = True
                        self.get_cur_selected_button().render()

                elif user_input in HardwareButtonsConstants.KEYS__ANYCLICK:
                    if self.top_nav.is_selected:
                        return self.top_nav.selected_button

                    elif self.next_button.is_selected:
                        return [self.year, self.month, self.day]
                    
                    else:
                        if self.is_in_year_col:
                            if self.is_in_up_row:
                                self.year += 1
                            else:
                                self.year -= 1
                                if self.year < 2023:
                                    self.year = 2023
                            
                            # Hack to get dynamically updateable TextAreas
                            self.year_display.text_lines[0]["text"] = str(self.year)
                            self.year_display.render()

                        elif self.is_in_month_col:
                            if self.is_in_up_row:
                                self.month += 1
                                if self.month > 12:
                                    self.month = 1
                            else:
                                self.month -= 1
                                if self.month == 0:
                                    self.month = 12
                            
                            # Hack to get dynamically updateable TextAreas
                            self.month_display.text_lines[0]["text"] = f"{self.month:02}"
                            self.month_display.render()

                        elif self.is_in_day_col:
                            if self.is_in_up_row:
                                self.day += 1
                                if self.day > 31:
                                    self.day = 1
                            else:
                                self.day -= 1
                                if self.day == 0:
                                    self.day = 31

                            # Hack to get dynamically updateable TextAreas
                            self.day_display.text_lines[0]["text"] = f"{self.day:02}"
                            self.day_display.render()
                # Write the screen updates
                self.renderer.show_image()



@dataclass
class NostrNIP26SelectDelegateeScreen(NostrButtonListScreen):
    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        super().__post_init__()

        details = TextArea(
            text="Select or scan the pubkey that will be authorized to sign on your behalf.",
            is_text_centered=True,
            screen_y=self.top_nav.height + int(1.5*GUIConstants.COMPONENT_PADDING)
        )
        self.components.append(details)



@dataclass
class NostrNIP26ReviewDelegateeScreen(NostrButtonListScreen):
    delegator_npub: str = None
    delegatee_npub: str = None

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        self.button_data = ["Next"]

        super().__post_init__()

        details = TextArea(
            text="Will authorize:",
            is_text_centered=True,
            screen_y=self.top_nav.height + int(1.5*GUIConstants.COMPONENT_PADDING)
        )
        self.components.append(details)

        text = f"npub:{self.delegatee_npub[4:15]}" + "\n" + "..." + self.delegatee_npub[-13:]
        delegatee = TextArea(
            text=text,
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_size=GUIConstants.BODY_FONT_MAX_SIZE + 2,
            font_color=NOSTR_ACCENT_COLOR,
            is_text_centered=True,
            screen_y=details.screen_y + details.height + GUIConstants.COMPONENT_PADDING,
        )
        self.components.append(delegatee)

        details2 = TextArea(
            text="To sign on behalf of:",
            is_text_centered=True,
            screen_y=delegatee.screen_y + delegatee.height + 2*GUIConstants.COMPONENT_PADDING
        )
        self.components.append(details2)

        delegator = TextArea(
            text=f"npub:{self.delegator_npub[4:13]}",
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_size=GUIConstants.BODY_FONT_MAX_SIZE + 2,
            font_color=NOSTR_ACCENT_COLOR,
            is_text_centered=True,
            screen_y=details2.screen_y + details2.height + GUIConstants.COMPONENT_PADDING,
        )
        self.components.append(delegator)



@dataclass
class NostrNIP26ReviewKindsScreen(NostrButtonListScreen):
    kinds: List[str] = None

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        self.button_data = ["Next"]

        super().__post_init__()

        details = TextArea(
            text="Will authorize event kinds:",
            is_text_centered=False,
            screen_y=self.top_nav.height + int(1.5*GUIConstants.COMPONENT_PADDING)
        )
        self.components.append(details)

        text = ""
        for kind in self.kinds:
            text += kind + "\n"
        kinds = TextArea(
            text=text,
            # font_size=GUIConstants.BODY_FONT_MAX_SIZE,
            font_color=NOSTR_ACCENT_COLOR,
            is_text_centered=False,
            screen_y=details.screen_y + details.height + GUIConstants.COMPONENT_PADDING,
        )
        self.components.append(kinds)



@dataclass
class NostrNIP26ReviewCreatedAtScreen(NostrButtonListScreen):
    valid_from: int = None
    valid_until: int = None

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        super().__post_init__()

        screen_y = self.top_nav.height + int(1.5*GUIConstants.COMPONENT_PADDING)
        if self.valid_from:
            details = TextArea(
                text="Valid from:",
                is_text_centered=True,
                screen_y=screen_y
            )
            self.components.append(details)

            timestamp = TextArea(
                text=datetime.fromtimestamp(self.valid_from).strftime('%Y-%m-%d %H:%M:%S'),
                font_size=GUIConstants.BODY_FONT_MAX_SIZE + 2,
                font_color=NOSTR_ACCENT_COLOR,
                is_text_centered=True,
                screen_y=details.screen_y + details.height + GUIConstants.COMPONENT_PADDING,
            )
            self.components.append(timestamp)

            screen_y = timestamp.screen_y + timestamp.height + 2*GUIConstants.COMPONENT_PADDING
        
        if self.valid_until:
            details = TextArea(
                text="Expires at:",
                is_text_centered=True,
                screen_y=screen_y
            )
            self.components.append(details)

            timestamp = TextArea(
                text=datetime.fromtimestamp(self.valid_until).strftime('%Y-%m-%d %H:%M:%S'),
                font_size=GUIConstants.BODY_FONT_MAX_SIZE + 2,
                font_color=NOSTR_ACCENT_COLOR,
                is_text_centered=True,
                screen_y=details.screen_y + details.height + GUIConstants.COMPONENT_PADDING,
            )
            self.components.append(timestamp)



@dataclass
class NostrNIP26PromptExportUnsignedDelegationScreen(NostrButtonListScreen):
    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        super().__post_init__()

        details = TextArea(
            text="Export this new (unsigned) delegation token to your Nostr client app.",
            is_text_centered=True,
            screen_y=self.top_nav.height + int(1.5*GUIConstants.COMPONENT_PADDING)
        )
        self.components.append(details)



@dataclass
class NostrNIP26PromptSignTokenScreen(NostrButtonListScreen):
    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        super().__post_init__()

        icon = Icon(
            icon_name=FontAwesomeIconConstants.PAPER_PLANE,
            icon_color=GUIConstants.SUCCESS_COLOR,
            icon_size=GUIConstants.ICON_LARGE_BUTTON_SIZE,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        icon.screen_x = int((self.canvas_width - icon.width)/2)
        self.components.append(icon)

        self.components.append(TextArea(
            text="Click to authorize this delegation",
            screen_y=icon.screen_y + icon.height + GUIConstants.COMPONENT_PADDING
        ))



"""****************************************************************************
    Sign Event
****************************************************************************"""
@dataclass
class NostrSignEventStartScreen(NostrButtonListScreen):
    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        self.button_data = [("Scan", FontAwesomeIconConstants.QRCODE)]

        super().__post_init__()

        self.components.append(TextArea(
            text="Scan the event json or its serialized form",
            is_text_centered=True,
            screen_y=self.top_nav.height + 3*GUIConstants.COMPONENT_PADDING
        ))



@dataclass
class NostrSignEventReviewScreen(NostrButtonListScreen):
    kind: str = None
    content: str = None

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        self.button_data = [("Sign", FontAwesomeIconConstants.PAPER_PLANE)]

        super().__post_init__()

        text = f"kind: {self.kind}" + "\n"
        text += "content: " + self.content

        self.components.append(TextArea(
            text=text,
            is_text_centered=False,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING,
            allow_text_overflow=True,
        ))



"""****************************************************************************
    npub / nsec Display and Export
****************************************************************************"""
@dataclass
class NostrBech32KeyDisplayScreen(NostrButtonListScreen):
    key: str = None
    is_pubkey: bool = True

    def __post_init__(self):
        # Customize defaults
        self.button_data = ["Next"]
        self.is_bottom_list = True

        super().__post_init__()

        keytype = TextArea(
            text="Public key:" if self.is_pubkey else "Private key:",
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        self.components.append(keytype)

        key_display = TextArea(
            text=f"{self.key[:14]}\n...{self.key[-10:]}",
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_color=NOSTR_ACCENT_COLOR,
            font_size=GUIConstants.BODY_FONT_SIZE + 12,
            is_text_centered=True,
        )
        key_display.screen_y = keytype.screen_y + keytype.height + int((self.buttons[0].screen_y - (keytype.screen_y + keytype.height) - key_display.height)/2)
        self.components.append(key_display)



@dataclass
class NostrPrivateKeyDisplayScreen(WarningEdgesMixin, NostrBech32KeyDisplayScreen):
    status_color: str = GUIConstants.DIRE_WARNING_COLOR
    is_pubkey: bool = False