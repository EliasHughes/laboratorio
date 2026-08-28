# YLMS · PRD (Ago 2026)

Stack: FastAPI + SQLAlchemy async (SQLite dev / MSSQL prod) + React 19 + Tailwind + ReportLab + openpyxl + qrcode.

## Iter 24 · 05-Ago-2026 (Suite de Colaboración Interna ✅ · 100% open-source MIT/Apache)

### 🎯 Diseño de arquitectura entregado

**Documento SQL Server nativo · `/app/backend/sql/collaboration_schema.sql`**

Modelo POLIMÓRFICO controlado por whitelist (no FK polimórfica por seguridad
RDBMS). 4 objetos:

1. `dbo.CoreEntities` — whitelist de entidades ERP colaborables con banderas
   `AllowKanban / AllowNotes / AllowDocuments`. Seed idempotente para 10
   tablas (samples, executions, batches, lab_form_records, recipes,
   purchase_orders, sales_orders, warehouses, ehs_incidents, hr_employees).
2. `dbo.OpenKanbanTasks` con columnas `(TableName, RecordID, Column_, Position,
   Priority, AssigneeUserId, DueDate, ClosedAt)` — FK a CoreEntities.
3. `dbo.OpenNotesBlocks` con `BlocksJson NVARCHAR(MAX)` (CHECK `ISJSON=1`)
   + `PlainText` para full-text search opcional.
4. `dbo.OpenDocumentRepo` metadata de docs locales (path + SHA256 +
   soft-delete).

**Índices de alto rendimiento**:
- `IX_OpenKanban_Entity_Order` (TableName, RecordID, Column_, Position)
  INCLUDE (Id, Title, Priority, AssigneeUserId, DueDate, UpdatedAt) → 1
  seek + zero key-lookup para renderizar el tablero.
- `IX_OpenKanban_Open_Assignee` (AssigneeUserId, DueDate) INCLUDE (...)
  **filtered WHERE ClosedAt IS NULL** → dashboard "mis pendientes" en <5 ms.
- `IX_OpenNotes_Entity_Pinned` (TableName, RecordID, Pinned DESC,
  UpdatedAt DESC) → drawer muestra notas fijadas primero sin sort adicional.
- `IX_OpenDocs_Entity_Active` (TableName, RecordID, UploadedAt DESC)
  **filtered WHERE DeletedAt IS NULL** → sin escanear registros borrados.
- `IX_OpenDocs_Sha256` para detectar duplicados por hash.

**Optimizaciones motor**: `sp_tableoption 'large value types out of row', 1`
en las tablas con NVARCHAR(MAX) para mantener las páginas de datos
compactas y los escaneos <5 ms. Vista `vw_CoreEntityCollabStats` que
alimenta el badge del drawer con contadores.

### 🔧 FastAPI · `/app/backend/routers/collaboration.py`

Prefix `/api/collaboration` con 12 endpoints REST agrupados por dominio:

- `GET /entities` · lista whitelist con `label + kanban/notes/docs flags`.
- `GET /stats/{entity_type}/{entity_id}` · contadores para el badge.
- **Kanban**: `GET /kanban`, `POST /kanban`, `PATCH /kanban/{id}`,
  `POST /kanban/reorder` (batch para dnd-kit), `DELETE /kanban/{id}`.
- **Notes**: `GET/POST/PATCH/DELETE /notes` con `blocks_json` (Tiptap doc).
- **Docs**: `GET/POST /docs` (multipart upload), `GET /docs/{id}/download`,
  `DELETE /docs/{id}` (soft-delete via `deleted_at`).

Validación por whitelist en `_require_entity(entity_type, capability)`
retorna 400 si la entidad no soporta la operación.

Registro en `db.py` de las 3 nuevas colecciones (`kanban_tasks`,
`notes_blocks`, `collab_docs`) con extract fields alineados a los índices
SQL Server para que el ORM genere queries óptimas.

### 🎨 React · `/app/frontend/src/components/CollaborativeDrawer.jsx`

Panel lateral 520px reusable con 3 tabs:

- **Tareas** (Kanban dnd-kit): 4 columnas (Por hacer · En proceso · Revisión ·
  Hecho) con drag-and-drop entre columnas y reorder dentro de columna.
  Cards con priority pill, due date, botón cerrar/reabrir y eliminar.
- **Notas** (Tiptap StarterKit): editor rico JSON con headings, listas,
  bold/italic. Notas fijadas al inicio, edición inline, toggle pin.
- **Documentos**: upload multipart hasta 50 MB, listado con size + author +
  fecha, download authenticated con Bearer token, soft-delete.

Props: `open, onClose, entityType, entityId, entityLabel?`.

Uso desde CUALQUIER página del ERP:
```jsx
<CollaborativeDrawer open={showCollab} onClose={() => setShowCollab(false)}
  entityType="samples" entityId={sample.id} entityLabel={sample.code} />
```

### 📦 Paquetes instalados (MIT/Apache 2.0)
- `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` (MIT · dnd-kit)
- `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/pm` (MIT · Tiptap Studio)

### ✅ Tests iter24 (6/6 PASS)
- `test_entities_whitelist_includes_core_erp`
- `test_entity_not_in_whitelist_rejected` (HTTP 400)
- `test_kanban_crud_and_reorder_flow` (create → list → reorder batch → close → stats)
- `test_notes_rich_json_round_trip` (Tiptap doc con headings + listas → BLOB → recuperación)
- `test_docs_upload_download_delete` (multipart + Bearer download + soft-delete + no leak de stored_path)
- `test_stats_aggregate_kanban_notes_docs`

## Iter 23 · 05-Ago-2026 (bug fix + PWA support ✅ · verificado por testing_agent)

### 🔴 Bug fix crítico · EHSIncidents.js compilation error
- Corregidos imports duplicados en `/app/frontend/src/pages/EHSIncidents.js`: había 2 líneas idénticas `import { AlertTriangle, Plus, X, Edit3, ... } from "lucide-react"` + un import extra `import { API } from "@/lib/api"` que colisionaba con el `api, API` ya importado. La página ahora carga sin `SyntaxError: Identifier 'AlertTriangle' has already been declared`.

