from embit.bip32 import HDKey
from seedsigner.controller import Controller
from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.helpers import nostr
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonListScreen, QRDisplayScreen
from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.qr_type import QRType
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.view import BackStackView, Destination, View


class BaseNostrView(View):
    @property
    def seed_num(self) -> int:
        return self.controller.nostr_data["seed_num"]

    @property
    def nostr_root_pk(self) -> HDKey:
        return nostr.derive_nostr_root(self.controller.storage.seeds[self.seed_num].seed_bytes)
    
    @property
    def nostr_root_npub(self) -> str:
        return nostr.get_npub(self.nostr_root_pk.secret)

    @property
    def nostr_root_nsec(self) -> str:
        return nostr.get_nsec(self.nostr_root_pk.secret)



class NostrKeyOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        if self.controller.nostr_data is None:
            self.controller.nostr_data = {}
        self.controller.nostr_data["seed_num"] = seed_num


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
            return Destination(NostrNIP26DelegationStartView)

        elif button_data[selected_menu_num] == EXPORT_PUBLIC_KEY:
            return Destination(NostrKeyDisplayView, view_args=dict(is_pubkey=True))

        elif button_data[selected_menu_num] == EXPORT_PRIVATE_KEY:
            return Destination(NostrKeyDisplayView, view_args=dict(is_pubkey=False))



