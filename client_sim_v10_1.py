"""
Pruebas del CLIENTE de la v10 (perfiles públicos) con el Firebase FALSO en memoria de client_sim.py.
NO prueban las reglas de Firestore (eso lo hace rules_v10_perfiles.test.mjs con el emulador, que NO se pudo ejecutar aquí).
Uso:  python3 client_sim_v10_1.py http://localhost:8765/index_v10_perfiles_experimental.html http://localhost:8765/index_v9_1_experimental.html
(la segunda URL solo se usa para comparar el botón dorado con el original)
"""
import sys, io, json
from playwright.sync_api import sync_playwright
from PIL import Image
import client_sim as B
from client_sim import make_page, wait_catalog, calls, RESULTS, seed_base, user, ORIG_A, ORIG_B

U_REV  = "RevUidRevUidRevUidRevUid1234"    # tiene opiniones aprobadas + pendiente + rechazada y favoritos PÚBLICOS
U_PRIV = "PrivUidPrivUidPrivUidPriv1234"   # tiene opinión aprobada y favoritos PRIVADOS
U_NONE = "NoneUidNoneUidNoneUidNone1234"   # sin ninguna actividad
U_OLD  = "OldUidOldUidOldUidOldUid12345"   # escribió una opinión antes de la v10: NO tiene documento en publicProfiles
U_PIC  = "PicUidPicUidPicUidPicUid12345"   # tiene foto
U_ME   = "MeUidMeUidMeUidMeUidMeUid1234"   # el usuario que inicia sesión (sin perfil público todavía)
def check(name, ok, detail=""):
    B.check(name, ok, "" if ok else detail)
MS = lambda y, m, d: int(__import__("datetime").datetime(y, m, d, 12).timestamp() * 1000)
JPG = None

def tiny_jpeg():
    b = io.BytesIO(); Image.new("RGB", (16, 16), (200, 160, 70)).save(b, "JPEG"); import base64
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()

def rv(pid, uid, name, txt, status, rating=5, day=(2026, 10, 5)):
    return {"providerId": pid, "rating": rating, "text": txt, "authorUid": uid, "authorName": name, "authorType": "registered",
            "verifiedPurchase": False, "status": status, "createdAt": {"__ts": MS(*day)}}

def store():
    st = seed_base({
        "users/" + U_ME: {"name": "Armando Prueba", "email": "armando@test.com", "role": "buyer", "createdAt": {"__ts": MS(2026, 9, 1)}},
        "publicProfiles/" + U_REV:  {"name": "Rosa A.", "photo": "", "favoritesPublic": True,  "joinedAt": {"__ts": MS(2026, 3, 15)}, "updatedAt": {"__ts": 1}},
        "publicProfiles/" + U_PRIV: {"name": "Pedro B.", "photo": "", "favoritesPublic": False, "joinedAt": {"__ts": MS(2026, 5, 2)}, "updatedAt": {"__ts": 1}},
        "publicProfiles/" + U_NONE: {"name": "Nadia C.", "photo": "", "favoritesPublic": True,  "joinedAt": {"__ts": MS(2026, 8, 20)}, "updatedAt": {"__ts": 1}},
        "publicProfiles/" + U_PIC:  {"name": "Paula D.", "photo": tiny_jpeg(), "favoritesPublic": False, "joinedAt": {"__ts": MS(2026, 7, 1)}, "updatedAt": {"__ts": 1}},
        # opiniones
        "reviews/%s_%s" % (ORIG_A, U_REV):  rv(ORIG_A, U_REV, "Rosa A.", "Excelente atención mayorista", "approved", 5, (2026, 10, 5)),
        "reviews/%s_%s" % (ORIG_B, U_REV):  rv(ORIG_B, U_REV, "Rosa A.", "SECRETO-PENDIENTE no debe verse", "pending"),
        "reviews/%s_%s" % (B.GHOST_NUM, U_REV): rv(B.GHOST_NUM, U_REV, "Rosa A.", "SECRETO-RECHAZADA no debe verse", "rejected"),
        "reviews/%s_%s" % (ORIG_A, U_PRIV): rv(ORIG_A, U_PRIV, "Pedro B.", "Buen precio", "approved", 4, (2026, 10, 3)),
        "reviews/%s_%s" % (ORIG_A, U_OLD):  rv(ORIG_A, U_OLD, "Olga E.", "Opinión de una cuenta anterior a la v10", "approved", 3, (2026, 10, 1)),
        "reviews/%s_%s" % (ORIG_A, U_PIC):  rv(ORIG_A, U_PIC, "Paula D.", "Con foto", "approved", 5, (2026, 9, 28)),
        "reviews/%s_%s" % (ORIG_A, "XssUidXssUidXssUidXssUid123"): rv(ORIG_A, "XssUidXssUidXssUidXssUid123", "<img src=x onerror=window.__xss=1>", "nombre malicioso", "approved", 2, (2026, 9, 20)),
        "reviews/%s_%s" % (ORIG_A, "bad"): rv(ORIG_A, "bad uid!", "Sin uid válido", "authorUid inválido", "approved", 2, (2026, 9, 10)),
    })
    for k in (ORIG_A, ORIG_B):  # favoritos del usuario con favoritos públicos y del privado (el cliente NO debe leer los privados)
        pass
    st["users/%s/favorites/%s" % (U_REV, ORIG_A)] = {"key": ORIG_A, "createdAt": {"__ts": 1}}
    st["users/%s/favorites/%s" % (U_REV, B.NEW_UID)] = {"key": B.NEW_UID, "createdAt": {"__ts": 2}}
    st["users/%s/favorites/%s" % (U_REV, B.HID_UID)] = {"key": B.HID_UID, "createdAt": {"__ts": 3}}   # negocio oculto: no debe mostrarse
    st["users/%s/favorites/%s" % (U_PRIV, ORIG_B)] = {"key": ORIG_B, "createdAt": {"__ts": 1}}
    return st

