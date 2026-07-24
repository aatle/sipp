import random
from time import monotonic as get_time
from time import sleep

import displayio
from card import Card, get_name, get_rank
from digit4x1 import UPDATE_RATE, Digit4x1
from digitalio import DigitalInOut
from egyptian_war_combos import BASIC_COMBOS
from micropython import const
from pwmio import PWMOut
from util import Button, map_range

Player = int


def shuffle(lst: list) -> None:
    for i in range(len(lst) - 1, 0, -1):
        j = random.randint(0, i)
        lst[i], lst[j] = lst[j], lst[i]


class EgyptianWar:
    def __init__(self, on_take_pile=lambda player: None) -> None:
        deck = list(range(52))
        shuffle(deck)
        half = len(deck) // 2
        self.hands = deck[half:], deck[:half]
        del deck
        self.pile: list[Card] = []
        self.turn = 0
        self.combos: tuple = BASIC_COMBOS
        self.burned = 0  # number of cards burned in this pile
        self.incorrect_slap_punishment = 2
        self.on_take_pile = on_take_pile
        self.challenge_chances: int | None = None
        self.challenge_win: Player | None = None

    def next_turn(self, *, challenge: bool = False) -> None:
        # Challenging a player with no cards places the turn on them and they instantly
        # lose the challenge
        if self.hands[1 - self.turn] or challenge:
            self.turn = 1 - self.turn

    def play_card(self) -> None:
        player = self.turn
        hand = self.hands[player]
        if not hand:
            return
        self.challenge_win = None
        card = hand.pop()
        self.pile.append(card)

        chances = self.get_challenge_chances(get_rank(card))
        if chances:
            # Challenge
            self.challenge_chances = chances
            self.next_turn(challenge=True)
            return
        if self.challenge_chances is not None:
            # Active challenge continues
            self.challenge_chances -= 1
            if self.challenge_chances > 0:
                # Continue with same player
                return
            # Lose challenge
            self.challenge_chances = None
            self.challenge_win = 1 - player
        self.next_turn()

    def slap_pile(self, player: Player) -> bool:
        hand = self.hands[player]
        won_challenge = player == self.challenge_win or (
            self.challenge_chances is not None
            and player != self.turn
            and not self.hands[self.turn]
            # Opponent ran out of cards during challenge
        )
        slap_correct = won_challenge or self.check_slap()
        if slap_correct:
            self.take_pile(player)
        else:
            for _ in range(self.incorrect_slap_punishment):
                if not hand:
                    break
                self.pile.insert(0, hand.pop())
                self.burned += 1
            if not hand and self.turn == player and self.challenge_chances is None:
                self.next_turn()
        return slap_correct

    def take_pile(self, player: Player) -> None:
        self.on_take_pile(player)
        self.challenge_chances = None
        self.challenge_win = None
        hand = self.hands[player]
        # while self.pile:
        #     hand.insert(0, self.pile.pop(0))
        hand[:] = self.pile + hand
        self.pile.clear()
        self.burned = 0
        self.turn = player
        if not hand:  # failsafe
            self.next_turn()

    def check_slap(self) -> bool:
        pile, burned = self.pile, self.burned
        return any(combo(pile, burned) for combo in self.combos)

    def check_win(self) -> Player | None:
        if self.pile:
            return None
        return 1 if not self.hands[0] else 0 if not self.hands[1] else None

    @staticmethod
    def get_challenge_chances(rank: int) -> int:
        if rank == 10:  # J
            return 1
        if rank == 11:  # Q
            return 2
        if rank == 12:  # K
            return 3
        if rank == 0:  # A
            return 4
        return 0


_TICK_RATE = const(60)

