// Pruebas de las reglas de Firestore v9.1 contra el EMULADOR (nunca contra Firebase real: el proyecto es «demo-mayoristas»).
// Ejecutar:  cd tests && npm install && npm test      (necesita Java 11+ y Node 18+)
// Cada prueba dice qué debe pasar. Las marcadas «LIMITACIÓN CONOCIDA» documentan algo que las reglas NO pueden impedir.
import { readFileSync } from 'node:fs';
import { describe, it, before, after, beforeEach } from 'node:test';
import { initializeTestEnvironment, assertFails, assertSucceeds } from '@firebase/rules-unit-testing';
import { doc, getDoc, getDocs, setDoc, deleteDoc, updateDoc, collection, query, where, serverTimestamp, getCountFromServer, Timestamp } from 'firebase/firestore';

const RULES = readFileSync(new URL('../firestore_rules_v9_1.rules', import.meta.url), 'utf8');
const ORIG_A = '595983897999', ORIG_B = '595972614198';          // originales (clave = WhatsApp)
const NEW_UID = 'AbCdEfGhIjKlMnOpQrStUvWxYz12';                  // negocio nuevo publicado (clave = uid del dueño)
const HID_UID = 'HiddenBizUidHiddenBizUid1234';                  // negocio nuevo oculto por el administrador
const GHOST_UID = 'GhostUidGhostUidGhostUid1234';                // no existe
const GHOST_NUM = '595900000000';                                // número que no es de ningún original
const BUYER = 'BuyerUidBuyerUidBuyerUid1234', BUYER2 = 'Buyer2UidBuyer2UidBuyer2U123', ADMIN = 'AdminUidAdminUidAdminUid123';
const VID = 'a1b2c3d4e5f6a7b8c9d0', VID2 = 'f0e1d2c3b4a5968778a9';

let env;
const ymd = (d) => d.toISOString().slice(0, 10).replace(/-/g, '');
const TODAY = () => ymd(new Date());
const DAYS_AGO = (n) => ymd(new Date(Date.now() - n * 86400000));
const DAYS_AHEAD = (n) => ymd(new Date(Date.now() + n * 86400000));

const anon = () => env.unauthenticatedContext().firestore();
const as = (uid, extra = {}) => env.authenticatedContext(uid, { email: uid.slice(0, 6).toLowerCase() + '@test.com', email_verified: true, ...extra }).firestore();

const evId = (key, type, day, vid) => `${key}_${type}_${day}_${vid}`;
const evData = (key, type, day, vid, over = {}) => ({ key, type, day, vid, createdAt: serverTimestamp(), ...over });
const putEv = (db, key, type = 'view', day = TODAY(), vid = VID, over = {}) => setDoc(doc(db, 'statEvents', evId(key, type, day, vid)), evData(key, type, day, vid, over));
const favData = (key, over = {}) => ({ key, createdAt: serverTimestamp(), ...over });
const putFav = (db, uid, key, over = {}) => setDoc(doc(db, 'users', uid, 'favorites', key), favData(key, over));

const biz = (status, w, extra = {}) => ({ rk: 'x', n: 'Negocio de prueba', c: 'Asunción', cs: ['Asunción'], k: ['Tecnología'], d: 'Descripción', m: '', a: '', ig: '', web: '', w, sh: 'pais', status, publishedAt: Timestamp.now(), updatedAt: Timestamp.now(), ...extra });

