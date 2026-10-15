"""Public root-width allocation of a bounded masked-rollout horizon.

Eight samples times twelve root actions times eight policy plies is comparable
to eight samples times twenty-four root actions times four plies. The threshold
comes from that approximate compute budget, not from tournament wins. This
function accepts no board, ranks, outcomes or referee information.
"""


def depth_for_actions(base_depth, legal_action_count):
    if type(base_depth) is not int or not 1 <= base_depth <= 12:
        raise ValueError('base depth must be an integer between one and twelve')
    if type(legal_action_count) is not int or not 1 <= legal_action_count <= 2000:
        raise ValueError('legal action count must be an integer between one and two thousand')
    return 8 if base_depth == 4 and legal_action_count <= 12 else base_depth
