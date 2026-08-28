"""Definiciones de schema del lado backend usadas por el generador de PDF
pixel-perfect y por endpoints introspectivos.

Cada schema describe la MISMA estructura que la usada por el frontend en
`/app/frontend/src/pages/labforms/schemas.js`, pero recortada a lo necesario
para renderizar el PDF fielmente: título, código, subtítulo y una lista de
`sections`. Cada sección puede ser:

  * type == "fields" (default): renderiza label + value en dos columnas.
  * type == "table": renderiza una tabla horizontal con las `columns` dadas
    y las filas provistas en `data[section.name]`.

La versión python contiene lo esencial (títulos + campos + tablas). Esto
permite generar PDF fiel al diseño sin tener que ejecutar JavaScript.
"""
from typing import Any, Dict, List, Optional


def F(name: str, label: str, ftype: str = "text", **extra) -> Dict[str, Any]:
    return {"name": name, "label": label, "type": ftype, **extra}


def C(key: str, label: str, ctype: str = "text", **extra) -> Dict[str, Any]:
    return {"key": key, "label": label, "type": ctype, **extra}


def SEC(title: str, fields=None, columns=None, name=None, default_rows=None) -> Dict[str, Any]:
    d: Dict[str, Any] = {"title": title}
    if columns:
        d.update({"type": "table", "name": name or "rows",
                  "columns": columns, "default_rows": default_rows or []})
    else:
        d.update({"type": "fields", "fields": fields or []})
    return d


FORM_SCHEMAS: Dict[str, Dict[str, Any]] = {}


# -------------------- Water analysis --------------------
FORM_SCHEMAS["water_analysis"] = {
    "form_type": "water_analysis",
    "code": "Y-FO-CC-012",
    "title": "Análisis de Calidad del Agua Osmotizada",
    "subtitle": "Rev. 04 · Control diario de conductividad, pH y dureza",
    "sections": [
        SEC("Identificación", fields=[
            F("fecha", "Fecha", "date"),
            F("operador", "Operador"),
            F("volumen", "Volumen tratado"),
        ]),
        SEC("Parámetros por muestra", columns=[
            C("hora", "Hora"),
            C("conductividad", "Conductividad (µS/cm)", "number"),
            C("ph", "pH", "number"),
            C("dureza", "Dureza (ppm CaCO₃)", "number"),
            C("observacion", "Observación"),
        ], name="muestras", default_rows=[{"hora": ""} for _ in range(8)]),
        SEC("Firma", fields=[F("analista", "Analista responsable")]),
    ],
}


# -------------------- Aged & distilled --------------------
FORM_SCHEMAS["aged_distilled_control"] = {
    "form_type": "aged_distilled_control",
    "code": "Y-FO-CC-009",
    "title": "Control de Elaboración · Productos Envejecidos y Destilados",
    "subtitle": "Rev. 08 · Registro por lote — físico-químico y sensorial",
    "sections": [
        SEC("Datos generales", fields=[
            F("producto", "Producto"), F("cliente", "Cliente"), F("lote", "Lote"),
            F("presentacion", "Presentación (Envasado / Granel)"),
            F("tanque", "Tanque origen"), F("fecha", "Fecha", "date"),
        ]),
        SEC("Parámetros físico-químicos", columns=[
            C("parametro", "Parámetro"), C("especificacion", "Especificación"),
            C("resultado", "Resultado"), C("estado", "Estado"),
        ], name="parametros"),
        SEC("Evaluación sensorial", fields=[
            F("aspecto", "Aspecto"), F("olor", "Olor"), F("sabor", "Sabor"),
        ]),
        SEC("Verificación previa al despacho (SÓLO GRANELES)", fields=[
            F("verif_aprobado_por", "Aprobado por"),
            F("verif_fecha", "Fecha verificación", "date"),
            F("verif_grado", "Grado"), F("verif_color", "Color"),
            F("verif_verificado_por", "Verificado por"),
        ]),
    ],
}