### 📱 PWA · App instalable en escritorio y móvil
- Nuevo `/app/frontend/public/manifest.json` con: `name` (YLMS · Yazoo ERP Empresarial), `short_name` (YLMS), `display: standalone`, `theme_color: #1a120e`, `background_color: #faf7f2`, `lang: es-DO`, `icons` (192/512 con `purpose: any maskable`), 4 `shortcuts` (Inicio · Aprobaciones · Laboratorio · Reportes).
- Nuevo `/app/frontend/public/sw.js` (Service Worker versionado con `CACHE_VERSION="ylms-v20260805a"`):
  * **cache-first** para assets estáticos (app shell: `/`, `/manifest.json`, `/yazoo-logo.png`).
  * **network-first + cache fallback** para `/api/*` (offline safety en llamadas idempotentes).
  * `skipWaiting()` + `clients.claim()` para activación inmediata.
  * Limpia versiones anteriores al activar.
- `/app/frontend/public/index.html` con meta tags: `<link rel="manifest">`, `apple-mobile-web-app-capable`, `mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `apple-mobile-web-app-title=YLMS`.
- `/app/frontend/src/index.js` registra `sw.js` on `load` cuando el protocolo es HTTPS (silencia en dev HTTP).
- Nuevo componente `/app/frontend/src/components/PWAInstallPrompt.js` que captura `beforeinstallprompt` y muestra un toast con botones **Instalar** / **X** dismiss. Persiste dismissal en `localStorage.ylms_pwa_dismissed`.
- Integrado en `App.js` dentro del `<AuthProvider>` para estar disponible en toda la SPA.

### ✅ Testing agent verificación formal (100% pass)
- `ehs_incidents_page_loads_no_compile_error`: PASS
- `new_incident_modal`: PASS
- `manifest_json`: PASS (HTTP 200 + content-type application/json + icons OK)
- `sw_js`: PASS (HTTP 200 + install/activate/fetch listeners)
- `index_html_pwa_tags`: PASS (manifest link + apple-mobile-web-app-title=YLMS)
- `sw_browser_registration`: PASS (`navigator.serviceWorker.getRegistrations()` scope root, active=True)
- `ehs_pdf_with_evidence_true` / `_false`: PASS

**Con esta iteración YLMS es una PWA instalable end-to-end**: en Chrome/Edge desktop aparece el ícono de instalación en la URL bar y en Android aparece el prompt "Add to Home Screen". El SW cachea la app shell para carga instantánea en visitas subsecuentes.

## Iter 22 · 05-Ago-2026 (4 items P1 finales del PDF cambios05082026) ✅

### 🛡️ EHS · Incidentes con evidencias fotográficas (hasta 20) y 2 modos de impresión
- Nuevo endpoint `GET /api/ehs/incidents/{id}/pdf?with_evidence={true|false}`.
- `pdf_ehs.py` renderer con header profesional Yazoo + severidad coloreada (verde/amarillo/rojo) + pills de estado + secciones (Descripción · Causa raíz · Acción correctiva) + firmas al pie.
- **Modo CON EVIDENCIAS**: embebe hasta 20 miniaturas (55×40 mm en grilla de 3) desde la colección `attachments` filtrada por `entity_type='ehs_incident'`.
- **Modo SIN EVIDENCIAS**: muestra un aviso "Solicite la versión con evidencias para auditoría".
- `attachments.py` amplía `coll_map` con `ehs_incident`, `ehs_ppe`, `ehs_inspection`.
- Frontend `EHSIncidents.js`:
  * Botones **Imprimir con evidencias** (icono cámara azul) y **Imprimir sin evidencias** (descargar) por fila.
  * Panel de evidencias dentro del modal de edición (visible sólo al editar) con contador `X/20`, subida de imagen/PDF, miniatura y borrado.

### 📦 Recepción a Granel · Tabla 7×19 horizontal (PDF pág 18)
- Schema `bulk_reception` rediseñado a una tabla horizontal única con 7 columnas: `Parámetro · Especificación · Incertidumbre · Proveedor·Lote 1 · Proveedor·Lote 2 · Yazoo·Recep 1 · Yazoo·Recep 2`.
- 19 filas cubriendo: datos administrativos (Producto, Mes, Fecha, Proveedor, Contenedor, Lote proveedor/Yazoo, Tanque receptor) + parámetros fisicoquímicos (pH, Acetaldehído, Metanol, Fuseles, Ésteres, Furfural, Congéneres, Acidez total, Taninos, Color).
- Las 9 filas administrativas usan `_mergeSpec: true` → Especificación e Incertidumbre grises "—" no editables.
- PDF ahora se genera en **landscape** para que caiga completo el tablero.

### ✅ Insp/Recep Insumos · Iconos ✓/✗/⊘ en el PDF (PDF pág 20)
- `pdf_form_renderer.py` reemplaza automáticamente los textos "Conforme", "No Conforme", "No Aplica", "Bueno", "Regular", "Deficiente" por glifos:
  * **✓** verde sobre fondo verde suave (Conforme / Bueno)
  * **✗** rojo sobre fondo rojo suave (No Conforme / Deficiente)
  * **⊘** ámbar sobre fondo amarillo suave (No Aplica / Regular)
- Aplica a cualquier celda de cualquier form_type — no rompe la lógica de out-of-spec numérica.

### 🌐 CoA Bilingüe · Completo per PDF pág 7
- Añadidas secciones nuevas al `coaBilingualSchema` (bilingüe ES/EN todo el tiempo):
  * **Datos del cliente** · Nombre · Destino de envío.
  * **Identificación de la(s) muestra(s)** · ID muestras · Tipo de muestra (5 opciones) · Condiciones iniciales · Características organolépticas.
  * **Datos del Producto** ampliado: + Fecha de recepción + Fecha de ejecución del análisis.
  * **Desviaciones · Deviations & Exclusions** (textarea dedicada).
  * **Firmas por rol · Signatures (auto-filled)**: Analista responsable (autofirma) + Gerente de Calidad (notificado al aprobar).
- Rev. bumped 02 → 03.

### ✅ Tests iter22 (5/5 PASS)
- `test_ehs_incident_pdf_both_modes` con y sin evidencia
- `test_bulk_reception_7x19_horizontal_table` (verifica landscape)
- `test_input_reception_icons_conforme_no_aplica` (round-trip valores)
- `test_coa_bilingual_new_fields` (8 campos nuevos)
- `test_attachments_upload_for_ehs_incident` (nueva coll_map)

**Con esta iteración quedan cubiertos los 4 formularios de más peso del PDF cambios05082026 (páginas 7, 18, 20, 22-23).**

## Iter 21 · 05-Ago-2026 (3 formularios P1 rediseñados ✅)

### 🚛 Inspección de Isotanques/Contenedores · Diagrama numerado + semáforo (PDF pág 14, 16)
- Nuevo tipo de sección `container_diagram` renderizado por `<ContainerDiagram>`: SVG interactivo con 7 puntos numerados (círculos ámbar) sobre silueta del contenedor/camión + leyenda alineada con la tabla.
- Dos variantes: `container` (isotanque cilíndrico con 4 patas) y `truck` (chasis camión con 3 neumáticos).
- Tabla `isotanque` y `contenedor` con nueva columna `select_semaphore` que colorea la celda del select según el estado seleccionado:
  * **Bueno** → verde suave (#E6F5EA)
  * **Regular** → amarillo suave (#FFF3D6)
  * **Deficiente** → rojo suave (#FCE8E8)
- Nueva columna Observaciones en cada tabla + Decisión final (Aprobado/Rechazado).
- Form ahora en modo `landscape` para acomodar el diagrama + tabla ancha.

### 🍾 Control de Envasado · 8 horas + checkboxes coloreando celda (PDF pág 12)
- Nueva columna `observaciones` de tipo `checkbox_multi_color` en la tabla de inspecciones horarias con 4 opciones que colorean la celda:
  * **Fuga** (rojo #FCE8E8)
  * **Catado no conforme** (amarillo #FFF3D6)
  * **Cambio de color** (azul #DDEEFF)
  * **Sin observación** (verde #E6F5EA)
- 8 filas de inspección precargadas (correspondientes a 8 horas consecutivas de turno).
- La celda se colorea automáticamente cuando el operario marca uno o más motivos de observación.

### 🥃 Elab. Envejecidos y Destilados · Tabla horizontal 7×21 + firmas por mezclado (PDF pág 9)
- Rediseño completo del schema `aged_distilled_control`:
  * **Datos generales** en la parte superior: Producto · Cliente · Lote · Presentación (Envasado/Granel) · Lote de envasado.
  * **Tabla principal** con 7 columnas: `Parámetros · Especificaciones · Incertidumbre · Mezclado 1 · Mezclado 2 · Mezclado 3 · Mezclado 4`.
  * **21 filas** cubriendo todos los parámetros del PDF: Fecha, Lote, Hora, Operador, Tanque + fisicoquímicos (Volumen, °GL directo/destilado, pH, Color, Densidad, Viscosidad, Azúcar, Acidez, Dureza, Taninos, Aldehídos, Metanol, Fusel, Ésteres, Furfural, Congéneres) + sensoriales (Aspecto, Olor, Sabor) + firma Analista + Hora entrega resultados + Observaciones.
  * Las filas administrativas usan `_mergeSpec: true` → las celdas de Especificación e Incertidumbre se muestran con `—` gris y no editables (efecto "diagonal" pedido en PDF).
  * Firma automática por columna: el Analista que completa un Mezclado firma esa columna.
- Sección **Aprobado por** con notificación al superior.
- Subtabla **Verificación de producto previo al despacho** (SÓLO GRANELES) con Fecha · Grado · Color · Verificado por (Supervisor/Coordinador).

### 🔧 Extensiones al TableField genérico
- Nuevos tipos de columna soportados por el `TableField`:
  * `select_semaphore` (dropdown que colorea la celda + el input)
  * `checkbox_multi_color` (chips con checkbox que colorean celda por opción seleccionada)
  * `date` (input date en celdas de subtablas)
- Fila con `_mergeSpec: true` bloquea automáticamente las columnas `especificacion`/`incertidumbre`/`limite` (visual gris + no editable).
- `initFromSchema` ignora secciones tipo `container_diagram` (no crea entry en `data`).

### ✅ Tests iter21 (3/3 PASS) + iter19c (13/13 PASS)
- `test_isotank_inspection_with_semaphore_payload`: crea record con Bueno/Regular/Deficiente, verifica round-trip + PDF landscape.
- `test_packaging_control_8h_with_checkbox_observations`: crea 8 filas horarias con arrays multi-observación, verifica persistencia.
- `test_aged_distilled_7cols_4_mezclados_horizontal`: crea record con 4 mezclados poblados + verificación de despacho, verifica round-trip completo.

## Iter 20 · 05-Ago-2026 (P0 del PDF cambios05082026) ✅

### 🎨 Rebrand + Reorganización del menú (Pag 1-3)
- **"Laboratorio Central" → "ERP Empresarial"** en header, samples seed y placeholder de Instruments.
- **Sub-agrupadores en Espacios de Trabajo → Laboratorio y Calidad** (per PDF pág 2):
  * **Laboratorio** (8): Muestras, Ejecución, Lotes & CoA, Productos, Catálogo, Reactivos, Equipos, Instrumentos.
  * **Registros de Laboratorio** (12): CoA ES/EN, Envejecimiento, Pulpas, Contenedores, Triangular, Granel, Envasado, Isotanques, Catado, Insumos, Instalaciones, Agua.
  * **Almacén de Laboratorio** (4): Stock, Ubicaciones, Transferencias, Elab. Envejecidos y Destilados.
- Cada agrupador con título + contador; conserva `data-testid="lab-subgroup-{key}"` para QA.

### 💾 "Guardar como borrador" (Pag 3, item 13)
- Nuevo componente `DraftConfirm` en `LabFormPage.js` con 3 opciones al cerrar formulario dirty: **Volver al formulario · Cerrar sin guardar · Guardar como borrador**.
- Botón `X` del header y `Cancelar` del footer disparan el flujo (antes cerraban directamente).
- Backend `LabFormBody.status_hint: "draft"` — respeta el status forzado en `create` y `update` (excepto si ya está `approved`).
- El registro queda con `status="draft"` para continuarlo luego desde la lista.

### 🧪 Formulario Agua Osmotizada (Pag 4-5)
- Añadidos los 6 campos que faltaban en `datos generales` según la imagen del PDF: `fecha (req)`, `hora_entrega_muestra (req)`, `operador (req)`, `volumen`, `analista (req, autofirma)`, `hora_entrega_resultados`.
- Eliminada la sección "Cierre" duplicada; los campos migraron a Datos Generales para respetar el orden del formulario impreso.

### 🍇 Recepción de Pulpas (Pag 15)
- Añadidas columnas **Observaciones** y **Analista** a la tabla de Análisis fisicoquímico (antes sólo Parámetro/Límite/Método/Resultado).

### 🍷 Control Envejecimiento (Pag 13)
- Añadida fila **Fecha** al inicio de `defaultRows` con `_mergeSpec: true` (junto con Operador) para que el renderer fusione la columna Especificación de esos parámetros que no aplican.

### 🍸 Prueba Triangular (Pag 19)
- Añadida sección **"Instrucciones al panelista"** con el texto oficial del PDF ("Se presentan tres muestras codificadas, dos son idénticas...").
- Añadido campo **Trío** vacío editable para código del trío.
- Removido el "Trío 2" duplicado — sólo hay 1 trío por prueba según el PDF adjuntado.
- Nuevo tipo de field `info` en LabFormPage que renderiza cajas informativas con fondo ámbar suave.

### ✅ Suite iter17..iter19c: 22/22 PASS · Smoke visual completo
Verificación visual OK en 3 screenshots: sub-agrupadores en workspace/laboratory, campos nuevos en Agua Osmotizada, modal "¿Cerrar sin guardar?".

### 📌 Backlog del PDF cambios05082026 pendiente (item por item para próxima iteración)
- P1 · Formulario **Elab. Envejecidos y Destilados** con tabla horizontal 7×21 + Verificación previa despacho + firmas condicionales
- P1 · **Control de Envasado** con tabla 8 horas + checkboxes que colorean celda de observación
- P1 · **Insp. Isotanques + Insp. Contenedores** con imagen del contenedor/isotanque con puntos numerados + semáforo Bueno/Regular/Deficiente
- P1 · **Recepción a Granel** tabla 7 columnas × 19 filas con encabezados en primera fila
- P1 · **Insp/Recep Insumos** iconos ✓/✗/⊘ en PDF para Conforme/No Conforme/No Aplica
- P1 · **CoA bilingüe** completar todos los campos del PDF pág 7
- P2 · Permisos granulares (read/write/read+write) por pantalla + roles predefinidos
- P2 · Firma auto-cambia al editar + bloqueo de columnas ya llenadas
- P2 · EHS: imprimir con/sin evidencias · adjuntar 20 imágenes · calcular índices frecuencia/gravedad/severidad
- P2 · EPP: N items por entrega
- P2 · Aprobaciones: 2 sub-tabs (Pendientes + Aprobadas con descarga)
- P2 · Auditoría con filtros avanzados
- P2 · Dashboard ejecutivo con KPIs Inventario/Laboratorio/Seguridad + gráficos
- P3 · Exportar Lote a ZIP · Integración Microsoft 365 (Teams/Outlook/SharePoint)

## Iter 19c · 04-Ago-2026 (formularios pixel-perfect ✅)

### 🎨 Nuevo renderer PDF pixel-perfect
- Nuevo módulo `/app/backend/pdf_form_renderer.py` con `render_lab_form_pdf(record, schema, signature_file_path)`.
- **Header tri-columna** fiel al PDF adjunto: [Logo Yazoo 20mm] · [Company + título formulario + subtítulo] · [Doc-control (Código/Revisión/Página)]. Sub-tira ámbar bajo el header.
- **Meta strip compacta**: Código · Registrado por · Fecha · Estado (+ aprobación si existe) con fondos gris claro tipo formato controlado.
- **Sección con banner oscuro** ancho completo antes de cada bloque de campos o tabla.
- **Tablas con out-of-spec automático**: cualquier celda de resultado que exceda `especificacion`/`limite` se resalta con fondo rojo suave (`#FCE8E8`) y texto bold rojo (`#8B1E1E`).
- **Firmas con imagen embebida** al pie: hasta 3 firmantes por fila con línea horizontal separadora y nombre + rol + fecha en pequeño.
- **Footer controlado**: `Y-FO-CS-001 REV.01` · Documento controlado · Impreso YYYY-MM-DD HH:MM.

