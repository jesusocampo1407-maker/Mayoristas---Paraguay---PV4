// Pruebas de las reglas v10 (perfiles públicos) contra el EMULADOR de Firestore. NUNCA contra Firebase real: proyecto «demo-mayoristas».
// ESTADO: ESCRITAS, NO EJECUTADAS (en el entorno donde se prepararon no hay firebase-tools ni red para instalarlo). Hay que correrlas antes de publicar las reglas.
// Ejecutar:  cd tests && npm install && npx firebase emulators:exec --only firestore --project demo-mayoristas "node --test rules_v10_perfiles.test.mjs"
// Colocar junto a ../firestore_rules_v10_perfiles.rules (o cambiar RULES). Necesita Java 11+ y Node 18+.
import { readFileSync } from 'node:fs';
import { describe, it, before, after, beforeEach } from 'node:test';
import { initializeTestEnvironment, assertFails, assertSucceeds } from '@firebase/rules-unit-testing';
import { doc, getDoc, getDocs, setDoc, deleteDoc, collection, query, where, serverTimestamp, Timestamp } from 'firebase/firestore';

const RULES = readFileSync(new URL('../firestore_rules_v10_perfiles.rules', import.meta.url), 'utf8');
const ORIG_A = '595983897999';
const BUYER = 'BuyerUidBuyerUidBuyerUid1234', BUYER2 = 'Buyer2UidBuyer2UidBuyer2U123', PROV = 'ProvUidProvUidProvUidProv1234', ADMIN = 'AdminUidAdminUidAdminUid123';
const CREATED = Timestamp.fromDate(new Date('2026-09-01T12:00:00Z'));
const JPG = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD';
let env;
const anon = () => env.unauthenticatedContext().firestore();
const as = (uid, extra = {}) => env.authenticatedContext(uid, { email: uid.slice(0, 6).toLowerCase() + '@test.com', email_verified: true, ...extra }).firestore();
const pub = (over = {}) => ({ name: 'Comprador U.', photo: '', favoritesPublic: false, joinedAt: CREATED, updatedAt: serverTimestamp(), ...over });
const put = (db, uid, over = {}) => setDoc(doc(db, 'publicProfiles', uid), pub(over));

before(async () => {
  env = await initializeTestEnvironment({ projectId: 'demo-mayoristas', firestore: { rules: RULES, host: process.env.FIRESTORE_EMULATOR_HOST?.split(':')[0] || '127.0.0.1', port: +(process.env.FIRESTORE_EMULATOR_HOST?.split(':')[1] || 8080) } });
});
after(async () => { await env.cleanup(); });
beforeEach(async () => {
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    await setDoc(doc(db, 'admins', ADMIN), { ok: true });
    for (const [u, role] of [[BUYER, 'buyer'], [BUYER2, 'buyer'], [PROV, 'provider']])
      await setDoc(doc(db, 'users', u), { name: 'Usuario ' + role, email: u.slice(0, 6).toLowerCase() + '@test.com', role, createdAt: CREATED });
    const rv = (status, id) => setDoc(doc(db, 'reviews', ORIG_A + '_' + id), { providerId: ORIG_A, rating: 5, text: 'Texto ' + status, authorUid: BUYER, authorName: 'Comprador U.', authorType: 'registered', verifiedPurchase: false, status, createdAt: Timestamp.now() });
    await rv('approved', 'a'); await rv('pending', 'p'); await rv('rejected', 'r');
    await setDoc(doc(db, 'users', BUYER, 'favorites', ORIG_A), { key: ORIG_A, createdAt: Timestamp.now() });
  });
});

describe('publicProfiles: lectura', () => {
  it('cualquiera (incluso sin sesión) puede LEER un perfil por uid', async () => {
    await env.withSecurityRulesDisabled(async (c) => setDoc(doc(c.firestore(), 'publicProfiles', BUYER), { name: 'Comprador U.', photo: '', favoritesPublic: false, joinedAt: CREATED, updatedAt: Timestamp.now() }));
    await assertSucceeds(getDoc(doc(anon(), 'publicProfiles', BUYER)));
  });
  it('NO se puede listar la colección (no hay forma de enumerar usuarios)', async () => {
    await assertFails(getDocs(collection(anon(), 'publicProfiles')));
    await assertFails(getDocs(collection(as(BUYER2), 'publicProfiles')));
  });
});

