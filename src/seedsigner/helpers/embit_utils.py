import embit

from binascii import b2a_base64, hexlify, unhexlify
from hashlib import sha256

from embit import bip32, compact, ec
from embit.bip32 import HDKey
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from embit.util import secp256k1


from seedsigner.models.settings_definition import SettingsConstants


"""
    Collection of generic embit-powered util methods.
"""
# TODO: PR these directly into `embit`? Or replace with new/existing methods already in `embit`?


# TODO: Refactor `wallet_type` to conform to our `sig_type` naming convention
def get_standard_derivation_path(network: str = SettingsConstants.MAINNET, wallet_type: str = SettingsConstants.SINGLE_SIG, script_type: str = SettingsConstants.NATIVE_SEGWIT) -> str:
    if network == SettingsConstants.MAINNET:
        network_path = "0'"
    elif network == SettingsConstants.TESTNET:
        network_path = "1'"
    elif network == SettingsConstants.REGTEST:
        network_path = "1'"
    else:
        raise Exception("Unexpected network")

    if wallet_type == SettingsConstants.SINGLE_SIG:
        if script_type == SettingsConstants.LEGACY_P2PKH:
            return f"m/44'/{network_path}/0'"
        elif script_type == SettingsConstants.NESTED_SEGWIT:
            return f"m/49'/{network_path}/0'"
        elif script_type == SettingsConstants.NATIVE_SEGWIT:
            return f"m/84'/{network_path}/0'"
        elif script_type == SettingsConstants.TAPROOT:
            return f"m/86'/{network_path}/0'"
        else:
            raise Exception("Unexpected script type")

    elif wallet_type == SettingsConstants.MULTISIG:
        if script_type == SettingsConstants.LEGACY_P2PKH:
            return f"m/45'" #BIP45
        elif script_type == SettingsConstants.NESTED_SEGWIT:
            return f"m/48'/{network_path}/0'/1'"
        elif script_type == SettingsConstants.NATIVE_SEGWIT:
            return f"m/48'/{network_path}/0'/2'"
        elif script_type == SettingsConstants.TAPROOT:
            raise Exception("Taproot multisig/musig not yet supported")
        else:
            raise Exception("Unexpected script type")
    else:
        raise Exception("Unexpected wallet type")    # checks that all inputs are from the same wallet



def get_xpub(seed_bytes, derivation_path: str, embit_network: str = "main") -> HDKey:
    root = bip32.HDKey.from_seed(seed_bytes, version=NETWORKS[embit_network]["xprv"])
    xprv = root.derive(derivation_path)
    xpub = xprv.to_public()
    return xpub



def get_single_sig_address(xpub: HDKey, script_type: str = SettingsConstants.NATIVE_SEGWIT, index: int = 0, is_change: bool = False, embit_network: str = "main") -> str:
    if is_change:
        pubkey = xpub.derive([1,index]).key
    else:
        pubkey = xpub.derive([0,index]).key

    if script_type == SettingsConstants.LEGACY_P2PKH:
        return embit.script.p2pkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.NESTED_SEGWIT:
        return embit.script.p2sh(embit.script.p2wpkh(pubkey)).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.NATIVE_SEGWIT:
        return embit.script.p2wpkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.TAPROOT:
        return embit.script.p2tr(pubkey).address(network=NETWORKS[embit_network])



def get_multisig_address(descriptor: Descriptor, index: int = 0, is_change: bool = False, embit_network: str = "main"):
    if is_change:
        branch_index = 1
    else:
        branch_index = 0

    # Can derive p2wsh, p2sh-p2wsh, and legacy (non-segwit) p2sh
    if descriptor.is_segwit or (descriptor.is_legacy and descriptor.is_basic_multisig):
        return descriptor.derive(index, branch_index=branch_index).script_pubkey().address(network=NETWORKS[embit_network])

    elif descriptor.is_taproot:
        # TODO: Not yet implemented!
        raise Exception("Taproot verification not yet implemented!")

    raise Exception(f"{descriptor.script_pubkey().script_type()} address verification not yet implemented!")



def get_embit_network_name(settings_name):
    """ Convert SeedSigner SettingsConstants for `network` to embit's NETWORK key """
    lookup = {
        SettingsConstants.MAINNET: "main",
        SettingsConstants.TESTNET: "test",
        SettingsConstants.REGTEST: "regtest",
    }
    return lookup.get(settings_name)