### 🖨️ Orientación landscape automática
Los formularios con tablas anchas se generan en **A4 landscape** (267 mm útiles):
- `water_analysis` (8 muestras por parámetro)
- `aging_process` (5 etapas de envejecimiento)
- `packaging_control` (11 columnas de inspección por hora)
- `aged_distilled_control` (18 parámetros × resultado × especificación)
- `bulk_reception` (parámetros × especificación × resultado matriz vertical)

El resto (`triangular_test`, `tasting_session`, `pulp_reception`, `container_inspection`, `isotank_inspection`, `input_reception`, `facility_inspection`, `coa_bilingual`) se mantiene en portrait.

### 🖥️ Modal frontend ancho para landscape forms
- `LabFormPage.js` detecta si `schema.formType ∈ WIDE_FORMS` y ensancha el modal a `max-w-[95vw]` (antes 5xl fijo). Al presionar "Nuevo Registro" el usuario ve la misma orientación horizontal que después imprimirá.

### 🔀 Routing lab_forms._record_to_pdf
- `_record_to_pdf` ahora usa el nuevo `pdf_form_renderer.render_lab_form_pdf` cuando existe un schema en `form_schemas.FORM_SCHEMAS`.
- `facility_inspection` mantiene su renderer specializado (31 filas Cumple/No Cumple).
- Fallback: `_record_to_pdf_generic` sigue disponible por si algún registro no tiene schema.