# -------------------- Aging process --------------------
FORM_SCHEMAS["aging_process"] = {
    "form_type": "aging_process",
    "code": "Y-FO-CO-001",
    "title": "Control de Proceso Envejecimiento",
    "subtitle": "Rev. 01 · Seguimiento fisicoquímico y sensorial",
    "sections": [
        SEC("Identificación", fields=[
            F("lote_serie", "N° Lote / N° Serie"), F("serie", "Serie"),
            F("fecha_inicio", "Fecha de inicio", "date"),
            F("fecha_vaciado", "Fecha de vaciado", "date"),
        ]),
        SEC("Parámetros por etapa de envejecimiento", columns=[
            C("parametro", "Parámetro"), C("especificacion", "Especificación"),
            C("env1", "Envej. 1"), C("env2", "Envej. 2"), C("env3", "Envej. 3"),
            C("env4", "Envej. 4"), C("env5", "Envej. 5"),
        ], name="parametros"),
        SEC("Firma", fields=[F("analista", "Analista responsable")]),
    ],
}


# -------------------- Triangular test --------------------
FORM_SCHEMAS["triangular_test"] = {
    "form_type": "triangular_test",
    "code": "Y-FO-CC-007",
    "title": "Prueba Triangular",
    "subtitle": "Rev. 05 · 3 muestras codificadas por trío, 2 idénticas y 1 diferente",
    "sections": [
        SEC("Datos", fields=[
            F("fecha", "Fecha", "date"),
            F("nombre", "Nombre del panelista (autofirma)"),
            F("producto_evaluado", "Producto evaluado"),
        ]),
        SEC("Identificación de la muestra diferente", fields=[
            F("trio1_muestra_diferente", "Trío 1 · Muestra diferente"),
            F("trio1_grado_confianza", "Trío 1 · Grado de confianza"),
            F("trio2_muestra_diferente", "Trío 2 · Muestra diferente"),
            F("trio2_grado_confianza", "Trío 2 · Grado de confianza"),
        ]),
        SEC("Evaluación del color", fields=[F("percepcion_color", "Percepción del color")]),
        SEC("Evaluación del sabor", fields=[
            F("nivel_dulzor", "Nivel del dulzor"),
            F("persistencia_boca", "Persistencia en boca"),
        ]),
        SEC("Evaluación del aroma", fields=[
            F("complejidad_aromatica", "Complejidad aromática"),
            F("sensaciones_destacadas", "Sensaciones destacadas"),
            F("notas_predominantes", "Notas predominantes"),
        ]),
        SEC("Cata Preparada · autofirma del panelista", fields=[
            F("caracteristicas_destacables", "Características destacables"),
            F("cata_preparada_por", "Cata preparada por (autofirma)"),
        ]),
    ],
}


# -------------------- Bulk reception (Y-FO-CC-011) · 7×19 horizontal --------------------
FORM_SCHEMAS["bulk_reception"] = {
    "form_type": "bulk_reception",
    "code": "Y-FO-CC-011",
    "title": "Recepción Productos a Granel",
    "subtitle": "Rev. 05 · Registro horizontal por lote — parámetros vs especificación",
    "sections": [
        SEC("Datos generales y análisis por lote · Tabla 7 columnas × 19 filas",
            columns=[
                C("parametro",      "Parámetro"),
                C("especificacion", "Especificación"),
                C("incertidumbre",  "Incertidumbre"),
                C("proveedor_1",    "Proveedor · Lote 1"),
                C("proveedor_2",    "Proveedor · Lote 2"),
                C("yazoo_1",        "Yazoo · Recep. 1"),
                C("yazoo_2",        "Yazoo · Recep. 2"),
            ], name="registros", default_rows=[
                {"parametro": "Producto"}, {"parametro": "Mes"},
                {"parametro": "Fecha"}, {"parametro": "Proveedor"},
                {"parametro": "N° Contenedor"},
                {"parametro": "Grado alcohólico despachado (CoA)"},
                {"parametro": "Lote (Proveedor)"}, {"parametro": "Lote (Yazoo)"},
                {"parametro": "Tanque receptor N°"},
                {"parametro": "Volumen recibido (L)"},
                {"parametro": "Grado alcohólico medido, °GL"},
                {"parametro": "pH"}, {"parametro": "Acetaldehído"},
                {"parametro": "Metanol"}, {"parametro": "Fuseles"},
                {"parametro": "Ésteres"}, {"parametro": "Furfural"},
                {"parametro": "Congéneres totales"},
                {"parametro": "Acidez total"}, {"parametro": "Taninos"},
                {"parametro": "Color, %T 450 nm"},
            ]),
        SEC("Decisión y firmas", fields=[
            F("decision_final", "Aprobado / Rechazado"),
            F("firma_calidad_proveedor", "Firma calidad del proveedor"),
            F("observaciones_recepcion", "Observaciones"),
            F("firma_calidad", "Analista de calidad Yazoo (autofirma)"),
        ]),
    ],
}