def parse_derivation_path(derivation_path: str) -> dict:
    """
    Parses a derivation path into its related SettingsConstants equivalents.

    Primarily only supports single sig derivation paths.

    May return None for fields it cannot parse.
    """
    # Support either m/44'/... or m/44h/... style
    derivation_path = derivation_path.replace("'", "h")

    sections = derivation_path.split("/")

    if sections[1] == "48h":
        # So far this helper is only meant for single sig message signing
        raise Exception("Not implemented")

    lookups = {
        "script_types": {
            "44h": SettingsConstants.LEGACY_P2PKH,
            "49h": SettingsConstants.NESTED_SEGWIT,
            "84h": SettingsConstants.NATIVE_SEGWIT,
            "86h": SettingsConstants.TAPROOT,
        },
        "networks": {
            "0h": SettingsConstants.MAINNET,
            "1h": [SettingsConstants.TESTNET, SettingsConstants.REGTEST],
        }
    }

    details = dict()
    details["script_type"] = lookups["script_types"].get(sections[1])
    if not details["script_type"]:
        details["script_type"] = SettingsConstants.CUSTOM_DERIVATION
    details["network"] = lookups["networks"].get(sections[2])

    # Check if there's a standard change path
    if sections[-2] in ["0", "1"]:
        details["is_change"] = sections[-2] == "1"
    else:
        details["is_change"] = None

    # Check if there's a standard address index
    if sections[-1].isdigit():
        details["index"] = int(sections[-1])
    else:
        details["index"] = None

    if details["is_change"] is not None and details["index"] is not None:
        # standard change and addr index; safe to truncate to the wallet level
        details["wallet_derivation_path"] = "/".join(sections[:-2])
    else:
        details["wallet_derivation_path"] = None

    details["clean_match"] = True
    for k, v in details.items():
        if v is None:
            # At least one field couldn't be parsed
            details["clean_match"] = False
            break

    return details



def sign_message(seed_bytes: bytes, derivation: str, msg: bytes, compressed: bool = True, embit_network: str = "main") -> bytes:
    """
        from: https://github.com/cryptoadvance/specter-diy/blob/b58a819ef09b2bca880a82c7e122618944355118/src/apps/signmessage/signmessage.py
    """
    """Sign message with private key"""
    msghash = sha256(
        sha256(
            b"\x18Bitcoin Signed Message:\n" + compact.to_bytes(len(msg)) + msg
        ).digest()
    ).digest()

    root = bip32.HDKey.from_seed(seed_bytes, version=NETWORKS[embit_network]["xprv"])
    prv = root.derive(derivation).key
    sig = secp256k1.ecdsa_sign_recoverable(msghash, prv._secret)
    flag = sig[64]
    sig = ec.Signature(sig[:64])
    c = 4 if compressed else 0
    flag = bytes([27 + flag + c])
    ser = flag + secp256k1.ecdsa_signature_serialize_compact(sig._sig)
    return b2a_base64(ser).strip().decode()



def parse_miniscript_n_of_m(spend_path: Descriptor):
    """
    Validates that the provided fragment is an n-of-m and returns relevant data.

    Expected structure:
    Multi(
        n,
        key1,
        key2,
        ...,
        keym
    )
    """
    from embit.descriptor.miniscript import Multi

    if not isinstance(spend_path, Multi):
        raise Exception(f"Spend path starts with `{type(spend_path)}` instead of `Multi`")

    path1_n = spend_path.args[0].num
    path1_m = len(spend_path.args) - 1
    print(path1_n, "of", path1_m)

    keys = []
    for key in spend_path.args[1:]:
        keys.append((
            hexlify(key.fingerprint).decode(),
            bip32.path_to_str(key.derivation),
            key.branches,
            key.key.to_base58(),
        ))
    return dict(
        n=path1_n,
        m=path1_m,
        keys=keys,
    )



def parse_miniscript_timelocked_1_of_m(spend_path: Descriptor):
    """
    Validates that the provided fragment is a 1-of-m WITH a timelock and returns relevant
    data.

    Expected structure:
    AndV(
        # First condition must be satisfied (threshold of 1 of m)
        V(Thresh(
            1,
            Pkh(KeyHash),
            A(Pkh(key2),
            ...,
            A(Pkh(keym)
        )),

        # AND second condition must be satisified (timelock elapsed)
        Older(timelock_blocks)
    )
    """
    from embit.descriptor.miniscript import AndV, Number, Older, Pkh, Thresh, V

    # TODO: add support for args[0] and args[1] to be flipped; order doesn't matter in
    # the AndV() args.
    if not isinstance(spend_path, AndV):
        raise Exception(f"Spend path starts with `{type(spend_path)}` instead of `AndV`")

    if not isinstance(spend_path.args[0], V):
        raise Exception(f"Expected miniscript type `V`, got `{type(spend_path.args[0])}`")

    if not isinstance(spend_path.args[0].args[0], Thresh):
        raise Exception(f"Expected miniscript type `Thresh`, got `{type(spend_path.args[0].args[0])}`")

    if not isinstance(spend_path.args[0].args[0].args[0], Number):
        raise Exception(f"Expected miniscript type `Number`, got `{type(spend_path.args[0].args[0].args[0])}`")

    if spend_path.args[0].args[0].args[0].num != 1:
        raise Exception(f"Expected threshold quorum of 1, got `{type(spend_path.args[0].args[0].args[0].num)}`")

    if not isinstance(spend_path.args[1], Older):
        raise Exception(f"Expected miniscript type `Older`, got `{type(spend_path.args[1])}`")
    
    path_n = 1
    path_m = len(spend_path.args[0].args[0].args) - 1
    print(path_n, "of", path_m)

    keys = []
    for option in spend_path.args[0].args[0].args[1:]:
        key = option.args[0]
        if type(key) == Pkh:
            key = key.args[0]
        keys.append((
            hexlify(key.fingerprint).decode(),
            bip32.path_to_str(key.derivation),
            key.branches,
            key.key.to_base58(),
        ))
    
    timelock = spend_path.args[1].args[0].num

    return dict(
        n=path_n,
        m=path_m,
        keys=keys,
        timelock=timelock,
    )



