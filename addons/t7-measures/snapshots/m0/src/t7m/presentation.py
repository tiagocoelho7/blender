"""Policy only: a supplied interval is not itself proof of geometric provenance."""
from dataclasses import dataclass
from fractions import Fraction as F
from .numeric import number, half_even, outward_text, decimal_text, Refusal

@dataclass(frozen=True)
class Certificate:
    lo: F
    hi: F
    quantity: str = 'distance'
    approximate: bool = False
    contact_proven: bool = False
    nominal_allowed: bool = True
    reference: tuple | None = None

def publish(c, p=3, unit='mm', nominal=None):
    """Pure formatter; external certificates are caller assertions, not verified geometry."""
    try:
        if type(c) is not Certificate or type(p) is not int or not 0<=p<=6:
            raise Refusal('PRESENTATION_INPUT')
        if unit not in ('mm','BU','mm2','BU2') or c.quantity not in ('distance','area','length'):
            raise Refusal('PRESENTATION_UNIT')
        if (c.quantity=='area') != (unit in ('mm2','BU2')):
            raise Refusal('PRESENTATION_DIMENSION')
        if any(type(v) is not bool for v in (c.approximate,c.contact_proven,c.nominal_allowed)):
            raise Refusal('PRESENTATION_BOOL')
        lo,hi = number(c.lo),number(c.hi)
        if not 0<=lo<=hi: raise Refusal('BOUNDS')
        if nominal is not None:
            value = number(nominal)
            if not lo<=value<=hi: raise Refusal('NOMINAL_CONTRADICTION')
        else: value = None
        ref = None
        if c.reference is not None:
            if type(c.reference) is not tuple or len(c.reference)!=2: raise Refusal('REFERENCE')
            rl,ru = map(number,c.reference)
            if not lo<=rl<=ru<=hi: raise Refusal('REFERENCE_CONTRADICTION')
            ref = (rl,ru)
        if c.contact_proven and (c.approximate or c.quantity!='distance' or lo!=0 or hi!=0):
            raise Refusal('CONTACT_CONTRADICTION')
        bounds = outward_text(lo,hi,p)
        if c.contact_proven:
            return dict(state='CONTATO_CERTIFICADO',bounds=bounds,unit=unit,nominal='0',sub_q=False)
        if c.quantity=='area' and lo==0: raise Refusal('AREA_LOWER_NOT_POSITIVE')
        if c.quantity=='length' and hi==0:
            return dict(state='COMPRIMENTO_DEGENERADO',bounds=bounds,unit=unit,nominal='0',sub_q=False)
        if lo==0:
            return dict(state='INDETERMINADO_COM_FAIXA',bounds=bounds,unit=unit,nominal=None,sub_q=False)
        state = 'POSITIVO_CERTIFICADO'
        if c.approximate and c.quantity=='area' and not c.nominal_allowed:
            state = 'AREA_INDETERMINADA_POR_INCERTEZA_TOTAL'
        if c.approximate and c.quantity=='distance': state = 'POSITIVO_CERTIFICADO_COM_FAIXA'
        candidate = None
        if c.nominal_allowed:
            if ref is not None:
                if half_even(ref[0],p)==half_even(ref[1],p):
                    candidate = half_even(ref[0],p)
            elif value is not None:
                candidate = half_even(value,p)
        q = F(1,10**p)
        # A nominal reference must not advertise resolution finer than the P envelope.
        if c.approximate and hi-lo>q: candidate = None
        subq = candidate==0 and lo>0 and hi<q
        text = decimal_text(candidate,p) if candidate is not None and candidate!=0 else None
        return dict(state=state,bounds=bounds,unit=unit,nominal=text,sub_q=subq,
                    threshold=decimal_text(1,p) if subq else None,
                    approximate=c.approximate,positive_internally=True)
    except (Refusal,ArithmeticError,ValueError,TypeError,OverflowError) as e:
        return dict(state='INDETERMINADO_SEM_FAIXA',reason=str(e),nominal=None,bounds=None,sub_q=False)

def compare(a,b,p=3):
    """Strict ordering only; overlapping or touching bounds never prove equality."""
    lo1,hi1,lo2,hi2 = map(number,(a.lo,a.hi,b.lo,b.hi))
    if not (0<=lo1<=hi1 and 0<=lo2<=hi2): raise Refusal('COMPARISON_BOUNDS')
    order = -1 if hi1<lo2 else (1 if hi2<lo1 else None)
    fa,fb = outward_text(lo1,hi1,p),outward_text(lo2,hi2,p)
    # Detect apparent overlap using exact values of the decimal text, not floats.
    visible_overlap = max(F(fa[0]),F(fb[0]))<=min(F(fa[1]),F(fb[1]))
    return dict(order=order,rounded_overlap_warning=order is not None and visible_overlap)
