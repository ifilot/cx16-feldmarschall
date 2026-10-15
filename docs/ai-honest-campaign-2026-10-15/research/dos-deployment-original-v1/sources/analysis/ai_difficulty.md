# Difficulty setting and identity disclosure

The original DGROUP menu entries at DS0A7C..0A9C link these strings and
far overlay1 callbacks. Each callback begins with an assignment to DS3E90:

| Label | Value | Callback |
| --- | ---: | --- |
| Sergeant | 1 | ovl1:D41A |
| Major | 2 | ovl1:D439 |
| Colonel | 3 | ovl1:D458 |
| General | 4 | ovl1:D477 |
| Marshal | 5 | ovl1:D496 |

`verify_ai_difficulty.py` checks all labels, stored far pointers and the
six assignment bytes against pinned original inputs. It does not reconstruct
the rest of the callbacks or verify interactive menu highlighting.

Overlay5 `5877..5DC8` consults the physical rank board while updating hidden
AI identities. Its late-disclosure gate is difficulty5 and sequence>30,
difficulty4 and sequence>40, or any difficulty and sequence>60. Unknown
non-Bomb records are then disclosed if distance to the reference square is
less than4 or their row is less than4. Other earlier branches can disclose
Miners or Bombs. A final pass discloses remaining unknowns when exactly one
non-Flag/non-Bomb unknown identity count is positive.

This is a concrete use of true physical identities in the AI's knowledge
state. It does not prove when normal gameplay calls each branch or how much
advantage it supplies. The sequence word is context+0; its relationship to
complete turns still needs caller/runtime evidence.

The346-case normalization comparison includes all threshold boundaries and
consistent states with only Scout identities left unknown. On layout3,
sequence31, owner0 and reference(6,4), the original changes10 watched bytes
at difficulties0..4 and34 at difficulty5; both C runs match byte for byte.
These are controlled initialized positions, not an interactive game trace.
