"""Catálogo centralizado de errores SIM — base de conocimiento del simulador NEXA."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorEntry:
    code: str
    type: str
    title: str
    description: str
    solution: str


CATALOG: dict[str, ErrorEntry] = {
    # Upload / Archivo
    "SIM-00200": ErrorEntry("SIM-00200", "EXCEL_LIMIT_EXCEEDED", "Archivo demasiado grande", "El archivo supera el tamaño máximo permitido para la carga.", "Reduzca el tamaño del archivo o contacte al administrador para revisar el límite configurado."),
    "SIM-00201": ErrorEntry("SIM-00201", "UPLOAD_ERROR", "Extensión de archivo no permitida", "La extensión del archivo no está en la lista de tipos permitidos (.xlsx, .xls).", "Asegúrese de subir un archivo Excel con extensión .xlsx (recomendado) o .xls."),
    "SIM-00202": ErrorEntry("SIM-00202", "UPLOAD_ERROR", "Prefijo de nombre de archivo incorrecto", "El nombre del archivo no comienza con el prefijo esperado para el módulo (HR-, GN- u OP-).", "Renombre el archivo para que comience con el prefijo correcto: 'HR-', 'GN-' u 'OP-' según el módulo."),
    "SIM-00203": ErrorEntry("SIM-00203", "INVALID_EXCEL_FILE", "Archivo Excel demasiado pequeño", "El archivo es demasiado pequeño para ser un Excel válido.", "Verifique que el archivo no esté vacío o corrupto y vuelva a descargarlo desde la fuente original."),
    "SIM-00204": ErrorEntry("SIM-00204", "ENCRYPTED_EXCEL_FILE", "Archivo cifrado o formato .xls legacy", "El archivo está cifrado, protegido con contraseña o es un .xls en formato OLE/CFBF legacy.", "Abra el archivo en Excel, quítele la contraseña si la tiene y guárdelo como .xlsx (sin contraseña)."),
    "SIM-00205": ErrorEntry("SIM-00205", "INVALID_EXCEL_FILE", "Archivo PDF con extensión .xlsx", "El archivo tiene extensión .xlsx pero en realidad es un documento PDF.", "Asegúrese de exportar el archivo correctamente desde Excel como .xlsx, no como PDF."),
    "SIM-00206": ErrorEntry("SIM-00206", "INVALID_EXCEL_FILE", "Firma de archivo incorrecta", "El archivo no tiene la firma de bytes de un Excel OOXML válido.", "Verifique que el archivo sea un Excel genuino guardado desde Microsoft Excel o compatible."),
    "SIM-00207": ErrorEntry("SIM-00207", "INVALID_EXCEL_FILE", "Path traversal detectado en el ZIP", "El archivo contiene entradas ZIP con rutas que usan '..' o separadores absolutos.", "No suba archivos modificados manualmente. Use solo archivos generados directamente por Excel."),
    "SIM-00208": ErrorEntry("SIM-00208", "INVALID_EXCEL_FILE", "Estructura OOXML incompleta", "Al archivo le faltan entradas obligatorias de la especificación OOXML.", "El archivo puede estar corrupto. Abra y vuelva a guardar desde Excel, o regenere desde la fuente original."),
    "SIM-00209": ErrorEntry("SIM-00209", "ENCRYPTED_EXCEL_FILE", "Workbook protegido con contraseña", "El archivo Excel está protegido con contraseña (EncryptionInfo detectado).", "Quite la protección en Excel: Archivo → Información → Proteger libro → Cifrar con contraseña → borrar contraseña → Guardar."),
    "SIM-00210": ErrorEntry("SIM-00210", "INVALID_EXCEL_FILE", "ZIP corrupto", "El archivo ZIP (XLSX) está corrupto o dañado y no puede abrirse.", "Descargue o regenere el archivo desde la fuente original. Si persiste, contacte al equipo de soporte."),
    # Seguridad de contenido
    "SIM-00300": ErrorEntry("SIM-00300", "UNSAFE_EXCEL_CONTENT", "Macros VBA detectadas", "El archivo contiene un proyecto VBA (xl/vbaProject.bin), lo que indica macros activas.", "Guarde el archivo como .xlsx: Archivo → Guardar como → Libro de Excel (.xlsx). Esto elimina las macros."),
    "SIM-00301": ErrorEntry("SIM-00301", "UNSAFE_EXCEL_CONTENT", "Macros en hojas detectadas", "El archivo contiene hojas de macro (XLM) u otros archivos de macro.", "Guarde el archivo como .xlsx desde Excel para eliminar las macros."),
    "SIM-00302": ErrorEntry("SIM-00302", "UNSAFE_EXCEL_CONTENT", "Conexiones de datos externas", "El archivo contiene conexiones de datos externas (xl/connections.xml).", "Elimine las conexiones: Datos → Consultas y conexiones → clic derecho → Eliminar. Luego guarde."),
    "SIM-00303": ErrorEntry("SIM-00303", "UNSAFE_EXCEL_CONTENT", "Power Query detectado", "El archivo contiene consultas de Power Query (xl/queries/).", "Elimine las consultas de Power Query desde el Editor de Power Query → eliminar todas → Cerrar y cargar."),
    "SIM-00304": ErrorEntry("SIM-00304", "UNSAFE_EXCEL_CONTENT", "Controles ActiveX", "El archivo contiene controles ActiveX (xl/activeX/).", "Elimine todos los controles ActiveX del archivo y guárdelo de nuevo."),
    "SIM-00305": ErrorEntry("SIM-00305", "UNSAFE_EXCEL_CONTENT", "Referencias URL externas en relaciones", "Un archivo .rels contiene un atributo Target que apunta a una URL externa.", "Revise y elimine los hipervínculos o referencias externas del archivo."),
    "SIM-00306": ErrorEntry("SIM-00306", "UNSAFE_EXCEL_CONTENT", "Objetos OLE o ActiveX", "El archivo contiene referencias a objetos OLE embebidos o controles ActiveX.", "Elimine todos los objetos incrustados (OLE) y controles del archivo."),
    "SIM-00307": ErrorEntry("SIM-00307", "UNSAFE_EXCEL_CONTENT", "Tipo de contenido con macros habilitadas", "[Content_Types].xml declara un content type de macro, aunque la extensión sea .xlsx.", "Guarde el archivo correctamente como .xlsx desde Excel. El archivo puede haber sido manipulado."),
    "SIM-00308": ErrorEntry("SIM-00308", "UNSAFE_EXCEL_CONTENT", "Inyección XXE en XML", "Se detectaron declaraciones <!DOCTYPE o <!ENTITY en un archivo XML del paquete OOXML.", "No suba archivos modificados manualmente. Use solo archivos generados directamente por Excel."),
    "SIM-00309": ErrorEntry("SIM-00309", "UNSAFE_EXCEL_CONTENT", "Patrones DDE detectados", "Se detectaron patrones de inyección DDE/DDEAUTO en las cadenas compartidas del archivo.", "Las celdas no deben contener fórmulas con DDE, SYSTEM, EXEC u otros comandos shell."),
    "SIM-00310": ErrorEntry("SIM-00310", "UNSAFE_EXCEL_CONTENT", "Fórmulas en hojas de datos", "Se detectaron elementos <f> (fórmulas) en las hojas. Solo se permiten valores de datos.", "Seleccione todas las celdas con fórmulas, cópielas y péguelas como 'Solo valores' (Pegado especial → Valores). Luego guarde."),
    "SIM-00311": ErrorEntry("SIM-00311", "UNSAFE_EXCEL_CONTENT", "Patrones shell sospechosos", "Se detectaron patrones sospechosos en las hojas (DDEAUTO, =cmd|, msexcel|).", "Revise y limpie el contenido de todas las celdas. Las celdas de datos no deben contener estos patrones."),
    "SIM-00312": ErrorEntry("SIM-00312", "UNSAFE_EXCEL_CONTENT", "Ejecutable embebido (PE/MZ)", "Se detectó una cabecera de ejecutable Windows (PE/MZ) dentro del archivo.", "El archivo puede estar infectado. No lo use y obténgalo de una fuente confiable."),
    "SIM-00313": ErrorEntry("SIM-00313", "VIRUS_DETECTED", "Firma EICAR detectada", "El archivo contiene la firma de prueba de antivirus EICAR.", "No suba archivos de prueba de antivirus. Use un archivo Excel de producción real."),
    "SIM-00314": ErrorEntry("SIM-00314", "VIRUS_DETECTED", "Malware detectado por antivirus", "El motor antivirus (ClamAV) detectó una firma de malware conocida en el archivo.", "El archivo está infectado. Obténgalo de una fuente confiable y escanéelo localmente antes de subir."),
    # Límites ZIP
    "SIM-00400": ErrorEntry("SIM-00400", "EXCEL_LIMIT_EXCEEDED", "Entrada descomprimida excede el límite", "Una entrada dentro del ZIP XLSX supera el tamaño descomprimido máximo permitido.", "Reduzca el contenido del archivo. Si el problema persiste, contacte al administrador."),
    "SIM-00401": ErrorEntry("SIM-00401", "EXCEL_LIMIT_EXCEEDED", "Ratio de compresión excesiva (posible ZIP bomb)", "Una entrada ZIP tiene un ratio de compresión anormalmente alto.", "No suba archivos comprimidos artificialmente. Use el archivo Excel original guardado desde Excel."),
    "SIM-00402": ErrorEntry("SIM-00402", "EXCEL_LIMIT_EXCEEDED", "Tamaño total descomprimido excede el límite", "La suma de todas las entradas descomprimidas supera el límite total permitido.", "Reduzca el contenido del archivo Excel (elimine hojas innecesarias, imágenes, etc.)."),
    # Validación de datos
    "SIM-00500": ErrorEntry("SIM-00500", "VALIDATION_ERROR", "Parámetros de solicitud inválidos", "El cuerpo o los parámetros de la solicitud no cumplen el esquema esperado por la API.", "Revise la documentación del endpoint y corrija los campos indicados en 'details'."),
    "SIM-00501": ErrorEntry("SIM-00501", "VALIDATION_ERROR", "Archivo no cargado", "No se incluyó ningún archivo en la solicitud de carga.", "Asegúrese de adjuntar el archivo Excel en el campo 'file' del formulario multipart/form-data."),
    "SIM-00502": ErrorEntry("SIM-00502", "VALIDATION_ERROR", "UUID inválido (debe ser versión 4)", "El parámetro 'id' no es un UUID versión 4 válido.", "Use el UUID exacto retornado por el endpoint de carga o listado de versiones."),
    "SIM-00503": ErrorEntry("SIM-00503", "VALIDATION_ERROR", "Validación de Excel HR fallida", "El contenido del archivo Excel HR no cumple las reglas de validación del módulo.", "Revise los errores en 'details', corrija las celdas indicadas y vuelva a subir el archivo."),
    "SIM-00504": ErrorEntry("SIM-00504", "VALIDATION_ERROR", "Validación de Excel GN fallida", "El contenido del archivo Excel GN no cumple las reglas de validación del módulo.", "Revise los errores en 'details', corrija las celdas indicadas y vuelva a subir el archivo."),
    "SIM-00505": ErrorEntry("SIM-00505", "VALIDATION_ERROR", "Validación de Excel OP fallida", "El contenido del archivo Excel OP no cumple las reglas de validación del módulo.", "Revise los errores en 'details', corrija las celdas indicadas y vuelva a subir el archivo."),
    "SIM-00506": ErrorEntry("SIM-00506", "VALIDATION_ERROR", "Validación de dominio fallida", "Los datos no cumplen las reglas de negocio del dominio.", "Revise el mensaje de error y los detalles para identificar qué campo o regla falló."),
    # Not Found
    "SIM-00600": ErrorEntry("SIM-00600", "NOT_FOUND", "Recurso no encontrado", "El recurso solicitado no existe en el sistema.", "Verifique el identificador utilizado. Use el listado de versiones para obtener IDs válidos."),
    "SIM-00601": ErrorEntry("SIM-00601", "NOT_FOUND", "No hay parametrización activa", "No existe ninguna versión activa de parametrización (HR, GN u OP).", "Suba y active una versión de parametrización para cada módulo (HR, GN y OP) antes de realizar cálculos."),
    "SIM-00602": ErrorEntry("SIM-00602", "NOT_FOUND", "Versión de parametrización no encontrada", "El ID de versión especificado no corresponde a ningún documento en el sistema.", "Use GET /parametrization/{hr|gn|op}/versions para obtener la lista de versiones disponibles."),
    # Dominio / Negocio
    "SIM-00700": ErrorEntry("SIM-00700", "DOMAIN_ERROR", "Error de dominio", "Se produjo un error en la lógica de negocio del simulador.", "Revise el mensaje de error. Si persiste, contacte al equipo de soporte con el correlation_id."),
    "SIM-00701": ErrorEntry("SIM-00701", "PARAMETRIZATION_ERROR", "Error de parametrización", "La parametrización activa está ausente, incompleta o es incompatible con los datos de entrada.", "Verifique que existan versiones activas de HR, GN y OP. Active una versión válida para cada módulo."),
    # HTTP
    "SIM-00800": ErrorEntry("SIM-00800", "BAD_REQUEST", "Solicitud incorrecta", "La solicitud HTTP tiene formato o parámetros incorrectos.", "Revise la documentación del endpoint y corrija los parámetros de la solicitud."),
    "SIM-00801": ErrorEntry("SIM-00801", "UNAUTHORIZED", "No autorizado", "La solicitud no incluye credenciales válidas de autenticación.", "Incluya las credenciales de autenticación correctas en la cabecera Authorization."),
    "SIM-00802": ErrorEntry("SIM-00802", "FORBIDDEN", "Acceso prohibido", "Las credenciales son válidas pero no tiene permiso para este recurso.", "Contacte al administrador para solicitar acceso al recurso."),
    "SIM-00803": ErrorEntry("SIM-00803", "NOT_FOUND", "Ruta no encontrada", "La URL solicitada no corresponde a ningún endpoint de la API.", "Revise la URL del endpoint. Consulte la documentación en /docs para ver los endpoints disponibles."),
    "SIM-00804": ErrorEntry("SIM-00804", "METHOD_NOT_ALLOWED", "Método HTTP no permitido", "El método HTTP utilizado no está permitido para este endpoint.", "Revise la documentación para confirmar el método correcto del endpoint."),
    "SIM-00805": ErrorEntry("SIM-00805", "UNSUPPORTED_MEDIA_TYPE", "Tipo de contenido no soportado", "El Content-Type de la solicitud no es soportado por este endpoint.", "Use multipart/form-data para cargas de archivos, o application/json para endpoints JSON."),
    "SIM-00806": ErrorEntry("SIM-00806", "HTTP_ERROR", "Error HTTP", "Se produjo un error HTTP no categorizado.", "Revise el código de estado y el mensaje de error para más detalles."),
    # Internos
    "SIM-00900": ErrorEntry("SIM-00900", "INTERNAL_SERVER_ERROR", "Error interno del servidor", "Se produjo un error inesperado en el servidor que no pudo ser manejado.", "Reporte el error al equipo de soporte incluyendo el 'correlation_id' de la respuesta para facilitar el diagnóstico."),
}


def lookup(sim_code: str) -> ErrorEntry | None:
    return CATALOG.get(sim_code)


def make_detail(
    sim_code: str,
    message: str | None = None,
    field: str | None = None,
    details=None,
):
    """Construye un ErrorDetail desde el catálogo.

    - type y message base vienen del catálogo (entry.type, entry.description).
    - message override: si se pasa, reemplaza entry.description (para mensajes dinámicos de excepciones).
    - field y details se pasan directamente.
    """
    entry = CATALOG[sim_code]
    from nexa_engine.modules.shared.responses import ErrorDetail  # lazy import — evita circular
    return ErrorDetail(
        code=sim_code,
        type=entry.type,
        message=message if message is not None else entry.description,
        field=field,
        details=details,
    )
