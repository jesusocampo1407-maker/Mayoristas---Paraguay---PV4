# Mayoristas Paraguay · v10.1 experimental: perfil público definitivo

Copia nueva sobre tu v10. NO se publicó nada ni se tocó Firebase real.

## Archivos
- `index_v10_1_perfil_publico_experimental.html` — HTML completo.
- `firestore_rules_v10_perfiles.rules` — borrador de reglas. **Idéntico al de la v10**: el diseño nuevo no necesitó cambiar ninguna regla.
- `tests/rules_v10_perfiles.test.mjs` + `tests/package.json` — pruebas de reglas (emulador). Solo se corrigió en `package.json` el nombre del archivo de prueba.
- `client_sim.py` + `client_sim_v10_1.py` — pruebas de la página con Firebase falso en memoria. `client_sim.py` lo reconstruí porque no venía adjunto.

## Qué contiene el perfil público (y nada más)
1. Nombre completo (el nombre público corto de siempre, p. ej. «Armando P.»).
2. Foto o avatar predeterminado, con anillo dorado.
3. «Miembro desde» con mes y año reales (los de la cuenta; no se pueden inventar).
4. Pestaña «Opiniones»: solo opiniones aprobadas.
5. Pestaña «Favoritos»: solo si la persona los hizo públicos.
6. Botón «Compartir perfil»: abre WhatsApp y «Más opciones» (menú de compartir del teléfono). En una computadora, sin menú nativo, aparece «Copiar enlace».

Diseño inspirado en Helena Jones: hoja oscura, avatar con anillo, nombre grande, tarjeta de dato, pestañas con subrayado dorado. Sin ajustes, campana, mensajes, seguidores, muro, estadísticas, comunidad ni directorio.

## Cómo funciona
- Tocar nombre o avatar en una opinión abre su perfil (ya existía; se conserva).
- Enlace individual: `…/index.html?perfil=<uid>`. Quien lo abre, con o sin sesión, ve directamente ese perfil. La dirección queda limpia después y «atrás» cierra el perfil.
- «Mi cuenta» → **«Mi perfil público»**: elegir/quitar foto, interruptor de favoritos públicos, ver mi perfil. Los mayoristas no la ven.
- Botón dorado `#acctBtn`: sin cambios (mismo HTML, posición, tamaño y colores a 390 y 360 px; sus líneas no aparecen en la diferencia).
- 13 negocios (12 fijos + 1 de Firestore): conservados; los 12 identificadores son idénticos a los de la v10.
- Cambios respecto a la v10: 17 líneas reemplazadas y 53 agregadas, todas del perfil público (CSS, pantalla de perfil, enlace y número de versión).

## Pruebas EJECUTADAS
- `client_sim_v10_1.py`: **81 de 81 pasan** (Chromium, 390 px y 360 px, Firebase falso).
  - Las 55 de la v10, adaptadas a pestañas y al rótulo «Miembro desde». Con mi simulador reconstruido, la v10 original también dio 55/55.
  - 26 nuevas: diseño oscuro, dos pestañas exactas, ausencia de comunidad/seguidores/mensajes/muro/directorio/estadísticas, botón «Compartir perfil», WhatsApp con el enlace individual, menú nativo, «Copiar enlace», sin datos privados en lo compartido, enlace `?perfil=` (sin sesión, atrás, enlace inválido, favoritos privados, carrera con el catálogo), `?p=` de fichas intacto, sin desbordamiento a 360 px.
- Comparación del botón dorado v10 vs v10.1: idéntico.
- Revisión visual con captura a 390 px.

## Pruebas NO ejecutadas (pendiente)
- **Las pruebas de reglas (30) NO se ejecutaron.** Este entorno no tiene acceso a npm (`registry.npmjs.org` no resuelve), así que no pude instalar `firebase-tools` ni el emulador. Tampoco pude comprobar que el archivo de reglas compile (solo verifiqué que llaves y paréntesis estén balanceados). **No publiques las reglas antes de correrlas:**
  `cd tests && npm install && npx firebase emulators:exec --only firestore --project demo-mayoristas "node --test rules_v10_perfiles.test.mjs"` (Java 11+, Node 18+; en una computadora o GitHub Actions).
- El Firebase falso no aplica reglas: la privacidad real de favoritos y la lectura de perfiles dependen de ellas.
- Sin probar con Firebase real, con WhatsApp real ni en un Android físico (el menú nativo y `wa.me` se probaron con simulaciones).
- Sin probar el flujo real de registro y verificación de correo.

## Limitaciones
- Fotos sin moderación automática; hay «Quitar foto (administrador)» (solo visible para el administrador; ya existía en la v10, no es una función nueva de uso general).
- Las fotos se guardan dentro del documento (128×128 JPEG, hasta ~20 KB) porque no usas Storage.
- Cuentas anteriores a la v10 que no han vuelto a entrar no tienen perfil: se muestra su nombre, avatar predeterminado y «Fecha de incorporación no disponible».
- El perfil es legible por quien tenga el enlace/uid; la colección no se puede listar.
- Al compartir, el nombre público de la persona va en el texto del mensaje.
- «Copiar enlace» solo aparece cuando el navegador no tiene menú nativo de compartir.

## Siguiente paso
Correr las pruebas de reglas con el emulador. Si pasan, tú decides si publicas reglas y HTML.
