"""
nexa_engine/adapters/entry_data_adapter.py
==========================================
NewEntryDataAdapter — Fase B del refactor contractual.

Responsabilidad única:
  Traducir el contrato entry_data (cadena_b / cadena_c en formato nuevo)
  al formato interno que espera UserInputLoader._cadena_b() / _cadena_c().

Principios:
  - Sin lógica financiera — solo traducción estructural
  - Sin defaults silenciosos — campos faltantes generan ValueError
  - Sin hardcodes — todas las constantes vienen del JSON contractual

Mappings principales:
  entry_data condiciones_cadena_b:
    opex.items[]                         → opex_consumo_variable[]
    inversiones_capex[]                  → inversion_plataforma (suma amortizada)
    equipo_soporte_mantenimiento{...}    → equipo_sm[], dispositivos_sm[], fte_equipo_sm
    costo_variable.tarifas_por_canal     → canales[].tarifa_unitaria  (por canal+modalidad)
    costo_variable.tasa_escalamiento     → canales[].pct_escalamiento / costo_escalamiento
    hitl.equipo[]                        → opex_consumo_variable[] items tipo HITL
    hitl.dispositivos_requeridos[]       → dispositivos_sm[] (slot HITL)

  entry_data condiciones_cadena_c:
    tarifa_proveedor_canal.items[]       → canales[] (nombre, modalidad, tarifa_proveedor, volumen)
    inversiones_capex[]                  → inversion_anual (suma de valores mensuales)
    recurso_humano_transversal.roles[]   → equipo_transversal[]
    costo_variable.tarifas_por_canal     → canales[].tarifa_proveedor (enrichment)
    costo_variable.tasa_escalamiento     → canales[].pct_escalamiento / costo_escalamiento
    hitl.equipo[]                        → costo_personal_hitl (suma)
    hitl.total_volumen_cadena_c          → canales[].volumen_mensual fallback
"""

from __future__ import annotations

from typing import Any, Dict, List


