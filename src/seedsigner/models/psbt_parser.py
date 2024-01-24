from binascii import hexlify
from embit import psbt, script, ec, bip32
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from embit.psbt import PSBT, PSBTScope, InputScope, OutputScope, DerivationPath
from embit.script import Script
from embit.transaction import TransactionOutput
from io import BytesIO
from typing import OrderedDict

from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants



class PSBTParser():
    def __init__(self, p: PSBT, seed: Seed, network: str = SettingsConstants.MAINNET):
        self.psbt: PSBT = p
        self.seed = seed
        self.network = network

        self.policy = None
        self.spend_amount = 0
        self.change_amount = 0
        self.change_data = []
        self.fee_amount = 0
        self.input_amount = 0
        self.external_input_amount = 0
        self.num_inputs = 0
        self.num_external_inputs = 0  # inputs that are not controlled by the seed; cooperative spend/payjoins
        self.destination_addresses = []
        self.destination_amounts = []

        self.root = None

        if self.seed is not None:
            self.parse()


    def get_change_data(self, change_num: int) -> dict:
        if change_num < len(self.change_data):
            return self.change_data[change_num]


    @property
    def num_change_outputs(self):
        return len(self.change_data)


    @property
    def is_multisig(self):
        """
            Multisig psbts will have "m" and "n" defined in policy
        """
        return "m" in self.policy


    @property
    def num_destinations(self):
        return len(self.destination_addresses)


    def _set_root(self):
        self.root = bip32.HDKey.from_seed(self.seed.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(self.network)]["xprv"])


    def parse(self):
        if self.psbt is None:
            print(f"self.psbt is None!!")
            return False

        if not self.seed:
            print("self.seed is None!")
            return False

        self._set_root()

        rt = self._parse_inputs()
        if rt == False:
            return False

        rt = self._parse_outputs()
        if rt == False:
            return False

        return True


    def derive_script_for_root(self, policy: dict, scope: InputScope | OutputScope) -> Script:
        sc = script.Script(b"")
        # multisig, we know witness script
        if policy["type"] == "p2wsh":
            sc = script.p2wsh(scope.witness_script)

        elif policy["type"] == "p2sh-p2wsh":
            sc = script.p2sh(script.p2wsh(scope.witness_script))

        # single-sig
        elif "pkh" in policy["type"]:
            my_pubkey = None
            # should be one or zero for single-key addresses
            if len(scope.bip32_derivations.values()) > 0:
                derivation_paths: list[DerivationPath] = list(scope.bip32_derivations.values())
                der = derivation_paths[0].derivation
                my_pubkey = self.root.derive(der)

            if policy["type"] == "p2wpkh" and my_pubkey is not None:
                sc = script.p2wpkh(my_pubkey)
            elif policy["type"] == "p2sh-p2wpkh" and my_pubkey is not None:
                sc = script.p2sh(script.p2wpkh(my_pubkey))

        elif "p2tr" in policy["type"]:
            my_pubkey = None
            # should have one or zero derivations for single-key addresses
            if len(scope.taproot_bip32_derivations.values()) > 0:
                # TODO: Support keys in taptree leaves
                leaf_hashes, derivation = list(scope.taproot_bip32_derivations.values())[0]
                der = derivation.derivation
                my_pubkey = self.root.derive(der)
                sc = script.p2tr(my_pubkey)
        
        return sc


    def _parse_inputs(self):
        self.input_amount = 0
        self.external_input_amount = 0
        self.num_inputs = 0
        for cur_input in self.psbt.inputs:
            inp_policy = None
            if cur_input.witness_utxo:
                utxo: TransactionOutput = cur_input.witness_utxo
                inp_policy = PSBTParser._get_policy(cur_input, utxo.script_pubkey, self.psbt.xpubs)
                if self.policy == None:
                    self.policy = inp_policy
                else:
                    if self.policy != inp_policy:
                        # TODO: Could be allowed in Payjoin txs
                        raise RuntimeError("Mixed inputs in the transaction")

                sc = self.derive_script_for_root(inp_policy, cur_input)
                if sc.data != utxo.script_pubkey.data:
                    # Current root does not control this input
                    self.num_external_inputs += 1
                    self.external_input_amount += utxo.value

                else:
                    self.num_inputs += 1
                    self.input_amount += utxo.value


    def _parse_outputs(self):
        self.spend_amount = 0
        self.change_amount = 0
        self.change_data = []
        self.fee_amount = 0
        self.destination_addresses = []
        self.destination_amounts = []
        for i, cur_output in enumerate(self.psbt.outputs):
            tx_vout: TransactionOutput = self.psbt.tx.vout[i]
            out_policy = PSBTParser._get_policy(cur_output, tx_vout.script_pubkey, self.psbt.xpubs)
            is_own_output = False

            # if policy is the same, it's possibly a change or receive output
            if out_policy == self.policy:
                # double-check that it's change
                # we already checked in get_cosigners and parse_multisig
                # that pubkeys are generated from cosigners,
                # and witness script is corresponding multisig
                # so we only need to check that scriptpubkey is generated from
                # witness script

                sc = self.derive_script_for_root(out_policy, cur_output)

                if sc.data == tx_vout.script_pubkey.data:
                    is_own_output = True

            if is_own_output:
                # This is a receive or change output that we control
                addr = tx_vout.script_pubkey.address(NETWORKS[SettingsConstants.map_network_to_embit(self.network)])
                fingerprints = []
                derivation_paths = []

                # extract info from non-taproot outputs
                if len(self.psbt.outputs[i].bip32_derivations) > 0:
                    for d, derivation_path in self.psbt.outputs[i].bip32_derivations.items():
                        fingerprints.append(hexlify(derivation_path.fingerprint).decode())
                        derivation_paths.append(bip32.path_to_str(derivation_path.derivation))

                # extract info from taproot outputs
                if len(self.psbt.outputs[i].taproot_bip32_derivations) > 0:
                    for d, (leaf_hashes, derivation) in self.psbt.outputs[i].taproot_bip32_derivations.items():
                        fingerprints.append(hexlify(derivation.fingerprint).decode())
                        derivation_paths.append(bip32.path_to_str(derivation.derivation))

                self.change_data.append({
                    "output_index": i,
                    "address": addr,
                    "amount": tx_vout.value,
                    "fingerprint": fingerprints,
                    "derivation_path": derivation_paths,
                })
                self.change_amount += tx_vout.value

            else:
                # This is an external addr that we don't control
                addr = tx_vout.script_pubkey.address(NETWORKS[SettingsConstants.map_network_to_embit(self.network)])
                self.destination_addresses.append(addr)
                self.destination_amounts.append(tx_vout.value)
                self.spend_amount += tx_vout.value

        self.fee_amount = self.psbt.fee()
        return True


    @staticmethod
    def trim(tx):
        trimmed_psbt = psbt.PSBT(tx.tx)
        for i, inp in enumerate(tx.inputs):
            print(inp.partial_sigs)
            if inp.final_scriptwitness:
                # Taproot sign; trim to only final_scriptwitness
                # From BIP-371 and BIP-174, once final script witness is populated
                # it contains all necessary signatures
                trimmed_psbt.inputs[i].final_scriptwitness = inp.final_scriptwitness
            else:
                trimmed_psbt.inputs[i].partial_sigs = inp.partial_sigs

        return trimmed_psbt


    @staticmethod
    def sig_count(tx):
        cnt = 0
        for i, inp in enumerate(tx.inputs):
            if inp.final_scriptwitness is not None:
                # Taproot sign
                cnt += 1
            else:
                cnt += len(list(inp.partial_sigs.keys()))

        return cnt


    @staticmethod
    def _get_policy(scope: PSBTScope, scriptpubkey: Script, xpubs: OrderedDict[bip32.HDKey, DerivationPath]) -> dict:
        """Parse scope and get policy"""
        # we don't know the policy yet, let's parse it
        script_type = scriptpubkey.script_type()
        # p2sh can be either legacy multisig, or nested segwit multisig
        # or nested segwit singlesig
        if script_type == "p2sh":
            if scope.witness_script is not None:
                script_type = "p2sh-p2wsh"
            elif (
                scope.redeem_script is not None
                and scope.redeem_script.script_type() == "p2wpkh"
            ):
                script_type = "p2sh-p2wpkh"
        policy = {"type": script_type}
        # expected multisig
        if "p2wsh" in script_type and scope.witness_script is not None:
            m, n, pubkeys = PSBTParser._parse_multisig(scope.witness_script)
            # check pubkeys are derived from cosigners
            try:
                cosigners = PSBTParser._get_cosigners(pubkeys, scope.bip32_derivations, xpubs)
                policy.update({"m": m, "n": n, "cosigners": cosigners})
            except:
                policy.update({"m": m, "n": n})
        return policy


    @staticmethod
    def _parse_multisig(sc: Script):
        """Takes a script and extracts m,n and pubkeys from it"""
        # OP_m <len:pubkey> ... <len:pubkey> OP_n OP_CHECKMULTISIG
        # check min size
        if len(sc.data) < 37 or sc.data[-1] != 0xAE:
            raise ValueError("Not a multisig script")
        m = sc.data[0] - 0x50
        if m < 1 or m > 16:
            raise ValueError("Invalid multisig script")
        n = sc.data[-2] - 0x50
        if n < m or n > 16:
            raise ValueError("Invalid multisig script")
        s = BytesIO(sc.data)
        # drop first byte
        s.read(1)
        # read pubkeys
        pubkeys = []
        for i in range(n):
            char = s.read(1)
            if char != b"\x21":
                raise ValueError("Invlid pubkey")
            pubkeys.append(ec.PublicKey.parse(s.read(33)))
        # check that nothing left
        if s.read() != sc.data[-2:]:
            raise ValueError("Invalid multisig script")
        return m, n, pubkeys


    @staticmethod
    def _get_cosigners(pubkeys: list[ec.PublicKey], derivations: OrderedDict[ec.PublicKey, DerivationPath], xpubs: OrderedDict[bip32.HDKey, DerivationPath]):
        """Returns xpubs used to derive pubkeys using global xpub field from psbt"""
        cosigners = []
        for i, pubkey in enumerate(pubkeys):
            if pubkey not in derivations:
                raise ValueError("Missing derivation")
            der = derivations[pubkey]
            for xpub in xpubs:
                origin_der = xpubs[xpub]
                # check fingerprint
                if origin_der.fingerprint == der.fingerprint:
                    # check derivation - last two indexes give pub from xpub
                    if origin_der.derivation == der.derivation[:-2]:
                        # check that it derives to pubkey actually
                        if xpub.derive(der.derivation[-2:]).key == pubkey:
                            # append strings so they can be sorted and compared
                            cosigners.append(xpub.to_base58())
                            break
        if len(cosigners) != len(pubkeys):
            raise RuntimeError("Can't get all cosigners")
        return sorted(cosigners)


    @staticmethod
    def has_matching_input_fingerprint(psbt: PSBT, seed: Seed):
        """
            Extracts the fingerprint from each psbt input utxo. Returns True if any match
            the current seed.
        """
        seed_fingerprint = seed.get_fingerprint()
        for input in psbt.inputs:
            for pub, derivation_path in input.bip32_derivations.items():
                if seed_fingerprint == hexlify(derivation_path.fingerprint).decode():
                    return True

            for pub, (leaf_hashes, derivation_path) in input.taproot_bip32_derivations.items():
                if seed_fingerprint == hexlify(derivation_path.fingerprint).decode():
                    return True
        return False


    def verify_multisig_output(self, descriptor: Descriptor, change_num: int) -> bool:
        change_data = self.get_change_data(change_num)
        i = change_data["output_index"]
        output = self.psbt.outputs[i]
        is_owner = descriptor.owns(output)
        # print(f"{self.psbt.tx.vout[i].script_pubkey.address()} | {output.value} | {is_owner}")
        return is_owner
