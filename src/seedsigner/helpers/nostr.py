from binascii import hexlify, unhexlify
from typing import List
from embit import bip32
from embit import ec
from hashlib import sha256
from seedsigner.helpers import bech32
from seedsigner.models.seed import Seed


# Nostr kinds
KIND__SET_METADATA = ("Set metadata", 0)
KIND__TEXT_NOTE = ("Notes", 1)
KIND__RECOMMEND_RELAY = ("Recommend relay", 2)
KIND__CONTACTS = ("Contacts", 3)
KIND__ENCRYPTED_DIRECT_MESSAGE = ("DMs", 4)
KIND__DELETE = ("Delete", 5)

ALL_KINDS = [
    KIND__SET_METADATA, KIND__TEXT_NOTE, KIND__RECOMMEND_RELAY, KIND__CONTACTS,
    KIND__ENCRYPTED_DIRECT_MESSAGE, KIND__DELETE
]



def derive_nostr_key(seed: Seed) -> bip32.HDKey:
    """ Derive the NIP-06 Nostr key at m/44'/1237'/0'/0/0 """
    """
        Note: You could derive sibling seeds (e.g. m/44h/1237h/0h/0/1) from the same root
        Seed, but so far Nostr use cases & best practices are limited to just a single
        direct path from mnemonic to npub/nsec. No sibling or child Nostr keys.
    """
    root = bip32.HDKey.from_seed(seed.seed_bytes)
    return root.derive("m/44h/1237h/0h/0/0")


def get_nsec(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    converted_bits = bech32.convertbits(nostr_root.secret, 8, 5)
    return bech32.bech32_encode("nsec", converted_bits, bech32.Encoding.BECH32)


def get_npub(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    privkey = ec.PrivateKey(secret=nostr_root.secret)
    pubkey = privkey.get_public_key().xonly()
    converted_bits = bech32.convertbits(pubkey, 8, 5)
    return bech32.bech32_encode("npub", converted_bits, bech32.Encoding.BECH32)


def pubkey_hex_to_npub(pubkey_hex: str) -> str:
    converted_bits = bech32.convertbits(unhexlify(pubkey_hex), 8, 5)
    return bech32.bech32_encode("npub", converted_bits, bech32.Encoding.BECH32)


def npub_to_hex(npub: str) -> str:
    hrp, data, spec = bech32.bech32_decode(npub)
    raw_public_key = bech32.convertbits(data, 5, 8)[:-1]
    return bytes(raw_public_key).hex()


def sign_message(seed: Seed, message: str):
    nostr_root = derive_nostr_key(seed=seed)
    sig = nostr_root.schnorr_sign(sha256(message.encode()).digest())
    return sig


def assemble_nip26_delegation_token(delegatee_pubkey: str, kinds: List[int], valid_until: int):
    token = f"nostr:delegation:{delegatee_pubkey}:"

    conditions = []
    if kinds:
        conditions.append(f"""kind={",".join([str(kind) for kind in kinds])}""")
    
    conditions.append(f"created_at<{valid_until}")

    return token + "&".join(conditions)



def parse_nip26_delegation_token(token: str):
    """
    nostr:delegation:477318cfb5427b9cfc66a9fa376150c1ddbc62115ae27cef72417eb959691396:kind=1&created_at<1675721885
    """
    parts = token.split(":")

    if parts[0] != "nostr":
        raise Exception(f"Invalid NIP-26 delegation token: {token}")
    if parts[1] != "delegation":
        raise Exception(f"Invalid NIP-26 delegation token: {token}")

    return dict(
        delegatee_pubkey=parts[2],
        delegatee_npub=pubkey_hex_to_npub(parts[2]),
        conditions=parts[3].split("&")
    )


def sign_nip26_delegation(seed: Seed, token: str):
    token_dict = parse_nip26_delegation_token(token)
    signature = sign_message(seed=seed, message=token)

    return [
        "delegation",
        token_dict["delegatee_pubkey"],
        "&".join(token_dict["conditions"]),
        hexlify(signature.serialize()).decode(),
    ]
