from embit import bip32
from embit.ec import PrivateKey
from seedsigner.helpers import bech32



def get_nostr_private_key(secret: bytes) -> str:
    print(secret)
    converted_bits = bech32.convertbits(bip32.HDKey.from_seed(secret).secret, 8, 5)
    return bech32.bech32_encode("nsec", converted_bits, bech32.Encoding.BECH32)


def get_nostr_public_key(secret: bytes) -> str:
    privkey = PrivateKey(secret=bip32.HDKey.from_seed(secret).secret)
    pubkey = privkey.get_public_key().serialize()[1:]
    converted_bits = bech32.convertbits(pubkey, 8, 5)
    return bech32.bech32_encode("npub", converted_bits, bech32.Encoding.BECH32)