# -------------------- Packaging control --------------------
FORM_SCHEMAS["packaging_control"] = {
    "form_type": "packaging_control",
    "code": "Y-FO-CC-034",
    "title": "Control de Envasado",
    "subtitle": "Rev. 06 · Arranque de línea, parámetros y trazabilidad del lote",
    "sections": [
        SEC("Datos generales", fields=[
            F("producto", "Producto"), F("linea", "Línea"), F("lote", "Lote"),
            F("fecha", "Fecha", "date"),
            F("lote_elaboracion", "Lote de elaboración"),
            F("hora_final", "Hora final"),
        ]),
        SEC("Arranque de línea · chequeo previo", fields=[
            F("me_produccion_anterior", "¿Existe ME de producción anterior?"),
            F("epp_alimentacion", "¿Personal alimentación tiene EPP?"),
            F("epp_llenado", "¿Personal llenado tiene TB, gorro y guantes?"),
            F("area_limpieza", "¿Área de llenado en orden y limpieza?"),
        ]),
        SEC("Arranque de línea · inspecciones por hora", columns=[
            C("hora", "Hora"), C("grado_gl", "Grado (°GL)"),
            C("capacidad_ml", "Capacidad (mL)"), C("color", "Color"),
            C("nm_abs_t", "nm Abs/%T"), C("dureza_ppm", "Dureza (ppm)"),
            C("turbidez_ntu", "Turbidez (NTU)"), C("viscosidad_cp", "Viscosidad (cP)"),
            C("fuga", "Fuga"), C("catado", "Catado"), C("pto_llenado", "Pto llenado"),
        ], name="inspecciones"),
        SEC("Trazabilidad del lote", fields=[
            F("codigo_previo", "¿Sin código previo?"),
            F("codigo_qr", "Código QR"), F("etiquetas", "Etiquetas"),
            F("estado_cajas", "Estado de cajas"),
            F("fecha_envasado", "Fecha de envasado", "date"),
            F("hora_envasado", "Hora de envasado"),
            F("codigo_caja", "Código de caja"),
            F("sellado_cajas", "Sellado de cajas"), F("destino", "Destino"),
        ]),
        SEC("Observaciones", fields=[F("observaciones_envasado", "Observaciones")]),
        SEC("Firmas", fields=[
            F("analista_inspector", "Analista / inspector (autofirma)"),
            F("revisado_por", "Revisado por"),
        ]),
    ],
}


