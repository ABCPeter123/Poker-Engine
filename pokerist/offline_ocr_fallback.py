"""Independent line OCR fallbacks for completed-image development audits."""
import io,math,re,subprocess
from PIL import Image,ImageOps
from amount_text import number_text

def single_word(image,exe,psm,alphabet):
    if not exe:return None
    with io.BytesIO() as buf:
        image.save(buf,format="PNG")
        try:
            result=subprocess.run([exe,"stdin","stdout","--psm",str(psm),"-c",
                "tessedit_char_whitelist="+alphabet,"tsv"],input=buf.getvalue(),
                capture_output=True,check=True,timeout=5)
        except (OSError,subprocess.SubprocessError):
            return None
    words=[]
    for line in result.stdout.decode("utf-8",errors="replace").splitlines()[1:]:
        c=line.split("\t",11)
        if len(c)==12 and c[0]=="5" and c[11].strip():
            try:confidence=float(c[10])
            except ValueError:return None
            if not math.isfinite(confidence):return None
            words.append((c[11].strip(),confidence))
    return words[0] if len(words)==1 else None

def amount_fallback(image,exe):
    p=ImageOps.invert(ImageOps.autocontrast(image.convert("L")))
    readings=[]
    for binary in (False,True):
        v=p.point(lambda x:255 if x>120 else 0) if binary else p
        v=ImageOps.expand(v.resize((v.width*4,v.height*4),Image.Resampling.LANCZOS),16,255)
        readings.append(single_word(v,exe,7,"0123456789.KM"))
    a,b=readings
    if not a or not b or a[0]!=b[0] or min(a[1],b[1])<10:return None
    text=a[0]
    return text if re.fullmatch(r"(?:[0-9]+|[0-9]+(?:\.[0-9]+)?[KM])",text) and number_text(text) is not None else None

def board_rank_fallback(image,x,exe):
    p=image.crop((x+1,244,x+33,281)).convert("L")
    p=ImageOps.expand(p.point(lambda v:0 if v<125 else 255).resize((128,148)),20,255)
    word=single_word(p,exe,13,"0123456789AJQK")
    if not word or word[1]<80:return None
    text=word[0]
    return "T" if text=="10" else text if len(text)==1 and text in "23456789AJQK" else None