before(async () => {
  env = await initializeTestEnvironment({ projectId: 'demo-mayoristas', firestore: { rules: RULES, host: process.env.FIRESTORE_EMULATOR_HOST?.split(':')[0] || '127.0.0.1', port: +(process.env.FIRESTORE_EMULATOR_HOST?.split(':')[1] || 8080) } });
});
after(async () => { await env.cleanup(); });
beforeEach(async () => {
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    await setDoc(doc(db, 'admins', ADMIN), { ok: true });
    for (const [u, role] of [[BUYER, 'buyer'], [BUYER2, 'buyer'], [NEW_UID, 'provider'], [HID_UID, 'provider']])
      await setDoc(doc(db, 'users', u), { name: 'Usuario ' + role, email: u.slice(0, 6).toLowerCase() + '@test.com', role, createdAt: Timestamp.now() });
    await setDoc(doc(db, 'businesses', NEW_UID), biz('published', '595981123456', { rk: NEW_UID }));
    await setDoc(doc(db, 'businesses', HID_UID), biz('hidden', '595982222222', { rk: HID_UID }));
    await setDoc(doc(db, 'businessRequests', NEW_UID), { ownerUid: NEW_UID, name: 'Tienda Nueva', whatsapp: '595981123456', status: 'published' });
    await setDoc(doc(db, 'reviews', ORIG_A + '_' + BUYER), { providerId: ORIG_A, rating: 5, text: 'Muy bueno', authorUid: BUYER, authorName: 'Comprador U.', authorType: 'registered', verifiedPurchase: false, status: 'approved', createdAt: Timestamp.now() });
    await setDoc(doc(db, 'reviews', ORIG_B + '_' + BUYER), { providerId: ORIG_B, rating: 3, text: 'Pendiente de revisar', authorUid: BUYER, authorName: 'Comprador U.', authorType: 'registered', verifiedPurchase: false, status: 'pending', createdAt: Timestamp.now() });
  });
});

/* ======================= FAVORITOS ======================= */
describe('Favoritos: crear', () => {
  it('visitante sin sesión NO puede crear ni leer favoritos', async () => {
    await assertFails(putFav(anon(), BUYER, ORIG_A));
    await assertFails(getDocs(collection(anon(), 'users', BUYER, 'favorites')));
  });
  it('usuario guarda un negocio ORIGINAL (clave = WhatsApp)', async () => { await assertSucceeds(putFav(as(BUYER), BUYER, ORIG_A)); });
  it('usuario guarda un negocio NUEVO publicado (clave = uid)', async () => { await assertSucceeds(putFav(as(BUYER), BUYER, NEW_UID)); });
  it('NO se puede guardar un número que no es de ningún original', async () => { await assertFails(putFav(as(BUYER), BUYER, GHOST_NUM)); });
  it('NO se puede guardar un uid inexistente', async () => { await assertFails(putFav(as(BUYER), BUYER, GHOST_UID)); });
  it('NO se puede guardar un negocio nuevo OCULTO', async () => { await assertFails(putFav(as(BUYER), BUYER, HID_UID)); });
  it('NO se puede guardar con campos de más', async () => { await assertFails(putFav(as(BUYER), BUYER, ORIG_A, { extra: 1 })); });
  it('NO se puede guardar si el campo key no coincide con el id', async () => { await assertFails(setDoc(doc(as(BUYER), 'users', BUYER, 'favorites', ORIG_A), favData(ORIG_B))); });
  it('NO se puede guardar con fecha inventada por el cliente', async () => { await assertFails(putFav(as(BUYER), BUYER, ORIG_A, { createdAt: Timestamp.fromDate(new Date('2020-01-01')) })); });
  it('NO se aceptan claves con formato inválido', async () => {
    for (const k of ['abc', '12345', 'con espacio 123456789', 'x'.repeat(41)]) await assertFails(putFav(as(BUYER), BUYER, k));
  });
});
describe('Favoritos: lectura, aislamiento entre cuentas, modificación y borrado', () => {
  beforeEach(async () => { await env.withSecurityRulesDisabled(async (c) => { await setDoc(doc(c.firestore(), 'users', BUYER, 'favorites', ORIG_A), favData(ORIG_A, { createdAt: Timestamp.now() })); await setDoc(doc(c.firestore(), 'users', BUYER, 'favorites', HID_UID), favData(HID_UID, { createdAt: Timestamp.now() })); }); });
  it('el dueño lee y lista sus favoritos', async () => {
    await assertSucceeds(getDoc(doc(as(BUYER), 'users', BUYER, 'favorites', ORIG_A)));
    await assertSucceeds(getDocs(collection(as(BUYER), 'users', BUYER, 'favorites')));
  });
  it('otra cuenta NO puede leer, listar, crear ni borrar favoritos ajenos', async () => {
    const o = as(BUYER2);
    await assertFails(getDoc(doc(o, 'users', BUYER, 'favorites', ORIG_A)));
    await assertFails(getDocs(collection(o, 'users', BUYER, 'favorites')));
    await assertFails(putFav(o, BUYER, ORIG_B));
    await assertFails(deleteDoc(doc(o, 'users', BUYER, 'favorites', ORIG_A)));
  });
  it('el administrador tampoco lee favoritos ajenos (son privados)', async () => { await assertFails(getDocs(collection(as(ADMIN), 'users', BUYER, 'favorites'))); });
  it('un favorito no se puede modificar (ni por su dueño)', async () => { await assertFails(updateDoc(doc(as(BUYER), 'users', BUYER, 'favorites', ORIG_A), { createdAt: serverTimestamp() })); });
  it('el dueño puede borrar un favorito normal', async () => { await assertSucceeds(deleteDoc(doc(as(BUYER), 'users', BUYER, 'favorites', ORIG_A))); });
  it('el dueño puede borrar un favorito HUÉRFANO (negocio ya oculto/inexistente)', async () => { await assertSucceeds(deleteDoc(doc(as(BUYER), 'users', BUYER, 'favorites', HID_UID))); });
  it('crear favoritos no abre la lista de usuarios', async () => { await assertFails(getDocs(collection(as(BUYER), 'users'))); });
});

