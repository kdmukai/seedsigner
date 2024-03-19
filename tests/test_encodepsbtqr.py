from seedsigner.models.encode_qr import EncodeQR
from seedsigner.models.qr_type import QRType
from embit import psbt
from binascii import a2b_base64

from seedsigner.models.settings import SettingsConstants
from seedsigner.models.seed import Seed



def test_ur_qr_encode():
    base64_psbt = "cHNidP8BAIkCAAAAAaLlQ/VRNpx3IFtoRTOCnq2xfJwg/n7R9XB0TTTnlX/UHQAAAAD9////AtzQAwAAAAAAIgAgCwVSg4Ae1lGNHzy76jLN6GSQaSVnktnmNDByu/wkn7FQwwAAAAAAACIAIJyFZJe7xxQjXpoEBhb8mIkau9OhobDS7xbYxnRIjJUSAAAAAE8BBIiyHgQFgrfagAAAAqP8rWjHFRBmTEWK39AFjd6Wo1sw1UxlgIvROVHUOHbiAzre+t61zOqKFV1xXtDPuUcQRh3M92zh0Zar8rDLPJKQFH7fnFkwAACAAAAAgAAAAIACAACATwEEiLIeBFIg7+eAAAACubwMfJNby3zfn9owhFfgl/Xe/GiHciMMxxB9v6q7BWcCurV9rH+K8ucVU3w52mcEttDldz7kh5cS0xBtWs7wmTYU4IEbazAAAIAAAACAAAAAgAIAAIBPAQSIsh4EX+8GLoAAAALvSlncnGchVCfK7tnzHPVYcBRcck0JGQuspGFpcGP+YQIAXYODa8PIF3hOOnUeYHhlv4PQ+UZCYynQCOoKgVJRhhQYTQfrMAAAgAAAAIAAAACAAgAAgE8BBIiyHgRgkAVVgAAAAsgLKl/ahhLHvS/3Cth+9Hde12MHJO5PP8REKtbWkqONAvETqIlMPWJ/f1uBvSCGFm+zzDYnnEBtuAYjZiQrzj9mFLQz4JUwAACAAAAAgAAAAIACAACATwEEiLIeBLQlJwmAAAAC4IOLeQD9ojcPbh5QGsPVUt/g+dCiQrlZ1DvZK21ajf8CN4aND6VGGhYiFtI9NNyna/M03ovmM4PSg3nR7Df9jsoUhSswjzAAAIAAAACAAAAAgAIAAIBPAQSIsh4EwYVAaYAAAAKvbrl5PeuwgEBUqMQqBYTaTR+PUfKrOXzPQ87VbyLgXwMFEpYG8cv4ljYX+uebG0hJLXsD8K9Lc9K2RqaBmFOtyBQ+RR7+MAAAgAAAAIAAAACAAgAAgAABAP0DDAIAAAADnI5jmO6QLNrEFUwjGd8ZaVBeFqwJGZ3APH1mGpO+GU1CAAAAAP////8tMJlbqdEddNCzmBnmZXSdFFfNTTzD8fd0L2l15pJNWwIAAAAA/////+zKvZECNrGUsrUdWJZnB42n6r1Rhi1XkTyPs/nHuhyoFAAAAAD/////WlvbBAAAAAAAF6kUoY7q7sUcfiktUmzDPQGi//fFvXyHb44BAAAAAAAXqRTHugXLmX3w/lCFhTkfalnedRIHrIeGWAIAAAAAABl2qRQUGQLrLqWokxaHzt65bE2Qle3FQYishdwFAAAAAAAZdqkUX4m0fmwPCUO6pcw8Zbx2YkykKIyIrNACJwAAAAAAFgAUuej6+oAPU186R0ACxtFVG1po+oU7EQUAAAAAABl2qRTGnZD1MfBn92OncmMkRD2Ea+fToYisEksCAAAAAAAXqRS8oz8RN18jt3aeydd/y+/StoEsdYcLajcAAAAAABepFHeYIqSnDz5GuBfk0XbjLOlqNF6Dhy4IFwAAAAAAGXapFDomdwaFLA0OfjLfhXXxGYcjwi94iKyGWAIAAAAAABl2qRSdfDacqPqO9CPL8VtX8vldzlBo6YisSVgCAAAAAAAWABR0DohsF88/3DalzIZyF2ZToibTSxXkLQAAAAAAGXapFPmlzMsqjXuIMCBczer3vGR+GX7KiKwyQAIAAAAAABl2qRTt97UCSLs90250ctaRfDmj6KvZzYis9QgXAAAAAAAWABS526HCIlmm4yis1TxaDNbeCCGyHkakAQAAAAAAF6kUIv85Uai5pFu94QXUYU6YV6ZY/HmHR8gBAAAAAAAZdqkU4cbRwoLlhic5Mx6SdsH8m8bF1nqIrNBvBgAAAAAAGXapFFBUM1drdEjYVzE3ZQOodhobVeNBiKwdSwIAAAAAABl2qRRV48mXLau6y2HwytGPyw/YWXIDR4isD+UGAAAAAAAZdqkUhup0yRlrxdycP9543gF4HEdYVX6IrEiVBAAAAAAAF6kU0xyHPo/mQeDTWX3uHecVQr3QNwmHLjUDAAAAAAAZdqkUR4aV0HjC/bVmOwfjXsbcMzVsbSKIrOqKBAAAAAAAFgAUEx8rhKUzD3fHWdK2v6R9xHvFqHpMhQIAAAAAABl2qRRIg2u4Ow74IDCcGKYnssKpOi2VeYisN6YbAAAAAAAXqRRCSDT9kY3HvkNQI480GmDcu8fffocMQQMAAAAAABl2qRQ83W+Njx6fiXXbXE0fFR9QfA0zJoisdggXAAAAAAAXqRQ9/3PVGaBETVlM+auG6MBXkqNa6YeQt04AAAAAABl2qRRHmF4qf2fYqxhuYPulQCJIhkKyo4isfY4BAAAAAAAXqRQb2OkwwU0kbjeTepBie2hH9Nyhy4d4oAIAAAAAABepFLxzGvLxJoys+l4fvCfHyKNfzx5XhzeVBAAAAAAAIgAgWE9I4MhYpgx9StM1jKekhXHNQ8ohBTlx4N8wbBvDeil4QAIAAAAAABepFJhDXqvM/jN8FZw/lHXkusDCJRTgh2q4AgAAAAAAF6kUtcjnRyRtAOawAnBvMygHecHHRCiHIIkLAAAAAAAZdqkU7X7qc767ZmR51ucTsc5G3uu4XDCIrNBnAwAAAAAAF6kU1SVFH4lwDMpvZEe/g4OXPA/R9EeHcIMDAAAAAAAXqRSGSbWdefvglK8rcFv861TKX7H4Lod63AUAAAAAABepFDspcMlIbqM0IOnk4iOp+VVWsIeIh1zsAQAAAAAAGXapFHrgjevUcXAC9y3FSqtB4O6YHBf9iKxiyAQAAAAAABYAFJWB2pija792dDLax+k7ko3rc3MTmdUBAAAAAAAWABTEd9Lq4RQ5DqWrFEJG0yGwTyNGVmzIAQAAAAAAF6kUvQ1oX0X+EqSr9nm5yVgTEqqwbBKH/jEJAAAAAAAWABS5Q9n7WwpD8V+DoUr1PhtaPjEAzpw4AwAAAAAAGXapFJV07D6tUzUodx2WS8O5Co4x365viKxedB8AAAAAABl2qRQwCg19nxZttgRYVNtqm634kcvwI4islXUXAAAAAAAXqRQdpv7S8UHAtUzhN9UjDzbA1r8l3odrcAMAAAAAABepFFY77ZQ2QH8SBYqU4lswOS2SM3NphxXvCQAAAAAAF6kUQIs3Q5sPU0ubPufbIGTl5aforUWHXtACAAAAAAAZdqkUomTncvcva43IhQjLUn/gkddAA4+IrL1sAwAAAAAAF6kUF0IHuQXB2WY+UKhOt2Fe1PP0YKeHziuGAwAAAAAWABQmwHI2oSXayEsODm4irKumczJcu2hZDQAAAAAAF6kUkEVhUQ33XDK3OqdRZDvT9lpyh5CHoNMJAAAAAAAXqRSoGqG/VTHq7TmPlXD2YYU8ih0HQYdqfgsAAAAAABl2qRTJ1SEupAnvPWOSxpcXFnbfVCx2r4issK0BAAAAAAAXqRTb7/iq9K3zhZIGk0VpFBtYiVJ724cDdRcAAAAAABl2qRRHkxnD6L4pYcssWJdqkDrkja7kmYisokoCAAAAAAAXqRT75VCujkWKFY/ifu/0Orj3JUV0Z4ezjAQAAAAAABYAFBpX8ddXQJ95Vy/v3zi+yYZVi/yglrAEAAAAAAAXqRSLFecvMVMAuxjHz6iSn0XpfQ98gIdNTRgAAAAAABepFB3Wn0gQsayX8cOkCtmSF/NRy08zh5QUBwAAAAAAGXapFLbjX9PnCBzJKViLkLVzyMwtVwNUiKyJSQUAAAAAABepFNDbsKF4ZizxSBuY7NHYnOEuPemxh9LxWwAAAAAAF6kUquecjseAlaEpHxPc83v8kGUFdkuHLzQIAAAAAAAXqRRX8vVVucqqFgH6mGJPEK+/reJ2oYd03AUAAAAAABepFBsBZvNXH4r6Ro8ojq4rmGTcNtBih9maAQAAAAAAGXapFF9oCUBEmn9pA1ddXZGZjsfEFsMOiKzEzwUAAAAAABl2qRRxJyHXAGx4sfRS9WH4eyJLHi+Wd4isLfotAAAAAAAXqRSORo5USPBTLgHEvyfKgfjCqMhnm4csWAIAAAAAABl2qRSRQ+PgB7THRZz/rts1ZV1kB3xCU4ishkoCAAAAAAAZdqkU6tpAL4E1Y53hpyNDyup0NNkIWZ2IrHaaAQAAAAAAF6kUdCiIVs9RAe6mhTnBrZ9rXDmBUwqHMRUHAAAAAAAWABRWDPxl5JVG+87QXnn6mxroeokXegbVCgAAAAAAF6kUc1nZFyA2yQQlxjG7wC8EmcwSYAaHkooLAAAAAAAZdqkUbWMloEkzLZaPkqmvj48ayjP24pWIrKXBCQAAAAAAF6kUhor0BRMQSHMrs8huHLt3PzkmwY+HLTQCAAAAAAAXqRRu2+r5RZ97rALhlGzLcTqXL0qWBYdtdQIAAAAAABepFOvvX6e4KHStEF9gAeP5sueSWoj8h8xKAgAAAAAAF6kUtCOpxVPaoJX6I6x4sYcxi0FRkZuHHEsCAAAAAAAXqRR0jXC8f5rOvLMnaCqNbFhgYV1VI4eynwUAAAAAABepFKk9GBH39jPYAijN98mQiXQLwO6th6KVBAAAAAAAF6kUxAXYvAMMGpeUwbSehQ6yl7PfBKaHhAwGAAAAAAAXqRSgEqI18gMoa8oDed3Nmw0e0JjANodsEAIAAAAAABl2qRSZlcV+iJuoM2F5GdNLhAmJB8LZkYisD9QBAAAAAAAXqRTltOpfMjLJA3a0569jL3OdK96kLYeQXgIAAAAAABl2qRRJxL+Ewl1I7R0UVRYyhvyTdhGt+Yisg0oCAAAAAAAZdqkUqzUSwEEJDrGszAlQNOTOyiXHGc6IrH0qCQAAAAAAF6kUA9gkZnXrwD3nSird5PjY/mKrjrKHrZUEAAAAAAAXqRR2GK6PRPCUdeDBifrkXqVW6OjTVocldRcAAAAAABYAFIALieV/hlNyLSnLzygXuapZ5ZWOeFACAAAAAAAXqRQzJK44f4kGcK0Mr67rQIf8V6K004eNCBcAAAAAABepFEPC9GKHNg91b0VHjiGqN9jskJBnh3wYBgAAAAAAF6kUac+U//Z6fP0Sd1hF+7H2spE6W3uHAAAAAAEBKzeVBAAAAAAAIgAgWE9I4MhYpgx9StM1jKekhXHNQ8ohBTlx4N8wbBvDeikBBc9UIQI90obbwglkzCu7YY5szpmsifPSjmmkMWB2zirsF7i5JSECXtSG8zlgDJHpslDlTL+/MPiyMHW404co4O9XwhrFJD4hAsaYDVoTjPJ1xm5KIpmVjO8AerWFj+0ij7ti1GkxvyI/IQMNJ5G2tHM6GGX9OMrL1a5LLFjx3eyHE9dG8/00BGJ6+yEDW0BA9BSig0YYQcMhaCQ5EgJhYPx0HfMNsknOEzNVBfkhA4/77ELJ9rT3+zhaRN/L3lk81Eie5dlCI15SuNT45ZV+Vq4iBgI90obbwglkzCu7YY5szpmsifPSjmmkMWB2zirsF7i5JRw+RR7+MAAAgAAAAIAAAACAAgAAgAAAAAABAAAAIgYCXtSG8zlgDJHpslDlTL+/MPiyMHW404co4O9XwhrFJD4c4IEbazAAAIAAAACAAAAAgAIAAIAAAAAAAQAAACIGAsaYDVoTjPJ1xm5KIpmVjO8AerWFj+0ij7ti1GkxvyI/HIUrMI8wAACAAAAAgAAAAIACAACAAAAAAAEAAAAiBgMNJ5G2tHM6GGX9OMrL1a5LLFjx3eyHE9dG8/00BGJ6+xwYTQfrMAAAgAAAAIAAAACAAgAAgAAAAAABAAAAIgYDW0BA9BSig0YYQcMhaCQ5EgJhYPx0HfMNsknOEzNVBfkctDPglTAAAIAAAACAAAAAgAIAAIAAAAAAAQAAACIGA4/77ELJ9rT3+zhaRN/L3lk81Eie5dlCI15SuNT45ZV+HH7fnFkwAACAAAAAgAAAAIACAACAAAAAAAEAAAAAAQHPVCEC5eStpJd5y6MpbkWgUYRhL6Sta3BAtONOSEC2uIXXIcEhAw5hli91LeHlLHv5WR6/xjfFTjCsXxE9MtO0wV/a7mTnIQMT9IzdgTJDxQ0CO5Ka1HcnXfbBnCdLN9NZrDKMf3Z+WSEDn6BiNDZ7YI//rSuZjrNIY0k0C3h7MBEur/nzJ7gVF08hA7UGbXn9OfXGcHLWujN7D1wpZqwQrOV49XIiJNtqr6dFIQPwycXFPO4Rf5xaNDQ1zryEERu4z+A3C6iz0+aKHfHq4VauIgIC5eStpJd5y6MpbkWgUYRhL6Sta3BAtONOSEC2uIXXIcEcGE0H6zAAAIAAAACAAAAAgAIAAIABAAAAAAAAACICAw5hli91LeHlLHv5WR6/xjfFTjCsXxE9MtO0wV/a7mTnHOCBG2swAACAAAAAgAAAAIACAACAAQAAAAAAAAAiAgMT9IzdgTJDxQ0CO5Ka1HcnXfbBnCdLN9NZrDKMf3Z+WRx+35xZMAAAgAAAAIAAAACAAgAAgAEAAAAAAAAAIgIDn6BiNDZ7YI//rSuZjrNIY0k0C3h7MBEur/nzJ7gVF08cPkUe/jAAAIAAAACAAAAAgAIAAIABAAAAAAAAACICA7UGbXn9OfXGcHLWujN7D1wpZqwQrOV49XIiJNtqr6dFHLQz4JUwAACAAAAAgAAAAIACAACAAQAAAAAAAAAiAgPwycXFPO4Rf5xaNDQ1zryEERu4z+A3C6iz0+aKHfHq4RyFKzCPMAAAgAAAAIAAAACAAgAAgAEAAAAAAAAAAAEBz1QhAqLp+NQOoYyma8paUW8hucqCdQu2VAZmFGMbV79csI7jIQKtZYJ+sgBVWQwp/xCIeS/x+/SZXAD4VHf56HFmnK9fkyECrvaSdw5m5ZxvwhF7/EbFGJP5MGIDhdbdcILAGsept4shAwlGvi1FP2ybbd5xYnQhz7Cvh2gWaTn5yvMVWm+Ev5keIQPCy/yDc1y1RCJYDMEy6UYkduq4Eq1dyLOoInv5xwsitSED0sEPo41jUtW51+oiJDQPHFt0scWX6aPHivum+kT7WBhWriICAqLp+NQOoYyma8paUW8hucqCdQu2VAZmFGMbV79csI7jHIUrMI8wAACAAAAAgAAAAIACAACAAAAAAAIAAAAiAgKtZYJ+sgBVWQwp/xCIeS/x+/SZXAD4VHf56HFmnK9fkxzggRtrMAAAgAAAAIAAAACAAgAAgAAAAAACAAAAIgICrvaSdw5m5ZxvwhF7/EbFGJP5MGIDhdbdcILAGsept4scGE0H6zAAAIAAAACAAAAAgAIAAIAAAAAAAgAAACICAwlGvi1FP2ybbd5xYnQhz7Cvh2gWaTn5yvMVWm+Ev5keHH7fnFkwAACAAAAAgAAAAIACAACAAAAAAAIAAAAiAgPCy/yDc1y1RCJYDMEy6UYkduq4Eq1dyLOoInv5xwsitRy0M+CVMAAAgAAAAIAAAACAAgAAgAAAAAACAAAAIgID0sEPo41jUtW51+oiJDQPHFt0scWX6aPHivum+kT7WBgcPkUe/jAAAIAAAACAAAAAgAIAAIAAAAAAAgAAAAA="

    tx = psbt.PSBT.parse(a2b_base64(base64_psbt))

    e = EncodeQR(psbt=tx, qr_type=QRType.PSBT__UR2)

    cnt = 0
    while cnt <= 10:
        fragment = e.next_part()
        img = e.part_to_image(fragment)
        cnt += 1