# -------------------- Tasting session --------------------
FORM_SCHEMAS["tasting_session"] = {
    "form_type": "tasting_session",
    "code": "Y-FO-CC-008",
    "title": "Registro Sesiones de Catado",
    "subtitle": "Rev. 03 · Consolidación estadística de una sesión de cata",
    "sections": [
        SEC("Datos", fields=[
            F("fecha", "Fecha", "date"),
            F("muestra_catada", "Muestra catada"),
            F("lote", "Lote"),
        ]),
        SEC("Estadísticas de la cata", fields=[
            F("n_catadores", "N° de catadores"),
            F("n_pruebas", "N° de pruebas"),
            F("n_aciertos", "N° de aciertos"),
            F("confiabilidad_pct", "% de confiabilidad"),
            F("indice_aceptacion", "Índice aceptación / rechazo"),
        ]),
        SEC("Conclusión", fields=[
            F("conclusion", "Conclusión (Aprobado / Rechazado)"),
            F("verificado_por", "Verificado por (autofirma)"),
        ]),
    ],
}


# -------------------- Pulp reception --------------------
FORM_SCHEMAS["pulp_reception"] = {
    "form_type": "pulp_reception",
    "code": "Y-FO-CC-058",
    "title": "Certificado de Análisis - Recepción de Pulpas",
    "subtitle": "Evaluación sensorial y fisicoquímica de pulpa/puré de fruta",
    "sections": [
        SEC("Datos generales", fields=[
            F("fecha", "Fecha", "date"), F("proveedor", "Proveedor"),
            F("producto", "Producto"), F("lote", "Lote"),
            F("cantidad_recibida", "Cantidad recibida"),
        ]),
        SEC("Análisis fisicoquímico", fields=[
            F("brix", "°Brix"), F("ph", "pH"),
            F("acidez", "Acidez"), F("color", "Color"), F("olor", "Olor"),
        ]),
        SEC("Decisión", fields=[
            F("decision", "Aceptado / Rechazado"),
            F("analista", "Analista"),
        ]),
    ],
}


# -------------------- Container inspection --------------------
FORM_SCHEMAS["container_inspection"] = {
    "form_type": "container_inspection",
    "code": "Y-FO-SI-004",
    "title": "Inspección de Contenedores (Camión), Isotanque y Chasis/Remolque",
    "subtitle": "Rev. 01 · Inspección de 7 puntos previa y posterior a la carga",
    "sections": [
        SEC("Datos", fields=[
            F("fecha", "Fecha", "date"), F("placa", "Placa / Identificación"),
            F("chofer", "Chofer"), F("empresa", "Empresa"),
        ]),
        SEC("Puntos de inspección", fields=[
            F(f"punto_{i}", f"Punto {i}") for i in range(1, 8)
        ]),
        SEC("Resultado", fields=[
            F("resultado", "Resultado (Cumple/No Cumple)"),
            F("inspector", "Inspector (autofirma)"),
        ]),
    ],
}


# -------------------- Isotank inspection --------------------
FORM_SCHEMAS["isotank_inspection"] = {
    "form_type": "isotank_inspection",
    "code": "Y-FO-CC-038",
    "title": "Inspección de Isotanques, Cisternas y Contenedores (Camión)",
    "subtitle": "Rev. 00 · Checklist previo a la carga",
    "sections": [
        SEC("Datos", fields=[
            F("fecha", "Fecha", "date"), F("isotank", "Isotanque N°"),
            F("chofer", "Chofer"), F("producto", "Producto a cargar"),
        ]),
        SEC("Checklist", columns=[
            C("item", "Item"), C("resultado", "Resultado"), C("observacion", "Observación"),
        ], name="checklist"),
        SEC("Firmas", fields=[F("inspector", "Inspector (autofirma)")]),
    ],
}