_x_position = const((128 - 44) // 2)


def load_card_layer(card: Card) -> displayio.TileGrid:
    bitmap = displayio.OnDiskBitmap(f"cards-bmp/{get_name(card)}.bmp")
    return displayio.TileGrid(
        bitmap, pixel_shader=bitmap.pixel_shader, x=_x_position, y=0
    )


def play_egyptian_war(
    player1: DigitalInOut,
    player2: DigitalInOut,
    splash: displayio.Group,
    digit4x1: Digit4x1,
    led_r: PWMOut,
    led_b: PWMOut,
) -> None:
    def set_text(hand_size1: int, hand_size2: int) -> None:
        digit4x1.text = f"{hand_size1:2}{hand_size2:2}"

    def set_color(player: Player | None) -> None:
        if player == 0:
            led_r.value = 0
            led_b.value = 1
        elif player == 1:
            led_r.value = 1
            led_b.value = 0
        else:
            led_r.value = led_b.value = 0

    def updated_sleep(seconds: float) -> None:
        start_time = get_time()
        while get_time() - start_time < seconds:
            digit4x1.update()
            sleep(1.0 / UPDATE_RATE)

    def on_take_pile(player: Player) -> None:
        update_card_layer()
        updated_sleep(0.5)
        player1_button.last_value = player2_button.last_value = False
        take_rate = 5
        blink_frequency = take_rate
        blink_duty_cycle = 0.8
        hand_sizes = [len(game.hands[0]), len(game.hands[1])]
        initial_size = hand_sizes[player]
        final_size = initial_size + len(game.pile)
        duration = len(game.pile) * 0.2
        start_time = get_time()
        while (elapsed := min(duration, get_time() - start_time)) < duration:
            new_hand_size = int(
                map_range(elapsed, 0.0, duration, initial_size, final_size)
            )
            if new_hand_size != hand_sizes[player]:
                hand_sizes[player] = new_hand_size
                set_text(hand_sizes[0], hand_sizes[1])
            sleep(1.0 / UPDATE_RATE)
            digit4x1.update()
            set_color(
                player if (elapsed * blink_frequency) % 1.0 < blink_duty_cycle else None
            )

    current_card: Card | None = None

    def update_card_layer() -> None:
        nonlocal current_card
        card = game.pile[-1] if game.pile else None
        if card != current_card:
            current_card = card
            if card_group:
                card_group.pop()
            if current_card is not None:
                digit4x1.text = digit4x1.BLANK_TEXT
                digit4x1.update()
                set_color(None)
                sleep(0.001)
                card_group.append(load_card_layer(current_card))

    def update_all() -> None:
        update_card_layer()
        set_text(len(game.hands[0]), len(game.hands[1]))
        set_color(game.turn)

    card_group = displayio.Group()
    splash.append(card_group)
    card_group = splash
    game = EgyptianWar(on_take_pile)
    player1_button = Button(player1)
    player2_button = Button(player2)
    update_all()
    while (winner := game.check_win()) is None:
        updated_sleep(1.0 / _TICK_RATE)
        time = get_time()
        press1 = player1_button.update(time)
        press2 = player2_button.update(time)
        if press1 == Button.SHORT_PRESS:
            game.slap_pile(0 if press2 != Button.SHORT_PRESS else random.randint(0, 1))
        elif press2 == Button.SHORT_PRESS:
            game.slap_pile(1)
        elif press1 == Button.LONG_PRESS and game.turn == 0:
            game.play_card()
        elif press2 == Button.LONG_PRESS and game.turn == 1:
            game.play_card()
        else:
            # No update needed
            continue
        update_all()
    start_time = get_time()
    blink_frequency = 5
    blink_duty_cycle = 0.5
    while (elapsed := get_time() - start_time) < 3.0:
        on_cycle = (elapsed * blink_frequency) % 1.0 < blink_duty_cycle
        set_color(
            winner if (elapsed * blink_frequency) % 1.0 < blink_duty_cycle else None
        )
        if on_cycle:
            digit4x1.text = digit4x1.BLANK_TEXT
        else:
            set_text(len(game.hands[0]), len(game.hands[1]))
        digit4x1.update()
        sleep(1.0 / UPDATE_RATE)