def test_specter_qr_encode():
    base64_psbt = "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"

    tx = psbt.PSBT.parse(a2b_base64(base64_psbt))

    e = EncodeQR(psbt=tx, qr_type=QRType.PSBT__SPECTER)

    cnt = 0
    while cnt <= 10:
        fragment = e.next_part()
        if (cnt+1) == 1:
            assert fragment == "p1of117 cHNidP8BAIkCAAAAAaLlQ/VRNpx3IFtoRTOCnq2xfJwg/n7R9XB0TTTnlX/UHQAAA"
        elif (cnt+1) == 2:
            assert fragment == "p2of117 AD9////AtzQAwAAAAAAIgAgCwVSg4Ae1lGNHzy76jLN6GSQaSVnktnmNDByu/wkn7"
        elif (cnt+1) == 3:
            assert fragment == "p3of117 FQwwAAAAAAACIAIJyFZJe7xxQjXpoEBhb8mIkau9OhobDS7xbYxnRIjJUSAAAAAE8"
        elif (cnt+1) == 4:
            assert fragment == "p4of117 BBIiyHgQFgrfagAAAAqP8rWjHFRBmTEWK39AFjd6Wo1sw1UxlgIvROVHUOHbiAzre"
        elif (cnt+1) == 5:
            assert fragment == "p5of117 +t61zOqKFV1xXtDPuUcQRh3M92zh0Zar8rDLPJKQFH7fnFkwAACAAAAAgAAAAIACA"
        elif (cnt+1) == 6:
            assert fragment == "p6of117 ACATwEEiLIeBFIg7+eAAAACubwMfJNby3zfn9owhFfgl/Xe/GiHciMMxxB9v6q7BW"
        elif (cnt+1) == 7:
            assert fragment == "p7of117 cCurV9rH+K8ucVU3w52mcEttDldz7kh5cS0xBtWs7wmTYU4IEbazAAAIAAAACAAAA"
        elif (cnt+1) == 8:
            assert fragment == "p8of117 AgAIAAIBPAQSIsh4EX+8GLoAAAALvSlncnGchVCfK7tnzHPVYcBRcck0JGQuspGFp"
        elif (cnt+1) == 9:
            assert fragment == "p9of117 cGP+YQIAXYODa8PIF3hOOnUeYHhlv4PQ+UZCYynQCOoKgVJRhhQYTQfrMAAAgAAAA"
        elif (cnt+1) == 10:
            assert fragment == "p10of117 IAAAACAAgAAgE8BBIiyHgRgkAVVgAAAAsgLKl/ahhLHvS/3Cth+9Hde12MHJO5PP8"
        elif (cnt+1) == 11:
            assert fragment == "p11of117 REKtbWkqONAvETqIlMPWJ/f1uBvSCGFm+zzDYnnEBtuAYjZiQrzj9mFLQz4JUwAAC"
        
        img = e.part_to_image(fragment)
        cnt += 1