### ✅ Verificación visual (via pdf → png)
- water_analysis: A4 landscape 1170×827, header pixel-perfect, tabla 5 columnas para 8 filas de muestras.
- aging_process: A4 landscape 2 páginas, mostrando 5 etapas × 12 parámetros con out-of-spec resaltado sobre datos reales.
- triangular_test: A4 portrait, secciones con banner oscuro, autofirma del panelista.

**Todos los 12 formularios de laboratorio ahora generan PDFs fieles al diseño del formulario impreso adjuntado.**

## Iter 19b · 04-Ago-2026 (endurecimiento pre-demo)

### 🔴 Bug crítico: botón "Abrir" en Aprobaciones
- Al hacer clic sobre "Abrir" en un registro pendiente, el frontend construía `/lab-forms/{seg}?open={id}` pero `LabFormPage.js` no manejaba el query param `?open=`, quedando la lista abierta y el usuario sin formulario.
- Además, `ROUTE_BY_TYPE` en `Approvals.js` no incluía `water_analysis`, `aged_distilled_control` ni `coa_bilingual`, produciendo rutas rotas (`/lab-forms/water_analysis`).
- **Fix**: agregado hook `useSearchParams` en `LabFormPage.js` que hace `GET /lab-forms/records/{id}` y abre el modal en modo edición al detectar `?open=`; se limpia el param del URL tras abrir. `ROUTE_BY_TYPE` extendido a los 13 form_types.