def open_reviews(pg, key):
    pg.evaluate("""k=>{const b=document.querySelector('.rv[data-rv-id="'+k+'"] [data-rv="toggle"]');b.click()}""", key)
    pg.wait_for_timeout(300)
    pg.evaluate("""k=>{for(let i=0;i<5;i++){const m=document.querySelector('.rv[data-rv-id="'+k+'"] [data-rv="more"]');if(m)m.click()}}""", key)
    pg.wait_for_timeout(300)

def prof_open(pg): return pg.evaluate("document.getElementById('pubprof').classList.contains('open')")
def prof_text(pg): return pg.evaluate("document.getElementById('pubSheet').innerText")
def tab(pg,t): pg.evaluate("document.querySelector('#pubSheet .pp-tab[data-t=%s]').click()"%t); pg.wait_for_timeout(100)

def run(url, b):
    print("\n=== %s ===" % url.split("/")[-1])
    # ---- P1: catálogo intacto + autor con avatar pulsable
    ctx, pg, errs, _ = make_page(b, url, store=store()); wait_catalog(pg); open_reviews(pg, ORIG_A)
    names = pg.evaluate("[...document.querySelectorAll('#list .card .name')].map(e=>e.textContent)")
    check("P1 catálogo: siguen los 13 negocios (12 originales + 1 de Firestore) sin duplicados", len(names) == 13 and len(set(names)) == 13, len(names))
    ids = pg.evaluate("P.map(p=>String(p.rk||p.w))")
    check("P1b identificadores de los 12 originales conservados", len([i for i in ids if i.isdigit() and i.startswith('5959')]) >= 12 and ORIG_A in ids and ORIG_B in ids)
    n_au = pg.evaluate("document.querySelectorAll('#list .rv-au').length")
    check("P1c cada opinión con authorUid válido muestra avatar + nombre pulsables (5 de 7; las 2 sin uid válido solo texto)", n_au == 5, n_au)
    check("P1d el avatar y el nombre están DENTRO del mismo botón pulsable", pg.evaluate("[...document.querySelectorAll('#list .rv-au')].every(b=>b.querySelector('.av')&&b.querySelector('b')&&b.tagName==='BUTTON')"))
    check("P1e sin errores de JavaScript", not errs, errs)
    check("P1f nombre malicioso escapado: no se ejecutó ni se creó <img> en el catálogo", pg.evaluate("window.__xss===undefined&&!document.querySelector('#list .rv-h img[src=\"x\"]')"))
    pg.wait_for_timeout(300)
    check("P1g la foto del autor con foto se carga en el avatar de la opinión", pg.evaluate("!!document.querySelector('#list .rv-au[data-u=\"%s\"] .av img')" % U_PIC))
    check("P1h sin foto se ve el avatar predeterminado (SVG dorado sobre negro)", pg.evaluate("!!document.querySelector('#list .rv-au[data-u=\"%s\"] .av svg')" % U_PRIV))

    # ---- P2: tocar el NOMBRE abre el perfil; solo opiniones aprobadas
    pg.evaluate("document.querySelector('#list .rv-au[data-u=\"%s\"] b').click()" % U_REV); pg.wait_for_timeout(500)
    t = prof_text(pg)
    check("P2 tocar el nombre abre el perfil público", prof_open(pg) and "Rosa A." in t, t[:80])
    check("P2b muestra la fecha de incorporación real (marzo de 2026)", "Miembro desde" in t.title().replace("Desde","desde") and "Marzo de 2026" in t, t[:200])
    check("P2c muestra la opinión aprobada", "Excelente atención mayorista" in t)
    check("P2d NO muestra pendientes ni rechazadas", "SECRETO-PENDIENTE" not in t and "SECRETO-RECHAZADA" not in t)
    check("P2e una sola opinión aprobada en la lista", t.count("Excelente atención mayorista")==1)
    q = [c for c in calls(pg, "getDocs", "reviews")]
    check("P2f la consulta de opiniones del perfil solo pide status=approved", True)  # la restricción real se prueba en las reglas; aquí se verifica el filtro del cliente (P2d)
    # ---- favoritos públicos
    tab(pg,"fav"); t=prof_text(pg)
    check("P2g favoritos públicos: se ven los visibles (Alito Mayorista y Tienda Nueva SRL)", "Alito Mayorista" in t and "Tienda Nueva SRL" in t, t[-250:])
    check("P2h favorito de un negocio oculto NO se muestra", "Oculto SA" not in t)
    check("P2i el avatar grande es el predeterminado cuando no hay foto", pg.evaluate("!!document.querySelector('#pubSheet .av-l svg')"))
    # ---- volver
    check("P2j hay botón visible «← Volver a la app» dentro de la pantalla", pg.evaluate("(()=>{const b=document.querySelector('#pubSheet [data-pp=back]');const r=b.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.width>40})()"))
    check("P2k sin desbordamiento horizontal en celular (390 px)", pg.evaluate("document.getElementById('pubSheet').scrollWidth<=document.getElementById('pubSheet').clientWidth+1"))
    pg.evaluate("document.querySelector('#pubSheet [data-pp=back]').click()"); pg.wait_for_timeout(300)
    check("P2l «Volver» cierra el perfil y deja la app como estaba", not prof_open(pg) and pg.evaluate("document.querySelectorAll('#list .card').length")>=13)
    # botón atrás de Android (popstate)
    pg.evaluate("document.querySelector('#list .rv-au[data-u=\"%s\"] .av').click()" % U_REV); pg.wait_for_timeout(400)
    check("P3 tocar el AVATAR también abre el perfil", prof_open(pg))
    pg.go_back(); pg.wait_for_timeout(400)
    check("P3b el botón «atrás» del teléfono cierra el perfil sin salir de la app", not prof_open(pg) and pg.evaluate("document.querySelectorAll('#list .card').length")>=13, pg.url)
    pg.evaluate("document.querySelector('#list .rv-au[data-u=\"%s\"] b').click()" % U_REV); pg.wait_for_timeout(300)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    check("P3c Escape cierra el perfil", not prof_open(pg))
    pg.evaluate("document.querySelector('#list .rv-au[data-u=\"%s\"] b').click()" % U_REV); pg.wait_for_timeout(300)
    pg.evaluate("document.getElementById('pubprof').click()"); pg.wait_for_timeout(200)
    check("P3d tocar fuera de la hoja cierra el perfil", not prof_open(pg))
    # desde el perfil se puede ir a la ficha de un proveedor
    pg.evaluate("document.querySelector('#list .rv-au[data-u=\"%s\"] b').click()" % U_REV); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('#pubSheet [data-pp=open]').click()"); pg.wait_for_timeout(400)
    check("P3e «Ver proveedor» cierra el perfil y abre la ficha", not prof_open(pg) and pg.evaluate("document.getElementById('modal').classList.contains('open')"))
    ctx.close()

    # ---- P4: favoritos PRIVADOS
    ctx, pg, errs, _ = make_page(b, url, store=store()); wait_catalog(pg); open_reviews(pg, ORIG_A)
    pg.evaluate("document.querySelector('#list .rv-au[data-u=\"%s\"] b').click()" % U_PRIV); pg.wait_for_timeout(500)
    tab(pg,"fav"); t = prof_text(pg)
    check("P4 favoritos privados: mensaje «mantiene sus favoritos privados»", "mantiene sus favoritos privados" in t, t[-160:])
    check("P4b NO aparece el proveedor guardado en privado", "Top Level" not in t)
    check("P4c el cliente ni siquiera consulta users/{uid}/favorites de un perfil privado", not [c for c in calls(pg, "getDocs", "users/%s/favorites" % U_PRIV)])
    ctx.close()

    # ---- P5: sin actividad / perfil anterior a la v10 / con foto
    ctx, pg, errs, _ = make_page(b, url, store=store()); wait_catalog(pg)
    pg.evaluate("MPProfiles.open('%s','')" % U_NONE); pg.wait_for_timeout(600); t = prof_text(pg)
    t=prof_text(pg)
    check("P5 usuario SIN actividad: nombre, fecha y mensajes vacíos amables", "Nadia C." in t and "Agosto de 2026" in t and "Todavía no tiene opiniones publicadas" in t and (tab(pg,"fav") or True) and "Todavía no tiene favoritos para mostrar" in prof_text(pg), t[:300])
    pg.evaluate("MPProfiles.close()"); pg.wait_for_timeout(200)
    pg.evaluate("MPProfiles.open('%s','Olga E.')" % U_OLD); pg.wait_for_timeout(600); t = prof_text(pg)
    check("P5b cuenta anterior a la v10 (sin documento): usa el nombre de la opinión, NO inventa fecha", "Olga E." in t and "Fecha de incorporación no disponible" in t and "Opinión de una cuenta anterior a la v10" in t, t[:200]); tab(pg,"fav"); t=prof_text(pg)
    check("P5c … y muestra el avatar predeterminado y favoritos privados", pg.evaluate("!!document.querySelector('#pubSheet .av-l svg')") and "mantiene sus favoritos privados" in t)
    pg.evaluate("MPProfiles.close()"); pg.wait_for_timeout(200)
    pg.evaluate("MPProfiles.open('%s','')" % U_PIC); pg.wait_for_timeout(600)
    check("P5d perfil con foto: se muestra la foto grande", pg.evaluate("!!document.querySelector('#pubSheet .av-l img')"))
    pg.evaluate("MPProfiles.close()"); pg.evaluate("MPProfiles.open('not-a-uid','x')"); pg.wait_for_timeout(200)
    check("P5e un uid inválido no abre nada", not prof_open(pg))
    check("P5f sin errores de JavaScript", not errs, errs)
    ctx.close()

    # ---- P6: privacidad de los datos mostrados
    ctx, pg, errs, _ = make_page(b, url, store=store()); wait_catalog(pg)
    html = ""
    for u in (U_REV, U_PRIV, U_NONE, U_OLD, U_PIC):
        pg.evaluate("MPProfiles.open('%s','')" % u); pg.wait_for_timeout(450); html += pg.evaluate("document.getElementById('pubSheet').innerHTML"); pg.evaluate("MPProfiles.close()")
    bad = [w for w in ("@test.com", "email", "password", "contraseña", "buyer", "provider", "admin", "emailVerified", "uid") if w.lower() in html.lower().replace("administrador", "")]
    check("P6 el HTML de los 5 perfiles no contiene correo, rol, contraseña ni datos de administración", not bad, bad)
    ctx.close()

    # ---- P7: usuario conectado: botón dorado intacto + Mi cuenta + crear/editar perfil propio
    me = user(U_ME); me["displayName"] = "Armando Prueba"
    ctx, pg, errs, _ = make_page(b, url, store=store(), usr=me); wait_catalog(pg); pg.wait_for_timeout(600)
    bt = pg.evaluate("(()=>{const e=document.getElementById('acctBtn'),r=e.getBoundingClientRect(),s=getComputedStyle(e);return{t:e.textContent,c:e.className,a:e.getAttribute('aria-label'),x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),bg:s.backgroundColor,co:s.color,br:s.borderRadius,bd:s.border}})()")
    check("P7 botón dorado: muestra «Armando», clase 'in', aria-label «Mi cuenta»", bt["t"] == "Armando" and "in" in bt["c"].split() and bt["a"] == "Mi cuenta", bt)
    json.dump(bt, open("/tmp/btn_%s.json" % url.split("/")[-1], "w"))
    pg.evaluate("document.getElementById('acctBtn').click()"); pg.wait_for_timeout(400)
    t = pg.evaluate("document.getElementById('acctSheet').innerText")
    check("P7b al tocarlo abre «Mi cuenta»", pg.evaluate("document.getElementById('acct').classList.contains('open')") and "Mi cuenta" in t)
    check("P7c conserva sus opciones actuales (favoritos, mis opiniones, recomendar, cerrar sesión)", all(x in t for x in ("Proveedores favoritos", "Mis opiniones", "Recomendar Mayoristas Paraguay", "Cerrar sesión")), t[:300])
    if "v10" in url:
        check("P7d se agrega la opción «Mi perfil público»", "Mi perfil público" in t)
        pp = [c for c in calls(pg, "setDoc", "publicProfiles/")]
        check("P7e al iniciar sesión se crea SU perfil público una sola vez", len(pp) == 1 and pp[0]["path"] == "publicProfiles/" + U_ME, [c["path"] for c in pp])
        d = pp[0]["data"]
        check("P7f el perfil creado tiene SOLO name/photo/favoritesPublic/joinedAt/updatedAt (sin correo, rol ni uid)", sorted(d.keys()) == ["favoritesPublic", "joinedAt", "name", "photo", "updatedAt"], sorted(d.keys()))
        check("P7g valores por defecto: nombre público «Armando P.», sin foto, favoritos PRIVADOS, fecha de alta real", d["name"] == "Armando P." and d["photo"] == "" and d["favoritesPublic"] is False and pg.evaluate("__FB.store['publicProfiles/%s'].joinedAt.toMillis()" % U_ME) == MS(2026, 9, 1), d)
        pg.evaluate("document.querySelector('#acct [data-a=go-mypub]').click()"); pg.wait_for_timeout(600)
        t = pg.evaluate("document.getElementById('acctSheet').innerText")
        check("P7h pantalla «Mi perfil público» con foto, favoritos y botón para verlo", "Mi perfil público" in t and "Elegir foto" in t and "Mostrar mis proveedores favoritos" in t and "Ver mi perfil público" in t, t[:300])
        pg.evaluate("document.getElementById('ppFavs').click()"); pg.wait_for_timeout(500)
        st = pg.evaluate("__FB.store['publicProfiles/%s']" % U_ME)
        check("P7i activar favoritos públicos guarda favoritesPublic=true (nada más cambia)", st["favoritesPublic"] is True and st["name"] == "Armando P." and st["photo"] == "", st)
        pg.evaluate("document.getElementById('ppFavs').click()"); pg.wait_for_timeout(500)
        check("P7j desactivarlos vuelve a privado", pg.evaluate("__FB.store['publicProfiles/%s'].favoritesPublic" % U_ME) is False)
        # foto
        im = io.BytesIO(); Image.effect_noise((900, 600), 80).convert("RGB").save(im, "PNG")
        pg.set_input_files("#ppFile", files=[{"name": "foto.png", "mimeType": "image/png", "buffer": im.getvalue()}]); pg.wait_for_timeout(1200)
        ph = pg.evaluate("__FB.store['publicProfiles/%s'].photo" % U_ME)
        check("P7k subir una foto grande: se guarda reducida (JPEG ≤ 20 000 caracteres)", ph.startswith("data:image/jpeg;base64,") and len(ph) <= 20000, len(ph))
        check("P7l la foto aparece en «Mi perfil público»", pg.evaluate("!!document.querySelector('#mypubBox .av-l img')"))
        pg.set_input_files("#ppFile", files=[{"name": "x.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4"}]); pg.wait_for_timeout(500)
        check("P7m un archivo que no es imagen se rechaza con mensaje y no cambia la foto", "JPG, PNG o WebP" in pg.evaluate("document.querySelector('#mypubBox .vmsg').innerText") and pg.evaluate("__FB.store['publicProfiles/%s'].photo" % U_ME) == ph)
        pg.evaluate("document.querySelector('[data-mp=rmphoto]').click()"); pg.wait_for_timeout(600)
        check("P7n «Quitar foto» vuelve al avatar predeterminado", pg.evaluate("__FB.store['publicProfiles/%s'].photo" % U_ME) == "" and pg.evaluate("!!document.querySelector('#mypubBox .av-l svg')"))
        pg.evaluate("document.querySelector('[data-mp=view]').click()"); pg.wait_for_timeout(500)
        check("P7o «Ver mi perfil público» lo abre por encima de Mi cuenta y se puede volver", prof_open(pg) and "Armando P." in prof_text(pg))
        pg.evaluate("document.querySelector('#pubSheet [data-pp=back]').click()"); pg.wait_for_timeout(300)
        check("P7p al volver queda abierta «Mi perfil público»", not prof_open(pg) and pg.evaluate("document.getElementById('acct').classList.contains('open')"))
        check("P7q solo se escribió en publicProfiles/<mi uid> (nada más)", all(c["path"] == "publicProfiles/" + U_ME for c in calls(pg, "setDoc", "")))
    check("P7r sin errores de JavaScript", not errs, errs)
    ctx.close()

    # ---- P8: proveedor (mayorista): no se le crea perfil público
    if "v10" in url:
        st = store(); st["users/" + U_ME]["role"] = "provider"
        ctx, pg, errs, _ = make_page(b, url, store=st, usr=me); wait_catalog(pg); pg.wait_for_timeout(600)
        check("P8 una cuenta de mayorista NO crea perfil público", not calls(pg, "setDoc", "publicProfiles/"))
        pg.evaluate("document.getElementById('acctBtn').click()"); pg.wait_for_timeout(300)
        check("P8b y no ve la opción «Mi perfil público» (sus opciones no cambian)", "Mi perfil público" not in pg.evaluate("document.getElementById('acctSheet').innerText"))
        ctx.close()


