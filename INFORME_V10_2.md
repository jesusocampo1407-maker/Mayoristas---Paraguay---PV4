# Mayoristas Paraguay · v10.2 experimental

Archivo nuevo: `index_v10_2_experimental.html`, creado a partir de `index_v10_1_perfil_publico_experimental.html`. La v10.1 y las anteriores NO se modificaron. No se publicó nada ni se tocó Firebase ni sus reglas (`firestore_rules_v10_perfiles.rules` es el mismo borrador, sin cambios; sigue sin publicar).

## Cambios
1. **Barra inferior:** `Inicio | Buscar | Registrar | Mi perfil` (4.º botón con icono de persona).
   - Con sesión (cuenta Emprendedor/Revendedor con correo verificado): abre directamente su perfil público.
   - Sin sesión: abre la pantalla de acceso (iniciar sesión / crear cuenta) con el aviso «Para ver tu perfil público, iniciá sesión o creá tu cuenta».
   - Cuentas que no tienen perfil público (mayoristas, correo sin verificar): se abre «Mi cuenta» con un aviso breve, sin crear nada.
2. **Botón superior «Entrar» / «Armando»:** no se modificó. Mismo HTML, posición, tamaño y colores que en la v10.1, sin y con sesión, a 390 y 360 px.
3. **Foto de perfil:** «Cambiar foto» abre el selector de imágenes del teléfono (`accept="image/*"`, sin forzar cámara) y luego un **recorte**: marco circular, arrastrar para mover, control de zoom y pellizco con dos dedos, vista previa circular en vivo, «Cancelar» y «Guardar foto». Solo al guardar se escribe en Firestore (`publicProfiles/<uid>`, como antes: JPEG 128×128, ≤ 20 000 caracteres). Cancelar, Escape y el botón «atrás» del teléfono cierran sin guardar. Sin librerías nuevas (solo canvas y eventos de puntero).
- Todo lo demás es la v10.1 sin tocar. Cambios en el archivo: 8 líneas reemplazadas (barra, icono, manejador de la barra, pantalla «Mi perfil público», versión) y 83 agregadas.

## Pruebas SIMULADAS (Chromium + Firebase falso en memoria): 119 de 119 pasan
`python3 client_sim_v10_2.py http://localhost:8765/index_v10_2_experimental.html` (con el HTML servido localmente).
- Las 81 de la v10.1 (perfiles, opiniones, favoritos, compartir, enlace `?perfil=`, privacidad) adaptadas a la foto con recorte.
- 38 nuevas: cuatro botones y su orden; Inicio/Buscar/Registrar siguen funcionando; «Mi perfil» sin sesión, con sesión y con cuenta de mayorista; barra sin desbordar a 390 y 360 px; selector `image/*`; recorte (abrir, arrastrar, zoom con control y con dos dedos simulados, cancelar, Escape, «atrás»); guardado con encuadre correcto (se comprobó el color de los píxeles del JPEG guardado); circular; PDF e imagen ilegible rechazados con mensaje; **persistencia tras recargar** (el backend simulado conserva el documento y la página se recarga desde cero); botón superior idéntico; 13 negocios con los 12 identificadores fijos idénticos a la v10.1.
- Dispositivo emulado «Pixel 7» (pantalla táctil, 412 px) para las pruebas de foto.

## Pruebas REALES: ninguna
- **No se probó en un teléfono real.** Lo que sigue es simulación y debe confirmarse en tu Android: que el selector muestre la galería/Fotos de tu teléfono (la web no puede obligar a una galería concreta; `image/*` es lo estándar y en Android moderno abre el selector de fotos), el arrastre y el pellizco con tus dedos, fotos grandes de cámara (a 12 MP o más pueden tardar o fallar por memoria), y fotos HEIC (se rechazan con mensaje si el navegador no las abre).
- **Las reglas de Firestore siguen sin ejecutarse** (sin acceso a npm en este entorno): hay 30 pruebas en `tests/` pendientes de correr con el emulador antes de publicar nada.
- Sin probar con Firebase real, con registro y verificación de correo reales, ni con WhatsApp real.
- «Persistencia tras recargar» está probada contra el Firebase simulado; con el real depende de las reglas publicadas.

## Limitaciones
- El botón «atrás» del teléfono mientras el recorte está abierto lo cierra (comportamiento intencional); si ya había un perfil abierto debajo, sigue abierto.
- «Mi perfil» no se marca como activo en la barra (abre una hoja, no una pantalla).
- La barra no muestra la foto del usuario, solo un icono.
- Las fotos siguen sin moderación automática (solo el administrador puede quitarlas).
