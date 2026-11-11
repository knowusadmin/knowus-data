#!/usr/bin/env python3
"""Text of every captured printed sample ballot -> sbtxt/<name>.txt.gz (raw text + layout text), as the NC pipeline reads it.
Usage: pdftext.py WORKDIR ZIP_OR_DIR [...]   (archive names carry a 5-digit capture prefix, removed here)"""
import gzip, os, re, subprocess, sys, tempfile, zipfile, concurrent.futures as cf
work = sys.argv[1]; os.makedirs(f'{work}/sbtxt', exist_ok=True)
items = []
for src in sys.argv[2:]:
    if os.path.isdir(src):
        items += [(os.path.join(src, f), None) for f in sorted(os.listdir(src)) if f.lower().endswith('.pdf')]
    else:
        z = zipfile.ZipFile(src); items += [(n, src) for n in z.namelist() if n.lower().endswith('.pdf')]
def one(it):
    name, zsrc = it
    base = re.sub(r'^\d{5}-', '', os.path.basename(name))[:-4]
    out = f'{work}/sbtxt/{base}.txt.gz'
    if os.path.exists(out): return 'skip'
    with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
        tmp.write(zipfile.ZipFile(zsrc).read(name) if zsrc else open(name, 'rb').read()); tmp.flush()
        t1 = subprocess.run(['timeout', '-k', '5', '60', 'pdftotext', tmp.name, '-'], capture_output=True, text=True, timeout=70).stdout
        t2 = subprocess.run(['timeout', '-k', '5', '60', 'pdftotext', '-layout', tmp.name, '-'], capture_output=True, text=True, timeout=70).stdout
    if not t1.strip(): return 'no text (scanned image?)'
    with gzip.open(out, 'wt') as f: f.write(t1 + '\n\f=====LAYOUT=====\f\n' + t2)
    return 'ok'
st = {}
with cf.ThreadPoolExecutor(3) as ex:
    for r in ex.map(one, items): st[r] = st.get(r, 0) + 1
print('pdftext', st, flush=True)