def test_seedsigner_qr():
    mnemonic = "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"

    e = EncodeQR(seed=Seed(mnemonic.split()), qr_type=QRType.SEED__SEEDQR)

    print(e.next_part())

    assert e.next_part() == "121802020768124106400009195602431595117715840445"



def test_xpub_qr():
    mnemonic = "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"

    e = EncodeQR(seed=Seed(mnemonic.split(), passphrase="pass"), qr_type=QRType.XPUB, network=SettingsConstants.TESTNET, derivation="m/48h/1h/0h/2h")

    assert e.next_part() == "[c49122a5/48h/1h/0h/2h]Vpub5mXgECaX5yYDNc5VnUG4jVNptyEg65qUjuofWchQeuMWWiq8rcPBoMxfrVggXj5NJmaNEToWpax8GMMucozvAdqf1bW1JsZsfdBzsK3VUC5"



def test_specter_xpub_qr():
    mnemonic = "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"

    e = EncodeQR(seed=Seed(mnemonic.split(), passphrase="pass"), qr_type=QRType.XPUB__SPECTER, network=SettingsConstants.TESTNET, derivation="m/48h/1h/0h/2h", qr_density=SettingsConstants.DENSITY__LOW)

    assert e.next_part() == "p1of4 [c49122a5/48h/1h/0h/2h]Vpub5mXgECaX5yYDN"
    assert e.next_part() == "p2of4 c5VnUG4jVNptyEg65qUjuofWchQeuMWWiq8rcPBo"
    assert e.next_part() == "p3of4 MxfrVggXj5NJmaNEToWpax8GMMucozvAdqf1bW1J"
    assert e.next_part() == "p4of4 sZsfdBzsK3VUC5"



