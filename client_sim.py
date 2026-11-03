"""
Pruebas del CLIENTE (la página HTML) con un Firebase FALSO en memoria.
NO prueban las reglas de Firestore (eso lo hace rules.test.js con el emulador).
Uso:  python3 client_sim.py http://localhost:8765/index_v9_1_experimental.html [otra_version.html ...]
Requiere: pip install playwright && playwright install chromium, y un servidor local (python3 -m http.server 8765).
"""
import sys, json, time, datetime
from playwright.sync_api import sync_playwright

NEW_UID   = "AbCdEfGhIjKlMnOpQrStUvWxYz12"   # negocio nuevo publicado
HID_UID   = "HiddenBizUidHiddenBizUid1234"   # negocio nuevo OCULTO (status hidden)
GHOST_UID = "GhostUidGhostUidGhostUid1234"   # no existe
ORIG_A    = "595983897999"                    # Alito (original)
ORIG_B    = "595972614198"                    # Top Level (original)
GHOST_NUM = "595900000000"                    # número que no es de ningún negocio

FAKE = {
"firebase-app.js": "export const initializeApp=(c)=>({c});export const getApp=()=>({});",
"firebase-auth.js": """
const FB=globalThis.__FB;
export const getAuth=()=>({get currentUser(){return FB.user}});
export const onAuthStateChanged=(a,cb)=>{FB.cbs.push(cb);setTimeout(()=>cb(FB.user),0);return()=>{}};
export const signOut=async()=>{FB.user=null;FB.cbs.forEach(c=>c(null))};
const no=async()=>{throw {code:'auth/operation-not-allowed'}};
export const createUserWithEmailAndPassword=no,signInWithEmailAndPassword=no,sendPasswordResetEmail=no,sendEmailVerification=async()=>{},updateProfile=async()=>{};
""",
"firebase-firestore.js": """
const FB=globalThis.__FB;
const P=(s)=>s.join('/');
const wrap=(v)=>{if(v&&typeof v==='object'){if(v.__ts!==undefined)return{toMillis:()=>v.__ts,toDate:()=>new Date(v.__ts)};if(Array.isArray(v))return v.map(wrap);const o={};for(const k in v)o[k]=wrap(v[k]);return o}return v};
const snap=(path)=>{const has=Object.prototype.hasOwnProperty.call(FB.store,path);return{id:path.split('/').pop(),ref:{path},exists:()=>has,data:()=>has?wrap(FB.store[path]):undefined}};
export const getFirestore=()=>({});
export const doc=(db,...s)=>({path:P(s),id:s[s.length-1]});
export const collection=(db,...s)=>({path:P(s),isCol:true});
export const where=(f,op,v)=>({f,op,v});
export const query=(col,...cons)=>({col,cons});
export const serverTimestamp=()=>({__sv:true});
export const getDoc=async(r)=>{FB.calls.push({op:'getDoc',path:r.path});return snap(r.path)};
const run=(q)=>{const col=q.col||q,cons=q.cons||[];const pre=col.path+'/';return Object.keys(FB.store).filter(k=>k.startsWith(pre)&&!k.slice(pre.length).includes('/')).filter(k=>cons.every(c=>c.op==='=='?FB.store[k][c.f]===c.v:true)).map(snap)};
export const getDocs=async(q)=>{const col=q.col||q;FB.calls.push({op:'getDocs',path:col.path});const d=FB.delay[col.path]||0;if(d)await new Promise(r=>setTimeout(r,d));const docs=run(q);return{docs,size:docs.length,empty:!docs.length,forEach:(f)=>docs.forEach(f)}};
export const getCountFromServer=async(q)=>({data:()=>({count:run(q).length})});
export const setDoc=async(r,data)=>{FB.calls.push({op:'setDoc',path:r.path,data:JSON.parse(JSON.stringify(data))});
  if(r.path.startsWith('statEvents/')&&Object.prototype.hasOwnProperty.call(FB.store,r.path))throw{code:'permission-denied'};
  const o={};for(const k in data)o[k]=(data[k]&&data[k].__sv)?{__ts:Date.now()}:data[k];FB.store[r.path]=o};
export const deleteDoc=async(r)=>{FB.calls.push({op:'deleteDoc',path:r.path});delete FB.store[r.path]};
export const addDoc=async()=>({id:'x'}),updateDoc=async()=>{},deleteField=()=>({}),writeBatch=()=>({set(){},update(){},delete(){},commit:async()=>{}}),runTransaction=async()=>{};
"""
}