### 🟢 Menú lateral simplificado
- Se eliminaron los items redundantes "Laboratorio" y "Registros de Lab." del sidebar (duplicaban la función de Espacios de Trabajo → Laboratorio y Calidad).
- Nuevo item **"Laboratorio y Calidad"** que apunta a `/workspace/laboratory`.
- Nuevo item **"Reportes Generales"** como módulo principal apuntando a `/reports/general`.
- `MODULE_SCREENS` de Layout consolidado: `laboratory` ahora contiene los 22 screens (LIMS + labforms + lab warehouse) que antes estaban repartidos.

### 🔒 Seguridad · AuthContext blindado
- **Eliminado el bypass offline con bcrypt** (`ylms_local_admin_bundle` en localStorage). Ya no se autentica contra hashes cacheados.
- Eliminada la caché offline del usuario (`ylms_offline_user`). Si el backend no responde, sesión limpia y logout.
- `logout()` ahora purga cualquier residuo legacy (bundle, offline user, backup tokens).
- **Test regresivo**: `Bearer offline-token` retorna 401 (imposible saltarse la autenticación).

### 📊 Widgets Vencimientos en Dashboard
- Nueva franja de 3 tarjetas en `Dashboard.js` alimentada por `GET /lab-warehouse/alerts`:
  * **Reactivos vencidos** (rojo)
  * **Por vencer (30 días)** (ámbar, con lista top-3 y contador de días)
  * **Stock bajo en Laboratorio** (info)
- Click en cualquier widget navega a `/lab-warehouse/stock` para gestión.

### 🚀 Documento de despliegue
- Nuevo `/app/DEPLOYMENT.md` con guía paso a paso para Windows Server:
  * Prerrequisitos (Python 3.11, Node 20, MSSQL 2019+ Express, ODBC Driver 17)
  * Creación de DB y usuario dedicado
  * Configuración `.env` con MONGO_URL para MSSQL usando `mssql+aioodbc`
  * Instalación como servicio Windows con NSSM
  * Deploy del frontend a IIS con `web.config` de reescritura SPA
  * Reglas de firewall y troubleshooting común
  * Credenciales de fábrica y protocolo de rotación

### ✅ Tests iter19b (4/4 PASS)
- `test_lab_warehouse_alerts_endpoint`
- `test_approvals_pending_items_all_have_frontend_route`
- `test_stale_offline_token_is_rejected`
- `test_lab_form_record_get_by_id_for_approvals_open`

**Suite iter16..iter19b: 23/23 PASS**

## Iter 19 · 04-Ago-2026 (post-demo continuación)

### 🟢 PDF Recetas de Producción (P0 pendiente)
- Nuevo módulo `/app/backend/pdf_recipe.py` con `recipe_to_pdf()`: header Yazoo + barra ámbar, meta grid, tabla BOM con subtotales/total, sección de instrucciones y línea de firma. ~56KB por PDF, imprimible A4.
- Nuevo endpoint `GET /api/production/recipes/{id}/pdf` (autenticado, con log_audit).
- Frontend `Recipes.js`: botón **PDF** por fila con `data-testid="rec-pdf-{code}"` que descarga el archivo.
- El módulo de Reportes Generales ya lo consumía (`pdf_url: /api/production/recipes/{id}/pdf`) — ahora sí funciona end-to-end.

### 🟢 Módulo "Laboratorio y Calidad" (agrupador)
- `Workspace.js` reorganizado: nuevo módulo `laboratory` (label: "Laboratorio y Calidad", icono `FlaskConical`) que agrupa TODOS los items lab: LIMS (muestras, ensayos, lotes, productos, pruebas, reactivos, equipos, instrumentos) + Registros de Laboratorio (12 formularios + CoA bilingüe) + Almacén de Laboratorio (stock, ubicaciones, transferencias).
- Se eliminaron los módulos separados `lims` y `labforms` de `MODULE_META`, todos sus screens ahora mapean a `laboratory`.
- Total: 24 opciones en el tile "Laboratorio y Calidad".

### 🟢 "Reportes Generales" como módulo principal
- Nuevo módulo `reports` de primer nivel en `MODULE_META` (icono `FileSearch`, color azul).
- `SCREEN_TO_MODULE["reports"] = "reports"`, ya no está dentro de "Sistema".
- Duplicado eliminado en `screens.py` (había dos entradas con key `reports`).

