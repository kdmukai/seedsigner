from collections import OrderedDict
from copy import deepcopy
import random

from binascii import a2b_base64
from embit import bip32
from embit.psbt import PSBT
from embit.descriptor import Descriptor

from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants

from psbt_testing_util import PSBTTestData, create_output



class TestPSBTParser:
    """
    Exhaustively test all supported script input and output types.
    """
    seed = PSBTTestData.seed

    def run_basic_test(self, psbt_base64: str, change_data: str, self_transfer_data: str):
        """
        Constructs a series of test psbts that use the specified `psbt_base64` for the input(s).

        * A spend to each recipient type + specified `change_data`
        * Self-transfer back to sender via the `self_transfer_data`
        * A full spend (no change) to each recipient type
        * 1 mega psbt with an output to each recipient type + specified `change_data`
        """
        psbt: PSBT = PSBT.parse(a2b_base64(psbt_base64))
        input_amount = sum([inp.utxo.value for inp in psbt.inputs])
        recipient_amount = random.randint(200_000, 90_000_000)
        fee_amount = 5_000
        change_output = create_output(change_data, input_amount - recipient_amount - fee_amount)

        # Spend the input(s) to each supported recipient type + change
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
            assert psbt_parser.change_amount == input_amount - recipient_amount - fee_amount
            assert psbt_parser.fee_amount == fee_amount
            assert psbt_parser.input_amount + psbt_parser.external_input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount
        
        # Internally cycle the input(s) back to sender via the `self_transfer_data`
        psbt.outputs.clear()
        psbt.outputs.append(create_output(self_transfer_data, input_amount - fee_amount))

        assert len(psbt.outputs) == 1
        psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
        assert psbt_parser.num_inputs == len(psbt.inputs)
        assert psbt_parser.num_external_inputs == 0
        assert psbt_parser.input_amount == input_amount
        assert psbt_parser.num_destinations == 0    # No external recipients == no destinations
        assert psbt_parser.num_change_outputs == 1  # PSBTParser considers self-transfers == change
        assert psbt_parser.spend_amount == 0        # No external recipients == nothing spent (ignores fee)
        assert psbt_parser.change_amount == input_amount - fee_amount  # PSBTParser considers self-transfers == change
        assert psbt_parser.fee_amount == fee_amount
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
        self.run_basic_test(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE, PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_SELF_TRANSFER)

    def test_singlesig_nested_segwit(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_1_INPUT, PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_CHANGE, PSBTTestData.SINGLE_SIG_NESTED_SEGWIT_SELF_TRANSFER)

    def test_singlesig_taproot(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_TAPROOT_1_INPUT, PSBTTestData.SINGLE_SIG_TAPROOT_CHANGE, PSBTTestData.SINGLE_SIG_TAPROOT_SELF_TRANSFER)

    def test_singlesig_legacy_p2pkh(self):
        self.run_basic_test(PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_1_INPUT, PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_CHANGE, PSBTTestData.SINGLE_SIG_LEGACY_P2PKH_SELF_TRANSFER)

    def test_multisig_native_segwit(self):
        self.run_basic_test(PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE, PSBTTestData.MULTISIG_NATIVE_SEGWIT_SELF_TRANSFER)

    def test_multisig_nested_segwit(self):
        self.run_basic_test(PSBTTestData.MULTISIG_NESTED_SEGWIT_1_INPUT, PSBTTestData.MULTISIG_NESTED_SEGWIT_CHANGE, PSBTTestData.MULTISIG_NESTED_SEGWIT_SELF_TRANSFER)

    def test_multisig_legacy_p2sh(self):
        self.run_basic_test(PSBTTestData.MULTISIG_LEGACY_P2SH_1_INPUT, PSBTTestData.MULTISIG_LEGACY_P2SH_CHANGE, PSBTTestData.MULTISIG_LEGACY_P2SH_SELF_TRANSFER)


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
            psbt: PSBT = PSBT.parse(a2b_base64(input))
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
        """
        PSBTParser should correctly verify multisig change and self-transfer outputs against the
        provided descriptor or fail to verify if we provide the wrong descriptor.
        """
        multisig_inputs = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_1_INPUT,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_1_INPUT,
            PSBTTestData.MULTISIG_LEGACY_P2SH_1_INPUT
        ]
        change_outputs =  [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_CHANGE,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_CHANGE,
            PSBTTestData.MULTISIG_LEGACY_P2SH_CHANGE
        ]
        self_transfer_outputs = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_SELF_TRANSFER,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_SELF_TRANSFER,
            PSBTTestData.MULTISIG_LEGACY_P2SH_SELF_TRANSFER
        ]
        descriptors = [
            PSBTTestData.MULTISIG_NATIVE_SEGWIT_DESCRIPTOR,
            PSBTTestData.MULTISIG_NESTED_SEGWIT_DESCRIPTOR,
            PSBTTestData.MULTISIG_LEGACY_P2SH_DESCRIPTOR
        ]

        for i, psbt_base64 in enumerate(multisig_inputs):
            # Construct a psbt with change & self-transfer outputs of the same type as the input
            psbt: PSBT = PSBT.parse(a2b_base64(psbt_base64))
            psbt.outputs.append(create_output(change_outputs[i], 100_000))
            psbt.outputs.append(create_output(self_transfer_outputs[i], 100_000))
            psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)

            # Attempt to verify the change & self-transfer outputs using the right and wrong descriptors
            for j, descriptor_str in enumerate(descriptors):
                descriptor = Descriptor.from_string(descriptor_str.replace("<0;1>", "{0,1}"))
                if i == j:
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=0) == True
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=1) == True  # self-transfer is considered change
                else:
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=0) == False
                    assert psbt_parser.verify_multisig_output(descriptor, change_num=1) == False



# TODO: Refactor all tests to be in the TestPSBTParser class(?)
def test_p2tr_change_detection():
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
            'amount': 2871443918,
            'fingerprint': ['394aed14'],
            'derivation_path': ['m/86h/1h/0h/1/1']}
        ]
    assert pp.spend_amount == 319049328
    assert pp.change_amount == 2871443918
    assert pp.destination_addresses == ['bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek']
    assert pp.destination_amounts == [319049328]



