import pytest
import random

from binascii import a2b_base64
from collections import OrderedDict
from copy import deepcopy

from embit import bip32
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from embit.psbt import PSBT

from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants

from psbt_testing_util import PSBTTestData, create_output



class TestPSBTParser:
    seed = PSBTTestData.seed

    def run_basic_test(self, psbt_base64: str, change_data: str):
        """
        Constructs a series of test psbts that use the specified psbt_base64 for the input(s).

        * 1 external recipient + change for each recipient type
        * 1 external recipient full spend (no change) for each recipient type
        * 1 mega psbt with all external recipient types in one tx + change
        """
        psbt = PSBT.parse(a2b_base64(psbt_base64))
        input_amount = sum([inp.utxo.value for inp in psbt.inputs])
        recipient_amount = random.randint(200_000, 90_000_000)
        change_output = create_output(change_data, input_amount - recipient_amount - 5_000)

        for output in PSBTTestData.ALL_EXTERNAL_OUTPUTS:
            psbt.outputs.clear()
            psbt.outputs.append(create_output(output, recipient_amount))
            psbt.outputs.append(change_output)

            assert len(psbt.outputs) == 2
            psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
            assert psbt_parser.num_inputs == len(psbt.inputs)
            assert psbt_parser.num_external_inputs == 0
            assert psbt_parser.input_amount == input_amount
            assert psbt_parser.num_destinations == 1
            assert psbt_parser.num_change_outputs == 1
            assert psbt_parser.spend_amount == recipient_amount
            assert psbt_parser.change_amount == input_amount - recipient_amount - 5_000
            assert psbt_parser.fee_amount == 5_000
            assert psbt_parser.input_amount + psbt_parser.external_input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount
        
        # Now do full spends with no change
        fee_amount = random.randint(5_000, 100_000)
        recipient_amount = input_amount - fee_amount

        for output in PSBTTestData.ALL_EXTERNAL_OUTPUTS:
            psbt.outputs.clear()
            psbt.outputs.append(create_output(output, recipient_amount))

            assert len(psbt.outputs) == 1
            psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
            assert psbt_parser.num_inputs == len(psbt.inputs)
            assert psbt_parser.num_external_inputs == 0
            assert psbt_parser.input_amount == input_amount
            assert psbt_parser.num_destinations == 1
            assert psbt_parser.num_change_outputs == 0
            assert psbt_parser.spend_amount == recipient_amount
            assert psbt_parser.change_amount == 0
            assert psbt_parser.fee_amount == fee_amount
            assert psbt_parser.input_amount + psbt_parser.external_input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount

        # Now try a single mega psbt with ALL the outputs at once
        psbt.outputs.clear()
        change_amount = input_amount - fee_amount
        for output in PSBTTestData.ALL_EXTERNAL_OUTPUTS:
            output_amount = random.randint(200_000, int(change_amount / 2))
            psbt.outputs.append(create_output(output, output_amount))
            change_amount -= output_amount

        # Don't forget the change!        
        psbt.outputs.append(create_output(change_data, change_amount))

        assert len(psbt.outputs) == len(PSBTTestData.ALL_EXTERNAL_OUTPUTS) + 1
        psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
        assert psbt_parser.num_inputs == len(psbt.inputs)
        assert psbt_parser.num_external_inputs == 0
        assert psbt_parser.input_amount == input_amount
        assert psbt_parser.num_destinations == len(PSBTTestData.ALL_EXTERNAL_OUTPUTS)
        assert psbt_parser.num_change_outputs == 1
        assert psbt_parser.spend_amount == input_amount - change_amount - fee_amount
        assert psbt_parser.change_amount == change_amount
        assert psbt_parser.fee_amount == fee_amount
        assert psbt_parser.input_amount + psbt_parser.external_input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount


    def test_singlesig_native_segwit(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE)

    def test_singlesig_nested_segwit(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_CHANGE)

    def test_singlesig_taproot(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_TAPROOT_1_INPUT, PSBTTestData.SINGLE_SIG_TAPROOT_CHANGE)

    # TODO: enable test once legacy p2pkh support is merged
    @pytest.mark.skip("Single sig legacy p2pkh support not yet implemented")
    def test_singlesig_legacy_p2pkh(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_1_INPUT, PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_CHANGE)

    def test_multisig_native_segwit(self):
        self.run_basic_test(PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE)

    def test_multisig_nested_segwit(self):
        self.run_basic_test(PSBTTestData.MULTISIG_NESTED_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NESTED_SEGWIT_CHANGE)

    # TODO: enable test once legacy p2sh support is merged
    @pytest.mark.skip("Multisig legacy p2sh support not yet implemented")
    def test_multisig_legacy_p2sh(self):
        self.run_basic_test(PSBTTestData.MULTISIG_LEGACY_P2SH_1_INPUT, PSBTTestData.MULTISIG_LEGACY_P2SH_CHANGE)


    def test_has_matching_input_fingerprint(self):
        """
        PSBTParser should correctly identify when a psbt contains an input that matches a
        given Seed's fingerprint.
        """
        wrong_seed = Seed(["bacon"] * 24)
        for input in PSBTTestData.ALL_INPUTS:
            psbt = PSBT.parse(a2b_base64(input))
            assert PSBTParser.has_matching_input_fingerprint(psbt, PSBTTestData.seed)
            assert PSBTParser.has_matching_input_fingerprint(psbt, wrong_seed) == False

        # The other keys in the multisig inputs should also match        
        for input in PSBTTestData.MULTISIG_INPUTS:
            psbt = PSBT.parse(a2b_base64(input))
            assert PSBTParser.has_matching_input_fingerprint(psbt, PSBTTestData.multisig_key_2)
            assert PSBTParser.has_matching_input_fingerprint(psbt, PSBTTestData.multisig_key_3)


    def test_trim_and_sig_count(self):
        """
        PSBTParser should correctly trim a psbt of all unnecessary data and count the number of
        signatures in the psbt.
        """
        output = create_output(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_RECEIVE, 100_000)
        for input in PSBTTestData.ALL_INPUTS:
            psbt = PSBT.parse(a2b_base64(input))
            psbt.outputs.append(output)
            psbt.sign_with(bip32.HDKey.from_seed(self.seed.seed_bytes))
            assert PSBTParser.sig_count(psbt) == 1

            # TODO: What can we test for before/after trimming?
            PSBTParser.trim(psbt)

            if input in PSBTTestData.MULTISIG_INPUTS:
                psbt.sign_with(bip32.HDKey.from_seed(PSBTTestData.multisig_key_2.seed_bytes))
                assert PSBTParser.sig_count(psbt) == 2

                psbt.sign_with(bip32.HDKey.from_seed(PSBTTestData.multisig_key_3.seed_bytes))
                assert PSBTParser.sig_count(psbt) == 3


    def test_verify_multisig_output(self):
        multisig_inputs = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_1_INPUT,
            # PSBTTestData.MULTISIG_LEGACY_P2SH_1_INPUT  # TODO: Enable once legacy p2sh support is merged
        ]
        change_outputs =  [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_CHANGE,
            PSBTTestData.MULTISIG_LEGACY_P2SH_CHANGE
        ]
        descriptors = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_DESCRIPTOR,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_DESCRIPTOR,
            PSBTTestData.MULTISIG_LEGACY_P2SH_DESCRIPTOR
        ]

        for i, psbt_base64 in enumerate(multisig_inputs):
            # Construct a psbt with a change output of the same type as the input
            psbt = PSBT.parse(a2b_base64(psbt_base64))
            psbt.outputs.append(create_output(change_outputs[i], 100_000))
            psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)

            # Attempt to verify the change using the right and wrong descriptors
            for j, descriptor_str in enumerate(descriptors):
                descriptor = Descriptor.from_string(descriptor_str.replace("<0;1>", "{0,1}"))
                if i == j:
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=0) == True
                else:
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=0) == False


    def test_p2tr_change_detection(self):
        """ Should successfully detect change in a p2tr to p2tr psbt spend
        
            PSBT Tx and Wallet Details
            - Single Sig Wallet P2TR (Taproot) with no passphrase
            - Regtest 394aed14 m/86'/1'/0' tpubDCawGrRg7YdHdFb9p4mmD8GBaZjJegL53FPFRrMkGoLcgLATJfksUs2y1Q7dVzixAkgecazsxEsUuyj3LyDw7eVVYHQyojwrc2hfesK4wXW
            - 1 Inputs
                - 3,190,493,401 sats
            - 2 Outputs
                - 1 Output spend to another wallet (bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek) p2tr address
                - 1 Output change
                    - addresss bcrt1prz4g6saush37epdwhvwpu78td3q7yfz3xxz37axlx7udck6wracq3rwq30)
                    - amount 2,871,443,918 sats
                    - Change addresses is index 1/1
                - Fee 155 sats
        """
        
        psbt_base64 = "cHNidP8BAIkCAAAAAf8upuiIWF1VTgC/Q8ZWRrameRigaXpRcQcBe8ye+TK3AQAAAAAXCgAAAs7BJqsAAAAAIlEgGKqNQ7yF4+yFrrscHnjrbEHiJFExhR903ze43FtOH3BwTgQTAAAAACJRINBe93RcrOYO4UVLLE0y8pzvblOKQWcoQ0obCey8nA5GAAAAAE8BBDWHzwNMUx9OgAAAAJdr+WtwWfVa6IPbpKZ4KgRC0clbm11Gl155IPA27n2FAvQCrFGH6Ac2U0Gcy1IH5f5ltgUBDz2+fe8iqL6JzZdgEDlK7RRWAACAAQAAgAAAAIAAAQB9AgAAAAGAKOOUFIzw9pbRDaZ7F0DYhLImrdMn//OSm++ff5VNdAAAAAAAAQAAAAKsjLwAAAAAABYAFKEcuxvXmB3rWHSqSviP5mrKMZoL2RArvgAAAAAiUSBGU0Lg5fx/ECsB1Z4ZUqXQFSLFnlmpm0rm5R2l599h2AAAAAABASvZECu+AAAAACJRIEZTQuDl/H8QKwHVnhlSpdAVIsWeWambSublHaXn32HYAQMEAAAAACEWF7hZVn7pIDR429kAn/WDeQiWjZey1iGHztsL1H83QLMZADlK7RRWAACAAQAAgAAAAIABAAAAAAAAAAEXIBe4WVZ+6SA0eNvZAJ/1g3kIlo2XstYhh87bC9R/N0CzACEHbJdqWyMxF2eOPr6YRXUJmry04HUbgKyeM2IZeG+NI9AZADlK7RRWAACAAQAAgAAAAIABAAAAAQAAAAEFIGyXalsjMRdnjj6+mEV1CZq8tOB1G4CsnjNiGXhvjSPQAAA="
        
        raw = a2b_base64(psbt_base64)
        tx = PSBT.parse(raw)
        
        mnemonic = "goddess rough corn exclude cream trial fee trumpet million prevent gaze power".split()
        pw = ""
        seed = Seed(mnemonic, passphrase=pw)

        pp = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

        assert pp.change_data == [
            {
                'output_index': 0,
                'address': 'bcrt1prz4g6saush37epdwhvwpu78td3q7yfz3xxz37axlx7udck6wracq3rwq30',
                'amount': 2_871_443_918,
                'fingerprint': ['394aed14'],
                'derivation_path': ['m/86h/1h/0h/1/1']}
            ]
        assert pp.spend_amount == 319_049_328
        assert pp.change_amount == 2_871_443_918
        assert pp.destination_addresses == ['bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek']
        assert pp.destination_amounts == [319_049_328]



