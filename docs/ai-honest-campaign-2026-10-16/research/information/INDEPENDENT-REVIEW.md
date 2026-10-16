# Independent information-model review

The exact single-observation background mechanism passes additional checks in
`tools/test_new_campaign_information_review.py`:

- With no missed-capture event, the complete rank marginals equal the unchanged
  template model exactly, for both colors.
- Captured disclosed enemy ranks remain in the public history and are removed
  once from hidden inventory. Live disclosed ranks are removed from hidden
  inventory without incrementing lost counts. Mixed captured/live fixtures keep
  exact totals and pass Q12 rounding for both colors.
- Replacing every hidden enemy rank nibble with any rank leaves the returned
  marginals unchanged. The runtime derives ranks from public history and counts,
  rather than trusting a concealed cell nibble.
- Private opponent setup commands are rejected; changing the input move seed
  changes neither posterior nor rank evidence.
- Public disclosure of the observed enemy retires the soft factor. At that
  point its likelihood is constant across compatible worlds, so it cancels
  rather than being counted again. Reset clears the entire event lifetime.

The registered mechanism conditions only on our already publicly disclosed
soldiers. Knowing our complete own setup does not imply that the opponent knows
those ranks. No inference is made from an opponent declining to attack a rank
that has not been publicly exposed. The rule is probabilistic, not a claim that
an alternative rank was impossible.

## Geometry limitation discovered after prototype completion

The protection gate tests own recapture rays on the original occupancy, before
choosing the hypothetical enemy attacker. An enemy piece can currently block an
own Scout ray, then vacate that square while capturing the supposed victim,
opening an actual Scout recapture. Example: own Scout45, enemy55, own victim65.
The original Scout45→65 ray is blocked by55; after55→65 the ray opens.

The current gate can therefore call that opportunity unprotected even though
the capture would have a geometrical reply. This is a mechanism limitation,
not an information leak or an inventory error. The independently added test
records both occupancies. No frozen runtime was edited. A corrected gate needs
a new immutable policy version and a new comparison; a result for the current
version should retain this qualification.

Scalar trace correction: the frozen observer used in `native-fixture.json`
does not emit candidate scalar traces. Every record now explicitly reports
`scalar_trace_available: false`; the arrays are null. The four differing native
selected moves are observed, but their internal numerical cause was not traced.
