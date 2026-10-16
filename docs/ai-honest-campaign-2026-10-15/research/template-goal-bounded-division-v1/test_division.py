"""Eight-byte reference for a bounded signed quotient; not runtime policy code."""
from fractions import Fraction
import json
from pathlib import Path
import random
import unittest

WIDTH = 8


def encode(n):
    assert 0 <= n < 1 << 64
    return [(n >> (8*i)) & 255 for i in range(WIDTH)]


def decode(a):
    return sum(n << (8*i) for i, n in enumerate(a))


def shifted_ten(a, counts):
    # Shift one byte then two bits; no wide Python remainder or dividend scan.
    result, carry = [0]*WIDTH, 0
    assert a[-1] == 0
    for i in range(1, WIDTH):
        v = a[i-1]*4 + carry
        result[i], carry = v & 255, v >> 8
        counts['initial_shift_byte_steps'] += 1
    assert carry == 0
    return result


def compare(a, b, counts):
    for i in range(WIDTH-1, -1, -1):
        counts['compare_byte_steps'] += 1
        if a[i] != b[i]:
            return 1 if a[i] > b[i] else -1
    return 0


def subtract(a, b, counts):
    borrow = 0
    for i in range(WIDTH):
        v = a[i] - b[i] - borrow
        borrow = int(v < 0)
        a[i] = v & 255
        counts['subtract_byte_steps'] += 1
    assert borrow == 0


def right_one(a, counts):
    carry = 0
    for i in range(WIDTH-1, -1, -1):
        v = a[i] + carry*256
        a[i], carry = v >> 1, v & 1
        counts['right_shift_byte_steps'] += 1


def quotient(magnitude, denominator, negative=False):
    counts = dict(stages=0, initial_shift_byte_steps=0, compare_byte_steps=0,
                  subtract_byte_steps=0, right_shift_byte_steps=0)
    # Caller must certify magnitude <= 2000*denominator and denominator > 0.
    shifted = shifted_ten(denominator, counts)
    remainder = list(magnitude)
    q = 0
    for bit in range(10, -1, -1):
        counts['stages'] += 1
        if compare(remainder, shifted, counts) >= 0:
            subtract(remainder, shifted, counts)
            q |= 1 << bit
        if bit:
            right_one(shifted, counts)
    assert q <= 2000
    # Integer sign restoration produces truncation toward zero, including -0.
    return (-q if negative else q), counts


def trunc(x):
    return (-1 if x < 0 else 1)*(abs(x.numerator)//x.denominator)


class BoundedDivision(unittest.TestCase):
    def check_case(self, numerator, denominator):
        self.assertGreater(denominator, 0)
        self.assertLess(denominator, 1 << 47)
        self.assertLessEqual(abs(numerator), 2000*denominator)
        actual, counts = quotient(encode(abs(numerator)), encode(denominator), numerator < 0)
        self.assertEqual(actual, trunc(Fraction(numerator, denominator)))
        self.assertEqual(counts['stages'], 11)
        self.assertLessEqual(counts['compare_byte_steps'], 88)
        self.assertLessEqual(counts['subtract_byte_steps'], 88)
        self.assertEqual(counts['right_shift_byte_steps'], 80)
        self.assertEqual(counts['initial_shift_byte_steps'], 7)
        return counts

    def test_boundaries_and_sign(self):
        for d in (1, 3, 4096, (1 << 46)-1, (1 << 47)-1):
            for q in (0, 1, 2, 511, 1023, 1024, 1999, 2000):
                for n in (q*d, max(0, q*d-1), min(2000*d, q*d+d-1)):
                    for sign in (-1, 1):
                        self.check_case(sign*n, d)

    def test_random_fraction_oracle(self):
        rng = random.Random(161047)
        maximum = dict(stages=0, initial_shift_byte_steps=0, compare_byte_steps=0,
                       subtract_byte_steps=0, right_shift_byte_steps=0)
        total = dict(maximum)
        for _ in range(5000):
            d = rng.randrange(1, 1 << 47)
            n = rng.randrange(-2000*d, 2000*d+1)
            counts = self.check_case(n, d)
            for k, v in counts.items():
                maximum[k] = max(maximum[k], v)
                total[k] += v
        self.__class__.operations = dict(synthetic_cases=5000, maximum=maximum, total=total)

    def test_convex_gain_and_separate_native_quarter(self):
        # Cancellation is exact before division; g/4 is a distinct truncation.
        for gains, weights in [([-400, 2000], [5, 1]), ([-400, 2000], [4, 1]),
                               ([-400, 2000], [6, 1]), ([-4, -1], [2, 1])]:
            n, d = sum(g*w for g, w in zip(gains, weights)), sum(weights)
            self.check_case(n, d)
            g, _ = quotient(encode(abs(n)), encode(d), n < 0)
            self.assertEqual(trunc(Fraction(g, 4)), int(g/4))
        self.assertEqual(trunc(Fraction(-3, 4)), 0)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BoundedDivision)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        Path(__file__).with_name('operations.json').write_text(json.dumps(BoundedDivision.operations, indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