class TestPSBTParserCooperativeSpend:
    malcolm_seed = Seed("better gown govern speak spawn vendor exercise item uncle odor sound cat".split())
    zoe_seed = Seed("sign sword lift deer ocean insect web lazy sick pencil start select".split())

    def test_payjoin(self):
        """
        has_external_inputs should return True when there is at least one input in the
        psbt that the signing key does not control.

        This test manually constructs a typical payjoin for each participant's context.
        * The recipient starts with a temporary self-payment to their own receive address.
        * The sender starts with a normal payment to the recipient.
        * The sender adds the recipient's input to their psbt and updates the payment amount
            accordingly.
        * The recipient adds the sender's input and the sender's change output to their psbt
            and updates their receive amount accordingly.
        """
        # The sender's initial psbt is just a normal payment; 1 input, 2 outputs (0: change, 1: receiver)
        malcolm_psbt_base64 = "cHNidP8BAHECAAAAAWvBiAY6UU7NLa1KICrjrxyaV9NB3dQVUnWnmNpP7SBGAQAAAAD9////Ata1PAAAAAAAFgAUcuNfLO4QMUvlKwpq5PQk+qFjAUUALTEBAAAAABYAFAyWIwiu+QIC4ZlObGHDlvZn6cwddwAAAE8BBDWHzwNXHdv+gAAAAG5A8fYC1UaCqTjVNmzP41+yrhVJEa02NktU+hU1gqpdAzp4rbh4dNpY+9lqJ8cE1mJQozBDm1mvmg6+s0+/TDUuEAPNCitUAACAAAAAgAAAAIAAAQEfivVtAQAAAAAWABTDpWRRgBdkOHw+xyCMOJAlYXOnDAEDBAEAAAAiBgLyWP5xUwnTMbj+HMUP62woAPFiEHvMJRZfp94fcnpRpxgDzQorVAAAgAAAAIAAAACAAAAAAAEAAAAAIgICz3sTM/0BgYjqZmMLL+67hILVA7diXpeQxlrZXreSc7sYA80KK1QAAIAAAACAAAAAgAEAAAABAAAAAAA="
        malcolm_psbt: PSBT = PSBT.parse(a2b_base64(malcolm_psbt_base64))
        malcolm_utxo_value = malcolm_psbt.inputs[0].utxo.value
        malcolm_payment = malcolm_psbt.outputs[1].value

        assert malcolm_utxo_value == 23_983_498
        assert malcolm_payment == 20_000_000

        # The receiver's initial psbt is an internal cycle spending her own utxo back to the same receive address as above
        # Additional 8,793,478 sats in the receiver's input.
        zoe_psbt_base64 = "cHNidP8BAFICAAAAAXAmz5cHZ6Z8NQtliuNnFqEV0GgegEaGOLkgnSEl334OAQAAAAD9////ARgthgAAAAAAFgAUDJYjCK75AgLhmU5sYcOW9mfpzB1uAAAATwEENYfPA6IqnfuAAAAAuBxif3KoUTYOOtbRNtTM66nYggBF1i/9wOO1oCmuPh0CP9yB9ueZ7pip6CzDKJhUUDBUXoh/3KlqjWrml9rXy3AQD4iQRFQAAIAAAACAAAAAgAABAR+GLYYAAAAAABYAFGcxK19pAPjZdCADa6WfVtPAawYqAQMEAQAAACIGA/XjxxoNMFunU4xNwU+BEIFSe1ilt+54iu5OC24O68qhGA+IkERUAACAAAAAgAAAAIAAAAAABAAAAAAiAgPGlMVmc+Nbw1Xehprds/1M9qKcaI+RzikiMqfussDzwRgPiJBEVAAAgAAAAIAAAACAAAAAAAUAAAAA"
        zoe_psbt: PSBT = PSBT.parse(a2b_base64(zoe_psbt_base64))
        zoe_utxo_value = zoe_psbt.inputs[0].utxo.value

        assert zoe_utxo_value == 8_793_478

        # Initially the respective psbts are not cooperative
        malcolm_psbt_parser = PSBTParser(malcolm_psbt, self.malcolm_seed)
        zoe_psbt_parser = PSBTParser(zoe_psbt, self.zoe_seed)
        assert malcolm_psbt_parser.is_cooperative_spend is False
        assert zoe_psbt_parser.is_cooperative_spend is False

        zoe_input_bip32_derivations = zoe_psbt.inputs[0].bip32_derivations
        zoe_output_bip32_derivations = zoe_psbt.outputs[0].bip32_derivations

        # Add the receiver's input to the sender's version of the payjoin tx
        malcolm_psbt.inputs.append(zoe_psbt.inputs[0])
        malcolm_psbt.inputs[1].bip32_derivations = OrderedDict()  # sender typically won't know these details about the receiver's input

        # Credit the receiver's total amount to be received
        malcolm_psbt.outputs[1].value = malcolm_payment + zoe_utxo_value

        # Malcolm's psbt is now the expected structure for this tx
        pj_zoe_psbt = deepcopy(malcolm_psbt)
        pj_zoe_psbt.inputs[0].bip32_derivations = OrderedDict()  # recipient typically won't know these details about the sender's input
        pj_zoe_psbt.inputs[1].bip32_derivations = zoe_input_bip32_derivations
        pj_zoe_psbt.outputs[1].bip32_derivations = zoe_output_bip32_derivations

        assert malcolm_psbt.tx.txid() == pj_zoe_psbt.tx.txid()

        print(f"\nMalcolm's PSBT: {malcolm_psbt}\n")
        print(f"Zoe's PSBT: {pj_zoe_psbt}\n")

        malcolm_psbt_parser = PSBTParser(malcolm_psbt, self.malcolm_seed)
        zoe_psbt_parser = PSBTParser(pj_zoe_psbt, self.zoe_seed)

        # Both parties should now view this as a cooperative spend
        assert malcolm_psbt_parser.is_cooperative_spend
        assert zoe_psbt_parser.is_cooperative_spend
        assert malcolm_psbt_parser.num_external_inputs > 0
        assert malcolm_psbt_parser.num_inputs == 1
        assert zoe_psbt_parser.num_external_inputs > 0
        assert zoe_psbt_parser.num_inputs == 1

        # But differ on their perspective of whether this is a payjoin receive
        assert malcolm_psbt_parser.is_payjoin_receive is False
        assert zoe_psbt_parser.is_payjoin_receive

        # Verify that the inputs are parsed correctly from Zoe's perspective
        assert zoe_psbt_parser.external_input_amount == malcolm_utxo_value
        assert zoe_psbt_parser.input_amount == zoe_utxo_value

        # Input contexts are reversed from Malcolm's perspective
        assert malcolm_psbt_parser.external_input_amount == zoe_utxo_value
        assert malcolm_psbt_parser.input_amount == malcolm_utxo_value

        # sanity check that both parties can sign
        assert malcolm_psbt.sign_with(bip32.HDKey.from_seed(self.malcolm_seed.seed_bytes)) == 1
        assert pj_zoe_psbt.sign_with(bip32.HDKey.from_seed(self.zoe_seed.seed_bytes)) == 1


    def test_coinjoin(self):
        # 3 of Malcolm's inputs; change + 2 equal-size coinjoin outputs
        malcolm_psbt_base64 = "cHNidP8BAOICAAAAA1LLjoXF/w70yPwWYGLNsnomFT+xOzfbQ6BvUnWJ30hDAQAAAAD9////UsuOhcX/DvTI/BZgYs2yeiYVP7E7N9tDoG9SdYnfSEMDAAAAAP3///9Sy46Fxf8O9Mj8FmBizbJ6JhU/sTs320Ogb1J1id9IQwIAAAAA/f///wOjQEEAAAAAABYAFC9NKd1nKSURCfVJ0o6jWWeWlmjhgJaYAAAAAAAWABRX/KTAYaj0b7PKz5gyctryXOfEsoCWmAAAAAAAFgAU/TrhKNM2cRT6q+DIUguvy+qU4/d5AAAATwEENYfPA1cd2/6AAAAAbkDx9gLVRoKpONU2bM/jX7KuFUkRrTY2S1T6FTWCql0DOnituHh02lj72WonxwTWYlCjMEObWa+aDr6zT79MNS4QA80KK1QAAIAAAACAAAAAgAABAR9ISakAAAAAABYAFONgMJvheO31yuSQZOaRNSrrbLdUAQMEAQAAACIGAwdb3fkBR1JOPt/lypRlqhdAzMUR3v1BknnKcD2IXtXzGAPNCitUAACAAAAAgAAAAIAAAAAAAwAAAAABAR/TPGwAAAAAABYAFFHsyt85+w/2e7hF0EPwiCY/TflkAQMEAQAAACIGA+f4JzG7qkZI4HSOq4FYksLwMmk3sksU1v7O0rMzVsrzGAPNCitUAACAAAAAgAAAAIAAAAAABAAAAAABAR+mDV0AAAAAABYAFB+v75HNdP9+BwA5PwHAAwouJdHyAQMEAQAAACIGAgr+mKm0GojP1MHLvlMUOEF7JHomGlLx1e1CbQsJdpNhGAPNCitUAACAAAAAgAAAAIAAAAAAAgAAAAAiAgOY2SYAfhS5fpzPQjMbNMEFbu+0q4EXkrYrhO4ksgJUGxgDzQorVAAAgAAAAIAAAACAAQAAAAIAAAAAIgID+67J/K4WQEgB5upEyOHKgHz+gjBNpa8pKEYoHIyQgUAYA80KK1QAAIAAAACAAAAAgAAAAAAGAAAAACICArA+YcBFJsnK5Tv5TkMdRC00Dw0+Rkf2S85oIr+PtG8RGAPNCitUAACAAAAAgAAAAIAAAAAABQAAAAA="

        # 2 of Zoe's inputs; 4 outputs: change + 3 equal-size coinjoin outputs
        zoe_psbt_base64 = "cHNidP8BANgCAAAAApk9OYgpN9j+vkxjBDBisOph+n02n7DYgmqp2z2wYHdeAQAAAAD9////mT05iCk32P6+TGMEMGKw6mH6fTafsNiCaqnbPbBgd14DAAAAAP3///8EKNIJAAAAAAAWABSRrp8CppZ5NN7QHVu1NHo2xDTJB4CWmAAAAAAAFgAUDJYjCK75AgLhmU5sYcOW9mfpzB2AlpgAAAAAABYAFFHi/EAdZ5+P+9PpJGDhC4kYs4TBgJaYAAAAAAAWABRnMStfaQD42XQgA2uln1bTwGsGKnkAAABPAQQ1h88Doiqd+4AAAAC4HGJ/cqhRNg461tE21MzrqdiCAEXWL/3A47WgKa4+HQI/3IH255numKnoLMMomFRQMFReiH/cqWqNauaX2tfLcBAPiJBEVAAAgAAAAIAAAACAAAEBHw3OewEAAAAAFgAUL98iIGb8nh2lZPktQvhScSXBWxABAwQBAAAAIgYCxPptltDpFMOMtI1sONzpkTfBFGYy1+oDti7jpXMCsxYYD4iQRFQAAIAAAACAAAAAgAAAAAADAAAAAAEBH1jtVwAAAAAAFgAUQKgWEXX0alk8P5TfhU4iczaYeZkBAwQBAAAAIgYDg0wW7W9vxlrfF/Ws48iBKc7Ra9TXxnarVQ0c9yhoT/QYD4iQRFQAAIAAAACAAAAAgAAAAAABAAAAACICA8GKzu4dfk0sHhD3wNSFxNPpvbsU17XHT5oUaBC72U0QGA+IkERUAACAAAAAgAAAAIABAAAAAQAAAAAiAgPGlMVmc+Nbw1Xehprds/1M9qKcaI+RzikiMqfussDzwRgPiJBEVAAAgAAAAIAAAACAAAAAAAUAAAAAIgICvwd7ouMhVz/1SQqiIZoTkg4IYdh97/qbLZbybz1z7W8YD4iQRFQAAIAAAACAAAAAgAAAAAAGAAAAACICA/XjxxoNMFunU4xNwU+BEIFSe1ilt+54iu5OC24O68qhGA+IkERUAACAAAAAgAAAAIAAAAAABAAAAAA="

        malcolm_psbt: PSBT = PSBT.parse(a2b_base64(malcolm_psbt_base64))
        assert len(malcolm_psbt.inputs) == 3
        assert len(malcolm_psbt.outputs) == 3
        assert malcolm_psbt.outputs[1].value == 10_000_000
        assert malcolm_psbt.outputs[2].value == 10_000_000
        malcolm_input_value = sum([inp.utxo.value for inp in malcolm_psbt.inputs])
        malcolm_change_value = malcolm_psbt.outputs[0].value
        assert malcolm_input_value == 2*10_000_000 + malcolm_psbt.fee() + malcolm_change_value

        zoe_psbt: PSBT = PSBT.parse(a2b_base64(zoe_psbt_base64))
        assert len(zoe_psbt.inputs) == 2
        assert len(zoe_psbt.outputs) == 4
        assert zoe_psbt.outputs[1].value == 10_000_000
        assert zoe_psbt.outputs[2].value == 10_000_000
        assert zoe_psbt.outputs[3].value == 10_000_000
        zoe_input_value = sum([inp.utxo.value for inp in zoe_psbt.inputs])
        zoe_change_value = zoe_psbt.outputs[0].value
        assert zoe_input_value == 3*10_000_000 + zoe_psbt.fee() + zoe_change_value

        # Now merge the two txs into an initial coinjoin tx
        initial_coinjoin_psbt = deepcopy(malcolm_psbt)
        initial_coinjoin_psbt.inputs.extend(zoe_psbt.inputs)
        initial_coinjoin_psbt.outputs.extend(zoe_psbt.outputs)

        assert len(initial_coinjoin_psbt.inputs) == 5
        assert len(initial_coinjoin_psbt.outputs) == 7

        # Malcolm's version won't know any of Zoe's bip32 derivation details
        malcolm_coinjoin_psbt = deepcopy(initial_coinjoin_psbt)
        for inp in malcolm_coinjoin_psbt.inputs[3:]:
            # Wipe Zoe's inputs
            inp.bip32_derivations = OrderedDict()
        for out in malcolm_coinjoin_psbt.outputs[3:]:
            # Wipe Zoe's outputs
            out.bip32_derivations = OrderedDict()
        
        zoe_coinjoin_psbt = deepcopy(initial_coinjoin_psbt)
        for inp in zoe_coinjoin_psbt.inputs[:3]:
            # Wipe Malcolm's inputs
            inp.bip32_derivations = OrderedDict()
        for out in zoe_coinjoin_psbt.outputs[:3]:
            # Wipe Malcolm's outputs
            out.bip32_derivations = OrderedDict()
        
        assert malcolm_coinjoin_psbt.tx.txid() == zoe_coinjoin_psbt.tx.txid()

        print(f"\nMalcolm's coinjoin PSBT: {malcolm_coinjoin_psbt}\n")
        print(f"Zoe's coinjoin PSBT: {zoe_coinjoin_psbt}\n")

        # Verify Malcolm's perspective of his inputs vs external inputs
        malcolm_psbt_parser = PSBTParser(malcolm_coinjoin_psbt, self.malcolm_seed)
        assert malcolm_psbt_parser.num_inputs == len(malcolm_psbt.inputs)
        assert malcolm_psbt_parser.num_external_inputs == len(zoe_psbt.inputs)
        assert malcolm_psbt_parser.num_inputs + malcolm_psbt_parser.num_external_inputs == len(initial_coinjoin_psbt.inputs)

        # Verify Malcolm's perspective of his outputs (his change and receive addrs are
        # both called "change" in current PSBTParser attr) vs external recipients.
        assert malcolm_psbt_parser.num_change_outputs == len(malcolm_psbt.outputs)
        assert malcolm_psbt_parser.change_amount == 2*10_000_000 + malcolm_change_value
        assert malcolm_psbt_parser.num_destinations == len(zoe_psbt.outputs)
        assert malcolm_psbt_parser.spend_amount == 3*10_000_000 + zoe_change_value

        # Verify Zoe's perspective of his inputs vs external inputs
        zoe_psbt_parser = PSBTParser(zoe_coinjoin_psbt, self.zoe_seed)
        assert zoe_psbt_parser.num_inputs == len(zoe_psbt.inputs)
        assert zoe_psbt_parser.num_external_inputs == len(malcolm_psbt.inputs)
        assert zoe_psbt_parser.num_inputs + zoe_psbt_parser.num_external_inputs == len(initial_coinjoin_psbt.inputs)

        # Verify Zoe's perspective of his outputs (his change and receive addrs are
        # both called "change" in current PSBTParser attr) vs external recipients.
        assert zoe_psbt_parser.num_change_outputs == len(zoe_psbt.outputs)
        assert zoe_psbt_parser.change_amount == 3*10_000_000 + zoe_change_value
        assert zoe_psbt_parser.num_destinations == len(malcolm_psbt.outputs)
        assert zoe_psbt_parser.spend_amount == 2*10_000_000 + malcolm_change_value

        # Verify that each party can sign
        assert malcolm_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.malcolm_seed.seed_bytes)) == 3
        assert zoe_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.zoe_seed.seed_bytes)) == 2


    def test_coinjoin_with_extra_output(self):
        """
            Two-party coinjoin yielding equal-size outputs, but with each party including
            an output to pay a third party coordinator.
        """
        # 3 of Malcolm's inputs; change + 2 equal-size coinjoin outputs + payment to 3rd party coordinator
        malcolm_psbt_base64 = "cHNidP8BAP0BAQIAAAADUsuOhcX/DvTI/BZgYs2yeiYVP7E7N9tDoG9SdYnfSEMCAAAAAP3///9Sy46Fxf8O9Mj8FmBizbJ6JhU/sTs320Ogb1J1id9IQwMAAAAA/f///1LLjoXF/w70yPwWYGLNsnomFT+xOzfbQ6BvUnWJ30hDAQAAAAD9////BDlsPQAAAAAAFgAUL00p3WcpJREJ9UnSjqNZZ5aWaOGAlpgAAAAAABYAFFf8pMBhqPRvs8rPmDJy2vJc58SygJaYAAAAAAAWABT9OuEo0zZxFPqr4MhSC6/L6pTj95DQAwAAAAAAFgAU+LYJo7gtgJH7LJn08DAru4OOSO15AAAATwEENYfPA1cd2/6AAAAAbkDx9gLVRoKpONU2bM/jX7KuFUkRrTY2S1T6FTWCql0DOnituHh02lj72WonxwTWYlCjMEObWa+aDr6zT79MNS4QA80KK1QAAIAAAACAAAAAgAABAR+mDV0AAAAAABYAFB+v75HNdP9+BwA5PwHAAwouJdHyAQMEAQAAACIGAgr+mKm0GojP1MHLvlMUOEF7JHomGlLx1e1CbQsJdpNhGAPNCitUAACAAAAAgAAAAIAAAAAAAgAAAAABAR/TPGwAAAAAABYAFFHsyt85+w/2e7hF0EPwiCY/TflkAQMEAQAAACIGA+f4JzG7qkZI4HSOq4FYksLwMmk3sksU1v7O0rMzVsrzGAPNCitUAACAAAAAgAAAAIAAAAAABAAAAAABAR9ISakAAAAAABYAFONgMJvheO31yuSQZOaRNSrrbLdUAQMEAQAAACIGAwdb3fkBR1JOPt/lypRlqhdAzMUR3v1BknnKcD2IXtXzGAPNCitUAACAAAAAgAAAAIAAAAAAAwAAAAAiAgOY2SYAfhS5fpzPQjMbNMEFbu+0q4EXkrYrhO4ksgJUGxgDzQorVAAAgAAAAIAAAACAAQAAAAIAAAAAIgID+67J/K4WQEgB5upEyOHKgHz+gjBNpa8pKEYoHIyQgUAYA80KK1QAAIAAAACAAAAAgAAAAAAGAAAAACICArA+YcBFJsnK5Tv5TkMdRC00Dw0+Rkf2S85oIr+PtG8RGAPNCitUAACAAAAAgAAAAIAAAAAABQAAAAAA"

        # 2 of Zoe's inputs; 4 outputs: change + 3 equal-size coinjoin outputs + payment to 3rd party coordinator
        zoe_psbt_base64 = "cHNidP8BAPcCAAAAApk9OYgpN9j+vkxjBDBisOph+n02n7DYgmqp2z2wYHdeAwAAAAD9////mT05iCk32P6+TGMEMGKw6mH6fTafsNiCaqnbPbBgd14BAAAAAP3///8FQv0FAAAAAAAWABSRrp8CppZ5NN7QHVu1NHo2xDTJB4CWmAAAAAAAFgAUZzErX2kA+Nl0IANrpZ9W08BrBiqAlpgAAAAAABYAFAyWIwiu+QIC4ZlObGHDlvZn6cwdgJaYAAAAAAAWABRR4vxAHWefj/vT6SRg4QuJGLOEwZDQAwAAAAAAFgAURsVsVzfCll3oga2Z1CByV626Q955AAAATwEENYfPA6IqnfuAAAAAuBxif3KoUTYOOtbRNtTM66nYggBF1i/9wOO1oCmuPh0CP9yB9ueZ7pip6CzDKJhUUDBUXoh/3KlqjWrml9rXy3AQD4iQRFQAAIAAAACAAAAAgAABAR9Y7VcAAAAAABYAFECoFhF19GpZPD+U34VOInM2mHmZAQMEAQAAACIGA4NMFu1vb8Za3xf1rOPIgSnO0WvU18Z2q1UNHPcoaE/0GA+IkERUAACAAAAAgAAAAIAAAAAAAQAAAAABAR8NznsBAAAAABYAFC/fIiBm/J4dpWT5LUL4UnElwVsQAQMEAQAAACIGAsT6bZbQ6RTDjLSNbDjc6ZE3wRRmMtfqA7Yu46VzArMWGA+IkERUAACAAAAAgAAAAIAAAAAAAwAAAAAiAgPBis7uHX5NLB4Q98DUhcTT6b27FNe1x0+aFGgQu9lNEBgPiJBEVAAAgAAAAIAAAACAAQAAAAEAAAAAIgID9ePHGg0wW6dTjE3BT4EQgVJ7WKW37niK7k4Lbg7ryqEYD4iQRFQAAIAAAACAAAAAgAAAAAAEAAAAACICA8aUxWZz41vDVd6Gmt2z/Uz2opxoj5HOKSIyp+6ywPPBGA+IkERUAACAAAAAgAAAAIAAAAAABQAAAAAiAgK/B3ui4yFXP/VJCqIhmhOSDghh2H3v+pstlvJvPXPtbxgPiJBEVAAAgAAAAIAAAACAAAAAAAYAAAAAAA=="

        malcolm_psbt: PSBT = PSBT.parse(a2b_base64(malcolm_psbt_base64))
        zoe_psbt: PSBT = PSBT.parse(a2b_base64(zoe_psbt_base64))

        assert len(malcolm_psbt.outputs) == 4
        assert len(zoe_psbt.outputs) == 5

        # Now merge the two txs into an initial coinjoin tx
        initial_coinjoin_psbt = deepcopy(malcolm_psbt)
        initial_coinjoin_psbt.inputs.extend(zoe_psbt.inputs)
        initial_coinjoin_psbt.outputs.extend(zoe_psbt.outputs)

        assert len(initial_coinjoin_psbt.inputs) == 5
        assert len(initial_coinjoin_psbt.outputs) == 9

        # Malcolm's version won't know any of Zoe's bip32 derivation details
        malcolm_coinjoin_psbt = deepcopy(initial_coinjoin_psbt)
        for inp in malcolm_coinjoin_psbt.inputs[3:]:
            # Wipe Zoe's inputs
            inp.bip32_derivations = OrderedDict()
        for out in malcolm_coinjoin_psbt.outputs[4:]:
            # Wipe Zoe's outputs
            out.bip32_derivations = OrderedDict()
        
        zoe_coinjoin_psbt = deepcopy(initial_coinjoin_psbt)
        for inp in zoe_coinjoin_psbt.inputs[:3]:
            # Wipe Malcolm's inputs
            inp.bip32_derivations = OrderedDict()
        for out in zoe_coinjoin_psbt.outputs[:4]:
            # Wipe Malcolm's outputs
            out.bip32_derivations = OrderedDict()
        
        assert malcolm_coinjoin_psbt.tx.txid() == zoe_coinjoin_psbt.tx.txid()

        print(f"\nMalcolm's coinjoin + payment PSBT: {malcolm_coinjoin_psbt}\n")
        print(f"Zoe's coinjoin + payment PSBT: {zoe_coinjoin_psbt}\n")

        # Verify Malcolm's perspective of his inputs vs external inputs
        malcolm_psbt_parser = PSBTParser(malcolm_coinjoin_psbt, self.malcolm_seed)
        assert malcolm_psbt_parser.num_inputs == len(malcolm_psbt.inputs)
        assert malcolm_psbt_parser.num_external_inputs == len(zoe_psbt.inputs)
        assert malcolm_psbt_parser.num_inputs + malcolm_psbt_parser.num_external_inputs == len(initial_coinjoin_psbt.inputs)

        # Verify Malcolm's perspective of his outputs (his change and receive addrs are
        # both called "change" in current PSBTParser attr) vs external recipients.
        assert malcolm_psbt_parser.num_change_outputs == len(malcolm_psbt.outputs) - 1  # Subtract Malcolm's payment to coordinator
        assert malcolm_psbt_parser.num_destinations == len(zoe_psbt.outputs) + 1        # All of Zoe's outputs plus Malcolm's payment to coordinator

        # Verify Zoe's perspective of his inputs vs external inputs
        zoe_psbt_parser = PSBTParser(zoe_coinjoin_psbt, self.zoe_seed)
        assert zoe_psbt_parser.num_inputs == len(zoe_psbt.inputs)
        assert zoe_psbt_parser.num_external_inputs == len(malcolm_psbt.inputs)
        assert zoe_psbt_parser.num_inputs + zoe_psbt_parser.num_external_inputs == len(initial_coinjoin_psbt.inputs)

        # Verify Zoe's perspective of his outputs (his change and receive addrs are
        # both called "change" in current PSBTParser attr) vs external recipients.
        assert zoe_psbt_parser.num_change_outputs == len(zoe_psbt.outputs) - 1
        assert zoe_psbt_parser.num_destinations == len(malcolm_psbt.outputs) + 1

        # Verify that each party can sign
        assert malcolm_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.malcolm_seed.seed_bytes)) == 3
        assert zoe_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.zoe_seed.seed_bytes)) == 2