/* ======================= ESTADÍSTICAS: crear ======================= */
describe('Eventos de rendimiento: crear', () => {
  it('visitante sin sesión registra una visita a un ORIGINAL', async () => { await assertSucceeds(putEv(anon(), ORIG_A, 'view')); });
  it('visitante registra view, wa, ig y web de un negocio NUEVO publicado', async () => {
    for (const t of ['view', 'wa', 'ig', 'web']) await assertSucceeds(putEv(anon(), NEW_UID, t));
  });
  it('un usuario logueado que NO es el dueño también puede registrar', async () => { await assertSucceeds(putEv(as(BUYER), NEW_UID, 'wa')); });
  it('el DUEÑO del negocio nuevo (uid == clave) NO puede registrar eventos propios', async () => { await assertFails(putEv(as(NEW_UID), NEW_UID, 'view')); });
  it('repetir el mismo evento (mismo id) se rechaza: ya existe, sería una modificación', async () => {
    await assertSucceeds(putEv(anon(), ORIG_A, 'view'));
    await assertFails(putEv(anon(), ORIG_A, 'view'));
  });
  it('LIMITACIÓN CONOCIDA: otro identificador de visitante («vid») distinto SÍ se acepta (por eso un script puede inflar contadores)', async () => {
    await assertSucceeds(putEv(anon(), ORIG_A, 'view', TODAY(), VID));
    await assertSucceeds(putEv(anon(), ORIG_A, 'view', TODAY(), VID2));
  });
  it('el id debe coincidir con los campos', async () => {
    await assertFails(setDoc(doc(anon(), 'statEvents', evId(ORIG_A, 'view', TODAY(), VID2)), evData(ORIG_A, 'view', TODAY(), VID)));
  });
  it('rechaza tipo inválido, vid inválido y campos de más', async () => {
    await assertFails(putEv(anon(), ORIG_A, 'compra'));
    await assertFails(putEv(anon(), ORIG_A, 'view', TODAY(), 'ABC'));                 // corto y con mayúsculas
    await assertFails(putEv(anon(), ORIG_A, 'view', TODAY(), VID, { extra: 'x' }));
  });
  it('rechaza una fecha del cliente en vez de la del servidor (createdAt)', async () => { await assertFails(putEv(anon(), ORIG_A, 'view', TODAY(), VID, { createdAt: Timestamp.fromDate(new Date('2020-01-01')) })); });
  it('día: hoy y ayer (UTC) se aceptan; anteayer, futuro y absurdos se rechazan', async () => {
    await assertSucceeds(putEv(anon(), ORIG_A, 'view', TODAY()));
    await assertSucceeds(putEv(anon(), ORIG_B, 'view', DAYS_AGO(1)));
    await assertFails(putEv(anon(), ORIG_A, 'wa', DAYS_AGO(2)));
    await assertFails(putEv(anon(), ORIG_A, 'ig', DAYS_AHEAD(2)));
    await assertFails(putEv(anon(), ORIG_A, 'web', '00000000'));
    await assertFails(putEv(anon(), ORIG_A, 'web', '99999999'));
  });
  it('solo para negocios que existen y están publicados', async () => {
    await assertFails(putEv(anon(), GHOST_NUM, 'view'));    // número que no es de un original
    await assertFails(putEv(anon(), GHOST_UID, 'view'));    // uid inexistente
    await assertFails(putEv(anon(), HID_UID, 'view'));      // negocio nuevo oculto
  });
  it('un negocio nuevo que el administrador oculta deja de aceptar eventos', async () => {
    await assertSucceeds(putEv(anon(), NEW_UID, 'view'));
    await env.withSecurityRulesDisabled(async (c) => { await setDoc(doc(c.firestore(), 'businesses', NEW_UID), biz('hidden', '595981123456', { rk: NEW_UID })); });
    await assertFails(putEv(anon(), NEW_UID, 'wa'));
  });
});