class NostrNIP26DelegationStartView(BaseNostrView):
    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26DelegationStartScreen

        CREATE = "Create NIP-26 token"
        SCAN = ("Scan NIP-26 token", FontAwesomeIconConstants.QRCODE)
        button_data = [CREATE, SCAN]

        selected_menu_num = NostrNIP26DelegationStartScreen(
            title="NIP-26 Delegation",
            button_data=button_data,
            npub=self.nostr_root_npub[:14]
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == CREATE:
            return Destination(NostrNIP25CreateTokenKindsView)

        elif button_data[selected_menu_num] == SCAN:
            from seedsigner.views.scan_views import ScanView
            self.controller.nostr_data = dict(seed_num=self.seed_num)
            self.controller.resume_main_flow = Controller.FLOW__NOSTR__NIP26_DELEGATION
            return Destination(ScanView)



class NostrNIP25CreateTokenKindsView(BaseNostrView):
    def __init__(self):
        super().__init__()
        self.selected_button = 0
        if "nip26_kinds" in self.controller.nostr_data:
            self.checked_buttons = self.controller.nostr_data["nip26_kinds"]
        else:
            self.checked_buttons = []


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26TokenKindsScreen

        button_data = [f"{kind[1]}: {kind[0]}" for kind in nostr.ALL_KINDS]

        # Re-use the Settings entry screen for MULTISELECT
        ret_value = NostrNIP26TokenKindsScreen(
            title="Allowed Kinds",
            button_data=button_data,
            checked_buttons=self.checked_buttons,
            selected_button=self.selected_button,
        ).display()

        if ret_value == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        if ret_value == len(nostr.ALL_KINDS):
            # "Next" click
            self.controller.nostr_data["nip26_kinds"] = sorted(self.checked_buttons)
            return Destination(NostrNIP26CreateTokenCreatedAt)
        
        if ret_value not in self.checked_buttons:
            # This is a new selection to add
            self.checked_buttons.append(ret_value)
        else:
            # This is a de-select to remove
            self.checked_buttons.remove(ret_value)

        # Stay in the multi-select Screen via recursion
        self.selected_button = ret_value
        return self.run()



class NostrNIP26CreateTokenCreatedAt(BaseNostrView):
    def run(self):
        from datetime import datetime, timezone
        import time
        from seedsigner.gui.screens.nostr_screens import NostrNIP26CreateTokenCreatedAtScreen
        ret_value = NostrNIP26CreateTokenCreatedAtScreen(
            title="Valid Until",
        ).display()

        if ret_value == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Otherwise returns a List[year, month, day]
        date_time = datetime(ret_value[0], ret_value[1], ret_value[2], 0, 0, 0).replace(tzinfo=timezone.utc)
        timestamp = int(time.mktime(date_time.timetuple()))
        self.controller.nostr_data["nip26_valid_until"] = timestamp

        return Destination(NostrNIP26SelectDelegateeView)



class NostrNIP26SelectDelegateeView(BaseNostrView):
    def run(self):
        SCAN = ("Scan npub", FontAwesomeIconConstants.QRCODE)
        CHILD = "Derive child seed"

        button_data = [SCAN, CHILD]
        selected_menu_num = ButtonListScreen(
            title="Select Delegatee",
            button_data=button_data,
            is_bottom_list=True,
            is_button_text_centered=False,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] == SCAN:
            from seedsigner.views.scan_views import ScanView
            self.controller.resume_main_flow = Controller.FLOW__NOSTR__NIP26_DELEGATION
            return Destination(ScanView)
        
        elif button_data[selected_menu_num] == CHILD:
            return Destination(None)



class NostrNIP26BuildToken(BaseNostrView):
    def __init__(self, npub: str):
        super().__init__()
        delegatee_pubkey = nostr.npub_to_hex(npub)
        token = nostr.assemble_nip26_delegation_token(
            delegatee_pubkey=delegatee_pubkey,
            kinds=self.controller.nostr_data["nip26_kinds"],
            valid_until=self.controller.nostr_data["nip26_valid_until"]
        )

        self.controller.nostr_data["nip26_delegatee"] = delegatee_pubkey
        self.controller.nostr_data["nip26_token"] = token

        self.controller.resume_main_flow = None


    def run(self):
        return Destination(NostrNIP26ReviewTokenView, skip_current_view=True)



class NostrNIP26ReviewTokenView(BaseNostrView):
    """ Can arrive here either by creating a delegation token or by scanning one in """
    def __init__(self, delegation_token: str = None):
        super().__init__()
        if delegation_token:
            self.delegation_token = delegation_token
        else:
            self.delegation_token = self.controller.nostr_data["nip26_token"]

        self.controller.resume_main_flow = None

        self.parsed_token = nostr.parse_nip26_delegation_token(self.delegation_token)


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26ReviewTokenScreen
        selected_menu_num = NostrNIP26ReviewTokenScreen(
            title="NIP-26 Delegation",
            delegator_npub=self.nostr_root_npub[:10],
            delegatee_npub=self.parsed_token["delegatee_npub"][:32],
            conditions=self.parsed_token["conditions"],
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        return Destination(NostrNIP26SignedTokenExportQRView)



class NostrNIP26SignedTokenExportQRView(BaseNostrView):
    def __init__(self):
        super().__init__()
        
        if "nip26_delegatee" in self.controller.nostr_data:
            # We created this delegation; need to transmit the full "delegation" tag
            self.data = nostr.sign_nip26_delegation(
                seed_bytes=self.nostr_root_pk.secret, 
                token=self.controller.nostr_data["nip26_token"]
            )
        else:
            # We just need to sign the token and return the signature
            self.data = nostr.sign_message(
                seed_bytes=self.nostr_root_pk.secret,
                message=self.controller.nostr_data["nip26_token"]
            )

        qr_density = self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY)
        qr_type = QRType.GENERIC__STATIC

        self.qr_encoder = EncodeQR(
            data=self.data,
            qr_type=qr_type,
            qr_density=qr_density,
        )


    def run(self):
        QRDisplayScreen(qr_encoder=self.qr_encoder).display()

        # Clean up our internal data
        self.controller.nostr_data = None

        return Destination(NostrKeyOptionsView, view_args=dict(seed_num=self.seed_num), skip_current_view=True, clear_history=True)



class NostrKeyDisplayView(BaseNostrView):
    def __init__(self, is_pubkey: bool = True):
        super().__init__()
        self.is_pubkey = is_pubkey


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrPublicKeyDisplayScreen, NostrPrivateKeyDisplayScreen

        if self.is_pubkey:
            selected_menu_num = NostrPublicKeyDisplayScreen(
                title="Nostr npub Export",
                key=self.nostr_root_npub,
            ).display()
        else:
            selected_menu_num = NostrPrivateKeyDisplayScreen(
                title="Nostr nsec Export",
                key=self.nostr_root_nsec,
            ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        return Destination(NostrKeyExportQRView, view_args=dict(is_pubkey=self.is_pubkey))



class NostrKeyExportQRView(BaseNostrView):
    def __init__(self, is_pubkey: bool = True):
        super().__init__()

        if is_pubkey:
            data = self.nostr_root_npub
        else:
            data = self.nostr_root_nsec

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
