from binascii import a2b_base64
import embit
import os
import sys
import time

from embit.psbt import PSBT
from mock import Mock, MagicMock

from seedsigner.models.psbt_parser import PSBTParser

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.hardware.ST7789'] = MagicMock()
sys.modules['seedsigner.gui.screens.screensaver'] = MagicMock()
sys.modules['seedsigner.gui.screens.LoadingScreenThread'] = MagicMock()
sys.modules['seedsigner.views.screensaver'] = MagicMock()
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['seedsigner.hardware.camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()


from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.gui.toast import BaseToastOverlayManagerThread, RemoveSDCardToastManagerThread, SDCardStateChangeToastManagerThread
from seedsigner.hardware.microsd import MicroSD
from seedsigner.helpers import embit_utils
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views import (MainMenuView, PowerOptionsView, RestartView, NotYetImplementedView, UnhandledExceptionView, 
    psbt_views, seed_views, settings_views, tools_views)
from seedsigner.views.view import ErrorView, NetworkMismatchErrorView, OptionDisabledView, PowerOffView, View

from .utils import ScreenshotComplete, ScreenshotRenderer



def test_generate_screenshots(target_locale):
    """
        The `Renderer` class is mocked so that calls in the normal code are ignored
        (necessary to avoid having it trying to wire up hardware dependencies).

        When the `Renderer` instance is needed, we patch in our own test-only
        `ScreenshotRenderer`.
    """
    # Prep the ScreenshotRenderer that will be patched over the normal Renderer
    screenshot_root = os.path.join(os.getcwd(), "seedsigner-screenshots")
    ScreenshotRenderer.configure_instance()
    screenshot_renderer: ScreenshotRenderer = ScreenshotRenderer.get_instance()

    # Replace the core `Singleton` calls so that only our ScreenshotRenderer is used.
    Renderer.configure_instance = Mock()
    Renderer.get_instance = Mock(return_value=screenshot_renderer)

    # Additional mocks needed
    PowerOffView.PowerOffThread = Mock()  # Don't let this View actually send the `shutdown` command!

    controller = Controller.get_instance()

    # Set up some test data that we'll need in the `Controller` for certain Views
    mnemonic_12 = "forum undo fragile fade shy sign arrest garment culture tube off merit".split()
    mnemonic_24 = "attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire".split()
    mnemonic_12b = ["abandon"] * 11 + ["about"]
    seed_12 = Seed(mnemonic=mnemonic_12, passphrase="cap*BRACKET3stove", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    seed_12b = Seed(mnemonic=mnemonic_12b, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    seed_24 = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    controller.storage.seeds.append(seed_12)
    controller.storage.seeds.append(seed_12b)
    controller.storage.set_pending_seed(seed_24)
    UnhandledExceptionViewFood = ["IndexError", "line 1, in some_buggy_code.py", "list index out of range"]

    # Pending mnemonic for ToolsCalcFinalWordShowFinalWordView
    controller.storage.init_pending_mnemonic(num_words=12)
    for i, word in enumerate(mnemonic_12[:11]):
        controller.storage.update_pending_mnemonic(word=word, index=i)
    controller.storage.update_pending_mnemonic(word="satoshi", index=11)  # random last word; not supposed to be a valid checksum (yet)

    # Load a PSBT into memory
    BASE64_PSBT_1 = """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"""
    decoder = DecodeQR()
    decoder.add_data(BASE64_PSBT_1)
    controller.psbt = decoder.get_psbt()
    controller.psbt_seed = seed_12b

    # Multisig wallet descriptor for the multisig in the above PSBT
    MULTISIG_WALLET_DESCRIPTOR = """wsh(sortedmulti(1,[22bde1a9/48h/1h/0h/2h]tpubDFfsBrmpj226ZYiRszYi2qK6iGvh2vkkghfGB2YiRUVY4rqqedHCFEgw12FwDkm7rUoVtq9wLTKc6BN2sxswvQeQgp7m8st4FP8WtP8go76/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*))#3jhtf6yx"""
    controller.multisig_wallet_descriptor = embit.descriptor.Descriptor.from_string(MULTISIG_WALLET_DESCRIPTOR)
    
    # Message signing data
    derivation_path = "m/84h/0h/0h/0/0"
    controller.sign_message_data = {
        "seed_num": 0,
        "derivation_path": derivation_path,
        "message": "I attest that I control this bitcoin address blah blah blah",
        "addr_format": embit_utils.parse_derivation_path(derivation_path)
    }

    # Automatically populate all Settings options Views
    settings_views_list = []
    settings_views_list.append(settings_views.SettingsMenuView)
    # so we get a choice for transcribe seed qr format
    controller.settings.set_value(
        attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
        value=SettingsConstants.OPTION__ENABLED
    )
    for settings_entry in SettingsDefinition.settings_entries:
        if settings_entry.visibility == SettingsConstants.VISIBILITY__HIDDEN:
            continue

        settings_views_list.append((settings_views.SettingsEntryUpdateSelectionView, dict(attr_name=settings_entry.attr_name), f"SettingsEntryUpdateSelectionView_{settings_entry.attr_name}"))
    

    settingsqr_data_persistent = "settings::v1 name=Total_noob_mode persistent=E coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E"
    settingsqr_data_not_persistent = "settings::v1 name=Ephemeral_noob_mode persistent=D coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E"

    screenshot_sections = {
        "Main Menu Views": [
            MainMenuView,
            (MainMenuView, {}, 'MainMenuView_SDCardStateChangeToast_removed', SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__REMOVED)),
            (MainMenuView, {}, 'MainMenuView_SDCardStateChangeToast_inserted', SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__INSERTED)),
            (MainMenuView, {}, 'MainMenuView_RemoveSDCardToast', RemoveSDCardToastManagerThread(activation_delay=0)),
            PowerOptionsView,
            RestartView,
            PowerOffView,
        ],
        "Seed Views": [
            seed_views.SeedsMenuView,
            seed_views.LoadSeedView,
            seed_views.SeedMnemonicEntryView,
            seed_views.SeedMnemonicInvalidView,
            seed_views.SeedFinalizeView,
            seed_views.SeedAddPassphraseView,
            seed_views.SeedReviewPassphraseView,
            
            (seed_views.SeedOptionsView, dict(seed_num=0)),
            (seed_views.SeedBackupView, dict(seed_num=0)),
            (seed_views.SeedExportXpubSigTypeView, dict(seed_num=0)),
            (seed_views.SeedExportXpubScriptTypeView, dict(seed_num=0, sig_type="msig")),
            (seed_views.SeedExportXpubCustomDerivationView, dict(seed_num=0, sig_type="ss", script_type="")),
            (seed_views.SeedExportXpubCoordinatorView, dict(seed_num=0, sig_type="ss", script_type="nat")),
            (seed_views.SeedExportXpubWarningView, dict(seed_num=0, sig_type="msig", script_type="nes", coordinator="spd", custom_derivation="")),
            (seed_views.SeedExportXpubDetailsView, dict(seed_num=0, sig_type="ss", script_type="nat", coordinator="bw", custom_derivation="")),
            #SeedExportXpubQRDisplayView,
            (seed_views.SeedWordsWarningView, dict(seed_num=0)),
            (seed_views.SeedWordsView, dict(seed_num=0)),
            (seed_views.SeedWordsView, dict(seed_num=0, page_index=2), "SeedWordsView_2"),
            (seed_views.SeedBIP85ApplicationModeView, dict(seed_num=0)),
            (seed_views.SeedBIP85SelectChildIndexView, dict(seed_num=0, num_words=24)),
            (seed_views.SeedBIP85InvalidChildIndexView, dict(seed_num=0, num_words=12)), 
            (seed_views.SeedWordsBackupTestPromptView, dict(seed_num=0)),
            (seed_views.SeedWordsBackupTestView, dict(seed_num=0)),
            (seed_views.SeedWordsBackupTestMistakeView, dict(seed_num=0, cur_index=7, wrong_word="unlucky")),
            (seed_views.SeedWordsBackupTestSuccessView, dict(seed_num=0)),
            (seed_views.SeedTranscribeSeedQRFormatView, dict(seed_num=0)),
            (seed_views.SeedTranscribeSeedQRWarningView, dict(seed_num=0)),
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, num_modules=25), "SeedTranscribeSeedQRWholeQRView_12_Standard"),
            (seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=21), "SeedTranscribeSeedQRWholeQRView_12_Compact"),

            # Screenshot doesn't render properly due to how the transparency mask is pre-rendered
            # (seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR)),

            (seed_views.SeedTranscribeSeedQRConfirmQRPromptView, dict(seed_num=0)),

            # Screenshot can't render live preview screens
            # (seed_views.SeedTranscribeSeedQRConfirmScanView, dict(seed_num=0)),

            #(seed_views.AddressVerificationStartView, dict(address=, script_type="nat", network="M")),
            #seed_views.AddressVerificationSigTypeView,
            #seed_views.SeedSingleSigAddressVerificationSelectSeedView,
            #seed_views.SeedAddressVerificationView,
            #seed_views.AddressVerificationSuccessView,

            seed_views.LoadMultisigWalletDescriptorView,
            seed_views.MultisigWalletDescriptorView,
            (seed_views.SeedDiscardView, dict(seed_num=0)),

            seed_views.SeedSignMessageConfirmMessageView,
            seed_views.SeedSignMessageConfirmAddressView,
        ],
        "PSBT Views": [
            psbt_views.PSBTSelectSeedView, # this will fail, be rerun below
            psbt_views.PSBTOverviewView,
            psbt_views.PSBTUnsupportedScriptTypeWarningView,
            psbt_views.PSBTNoChangeWarningView,
            psbt_views.PSBTMathView,
            (psbt_views.PSBTAddressDetailsView, dict(address_num=0)),
            (psbt_views.PSBTAddressDetailsView, dict(address_num=0), "PSBTAddressDetailsView_testnet"),
            (psbt_views.PSBTAddressDetailsView, dict(address_num=0), "PSBTAddressDetailsView_regtest"),

            # TODO: Render Multisig change w/ and w/out the multisig wallet descriptor onboard
            (psbt_views.PSBTChangeDetailsView, dict(change_address_num=0)),
            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=False), "PSBTAddressVerificationFailedView_singlesig_change"),
            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=False), "PSBTAddressVerificationFailedView_singlesig_selftransfer"),
            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=True), "PSBTAddressVerificationFailedView_multisig_change"),
            (psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=True), "PSBTAddressVerificationFailedView_multisig_selftransfer"),
            psbt_views.PSBTFinalizeView,
            #PSBTSignedQRDisplayView
            psbt_views.PSBTSigningErrorView,

            # Payjoin from the receiver's perspective
            (psbt_views.PSBTOverviewView, {}, "PSBTOverviewView_payjoin_receive"),
            (psbt_views.PSBTMathView, {}, "PSBTMathView_payjoin_receive"),
            (psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), "PSBTChangeDetailsView_payjoin_receive"),

            # Payjoin from the sender's perspective
            (psbt_views.PSBTOverviewView, {}, "PSBTOverviewView_payjoin_send"),
            (psbt_views.PSBTMathView, {}, "PSBTMathView_payjoin_send"),
            (psbt_views.PSBTAddressDetailsView, dict(address_num=0), "PSBTAddressDetailsView_payjoin_send"),
            (psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), "PSBTChangeDetailsView_payjoin_send"),

            # Coinjoin
            (psbt_views.PSBTOverviewView, {}, "PSBTOverviewView_coinjoin"),
            (psbt_views.PSBTMathView, {}, "PSBTMathView_coinjoin"),
        ],
        "Tools Views": [
            tools_views.ToolsMenuView,
            #ToolsImageEntropyLivePreviewView
            #ToolsImageEntropyFinalImageView
            tools_views.ToolsImageEntropyMnemonicLengthView,
            tools_views.ToolsDiceEntropyMnemonicLengthView,
            (tools_views.ToolsDiceEntropyEntryView, dict(total_rolls=50)),
            tools_views.ToolsCalcFinalWordNumWordsView,
            tools_views.ToolsCalcFinalWordFinalizePromptView,
            tools_views.ToolsCalcFinalWordCoinFlipsView,
            (tools_views.ToolsCalcFinalWordShowFinalWordView, {}, "ToolsCalcFinalWordShowFinalWordView_pick_word"),
            (tools_views.ToolsCalcFinalWordShowFinalWordView, dict(coin_flips="0010101"), "ToolsCalcFinalWordShowFinalWordView_coin_flips"),
            #tools_views.ToolsCalcFinalWordDoneView,
            tools_views.ToolsAddressExplorerSelectSourceView,
            tools_views.ToolsAddressExplorerAddressTypeView,
            tools_views.ToolsAddressExplorerAddressListView,
            #tools_views.ToolsAddressExplorerAddressView,
        ],
        "Settings Views": settings_views_list + [
            settings_views.IOTestView,
            settings_views.DonateView,
            (settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_persistent), "SettingsIngestSettingsQRView_persistent"),
            (settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_not_persistent), "SettingsIngestSettingsQRView_not_persistent"),
        ],
        "Misc Error Views": [
            NotYetImplementedView,
            (UnhandledExceptionView, dict(error=UnhandledExceptionViewFood)),
            NetworkMismatchErrorView,
            (OptionDisabledView, dict(settings_attr=SettingsConstants.SETTING__MESSAGE_SIGNING)),
            (ErrorView, dict(
                title="Error",
                status_headline="Unknown QR Type",
                text="QRCode is invalid or is a data format not yet supported.",
                button_text="Back",
            )),
        ]
    }

    readme = f"""# SeedSigner Screenshots\n"""

    def screencap_view(view_cls: View, view_name: str, view_args: dict={}, toast_thread: BaseToastOverlayManagerThread = None):
        screenshot_renderer.set_screenshot_filename(f"{view_name}.png")
        try:
            print(f"Running {view_name}")
            try:
                view_cls(**view_args).run()
            except ScreenshotComplete:
                if toast_thread is not None:
                    controller.activate_toast(toast_thread)
                    while controller.toast_notification_thread.is_alive():
                        time.sleep(0.1)
                raise ScreenshotComplete()
        except ScreenshotComplete:
            # Slightly hacky way to exit ScreenshotRenderer as expected
            pass
            print(f"Completed {view_name}")
        except Exception as e:
            # Something else went wrong
            from traceback import print_exc
            print_exc()
            raise e
        finally:
            if toast_thread:
                toast_thread.stop()

    for section_name, screenshot_list in screenshot_sections.items():
        subdir = section_name.lower().replace(" ", "_")
        screenshot_renderer.set_screenshot_path(os.path.join(screenshot_root, subdir))
        readme += "\n\n---\n\n"
        readme += f"## {section_name}\n\n"
        readme += """<table style="border: 0;">"""
        readme += f"""<tr><td align="center">\n"""
        for screenshot in screenshot_list:
            if type(screenshot) == tuple:
                if len(screenshot) == 2:
                    view_cls, view_args = screenshot
                    view_name = view_cls.__name__
                elif len(screenshot) == 3:
                    view_cls, view_args, view_name = screenshot
                elif len(screenshot) == 4:
                    view_cls, view_args, view_name, toast_thread = screenshot
            else:
                view_cls = screenshot
                view_args = {}
                view_name = view_cls.__name__
                toast_thread = None

            screencap_view(view_cls, view_name, view_args, toast_thread=toast_thread)
            readme += """  <table align="left" style="border: 1px solid gray;">"""
            readme += f"""<tr><td align="center">{view_name}<br/><br/><img src="{subdir}/{view_name}.png"></td></tr>"""
            readme += """</table>\n"""

        readme += "</td></tr></table>"

    # many screens don't work, leaving a missing image, re-run here for now
    controller.psbt_seed = None
    screenshot_renderer.set_screenshot_path(os.path.join(screenshot_root, "psbt_views"))
    screencap_view(psbt_views.PSBTSelectSeedView, 'PSBTSelectSeedView', {})

    controller.settings.set_value(
        attr_name=SettingsConstants.SETTING__NETWORK,
        value=SettingsConstants.TESTNET
    )
    controller.psbt_parser = PSBTParser(
        PSBT.parse(a2b_base64(BASE64_PSBT_1)),
        seed=seed_12b,
        network=SettingsConstants.TESTNET
    )
    screencap_view(psbt_views.PSBTAddressDetailsView, 'PSBTAddressDetailsView_testnet', dict(address_num=0))

    controller.settings.set_value(
        attr_name=SettingsConstants.SETTING__NETWORK,
        value=SettingsConstants.REGTEST
    )
    controller.psbt_parser = PSBTParser(
        PSBT.parse(a2b_base64(BASE64_PSBT_1)),
        seed=seed_12b,
        network=SettingsConstants.REGTEST
    )
    screencap_view(psbt_views.PSBTAddressDetailsView, 'PSBTAddressDetailsView_regtest', dict(address_num=0))


    # Render payjoin screens for real; use tx from test_psbt_parser.py payjoin test
    zoe_seed = Seed("sign sword lift deer ocean insect web lazy sick pencil start select".split())
    payjoin_base64 = "cHNidP8BAJoCAAAAAmvBiAY6UU7NLa1KICrjrxyaV9NB3dQVUnWnmNpP7SBGAQAAAAD9////cCbPlwdnpnw1C2WK42cWoRXQaB6ARoY4uSCdISXffg4BAAAAAP3///8C1rU8AAAAAAAWABRy418s7hAxS+UrCmrk9CT6oWMBRYZatwEAAAAAFgAUDJYjCK75AgLhmU5sYcOW9mfpzB13AAAATwEENYfPA1cd2/6AAAAAbkDx9gLVRoKpONU2bM/jX7KuFUkRrTY2S1T6FTWCql0DOnituHh02lj72WonxwTWYlCjMEObWa+aDr6zT79MNS4QA80KK1QAAIAAAACAAAAAgAABAR+K9W0BAAAAABYAFMOlZFGAF2Q4fD7HIIw4kCVhc6cMAQMEAQAAAAABAR+GLYYAAAAAABYAFGcxK19pAPjZdCADa6WfVtPAawYqAQMEAQAAACIGA/XjxxoNMFunU4xNwU+BEIFSe1ilt+54iu5OC24O68qhGA+IkERUAACAAAAAgAAAAIAAAAAABAAAAAAiAgLPexMz/QGBiOpmYwsv7ruEgtUDt2Jel5DGWtlet5JzuxgDzQorVAAAgAAAAIAAAACAAQAAAAEAAAAAIgIDxpTFZnPjW8NV3oaa3bP9TPainGiPkc4pIjKn7rLA88EYD4iQRFQAAIAAAACAAAAAgAAAAAAFAAAAAA=="
    controller.psbt_seed = zoe_seed
    decoder = DecodeQR()
    decoder.add_data(payjoin_base64)
    controller.psbt = decoder.get_psbt()
    controller.psbt_parser = PSBTParser(p=controller.psbt, seed=zoe_seed, network=SettingsConstants.REGTEST)
    controller.multisig_wallet_descriptor = None
    screencap_view(psbt_views.PSBTOverviewView, view_name='PSBTOverviewView_payjoin_receive')
    screencap_view(psbt_views.PSBTMathView, view_name='PSBTMathView_payjoin_receive')
    screencap_view(psbt_views.PSBTChangeDetailsView, view_name='PSBTChangeDetailsView_payjoin_receive', view_args=dict(change_address_num=0))

    # And then change to the payjoin sender's context
    malcolm_seed = Seed("better gown govern speak spawn vendor exercise item uncle odor sound cat".split())
    payjoin_base64 = "cHNidP8BAJoCAAAAAmvBiAY6UU7NLa1KICrjrxyaV9NB3dQVUnWnmNpP7SBGAQAAAAD9////cCbPlwdnpnw1C2WK42cWoRXQaB6ARoY4uSCdISXffg4BAAAAAP3///8C1rU8AAAAAAAWABRy418s7hAxS+UrCmrk9CT6oWMBRYZatwEAAAAAFgAUDJYjCK75AgLhmU5sYcOW9mfpzB13AAAATwEENYfPA1cd2/6AAAAAbkDx9gLVRoKpONU2bM/jX7KuFUkRrTY2S1T6FTWCql0DOnituHh02lj72WonxwTWYlCjMEObWa+aDr6zT79MNS4QA80KK1QAAIAAAACAAAAAgAABAR+K9W0BAAAAABYAFMOlZFGAF2Q4fD7HIIw4kCVhc6cMAQMEAQAAACIGAvJY/nFTCdMxuP4cxQ/rbCgA8WIQe8wlFl+n3h9yelGnGAPNCitUAACAAAAAgAAAAIAAAAAAAQAAAAABAR+GLYYAAAAAABYAFGcxK19pAPjZdCADa6WfVtPAawYqAQMEAQAAAAAiAgLPexMz/QGBiOpmYwsv7ruEgtUDt2Jel5DGWtlet5JzuxgDzQorVAAAgAAAAIAAAACAAQAAAAEAAAAAAA=="
    controller.psbt_seed = malcolm_seed
    decoder = DecodeQR()
    decoder.add_data(payjoin_base64)
    controller.psbt = decoder.get_psbt()
    controller.psbt_parser = PSBTParser(p=controller.psbt, seed=malcolm_seed, network=SettingsConstants.REGTEST)
    screencap_view(psbt_views.PSBTOverviewView, view_name='PSBTOverviewView_payjoin_send')
    screencap_view(psbt_views.PSBTMathView, view_name='PSBTMathView_payjoin_send')
    screencap_view(psbt_views.PSBTAddressDetailsView, view_name='PSBTAddressDetailsView_payjoin_send', view_args=dict(address_num=0))
    screencap_view(psbt_views.PSBTChangeDetailsView, view_name='PSBTChangeDetailsView_payjoin_send', view_args=dict(change_address_num=0))

    # Render the coinjoin screens for real
    malcolm_coinjoin_psbt_base64 = "cHNidP8BAP2wAQIAAAAFUsuOhcX/DvTI/BZgYs2yeiYVP7E7N9tDoG9SdYnfSEMBAAAAAP3///9Sy46Fxf8O9Mj8FmBizbJ6JhU/sTs320Ogb1J1id9IQwMAAAAA/f///1LLjoXF/w70yPwWYGLNsnomFT+xOzfbQ6BvUnWJ30hDAgAAAAD9////mT05iCk32P6+TGMEMGKw6mH6fTafsNiCaqnbPbBgd14BAAAAAP3///+ZPTmIKTfY/r5MYwQwYrDqYfp9Np+w2IJqqds9sGB3XgMAAAAA/f///wejQEEAAAAAABYAFC9NKd1nKSURCfVJ0o6jWWeWlmjhgJaYAAAAAAAWABRX/KTAYaj0b7PKz5gyctryXOfEsoCWmAAAAAAAFgAU/TrhKNM2cRT6q+DIUguvy+qU4/co0gkAAAAAABYAFJGunwKmlnk03tAdW7U0ejbENMkHgJaYAAAAAAAWABQMliMIrvkCAuGZTmxhw5b2Z+nMHYCWmAAAAAAAFgAUUeL8QB1nn4/70+kkYOELiRizhMGAlpgAAAAAABYAFGcxK19pAPjZdCADa6WfVtPAawYqeQAAAE8BBDWHzwNXHdv+gAAAAG5A8fYC1UaCqTjVNmzP41+yrhVJEa02NktU+hU1gqpdAzp4rbh4dNpY+9lqJ8cE1mJQozBDm1mvmg6+s0+/TDUuEAPNCitUAACAAAAAgAAAAIAAAQEfSEmpAAAAAAAWABTjYDCb4Xjt9crkkGTmkTUq62y3VAEDBAEAAAAiBgMHW935AUdSTj7f5cqUZaoXQMzFEd79QZJ5ynA9iF7V8xgDzQorVAAAgAAAAIAAAACAAAAAAAMAAAAAAQEf0zxsAAAAAAAWABRR7MrfOfsP9nu4RdBD8IgmP035ZAEDBAEAAAAiBgPn+Ccxu6pGSOB0jquBWJLC8DJpN7JLFNb+ztKzM1bK8xgDzQorVAAAgAAAAIAAAACAAAAAAAQAAAAAAQEfpg1dAAAAAAAWABQfr++RzXT/fgcAOT8BwAMKLiXR8gEDBAEAAAAiBgIK/piptBqIz9TBy75TFDhBeyR6JhpS8dXtQm0LCXaTYRgDzQorVAAAgAAAAIAAAACAAAAAAAIAAAAAAQEfDc57AQAAAAAWABQv3yIgZvyeHaVk+S1C+FJxJcFbEAEDBAEAAAAAAQEfWO1XAAAAAAAWABRAqBYRdfRqWTw/lN+FTiJzNph5mQEDBAEAAAAAIgIDmNkmAH4UuX6cz0IzGzTBBW7vtKuBF5K2K4TuJLICVBsYA80KK1QAAIAAAACAAAAAgAEAAAACAAAAACICA/uuyfyuFkBIAebqRMjhyoB8/oIwTaWvKShGKByMkIFAGAPNCitUAACAAAAAgAAAAIAAAAAABgAAAAAiAgKwPmHARSbJyuU7+U5DHUQtNA8NPkZH9kvOaCK/j7RvERgDzQorVAAAgAAAAIAAAACAAAAAAAUAAAAAAAAAAA=="

    # Messy coinjoin w/extra outputs
    malcolm_coinjoin_psbt_base64 = "cHNidP8BAP3uAQIAAAAFUsuOhcX/DvTI/BZgYs2yeiYVP7E7N9tDoG9SdYnfSEMCAAAAAP3///9Sy46Fxf8O9Mj8FmBizbJ6JhU/sTs320Ogb1J1id9IQwMAAAAA/f///1LLjoXF/w70yPwWYGLNsnomFT+xOzfbQ6BvUnWJ30hDAQAAAAD9////mT05iCk32P6+TGMEMGKw6mH6fTafsNiCaqnbPbBgd14DAAAAAP3///+ZPTmIKTfY/r5MYwQwYrDqYfp9Np+w2IJqqds9sGB3XgEAAAAA/f///wk5bD0AAAAAABYAFC9NKd1nKSURCfVJ0o6jWWeWlmjhgJaYAAAAAAAWABRX/KTAYaj0b7PKz5gyctryXOfEsoCWmAAAAAAAFgAU/TrhKNM2cRT6q+DIUguvy+qU4/eQ0AMAAAAAABYAFPi2CaO4LYCR+yyZ9PAwK7uDjkjtQv0FAAAAAAAWABSRrp8CppZ5NN7QHVu1NHo2xDTJB4CWmAAAAAAAFgAUZzErX2kA+Nl0IANrpZ9W08BrBiqAlpgAAAAAABYAFAyWIwiu+QIC4ZlObGHDlvZn6cwdgJaYAAAAAAAWABRR4vxAHWefj/vT6SRg4QuJGLOEwZDQAwAAAAAAFgAURsVsVzfCll3oga2Z1CByV626Q955AAAATwEENYfPA1cd2/6AAAAAbkDx9gLVRoKpONU2bM/jX7KuFUkRrTY2S1T6FTWCql0DOnituHh02lj72WonxwTWYlCjMEObWa+aDr6zT79MNS4QA80KK1QAAIAAAACAAAAAgAABAR+mDV0AAAAAABYAFB+v75HNdP9+BwA5PwHAAwouJdHyAQMEAQAAACIGAgr+mKm0GojP1MHLvlMUOEF7JHomGlLx1e1CbQsJdpNhGAPNCitUAACAAAAAgAAAAIAAAAAAAgAAAAABAR/TPGwAAAAAABYAFFHsyt85+w/2e7hF0EPwiCY/TflkAQMEAQAAACIGA+f4JzG7qkZI4HSOq4FYksLwMmk3sksU1v7O0rMzVsrzGAPNCitUAACAAAAAgAAAAIAAAAAABAAAAAABAR9ISakAAAAAABYAFONgMJvheO31yuSQZOaRNSrrbLdUAQMEAQAAACIGAwdb3fkBR1JOPt/lypRlqhdAzMUR3v1BknnKcD2IXtXzGAPNCitUAACAAAAAgAAAAIAAAAAAAwAAAAABAR9Y7VcAAAAAABYAFECoFhF19GpZPD+U34VOInM2mHmZAQMEAQAAAAABAR8NznsBAAAAABYAFC/fIiBm/J4dpWT5LUL4UnElwVsQAQMEAQAAAAAiAgOY2SYAfhS5fpzPQjMbNMEFbu+0q4EXkrYrhO4ksgJUGxgDzQorVAAAgAAAAIAAAACAAQAAAAIAAAAAIgID+67J/K4WQEgB5upEyOHKgHz+gjBNpa8pKEYoHIyQgUAYA80KK1QAAIAAAACAAAAAgAAAAAAGAAAAACICArA+YcBFJsnK5Tv5TkMdRC00Dw0+Rkf2S85oIr+PtG8RGAPNCitUAACAAAAAgAAAAIAAAAAABQAAAAAAAAAAAAA="

    decoder = DecodeQR()
    decoder.add_data(malcolm_coinjoin_psbt_base64)
    controller.psbt = decoder.get_psbt()
    controller.psbt_parser = PSBTParser(p=controller.psbt, seed=malcolm_seed, network=SettingsConstants.REGTEST)
    screencap_view(psbt_views.PSBTOverviewView, view_name='PSBTOverviewView_coinjoin')
    screencap_view(psbt_views.PSBTMathView, view_name='PSBTMathView_coinjoin')


    with open(os.path.join(screenshot_root, "README.md"), 'w') as readme_file:
       readme_file.write(readme)
