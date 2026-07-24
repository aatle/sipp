from card import Card, get_rank


def _combo(pile: list[Card], burned: int) -> bool:  # stub
    return False


def double(pile: list[Card], burned: int) -> bool:
    return len(pile) - burned >= 2 and get_rank(pile[-1]) == get_rank(pile[-2])


def sandwich(pile: list[Card], burned: int) -> bool:
    return len(pile) - burned >= 3 and get_rank(pile[-1]) == get_rank(pile[-3])


def top_bottom(pile: list[Card], burned: int) -> bool:
    return burned == 0 and len(pile) >= 2 and get_rank(pile[-1]) == get_rank(pile[0])


def marriage(pile: list[Card], burned: int) -> bool:
    if len(pile) - burned < 2:
        return False
    rank1 = get_rank(pile[-1])
    rank2 = get_rank(pile[-2])
    return (rank1 == "K" and rank2 == "Q") or (rank1 == "Q" and rank2 == "Q")


BASIC_COMBOS = double, sandwich, top_bottom, marriage
