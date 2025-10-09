from base import FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.views.view import MainMenuView, UnhandledExceptionView
from seedsigner.views import scan_views, seed_views, psbt_views
from seedsigner.models.settings import SettingsConstants


# TODO: Cleanup: convert TAB spacing to SPACE
class TestPSBTFlows(FlowTest):

	def test_scan_psbt_first_then_correct_seedqr_flow(self):
		"""
			Selecting "Scan" from the MainMenuView and scanning a PSBT should enter the PSBTSelectSeedView flow
			when Scan a Seed is selected from PSBTSelectSeedView it should enter the ScanView flow
			when a SeedQR is scanned it should enter the PSBTOverviewView flow
			since the PSBT has change no warning is displayed and it should enter the PSBTMathView flow
			since the PSBT is not a self transfer it should enter the PSBTAddressDetailsView flow
		"""
		def load_psbt_into_decoder(view: scan_views.ScanView):
			"""
				PSBT Tx and Wallet Details
				- Single Sig Wallet P2WPKH (Native Segwit) with no passphrase
				- Regtest c751dc07 m/84'/1'/0' tpubDDZBrnxMxbVzqt8EoEiABPxeKzFWma5pra5UEbg3Wst1hrwr6feuvcy7Sov7cpuYx94ypuy1PQ9NDNoQagFs37wGALzLb5Ei3FvyJWPPPKZ
				- 2 Inputs
					- 56,522,834 sats
					- 1,990,245,069 sats
				- 4 Outputs
					- 1 Output to another wallet (bcrt1q7cw0wzy8g6mq5qvkpvhnk5gsps5ncy3srp0n2j) of 123,456 sats
					- 3 Outputs change
						- 3 outputs to emulate a fake mix to increase privacy
						- Change addresses are index 1/7, 1/8, 1/9
						- 1/7 address bcrt1q53j0xwuskuf5gnvynadh0hlazyy8srydlucrhg with amount 123,456 sats
						- 1/8 address bcrt1q5gtw3zfp4cx67yk5q42q6j6rfza8aqcwpyyslv with amount 1,990,121,477 sats
						- 1/9 address bcrt1q9rrg7399m43cn0yg4tz0v0ate89jgf2d6kpz7v with amount 56,399,242 sats
					- Fee 272 sats
			"""
			view.decoder.add_data("cHNidP8BANgCAAAAAsTXZs3fz/dmGb6M80+jjvJZdYya+cw5bT/dGuhZFdSlAAAAAAD9////qo6xg/UZAvUkcbse1F+C9zbP/FeZNjThx7SCIn6eMCgBAAAAAP3///8EQOIBAAAAAAAWABSkZPM7kLcTRE2En1t33/0RCHgMjQXYnnYAAAAAFgAUKMaPRKXdY4m8iKrE9j+rycskJU1A4gEAAAAAABYAFPYc9wiHRrYKAZYLLztREAwpPBIwipVcAwAAAAAWABSiFuiJIa4NrxLUBVQNS0NIun6DDtoRAABPAQQ1h88DBcQGZIAAAAA+0J+jlNL3dpWwlnBi8Dx+Ipg4e6uvB3HdjzFPX7r9CAOOlAIxgII+/xCcj+XoEenKH7wj5s5wlu7Q7CCZWFLGLhA5Su0UVAAAgAEAAIAAAACAAAEA7QIAAAAEE6njX/fnvn7hbkKIRcxzNYFOSfbCdNeWnd7Fe/1UcQ0BAAAAAP3///8TqeNf9+e+fuFuQohFzHM1gU5J9sJ015ad3sV7/VRxDQMAAAAA/f///xOp41/3575+4W5CiEXMczWBTkn2wnTXlp3exXv9VHENBAAAAAD9////E6njX/fnvn7hbkKIRcxzNYFOSfbCdNeWnd7Fe/1UcQ0GAAAAAP3///8CUnheAwAAAAAWABRCfygPJ+Fjsx4BknYvvm3A3qKn2xJ/XQcAAAAAF6kU1I4TAst5nAj15ey7vwe5cM3OFq+HlhEAAAEBH1J4XgMAAAAAFgAUQn8oDyfhY7MeAZJ2L75twN6ip9sBAwQBAAAAIgYCo7sfm78RQY3B5n0ac/QF8VtMAzFnci+h5D1MtpgRY7oYOUrtFFQAAIABAACAAAAAgAEAAAAGAAAAAAEAcQIAAAABxY7wh0nsfJQfzWrD/9rN9BYsM+iOmPaO6I0ANFgO/PcAAAAAAP3///8CptiUAAAAAAAWABRIm4HhQY/TzOjeWSPRrbuJo9MlW826oHYAAAAAFgAU0z+0L2QSLGtyQTn8FhbCpcI7jbliAQAAAQEfzbqgdgAAAAAWABTTP7QvZBIsa3JBOfwWFsKlwjuNuQEDBAEAAAAiBgITHmebEANk81CraV4xZIpqkNjjw0tIvezl1Ism1NRH3Rg5Su0UVAAAgAEAAIAAAACAAQAAAAAAAAAAIgICuTT7WnuiUTpObjWnZFHzIeEvW9PTB+1LLVFNQJVFeIIYOUrtFFQAAIABAACAAAAAgAEAAAAHAAAAACICAk8f3hpc5C35chgSg+Pe2zZ9IhHREd4aKW2+yAMRIFeqGDlK7RRUAACAAQAAgAAAAIABAAAACQAAAAAAIgIDjt1CjvrnMMnjbmTNKUAYoKEDRbmKjNjbq+6Ppqj3bqQYOUrtFFQAAIABAACAAAAAgAEAAAAIAAAAAA==")

		def load_seed_into_decoder(view: scan_views.ScanView):
			view.decoder.add_data("080115060387063104071857067618681125136207731354")
	
		self.run_sequence([
			FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
			FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
			FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
			FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
			FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
			FlowStep(seed_views.SeedOptionsView, is_redirect=True),
			FlowStep(psbt_views.PSBTOverviewView),
			FlowStep(psbt_views.PSBTMathView),
			FlowStep(psbt_views.PSBTAddressDetailsView, button_data_selection=0),
			FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
			FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
			FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),
			FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
			FlowStep(psbt_views.PSBTSignedQRDisplayView),
			FlowStep(MainMenuView)
		])


	def test_scan_psbt_first_then_load_electrum_seed(self):
		"""
			Should be able to load an Electrum mnemonic after first loading in a psbt.
		"""
		def load_psbt_into_decoder(view: scan_views.ScanView):
			# Single sig psbt for the below Electrum mnemonic
			view.decoder.add_data("cHNidP8BAHECAAAAAX9/d6VyI7nvVTyhLBfqu05za2AJ2Z0dKMC0cUX+S2U7AQAAAAD9////AgeHAAAAAAAAFgAUOnNPuZMD1sQudt3+7LvHBUvGhyd//gAAAAAAABYAFGO9QLvu4V9/hz6ZjbIGMrqsEiIYAjQTAAABAR+ghgEAAAAAABYAFKawrgcT62jmIVQwyHPCV0thmJWbAQDBAQAAAAABAYeHL9UQlz/jEKUuNNY3LTeQRjudjBinsP2L0ppvgRt0AAAAAAD/////AnbP3rsPAAAAIlEgtgmCioGjfKwp6f8rOoI4OPb+ZV8db581J9IizZPskl2ghgEAAAAAABYAFKawrgcT62jmIVQwyHPCV0thmJWbAUDCBlMh9VjZN2NdU9Wabi0o3Ct1q9YHTsJRLAkLfUuIHB+BE+ucR4bdGAJG5nBhCWOmCXbpRwKP1INRYvkuQ2fHAAAAACIGA2+PEYHyVy6nhYwAx5SJKBIWXjsWgjhhf/2FEWqXgxnoEKNOC3gAAACAAAAAAAAAAAAAACICA0SBeeHxfHdny6rUnQJuteAnQ7shSydexjJCkSJarn3mEKNOC3gAAACAAQAAAAEAAAAA")

		self.settings.set_value(SettingsConstants.SETTING__ELECTRUM_SEEDS, SettingsConstants.OPTION__ENABLED)

		sequence = [
			FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
			FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
			FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.TYPE_ELECTRUM),
			FlowStep(seed_views.SeedElectrumMnemonicStartView),
		]

		# Load the associated Electrum mnemonic during the flow
		for word in "apple drip silly junior language resource unaware whale snake copy gravity tank".split():
			sequence += [
				FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word),
			]

		sequence += [
			FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
			FlowStep(seed_views.SeedOptionsView, is_redirect=True),
			FlowStep(psbt_views.PSBTOverviewView),
			FlowStep(psbt_views.PSBTMathView),
		]

		self.run_sequence(sequence)


	def test_scan_multisig_psbt_seed_already_signed_flow(self):
		
		def load_psbt_into_decoder(view: scan_views.ScanView):
			view.decoder.add_data("cHNidP8BAIkCAAAAAc9dCSh2RcRPfHaT5bNVBpbg0jAekRLqOK+bpN/QA0jeAAAAAAD9////AtAHAAAAAAAAIlEg24shYsV3IRCzlgmMKjAsR4Ad9tX896z7zDAi5q0TU9H3CgAAAAAAACIAIByGQg/VP2aRID62ty40E64HYZeRRsKRGLt8J/76R6stQ04FAE8BBDWHzwSLLGdzgAAAAq3q6nR20JnHR+vKrBQdWxN9C7xU8zNX942mVF7AQpl2ArrdLwVlkGxaatQJ4wwkvypNBKbwOq9hXGLNlKi7rZWAFDUxzXUwAACAAQAAgAAAAIACAACATwEENYfPBHOCZmWAAAACmH6KTXIny0vueRgQFBq4M6oMuG8f1QM0I/RzKQ03bCgCHrF0fyUtV0+FD2N34u/woqb8MAt/o+7Ed58RddhY8zYUCUjSaDAAAIABAACAAAAAgAIAAIAAAQEriBMAAAAAAAAiACBY4WsjDgJXLj3VW222jU1tkIIhT26ce/2efH73BWGGBiICAqyfkrdUO662QBrdvJcSOZMFxniD7M1awm9U0Kb5XCm5RzBEAiAPkQTY84YjFFkpD6MI2cc5rJySqws5fsTQA/8XEZFpbAIgTNVykbEH4Z7bqyzhhy6lty0K8rtCUDCaHNv+47NNIWgBAQMEAQAAAAEFR1IhApL4XO+VE1pPYn5wnRFyJQKVSc9TX2dO6KIBH6jwvgPaIQKsn5K3VDuutkAa3byXEjmTBcZ4g+zNWsJvVNCm+VwpuVKuIgYCkvhc75UTWk9ifnCdEXIlApVJz1NfZ07oogEfqPC+A9ocNTHNdTAAAIABAACAAAAAgAIAAIAAAAAAAAAAACIGAqyfkrdUO662QBrdvJcSOZMFxniD7M1awm9U0Kb5XCm5HAlI0mgwAACAAQAAgAAAAIACAACAAAAAAAAAAAAAAAEBR1IhApYXaczuYbBM/A+EH639Ir2yIB4PxL46dK/I1V1O9aHgIQLa02HCI/+EP+9gGpxHskjYWFN5hZzXY7RRvwV4UF42ylKuIgIClhdpzO5hsEz8D4Qfrf0ivbIgHg/Evjp0r8jVXU71oeAcNTHNdTAAAIABAACAAAAAgAIAAIABAAAAAAAAACICAtrTYcIj/4Q/72AanEeySNhYU3mFnNdjtFG/BXhQXjbKHAlI0mgwAACAAQAAgAAAAIACAACAAQAAAAAAAAAA")
		
		def load_seed_into_decoder(view: scan_views.ScanView):
			view.decoder.add_data("073318950739065415961602009907670428187212261116")
			
		self.run_sequence([
			FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
			FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
			FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
			FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
			FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
			FlowStep(seed_views.SeedOptionsView, is_redirect=True),
			FlowStep(psbt_views.PSBTOverviewView),
			FlowStep(psbt_views.PSBTMathView),
			FlowStep(psbt_views.PSBTAddressDetailsView, button_data_selection=0),
			FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.SKIP_VERIFICATION),
			FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
			FlowStep(psbt_views.PSBTSigningErrorView, button_data_selection=psbt_views.PSBTSigningErrorView.SELECT_DIFF_SEED),
			FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
			FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
			FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE),
			FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="abc")),
			FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
			FlowStep(seed_views.SeedOptionsView, is_redirect=True),
			FlowStep(psbt_views.PSBTOverviewView),
			FlowStep(psbt_views.PSBTMathView),
			FlowStep(psbt_views.PSBTAddressDetailsView, button_data_selection=0),
			FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.SKIP_VERIFICATION),
			FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
			FlowStep(psbt_views.PSBTSignedQRDisplayView),
			FlowStep(MainMenuView),
		])


	def test_parse_and_display_op_return_content(self):
		"""
			PSBTs that include an OP_RETURN should be able to be parsed like any other
			PSBT and route to the dedicated OP_RETURN View to display the content
		"""
		def load_psbt_into_decoder(view: scan_views.ScanView):
			"""
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
			view.decoder.add_data("cHNidP8BAIYCAAAAATpQ10o+gKdZ8ThpKsbfHiHYn3NhvUrQ5DvW0ZWX8jKLAAAAAAD9////AujC9QUAAAAAFgAUY61+2BcXt+tsWoxV1nVw20kVb1UAAAAAAAAAACtqTChDaGFuY2VsbG9yIG9uIHRoZSBicmluayBvZiB0aGlyZCBiYWlsb3V0aQAAAE8BBDWHzwNXmUmVgAAAANRFa7R5gYD84Wbha3d1QnjgfYPOBw87on6cXS32WoyqAsPFtPxB7PRTdbujUnBPUVDh9YUBtwrl4nc0OcRNGvIyEA+4gv9UAACAAQAAgAAAAIAAAQB0AgAAAAGNFK/1X0fP5q+nu5XX7Tk2VRa0EL+jkGI9CHiJvsjZCgAAAAAA/f///wKMw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAAAAAAAAAAAZakwWYml0Y29pbiBpcyBmcmVlIHNwZWVjaGgAAAABAR+Mw/UFAAAAABYAFIpZMNnUU6cQt8Q0YpZ0pnvsSA5fAQMEAQAAACIGAvxDI0eNI1oQ2AU69R7A0jf+hUdilWCgrWHgdzkqlaXMGA+4gv9UAACAAQAAgAAAAIAAAAAAAQAAAAAiAgK9qKtzGWyiRrpmupdA99NVLriz3GQy6cENbyD19sfl/hgPuIL/VAAAgAEAAIAAAACAAAAAAAIAAAAAAA==")

		def load_seed_into_decoder(view: scan_views.ScanView):
			view.decoder.add_data("114006021552133507590698063102151531110102551496")

		self.run_sequence([
			FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
			FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
			FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
			FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
			FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
			FlowStep(seed_views.SeedOptionsView, is_redirect=True),
			FlowStep(psbt_views.PSBTOverviewView),
			FlowStep(psbt_views.PSBTMathView),
			FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),

			# Should route to display OP_RETURN content
			FlowStep(psbt_views.PSBTOpReturnView, button_data_selection=0),

			# Should be able to sign the psbt
			FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
			FlowStep(psbt_views.PSBTSignedQRDisplayView),
			FlowStep(MainMenuView)
		])


	def test_psbt_with_bip353_dnssec_proof(self):
		"""
			PSBTs that include a BIP-353 recipient should be able to be parsed like any other
			PSBT and include the DNSSEC proof details side flow.
		"""
		def load_psbt_into_decoder(view: scan_views.ScanView):
			"""
				PSBT Tx and Wallet Details
				- Single Sig Wallet P2WPKH (Native Segwit) with no passphrase
				- Testnet 1f0af9e6 m/84'/1'/0' tpubDDBfg6BcdvY62zqSfwiAqN68gbNyGVja6tKL5Nq2JQNJX9G3yqwpotfAsxQPYLGSZJwy5KXtsv3P6mutQV3Sj491PZtth6FpSdcunjDaqaL
				- 1 Input
					- 29,719 sats
				- 2 Outputs
					- 1 Output back to self (tb1qhjj2sx6n7krz7n25fxqm5ymc7njgf0aevmvm77) of 19,578 sats
					- 1 BIP-353 recipient: test@alvroble.com == tb1q0pfv694a8e83rdpcnt77uy8atjpc2qeq3k05d9 of 10,000 sats
				- Fee 141 sats

				The psbt includes the BIP-353 DNSSEC proof which resolves to:
					{
						'valid_from': 1757563200,
						'expires': 1757703396,
						'max_cache_ttl': 300,
						'verified_rrs': [
							{
								'type': 'txt',
								'name': 'test.user._bitcoin-payment.alvroble.com.',
								'contents': 'bitcoin:tb1q0pfv694a8e83rdpcnt77uy8atjpc2qeq3k05d9'
							}
						]
					}
			"""
			view.decoder.add_data("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")

		def load_seed_into_decoder(view: scan_views.ScanView):
			view.decoder.add_data("155003671770097405800105027407971709102912960425")

		self.run_sequence([
			FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
			FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
			FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
			FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
			FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
			FlowStep(seed_views.SeedOptionsView, is_redirect=True),
			FlowStep(psbt_views.PSBTOverviewView),
			FlowStep(psbt_views.PSBTMathView),
			FlowStep(psbt_views.PSBTAddressDetailsView),

			# Should route to verify the DNSSEC proof
			FlowStep(psbt_views.PSBTBIP353DNSSECDetailsView),

			# Resumes the normal flow
			FlowStep(psbt_views.PSBTChangeDetailsView, button_data_selection=psbt_views.PSBTChangeDetailsView.NEXT),

			# Should be able to sign the psbt
			FlowStep(psbt_views.PSBTFinalizeView, button_data_selection=psbt_views.PSBTFinalizeView.APPROVE_PSBT),
			FlowStep(psbt_views.PSBTSignedQRDisplayView),
			FlowStep(MainMenuView)
		])


	def test_psbt_with_invalid_bip353_dnssec_proof(self):
		"""
			PSBT with an invalid BIP-353 DNSSEC proof should route to an error screen
		"""
		def load_psbt_into_decoder(view: scan_views.ScanView):
			"""
				Same PSBT as the valid BIP-353 test above, but with the DNSSEC proof data
				swapped (uses the proof for "craig@sparrowwallet.com" when we're
				expecting the proof for "test@alvroble.com").
			"""
			view.decoder.add_data("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")

		def load_seed_into_decoder(view: scan_views.ScanView):
			view.decoder.add_data("155003671770097405800105027407971709102912960425")

		self.run_sequence([
			FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
			FlowStep(scan_views.ScanView, before_run=load_psbt_into_decoder),  # simulate read PSBT; ret val is ignored
			FlowStep(psbt_views.PSBTSelectSeedView, button_data_selection=psbt_views.PSBTSelectSeedView.SCAN_SEED),
			FlowStep(scan_views.ScanSeedQRView, before_run=load_seed_into_decoder),
			FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
			FlowStep(seed_views.SeedOptionsView, is_redirect=True),
			FlowStep(psbt_views.PSBTOverviewView),
			FlowStep(psbt_views.PSBTMathView),
			FlowStep(psbt_views.PSBTAddressDetailsView),

			# Attempts DNNSEC proof verification but upon failure immediately routes away
			FlowStep(psbt_views.PSBTBIP353DNSSECDetailsView, is_redirect=True),
			FlowStep(psbt_views.PSBTBIP353DNSSECVerificationFailedView),

			# PSBT flow is aborted after verification failure
			FlowStep(MainMenuView)
		])