describe('publicProfiles: crear', () => {
  it('el comprador verificado crea SU perfil (favoritos privados por defecto, fecha real de alta)', async () => { await assertSucceeds(put(as(BUYER), BUYER)); });
  it('no se puede crear el perfil de otra persona', async () => { await assertFails(put(as(BUYER), BUYER2)); });
  it('sin sesión no se puede crear', async () => { await assertFails(put(anon(), BUYER)); });
  it('un mayorista (provider) no puede crear perfil público', async () => { await assertFails(put(as(PROV), PROV)); });
  it('con correo SIN verificar no se puede crear', async () => { await assertFails(put(as(BUYER, { email_verified: false }), BUYER)); });
  it('la fecha de incorporación no se puede inventar (debe ser users/{uid}.createdAt)', async () => {
    await assertFails(put(as(BUYER), BUYER, { joinedAt: Timestamp.fromDate(new Date('2020-01-01T00:00:00Z')) }));
  });
  it('no admite campos extra: correo, rol, admin, uid', async () => {
    for (const extra of [{ email: 'a@b.com' }, { role: 'buyer' }, { isAdmin: true }, { uid: BUYER }])
      await assertFails(put(as(BUYER), BUYER, extra));
  });
  it('faltando un campo obligatorio se rechaza', async () => {
    const { photo, ...sinFoto } = pub();
    await assertFails(setDoc(doc(as(BUYER), 'publicProfiles', BUYER), sinFoto));
  });
  it('nombre vacío o de más de 40 caracteres se rechaza', async () => {
    await assertFails(put(as(BUYER), BUYER, { name: '' }));
    await assertFails(put(as(BUYER), BUYER, { name: 'x'.repeat(41) }));
  });
  it('favoritesPublic debe ser booleano', async () => { await assertFails(put(as(BUYER), BUYER, { favoritesPublic: 'si' })); });
  it('updatedAt debe ser la hora del servidor', async () => { await assertFails(put(as(BUYER), BUYER, { updatedAt: Timestamp.fromDate(new Date('2020-01-01')) })); });
  it('foto: solo JPEG en base64 y de hasta 24 000 caracteres', async () => {
    await assertSucceeds(put(as(BUYER), BUYER, { photo: JPG }));
    await assertFails(put(as(BUYER2), BUYER2, { photo: 'https://ejemplo.com/foto.jpg' }));
    await assertFails(put(as(BUYER2), BUYER2, { photo: 'javascript:alert(1)' }));
    await assertFails(put(as(BUYER2), BUYER2, { photo: 'data:image/svg+xml;base64,PHN2Zz4=' }));
    await assertFails(put(as(BUYER2), BUYER2, { photo: 'data:image/jpeg;base64,' + 'A'.repeat(24000) }));
  });
});

describe('publicProfiles: actualizar y borrar', () => {
  beforeEach(async () => { await assertSucceeds(put(as(BUYER), BUYER)); });
  it('el dueño cambia foto y visibilidad de favoritos', async () => {
    await assertSucceeds(put(as(BUYER), BUYER, { photo: JPG, favoritesPublic: true }));
    await assertSucceeds(put(as(BUYER), BUYER, { photo: '', favoritesPublic: false }));
  });
  it('el dueño NO puede cambiar su fecha de incorporación', async () => {
    await assertFails(put(as(BUYER), BUYER, { joinedAt: Timestamp.fromDate(new Date('2026-10-30T00:00:00Z')) }));
  });
  it('otra persona no puede editar el perfil', async () => { await assertFails(put(as(BUYER2), BUYER, { favoritesPublic: true })); });
  it('el administrador SOLO puede vaciar la foto', async () => {
    await assertSucceeds(put(as(BUYER), BUYER, { photo: JPG }));
    await assertSucceeds(put(as(ADMIN), BUYER, { photo: '' }));
  });
  it('el administrador NO puede cambiar nombre, favoritos ni poner otra foto', async () => {
    await assertFails(put(as(ADMIN), BUYER, { name: 'Otro N.' }));
    await assertFails(put(as(ADMIN), BUYER, { favoritesPublic: true }));
    await assertFails(put(as(ADMIN), BUYER, { photo: JPG }));
  });
  it('nadie puede borrar un perfil', async () => {
    await assertFails(deleteDoc(doc(as(BUYER), 'publicProfiles', BUYER)));
    await assertFails(deleteDoc(doc(as(ADMIN), 'publicProfiles', BUYER)));
  });
});