# TODO: Test no longer necessary now that we have exhaustive tests for all types above?
def test_p2sh_legacy_multisig():
    """
        Should correctly parse a legacy multisig p2sh (m/45') psbt.

        PSBT Tx, wallet, and keys
        - Legacy 2-of-3 multisig p2sh; same format as Unchained
        - Regtest xpubs:
            - 0f889044 m/45' tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62 (aka "Zoe" test seed)
            - 03cd0a2b m/45' tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L (aka "Malcolm" test seed)
            - 769f695c m/45' tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM (aka "Unchained" test seed)

        - 2 Inputs
            - 199,661 sats
        - 3 Outputs
            - 1 Output spend to another wallet: 50,000 sats to bcrt1q8q5uk9z7ta08h8hvknysd5n80w6f7kuvk5ey2m
            - 1 Output internal self-cycle
                - addresss 2N5eN5vUpgsLHAGzKm2VfmYyvNwXmCug5dH
                - amount 90,000 sats
                - receive address is index 0/5
            - 1 Output change
                - addresss 2NEnA5emHw9Q6vHXr912hGMSPtnrwAMReLz)
                - amount 58,969 sats
                - change addresses is index 1/0
            - Fee 692 sats

        "Malcolm": better gown govern speak spawn vendor exercise item uncle odor sound cat
        "Zoe": sign sword lift deer ocean insect web lazy sick pencil start select
        "Unchained": slight affair prefer tenant vacant below drill govern surface science affair nut

    """
    descriptor = Descriptor.from_string("sh(sortedmulti(2,[0f889044/45h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/<0;1>/*,[03cd0a2b/45h]tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L/<0;1>/*,[769f695c/45h]tpubD98hRDKvtATTM8hy5Vvt5ZrvDXwJvrUZm1p1mTKDmd7FqUHY9Wj2k4X1CvxjjtTf3JoChWqYbnWjfkRJ65GQnpVJKbbMfjnGzCwoBUXafyM/<0;1>/*))#uardwtq4".replace("<0;1>", "{0,1}"))
    psbt_base64 = "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"
    raw = a2b_base64(psbt_base64)
    tx = PSBT.parse(raw)

    # 03cd0a2b test seed
    mnemonic = "better gown govern speak spawn vendor exercise item uncle odor sound cat".split()
    seed = Seed(mnemonic)
    assert seed.get_fingerprint() == "03cd0a2b"

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

    assert psbt_parser.spend_amount == 50000
    assert psbt_parser.change_amount == 90000 + 58969
    assert psbt_parser.fee_amount == 692

    assert psbt_parser.destination_addresses == ['bcrt1q8q5uk9z7ta08h8hvknysd5n80w6f7kuvk5ey2m']
    assert psbt_parser.destination_amounts == [50000]

    assert psbt_parser.get_change_data(0)['address'] == '2NEnA5emHw9Q6vHXr912hGMSPtnrwAMReLz'
    assert psbt_parser.get_change_data(0)["amount"] == 58969

    assert psbt_parser.get_change_data(1)['address'] == '2N5eN5vUpgsLHAGzKm2VfmYyvNwXmCug5dH'
    assert psbt_parser.get_change_data(1)["amount"] == 90000

    # We should be able to verify the change addr
    assert psbt_parser.verify_multisig_output(descriptor, 0)

    # And the self-transfer receive addr
    assert psbt_parser.verify_multisig_output(descriptor, 1)



# TODO: Test no longer necessary now that we have exhaustive tests for all types above?
def test_p2sh_p2wpkh_nested_segwit():
    """
        Should correctly parse a nested segwit (m/49'/1'/0') psbt.

        PSBT Tx, wallet, and keys
        - nested segwit single sig
        - Regtest xpubs:
            - c751dc07 c751dc07 tpubDDS23bf7c9mdfWpuvA61HHCYDusq25UtMNYsFagKPNMNWHSm8bvwmNNP2KSpivN3gQWAK8fhDFk3dzgoBn9rPoMncKxJuqNAv7sJMShbZ6i

        - 1 Inputs
            - 149,009 sats
        - 2 Outputs
            - 1 Output spend to another wallet: 93,000 sats to tb1qs7mdpjq7g7zq46vvycr8d6udc7za726ut8har9krfxpnc7kr04gqmdy2e4
            - 1 Output change
                - addresss 2Mz3MthXyM4YDjLPw1V4PAacKt4pD8Cz8N3)
                - amount 55,832 sats
                - change addresses is index 1/1
            - Fee 177 sats

        seed: goddess rough corn exclude cream trial fee trumpet million prevent gaze power
        passphrase: test

    """

    descriptor = Descriptor.from_string("sh(wpkh([c751dc07/49h/1h/0h]tpubDDS23bf7c9mdfWpuvA61HHCYDusq25UtMNYsFagKPNMNWHSm8bvwmNNP2KSpivN3gQWAK8fhDFk3dzgoBn9rPoMncKxJuqNAv7sJMShbZ6i/<0;1>/*))#7sn8gf37".replace("<0;1>", "{0,1}"))
    psbt_base64 = "cHNidP8BAH4CAAAAAXfY5crHl+bXtTvKvdo2MaFQeIXw+P+3kzZwBRgw84lFAQAAAAD9////AhjaAAAAAAAAF6kUSop8lEmO4FB1AyV1GJe2bygA7ASHSGsBAAAAAAAiACCHttDIHkeECumMJgZ2643Hhd8rXFnv0ZbDSYM8esN9UIouEwBPAQQ1h88Dv3UWAIAAAACfHgAYuw3ODwXCSP0valI9edAB1t3EInR2TXkbOd+F+AJgmJs8XUkZD5zQAgd3+/ijOqVphlWUMzxDnRorBQYEgxDHUdwHMQAAgAEAAIAAAACAAAEBIBFGAgAAAAAAF6kU7ijES3iWT8u0+44/blPlLfh9WkyHAQMEAQAAAAEEFgAUX7JspW1r0gC+WkUHwGABJ8DU9f8iBgO1/adRC+r8XJ/bjnfdwk3740n0m8gE3+xN8GHsNrxDUxjHUdwHMQAAgAEAAIAAAACAAQAAAAAAAAAAAQAWABT8V9vY29XR8niVYdVSF9H4zRTAbiICArH6DjPShnzXiaAnc2BR1f61QQliH0BOhqAvksByf3e9GMdR3AcxAACAAQAAgAAAAIABAAAAAQAAAAAA"
    raw = a2b_base64(psbt_base64)
    tx = PSBT.parse(raw)

    # 03cd0a2b test seed
    mnemonic = "goddess rough corn exclude cream trial fee trumpet million prevent gaze power".split()
    seed = Seed(mnemonic=mnemonic, passphrase="test")
    assert seed.get_fingerprint() == "c751dc07"

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.TESTNET)

    assert psbt_parser.spend_amount == 93000
    assert psbt_parser.change_amount == 55832
    assert psbt_parser.fee_amount == 177

    assert psbt_parser.destination_addresses == ['tb1qs7mdpjq7g7zq46vvycr8d6udc7za726ut8har9krfxpnc7kr04gqmdy2e4']
    assert psbt_parser.destination_amounts == [93000]

    assert psbt_parser.get_change_data(0)['address'] == '2Mz3MthXyM4YDjLPw1V4PAacKt4pD8Cz8N3'
    assert psbt_parser.get_change_data(0)["amount"] == 55832

    # We should be able to verify the change addr
    assert psbt_parser.verify_multisig_output(descriptor, 0)