def user(uid, role="buyer", email=None):
    return {"uid": uid, "email": email or (uid[:6].lower()+"@test.com"), "emailVerified": True, "displayName": "Usuario Prueba"}

def seed_base(extra=None):
    st = {
      "businesses/"+NEW_UID: {"n":"Tienda Nueva SRL","c":"Asunción","cs":["Asunción"],"k":["Tecnología"],"d":"Productos varios de prueba","m":"","a":"","ig":"tiendanueva","web":"","w":"595981123456","sh":"pais","status":"published","publishedAt":{"__ts":1000}},
      "businesses/"+HID_UID: {"n":"Oculto SA","c":"Asunción","cs":["Asunción"],"k":["Tecnología"],"d":"Negocio oculto por el administrador","m":"","a":"","ig":"","web":"","w":"595982222222","sh":"pais","status":"hidden","publishedAt":{"__ts":1001}},
      # publicado pero con el WhatsApp de un original (debe descartarse) y otro con WhatsApp inválido
      "businesses/ImpostorUidImpostorUid123": {"n":"Impostor","c":"Asunción","cs":["Asunción"],"k":["Tecnología"],"d":"Usa el WhatsApp de un original","m":"","a":"","ig":"","web":"","w":ORIG_A,"sh":"pais","status":"published","publishedAt":{"__ts":1002}},
      "businesses/BadNumberUidBadNumberUid12": {"n":"Numero malo","c":"Asunción","cs":["Asunción"],"k":["Tecnología"],"d":"WhatsApp inválido","m":"","a":"","ig":"","web":"","w":"123","sh":"pais","status":"published","publishedAt":{"__ts":1003}},
    }
    st.update(extra or {}); return st

def make_page(browser, base_url, store=None, usr=None, delay=None, qs=""):
    ctx = browser.new_context(viewport={"width":390,"height":900})
    ctx.set_default_timeout(8000)
    reqs=[]
    def handle(route):
        name = route.request.url.split('/')[-1]
        reqs.append(name)
        route.fulfill(status=200, content_type="application/javascript", headers={"access-control-allow-origin":"*"}, body=FAKE.get(name,"export{}"))
    ctx.route("https://www.gstatic.com/firebasejs/**", handle)
    ctx.route("https://wa.me/**", lambda r: r.abort()); ctx.route("https://www.instagram.com/**", lambda r: r.abort())
    pg = ctx.new_page(); errs=[]
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    init = "globalThis.__FB={store:%s,calls:[],cbs:[],user:%s,delay:%s};" % (
        json.dumps(store if store is not None else seed_base()), json.dumps(
            dict(usr, **{}) if usr else None), json.dumps(delay or {}))
    if usr:  # métodos del usuario falso
        init += "if(__FB.user){__FB.user.reload=async()=>{};__FB.user.getIdToken=async()=>'t';}"
    pg.add_init_script(init)
    pg.goto(base_url + qs); 
    return ctx, pg, errs, reqs

def wait_catalog(pg, n=13):
    pg.wait_for_function("document.querySelectorAll('#list .card').length>=%d"%n)
    pg.wait_for_timeout(300)

def calls(pg, op="setDoc", prefix=""):
    return pg.evaluate("__FB.calls.filter(c=>c.op==='%s'&&c.path.startsWith('%s'))"%(op,prefix))

def idx_of(pg, key):
    return pg.evaluate("P.findIndex(p=>String(p.rk||p.w)==='%s')"%key)

def click_link(pg, t, key):
    pg.evaluate("""([t,k])=>{const a=document.querySelector('a[data-t="'+t+'"][data-k="'+k+'"]');
      if(!a)throw new Error('no hay enlace '+t+' '+k);a.addEventListener('click',e=>e.preventDefault());a.click()}""",[t,key])
    pg.wait_for_timeout(250)

RESULTS=[]
def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail)); print(("  PASA   " if ok else "  FALLA  ")+name+(("  -> "+str(detail)) if detail else ""))