# -------------------- Input reception (Y-FO-CC-030) · Iconos ✓/✗/⊘ --------------------
FORM_SCHEMAS["input_reception"] = {
    "form_type": "input_reception",
    "code": "Y-FO-CC-030",
    "title": "Registro de Inspección · Recepción de Insumos",
    "subtitle": "Rev. 02 · Muestreo AQL + inspección visual/física/documental",
    "sections": [
        SEC("Datos generales", fields=[
            F("fecha", "Fecha", "date"), F("hora", "Hora"),
            F("proveedor", "Proveedor"), F("cliente", "Cliente"),
            F("inspector_calidad", "Inspector de calidad"),
            F("placa_no", "Placa N°"),
            F("no_orden_conduce", "N° Orden / Conduce"),
            F("responsable_recepcion", "Responsable recepción"),
        ]),
        SEC("I. Identificación del insumo", fields=[
            F("tipo_insumo", "Tipo de insumo"),
            F("nombre_insumo", "Nombre del insumo"),
            F("mercado_destino", "Mercado destino"),
            F("lote_proveedor", "Lote proveedor"),
            F("cantidad_recibida", "Cantidad recibida"),
            F("unidad", "Unidad"),
            F("condicion_transporte", "Condición del transporte"),
            F("obs_identificacion", "Observaciones"),
        ]),
        SEC("II. Muestreo aplicado", fields=[
            F("tamano_lote", "Tamaño del lote"),
            F("nivel_inspeccion", "Nivel de inspección"),
            F("aql", "AQL"), F("tamano_muestra", "Tamaño de muestra"),
            F("tipo_inspeccion", "Tipo de inspección"),
            F("obs_muestreo", "Observaciones"),
        ]),
        SEC("III. Criterios · Botellas / Tapas / Corchos", columns=[
            C("criterio", "Criterio"),
            C("resultado", "Resultado"),
            C("observaciones", "Observaciones"),
        ], name="criterios_botellas", default_rows=[
            {"criterio": "Integridad física"}, {"criterio": "Limpieza"},
            {"criterio": "Dimensión / acabado"}, {"criterio": "Compatibilidad"},
            {"criterio": "Contenido neto"}, {"criterio": "Apariencia superficie"},
            {"criterio": "Diseño y color"}, {"criterio": "Fuga"},
            {"criterio": "Porosidad"}, {"criterio": "Ajuste"},
            {"criterio": "Olor"},
        ]),
        SEC("Etiquetas / Cajas / Separadores / Termoencogibles", columns=[
            C("criterio", "Criterio"),
            C("resultado", "Resultado"),
            C("observaciones", "Observaciones"),
        ], name="criterios_etiquetas", default_rows=[
            {"criterio": "Diseño correcto"}, {"criterio": "Impresión / color"},
            {"criterio": "Adhesión"}, {"criterio": "Integridad del empaque"},
            {"criterio": "Peso / gramaje"}, {"criterio": "Etiquetado legible"},
        ]),
        SEC("Decisión y firmas", fields=[
            F("decision", "Aprobado / Rechazado"),
            F("inspector_firma", "Inspector (autofirma)"),
            F("aprobado_por", "Aprobado por"),
        ]),
    ],
}


