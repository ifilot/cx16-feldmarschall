"""Independent synthetic arithmetic feasibility; not a policy implementation."""
from fractions import Fraction
import random
import unittest

ONE, Q = 1 << 24, 4096


def limbs(n):
    assert 0 <= n < 1 << 64
    return [(n >> (8*i)) & 255 for i in range(8)]


def value(a):
    return sum(v << (8*i) for i, v in enumerate(a))


def multiply(a, b):
    result = [0]*16
    for i in range(8):
        carry = 0
        for j in range(8):
            v = result[i+j] + a[i]*b[j] + carry
            result[i+j], carry = v & 255, v >> 8
        result[i+8] += carry
    assert not any(result[8:])
    return result[:8]


def divide(a, b):
    # Binary long division; Python integer remainder is a reference for an
    # eight-byte shift/subtract register, not a cc65 performance measurement.
    d, remainder, quotient = value(b), 0, 0
    assert d
    for bit in range(63, -1, -1):
        remainder = remainder*2 + ((a[bit//8] >> (bit % 8)) & 1)
        quotient <<= 1
        if remainder >= d:
            remainder -= d
            quotient += 1
    return quotient


def trunc(x):
    return (-1 if x < 0 else 1) * (abs(x.numerator)//x.denominator)


def goal(background, compatible, template_gains, H, S, U, E, flag, bomb, bomb_gain):
    per = (ONE-background)//compatible if compatible else 0
    t, A = len(template_gains), sum(template_gains)
    D = per*t*H*U + background*E*H
    if not D:
        return None
    N = per*A*H*U + background*E*S
    immobile, mobile = flag*2000+bomb*bomb_gain, Q-flag-bomb
    # A production implementation must signed-add these two magnitudes.
    x = value(multiply(limbs(abs(immobile)), limbs(D)))
    if immobile < 0:
        x = -x
    y = value(multiply(limbs(mobile), limbs(abs(N))))
    if N < 0:
        y = -y
    magnitude = limbs(abs(x+y))
    denominator = multiply(limbs(Q), limbs(D))
    g = divide(magnitude, denominator)
    return -g if x+y < 0 else g


class Arithmetic(unittest.TestCase):
    def test_declared_bounds(self):
        D = ONE*33*40
        self.assertLess(D, 1 << 35)
        self.assertLess(Q*D, 1 << 47)
        self.assertLess(Q*2000*D, 1 << 58)
        self.assertGreater(ONE*2000, (1 << 31)-1)

    def test_synthetic_fraction_oracle(self):
        rng = random.Random(160104)
        for _ in range(3000):
            compatible = rng.randint(0, 8)
            background = rng.randrange(ONE+1) if compatible else ONE
            gains = [rng.randint(-400, 400) for _ in range(rng.randint(0, compatible))]
            H, U = rng.randint(1, 33), rng.randint(1, 40)
            E, S = rng.randint(0, U), rng.randint(-400*H, 400*H)
            flag = rng.randint(0, Q)
            bomb = rng.randint(0, Q-flag)
            bgain = rng.randint(-400, 400)
            per = (ONE-background)//compatible if compatible else 0
            mass = per*len(gains) + Fraction(background*E, U)
            actual = goal(background, compatible, gains, H, S, U, E, flag, bomb, bgain)
            if not mass:
                self.assertIsNone(actual)
                continue
            conditional = (per*sum(gains) + Fraction(background*E*S, U*H))/mass
            oracle = trunc((flag*2000+bomb*bgain+(Q-flag-bomb)*conditional)/Q)
            self.assertEqual(actual, oracle)

    def test_signed_cancellation_and_fraction(self):
        # Do not truncate the mobile mean before adding Flag/Bomb contributions.
        self.assertEqual(goal(ONE, 0, [], 3, -1, 1, 1, 1, 0, -400), 0)
        self.assertEqual(goal(ONE, 0, [], 3, -2, 1, 1, 0, 0, -400), 0)
        self.assertEqual(goal(ONE, 0, [], 3, -4, 1, 1, 0, 0, -400), -1)


if __name__ == '__main__':
    unittest.main()
