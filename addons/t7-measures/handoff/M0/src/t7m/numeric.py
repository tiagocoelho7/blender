"""Exact represented inputs and dyadic outward enclosures; Python standard library."""
from fractions import Fraction as F
from decimal import Decimal
from math import isfinite, isqrt
from contextvars import ContextVar
import struct

class Refusal(ValueError):
    pass

INPUT_BITS = 2048
WORK_BITS = 4096
MAX_STEPS = 2_000_000
_meter = ContextVar('t7m_meter', default=None)

def check(x):
    meter = _meter.get()
    if meter is not None:
        meter[0] += 1
        if meter[0] > MAX_STEPS:
            raise Refusal('EXACT_OPERATION_BUDGET')
    if max(x.numerator.bit_length(), x.denominator.bit_length()) > WORK_BITS:
        raise Refusal('EXACT_BIT_BUDGET')
    return x

def number(x):
    # Reject bool, subclasses, strings and custom conversion hooks.
    if type(x) is float:
        if not isfinite(x):
            raise Refusal('NONFINITE')
        x = F(*x.as_integer_ratio())
    elif type(x) is Decimal:
        if not x.is_finite() or len(x.as_tuple().digits) > 400 or abs(x.as_tuple().exponent) > 400:
            raise Refusal('DECIMAL_RANGE')
        x = F(x)
    elif type(x) is int:
        if x.bit_length() > INPUT_BITS:
            raise Refusal('INPUT_BITS')
        x = F(x)
    elif type(x) is not F:
        raise Refusal('UNSUPPORTED_NUMBER')
    if max(x.numerator.bit_length(), x.denominator.bit_length()) > INPUT_BITS:
        raise Refusal('INPUT_BITS')
    return x

def root_bounds(x, bits=192):
    """Exact dyadic enclosure, no float overflow; x is a nonnegative rational."""
    x = check(x)
    if x < 0 or type(bits) is not int or not 0 <= bits <= 256:
        raise Refusal('SQRT_DOMAIN')
    a, b = isqrt(x.numerator), isqrt(x.denominator)
    if a*a == x.numerator and b*b == x.denominator:
        return F(a,b), F(a,b)
    # Relative scaling also encloses subnormal-scale and enormous finite inputs.
    exp = (x.numerator.bit_length() - x.denominator.bit_length()) // 2
    shift = bits - exp
    scale = F(2)**shift
    y = check(x*scale*scale)
    k = isqrt(y.numerator // y.denominator)
    lo = check(F(k)/scale)
    hi = lo if lo*lo == x else check(F(k+1)/scale)
    assert lo*lo <= x <= hi*hi
    return lo, hi

def half_even(x, p):
    y = x * 10**p
    k, r = divmod(y.numerator, y.denominator)
    if 2*r > y.denominator or (2*r == y.denominator and k % 2):
        k += 1
    return k

def decimal_text(k, p):
    if not p:
        return str(k)
    sign = '-' if k < 0 else ''
    digits = str(abs(k)).zfill(p+1)
    return sign + digits[:-p] + '.' + digits[-p:]

def outward_text(lo, hi, p):
    scale = 10**p
    l = (lo*scale).numerator // (lo*scale).denominator
    u = -((-hi*scale).numerator // (-hi*scale).denominator)
    return decimal_text(l,p), decimal_text(u,p)

def f32_radius(x):
    """Half largest adjacent binary32 step. Refuse non-binary32 source values."""
    try:
        v = float(x)
        raw = struct.pack('>f', v)
        observed = struct.unpack('>f', raw)[0]
    except (ValueError, OverflowError, struct.error):
        raise Refusal('BINARY32_RANGE')
    if not isfinite(observed) or F.from_float(observed) != x:
        raise Refusal('BINARY32_SOURCE_REQUIRED_FOR_P')
    bits = struct.unpack('>I', raw)[0] & 0x7fffffff
    if bits == 0:
        return F(1,2**150)
    if bits >= 0x7f7fffff:
        raise Refusal('BINARY32_NONFINITE_NEIGHBOR')
    a = F.from_float(abs(observed))
    prev = F.from_float(struct.unpack('>f', struct.pack('>I', bits-1))[0])
    nxt = F.from_float(struct.unpack('>f', struct.pack('>I', bits+1))[0])
    return max(a-prev, nxt-a)/2