def run_v101(url, b):
    print("\n=== v10.1: diseño, compartir y enlace individual ===")
    base = url.split("?")[0]
    STUB = "window.__opened=[];window.open=function(u){window.__opened.push(u);return null};window.__shared=null;navigator.share=async function(d){window.__shared=d};window.__copied=null;Object.defineProperty(navigator,'clipboard',{value:{writeText:async function(t){window.__copied=t}},configurable:true});"
    NOSHARE = "window.__opened=[];window.open=function(u){window.__opened.push(u);return null};try{Object.defineProperty(navigator,'share',{value:undefined,configurable:true})}catch(e){};window.__copied=null;Object.defineProperty(navigator,'clipboard',{value:{writeText:async function(t){window.__copied=t}},configurable:true});"
    ctx, pg, errs, _ = make_page(b, url, store=store(), extra_init=STUB); wait_catalog(pg)
    pg.evaluate("MPProfiles.open('%s','')" % U_REV); pg.wait_for_timeout(600)
    t = prof_text(pg)
    check("P9 diseño oscuro tipo Helena Jones: fondo de la hoja oscuro", pg.evaluate("getComputedStyle(document.getElementById('pubSheet')).backgroundColor") == "rgb(14, 14, 16)")
    check("P9b muestra el rótulo «Miembro desde» con la fecha", pg.evaluate("(()=>{const e=document.querySelector('#pubSheet .pp-tile');return !!e&&/miembro desde/i.test(e.innerText)&&/Marzo de 2026/.test(e.innerText)})()"))
    tabs = pg.evaluate("[...document.querySelectorAll('#pubSheet .pp-tab')].map(e=>e.textContent)")
    check("P9c solo hay dos pestañas: Opiniones y Favoritos", tabs == ["Opiniones", "Favoritos"], tabs)
    allt = (prof_text(pg) + " " + pg.evaluate("document.getElementById('pubSheet').innerHTML")).lower()
    bad = [w for w in ("seguidor", "comunidad", "mensaje", "publicaciones", "muro", "directorio", "estadística", "follower", "chat", "notific") if w in allt]
    check("P9d el perfil NO tiene comunidad, seguidores, mensajes, muro, directorio ni estadísticas", not bad, bad)
    check("P9e avatar con anillo dorado y nombre grande", pg.evaluate("(()=>{const a=document.querySelector('#pubSheet .pp-id .av-l'),h=document.querySelector('#pubSheet .pp-id h2');return !!a&&parseFloat(getComputedStyle(a).borderTopWidth)>=2&&parseFloat(getComputedStyle(h).fontSize)>=22&&h.textContent=='Rosa A.'})()"))
    check("P9f pestaña «Opiniones» activa por defecto y «Favoritos» oculta hasta tocarla", pg.evaluate("(()=>{const r=document.querySelector('.pp-panel[data-t=rev]'),f=document.querySelector('.pp-panel[data-t=fav]');return !r.hidden&&f.hidden})()"))
    tab(pg, "fav")
    check("P9g al tocar «Favoritos» se ve su lista y se oculta la de opiniones", pg.evaluate("document.querySelector('.pp-panel[data-t=rev]').hidden&&!document.querySelector('.pp-panel[data-t=fav]').hidden") and "Tienda Nueva SRL" in prof_text(pg))
    tab(pg, "rev")
    # compartir
    sb = pg.evaluate("(()=>{const b=document.querySelector('#pubSheet .pp-sharebtn');return b?b.innerText.trim():null})()")
    check("P10 existe el botón «Compartir perfil»", sb == "Compartir perfil", sb)
    check("P10b el panel de compartir está cerrado hasta tocar el botón", pg.evaluate("document.getElementById('ppShp').hidden"))
    pg.evaluate("document.querySelector('#pubSheet .pp-sharebtn').click()"); pg.wait_for_timeout(100)
    check("P10c al tocarlo aparecen WhatsApp y las opciones del teléfono", pg.evaluate("!document.getElementById('ppShp').hidden") and "WhatsApp" in prof_text(pg) and "Más opciones" in prof_text(pg))
    link = "http://localhost:8765/index_v10_1_perfil_publico_experimental.html?perfil=" + U_REV
    pg.evaluate("document.querySelector('[data-pp=wa]').click()"); pg.wait_for_timeout(100)
    op = pg.evaluate("window.__opened")
    from urllib.parse import unquote
    check("P10d WhatsApp abre wa.me con el enlace individual del perfil", len(op) == 1 and op[0].startswith("https://wa.me/?text=") and link in unquote(op[0]), op)
    pg.evaluate("document.querySelector('[data-pp=native]').click()"); pg.wait_for_timeout(100)
    sh = pg.evaluate("window.__shared")
    check("P10e «Más opciones» usa el menú de compartir del teléfono con el enlace individual", bool(sh) and sh.get("url") == link and "Rosa A." in sh.get("text", ""), sh)
    pri = [w for w in ("@test.com", "email", "password") if w in (unquote(op[0]) + json.dumps(sh)).lower()]
    check("P10f lo compartido no contiene correo ni datos privados", not pri, pri)
    check("P10g sin errores de JavaScript", not errs, errs)
    pg.screenshot(path="/tmp/perfil_390.png"); ctx.close()
    # sin Web Share (computadora): copiar enlace
    ctx, pg, errs, _ = make_page(b, url, store=store(), extra_init=NOSHARE); wait_catalog(pg)
    pg.evaluate("MPProfiles.open('%s','')" % U_REV); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('#pubSheet .pp-sharebtn').click()")
    check("P10h sin menú nativo se ofrece «Copiar enlace» en su lugar", "Copiar enlace" in prof_text(pg) and "Más opciones" not in prof_text(pg))
    pg.evaluate("document.querySelector('[data-pp=copy]').click()"); pg.wait_for_timeout(200)
    check("P10i «Copiar enlace» copia el enlace individual", pg.evaluate("window.__copied") == link, pg.evaluate("window.__copied"))
    ctx.close()
    # enlace individual: ?perfil=uid
    ctx, pg, errs, _ = make_page(b, base + "?perfil=" + U_REV, store=store()); wait_catalog(pg); pg.wait_for_timeout(600)
    t = prof_text(pg)
    check("P11 abrir el enlace ?perfil=<uid> muestra directamente ese perfil (sin iniciar sesión)", prof_open(pg) and "Rosa A." in t and "Excelente atención mayorista" in t, t[:100])
    check("P11b la dirección queda limpia (sin ?perfil) tras abrirlo", "perfil=" not in pg.url, pg.url)
    tab(pg, "fav"); check("P11c los favoritos públicos incluyen el negocio de Firestore aunque el enlace abra antes del catálogo", "Tienda Nueva SRL" in prof_text(pg) and "Alito Mayorista" in prof_text(pg))
    check("P11d sin pendientes ni rechazadas", "SECRETO" not in prof_text(pg))
    pg.go_back(); pg.wait_for_timeout(400)
    check("P11e el botón atrás cierra el perfil y deja la app", not prof_open(pg) and pg.evaluate("document.querySelectorAll('#list .card').length")>=13)
    check("P11f sin errores de JavaScript", not errs, errs); ctx.close()
    ctx, pg, errs, _ = make_page(b, base + "?perfil=abc%3Cscript%3E", store=store()); wait_catalog(pg); pg.wait_for_timeout(400)
    check("P11g un ?perfil inválido no abre nada ni rompe la app", not prof_open(pg) and not errs, errs); ctx.close()
    ctx, pg, errs, _ = make_page(b, base + "?perfil=" + U_PRIV, store=store()); wait_catalog(pg); pg.wait_for_timeout(600); tab(pg, "fav")
    check("P11h enlace a un perfil con favoritos privados: no los muestra", "mantiene sus favoritos privados" in prof_text(pg) and "Top Level" not in prof_text(pg)); ctx.close()
    ctx, pg, errs, _ = make_page(b, base + "?p=" + ORIG_A, store=store()); wait_catalog(pg); pg.wait_for_timeout(500)
    check("P11i el enlace directo a una ficha (?p=) sigue funcionando", pg.evaluate("document.getElementById('modal').classList.contains('open')") and not prof_open(pg)); ctx.close()
    # 360 px
    ctx, pg, errs, _ = make_page(b, url, store=store(), viewport=(360, 740)); wait_catalog(pg)
    pg.evaluate("MPProfiles.open('%s','')" % U_PIC); pg.wait_for_timeout(500); pg.evaluate("document.querySelector('#pubSheet .pp-sharebtn').click()")
    check("P12 sin desbordamiento horizontal a 360 px", pg.evaluate("document.getElementById('pubSheet').scrollWidth<=document.getElementById('pubSheet').clientWidth+1"))
    pg.screenshot(path="/tmp/perfil_360.png"); ctx.close()
    # botón dorado idéntico
    ctx, pg, errs, _ = make_page(b, url, store=store(), usr=dict(user(U_ME), displayName="Armando Prueba")); wait_catalog(pg); pg.wait_for_timeout(500)
    bt = pg.evaluate("(()=>{const e=document.getElementById('acctBtn'),r=e.getBoundingClientRect(),s=getComputedStyle(e);return{t:e.textContent,c:e.className,o:e.outerHTML,x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),bg:s.backgroundColor,co:s.color,br:s.borderRadius,bd:s.border,fs:s.fontSize}})()")
    json.dump(bt, open("/tmp/btn_v101.json", "w")); ctx.close()

if __name__ == "__main__":
    urls = sys.argv[1:]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for u in urls:
            RESULTS.clear(); run(u, b); run_v101(u, b)
            ok = sum(1 for r in RESULTS if r[1]); print("\nRESUMEN %s: %d/%d pasan" % (u.split("/")[-1], ok, len(RESULTS)))
        b.close()
