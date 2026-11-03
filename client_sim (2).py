"""Firebase FALSO en memoria para probar el CLIENTE (no las reglas). Reconstruido: el original no se adjuntó."""
import json
from PIL import Image  # noqa
RESULTS = []
ORIG_A, ORIG_B = "595983897999", "595972614198"   # Alito Mayorista / Top Level Mayorista
GHOST_NUM = "595900000001"
NEW_UID = "NewBizUidNewBizUidNewBiz1234"
HID_UID = "HidBizUidHidBizUidHidBiz1234"

def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(("  PASA  " if ok else "  FALLA ") + name + ("" if ok else "  -> " + str(detail)[:300]))

def user(uid):
    return {"uid": uid, "email": uid[:6].lower() + "@test.com", "emailVerified": True, "displayName": ""}

def seed_base(extra):
    st = {
        "businesses/" + NEW_UID: {"rk": NEW_UID, "n": "Tienda Nueva SRL", "c": "Asunción", "cs": ["Asunción"], "k": ["Tecnología"], "d": "Accesorios", "m": "Desde 5", "a": "", "ig": "", "web": "", "w": "595981111222", "sh": "pais", "status": "published", "publishedAt": {"__ts": 1000}, "updatedAt": {"__ts": 1000}},
        "businesses/" + HID_UID: {"rk": HID_UID, "n": "Oculto SA", "c": "Asunción", "cs": ["Asunción"], "k": ["Tecnología"], "d": "Oculto", "m": "", "a": "", "ig": "", "web": "", "w": "595981111333", "sh": "pais", "status": "hidden", "publishedAt": {"__ts": 1000}, "updatedAt": {"__ts": 1000}},
    }
    st.update(extra); return st

INIT = r"""
(()=>{
const ST=%STORE%, USR=%USR%, calls=[];
function TS(ms){return{__t:1,ms:ms,toMillis(){return ms},toDate(){return new Date(ms)}}}
function rev(v){if(v&&typeof v==='object'){if('__ts' in v&&Object.keys(v).length===1)return TS(v.__ts);for(const k in v)v[k]=rev(v[k])}return v}
for(const k in ST)ST[k]=rev(ST[k]);
const SRV={__srv:1};
function res(d){const o={};for(const k in d)o[k]=(d[k]&&d[k].__srv)?TS(Date.now()):d[k];return o}
const ref=(db,...seg)=>{const p=seg.join('/');return{path:p,id:seg[seg.length-1]}};
const snap=(p)=>({id:p.split('/').pop(),exists:()=>p in ST,data:()=>ST[p]?Object.assign({},ST[p]):undefined});
window.__FB={store:ST,calls:calls};
window.__API={
 initializeApp:()=>({}),getAuth:()=>({}),getFirestore:()=>({}),
 onAuthStateChanged:(a,cb)=>{setTimeout(()=>cb(USR?Object.assign({reload:async()=>{},getIdToken:async()=>'t'},USR):null),30);return()=>{}},
 signOut:async()=>{},signInWithEmailAndPassword:async()=>{throw{code:'auth/invalid-credential'}},createUserWithEmailAndPassword:async()=>{throw{code:'auth/x'}},
 sendEmailVerification:async()=>{},sendPasswordResetEmail:async()=>{},updateProfile:async()=>{},
 doc:ref,collection:ref,serverTimestamp:()=>SRV,deleteField:()=>({__del:1}),
 where:(f,op,v)=>({f,op,v}),query:(c,...w)=>({path:c.path,w}),
 getDoc:async(r)=>{calls.push({fn:'getDoc',path:r.path});return snap(r.path)},
 getDocs:async(q)=>{const base=q.path;calls.push({fn:'getDocs',path:base,w:q.w||[]});
   const ids=Object.keys(ST).filter(k=>k.startsWith(base+'/')&&k.split('/').length===base.split('/').length+1);
   const docs=ids.filter(k=>(q.w||[]).every(c=>ST[k][c.f]===c.v)).map(k=>snap(k));return{docs,size:docs.length,empty:!docs.length,forEach:f=>docs.forEach(f)}},
 setDoc:async(r,d)=>{calls.push({fn:'setDoc',path:r.path,data:Object.assign({},d)});ST[r.path]=res(d)},
 updateDoc:async(r,d)=>{calls.push({fn:'updateDoc',path:r.path});ST[r.path]=Object.assign(ST[r.path]||{},res(d))},
 addDoc:async(c,d)=>{const p=c.path+'/a'+Date.now();calls.push({fn:'addDoc',path:p});ST[p]=res(d);return{id:p.split('/').pop()}},
 deleteDoc:async(r)=>{calls.push({fn:'deleteDoc',path:r.path});delete ST[r.path]},
 getCountFromServer:async()=>({data:()=>({count:0})}),
 writeBatch:()=>{const o=[];return{set:(r,d)=>o.push(()=>window.__API.setDoc(r,d)),update:(r,d)=>o.push(()=>window.__API.updateDoc(r,d)),delete:(r)=>o.push(()=>window.__API.deleteDoc(r)),commit:async()=>{for(const f of o)await f()}}},
 runTransaction:async(db,f)=>f({get:async(r)=>snap(r.path),set:()=>{},update:()=>{}})
};
try{localStorage.setItem('mp_nostats','1')}catch(e){}
})();
"""
MOD = "const A=window.__API;export const "+",".join("%s=A.%s"%(k,k) for k in
  "initializeApp getAuth getFirestore onAuthStateChanged signOut signInWithEmailAndPassword createUserWithEmailAndPassword sendEmailVerification sendPasswordResetEmail updateProfile doc collection serverTimestamp deleteField where query getDoc getDocs setDoc updateDoc addDoc deleteDoc getCountFromServer writeBatch runTransaction".split())+";"

def make_page(b, url, store=None, usr=None, viewport=(390, 800), extra_init="", ctx_kwargs=None):
    ctx = b.new_context(viewport={"width": viewport[0], "height": viewport[1]}, **(ctx_kwargs or {}))
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    ctx.route("**/*", lambda r: r.fulfill(status=200, content_type="text/javascript", body=MOD) if "gstatic.com/firebasejs" in r.request.url
              else (r.continue_() if r.request.url.startswith(("http://localhost", "http://127.0.0.1", "data:")) else r.abort()))
    ctx.add_init_script(INIT.replace("%STORE%", json.dumps(store or seed_base({}))).replace("%USR%", json.dumps(usr)) + extra_init)
    pg.goto(url); return ctx, pg, errs, None

def wait_catalog(pg, n=13):
    pg.wait_for_function("document.querySelectorAll('#list .card').length>=%d" % n, timeout=15000); pg.wait_for_timeout(300)

def calls(pg, fn, prefix):
    return [c for c in pg.evaluate("__FB.calls") if c["fn"] == fn and c["path"].startswith(prefix)]