def run(base_url, b):
    print("\n=== %s ===" % base_url); is91 = "v9_1" in base_url
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")

    # C1 catálogo: 12 originales + 1 nuevo; sin duplicados; descarta duplicado de WhatsApp y número inválido
    ctx,pg,errs,reqs = make_page(b, base_url); wait_catalog(pg)
    names = pg.evaluate("[...document.querySelectorAll('#list .card .name')].map(e=>e.textContent)")
    check("C1 catálogo: 13 negocios (12 originales + 1 nuevo), sin duplicados", len(names)==13 and len(set(names))==13, len(names))
    check("C1b el negocio nuevo aparece; oculto, impostor (WhatsApp repetido) y número inválido NO", "Tienda Nueva SRL" in names and not any(x in names for x in ["Oculto SA","Impostor","Numero malo"]))
    check("C1c sin errores de JavaScript", not errs, errs)
    check("C1d App Check inerte: no se pide firebase-app-check.js", "firebase-app-check.js" not in reqs)
    ctx.close()

    # E1 visitante anónimo, negocio ORIGINAL (clave = WhatsApp)
    ctx,pg,errs,_ = make_page(b, base_url); wait_catalog(pg)
    pg.evaluate("openP(%d)"%idx_of(pg,ORIG_A)); pg.wait_for_timeout(250)
    ev = calls(pg,"setDoc","statEvents/")
    check("E1 original: la visita crea 1 evento 'view' con clave = WhatsApp", len(ev)==1 and ev[0]["data"]["key"]==ORIG_A and ev[0]["data"]["type"]=="view" and ev[0]["path"].startswith("statEvents/"+ORIG_A+"_view_"+day+"_"), [e["path"] for e in ev])
    pg.evaluate("closeM()"); pg.evaluate("openP(%d)"%idx_of(pg,ORIG_A)); pg.wait_for_timeout(200)
    check("E1b segunda visita el mismo día: no escribe otro evento", len(calls(pg,"setDoc","statEvents/"))==1)
    click_link(pg,"wa",ORIG_A); click_link(pg,"ig",ORIG_A)
    t=[e["data"]["type"] for e in calls(pg,"setDoc","statEvents/")]
    check("E1c clics en WhatsApp e Instagram del original se cuentan (view, wa, ig)", sorted(t)==["ig","view","wa"], t)
    ctx.close()

    # E2 negocio NUEVO (clave = uid)
    ctx,pg,errs,_ = make_page(b, base_url); wait_catalog(pg)
    pg.evaluate("openP(%d)"%idx_of(pg,NEW_UID)); pg.wait_for_timeout(250); click_link(pg,"wa",NEW_UID); click_link(pg,"ig",NEW_UID)
    ev = calls(pg,"setDoc","statEvents/")
    check("E2 nuevo: view + wa + ig con clave = uid del negocio", sorted(e["data"]["type"] for e in ev)==["ig","view","wa"] and all(e["data"]["key"]==NEW_UID for e in ev), [e["path"][:40] for e in ev])
    ctx.close()

    # E3 el dueño de un negocio NUEVO logueado no cuenta
    st = seed_base({"users/"+NEW_UID:{"name":"Dueño Nuevo","email":"dueno@test.com","role":"provider"}})
    ctx,pg,errs,_ = make_page(b, base_url, st, user(NEW_UID)); wait_catalog(pg); pg.wait_for_timeout(400)
    pg.evaluate("openP(%d)"%idx_of(pg,NEW_UID)); pg.wait_for_timeout(250); click_link(pg,"wa",NEW_UID)
    check("E3 dueño de negocio nuevo (uid == clave): 0 eventos propios", len(calls(pg,"setDoc","statEvents/"))==0)
    pg.evaluate("closeM()"); pg.evaluate("openP(%d)"%idx_of(pg,ORIG_B)); pg.wait_for_timeout(300)
    check("E3b ese mismo usuario SÍ cuenta al visitar a OTRO negocio", len(calls(pg,"setDoc","statEvents/"))==1)
    ctx.close()

    # E4 dueño de un ORIGINAL que además se registró con el mismo WhatsApp
    OWN="OwnerOfAlitoOwnerOfAlito1234"
    st = seed_base({"users/"+OWN:{"name":"Dueño Alito","email":"alito@test.com","role":"provider"},"businessRequests/"+OWN:{"whatsapp":ORIG_A,"name":"Alito Mayorista"}})
    ctx,pg,errs,_ = make_page(b, base_url, st, user(OWN)); wait_catalog(pg); pg.wait_for_timeout(500)
    pg.evaluate("openP(%d)"%idx_of(pg,ORIG_A)); pg.wait_for_timeout(500); click_link(pg,"wa",ORIG_A); pg.wait_for_timeout(300)
    n=len(calls(pg,"setDoc","statEvents/"))
    check("E4 dueño de un original (cuenta mayorista con su mismo WhatsApp) no cuenta sus propias visitas/clics", n==0, "eventos propios: %d"%n)
    ctx.close()

    # E5 comprador logueado cuenta normalmente
    st = seed_base({"users/BuyerUidBuyerUidBuyerUid1234":{"name":"Comprador Uno","email":"c@test.com","role":"buyer"}})
    ctx,pg,errs,_ = make_page(b, base_url, st, user("BuyerUidBuyerUidBuyerUid1234")); wait_catalog(pg); pg.wait_for_timeout(300)
    pg.evaluate("openP(%d)"%idx_of(pg,ORIG_A)); pg.wait_for_timeout(300)
    check("E5 un comprador logueado SÍ cuenta (no es dueño)", len(calls(pg,"setDoc","statEvents/"))==1)
    ctx.close()

    # E6 exclusión del dispositivo con ?nostats=1 (solo v9.1)
    if is91:
        ctx,pg,errs,_ = make_page(b, base_url, qs="?nostats=1"); wait_catalog(pg)
        pg.evaluate("openP(%d)"%idx_of(pg,ORIG_A)); pg.wait_for_timeout(300)
        a=len(calls(pg,"setDoc","statEvents/"))
        pg.goto(base_url); pg.evaluate("globalThis.__FB=globalThis.__FB||{}") ; 
        ctx.close()
        ctx,pg,errs,_ = make_page(b, base_url, qs="?nostats=1"); wait_catalog(pg)
        # persistencia: segunda carga SIN parámetro en el mismo contexto
        pg.goto(base_url); wait_catalog(pg); pg.evaluate("openP(%d)"%idx_of(pg,ORIG_A)); pg.wait_for_timeout(300)
        b2=len(calls(pg,"setDoc","statEvents/"))
        pg.goto(base_url+"?nostats=0"); wait_catalog(pg); pg.evaluate("openP(%d)"%idx_of(pg,ORIG_B)); pg.wait_for_timeout(300)
        c=len(calls(pg,"setDoc","statEvents/"))
        check("E6 ?nostats=1 excluye el dispositivo (y persiste); ?nostats=0 lo revierte", a==0 and b2==0 and c==1, (a,b2,c))
        ctx.close()

    # F1 favoritos: solo negocios válidos y publicados
    FUID="FavUserFavUserFavUserFav1234"
    fav = lambda k: {"users/%s/favorites/%s"%(FUID,k):{"key":k,"createdAt":{"__ts":5}}}
    extra={"users/"+FUID:{"name":"Fav Usuario","email":"f@test.com","role":"buyer"}}
    for k in [ORIG_A,NEW_UID,GHOST_NUM,HID_UID,GHOST_UID]: extra.update(fav(k))
    def open_favs(pg):
        pg.click("#acctBtn"); pg.wait_for_selector("[data-a=go-favs]"); pg.click("[data-a=go-favs]"); pg.wait_for_selector("#favBox")
    ctx,pg,errs,_ = make_page(b, base_url, seed_base(extra), user(FUID)); wait_catalog(pg); pg.wait_for_timeout(500)
    open_favs(pg); pg.wait_for_function("document.querySelectorAll('#favBox .fvi').length>0"); 
    items = pg.evaluate("[...document.querySelectorAll('#favBox .fvt b')].map(e=>e.textContent)")
    check("F1 favoritos guardados: 5 (2 válidos, 1 inexistente-número, 1 oculto, 1 uid inexistente) → la pantalla muestra SOLO los 2 válidos", sorted(items)==["Alito Mayorista","Tienda Nueva SRL"], items)
    hearts = pg.evaluate("[...document.querySelectorAll('#list .fav.on')].length")
    check("F1b corazones marcados en el catálogo: solo los válidos (2)", hearts==2, hearts)
    check("F1c no se escribió nada al mostrar favoritos (los huérfanos no se borran solos)", len(calls(pg,"deleteDoc"))==0 and len(calls(pg,"setDoc","users/"))==0)
    ctx.close()

    # F2 carrera: abrir Favoritos ANTES de que termine de cargar el catálogo publicado
    ctx,pg,errs,_ = make_page(b, base_url, seed_base(extra), user(FUID), delay={"businesses":1800}); pg.wait_for_timeout(700)
    open_favs(pg); pg.wait_for_timeout(500)
    early = pg.evaluate("[...document.querySelectorAll('#favBox .fvt b')].map(e=>e.textContent)")
    pg.wait_for_timeout(2300)
    late = pg.evaluate("[...document.querySelectorAll('#favBox .fvt b')].map(e=>e.textContent)")
    check("F2 favoritos abiertos con el catálogo aún cargando: al terminar de cargar aparece también el negocio nuevo", sorted(late)==["Alito Mayorista","Tienda Nueva SRL"], {"antes":early,"después":late})
    ctx.close()

    # F3 guardar y quitar favorito (negocio nuevo y original)
    ctx,pg,errs,_ = make_page(b, base_url, seed_base({"users/"+FUID:extra["users/"+FUID]}), user(FUID)); wait_catalog(pg); pg.wait_for_timeout(400)
    for k in [NEW_UID, ORIG_B]:
        pg.evaluate("document.querySelector('#list .fav[data-fk=\"%s\"]').click()"%k); pg.wait_for_timeout(250)
    sets=[c for c in calls(pg,"setDoc","users/%s/favorites/"%FUID)]
    shape_ok=all(sorted(c["data"].keys())==["createdAt","key"] and c["data"]["key"]==c["path"].split("/")[-1] for c in sets)
    check("F3 guardar favorito crea users/{uid}/favorites/{clave} con {key, createdAt} (original y nuevo)", len(sets)==2 and shape_ok, [c["path"].split("/")[-1][:14] for c in sets])
    pg.evaluate("document.querySelector('#list .fav[data-fk=\"%s\"]').click()"%NEW_UID); pg.wait_for_timeout(250)
    check("F3b tocar de nuevo el corazón lo quita (deleteDoc)", len(calls(pg,"deleteDoc","users/%s/favorites/%s"%(FUID,NEW_UID)))==1)
    ctx.close()

    # L1 enlaces compartidos ?p=
    ctx,pg,errs,_ = make_page(b, base_url, qs="?p="+ORIG_A); wait_catalog(pg)
    check("L1 ?p=<WhatsApp> abre la ficha del ORIGINAL", pg.evaluate("document.getElementById('modal').classList.contains('open')") and "Alito" in pg.inner_text("#sheet"))
    ctx.close()
    ctx,pg,errs,_ = make_page(b, base_url, delay={"businesses":900}, qs="?p="+NEW_UID); wait_catalog(pg); pg.wait_for_timeout(300)
    check("L2 ?p=<uid> abre la ficha del negocio NUEVO (cuando termina de cargar el catálogo)", pg.evaluate("document.getElementById('modal').classList.contains('open')") and "Tienda Nueva" in pg.inner_text("#sheet"))
    ctx.close()
    for label,key in [("oculto",HID_UID),("inexistente",GHOST_UID)]:
        ctx,pg,errs,_ = make_page(b, base_url, qs="?p="+key); wait_catalog(pg); pg.wait_for_timeout(500)
        opened = pg.evaluate("document.getElementById('modal').classList.contains('open')")
        toast = pg.evaluate("(document.getElementById('mpToast')||{}).textContent||''")
        check("L3 ?p=<%s>: no abre ficha%s"%(label," y avisa que no está disponible" if is91 else ""), (not opened) and ((("no está disponible" in toast) if is91 else True)), {"abrió":opened,"aviso":toast})
        ctx.close()
    ctx,pg,errs,_ = make_page(b, base_url, qs="?p=%3Cscript%3E"); wait_catalog(pg); pg.wait_for_timeout(300)
    check("L4 ?p= con basura se ignora (sin ficha, sin aviso, sin errores)", not pg.evaluate("document.getElementById('modal').classList.contains('open')") and not (pg.evaluate("(document.getElementById('mpToast')||{}).textContent||''")) and not errs, errs)
    ctx.close()

if __name__=="__main__":
    urls=sys.argv[1:] or ["http://localhost:8765/index_v9_1_experimental.html"]
    with sync_playwright() as p:
        b=p.chromium.launch()
        for u in urls:
            RESULTS.clear(); run(u,b)
            ok=sum(1 for r in RESULTS if r[1]); print("\nRESUMEN %s: %d/%d pasan"%(u.split('/')[-1],ok,len(RESULTS)))
        b.close()
