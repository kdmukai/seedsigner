from seedsigner.helpers import nostr
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonListScreen, QRDisplayScreen
from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.qr_type import QRType
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.view import BackStackView, Destination, View



class NostrKeyOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        EXPORT_PRIVATE_KEY = "Export private key"
        EXPORT_PUBLIC_KEY = "Export public key"

        button_data = [EXPORT_PRIVATE_KEY, EXPORT_PUBLIC_KEY]

        selected_menu_num = ButtonListScreen(
            title="Nostr Key Options",
            button_data=button_data,
            is_bottom_list=True,
            is_button_text_centered=False,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == EXPORT_PRIVATE_KEY:
            return Destination(NostrKeyDisplayView, view_args=dict(seed_num=self.seed_num, is_pubkey=False))

        elif button_data[selected_menu_num] == EXPORT_PUBLIC_KEY:
            return Destination(NostrKeyDisplayView, view_args=dict(seed_num=self.seed_num, is_pubkey=True))



class NostrKeyDisplayView(View):
    def __init__(self, seed_num: int, is_pubkey: bool = True):
        super().__init__()
        self.seed_num = seed_num
        self.is_pubkey = is_pubkey

        seed = self.controller.get_seed(seed_num)
        if is_pubkey:
            self.key = nostr.get_nostr_public_key(seed.seed_bytes)
        else:
            self.key = nostr.get_nostr_private_key(seed.seed_bytes)


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrPublicKeyDisplayScreen, NostrPrivateKeyDisplayScreen

        if self.is_pubkey:
            selected_menu_num = NostrPublicKeyDisplayScreen(
                title="Nostr Key Export",
                key=self.key,
            ).display()
        else:
            selected_menu_num = NostrPrivateKeyDisplayScreen(
                title="Nostr Key Export",
                key=self.key,
            ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        return Destination(NostrKeyExportQRView, view_args=dict(seed_num=self.seed_num, is_pubkey=self.is_pubkey))



class NostrKeyExportQRView(View):
    def __init__(self, seed_num: int, is_pubkey: bool = True):
        super().__init__()
        self.seed_num = seed_num
        seed = self.controller.get_seed(seed_num)

        if is_pubkey:
            data = nostr.get_nostr_public_key(seed.seed_bytes)
        else:
            data = nostr.get_nostr_private_key(seed.seed_bytes)

        qr_density = self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY)
        qr_type = QRType.GENERIC__STATIC

        self.qr_encoder = EncodeQR(
            data=data,
            qr_type=qr_type,
            qr_density=qr_density,
        )


    def run(self):
        QRDisplayScreen(qr_encoder=self.qr_encoder).display()

        return Destination(NostrKeyOptionsView, view_args=dict(seed_num=self.seed_num), skip_current_view=True, clear_history=True)
