

from dataclasses import dataclass
from typing import List
from seedsigner.gui.components import FontAwesomeIconConstants, GUIConstants, TextArea

from seedsigner.gui.screens.screen import ButtonListScreen, WarningEdgesMixin



@dataclass
class NostrNIP26DelegationStartScreen(ButtonListScreen):
    npub: str = None

    def __post_init__(self):
        # Customize defaults
        self.button_data = [("Scan delegation", FontAwesomeIconConstants.QRCODE)]
        self.is_bottom_list = True

        super().__post_init__()

        keytype = TextArea(
            text="Delegate on behalf of:",
            is_text_centered=True,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        self.components.append(keytype)

        key_display = TextArea(
            text=f"{self.npub}...",
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_color=GUIConstants.ACCENT_COLOR,
            font_size=GUIConstants.BODY_FONT_SIZE + 12,
            is_text_centered=True,
        )
        key_display.screen_y = keytype.screen_y + keytype.height + int((self.buttons[0].screen_y - (keytype.screen_y + keytype.height) - key_display.height)/2)
        self.components.append(key_display)



@dataclass
class NostrNIP26DelegationTokenScreen(ButtonListScreen):
    delegator_npub: str = None
    delegatee_npub: str = None
    conditions: List[str] = None

    def __post_init__(self):
        # Customize defaults
        self.is_bottom_list = True
        self.button_data = [("Sign delegation", FontAwesomeIconConstants.PEN)]

        super().__post_init__()

        text = f"Allow: {self.delegatee_npub}\n"
        text += f"To post on behalf of: {self.delegator_npub}\n"
        text += f"""Conditions: {", ".join(self.conditions)}"""
        details = TextArea(
            text=text,
            is_text_centered=False,
            screen_y=self.top_nav.height + GUIConstants.COMPONENT_PADDING
        )
        self.components.append(details)



@dataclass
class NostrPublicKeyDisplayScreen(ButtonListScreen):
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
            text=f"{self.key[:10]}...\n...{self.key[-10:]}",
            font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
            font_color=GUIConstants.ACCENT_COLOR,
            font_size=GUIConstants.BODY_FONT_SIZE + 12,
            is_text_centered=True,
        )
        key_display.screen_y = keytype.screen_y + keytype.height + int((self.buttons[0].screen_y - (keytype.screen_y + keytype.height) - key_display.height)/2)
        self.components.append(key_display)



@dataclass
class NostrPrivateKeyDisplayScreen(WarningEdgesMixin, NostrPublicKeyDisplayScreen):
    status_color: str = GUIConstants.DIRE_WARNING_COLOR
    is_pubkey: bool = False