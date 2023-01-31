import json
from binascii import hexlify, unhexlify
from typing import List
from embit import bip32
from embit import ec
from hashlib import sha256
from seedsigner.helpers import bech32
from seedsigner.models.seed import Seed



KIND__SET_METADATA = 0
KIND__TEXT_NOTE = 1
KIND__RECOMMEND_RELAY = 2
KIND__CONTACTS = 3
KIND__ENCRYPTED_DIRECT_MESSAGE = 4
KIND__DELETE = 5
KIND__REACTIONS = 7
KIND__LIST = 3000

KINDS = {
    KIND__SET_METADATA: "Set metadata",
    KIND__TEXT_NOTE: "Text note",
    KIND__RECOMMEND_RELAY: "Recommend relay",
    KIND__CONTACTS: "Contacts",
    KIND__ENCRYPTED_DIRECT_MESSAGE: "Encrypted DM",
    KIND__DELETE: "Delete",
    KIND__REACTIONS: "Reactions",
    KIND__LIST: "List",
}



class SerializedEventFields:
    # Nostr Events are serialized as (see NIP-01):
    #   [0, <sender_pubkey: str>, <created_at: int>, <kind: int>, <tags: List[List[str]]>, <content:str>]
    SENDER_PUBKEY = 1
    CREATED_AT = 2
    KIND = 3
    TAGS = 4
    CONTENT = 5



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


def get_pubkey_hex(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    privkey = ec.PrivateKey(secret=nostr_root.secret)
    return hexlify(privkey.get_public_key().xonly()).decode()


def get_privkey_hex(seed: Seed) -> str:
    nostr_root = derive_nostr_key(seed=seed)
    return hexlify(nostr_root.secret).decode()



"""****************************************************************************
    Key format conversion
****************************************************************************"""
def pubkey_hex_to_npub(pubkey_hex: str) -> str:
    converted_bits = bech32.convertbits(unhexlify(pubkey_hex), 8, 5)
    return bech32.bech32_encode("npub", converted_bits, bech32.Encoding.BECH32)


def npub_to_hex(npub: str) -> str:
    hrp, data, spec = bech32.bech32_decode(npub)
    raw_public_key = bech32.convertbits(data, 5, 8)[:-1]
    return bytes(raw_public_key).hex()



"""****************************************************************************
    Signing
****************************************************************************"""
def sign_message(seed: Seed, full_message: str):
    """ Hashes the full_message and then signs """
    nostr_root = derive_nostr_key(seed=seed)
    sig = nostr_root.schnorr_sign(sha256(full_message.encode()).digest())
    return sig



"""****************************************************************************
    Events
****************************************************************************"""
def serialize_event(event_dict: dict) -> str:
    """ Serialize an Event from its json form """
    data = [0, event_dict["pubkey"], event_dict["created_at"], event_dict["kind"], event_dict["tags"], event_dict["content"]]
    data_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    return data_str


def sign_event(seed: Seed, serialized_event: str):
    return sign_message(seed=seed, full_message=serialized_event)



"""****************************************************************************
    NIP-26 Delegation
****************************************************************************"""
def assemble_nip26_delegation_token(delegatee_pubkey: str, kinds: List[int] = None, valid_from: int = None, valid_until: int = None):
    token = f"nostr:delegation:{delegatee_pubkey}:"

    conditions = []
    if kinds:
        conditions.append(f"""kind={",".join([str(k) for k in kinds])}""")
    
    if valid_from:
        conditions.append(f"created_at>{valid_from}")

    if valid_until:
        conditions.append(f"created_at<{valid_until}")

    return token + "&".join(conditions)



def parse_nip26_delegation_token(token: str):
    """
    nostr:delegation:<delegatee pubkey>:kind=1,3000&created_at<1675721885
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


def sign_nip26_delegation(seed: Seed, token: str, compact: bool=True):
    token_dict = parse_nip26_delegation_token(token)
    signature = sign_message(seed=seed, full_message=token)

    token = []
    if not compact:
        token.append("delegation")
        token.append(token_dict["delegatee_pubkey"])
    
    token.append("&".join(token_dict["conditions"]))
    token.append(hexlify(signature.serialize()).decode())

    return token