/* ======================= ESTADÍSTICAS: lectura ======================= */
describe('Eventos de rendimiento: lectura', () => {
  beforeEach(async () => {
    await env.withSecurityRulesDisabled(async (c) => {
      const db = c.firestore();
      for (const [k, t, v] of [[NEW_UID, 'view', VID], [NEW_UID, 'wa', VID], [NEW_UID, 'view', VID2], [ORIG_A, 'view', VID]])
        await setDoc(doc(db, 'statEvents', evId(k, t, TODAY(), v)), evData(k, t, TODAY(), v, { createdAt: Timestamp.now() }));
    });
  });
  it('visitante sin sesión NO lee eventos (ni get, ni list, ni conteo)', async () => {
    await assertFails(getDoc(doc(anon(), 'statEvents', evId(NEW_UID, 'view', TODAY(), VID))));
    await assertFails(getDocs(collection(anon(), 'statEvents')));
    await assertFails(getCountFromServer(query(collection(anon(), 'statEvents'), where('key', '==', NEW_UID))));
  });
  it('el dueño del negocio nuevo cuenta SUS eventos (filtrando por su uid)', async () => {
    const r = await assertSucceeds(getCountFromServer(query(collection(as(NEW_UID), 'statEvents'), where('key', '==', NEW_UID), where('type', '==', 'view'))));
    if (r.data().count !== 2) throw new Error('se esperaban 2 visitas y hay ' + r.data().count);
  });
  it('el dueño NO puede leer eventos de otro negocio ni listar sin filtro', async () => {
    await assertFails(getDocs(query(collection(as(NEW_UID), 'statEvents'), where('key', '==', ORIG_A))));
    await assertFails(getDocs(collection(as(NEW_UID), 'statEvents')));
    await assertFails(getDoc(doc(as(NEW_UID), 'statEvents', evId(ORIG_A, 'view', TODAY(), VID))));
  });
  it('un comprador cualquiera NO lee eventos', async () => { await assertFails(getDocs(query(collection(as(BUYER), 'statEvents'), where('key', '==', NEW_UID)))); });
  it('el administrador lee todo (originales y nuevos)', async () => {
    await assertSucceeds(getDocs(collection(as(ADMIN), 'statEvents')));
    await assertSucceeds(getDocs(query(collection(as(ADMIN), 'statEvents'), where('key', '==', ORIG_A))));
  });
  it('LIMITACIÓN CONOCIDA: el dueño de un ORIGINAL (sin vínculo uid↔WhatsApp) no puede leer las estadísticas de su número', async () => {
    await assertFails(getDocs(query(collection(as(NEW_UID), 'statEvents'), where('key', '==', ORIG_A))));
  });
});