### ✅ Tests iter19 (5/5 PASS)
- `test_create_recipe` (roll-up de costo 50*150+50*3.5=7675 verificado)
- `test_recipe_pdf` (%PDF header, >5KB, content-type correcto)
- `test_admin_has_reports_and_lab_wh_screens`
- `test_reports_kinds_includes_recipe`
- `test_reports_search_recipes_have_pdf_url`

**Suite iter11..iter19: 45+ tests PASS.**

## Iter 18 · 04-Ago-2026 (día de entrega — continuación)

### 🟢 PDF Pixel-Perfect (schema-driven)
- Nuevo módulo `/app/backend/form_schemas.py` con `FORM_SCHEMAS` que refleja la estructura del frontend: `title`, `code`, `subtitle`, y `sections` cada una con `fields` o `columns/name` (tabla).
- `_record_to_pdf_generic` reescrito para iterar el schema en lugar de hacer un walker plano. Cada sección aparece con banner oscuro tipo Dynamics 365, y las tablas usan las columnas exactas del formulario. Los datos fuera del schema se anexan como "Datos adicionales".
- Los valores fuera de especificación se resaltan en rojo automáticamente para columnas de resultado.
- 12 schemas mapeados: aging_process, pulp_reception, container_inspection, triangular_test, bulk_reception, packaging_control, isotank_inspection, tasting_session, input_reception, facility_inspection, water_analysis, aged_distilled_control + coa_bilingual.

### 🟢 CoA Bilingüe Y-FO-CC-013
- Nuevo form_type `coa_bilingual` con schema completo:
  * Datos del producto (ES + EN)
  * Tabla fisicoquímica bilingüe con métodos, especificaciones y unidades
  * Tabla microbiológica bilingüe
  * Análisis sensorial (Appearance/Aroma/Taste)
  * Conclusión + autofirma del liberador
- Registrado en FORM_TYPES, FORM_SIGNATURE_SLOTS (analista + gerente de calidad), rutas frontend `/lab-forms/coa`, screen `lf_coa_bilingual`.

### 🟢 Almacén de Laboratorio (`/lab-warehouse/*`)
- Backend `/app/backend/routers/lab_warehouse.py` con 4 grupos:
  * **Ubicaciones** (`lab_locations`): anaqueles, neveras, congeladores, gavetas, gabinetes con temperatura y zona.
  * **Stock** (`lab_stock_items`): reactivos/consumibles/vidrio/soluciones/estándares con lote, vencimiento, cantidad, mínimo. Endpoint enriquece cada ítem con `expiry_days`, `expired`, `near_expiry` (30d), `low_stock`.
  * **Ajustes** (`lab_stock_movements`): traza cada cambio con motivo.
  * **Transferencias** (`lab_stock_transfers`) direction `from_central` / `to_central`: al completar actualiza automáticamente el stock del lab.
- **Alertas** (`/lab-warehouse/alerts`): resumen para dashboard con expired, near_expiry y low_stock counts + detalle.
- Frontend: 3 páginas (`LabWarehouseStock.js`, `LabWarehouseLocations.js`, `LabWarehouseTransfers.js`) con badges de estado (Vencido/Por vencer/Bajo/OK), filtros por tarjeta, form modal.

### ✅ Tests iter18 (4/4 PASS)
- `test_coa_bilingual_form_registered`
- `test_coa_bilingual_roundtrip_and_pdf` (verifica generación PDF con nuevo renderer)
- `test_lab_warehouse_full_flow` (locations → stock → adjust → alerts → transfer)
- `test_pdf_uses_schema_sections_for_water`

**Suite iter11..iter18: 40+ tests PASS.**

## Iter 17 · 04-Ago-2026 (día de entrega)

### 🔴 Bugs P0 corregidos
- **CRÍTICO: Aprobaciones no llegaban al módulo.** El endpoint `/approvals/pending` filtraba por `approval_required=True` que nunca se seteaba al crear registros. La creación guarda `status="pending_approval"` en su lugar. Corregido: query ahora filtra por `status IN ("pending_approval", "pending_review")`. Test iter17 verifica que un registro creado con `request_approval=True` aparece inmediatamente en el módulo.
- **CRÍTICO: Firmas automáticas quedaban vacías.** `_build_signatures` sólo firmaba si el rol del usuario aparecía en `role_hint` del slot; el rol `admin` no aparecía en ningún slot, por lo que ni siquiera el administrador podía firmar. **Fix**: admin y roles gerenciales (`admin`, `quality_manager`, `management`, `supervisor`, `director`, `coordinator`) firman como fallback CUALQUIER slot que el rol específico no cubre. Test verifica que admin firma el slot `analyst` de water_analysis.
- **Aprobaciones extendidas a más entidades**. El módulo ahora también muestra: órdenes de compra pendientes, transferencias de inventario pendientes y solicitudes de vacaciones pendientes (todas identificadas por `status`).

### 🔴 hideLinkedSample global (PDF pág. 7)
- Se agregó `hideLinkedSample: true` a **TODOS** los schemas de laboratorio: aging_process, pulp_reception, container_inspection, isotank_inspection, input_reception, facility_inspection, water_analysis, aged_distilled_control (además de los ya marcados en Iter 15).
- Ahora el campo "Muestra vinculada" ya no aparece en NINGÚN formulario según el requisito del PDF.

### 🟢 Módulo de Reportes Generales (`/reports/general`)
- Nuevo router `/app/backend/routers/reports.py` con endpoints `/reports/general/kinds` (categorías con conteos) y `/reports/general/search?q=&kind=&date_from=&date_to=` (búsqueda transversal).
- Cubre 12 fuentes: registros de laboratorio, facturas venta/compra, cotizaciones, órdenes venta/compra, transferencias inventario, recetas, CoA, lotes, vacaciones, incidentes EHS.
- Frontend `/app/frontend/src/pages/ReportsGeneral.js`: tiles por tipo, búsqueda por texto + rango de fechas, descarga de PDF nativo cuando el tipo lo soporta (mantiene fidelidad al diseño).

### ✅ Tests
- `test_iter17_approvals_and_reports.py` (4 tests):
  - `test_lab_form_request_approval_reaches_approvals_module` (verifica bugfix crítico)
  - `test_admin_signature_autofills_on_any_form`
  - `test_reports_module_search_and_kinds`
  - `test_purchase_order_pending_shows_in_approvals`