def test_parse_op_return_content():
    """
        Should successfully parse the OP_RETURN content from a PSBT.

        PSBT Tx and Wallet Details
        - Single Sig Wallet P2WPKH (Native Segwit) with no passphrase
        - Regtest 0fb882ff m/84'/1'/0' tpubDCfk37PqcQx6nFtFVuYHvRLJHxvYj33NjHkKRyRmWyCjyJ64sYBXyVjsTHaLBp5GLhM91VBgJ8nKDWDu52J2xVRy64c7ybEjjyWQJuQGLcg
        - 1 Input
            - 99,992,460 sats
        - 2 Outputs
            - 1 Output back to self (bcrt1qvwkhakqhz7m7kmz6332avatsmdy32m644g86vv) of 99,992,296 sats
            - 1 OP_RETURN: "Chancellor on the brink of third bailout"
        - Fee 164 sats
    """
    psbt_base64 = "cHNidP8BAIYCAAAAATpQ10o+gKdZ8ThpKsbfHiHYn3NhvUrQ5DvW0ZWX8jKLAAAAAAD9////AujC9QUAAAAAFgAUY61+2BcXt+tsWoxV1nVw20kVb1UAAAAAAAAAACtqTChDaGFuY2VsbG9yIG9uIHRoZSBicmluayBvZiB0aGlyZCBiYWlsb3V0aQAAAE8BBDWHzwNXmUmVgAAAANRFa7R5gYD84Wbha3d1QnjgfYPOBw87on6cXS32WoyqAsPFtPxB7PRTdbujUnBPUVDh9YUBtwrl4nc0OcRNGvIyEA+4gv9UAACAAQAAgAAAAIAAAQB0AgAAAAGNFK/1X0fP5q+nu5XX7Tk2VRa0EL+jkGI9CHiJvsjZCgAAAAAA/f///wKMw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAAAAAAAAAAAZakwWYml0Y29pbiBpcyBmcmVlIHNwZWVjaGgAAAABAR+Mw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAQMEAQAAACIGAvxDI0eNI1oQ2AU69R7A0jf+hUdilWCgrWHgdzkqlaXMGA+4gv9UAACAAQAAgAAAAIAAAAAAAQAAAAAiAgK9qKtzGWyiRrpmupdA99NVLriz3GQy6cENbyD19sfl/hgPuIL/VAAAgAEAAIAAAACAAAAAAAIAAAAAAA=="

    raw = a2b_base64(psbt_base64)
    tx = PSBT.parse(raw)

    mnemonic = "model ensure search plunge galaxy firm exclude brain satoshi meadow cable roast".split()
    pw = ""
    seed = Seed(mnemonic, passphrase=pw)

    psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)

    # Remember to do the comparison as bytes
    assert psbt_parser.op_return_data == "Chancellor on the brink of third bailout".encode()

    # PSBT is an internal self-spend to the its own receive addr, but the parser categorizes it as "change"
    assert psbt_parser.change_data == [
        {
            'output_index': 0,
            'address': 'bcrt1qvwkhakqhz7m7kmz6332avatsmdy32m644g86vv',
            'amount': 99992296,
            'fingerprint': ['0fb882ff'],
            'derivation_path': ["m/84h/1h/0h/0/2"]}
        ]
    assert psbt_parser.spend_amount == 0  # This is a self-spend; no value being spent, other than the tx fee
    assert psbt_parser.change_amount == 99992296
    assert psbt_parser.destination_addresses == []
    assert psbt_parser.destination_amounts == []



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
        malcolm_psbt_base64 = "cHNidP8BAHECAAAAAQsGinuVfKOSMjCotn0gayHKeAkmFLwxKe7MQPPKRtubAQAAAAD9////Ata1PAAAAAAAFgAU/BI5NUqzoWjyq4tstZzSEWSm9AYALTEBAAAAABYAFMEFrZXlMRv097/TWSoEFDovXO4yhgAAAE8BBDWHzwNqxgvHgAAAACyqFS7//hT3CzogXiU0/vmfRrc+pVADQOZk6425iJCpA16+JtRTZMQQ+VZDwACEPueMErrOarCcoJzORFlLGW56EAPNCitUAACAAQAAgAAAAIAAAQBxAgAAAAFaod+FKqUT6rHnR/PdokVkhnnUUXKpcu7XqrWKXEmqcwAAAAAA/f///wLp6ocEAAAAABYAFA0rwdnbS4A+frYVyJyBBLmiajt5ivVtAQAAAAAWABQK/RwHdGhn2DwbNjWOwp4Keh+cd4UAAAABAR+K9W0BAAAAABYAFAr9HAd0aGfYPBs2NY7Cngp6H5x3AQMEAQAAACIGA6qEQN0MJ/0rCTvtEgWEz+wigtuulY1Y0La2dcFxyaFwGAPNCitUAACAAQAAgAAAAIAAAAAAAQAAAAAiAgLBF0hsiMHXz+SCFBfLZC1gbHfQMHvvkSD+HJqd03MZThgDzQorVAAAgAEAAIAAAACAAQAAAAEAAAAAAA=="
        malcolm_psbt: PSBT = PSBT.parse(a2b_base64(malcolm_psbt_base64))
        malcolm_utxo_value = malcolm_psbt.inputs[0].utxo.value
        malcolm_payment = malcolm_psbt.outputs[1].value

        assert malcolm_utxo_value == 23_983_498
        assert malcolm_payment == 20_000_000
        assert malcolm_psbt.fee() == 4788

        # The receiver's initial psbt is an internal cycle spending her own utxo back to the same receive address as above
        # Additional 8,793,478 sats in the receiver's input.
        zoe_psbt_base64 = "cHNidP8BAFICAAAAAbonjf9fK0qIC760x/Fz276M36J6qr9NqRInpWhJaQF5AQAAAAD9////ARgthgAAAAAAFgAUwQWtleUxG/T3v9NZKgQUOi9c7jKFAAAATwEENYfPA5nI5EuAAAAA4tuMo0iIndBkgQwRyrAsvFfNCn9R180d3N/G1wF+zU8CCffY6y+wLZlHB10lzX1VdNadivJm0ekpnRp9bHeeZkkQD4iQRFQAAIABAACAAAAAgAABAHECAAAAAfJHWB4qFO/vatbVFJF8F3HM7YnWzXF/WubersJnXYUvAQAAAAD9////AuyybwUAAAAAFgAUjnqTNYlTwtB7muOu7nCmTFwGPheGLYYAAAAAABYAFLgTmiZV8MyxgCCT8QNSPqZrWCC1hAAAAAEBH4YthgAAAAAAFgAUuBOaJlXwzLGAIJPxA1I+pmtYILUBAwQBAAAAIgYDXeNmpbMSYfAf77tgst0Cpv3o0EAWxZzSL58bYzs4bEIYD4iQRFQAAIABAACAAAAAgAAAAAABAAAAACICA/ABKpngw9LSn1ak7pntsblOKhitevphw85ksST8aQCAGA+IkERUAACAAQAAgAAAAIAAAAAAAgAAAAA="
        zoe_psbt: PSBT = PSBT.parse(a2b_base64(zoe_psbt_base64))
        zoe_utxo_value = zoe_psbt.inputs[0].utxo.value

        assert zoe_utxo_value == 8_793_478

        # Initially the respective psbts are not cooperative
        malcolm_psbt_parser = PSBTParser(malcolm_psbt, self.malcolm_seed)
        zoe_psbt_parser = PSBTParser(zoe_psbt, self.zoe_seed)
        assert malcolm_psbt_parser.is_cooperative_spend is False
        assert zoe_psbt_parser.is_cooperative_spend is False

        # Add the receiver's input to the sender's version of the payjoin tx
        pj_malcolm_psbt = deepcopy(malcolm_psbt)
        pj_malcolm_psbt.inputs.append(deepcopy(zoe_psbt.inputs[0]))

        # Credit the receiver's total amount to be received
        pj_malcolm_psbt.outputs[1].value = malcolm_payment + zoe_utxo_value

        # Make the matching tx changes on Zoe's psbt
        pj_zoe_psbt = deepcopy(zoe_psbt)

        # Add Malcolm's input
        pj_zoe_psbt.inputs.clear()
        pj_zoe_psbt.inputs.append(deepcopy(malcolm_psbt.inputs[0]))
        pj_zoe_psbt.inputs.append(deepcopy(zoe_psbt.inputs[0]))

        # Add Malcolm's change output
        pj_zoe_psbt.outputs.clear()
        pj_zoe_psbt.outputs.append(deepcopy(malcolm_psbt.outputs[0]))
        pj_zoe_psbt.outputs.append(deepcopy(zoe_psbt.outputs[0]))

        # Credit Zoe's output to the total amount to be received
        pj_zoe_psbt.outputs[1].value = malcolm_payment + zoe_utxo_value

        # Standardize on Malcolm's psbt's locktime so we get the same txid
        pj_zoe_psbt.locktime = pj_malcolm_psbt.locktime

        pj_malcolm_psbt.inputs[1].bip32_derivations = OrderedDict()  # sender typically won't know these details about the receiver's input
        pj_zoe_psbt.inputs[0].bip32_derivations = OrderedDict()  # recipient typically won't know these details about the sender's input
        pj_zoe_psbt.outputs[0].bip32_derivations = OrderedDict() # recipient typically won't know these details about the sender's change output

        assert pj_malcolm_psbt.fee() == pj_zoe_psbt.fee()
        assert pj_malcolm_psbt.outputs[0].value == pj_zoe_psbt.outputs[0].value
        assert pj_malcolm_psbt.outputs[1].value == pj_zoe_psbt.outputs[1].value
        assert len(pj_malcolm_psbt.inputs) == len(pj_zoe_psbt.inputs)
        assert len(pj_malcolm_psbt.outputs) == len(pj_zoe_psbt.outputs)

        assert pj_malcolm_psbt.tx.txid() == pj_zoe_psbt.tx.txid()

        print(f"\nMalcolm's PSBT:\n{pj_malcolm_psbt}\n")
        print(f"Zoe's PSBT:\n{pj_zoe_psbt}\n")

        malcolm_psbt_parser = PSBTParser(pj_malcolm_psbt, self.malcolm_seed)
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
        assert pj_malcolm_psbt.sign_with(bip32.HDKey.from_seed(self.malcolm_seed.seed_bytes)) == 1
        assert pj_zoe_psbt.sign_with(bip32.HDKey.from_seed(self.zoe_seed.seed_bytes)) == 1


    def test_coinjoin_remix(self):
        # Malcolm's 1 input will get coinjoined to 3 equal-size outputs + change + the entire fee
        malcolm_psbt_base64 = "cHNidP8BAK8CAAAAAQsGinuVfKOSMjCotn0gayHKeAkmFLwxKe7MQPPKRtubAAAAAAD9////BLvyvQIAAAAAFgAU/BI5NUqzoWjyq4tstZzSEWSm9AaAlpgAAAAAABYAFMUzbape1rIuKePnFNqTRvu2pdtogJaYAAAAAAAWABQ8t/Nqcumn5ze6hBz98KVlpXpiuYCWmAAAAAAAFgAUWq0V0RzpDydc6hioUyKa1CIvz/6HAAAATwEENYfPA2rGC8eAAAAALKoVLv/+FPcLOiBeJTT++Z9Gtz6lUANA5mTrjbmIkKkDXr4m1FNkxBD5VkPAAIQ+54wSus5qsJygnM5EWUsZbnoQA80KK1QAAIABAACAAAAAgAABAHECAAAAAVqh34UqpRPqsedH892iRWSGedRRcqly7teqtYpcSapzAAAAAAD9////AunqhwQAAAAAFgAUDSvB2dtLgD5+thXInIEEuaJqO3mK9W0BAAAAABYAFAr9HAd0aGfYPBs2NY7Cngp6H5x3hQAAAAEBH+nqhwQAAAAAFgAUDSvB2dtLgD5+thXInIEEuaJqO3kBAwQBAAAAIgYDpfEcvMm8NiPKitIUlmgnNWEGyPope1xPrU+Ob8MmLooYA80KK1QAAIABAACAAAAAgAEAAAAAAAAAACICAsEXSGyIwdfP5IIUF8tkLWBsd9Awe++RIP4cmp3TcxlOGAPNCitUAACAAQAAgAAAAIABAAAAAQAAAAAiAgIClsxEfwpXGwUSFMtsp3ZU+CSxmmWzh3JimzxSrw0b2hgDzQorVAAAgAEAAIAAAACAAAAAAAUAAAAAIgIDR3G1s+sqiJ773qeaExKRLNeMHA7S3p0/u6IiTb3eADUYA80KK1QAAIABAACAAAAAgAAAAAAEAAAAACICA9DaEhiT8c6P52OPNAUVbuexvE/e0x2Km5+/YOHfPfMqGAPNCitUAACAAQAAgAAAAIAAAAAAAwAAAAA="

        # Zoe is getting a free remix round.
        # Her 3 equal-size inputs should pass straight through back to her as 3 equal-size outputs.
        # Zero contribution to the fee.
        zoe_psbt_base64 = "cHNidP8BAOICAAAAA1kLH0GGvUf0B6/veyuvf29MlsiDix7Vdkzv1GkJ+9uWAwAAAAD9////WQsfQYa9R/QHr+97K69/b0yWyIOLHtV2TO/UaQn725YAAAAAAP3///9ZCx9Bhr1H9Aev73srr39vTJbIg4se1XZM79RpCfvblgEAAAAA/f///wOAlpgAAAAAABYAFHx5pQPycxhKf7dcZt9PUM8pChiUgJaYAAAAAAAWABQbz3GDEIv67ZaEA73vZnyytiZNfE2VmAAAAAAAFgAU5mmZUOmhcb8RJp1+0acZ3zTY2fqHAAAATwEENYfPA5nI5EuAAAAA4tuMo0iIndBkgQwRyrAsvFfNCn9R180d3N/G1wF+zU8CCffY6y+wLZlHB10lzX1VdNadivJm0ekpnRp9bHeeZkkQD4iQRFQAAIABAACAAAAAgAABAK8CAAAAAbonjf9fK0qIC760x/Fz276M36J6qr9NqRInpWhJaQF5AAAAAAD9////BICWmAAAAAAAFgAUqlWYMkRXruqo96aWz1DwubPbzfeAlpgAAAAAABYAFIDVYgQDfTCE9u0sAR6rtkSExqECoe6lAwAAAAAWABTN3q8RUz/MLa090ZT2y6jT8vCmxYCWmAAAAAAAFgAU4g39zwlKfNZOMSvLuznNj4l0cP+GAAAAAQEfgJaYAAAAAAAWABTiDf3PCUp81k4xK8u7Oc2PiXRw/wEDBAEAAAAiBgJVufM0kuWfa0fghzpmDTXVYkJ+7fgU68TAkijeBtrhSBgPiJBEVAAAgAEAAIAAAACAAAAAAAMAAAAAAQCvAgAAAAG6J43/XytKiAu+tMfxc9u+jN+ieqq/TakSJ6VoSWkBeQAAAAAA/f///wSAlpgAAAAAABYAFKpVmDJEV67qqPemls9Q8Lmz2833gJaYAAAAAAAWABSA1WIEA30whPbtLAEeq7ZEhMahAqHupQMAAAAAFgAUzd6vEVM/zC2tPdGU9suo0/LwpsWAlpgAAAAAABYAFOIN/c8JSnzWTjEry7s5zY+JdHD/hgAAAAEBH4CWmAAAAAAAFgAUqlWYMkRXruqo96aWz1DwubPbzfcBAwQBAAAAIgYDbB5b3qRPgnP34RTXyFpfZBRCEknHxog+QP+sa/Hbb+gYD4iQRFQAAIABAACAAAAAgAAAAAAEAAAAAAEArwIAAAABuieN/18rSogLvrTH8XPbvozfonqqv02pEielaElpAXkAAAAAAP3///8EgJaYAAAAAAAWABSqVZgyRFeu6qj3ppbPUPC5s9vN94CWmAAAAAAAFgAUgNViBAN9MIT27SwBHqu2RITGoQKh7qUDAAAAABYAFM3erxFTP8wtrT3RlPbLqNPy8KbFgJaYAAAAAAAWABTiDf3PCUp81k4xK8u7Oc2PiXRw/4YAAAABAR+AlpgAAAAAABYAFIDVYgQDfTCE9u0sAR6rtkSExqECAQMEAQAAACIGAmUPW6QftT9y2kOfeeTF44q7Nc1DOLlSiUjnolIn53KdGA+IkERUAACAAQAAgAAAAIAAAAAABQAAAAAiAgKkWmbLPBO+19QtskRAj8m7QQxMrQ+lqrHZWayUs4t/JBgPiJBEVAAAgAEAAIAAAACAAAAAAAcAAAAAIgIDHkqzZv1F3Un83ro7YS8FmUOBESenrQm3a1VryPF3JdoYD4iQRFQAAIABAACAAAAAgAAAAAAGAAAAACICAzmJrvfJwSZdu9Me26l/2pyTIP20+VmGjWEoWmOWiKRGGA+IkERUAACAAQAAgAAAAIAAAAAACAAAAAA="

        malcolm_psbt: PSBT = PSBT.parse(a2b_base64(malcolm_psbt_base64))
        assert len(malcolm_psbt.inputs) == 1
        assert len(malcolm_psbt.outputs) == 4
        assert malcolm_psbt.outputs[1].value == 10_000_000
        assert malcolm_psbt.outputs[2].value == 10_000_000
        assert malcolm_psbt.outputs[3].value == 10_000_000
        malcolm_input_value = sum([inp.utxo.value for inp in malcolm_psbt.inputs])
        malcolm_change_value = malcolm_psbt.outputs[0].value
        assert malcolm_input_value == 3 * 10_000_000 + malcolm_psbt.fee() + malcolm_change_value

        zoe_psbt: PSBT = PSBT.parse(a2b_base64(zoe_psbt_base64))

        # Have to manually zero out Zoe's fee component
        zoe_psbt.outputs[2].value = 10_000_000
        assert zoe_psbt.fee() == 0
        assert len(zoe_psbt.inputs) == 3
        assert len(zoe_psbt.outputs) == 3
        assert zoe_psbt.outputs[0].value == 10_000_000
        assert zoe_psbt.outputs[1].value == 10_000_000
        assert zoe_psbt.outputs[2].value == 10_000_000
        assert sum([inp.utxo.value for inp in zoe_psbt.inputs]) == 3 * 10_000_000

        # Now merge the two txs into an initial coinjoin tx
        initial_coinjoin_psbt = deepcopy(malcolm_psbt)
        initial_coinjoin_psbt.inputs.extend(zoe_psbt.inputs)
        initial_coinjoin_psbt.outputs.extend(zoe_psbt.outputs)

        assert len(initial_coinjoin_psbt.inputs) == 4
        assert len(initial_coinjoin_psbt.outputs) == 7

        # Malcolm's version won't know any of Zoe's bip32 derivation details
        malcolm_coinjoin_psbt = deepcopy(initial_coinjoin_psbt)
        for inp in malcolm_coinjoin_psbt.inputs[len(malcolm_psbt.inputs):]:
            # Wipe Zoe's inputs
            inp.bip32_derivations = OrderedDict()
        for out in malcolm_coinjoin_psbt.outputs[len(malcolm_psbt.outputs):]:
            # Wipe Zoe's outputs
            out.bip32_derivations = OrderedDict()
        
        zoe_coinjoin_psbt = deepcopy(zoe_psbt)
        zoe_coinjoin_psbt.inputs.clear()
        zoe_coinjoin_psbt.inputs.extend(malcolm_psbt.inputs)
        zoe_coinjoin_psbt.inputs.extend(zoe_psbt.inputs)

        zoe_coinjoin_psbt.outputs.clear()
        zoe_coinjoin_psbt.outputs.extend(malcolm_psbt.outputs)
        zoe_coinjoin_psbt.outputs.extend(zoe_psbt.outputs)

        for inp in zoe_coinjoin_psbt.inputs[:len(malcolm_psbt.inputs)]:
            # Wipe Malcolm's inputs
            inp.bip32_derivations = OrderedDict()
        for out in zoe_coinjoin_psbt.outputs[:len(malcolm_psbt.outputs)]:
            # Wipe Malcolm's outputs
            out.bip32_derivations = OrderedDict()

        # Standardize on Malcolm's psbt's locktime so we get the same txid
        zoe_coinjoin_psbt.locktime = malcolm_coinjoin_psbt.locktime

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
        assert malcolm_psbt_parser.change_amount == 3 * 10_000_000 + malcolm_change_value
        assert malcolm_psbt_parser.num_destinations == len(zoe_psbt.outputs)
        assert malcolm_psbt_parser.spend_amount == 3 * 10_000_000

        # Verify Zoe's perspective of his inputs vs external inputs
        zoe_psbt_parser = PSBTParser(zoe_coinjoin_psbt, self.zoe_seed)
        assert zoe_psbt_parser.num_inputs == len(zoe_psbt.inputs)
        assert zoe_psbt_parser.num_external_inputs == len(malcolm_psbt.inputs)
        assert zoe_psbt_parser.num_inputs + zoe_psbt_parser.num_external_inputs == len(initial_coinjoin_psbt.inputs)

        # Verify Zoe's perspective of his outputs (his change and receive addrs are
        # both called "change" in current PSBTParser attr) vs external recipients.
        assert zoe_psbt_parser.num_change_outputs == len(zoe_psbt.outputs)
        assert zoe_psbt_parser.change_amount == 3 * 10_000_000
        assert zoe_psbt_parser.num_destinations == len(malcolm_psbt.outputs)
        assert zoe_psbt_parser.spend_amount == 3 * 10_000_000 + malcolm_change_value

        # Verify that each party can sign
        assert malcolm_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.malcolm_seed.seed_bytes)) == 1
        assert zoe_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.zoe_seed.seed_bytes)) == 3


    def test_coinjoin_shared_fee(self):
        # 2 of Malcolm's inputs; change + 3 equal-size coinjoin outputs
        malcolm_psbt_base64 = "cHNidP8BANgCAAAAArul4tS+fuRK5C5k1wgmK6EswycT4rSZLcrgIkJR3ZLjAQAAAAD9////u6Xi1L5+5ErkLmTXCCYroSzDJxPitJktyuAiQlHdkuMAAAAAAP3///8EQFYPAAAAAAAWABTSLrB1Gw/AzF1Mnt6FyovqCvewzkB4fQEAAAAAFgAUPLfzanLpp+c3uoQc/fClZaV6YrlAeH0BAAAAABYAFMUzbape1rIuKePnFNqTRvu2pdtoQHh9AQAAAAAWABQbGIbPuDt1+72IozMVnVL6aLOxx4gAAABPAQQ1h88DasYLx4AAAAAsqhUu//4U9ws6IF4lNP75n0a3PqVQA0DmZOuNuYiQqQNevibUU2TEEPlWQ8AAhD7njBK6zmqwnKCczkRZSxluehADzQorVAAAgAEAAIAAAACAAAEAcQIAAAABCwaKe5V8o5IyMKi2fSBrIcp4CSYUvDEp7sxA88pG25sAAAAAAP3///8Cdm83AwAAAAAWABT8Ejk1SrOhaPKri2y1nNIRZKb0Bk9wUAEAAAAAFgAUWq0V0RzpDydc6hioUyKa1CIvz/6HAAAAAQEfT3BQAQAAAAAWABRarRXRHOkPJ1zqGKhTIprUIi/P/gEDBAEAAAAiBgPQ2hIYk/HOj+djjzQFFW7nsbxP3tMdipufv2Dh3z3zKhgDzQorVAAAgAEAAIAAAACAAAAAAAMAAAAAAQBxAgAAAAELBop7lXyjkjIwqLZ9IGshyngJJhS8MSnuzEDzykbbmwAAAAAA/f///wJ2bzcDAAAAABYAFPwSOTVKs6Fo8quLbLWc0hFkpvQGT3BQAQAAAAAWABRarRXRHOkPJ1zqGKhTIprUIi/P/ocAAAABAR92bzcDAAAAABYAFPwSOTVKs6Fo8quLbLWc0hFkpvQGAQMEAQAAACIGAsEXSGyIwdfP5IIUF8tkLWBsd9Awe++RIP4cmp3TcxlOGAPNCitUAACAAQAAgAAAAIABAAAAAQAAAAAiAgN3YOT8DuZ8ClbwGDstYqEAcnMR31jqZerjuIyoxv+ekBgDzQorVAAAgAEAAIAAAACAAQAAAAIAAAAAIgIDR3G1s+sqiJ773qeaExKRLNeMHA7S3p0/u6IiTb3eADUYA80KK1QAAIABAACAAAAAgAAAAAAEAAAAACICAgKWzER/ClcbBRIUy2yndlT4JLGaZbOHcmKbPFKvDRvaGAPNCitUAACAAQAAgAAAAIAAAAAABQAAAAAiAgN0WjuVgDW0dYoQ1U2zXEm5HpUP0DHg9cavCrKjjMVZjxgDzQorVAAAgAEAAIAAAACAAAAAAAYAAAAA"

        # 1 of Zoe's inputs; change + 2 equal-size coinjoin outputs
        zoe_psbt_base64 = "cHNidP8BAJACAAAAAVkLH0GGvUf0B6/veyuvf29MlsiDix7Vdkzv1GkJ+9uWAgAAAAD9////A1jpqgAAAAAAFgAUIb3LqEYyx8uc8OEsn2iJvxf295RAeH0BAAAAABYAFHx5pQPycxhKf7dcZt9PUM8pChiUQHh9AQAAAAAWABTmaZlQ6aFxvxEmnX7RpxnfNNjZ+ogAAABPAQQ1h88DmcjkS4AAAADi24yjSIid0GSBDBHKsCy8V80Kf1HXzR3c38bXAX7NTwIJ99jrL7AtmUcHXSXNfVV01p2K8mbR6SmdGn1sd55mSRAPiJBEVAAAgAEAAIAAAACAAAEArwIAAAABuieN/18rSogLvrTH8XPbvozfonqqv02pEielaElpAXkAAAAAAP3///8EgJaYAAAAAAAWABSqVZgyRFeu6qj3ppbPUPC5s9vN94CWmAAAAAAAFgAUgNViBAN9MIT27SwBHqu2RITGoQKh7qUDAAAAABYAFM3erxFTP8wtrT3RlPbLqNPy8KbFgJaYAAAAAAAWABTiDf3PCUp81k4xK8u7Oc2PiXRw/4YAAAABAR+h7qUDAAAAABYAFM3erxFTP8wtrT3RlPbLqNPy8KbFAQMEAQAAACIGAxC3YX4M/2O9x3P2nRH6LIwU+lIvoSv7ZFHvsVKksPjhGA+IkERUAACAAQAAgAAAAIABAAAAAQAAAAAiAgL9hPuyeOZBhuiRecG7bAi2YIHNYoxWyN5qxjdHtUSq4hgPiJBEVAAAgAEAAIAAAACAAQAAAAIAAAAAIgICpFpmyzwTvtfULbJEQI/Ju0EMTK0Ppaqx2VmslLOLfyQYD4iQRFQAAIABAACAAAAAgAAAAAAHAAAAACICAzmJrvfJwSZdu9Me26l/2pyTIP20+VmGjWEoWmOWiKRGGA+IkERUAACAAQAAgAAAAIAAAAAACAAAAAA="

        equal_size_amount = 25_000_000

        malcolm_psbt: PSBT = PSBT.parse(a2b_base64(malcolm_psbt_base64))
        assert len(malcolm_psbt.inputs) == 2
        assert len(malcolm_psbt.outputs) == 4
        malcolm_input_value = sum([inp.utxo.value for inp in malcolm_psbt.inputs])
        malcolm_change_value = malcolm_psbt.outputs[0].value
        assert malcolm_input_value == (len(malcolm_psbt.outputs) - 1) * equal_size_amount + malcolm_psbt.fee() + malcolm_change_value

        assert malcolm_psbt.outputs[1].value == equal_size_amount
        assert malcolm_psbt.outputs[2].value == equal_size_amount
        assert malcolm_psbt.outputs[3].value == equal_size_amount
        malcolm_fee_value = malcolm_psbt.fee()

        zoe_psbt: PSBT = PSBT.parse(a2b_base64(zoe_psbt_base64))
        assert len(zoe_psbt.inputs) == 1
        assert len(zoe_psbt.outputs) == 3
        zoe_input_value = sum([inp.utxo.value for inp in zoe_psbt.inputs])
        zoe_change_value = zoe_psbt.outputs[0].value
        assert zoe_input_value == (len(zoe_psbt.outputs) - 1) * equal_size_amount + zoe_psbt.fee() + zoe_change_value

        assert zoe_psbt.outputs[1].value == equal_size_amount
        assert zoe_psbt.outputs[2].value == equal_size_amount
        zoe_fee_value = zoe_psbt.fee()

        # Now merge the two txs into an initial coinjoin tx
        malcolm_coinjoin_psbt = deepcopy(malcolm_psbt)
        malcolm_coinjoin_psbt.inputs.extend(deepcopy(zoe_psbt.inputs))
        malcolm_coinjoin_psbt.outputs.extend(deepcopy(zoe_psbt.outputs))

        assert len(malcolm_coinjoin_psbt.inputs) == len(malcolm_psbt.inputs) + len(zoe_psbt.inputs)
        assert len(malcolm_coinjoin_psbt.outputs) == len(malcolm_psbt.outputs) + len(zoe_psbt.outputs)

        zoe_coinjoin_psbt = deepcopy(zoe_psbt)
        zoe_coinjoin_psbt.inputs.clear()
        zoe_coinjoin_psbt.inputs.extend(deepcopy(malcolm_psbt.inputs))
        zoe_coinjoin_psbt.inputs.append(deepcopy(zoe_psbt.inputs[0]))
        
        zoe_coinjoin_psbt.outputs.clear()
        zoe_coinjoin_psbt.outputs.extend(deepcopy(malcolm_psbt.outputs))
        zoe_coinjoin_psbt.outputs.extend(deepcopy(zoe_psbt.outputs))

        # Standardize on Malcolm's psbt's locktime so we get the same txid
        zoe_coinjoin_psbt.locktime = malcolm_coinjoin_psbt.locktime

        assert malcolm_coinjoin_psbt.tx.txid() == zoe_coinjoin_psbt.tx.txid()
        assert malcolm_coinjoin_psbt.fee() == malcolm_fee_value + zoe_fee_value

        # Malcolm's version won't know any of Zoe's bip32 derivation details
        # malcolm_coinjoin_psbt = deepcopy(initial_coinjoin_psbt)
        for inp in malcolm_coinjoin_psbt.inputs[len(malcolm_psbt.inputs):]:
            # Wipe Zoe's inputs
            inp.bip32_derivations = OrderedDict()
        for out in malcolm_coinjoin_psbt.outputs[len(malcolm_psbt.outputs):]:
            # Wipe Zoe's outputs
            out.bip32_derivations = OrderedDict()
        
        # zoe_coinjoin_psbt = deepcopy(initial_coinjoin_psbt)
        for inp in zoe_coinjoin_psbt.inputs[:len(malcolm_psbt.inputs)]:
            # Wipe Malcolm's inputs
            inp.bip32_derivations = OrderedDict()
        for out in zoe_coinjoin_psbt.outputs[:len(malcolm_psbt.outputs)]:
            # Wipe Malcolm's outputs
            out.bip32_derivations = OrderedDict()

        print(f"\nMalcolm's coinjoin PSBT: {malcolm_coinjoin_psbt}\n")
        print(f"Zoe's coinjoin PSBT: {zoe_coinjoin_psbt}\n")

        # Verify Malcolm's perspective of his inputs vs external inputs
        malcolm_psbt_parser = PSBTParser(malcolm_coinjoin_psbt, self.malcolm_seed)
        assert malcolm_psbt_parser.num_inputs == len(malcolm_psbt.inputs)
        assert malcolm_psbt_parser.num_external_inputs == len(zoe_psbt.inputs)
        assert malcolm_psbt_parser.num_inputs + malcolm_psbt_parser.num_external_inputs == len(malcolm_psbt.inputs) + len(zoe_psbt.inputs)

        # Verify Malcolm's perspective of his outputs (his change and receive addrs are
        # both called "change" in current PSBTParser attr) vs external recipients.
        assert malcolm_psbt_parser.num_change_outputs == len(malcolm_psbt.outputs)
        assert malcolm_psbt_parser.change_amount == (len(malcolm_psbt.outputs) - 1) * equal_size_amount + malcolm_change_value
        assert malcolm_psbt_parser.num_destinations == len(zoe_psbt.outputs)
        assert malcolm_psbt_parser.spend_amount == (len(zoe_psbt.outputs) - 1) * equal_size_amount + zoe_change_value

        # Verify Zoe's perspective of her inputs vs external inputs
        zoe_psbt_parser = PSBTParser(zoe_coinjoin_psbt, self.zoe_seed)
        assert zoe_psbt_parser.num_inputs == len(zoe_psbt.inputs)
        assert zoe_psbt_parser.num_external_inputs == len(malcolm_psbt.inputs)
        assert zoe_psbt_parser.num_inputs + zoe_psbt_parser.num_external_inputs == len(malcolm_psbt.inputs) + len(zoe_psbt.inputs)

        # Verify Zoe's perspective of her outputs (her change and receive addrs are
        # both called "change" in current PSBTParser attr) vs external recipients.
        assert zoe_psbt_parser.num_change_outputs == len(zoe_psbt.outputs)
        assert zoe_psbt_parser.change_amount == (len(zoe_psbt.outputs) - 1) * equal_size_amount + zoe_change_value
        assert zoe_psbt_parser.num_destinations == len(malcolm_psbt.outputs)
        assert zoe_psbt_parser.spend_amount == (len(malcolm_psbt.outputs) - 1) * equal_size_amount + malcolm_change_value

        # Verify that each party can sign
        assert malcolm_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.malcolm_seed.seed_bytes)) == len(malcolm_psbt.inputs)
        assert zoe_coinjoin_psbt.sign_with(bip32.HDKey.from_seed(self.zoe_seed.seed_bytes)) == len(zoe_psbt.inputs)


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
