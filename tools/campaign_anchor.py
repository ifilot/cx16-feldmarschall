"""Bound rollout residual improvements relative to the legal native action.

Current correction: clip(E[future-immediate] + credit - pass_reference).
Parent correction: clip(d(action)-d(parent)), where d=E[future-immediate]+credit.
With no clipping these differ by one action-independent constant, so ranking
is unchanged. Parent anchoring makes the fallback action's correction exactly
zero; this is a clipping-anchor experiment, not an extra search or score fit.

Policy-improvement literature motivates comparison with a base policy's legal
action, but gives no guarantee for this bounded residual heuristic under an
approximate opponent model: https://arxiv.org/abs/1910.02426
"""
import math


def choices(scores,credit,totals,weights,parent):
    """Return (choice_scores, corrections, diagnostics), using adapter totals.

    totals[move] contains weighted sums of future, immediate and pass-reference
    values. The caller retains its existing forced-win handling and move ties.
    Only public native scores/credits and permitted sampled futures enter here.
    """
    if not scores or parent not in scores or set(scores)!=set(totals):
        raise ValueError('matching legal actions and native parent required')
    if not weights or any(not math.isfinite(w) or w<=0 for w in weights):
        raise ValueError('finite positive sample weights required')
    mass=sum(weights)
    if not math.isfinite(mass):raise ValueError('finite total sample weight required')
    if any(not math.isfinite(value) for value in scores.values()):
        raise ValueError('finite native scores required')
    residual={}
    reference=None
    for move,values in totals.items():
        if len(values)!=3 or any(not math.isfinite(value) for value in values) or not math.isfinite(credit.get(move,0)):
            raise ValueError('three finite search totals and finite credits required')
        future,immediate,waiting=values
        waiting/=mass
        if not math.isfinite(waiting):raise ValueError('finite normalized reference required')
        if reference is None:reference=waiting
        if abs(waiting-reference)>1e-8:raise ValueError('pass reference must be action independent')
        residual[move]=future/mass-immediate/mass+credit.get(move,0)
        if not math.isfinite(residual[move]):raise ValueError('finite normalized residual required')
    anchor=residual[parent]
    differences={move:value-anchor for move,value in residual.items()}
    if any(not math.isfinite(value) for value in differences.values()):
        raise ValueError('finite residual difference required')
    corrections={move:max(-192,min(192,value)) for move,value in differences.items()}
    corrected={move:scores[move]+corrections[move] for move in scores}
    assert corrections[parent]==0
    return corrected,corrections,dict(mode='legal-native-parent-anchor-v1',
        parent=parent,pass_reference=reference,parent_residual=anchor,parent_correction=0,
        pass_anchor_saturated_actions=sum(abs(value-reference)>=192 for value in residual.values()),
        parent_anchor_saturated_actions=sum(abs(value)>=192 for value in differences.values()),
        values=[dict(move=move,residual=residual[move],preclip_correction=differences[move],
                     correction=corrections[move]) for move in sorted(scores)])