- **Suite iter11..iter17: 36/36 PASS**

### 📝 Pendientes conocidos del PDF (para post-demo)
- Rediseño visual completo de 6 formularios con orientación horizontal exacta a las fotos (aged_distilled, packaging, aging, bulk_reception, triangular, water_analysis): estructura ya coincide, falta pixel-perfect PDF horizontal.
- Nuevo formulario Y-FO-CC-013 "Certificado de Análisis" bilingüe ES/EN (existe uno genérico en `/coa`, se puede reforzar con el diseño del PDF).
- Fusión de "Registro de Inspección Recepción de Insumos" (Y-FO-CC-030) + "Certificado de Análisis Materia Prima" (Y-FO-CC-058) en un solo formulario doble cara.
- Módulo "Laboratorio y Calidad" con submódulos Almacén de Laboratorio (stock/ubicaciones, gestión de lotes, transferencias con almacén central, preparación de soluciones valoradas, consumibles/vidrio).
- PDF renderer con fidelidad "pixel-perfect" al schema visual (actual mapea key→value; falta orientar por sección UI).

## Iter 16 · 03-Ago-2026 (submódulos ERP)

### 🔴 Bugs P0 corregidos (demo mañana)
- **CRÍTICO: Pérdida de datos al editar registros de laboratorio.** El endpoint `GET /lab-forms/records` excluía el campo `data` de la lista (proyección `{"data": 0}`). Al hacer clic en "Editar", el frontend pasaba `initial.data = undefined` y `initFromSchema` devolvía un formulario vacío. **Solución:** función `openEdit()` en `LabFormPage.js` que hace `GET /lab-forms/records/{id}` para obtener el registro completo antes de abrir el modal. Los datos guardados ahora se preservan al editar.
- **Formularios nuevos invisibles como tiles.** `lf_water` y `lf_aged_distilled` faltaban en `SCREEN_TO_MODULE` de `Workspace.js`. Agregados → aparecen en Workspace → Registros de Laboratorio.
- **Botón Eliminar removido en registros de laboratorio.** Política Yazoo: los datos del ERP no se borran. El botón se reemplaza con toast informativo "Solicita anulación al administrador".

### 💱 Moneda y ITBIS
- Monedas soportadas: **DOP, USD, EUR** en Compras, Ventas, CxP, CxC, Órdenes.
- **IVA → ITBIS** en toda la UI y comentarios de código (18%).
- Backend `erp_purchases.py`: default `currency="DOP"` y `tax_rate=0.18`.

### 🟢 Submódulos nuevos (Iter 16)
- **Inventario → Transferencias entre Almacenes** (`/inventory/transfers`)
  - Flujo Pendiente → Aprobada → Completada con trazabilidad en `stock_movements`
  - No se permite origen=destino, no se pueden cancelar completadas
- **Inventario → Tanques y Silos** (`/inventory/tanks`)
  - CRUD con capacidad_L, volumen_actual_L, % llenado calculado
  - Actualizar volumen con validación de capacidad y log en `stock_movements`
  - Tipos: Almacenamiento / Fermentación / Envejecimiento / Mezcla
  - Vista tipo tarjetas con barra de llenado (verde <70%, amarillo 70-90%, rojo >90%)
- **Inventario → Cuarentena / Bloqueo de Lotes** (`/inventory/quarantine`)
  - Retención de lotes con estado (quarantined → released / rejected)
  - Actualiza `quarantine_status` en `batches` para bloquear despacho
- **Producción → Recetas / Fórmulas (BOM)** (`/production/recipes`)
  - CRUD con versionado (`new-version` archiva la anterior)
  - Cálculo automático de costo total y costo unitario
  - **MRP básico**: explosión de componentes por cantidad objetivo
- **RRHH → Vacaciones y Permisos** (`/hr/vacations`)
  - Solicitudes con cálculo automático de días
  - Aprobación/Rechazo, KPIs por estado
- **RRHH → Organigrama** (`/hr/organigram`)
  - Vista jerárquica plegable basada en `manager_id`
  - Asignar/quitar manager desde la UI

### 🔧 Backend nuevos routers
- `/app/backend/routers/inventory_ops.py` — transferencias, tanques, cuarentena
- `/app/backend/routers/recipes.py` — recetas + MRP
- `/app/backend/routers/hr_ext.py` — vacaciones + organigrama
- `/app/backend/db.py` — 4 colecciones nuevas: `tanks`, `batch_quarantines`, `vacations` (+ `inventory_transfers`, `recipes` de Iter 15)
- `/app/backend/screens.py` — 7 screens nuevas: `inv_transfers`, `inv_tanks`, `inv_quarantine`, `prod_recipes`, `hr_vacations`, `hr_organigram`, `sales_orders`, `finance_ap`, `finance_ar`

### 🖥️ Frontend nuevas páginas
- `InventoryTransfers.js`, `InventoryTanks.js`, `InventoryQuarantine.js`
- `Recipes.js` (con modal MRP)
- `HRVacations.js`, `HROrganigram.js` (flatten iterativo, sin recursión de componente)

### ✅ Tests
- `test_iter16_bugfixes_and_submodules.py` (6 tests):
  - `test_edit_endpoint_returns_full_data` (verifica bugfix crítico)
  - `test_inventory_transfer_flow` (create → approve → complete)
  - `test_tank_capacity_and_fill` (fill_pct auto-calculado)
  - `test_batch_quarantine_and_release`
  - `test_recipe_with_versioned_bom`
  - `test_vacation_request_flow` (create + approve)
- **Suite iter11..iter16: 32/32 PASS**

## Iter 15 · 03-Ago-2026 (pre-demo Yazoo)

### 🔴 Bloqueadores P0 resueltos
- **Frontend en blanco por temporal-dead-zone en `schemas.js`**: `ALL_SCHEMAS` referenciaba `waterAnalysisSchema` y `agedDistilledControlSchema` antes de ser declaradas. Se movió el registro maestro al final del archivo.
- **Test `test_new_form_types_registered` fallando**: el endpoint `/api/lab-forms/types` devuelve lista, no dict. Se corrigió el test para iterar el arreglo.

