
import sys,os,json,traceback
sys.path.insert(0,sys.argv[1]); import tparse
D=sys.argv[2]; out={}
for i,fn in enumerate(sorted(os.listdir(D))):
    if not fn.endswith('.pdf'): continue
    try: out[fn[:-4]]=tparse.parse(D+'/'+fn)
    except Exception as e: out[fn[:-4]]={'error':traceback.format_exc()[-400:]}
    if i%50==0: print(i,flush=True)
json.dump(out,open(sys.argv[3],'w')); print('DONE',len(out),flush=True)
