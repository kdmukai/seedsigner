from seedsigner.controller import Controller
from seedsigner.gui.components import FontAwesomeIconConstants
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
        NIP_26_DELEGATION = "NIP-26 delegation"
        DERIVE_CHILD_KEY = "Derive child key"
        EXPORT_PUBLIC_KEY = "Export public key"
        EXPORT_PRIVATE_KEY = ("Export private key", FontAwesomeIconConstants.TRIANGLE_EXCLAMATION)

        button_data = [NIP_26_DELEGATION, DERIVE_CHILD_KEY, EXPORT_PUBLIC_KEY, EXPORT_PRIVATE_KEY]

        selected_menu_num = ButtonListScreen(
            title="Nostr Key Options",
            button_data=button_data,
            is_bottom_list=True,
            is_button_text_centered=False,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == NIP_26_DELEGATION:
            return Destination(NostrNIP26DelegationStartView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == EXPORT_PRIVATE_KEY:
            return Destination(NostrKeyDisplayView, view_args=dict(seed_num=self.seed_num, is_pubkey=False))

        elif button_data[selected_menu_num] == EXPORT_PUBLIC_KEY:
            return Destination(NostrKeyDisplayView, view_args=dict(seed_num=self.seed_num, is_pubkey=True))



class NostrNIP26DelegationStartView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
    

    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26DelegationStartScreen
        selected_menu_num = NostrNIP26DelegationStartScreen(
            title="NIP-26 Delegation",
            npub=nostr.get_npub(nostr.derive_nostr_root(self.controller.storage.seeds[self.seed_num].seed_bytes).secret)[:10]
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            from seedsigner.views.scan_views import ScanView
            self.controller.nostr_data = dict(seed_num=self.seed_num)
            self.controller.resume_main_flow = Controller.FLOW__NOSTR__NIP26_DELEGATION
            return Destination(ScanView)



class NostrNIP26DelegationTokenView(View):
    def __init__(self, delegation_token: str):
        super().__init__()
        self.delegation_token = delegation_token
        self.parsed_token = nostr.parse_nip26_delegation_token(delegation_token)

        self.seed_num = self.controller.nostr_data["seed_num"]
        self.controller.nostr_data = None
        self.controller.resume_main_flow = None


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26DelegationTokenScreen
        selected_menu_num = NostrNIP26DelegationTokenScreen(
            title="NIP-26 Delegation",
            delegator_npub=nostr.get_npub(nostr.derive_nostr_root(self.controller.storage.seeds[self.seed_num].seed_bytes).secret)[:10],
            delegatee_npub=self.parsed_token["delegatee_npub"][:32],
            conditions=self.parsed_token["conditions"],
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        return Destination(NostrNIP26SignedTokenExportQRView, view_args=dict(seed_num=self.seed_num, delegation_token=self.delegation_token))



class NostrNIP26SignedTokenExportQRView(View):
    def __init__(self, seed_num: int, delegation_token: str):
        super().__init__()
        self.seed_num = seed_num
        # self.data = nostr.sign_nip26_delegation(nostr.derive_nostr_root(self.controller.storage.seeds[self.seed_num].seed_bytes).secret, delegation_token)
        self.data = nostr.sign_message(nostr.derive_nostr_root(self.controller.storage.seeds[self.seed_num].seed_bytes).secret, message=delegation_token)

        qr_density = self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY)
        qr_type = QRType.GENERIC__STATIC

        self.qr_encoder = EncodeQR(
            data=self.data,
            qr_type=qr_type,
            qr_density=qr_density,
        )


    def run(self):
        QRDisplayScreen(qr_encoder=self.qr_encoder).display()

        return Destination(NostrKeyOptionsView, view_args=dict(seed_num=self.seed_num), skip_current_view=True, clear_history=True)




class NostrKeyDisplayView(View):
    def __init__(self, seed_num: int, is_pubkey: bool = True):
        super().__init__()
        self.seed_num = seed_num
        self.is_pubkey = is_pubkey

        seed = self.controller.get_seed(seed_num)
        if is_pubkey:
            self.key = nostr.get_npub(nostr.derive_nostr_root(seed.seed_bytes).secret)
        else:
            self.key = nostr.get_nsec(nostr.derive_nostr_root(seed.seed_bytes).secret)


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrPublicKeyDisplayScreen, NostrPrivateKeyDisplayScreen

        if self.is_pubkey:
            selected_menu_num = NostrPublicKeyDisplayScreen(
                title="Nostr npub Export",
                key=self.key,
            ).display()
        else:
            selected_menu_num = NostrPrivateKeyDisplayScreen(
                title="Nostr nsec Export",
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
            data = nostr.get_npub(seed.seed_bytes)
        else:
            data = nostr.get_nsec(seed.seed_bytes)

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