# -------------------- CoA bilingüe (Y-FO-CC-013) · Rev 03 --------------------
FORM_SCHEMAS["coa_bilingual"] = {
    "form_type": "coa_bilingual",
    "code": "Y-FO-CC-013",
    "title": "Certificado de Análisis · Certificate of Analysis",
    "subtitle": "Rev. 03 · Documento bilingüe ES/EN para exportación",
    "sections": [
        SEC("Datos del cliente · Customer Details", fields=[
            F("nombre_cliente", "Nombre del cliente · Customer name"),
            F("destino_envio", "Destino de envío · Ship-to destination"),
        ]),
        SEC("Identificación de la(s) muestra(s) · Sample Identification", fields=[
            F("id_muestras", "Identificación de la(s) muestra(s) · Sample ID(s)"),
            F("tipo_muestra", "Tipo de muestra · Sample type"),
            F("condiciones_iniciales", "Condiciones iniciales · Initial conditions"),
            F("caract_organolepticas", "Características organolépticas · Organoleptic characteristics"),
        ]),
        SEC("Datos del Producto · Product Details", fields=[
            F("producto_es", "Producto · Product"),
            F("producto_en", "Product name (EN)"),
            F("lote", "Lote · Batch N°"),
            F("cantidad_fabricada", "Cantidad fabricada · Manufactured qty"),
            F("fecha_fabricacion", "Fecha de fabricación · Manufacture date", "date"),
            F("fecha_vencimiento", "Fecha de vencimiento · Expiry date", "date"),
            F("fecha_recepcion", "Fecha de recepción · Reception date", "date"),
            F("fecha_ejecucion", "Fecha de ejecución del análisis · Analysis date", "date"),
        ]),
        SEC("Análisis Fisicoquímico · Physicochemical Analysis", columns=[
            C("parameter", "Parámetro · Parameter"),
            C("method", "Método · Method"),
            C("specification", "Especificación · Spec"),
            C("result", "Resultado · Result"),
            C("units", "Unidades · Units"),
        ], name="physchem", default_rows=[
            {"parameter": "Fuerza real · Real strength (°GL)", "units": "%v/v"},
            {"parameter": "pH", "units": ""},
            {"parameter": "Acidez total · Total acidity", "units": "mg/100mL AA"},
            {"parameter": "Metanol · Methanol", "units": "mg/100mL AA"},
            {"parameter": "Fusel total · Higher alcohols", "units": "mg/100mL AA"},
            {"parameter": "Ésteres · Esters", "units": "mg/100mL AA"},
            {"parameter": "Aldehídos · Aldehydes", "units": "mg/100mL AA"},
            {"parameter": "Furfural · Furfural", "units": "mg/100mL AA"},
            {"parameter": "Color a 450 nm · Color at 450 nm", "units": "%T"},
        ]),
        SEC("Análisis Microbiológico · Microbiological Analysis", columns=[
            C("parameter", "Parámetro · Parameter"),
            C("method", "Método · Method"),
            C("specification", "Límite máx · Max limit"),
            C("result", "Resultado · Result"),
            C("units", "Unidades · Units"),
        ], name="micro", default_rows=[
            {"parameter": "Aerobios totales · Total aerobic count", "units": "UFC/mL"},
            {"parameter": "Levaduras y hongos · Yeasts & molds", "units": "UFC/mL"},
            {"parameter": "Coliformes · Coliforms", "units": "UFC/mL"},
        ]),
        SEC("Análisis Sensorial · Sensory Analysis", fields=[
            F("appearance", "Aspecto · Appearance"),
            F("aroma", "Aroma · Aroma"),
            F("taste", "Sabor · Taste"),
        ]),
        SEC("Desviaciones · Deviations & Exclusions", fields=[
            F("desviaciones", "Desviaciones adicionales o exclusiones de métodos · Deviations"),
        ]),
        SEC("Conclusión · Conclusion", fields=[
            F("conclusion", "Cumple con especificaciones · Meets specifications"),
            F("notes", "Observaciones · Notes"),
        ]),
        SEC("Firmas por rol · Signatures (auto-filled)", fields=[
            F("released_by", "Analista responsable · Lab analyst (autofirma)"),
            F("approved_by", "Gerente de Calidad · Quality Manager (aprueba)"),
        ]),
    ],
}


# -------------------- Facility inspection --------------------
FORM_SCHEMAS["facility_inspection"] = {
    "form_type": "facility_inspection",
    "code": "Y-FO-BI-018",
    "title": "Inspección de las Instalaciones",
    "subtitle": "Rev. 02 · Checklist BPM Yazoo",
    "sections": [
        SEC("Datos", fields=[
            F("fecha", "Fecha", "date"), F("area", "Área inspeccionada"),
            F("inspector", "Inspector"),
        ]),
        SEC("Checklist BPM (31 puntos)", columns=[
            C("item", "Punto"), C("cumple", "Cumple / No cumple"),
            C("observacion", "Observación"),
        ], name="checklist"),
        SEC("Cierre", fields=[
            F("inspector_firma", "Inspector (autofirma)"),
            F("responsable_firma", "Responsable del área"),
        ]),
    ],
}


def get_schema(form_type: str) -> Optional[Dict[str, Any]]:
    return FORM_SCHEMAS.get(form_type)