/* ======================= ESTADÍSTICAS: modificar y eliminar ======================= */
describe('Eventos de rendimiento: intentos de modificación y eliminación', () => {
  const id = () => evId(NEW_UID, 'view', TODAY(), VID);
  beforeEach(async () => { await env.withSecurityRulesDisabled(async (c) => { await setDoc(doc(c.firestore(), 'statEvents', id()), evData(NEW_UID, 'view', TODAY(), VID, { createdAt: Timestamp.now() })); }); });
  const actors = () => [['visitante', anon()], ['dueño', as(NEW_UID)], ['comprador', as(BUYER)], ['administrador', as(ADMIN)]];
  it('NADIE puede modificar un evento (update)', async () => { for (const [, db] of actors()) await assertFails(updateDoc(doc(db, 'statEvents', id()), { type: 'wa' })); });
  it('NADIE puede reescribir un evento existente con setDoc', async () => { for (const [, db] of actors()) await assertFails(setDoc(doc(db, 'statEvents', id()), evData(NEW_UID, 'view', TODAY(), VID))); });
  it('NADIE puede borrar un evento', async () => { for (const [, db] of actors()) await assertFails(deleteDoc(doc(db, 'statEvents', id()))); });
  it('no existe ningún contador editable: otras colecciones de estadísticas están denegadas', async () => {
    await assertFails(setDoc(doc(as(NEW_UID), 'stats', NEW_UID), { views: 9999 }));
    await assertFails(setDoc(doc(as(ADMIN), 'counters', NEW_UID), { views: 1 }));
  });
});

/* ======================= LECTURA en otras colecciones (regresión) ======================= */
describe('Permisos de lectura que no deben cambiar', () => {
  it('catálogo público: se listan solo los publicados; sin filtro se deniega', async () => {
    await assertSucceeds(getDocs(query(collection(anon(), 'businesses'), where('status', '==', 'published'))));
    await assertFails(getDocs(collection(anon(), 'businesses')));
    await assertFails(getDoc(doc(anon(), 'businesses', HID_UID)));
    await assertSucceeds(getDoc(doc(anon(), 'businesses', NEW_UID)));
  });
  it('ficha oculta: la ve su dueño y el administrador', async () => {
    await assertSucceeds(getDoc(doc(as(HID_UID), 'businesses', HID_UID)));
    await assertSucceeds(getDoc(doc(as(ADMIN), 'businesses', HID_UID)));
    await assertFails(getDoc(doc(as(BUYER), 'businesses', HID_UID)));
  });
  it('perfiles: cada cuenta lee el suyo, no el ajeno, y nadie lista', async () => {
    await assertSucceeds(getDoc(doc(as(BUYER), 'users', BUYER)));
    await assertFails(getDoc(doc(as(BUYER2), 'users', BUYER)));
    await assertFails(getDoc(doc(anon(), 'users', BUYER)));
    await assertFails(getDocs(collection(as(ADMIN), 'users')));
  });
  it('solicitudes de negocio: solo su dueño y el administrador', async () => {
    await assertSucceeds(getDoc(doc(as(NEW_UID), 'businessRequests', NEW_UID)));
    await assertFails(getDoc(doc(as(BUYER), 'businessRequests', NEW_UID)));
    await assertFails(getDoc(doc(anon(), 'businessRequests', NEW_UID)));
    await assertSucceeds(getDoc(doc(as(ADMIN), 'businessRequests', NEW_UID)));
  });
  it('opiniones: las aprobadas son públicas; las pendientes solo su autor y el administrador', async () => {
    await assertSucceeds(getDoc(doc(anon(), 'reviews', ORIG_A + '_' + BUYER)));
    await assertFails(getDoc(doc(anon(), 'reviews', ORIG_B + '_' + BUYER)));
    await assertSucceeds(getDoc(doc(as(BUYER), 'reviews', ORIG_B + '_' + BUYER)));
    await assertSucceeds(getDoc(doc(as(ADMIN), 'reviews', ORIG_B + '_' + BUYER)));
  });
  it('cualquier colección no prevista está denegada', async () => {
    await assertFails(getDoc(doc(as(ADMIN), 'otraColeccion', 'x')));
    await assertFails(setDoc(doc(as(ADMIN), 'otraColeccion', 'x'), { a: 1 }));
  });
});
