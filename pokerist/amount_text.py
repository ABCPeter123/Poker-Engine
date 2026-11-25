"""Parse chip labels without silently repairing uncertain characters."""
import re
from decimal import Decimal, InvalidOperation

MAX_CHIPS=2**53-1
def number_text(text):
    if not isinstance(text,str):
        return None
    s=text.strip().upper().replace("\u00a0"," ").replace("\u202f"," ")
    # A detached suffix is common in OCR. Do not concatenate arbitrary digits.
    compact=re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)\s*([KM])\.?",s)
    if compact:
        digits,unit=compact.groups()
        digits=digits.replace(",",".")
        # Comma with exactly three decimals is ambiguous with grouping.
        if "," in compact[1] and len(compact[1].split(",")[1])==3:
            return None
        try:
            factor={"K":1000,"M":1000000}[unit]
            amount=Decimal(digits)*factor
            if amount!=amount.to_integral_value() or not 0<=amount<=MAX_CHIPS:
                return None
            decimals=len(digits.partition(".")[2])
            return {"display":text,"value":int(amount),"approximate":True,
                    "display_step":str(Decimal(factor).scaleb(-decimals)),"verified":False}
        except (InvalidOperation,ValueError,OverflowError):
            return None
    if re.fullmatch(r"[0-9]+",s):
        digits=s
    elif re.fullmatch(r"[0-9]{1,3}(?: [0-9]{3})+",s):
        digits=s.replace(" ","")
    elif re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+",s):
        digits=s.replace(",","")
    else:
        return None
    if len(digits)>16:
        return None
    amount=int(digits)
    return {"display":text,"value":amount,"approximate":False,"verified":False} if amount<=MAX_CHIPS else None
