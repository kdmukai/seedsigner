import json
from seedsigner.controller import Controller
from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.helpers import nostr
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonListScreen, QRDisplayScreen
from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.view import BackStackView, Destination, View


class BaseNostrView(View):
    @property
    def seed_num(self) -> int:
        return self.controller.nostr_data["seed_num"]
    
    @property
    def seed(self) -> Seed:
        return self.controller.storage.seeds[self.seed_num]

    @property
    def nostr_npub(self) -> str:
        return nostr.get_npub(self.seed)

    @property
    def nostr_nsec(self) -> str:
        return nostr.get_nsec(self.seed)
    
    @property
    def nostr_pubkey_hex(self) -> str:
        return nostr.get_pubkey_hex(self.seed)

    @property
    def nostr_privkey_hex(self) -> str:
        return nostr.get_privkey_hex(self.seed)



class NostrKeyOptionsView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed = self.controller.storage.seeds[seed_num]

        # Always reset temp Nostr data here
        self.controller.nostr_data = {}
        self.controller.nostr_data["seed_num"] = seed_num


    def run(self):
        NIP_26_DELEGATION = ("NIP-26 delegation", FontAwesomeIconConstants.ADDRESS_CARD)
        SIGN = ("Sign event", FontAwesomeIconConstants.PEN)
        EXPORT_PUBLIC_KEY = ("Export pubkey", FontAwesomeIconConstants.KEY)
        EXPORT_PRIVATE_KEY = ("Export privkey", FontAwesomeIconConstants.TRIANGLE_EXCLAMATION)

        button_data = [NIP_26_DELEGATION, SIGN, EXPORT_PUBLIC_KEY, EXPORT_PRIVATE_KEY]

        selected_menu_num = ButtonListScreen(
            # title="Nostr Key Options",
            title=f"npub: {nostr.get_npub(self.seed)[4:13]}",
            button_data=button_data,
            is_bottom_list=True,
            is_button_text_centered=False,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == NIP_26_DELEGATION:
            return Destination(NostrNIP26DelegationStartView)

        elif button_data[selected_menu_num] == SIGN:
            return Destination(NostrSignEventStartView)

        elif button_data[selected_menu_num] == EXPORT_PUBLIC_KEY:
            return Destination(NostrKeySelectFormatView, view_args=dict(is_pubkey=True))

        elif button_data[selected_menu_num] == EXPORT_PRIVATE_KEY:
            return Destination(NostrKeySelectFormatView, view_args=dict(is_pubkey=False))



"""****************************************************************************
    NIP-26 Delegation
****************************************************************************"""
class NostrNIP26DelegationStartView(BaseNostrView):
    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26DelegationStartScreen

        CREATE = "Create NIP-26 token"
        SCAN = ("Scan NIP-26 token", FontAwesomeIconConstants.QRCODE)
        button_data = [CREATE, SCAN]

        selected_menu_num = NostrNIP26DelegationStartScreen(
            title="NIP-26 Delegation",
            button_data=button_data,
            npub=f"npub:{self.nostr_npub[4:13]}",
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

        # Used to preserve the rendering position in the list
        self.initial_scroll = 0


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26TokenKindsScreen

        button_data = [f"{kind[1]}: {kind[0]}" for kind in nostr.ALL_KINDS]

        # Re-use the Settings entry screen for MULTISELECT
        screen = NostrNIP26TokenKindsScreen(
            title="Allowed Kinds",
            button_data=button_data,
            checked_buttons=self.checked_buttons,
            selected_button=self.selected_button,
            scroll_y_initial_offset=self.initial_scroll,
        )
        ret_value = screen.display()

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
        self.initial_scroll = screen.buttons[0].scroll_y
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
        button_data = [SCAN]

        onboard_seeds = []
        for i, seed in enumerate(self.controller.storage.seeds):
            if i == self.seed_num:
                continue
            onboard_seeds.append(nostr.get_npub(seed))
            button_data.append(f"npub: {nostr.get_npub(seed)[4:13]}")
            
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
        
        else:
            for i, npub in enumerate(onboard_seeds):
                if i + 1 == selected_menu_num:
                    return Destination(NostrNIP26BuildToken, view_args=dict(npub=npub))




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
            # We just scanned in a token from a client app
            self.controller.nostr_data["nip26_token"] = delegation_token

        self.delegation_token = self.controller.nostr_data["nip26_token"]
        self.controller.resume_main_flow = None

        self.parsed_token = nostr.parse_nip26_delegation_token(self.delegation_token)


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrNIP26ReviewTokenScreen
        selected_menu_num = NostrNIP26ReviewTokenScreen(
            title="NIP-26 Delegation",
            delegator_npub=self.nostr_npub[:10],
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
                seed=self.seed,
                token=self.controller.nostr_data["nip26_token"]
            )
        else:
            # We just need to sign the token and return the signature
            self.data = nostr.sign_message(
                seed=self.seed,
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

        return Destination(NostrKeyOptionsView, view_args=dict(seed_num=self.seed_num), skip_current_view=True, clear_history=True)



"""****************************************************************************
    Sign Event
****************************************************************************"""
class NostrSignEventStartView(BaseNostrView):
    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrSignEventStartScreen
        from seedsigner.views.scan_views import ScanView
        selected_menu_num = NostrSignEventStartScreen().display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        return Destination(ScanView)



class NostrSignEventReviewView(BaseNostrView):
    def __init__(self, serialized_event: str = None, json_event: str = None):
        super().__init__()
        if json_event:
            event_dict = json.loads(json_event)
            serialized_event = nostr.serialize_event(event_dict)

        self.controller.nostr_data["raw_serialized_event"] = serialized_event
        self.serialized_event = json.loads(serialized_event)
    

    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrSignEventReviewScreen
        sender_pubkey = self.serialized_event[nostr.SerializedEventFields.SENDER_PUBKEY]
        sender_npub = nostr.pubkey_hex_to_npub(self.serialized_event[nostr.SerializedEventFields.SENDER_PUBKEY])
        kind = f"{self.serialized_event[nostr.SerializedEventFields.KIND]}: {nostr.ALL_KINDS[self.serialized_event[nostr.SerializedEventFields.KIND]][0]}"
        content = self.serialized_event[nostr.SerializedEventFields.CONTENT]

        if sender_pubkey != self.nostr_pubkey_hex:
            # This Seed can't sign this Event
            from seedsigner.gui.screens import DireWarningScreen
            DireWarningScreen(
                title="Wrong Seed",
                status_headline="Cannot sign event",
                text=f"""Current seed is {self.nostr_npub[:10]} but event expects {sender_npub[:10]}""",
                button_data=["OK"],
                show_back_button=False,
            ).display()

            return Destination(NostrKeyOptionsView, view_args=dict(seed_num=self.seed_num), clear_history=True)

        selected_menu_num = NostrSignEventReviewScreen(
            title="Sign Event",
            kind=kind,
            content=content,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        return Destination(NostrSignEventSignatureQRView)



class NostrSignEventSignatureQRView(BaseNostrView):
    def __init__(self):
        super().__init__()

        signature = nostr.sign_event(seed=self.seed, serialized_event=self.controller.nostr_data["raw_serialized_event"])

        qr_density = self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY)
        qr_type = QRType.GENERIC__STATIC

        self.qr_encoder = EncodeQR(
            data=signature,
            qr_type=qr_type,
            qr_density=qr_density,
        )


    def run(self):
        QRDisplayScreen(qr_encoder=self.qr_encoder).display()

        return Destination(NostrKeyOptionsView, view_args=dict(seed_num=self.seed_num), clear_history=True)



"""****************************************************************************
    npub / nsec View and Export
****************************************************************************"""
class NostrKeySelectFormatView(BaseNostrView):
    def __init__(self, is_pubkey: bool):
        super().__init__()
        self.is_pubkey = is_pubkey


    def run(self):
        BECH32 = "npub (bech32)" if self.is_pubkey else "nsec (bech32)"
        HEX = "Hex"

        button_data = [BECH32, HEX]
        selected_menu_num = ButtonListScreen(
            title="Key Format",
            button_data=button_data,
            is_bottom_list=True,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] == BECH32:
            return Destination(NostrKeyDisplayView, view_args=dict(is_pubkey=self.is_pubkey, is_bech32=True))

        elif button_data[selected_menu_num] == HEX:
            return Destination(NostrKeyDisplayView, view_args=dict(is_pubkey=self.is_pubkey, is_bech32=False))



class NostrKeyDisplayView(BaseNostrView):
    def __init__(self, is_pubkey: bool = True, is_bech32: bool = True):
        super().__init__()
        self.is_pubkey = is_pubkey
        self.is_bech32 = is_bech32


    def run(self):
        from seedsigner.gui.screens.nostr_screens import NostrBech32KeyDisplayScreen, NostrPrivateKeyDisplayScreen

        if self.is_pubkey:
            if self.is_bech32:
                title = "npub Export"
                key = self.nostr_npub
            else:
                title = "Hex Pubkey Export"
                key = self.nostr_pubkey_hex
        else:
            if self.is_bech32:
                title = "nsec Export"
                key = self.nostr_nsec
            else:
                title = "Hex Privkey Export"
                key = self.nostr_privkey_hex

        selected_menu_num = NostrBech32KeyDisplayScreen(
            title=title,
            key=key,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        return Destination(NostrKeyExportQRView, view_args=dict(is_pubkey=self.is_pubkey, is_bech32=self.is_bech32))



class NostrKeyExportQRView(BaseNostrView):
    def __init__(self, is_pubkey: bool = True, is_bech32: bool = True):
        super().__init__()

        if is_pubkey:
            data = self.nostr_npub if is_bech32 else self.nostr_pubkey_hex
        else:
            data = self.nostr_nsec if is_bech32 else self.nostr_privkey_hex

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