describe('favoritos: privados salvo que el dueño los haga públicos', () => {
  const favsOf = (db, uid) => getDocs(collection(db, 'users', uid, 'favorites'));
  it('sin perfil público: solo el dueño lee sus favoritos', async () => {
    await assertSucceeds(favsOf(as(BUYER), BUYER));
    await assertFails(favsOf(as(BUYER2), BUYER));
    await assertFails(favsOf(anon(), BUYER));
  });
  it('con favoritesPublic=false: siguen privados', async () => {
    await assertSucceeds(put(as(BUYER), BUYER, { favoritesPublic: false }));
    await assertFails(favsOf(as(BUYER2), BUYER)); await assertFails(favsOf(anon(), BUYER));
    await assertFails(getDoc(doc(anon(), 'users', BUYER, 'favorites', ORIG_A)));
  });
  it('con favoritesPublic=true: cualquiera puede LEERLOS (y solo leerlos)', async () => {
    await assertSucceeds(put(as(BUYER), BUYER, { favoritesPublic: true }));
    await assertSucceeds(favsOf(anon(), BUYER)); await assertSucceeds(favsOf(as(BUYER2), BUYER));
    await assertFails(setDoc(doc(as(BUYER2), 'users', BUYER, 'favorites', ORIG_A), { key: ORIG_A, createdAt: serverTimestamp() }));
    await assertFails(deleteDoc(doc(as(BUYER2), 'users', BUYER, 'favorites', ORIG_A)));
  });
  it('al volver a privado se cierra de inmediato', async () => {
    await assertSucceeds(put(as(BUYER), BUYER, { favoritesPublic: true }));
    await assertSucceeds(put(as(BUYER), BUYER, { favoritesPublic: false }));
    await assertFails(favsOf(anon(), BUYER));
  });
  it('hacer públicos los favoritos de uno no abre los de otra persona', async () => {
    await assertSucceeds(put(as(BUYER), BUYER, { favoritesPublic: true }));
    await assertFails(favsOf(anon(), BUYER2));
  });
});

describe('opiniones: el perfil solo ve las APROBADAS (regla existente, comprobación de regresión)', () => {
  const byAuthor = (db, ...extra) => getDocs(query(collection(db, 'reviews'), where('authorUid', '==', BUYER), ...extra));
  it('consulta por autor + status=approved: permitida a cualquiera', async () => {
    const s = await assertSucceeds(byAuthor(anon(), where('status', '==', 'approved')));
    if (s.size !== 1) throw new Error('debía devolver solo la aprobada, devolvió ' + s.size);
  });
  it('consulta por autor SIN filtrar estado: denegada a un tercero (no puede leer pendientes ni rechazadas)', async () => {
    await assertFails(byAuthor(anon())); await assertFails(byAuthor(as(BUYER2)));
  });
  it('un tercero no puede leer una opinión pendiente o rechazada por id', async () => {
    await assertFails(getDoc(doc(as(BUYER2), 'reviews', ORIG_A + '_' + 'p'))); await assertFails(getDoc(doc(anon(), 'reviews', ORIG_A + '_' + 'r')));
  });
});

describe('regresión: no se abrió nada más', () => {
  it('users/{uid} sigue privado (correo y rol)', async () => {
    await assertFails(getDoc(doc(anon(), 'users', BUYER))); await assertFails(getDoc(doc(as(BUYER2), 'users', BUYER)));
    await assertSucceeds(getDoc(doc(as(BUYER), 'users', BUYER)));
  });
  it('admins sigue sin ser legible por terceros', async () => { await assertFails(getDoc(doc(as(BUYER), 'admins', ADMIN))); });
});