def test_ur_xpub_qr():    
    mnemonic = "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"
    
    e = EncodeQR(
        seed=Seed(mnemonic.split(), passphrase="pass"),
        qr_type=QRType.XPUB__UR,
        network=SettingsConstants.TESTNET,
        derivation="m/48h/1h/0h/2h",
        qr_density=SettingsConstants.DENSITY__MEDIUM
    )
    
    assert e.next_part() == "UR:CRYPTO-ACCOUNT/1-4/LPADAACSKPCYMOMNLGRYHDCKOEADCYSSMECPONAOLYTAADMETAADDLOXAXHDCLAOKSRLNLKPUEGYATHPMNSNIYMUECBY"
    assert e.next_part() == "UR:CRYPTO-ACCOUNT/2-4/LPAOAACSKPCYMOMNLGRYHDCKKKGHZMLUZORPVDGUOTECSTTKTOLPCWPTNTLKZTTIZTBEAAHDCXVDTPMYRSTDMOPSCXFZ"
    assert e.next_part() == "UR:CRYPTO-ACCOUNT/3-4/LPAXAACSKPCYMOMNLGRYHDCKSPZSBZSPGERLGDATUYNLPYBTGYIYYKBTWTAOSWKSVTSGCHBYDKYAVDAMTAADMONDGDFD"
    assert e.next_part() == "UR:CRYPTO-ACCOUNT/4-4/LPAAAACSKPCYMOMNLGRYHDCKDYOTADLOCSDYYKADYKAEYKAOYKAOCYSSMECPONAXAAAYCYIOREKKJKAEAEAEWZWDMYON"