def parse_miniscript_n_of_m_decays_to_1_of_m(ms: Descriptor) -> bool:
    """
    Checks if a miniscript is an n-of-m that decays to a 1-of-m

    Output format:
    [
        {
            'n': 2,
            'm': 3,
            'keys': [
                ('0f889044', 'm/48h/1h/0h/2h', [0, 1], 'tpubDFQDKbH2mDqNDPNaUVxM6R5mHhzC4u5F6mNnUkCf6gBMbcENMQ1ZGFLZc3QwgdEv2f34wkTvLMG5kD8AZEZRhat1HQDj42eVxQSxbcqxn31'),
                ('03cd0a2b', 'm/48h/1h/0h/2h', [0, 1], 'tpubDEPEYgTj1ddmZqDdpiq5Gjttx3CnNSFppSaUa5eHAUVNMD2FE1ihGA2EMP92mzmSUGJsTAgMhBTACd9xsRDB5K4GKJH8RzbRuFUrmVVLR15'),
                ('3666c686', 'm/48h/1h/0h/2h', [0, 1], 'tpubDERSdjUfKa7Qy6c7k3s1jcEcEUYudhy4WcEN1PDKtTVK7cPQVRQRSGdVDNDGiPGrQ1WT28Qws4zZ4bRj1LnpCgsiGkbqHkxMEdnsr9hS9sr')
            ]
        },
        {
            'n': 1,
            'm': 3,
            'keys': [
                ('0f889044', 'm/48h/1h/0h/2h', [2, 3], 'tpubDFQDKbH2mDqNDPNaUVxM6R5mHhzC4u5F6mNnUkCf6gBMbcENMQ1ZGFLZc3QwgdEv2f34wkTvLMG5kD8AZEZRhat1HQDj42eVxQSxbcqxn31'),
                ('03cd0a2b', 'm/48h/1h/0h/2h', [2, 3], 'tpubDEPEYgTj1ddmZqDdpiq5Gjttx3CnNSFppSaUa5eHAUVNMD2FE1ihGA2EMP92mzmSUGJsTAgMhBTACd9xsRDB5K4GKJH8RzbRuFUrmVVLR15'),
                ('3666c686', 'm/48h/1h/0h/2h', [2, 3], 'tpubDERSdjUfKa7Qy6c7k3s1jcEcEUYudhy4WcEN1PDKtTVK7cPQVRQRSGdVDNDGiPGrQ1WT28Qws4zZ4bRj1LnpCgsiGkbqHkxMEdnsr9hS9sr')
            ],
            'timelock': 10
        }
    ]
    """
    from embit.descriptor.miniscript import OrD, Multi
    # Root is an OrD
    if not isinstance(ms, OrD):
        raise Exception(f"Expected miniscript type `OrD`, got `{type(ms)}`")

    if not len(ms.args) == 2:
        raise Exception(f"Expected 2 args in the `OrD`, got `{len(ms.args)}`")

    if not isinstance(ms.args[0], Multi):
        raise Exception(f"Expected miniscript type `Multi`, got `{type(ms.args[0])}`")

    # TODO: add support for the decay path to be first; order doesn't matter in the
    # OrD() args.
    path_1 = parse_miniscript_n_of_m(ms.args[0])
    path_2 = parse_miniscript_timelocked_1_of_m(ms.args[1])

    return [
        path_1,
        path_2
    ]


def parse_miniscript_descriptor(descriptor: str) -> Descriptor:
    dstr = descriptor.replace("\n", "").replace(" ", "").replace("<0;1>", "{0,1}").replace("<2;3>", "{2,3}")
    print(dstr)
    return Descriptor.from_string(dstr)