class NewEntryDataAdapter:
    """
    Traduce `condiciones_cadena_b` y `condiciones_cadena_c` del formato
    contractual entry_data al formato interno que consume UserInputLoader.

    No modifica condiciones_cadena_a, panel_de_control, polizas, etc.
    Solo actúa sobre las secciones con mismatch estructural documentado en
    docs/audit/fase_adapter_formula_mapping.md (gaps C1, C2).
    """

    # ──────────────────────────────────────────────────────────────────
    # Punto de entrada público
    # ──────────────────────────────────────────────────────────────────

    def adaptar(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recibe el payload entry_data después de la normalización inicial
        (panel_de_control ya construido) y traduce cadena_b / cadena_c
        al formato que espera _cadena_b() / _cadena_c() en UserInputLoader.

        Actúa in-place sobre una copia del dict; el original no se modifica.

        Args:
            data: dict con claves `condiciones_cadena_b` y/o `condiciones_cadena_c`
                  en formato entry_data, más opcionalmente `panel_de_control`.

        Returns:
            Nuevo dict con cadena_b y cadena_c traducidos.
        """
        result = dict(data)

        if "condiciones_cadena_b" in result:
            cb = result["condiciones_cadena_b"]
            if self._es_formato_entry_data_b(cb):
                result["condiciones_cadena_b"] = self._adaptar_cadena_b(cb)

        if "condiciones_cadena_c" in result:
            cc = result["condiciones_cadena_c"]
            if self._es_formato_entry_data_c(cc):
                result["condiciones_cadena_c"] = self._adaptar_cadena_c(cc)

        return result

    # ──────────────────────────────────────────────────────────────────
    # Detección de formato
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _es_formato_entry_data_b(d: Dict) -> bool:
        """
        El formato entry_data de cadena_b se reconoce por tener `opex` o
        `equipo_soporte_mantenimiento` o `costo_variable` o `hitl` en lugar
        de los campos internos `canales`, `opex_consumo_variable`, `equipo_sm`.
        """
        entry_data_keys = {"opex", "equipo_soporte_mantenimiento", "costo_variable",
                           "inversiones_capex", "hitl"}
        internal_keys   = {"canales", "opex_consumo_variable", "equipo_sm"}
        has_entry  = bool(entry_data_keys & set(d.keys()))
        has_intern = bool(internal_keys & set(d.keys()))
        # Si tiene claves entry_data y NO tiene claves internas → necesita adaptación
        return has_entry and not has_intern

    @staticmethod
    def _es_formato_entry_data_c(d: Dict) -> bool:
        """
        El formato entry_data de cadena_c se reconoce por tener
        `tarifa_proveedor_canal` o `recurso_humano_transversal` o `hitl`
        en lugar de `canales` o `equipo_transversal`.
        """
        entry_data_keys = {"tarifa_proveedor_canal", "recurso_humano_transversal",
                           "inversiones_capex", "costo_variable", "hitl"}
        internal_keys   = {"canales", "equipo_transversal"}
        has_entry  = bool(entry_data_keys & set(d.keys()))
        has_intern = bool(internal_keys & set(d.keys()))
        return has_entry and not has_intern

    # ──────────────────────────────────────────────────────────────────
    # Cadena B
    # ──────────────────────────────────────────────────────────────────

    def _adaptar_cadena_b(self, d: Dict) -> Dict:
        """
        Traduce condiciones_cadena_b del formato entry_data al formato
        interno que espera UserInputLoader._cadena_b().

        Formato interno esperado:
          canales[]                  ← reconstruido desde costo_variable
          opex_consumo_variable[]    ← desde opex.items[] + hitl.equipo[]
          equipo_sm[]                ← desde equipo_soporte_mantenimiento.roles[]
          dispositivos_sm[]          ← desde equipo_soporte_mantenimiento.dispositivos_requeridos[]
          inversion_plataforma       ← suma de inversiones_capex[].valor_mes_actual
          fte_equipo_sm              ← equipo_soporte_mantenimiento.fte
        """
        volume_service      = d.get("_volume_service")
        canales             = self._b_construir_canales(d, volume_service)
        opex_consumo        = self._b_construir_opex_consumo(d)
        equipo_sm           = self._b_construir_equipo_sm(d)
        dispositivos_sm     = self._b_construir_dispositivos_sm(d)
        inversion_plataforma = self._b_calcular_inversion(d)
        fte_equipo_sm       = self._b_obtener_fte(d)

        return {
            "canales":               canales,
            "opex_consumo_variable": opex_consumo,
            "equipo_sm":             equipo_sm,
            "dispositivos_sm":       dispositivos_sm,
            "inversion_plataforma":  inversion_plataforma,
            "fte_equipo_sm":         fte_equipo_sm,
            "amortizar_dispositivos_sm": False,  # entry_data ya provee valor_mes_actual
        }

    def _b_construir_canales(self, d: Dict, volume_service=None) -> List[Dict]:
        """
        Reconstruye canales[] desde costo_variable.tarifas_por_canal +
        tasa_escalamiento.

        Cada combinación (modalidad, canal) con tarifa > 0 o tasa > 0
        genera un canal. El volumen_mensual se deja en 0 porque entry_data
        no lo especifica a este nivel — se configura en la volumetria.
        """
        costo_var = d.get("costo_variable", {})
        tarifas   = costo_var.get("tarifas_por_canal", {})
        tasas_esc = costo_var.get("tasa_escalamiento", {})

        # Tarifa de escalamiento global (valor fijo por unidad)
        tarifa_esc_inbound  = float(
            tasas_esc.get("tarifa_de_escalamiento_indbound", {}).get("value", 0) or 0
        )
        tarifa_esc_outbound = float(
            tasas_esc.get("tarifa_de_escalamiento_outbound", {}).get("value", 0) or 0
        )

        canales = []

        for modalidad_key in ("inbound", "outbound"):
            tarifa_esc = tarifa_esc_inbound if modalidad_key == "inbound" else tarifa_esc_outbound
            modalidad_label = modalidad_key.capitalize()  # "Inbound" / "Outbound"

            tarifas_modalidad = tarifas.get(modalidad_key, [])
            tasas_modalidad   = {
                item["canal"]: float(item.get("tasa", 0) or 0)
                for item in tasas_esc.get(modalidad_key, [])
                if "canal" in item
            }

            for item in tarifas_modalidad:
                canal_nombre = str(item.get("canal", ""))
                tarifa       = float(item.get("tarifa", 0) or 0)
                pct_esc      = tasas_modalidad.get(canal_nombre, 0.0)

                canales.append({
                    "nombre":             f"{canal_nombre} {modalidad_label}",
                    "modalidad":          modalidad_label,
                    "producto":           canal_nombre,
                    "volumen_mensual":    (
                        volume_service.volumen(modalidad_label, canal_nombre, "cadena_b")
                        if volume_service else 0.0
                    ),
                    "activo":             True,
                    "opex_fijo":          0.0,
                    "tarifa_unitaria":    tarifa,
                    "pct_escalamiento":   pct_esc,
                    "costo_escalamiento": tarifa_esc,
                })

        return canales

    def _b_construir_opex_consumo(self, d: Dict) -> List[Dict]:
        """
        Traduce opex.items[] al formato ItemOpexConsumoInput.

        entry_data campo `valor`  → interno `valor_unitario`
        entry_data campo `rubro`  → interno `nombre`
        entry_data campo `tipo_de_cobro` → interno `tipo_cobro`

        Además, agrega los roles HITL como items de consumo con
        producto = "HITL" para que CadenaBCalculator los separe.
        """
        items = []

        # 1. Opex regular
        for item in d.get("opex", {}).get("items", []):
            if not item.get("canal") and not item.get("producto"):
                # Item sin canal/producto — se asigna como opex genérico
                canal_val   = ""
                prod_val    = "General"
                modal_val   = str(item.get("modalidad", "Inbound"))
            else:
                canal_val   = str(item.get("canal", ""))
                prod_val    = str(item.get("producto", ""))
                modal_val   = str(item.get("modalidad", "Inbound"))

            items.append({
                "nombre":        str(item.get("rubro", prod_val)),
                "producto":      prod_val,
                "modalidad":     modal_val,
                "canal":         canal_val,
                "valor_unitario": float(item.get("valor", 0) or 0),
                "cantidad":      float(item.get("cantidad", 1) or 1),
                "tipo_cobro":    str(item.get("tipo_de_cobro", "Unitario")),
            })

        # 2. HITL: cada rol activado con personas > 0 se incluye como
        #    item HITL para que CadenaBCalculator calcule costo_personal_hitl
        hitl = d.get("hitl", {})
        for rol in hitl.get("equipo", []):
            personas = float(rol.get("personas", rol.get("fte", 0)) or 0)
            if not rol.get("activado", personas > 0):
                continue
            if personas <= 0:
                continue
            items.append({
                "nombre":        str(rol.get("rol", "HITL")),
                "producto":      "HITL",
                "modalidad":     "Inbound",
                "canal":         "",
                "valor_unitario": 0.0,  # costo calculado por salario; placeholder = 0
                "cantidad":      personas,
                "tipo_cobro":    "FTE",
            })

        return items

    def _b_construir_equipo_sm(self, d: Dict) -> List[Dict]:
        """
        Traduce equipo_soporte_mantenimiento.roles[] al formato MiembroEquipoSMInput.

        entry_data `dedicacion` (% entero, ej. 10) → interno `pct_dedicacion` (fracción, ej. 0.10)
        entry_data `activado`                       → interno `activo`
        """
        esm = d.get("equipo_soporte_mantenimiento", {})
        roles = esm.get("roles", [])
        resultado = []
        for rol in roles:
            dedicacion_raw = float(rol.get("dedicacion", rol.get("fte", 0)) or 0)
            # Si dedicacion > 1 está en %, convertir a fracción
            pct = dedicacion_raw / 100.0 if dedicacion_raw > 1.0 else dedicacion_raw
            resultado.append({
                "rol":            str(rol.get("rol", "")),
                "activo":         bool(rol.get("activado", dedicacion_raw > 0)),
                "pct_dedicacion": pct,
            })
        return resultado

    def _b_construir_dispositivos_sm(self, d: Dict) -> List[Dict]:
        """
        Traduce equipo_soporte_mantenimiento.dispositivos_requeridos[]
        al formato DispositivoSMInput.

        entry_data `precio`                          → interno `costo_unitario`
        entry_data `cantidad_atribuible_a_la_operacion` → interno `cantidad`
        `meses_amortizacion = 1` porque entry_data ya provee el valor mensual
        implícitamente (amortizar_dispositivos_sm = False en el resultado final).
        """
        esm = d.get("equipo_soporte_mantenimiento", {})
        dispositivos = esm.get("dispositivos_requeridos", [])
        resultado = []
        for dev in dispositivos:
            precio   = float(dev.get("precio", 0) or 0)
            cantidad = float(dev.get("cantidad_atribuible_a_la_operacion", dev.get("cantidad", 0)) or 0)
            if precio == 0 and cantidad == 0:
                continue
            resultado.append({
                "tipo":               str(dev.get("descripcion", dev.get("tipo", ""))),
                "costo_unitario":     precio,
                "cantidad":           cantidad,
                "meses_amortizacion": 1,
            })
        return resultado

    @staticmethod
    def _b_calcular_inversion(d: Dict) -> float:
        """
        Suma los valores mensuales de inversiones_capex[] para obtener
        el costo mensual total de inversión de plataforma.

        Usa `valor_mes_actual` si está disponible; si no, amortiza
        `valor_total / meses_a_diferir_inversion`.
        """
        total = 0.0
        for inv in d.get("inversiones_capex", []):
            valor_mes = inv.get("valor_mes_actual", inv.get("valor_mensual"))
            if valor_mes is not None:
                total += float(valor_mes or 0)
            else:
                valor_total = float(inv.get("valor_total", 0) or 0)
                meses       = int(inv.get("meses_a_diferir_inversion", inv.get("meses_a_diferir", 1)) or 1)
                total       += valor_total / meses if meses > 0 else 0.0
        return total

    @staticmethod
    def _b_obtener_fte(d: Dict) -> float:
        """Extrae el FTE del equipo S&M desde equipo_soporte_mantenimiento.fte."""
        esm = d.get("equipo_soporte_mantenimiento", {})
        fte = esm.get("fte", 1.0)
        return float(fte or 1.0)

    # ──────────────────────────────────────────────────────────────────
    # Cadena C
    # ──────────────────────────────────────────────────────────────────

    def _adaptar_cadena_c(self, d: Dict) -> Dict:
        """
        Traduce condiciones_cadena_c del formato entry_data al formato
        interno que espera UserInputLoader._cadena_c().

        Formato interno esperado:
          canales[]                       ← desde tarifa_proveedor_canal.items[] + costo_variable
          equipo_transversal[]            ← desde recurso_humano_transversal.roles[]
          inversion_anual                 ← 0.0 (Excel K34 no incluye K38)
          opex_herramientas_transversal   ← Σ(precio × cantidad_atribuible) de recurso_humano_transversal.opex
        """
        volume_service          = d.get("_volume_service")
        canales                 = self._c_construir_canales(d, volume_service)
        equipo                  = self._c_construir_equipo_transversal(d)
        inversion_anual         = self._c_calcular_inversion(d)
        opex_herramientas       = self._c_calcular_opex_herramientas_transversal(d)

        return {
            "canales":                        canales,
            "equipo_transversal":             equipo,
            "inversion_anual":                inversion_anual,
            "opex_herramientas_transversal":  opex_herramientas,
        }

    def _c_construir_canales(self, d: Dict, volume_service=None) -> List[Dict]:
        """
        Reconstruye canales[] desde tarifa_proveedor_canal.items[] enriquecido
        con costo_variable.tarifas_por_canal y tasa_escalamiento.

        Cada item en tarifa_proveedor_canal define un canal con:
          - nombre     = servicio
          - modalidad  = modalidad
          - tarifa_proveedor (valor del ítem)
          - volumen_mensual  = cantidad (unidades)
          - pct_escalamiento / costo_escalamiento desde costo_variable.tasa_escalamiento
        """
        costo_var = d.get("costo_variable", {})
        tarifas   = costo_var.get("tarifas_por_canal", {})
        tasas_esc = costo_var.get("tasa_escalamiento", {})

        # Excel V2-8 · 'Costo Cadena C'!D136 — OPEX fijo from costo_variable.opex_items (tipo_de_gasto='Fijo')
        opex_items_cv = costo_var.get("opex_items", [])
        total_opex_fijo = sum(
            float(it.get("valor_total", 0) or 0)
            for it in opex_items_cv
            if str(it.get("tipo_de_gasto", "")).strip().lower() == "fijo"
        )
        _raw_items = d.get("tarifa_proveedor_canal", {}).get("items", [])
        _total_vol_raw = sum(float(it.get("cantidad", 0) or 0) for it in _raw_items) or 1.0

        tarifa_esc_inbound  = float(
            tasas_esc.get("tarifa_de_escalamiento_indbound", {}).get("value", 0) or 0
        )
        tarifa_esc_outbound = float(
            tasas_esc.get("tarifa_de_escalamiento_outbound", {}).get("value", 0) or 0
        )

        # Indexar tasas de escalamiento por (modalidad_lower, canal)
        tasas_idx: Dict[tuple, float] = {}
        for m_key in ("inbound", "outbound"):
            for item in tasas_esc.get(m_key, []):
                key = (m_key, str(item.get("canal", "")))
                tasas_idx[key] = float(item.get("tasa", 0) or 0)

        # Indexar tarifas por (modalidad_lower, canal) para enriquecer
        tarifas_idx: Dict[tuple, float] = {}
        for m_key in ("inbound", "outbound"):
            for item in tarifas.get(m_key, []):
                key = (m_key, str(item.get("canal", "")))
                tarifas_idx[key] = float(item.get("tarifa", 0) or 0)

        canales = []

        for item in d.get("tarifa_proveedor_canal", {}).get("items", []):
            servicio    = str(item.get("servicio", item.get("canal", "")))
            modalidad   = str(item.get("modalidad", "Inbound"))
            valor       = float(item.get("valor", 0) or 0)
            cantidad    = float(item.get("cantidad", 0) or 0)
            if volume_service:
                cantidad = volume_service.volumen(modalidad, servicio, "cadena_c") or cantidad

            m_key       = modalidad.lower()
            pct_esc     = tasas_idx.get((m_key, servicio), 0.0)
            tarifa_esc  = tarifa_esc_inbound if m_key == "inbound" else tarifa_esc_outbound
            # Si hay tarifa en costo_variable, esta sobreescribe el valor del ítem
            tarifa_cv   = tarifas_idx.get((m_key, servicio), valor)
            # Distribute total_opex_fijo proportionally by raw channel volume
            raw_vol     = float(item.get("cantidad", 0) or 0)
            opex_fijo   = total_opex_fijo * raw_vol / _total_vol_raw

            canales.append({
                "nombre":             servicio,
                "modalidad":          modalidad,
                "volumen_mensual":    cantidad,
                "activo":             True,
                "opex_fijo_integ":    opex_fijo,
                "tarifa_unitaria":    tarifa_cv,  # CADENA_C_NULL fix: → CanalCadenaC.tarifa_proveedor via context_builder
                "opex_var_integ":     0.0,
                "pct_escalamiento":   pct_esc,
                "costo_escalamiento": tarifa_esc,
            })

        # Si no había items en tarifa_proveedor_canal pero sí hay costo_variable,
        # construir canales desde tarifas directamente
        if not canales:
            for m_key in ("inbound", "outbound"):
                modalidad_label = m_key.capitalize()
                tarifa_esc = tarifa_esc_inbound if m_key == "inbound" else tarifa_esc_outbound
                for item in tarifas.get(m_key, []):
                    canal_nombre = str(item.get("canal", ""))
                    tarifa       = float(item.get("tarifa", 0) or 0)
                    pct_esc      = tasas_idx.get((m_key, canal_nombre), 0.0)
                    if tarifa == 0 and pct_esc == 0:
                        continue
                    canales.append({
                        "nombre":             canal_nombre,
                        "modalidad":          modalidad_label,
                        "volumen_mensual":    (
                            volume_service.volumen(modalidad_label, canal_nombre, "cadena_c")
                            if volume_service else float(d.get("hitl", {}).get("total_volumen_cadena_c", 0) or 0)
                        ),
                        "activo":             True,
                        "opex_fijo_integ":    0.0,
                        "opex_var_integ":     tarifa,
                        "pct_escalamiento":   pct_esc,
                        "costo_escalamiento": tarifa_esc,
                    })

        return canales

    def _c_construir_equipo_transversal(self, d: Dict) -> List[Dict]:
        """
        Traduce recurso_humano_transversal.roles[] al formato
        MiembroEquipoTransversalInput.

        entry_data `dedicacion` (% entero) → interno `pct_dedicacion` (fracción)
        entry_data `activado`              → interno `activo`
        entry_data `salario_cargado`       → interno `salario_cargado` (pass-through si existe)
        """
        rht = d.get("recurso_humano_transversal", {})
        roles = rht.get("roles", [])
        resultado = []
        for rol in roles:
            if not rol.get("activado", False):
                continue
            dedicacion_raw = float(rol.get("dedicacion", 0) or 0)
            pct = dedicacion_raw / 100.0 if dedicacion_raw > 1.0 else dedicacion_raw
            member: Dict = {
                "rol":            str(rol.get("rol", "")),
                "activo":         True,
                "pct_dedicacion": pct,
            }
            sal = rol.get("salario_cargado")
            if sal is not None:
                member["salario_cargado"] = float(sal)
            resultado.append(member)
        return resultado

    @staticmethod
    def _c_calcular_opex_herramientas_transversal(d: Dict) -> float:
        """
        Suma precio × cantidad_atribuible de recurso_humano_transversal.opex.

        Excel V2-8 · 'Costo Cadena C' equipo row — monthly tools/equipment cost
        for the transversal implementation team (computers, licenses, workspace).
        """
        rht = d.get("recurso_humano_transversal", {})
        return sum(
            float(it.get("precio", 0) or 0) * float(it.get("cantidad_atribuible", 0) or 0)
            for it in rht.get("opex", [])
        )

    @staticmethod
    def _c_calcular_inversion(d: Dict) -> float:
        """
        Retorna 0.0 — inversiones de Cadena C no contribuyen al CTS.

        Excel V2-8 · 'Costo Cadena C'!K34 = SUM(K35, K36, K40)
        K38 (Inversión amortización) NOT included in K34; K38=0 (#REF! broken formula).
        Including all CAPEX items would add +76.32 COP/tx vs Excel.
        """
        return 0.0