### 📝 Cambios del PDF `cambio-082026.pdf` (formularios)
- **Aging Process (Y-FO-CO-001)** — parametros ahora incluye Operador, Aspecto, Olor, Sabor, Analista, Observación como filas por etapa.
- **Prueba Triangular (Y-FO-CC-007)** — rediseño: Trío 1 y Trío 2 con selector A/B/C independiente + grado de confianza (Muy seguro/Seguro/Poco seguro). Autofirma del panelista en "nombre" y "cata_preparada_por". Se removieron firmas por rol y campo "muestra vinculada".
- **Sesiones Catado (Y-FO-CC-008)** — sin firmas por rol, sin muestras vinculadas, `verificado_por` autofirmado por usuario.
- **Recepción Granel (Y-FO-CC-011)** — agregado campo Mes y tabla vertical Parámetro / Especificación / Resultado. Decisión Aprobado/Rechazado + firma calidad proveedor.
- **Control de Envasado (Y-FO-CC-034)** — tabla ARRANQUE DE LINEA con 8 filas por hora (grado/capacidad/color/nm/dureza/turbidez/viscosidad/fuga/catado/pto llenado) + trazabilidad de lote separada.

### 🟢 Submódulos nuevos Alta Prioridad
- **Finanzas → Cuentas por Pagar** (`/finance/ap`)
  - CRUD facturas de proveedor (NCF, emitida, vence, subtotal, ITBIS, total, moneda, notas)
  - Registro de pagos parciales con actualización de saldo y estado (pending → partial → paid)
  - Reporte de antigüedad (aging) con buckets 0-30 / 31-60 / 61-90 / >90 días
- **Finanzas → Cuentas por Cobrar** (`/finance/ar`)
  - Extiende `sales_invoices` con cobros aplicados (`ar_payments`)
  - Muestra Cobrado / Saldo calculados en línea
  - Reporte de antigüedad idéntico a CxP
- **Ventas → Órdenes de Venta** (`/sales/orders`)
  - Flujo Borrador → Confirmada → Despachada → Facturada (transiciones validadas)
  - Al facturar auto-crea `sales_invoices` con estado `issued`
  - KPIs por estado + valor abierto

### 🔧 Backend
- `/app/backend/routers/finance_ap_ar.py` (nuevo) — routers `/finance/ap` y `/finance/ar` con aging y pagos
- `/app/backend/routers/sales_orders.py` (nuevo) — router `/sales/orders` con máquina de estados
- `/app/backend/db.py` — nuevas colecciones: `ap_invoices`, `ap_payments`, `ar_payments`, `sales_orders`, `inventory_transfers`, `recipes`
- `/app/backend/screens.py` — 3 nuevas screens: `finance_ap`, `finance_ar`, `sales_orders`
- `/app/backend/routers/lab_forms.py` — `triangular_test` y `tasting_session` con `signature_slots: []` + autofill panelista

### 🖥️ Frontend
- `/app/frontend/src/pages/FinanceAP.js`, `FinanceAR.js`, `SalesOrders.js` (nuevos)
- `/app/frontend/src/pages/labforms/schemas.js` — 5 schemas rediseñados + soporte `hideLinkedSample`
- `/app/frontend/src/pages/labforms/LabFormPage.js` — respeta `hideLinkedSample`, autofirma amplida a `nombre`, `cata_preparada_por`, `preparada_por`, `panelista`
- `/app/frontend/src/App.js` — 3 rutas nuevas
- `/app/frontend/src/components/Layout.js` — MODULE_SCREENS extendido
- `/app/frontend/src/pages/Workspace.js` — SCREEN_ICON / SCREEN_TO_ROUTE / SCREEN_TO_MODULE actualizados

### ✅ Tests
- `test_iter15_pdf_form_changes.py` (3 tests) — sin firmas rol tasting/triangular, autofirma panelista, bulk_reception acepta `mes`
- `test_iter15_submodules.py` (3 tests) — flujo CxP completo con aging, órdenes de venta con state machine y factura auto-creada, aplicación de cobros CxC
- **Suite iter11..iter15: 26 tests PASS**

## Iter 14 · Ago 2026
- Formularios nuevos Y-FO-CC-012 (Análisis Agua) y Y-FO-CC-009 (Envejecidos y Destilados).

## Iter 13 · Feb 2026
- EHS extendido: Incidentes/Casi-accidentes, EPP, Inspecciones, `/ehs/dashboard`.
- Inventario extendido: Kardex, Conteo físico con ajustes automáticos.

## Iter 12 · Feb 2026
- Sidebar plegable, botón Volver, BUG 500 empleado, QR en PDF, auto-códigos, aprobación de compras.

## Iter 11 y previos
Sidebar 15 módulos Dynamics 365, Cotización PDF bilingüe, Mantenimiento Calendario, Logística, I+D, Workspace, Nómina RD 2026, EHS Accidentes, Firmas, CoA bilingüe.

## Pendientes post-demo (backlog priorizado)
1. **Inventario → Transferencias entre Almacenes** (colección `inventory_transfers` ya creada; UI pendiente)
2. **Producción → Recetas / Fórmulas** (colección `recipes` ya creada; UI pendiente)
3. Producción → MRP básico (explosión BOM)
4. RRHH → Organigrama visual + Vacaciones y Permisos
5. Compras → RFQ multi-proveedor
6. I+D extendido: Fichas Experimentación, Análisis Sensorial, QC Inicial
7. Seguridad Industrial: MSDS, Capacitaciones SST, Permisos de trabajo, Incidentes ambientales
8. Endurecer Modo Offline: revisar `bcryptjs` en `AuthContext.js`

## Credenciales
`admin@yazoo.com` / `Admin123!`. Ver `/app/memory/test_credentials.md`.

## Despliegue local (para la demo de mañana)
Ver **`/app/DESPLIEGUE_WINDOWS.md`**.
