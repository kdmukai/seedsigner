from binascii import a2b_base64
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass

from embit import bip32
from embit.networks import NETWORKS
from embit.psbt import PSBT

from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants

from psbt_testing_util import PSBTTestData, create_output



class TestPSBTParser:
    seed = Seed("model ensure search plunge galaxy firm exclude brain satoshi meadow cable roast".split())

    def test_manually_construct_test_psbts(self):
        psbt = PSBT.parse(a2b_base64(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_1_INPUT))
        psbt.outputs.append(create_output(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_RECEIVE, 250_000))
        psbt.outputs.append(create_output(PSBTTestData.SINGLE_SIG_NATIVE_SEGWIT_CHANGE, 100_000_000 - 250_000 - 5_000))

        assert len(psbt.outputs) == 2
        psbt_parser = PSBTParser(p=psbt, seed=self.seed, network=SettingsConstants.REGTEST)
        assert psbt_parser.num_inputs == 1
        assert psbt_parser.num_external_inputs == 0
        assert psbt_parser.input_amount == 100_000_000
        assert psbt_parser.num_destinations == 1
        assert psbt_parser.num_change_outputs == 1
        assert psbt_parser.spend_amount == 250_000
        assert psbt_parser.change_amount == 100_000_000 - 250_000 - 5_000
        assert psbt_parser.fee_amount == 5_000
        assert psbt_parser.input_amount + psbt_parser.external_input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount




    @dataclass
    class SamplePSBT:
        description: str
        psbt_base64: str

        num_inputs: int
        num_external_inputs: int
        input_amount: int
        external_input_amount: int

        num_destinations: int
        num_change_outputs: int
        spend_amount: int
        change_amount: int
        fee_amount: int


        def run_test(self, seed: Seed):
            raw = a2b_base64(self.psbt_base64)
            tx = PSBT.parse(raw)
            psbt_parser = PSBTParser(p=tx, seed=seed, network=SettingsConstants.REGTEST)
            try:
                assert psbt_parser.num_inputs == self.num_inputs
                assert psbt_parser.num_external_inputs == self.num_external_inputs
                assert psbt_parser.input_amount == self.input_amount
                assert psbt_parser.num_destinations == self.num_destinations
                assert psbt_parser.num_change_outputs == self.num_change_outputs
                assert psbt_parser.spend_amount == self.spend_amount
                assert psbt_parser.change_amount == self.change_amount
                assert psbt_parser.fee_amount == self.fee_amount
                assert psbt_parser.input_amount + psbt_parser.external_input_amount == psbt_parser.spend_amount + psbt_parser.change_amount + psbt_parser.fee_amount
            except AssertionError as e:
                print(f"Failed: {self.description}")
                raise e


    def test_singlesig_native_segwit(self):
        samples = [
            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to native segwit (P2WPKH), 1 recipient + change",
                psbt_base64="cHNidP8BAHECAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////ApDQAwAAAAAAFgAUZzx7c8fgIzjkDdnWHtwHQARoCZPo/PEFAAAAABYAFKzBNAcJ6be6vv+SGAbwVwxlK9BYbwAAAE8BBDWHzwNXmUmVgAAAANRFa7R5gYD84Wbha3d1QnjgfYPOBw87on6cXS32WoyqAsPFtPxB7PRTdbujUnBPUVDh9YUBtwrl4nc0OcRNGvIyEA+4gv9UAACAAQAAgAAAAIAAAQCIAgAAAAHVNy3baqUJbmJM5kN9epW7oIqXB1O2s+Fs8julxND8ZQEAAAAXFgAUI+kCxhZQ0mdMSs6OSgKGdDKUanr9////As0uGh4BAAAAFgAUjiVTkQBkiXD8ylfqveCHXOprMQ4A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMObgAAAAEBHwDh9QUAAAAAFgAUWIy6PsONzU/ua84Dwjbsu/ZWYw4BAwQBAAAAIgYC9duqeSZYNc80SQfOc/SXZUUWqXZamBfjbIPdn18lj/cYD7iC/1QAAIABAACAAAAAgAAAAAADAAAAAAAiAgIsFe/QjIIqYofxtCtsMOzO1H8cVITD59cudoCjBYk9JxgPuIL/VAAAgAEAAIAAAACAAQAAAAAAAAAA",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=1,
                spend_amount=250_000,
                change_amount=99_745_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to nested segwit (P2SH-P2WPKH), 1 recipient + change",
                psbt_base64="cHNidP8BAHICAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////Auj88QUAAAAAFgAUrME0Bwnpt7q+/5IYBvBXDGUr0FiQ0AMAAAAAABepFKibZqx9neTX1dpNrnEGUUc1VkMUh3AAAABPAQQ1h88DV5lJlYAAAADURWu0eYGA/OFm4Wt3dUJ44H2DzgcPO6J+nF0t9lqMqgLDxbT8Qez0U3W7o1JwT1FQ4fWFAbcK5eJ3NDnETRryMhAPuIL/VAAAgAEAAIAAAACAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAiAgIsFe/QjIIqYofxtCtsMOzO1H8cVITD59cudoCjBYk9JxgPuIL/VAAAgAEAAIAAAACAAQAAAAAAAAAAAA==",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=1,
                spend_amount=250_000,
                change_amount=99_745_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to native segwit multisig (P2WSH), 1 recipient + change",
                psbt_base64="cHNidP8BAH0CAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////ApDQAwAAAAAAIgAgdO97VShcxP5DMHTth+VP/DotLR6J5BERK4hp4o1IDq/o/PEFAAAAABYAFKzBNAcJ6be6vv+SGAbwVwxlK9BYcAAAAE8BBDWHzwNXmUmVgAAAANRFa7R5gYD84Wbha3d1QnjgfYPOBw87on6cXS32WoyqAsPFtPxB7PRTdbujUnBPUVDh9YUBtwrl4nc0OcRNGvIyEA+4gv9UAACAAQAAgAAAAIAAAQCIAgAAAAHVNy3baqUJbmJM5kN9epW7oIqXB1O2s+Fs8julxND8ZQEAAAAXFgAUI+kCxhZQ0mdMSs6OSgKGdDKUanr9////As0uGh4BAAAAFgAUjiVTkQBkiXD8ylfqveCHXOprMQ4A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMObgAAAAEBHwDh9QUAAAAAFgAUWIy6PsONzU/ua84Dwjbsu/ZWYw4BAwQBAAAAIgYC9duqeSZYNc80SQfOc/SXZUUWqXZamBfjbIPdn18lj/cYD7iC/1QAAIABAACAAAAAgAAAAAADAAAAAAAiAgIsFe/QjIIqYofxtCtsMOzO1H8cVITD59cudoCjBYk9JxgPuIL/VAAAgAEAAIAAAACAAQAAAAAAAAAA",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=1,
                spend_amount=250_000,
                change_amount=99_745_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to nested segwit multisig (P2SH-P2WSH), 1 recipient + change",
                psbt_base64="cHNidP8BAHICAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////ApDQAwAAAAAAF6kUqJtmrH2d5NfV2k2ucQZRRzVWQxSH6PzxBQAAAAAWABSswTQHCem3ur7/khgG8FcMZSvQWHAAAABPAQQ1h88DV5lJlYAAAADURWu0eYGA/OFm4Wt3dUJ44H2DzgcPO6J+nF0t9lqMqgLDxbT8Qez0U3W7o1JwT1FQ4fWFAbcK5eJ3NDnETRryMhAPuIL/VAAAgAEAAIAAAACAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAAIgICLBXv0IyCKmKH8bQrbDDsztR/HFSEw+fXLnaAowWJPScYD7iC/1QAAIABAACAAAAAgAEAAAAAAAAAAA==",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=1,
                spend_amount=250_000,
                change_amount=99_745_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to P2WPKH, 2 recipients + change",
                psbt_base64="cHNidP8BAJACAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////AzBXBQAAAAAAFgAUXNvtaeJYavxHqwlZRVNNJAqQcZ24pewFAAAAABYAFKzBNAcJ6be6vv+SGAbwVwxlK9BYkNADAAAAAAAWABRnPHtzx+AjOOQN2dYe3AdABGgJk28AAABPAQQ1h88DV5lJlYAAAADURWu0eYGA/OFm4Wt3dUJ44H2DzgcPO6J+nF0t9lqMqgLDxbT8Qez0U3W7o1JwT1FQ4fWFAbcK5eJ3NDnETRryMhAPuIL/VAAAgAEAAIAAAACAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAAIgICLBXv0IyCKmKH8bQrbDDsztR/HFSEw+fXLnaAowWJPScYD7iC/1QAAIABAACAAAAAgAEAAAAAAAAAAAA=",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=2,  # 2 outputs
                num_change_outputs=1,
                spend_amount=250_000 + 350_000,
                change_amount=99_395_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to P2WPKH, full spend to one recipient",
                psbt_base64="cHNidP8BAFICAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////AXjN9QUAAAAAFgAUZzx7c8fgIzjkDdnWHtwHQARoCZNvAAAATwEENYfPA1eZSZWAAAAA1EVrtHmBgPzhZuFrd3VCeOB9g84HDzuifpxdLfZajKoCw8W0/EHs9FN1u6NScE9RUOH1hQG3CuXidzQ5xE0a8jIQD7iC/1QAAIABAACAAAAAgAABAIgCAAAAAdU3LdtqpQluYkzmQ316lbugipcHU7az4WzyO6XE0PxlAQAAABcWABQj6QLGFlDSZ0xKzo5KAoZ0MpRqev3///8CzS4aHgEAAAAWABSOJVORAGSJcPzKV+q94Idc6msxDgDh9QUAAAAAFgAUWIy6PsONzU/ua84Dwjbsu/ZWYw5uAAAAAQEfAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDgEDBAEAAAAiBgL126p5Jlg1zzRJB85z9JdlRRapdlqYF+Nsg92fXyWP9xgPuIL/VAAAgAEAAIAAAACAAAAAAAMAAAAAAA==",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=0,
                spend_amount=99_995_000,
                change_amount=0,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to P2WPKH, internal cycle back to own wallet",
                psbt_base64="cHNidP8BAFICAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////AXjN9QUAAAAAFgAU8cfhU9/rh73NVOJO2Na0fFhKSARvAAAATwEENYfPA1eZSZWAAAAA1EVrtHmBgPzhZuFrd3VCeOB9g84HDzuifpxdLfZajKoCw8W0/EHs9FN1u6NScE9RUOH1hQG3CuXidzQ5xE0a8jIQD7iC/1QAAIABAACAAAAAgAABAIgCAAAAAdU3LdtqpQluYkzmQ316lbugipcHU7az4WzyO6XE0PxlAQAAABcWABQj6QLGFlDSZ0xKzo5KAoZ0MpRqev3///8CzS4aHgEAAAAWABSOJVORAGSJcPzKV+q94Idc6msxDgDh9QUAAAAAFgAUWIy6PsONzU/ua84Dwjbsu/ZWYw5uAAAAAQEfAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDgEDBAEAAAAiBgL126p5Jlg1zzRJB85z9JdlRRapdlqYF+Nsg92fXyWP9xgPuIL/VAAAgAEAAIAAAACAAAAAAAMAAAAAIgIC6lfZrb26+ddGMbyOUAS8K5f8BqdwOMR+/jo3fwtCy9AYD7iC/1QAAIABAACAAAAAgAAAAAAEAAAAAA==",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=0,
                num_change_outputs=1,
                spend_amount=0,
                change_amount=99_995_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to P2WPKH, 1 recipient + internal cycle back to own wallet + change",
                psbt_base64="cHNidP8BAJACAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////A0BLTAAAAAAAFgAU8cfhU9/rh73NVOJO2Na0fFhKSASosaUFAAAAABYAFKzBNAcJ6be6vv+SGAbwVwxlK9BYkNADAAAAAAAWABRnPHtzx+AjOOQN2dYe3AdABGgJk28AAABPAQQ1h88DV5lJlYAAAADURWu0eYGA/OFm4Wt3dUJ44H2DzgcPO6J+nF0t9lqMqgLDxbT8Qez0U3W7o1JwT1FQ4fWFAbcK5eJ3NDnETRryMhAPuIL/VAAAgAEAAIAAAACAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAiAgLqV9mtvbr510YxvI5QBLwrl/wGp3A4xH7+Ojd/C0LL0BgPuIL/VAAAgAEAAIAAAACAAAAAAAQAAAAAIgICLBXv0IyCKmKH8bQrbDDsztR/HFSEw+fXLnaAowWJPScYD7iC/1QAAIABAACAAAAAgAEAAAAAAAAAAAA=",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=2,
                spend_amount=250_000,
                change_amount=5_000_000 + 94_745_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig native segwit (P2WPKH) to P2WPKH, 2 inputs, 1 recipient + change",
                psbt_base64="cHNidP8BAJoCAAAAAsJ89R3J4RM3F/2mTME/ag5R+BIhKutmLi6PRugo3Y95AAAAAAD9////ThP/Rpf2aY1kfIqH7QAdhj4S10nGd0xGtrSCfhA8Jl0BAAAAAP3///8CgNHwCAAAAAAWABRnPHtzx+AjOOQN2dYe3AdABGgJk/jc+gIAAAAAFgAUrME0Bwnpt7q+/5IYBvBXDGUr0FhwAAAATwEENYfPA1eZSZWAAAAA1EVrtHmBgPzhZuFrd3VCeOB9g84HDzuifpxdLfZajKoCw8W0/EHs9FN1u6NScE9RUOH1hQG3CuXidzQ5xE0a8jIQD7iC/1QAAIABAACAAAAAgAABAHECAAAAAfFB2o8nAMMw9ZFG4EHYvsMle9RkAw0xCXoVr12ZRrRqAQAAAAD9////AgDh9QUAAAAAFgAUkafX/Pco8lEPjPg2Vyd2MC0Cv8w/ijgMAQAAABYAFLHv1XF6upFAIyRP61rF77j3NegLbwAAAAEBHwDh9QUAAAAAFgAUkafX/Pco8lEPjPg2Vyd2MC0Cv8wBAwQBAAAAIgYCKALMbvmaFrAPq1M4ikZhDSVahyZhdJAi3ScfXi9k/JsYD7iC/1QAAIABAACAAAAAgAAAAAAFAAAAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAAIgICLBXv0IyCKmKH8bQrbDDsztR/HFSEw+fXLnaAowWJPScYD7iC/1QAAIABAACAAAAAgAEAAAAAAAAAAA==",
                num_inputs=2,
                num_external_inputs=0,
                input_amount=200_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=1,
                spend_amount=150_000_000,
                change_amount=49_995_000,
                fee_amount=5_000,
            ),
        ]

        seed = Seed(self.mnemonic)
        for sample in samples:
            sample.run_test(seed)


    def test_singlesig_nested_segwit(self):
        samples = [
            TestPSBTParser.SamplePSBT(
                description="Single sig P2SH-P2WPKH to P2WPKH, 1 recipient + change",
                psbt_base64="cHNidP8BAHECAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////ApDQAwAAAAAAFgAUZzx7c8fgIzjkDdnWHtwHQARoCZPo/PEFAAAAABYAFKzBNAcJ6be6vv+SGAbwVwxlK9BYbwAAAE8BBDWHzwNXmUmVgAAAANRFa7R5gYD84Wbha3d1QnjgfYPOBw87on6cXS32WoyqAsPFtPxB7PRTdbujUnBPUVDh9YUBtwrl4nc0OcRNGvIyEA+4gv9UAACAAQAAgAAAAIAAAQCIAgAAAAHVNy3baqUJbmJM5kN9epW7oIqXB1O2s+Fs8julxND8ZQEAAAAXFgAUI+kCxhZQ0mdMSs6OSgKGdDKUanr9////As0uGh4BAAAAFgAUjiVTkQBkiXD8ylfqveCHXOprMQ4A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMObgAAAAEBHwDh9QUAAAAAFgAUWIy6PsONzU/ua84Dwjbsu/ZWYw4BAwQBAAAAIgYC9duqeSZYNc80SQfOc/SXZUUWqXZamBfjbIPdn18lj/cYD7iC/1QAAIABAACAAAAAgAAAAAADAAAAAAAiAgIsFe/QjIIqYofxtCtsMOzO1H8cVITD59cudoCjBYk9JxgPuIL/VAAAgAEAAIAAAACAAQAAAAAAAAAA",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=1,
                spend_amount=250_000,
                change_amount=99_745_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig P2SH-P2WPKH to P2WPKH, 2 recipients + change",
                psbt_base64="cHNidP8BAJACAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////AzBXBQAAAAAAFgAUXNvtaeJYavxHqwlZRVNNJAqQcZ24pewFAAAAABYAFKzBNAcJ6be6vv+SGAbwVwxlK9BYkNADAAAAAAAWABRnPHtzx+AjOOQN2dYe3AdABGgJk28AAABPAQQ1h88DV5lJlYAAAADURWu0eYGA/OFm4Wt3dUJ44H2DzgcPO6J+nF0t9lqMqgLDxbT8Qez0U3W7o1JwT1FQ4fWFAbcK5eJ3NDnETRryMhAPuIL/VAAAgAEAAIAAAACAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAAIgICLBXv0IyCKmKH8bQrbDDsztR/HFSEw+fXLnaAowWJPScYD7iC/1QAAIABAACAAAAAgAEAAAAAAAAAAAA=",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=2,  # 2 outputs
                num_change_outputs=1,
                spend_amount=250_000 + 350_000,
                change_amount=99_395_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig P2SH-P2WPKH to P2WPKH, full spend to one recipient",
                psbt_base64="cHNidP8BAFICAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////AXjN9QUAAAAAFgAUZzx7c8fgIzjkDdnWHtwHQARoCZNvAAAATwEENYfPA1eZSZWAAAAA1EVrtHmBgPzhZuFrd3VCeOB9g84HDzuifpxdLfZajKoCw8W0/EHs9FN1u6NScE9RUOH1hQG3CuXidzQ5xE0a8jIQD7iC/1QAAIABAACAAAAAgAABAIgCAAAAAdU3LdtqpQluYkzmQ316lbugipcHU7az4WzyO6XE0PxlAQAAABcWABQj6QLGFlDSZ0xKzo5KAoZ0MpRqev3///8CzS4aHgEAAAAWABSOJVORAGSJcPzKV+q94Idc6msxDgDh9QUAAAAAFgAUWIy6PsONzU/ua84Dwjbsu/ZWYw5uAAAAAQEfAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDgEDBAEAAAAiBgL126p5Jlg1zzRJB85z9JdlRRapdlqYF+Nsg92fXyWP9xgPuIL/VAAAgAEAAIAAAACAAAAAAAMAAAAAAA==",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=0,
                spend_amount=99_995_000,
                change_amount=0,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig P2SH-P2WPKH to P2WPKH, internal cycle back to own wallet",
                psbt_base64="cHNidP8BAFICAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////AXjN9QUAAAAAFgAU8cfhU9/rh73NVOJO2Na0fFhKSARvAAAATwEENYfPA1eZSZWAAAAA1EVrtHmBgPzhZuFrd3VCeOB9g84HDzuifpxdLfZajKoCw8W0/EHs9FN1u6NScE9RUOH1hQG3CuXidzQ5xE0a8jIQD7iC/1QAAIABAACAAAAAgAABAIgCAAAAAdU3LdtqpQluYkzmQ316lbugipcHU7az4WzyO6XE0PxlAQAAABcWABQj6QLGFlDSZ0xKzo5KAoZ0MpRqev3///8CzS4aHgEAAAAWABSOJVORAGSJcPzKV+q94Idc6msxDgDh9QUAAAAAFgAUWIy6PsONzU/ua84Dwjbsu/ZWYw5uAAAAAQEfAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDgEDBAEAAAAiBgL126p5Jlg1zzRJB85z9JdlRRapdlqYF+Nsg92fXyWP9xgPuIL/VAAAgAEAAIAAAACAAAAAAAMAAAAAIgIC6lfZrb26+ddGMbyOUAS8K5f8BqdwOMR+/jo3fwtCy9AYD7iC/1QAAIABAACAAAAAgAAAAAAEAAAAAA==",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=0,
                num_change_outputs=1,
                spend_amount=0,
                change_amount=99_995_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig P2SH-P2WPKH to P2WPKH, 1 recipient + internal cycle back to own wallet + change",
                psbt_base64="cHNidP8BAJACAAAAAU4T/0aX9mmNZHyKh+0AHYY+EtdJxndMRra0gn4QPCZdAQAAAAD9////A0BLTAAAAAAAFgAU8cfhU9/rh73NVOJO2Na0fFhKSASosaUFAAAAABYAFKzBNAcJ6be6vv+SGAbwVwxlK9BYkNADAAAAAAAWABRnPHtzx+AjOOQN2dYe3AdABGgJk28AAABPAQQ1h88DV5lJlYAAAADURWu0eYGA/OFm4Wt3dUJ44H2DzgcPO6J+nF0t9lqMqgLDxbT8Qez0U3W7o1JwT1FQ4fWFAbcK5eJ3NDnETRryMhAPuIL/VAAAgAEAAIAAAACAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAiAgLqV9mtvbr510YxvI5QBLwrl/wGp3A4xH7+Ojd/C0LL0BgPuIL/VAAAgAEAAIAAAACAAAAAAAQAAAAAIgICLBXv0IyCKmKH8bQrbDDsztR/HFSEw+fXLnaAowWJPScYD7iC/1QAAIABAACAAAAAgAEAAAAAAAAAAAA=",
                num_inputs=1,
                num_external_inputs=0,
                input_amount=100_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=2,
                spend_amount=250_000,
                change_amount=5_000_000 + 94_745_000,
                fee_amount=5_000,
            ),

            TestPSBTParser.SamplePSBT(
                description="Single sig P2SH-P2WPKH to P2WPKH, 2 inputs, 1 recipient + change",
                psbt_base64="cHNidP8BAJoCAAAAAsJ89R3J4RM3F/2mTME/ag5R+BIhKutmLi6PRugo3Y95AAAAAAD9////ThP/Rpf2aY1kfIqH7QAdhj4S10nGd0xGtrSCfhA8Jl0BAAAAAP3///8CgNHwCAAAAAAWABRnPHtzx+AjOOQN2dYe3AdABGgJk/jc+gIAAAAAFgAUrME0Bwnpt7q+/5IYBvBXDGUr0FhwAAAATwEENYfPA1eZSZWAAAAA1EVrtHmBgPzhZuFrd3VCeOB9g84HDzuifpxdLfZajKoCw8W0/EHs9FN1u6NScE9RUOH1hQG3CuXidzQ5xE0a8jIQD7iC/1QAAIABAACAAAAAgAABAHECAAAAAfFB2o8nAMMw9ZFG4EHYvsMle9RkAw0xCXoVr12ZRrRqAQAAAAD9////AgDh9QUAAAAAFgAUkafX/Pco8lEPjPg2Vyd2MC0Cv8w/ijgMAQAAABYAFLHv1XF6upFAIyRP61rF77j3NegLbwAAAAEBHwDh9QUAAAAAFgAUkafX/Pco8lEPjPg2Vyd2MC0Cv8wBAwQBAAAAIgYCKALMbvmaFrAPq1M4ikZhDSVahyZhdJAi3ScfXi9k/JsYD7iC/1QAAIABAACAAAAAgAAAAAAFAAAAAAEAiAIAAAAB1Tct22qlCW5iTOZDfXqVu6CKlwdTtrPhbPI7pcTQ/GUBAAAAFxYAFCPpAsYWUNJnTErOjkoChnQylGp6/f///wLNLhoeAQAAABYAFI4lU5EAZIlw/MpX6r3gh1zqazEOAOH1BQAAAAAWABRYjLo+w43NT+5rzgPCNuy79lZjDm4AAAABAR8A4fUFAAAAABYAFFiMuj7Djc1P7mvOA8I27Lv2VmMOAQMEAQAAACIGAvXbqnkmWDXPNEkHznP0l2VFFql2WpgX42yD3Z9fJY/3GA+4gv9UAACAAQAAgAAAAIAAAAAAAwAAAAAAIgICLBXv0IyCKmKH8bQrbDDsztR/HFSEw+fXLnaAowWJPScYD7iC/1QAAIABAACAAAAAgAEAAAAAAAAAAA==",
                num_inputs=2,
                num_external_inputs=0,
                input_amount=200_000_000,
                external_input_amount=0,
                num_destinations=1,
                num_change_outputs=1,
                spend_amount=150_000_000,
                change_amount=49_995_000,
                fee_amount=5_000,
            ),
        ]

        seed = Seed(self.mnemonic)
        for sample in samples:
            sample.run_test(seed)


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
                'amount': 2871443918,
                'fingerprint': ['394aed14'],
                'derivation_path': ['m/86h/1h/0h/1/1']}
            ]
        assert pp.spend_amount == 319049328
        assert pp.change_amount == 2871443918
        assert pp.destination_addresses == ['bcrt1p6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek']
        assert pp.destination_amounts == [319049328]



    def test_has_external_inputs(self):
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
        malcolm_seed = Seed("better gown govern speak spawn vendor exercise item uncle odor sound cat".split())
        zoe_seed = Seed("sign sword lift deer ocean insect web lazy sick pencil start select".split())

        # The sender's initial psbt is just a normal payment; 1 input, 2 outputs (0: change, 1: receiver)
        malcolm_psbt_base64 = "cHNidP8BAHECAAAAAWYnORF7WxbvXGvLsusU+pc6TXZa8VEMNdp7vaBQVYVCAgAAAAD9////AtawLQAAAAAAFgAUcuNfLO4QMUvlKwpq5PQk+qFjAUXKLkABAAAAABYAFAyWIwiu+QIC4ZlObGHDlvZn6cwdbgAAAE8BBDWHzwNXHdv+gAAAAG5A8fYC1UaCqTjVNmzP41+yrhVJEa02NktU+hU1gqpdAzp4rbh4dNpY+9lqJ8cE1mJQozBDm1mvmg6+s0+/TDUuEAPNCitUAACAAAAAgAAAAIAAAQEfivVtAQAAAAAWABTjYDCb4Xjt9crkkGTmkTUq62y3VAEDBAEAAAAiBgMHW935AUdSTj7f5cqUZaoXQMzFEd79QZJ5ynA9iF7V8xgDzQorVAAAgAAAAIAAAACAAAAAAAMAAAAAIgICz3sTM/0BgYjqZmMLL+67hILVA7diXpeQxlrZXreSc7sYA80KK1QAAIAAAACAAAAAgAEAAAABAAAAAAA="
        malcolm_psbt = PSBT.parse(a2b_base64(malcolm_psbt_base64))
        malcolm_utxo_value = malcolm_psbt.inputs[0].utxo.value

        # The receiver's initial psbt is an internal cycle spending her own utxo back to the same receive address as above
        zoe_psbt_base64 = "cHNidP8BAFICAAAAAXAmz5cHZ6Z8NQtliuNnFqEV0GgegEaGOLkgnSEl334OAQAAAAD9////ARgthgAAAAAAFgAUDJYjCK75AgLhmU5sYcOW9mfpzB1uAAAATwEENYfPA6IqnfuAAAAAuBxif3KoUTYOOtbRNtTM66nYggBF1i/9wOO1oCmuPh0CP9yB9ueZ7pip6CzDKJhUUDBUXoh/3KlqjWrml9rXy3AQD4iQRFQAAIAAAACAAAAAgAABAR+GLYYAAAAAABYAFGcxK19pAPjZdCADa6WfVtPAawYqAQMEAQAAACIGA/XjxxoNMFunU4xNwU+BEIFSe1ilt+54iu5OC24O68qhGA+IkERUAACAAAAAgAAAAIAAAAAABAAAAAAiAgPGlMVmc+Nbw1Xehprds/1M9qKcaI+RzikiMqfussDzwRgPiJBEVAAAgAAAAIAAAACAAAAAAAUAAAAA"
        zoe_psbt = PSBT.parse(a2b_base64(zoe_psbt_base64))
        zoe_utxo_value = zoe_psbt.inputs[0].utxo.value

        # Initially the respective psbts are not cooperative
        malcolm_psbt_parser = PSBTParser(malcolm_psbt, malcolm_seed)
        zoe_psbt_parser = PSBTParser(zoe_psbt, zoe_seed)
        assert malcolm_psbt_parser.num_external_inputs == 0
        assert zoe_psbt_parser.num_external_inputs == 0

        # Add the receiver's input to the sender's version of the payjoin tx
        malcolm_psbt.inputs.append(deepcopy(zoe_psbt.inputs[0]))
        # malcolm_psbt.inputs[1].bip32_derivations = OrderedDict()  # sender typically won't know these details about the receiver's input

        # Add the sender's input to recipient's version of the payjoin tx
        zoe_psbt.inputs.append(deepcopy(malcolm_psbt.inputs[0]))
        # zoe_psbt.inputs[1].bip32_derivations = OrderedDict()  # recipient typically won't know these details about the sender's input

        # Add the sender's change to recipient's verstion of the payjoin tx
        zoe_psbt.outputs.append(deepcopy(malcolm_psbt.outputs[0]))
        zoe_psbt.outputs[1].bip32_derivations = OrderedDict()  # recipient typically won't know these details about the sender's output

        # Credit the receiver's total amount to be received
        malcolm_psbt.outputs[1].value += zoe_utxo_value
        zoe_psbt.outputs[1].value += zoe_utxo_value

        print("Malcolm's PSBT:", malcolm_psbt)
        print("Zoe's PSBT:", zoe_psbt)

        # Both parties should now view this as a cooperative spend
        malcolm_psbt_parser = PSBTParser(malcolm_psbt, malcolm_seed)
        zoe_psbt_parser = PSBTParser(zoe_psbt, zoe_seed)
        assert malcolm_psbt_parser.num_external_inputs > 0
        assert zoe_psbt_parser.num_external_inputs > 0

        # Verify that the inputs are parsed correctly from Zoe's perspective
        assert zoe_psbt_parser.external_input_amount == malcolm_utxo_value
        assert zoe_psbt_parser.input_amount == zoe_utxo_value

        # Input contexts are reversed from Malcolm's perspective
        assert malcolm_psbt_parser.external_input_amount == zoe_utxo_value
        assert malcolm_psbt_parser.input_amount == malcolm_utxo_value

        # sanity check that both parties can sign
        assert malcolm_psbt.sign_with(bip32.HDKey.from_seed(malcolm_seed.seed_bytes)) == 1
        assert zoe_psbt.sign_with(bip32.HDKey.from_seed(zoe_seed.seed_bytes)) == 1
