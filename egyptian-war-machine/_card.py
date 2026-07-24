from micropython import const

_SUITS = const("HDSC")
_RANKS = const("A23456789TJQK")

Card = int


def get_suit(card: Card) -> int:
    return card // 13


def get_rank(card: Card) -> int:
    return card % 13


def get_name(card: Card) -> str:
    return _SUITS[get_suit(card)] + _RANKS[get_rank(card)]
