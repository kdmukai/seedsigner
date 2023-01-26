from binascii import hexlify, unhexlify
from embit import bip32
from embit import ec
from hashlib import sha256
from seedsigner.helpers import bech32


def derive_nostr_root(seed_bytes: bytes) -> bip32.HDKey:
    """ Derive the NIP-06 Nostr root at m/44'/1237'/0' """
    root = bip32.HDKey.from_seed(seed_bytes)
    return root.derive("m/44h/1237h/0h")


def derive_nostr_child(seed_bytes: bytes, index: int) -> bip32.HDKey:
    """ Derive the NIP-06 Nostr child at m/44'/1237'/0'/0/{index} """
    root = bip32.HDKey.from_seed(seed_bytes)
    return root.derive("m/44h/1237h/0h/0/{index}")


def get_nsec(seed_bytes: bytes) -> str:
    nostr_root = derive_nostr_root(seed_bytes=seed_bytes)
    converted_bits = bech32.convertbits(nostr_root.secret, 8, 5)
    return bech32.bech32_encode("nsec", converted_bits, bech32.Encoding.BECH32)


def get_npub(seed_bytes: bytes) -> str:
    nostr_root = derive_nostr_root(seed_bytes=seed_bytes)
    privkey = ec.PrivateKey(secret=nostr_root.secret)
    pubkey = privkey.get_public_key().serialize()[1:]
    converted_bits = bech32.convertbits(pubkey, 8, 5)
    return bech32.bech32_encode("npub", converted_bits, bech32.Encoding.BECH32)


def pubkey_hex_to_npub(pubkey_hex: str) -> str:
    converted_bits = bech32.convertbits(unhexlify(pubkey_hex), 8, 5)
    return bech32.bech32_encode("npub", converted_bits, bech32.Encoding.BECH32)


def sign_message(seed_bytes: bytes, message: str):
    nostr_root = derive_nostr_root(seed_bytes=seed_bytes)
    sig = nostr_root.schnorr_sign(sha256(message.encode()).digest())
    return sig


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


def sign_nip26_delegation(seed_bytes: bytes, token: str):
    token_dict = parse_nip26_delegation_token(token)
    signature = sign_message(seed_bytes=seed_bytes, message=token)

    return [
        "delegation",
        token_dict["delegatee_pubkey"],
        "&".join(token_dict["conditions"]),
        hexlify(signature.serialize()).decode(),
    ]
