"""Unified gateway entrypoint and bounded strict JSON parsing utility."""
import json
import math
def reject_duplicate(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise ValueError('duplicate JSON key')
        out[k] = v
    return out

def finite_float(text):
    value=float(text)
    if not math.isfinite(value) or abs(value)>9007199254740991: raise ValueError('nonfinite or oversized number')
    return value

def bounded_int(text):
    if len(text)>17: raise ValueError('oversized integer')
    value=int(text)
    if abs(value)>9007199254740991: raise ValueError('oversized integer')
    return value

def strict_json(raw,maximum=8192):
    if not isinstance(raw,(str,bytes,bytearray)) or len(raw)>maximum: raise ValueError('invalid payload size/type')
    text=raw.decode('utf-8') if isinstance(raw,(bytes,bytearray)) else raw
    depth=0;quoted=False;escaped=False
    for ch in text:
        if quoted:
            if escaped: escaped=False
            elif ch=='\\': escaped=True
            elif ch=='"': quoted=False
        elif ch=='"': quoted=True
        elif ch in '{[':
            depth+=1
            if depth>32: raise ValueError('excessive JSON nesting')
        elif ch in '}]':
            depth-=1
            if depth<0: raise ValueError('unbalanced JSON')
    try:
        return json.loads(text,object_pairs_hook=reject_duplicate,parse_float=finite_float,
            parse_int=bounded_int,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    except (RecursionError,OverflowError) as error:
        raise ValueError('excessive JSON structure') from error


def main():
    from runtime import main as run
    run()

if __name__ == '__main__':
    main()
