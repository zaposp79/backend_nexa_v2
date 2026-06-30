"""Módulo parametrizacion — provider de storage y aliases.

Contenido
---------
- provider.py : ParametrizationProvider + get_provider() (fuente única de
  parametrización; lee storage/parametrization/{hr,gn,op}/).

Desviación vs. el plan de refactor (no hay alias.py / storage_loader.py)
------------------------------------------------------------------------
El plan original proponía extraer la constante `_COMPONENTE_ALIAS` a un
`alias.py` y los loaders de storage a un `storage_loader.py`. Al inspeccionar
el código se confirmó que:

  - `_COMPONENTE_ALIAS` NO es una constante de módulo: es un **atributo de
    clase** de `ParametrizationProvider` (accedido vía `self._COMPONENTE_ALIAS`).
  - Los "loaders" son **métodos** de la misma clase, no funciones de módulo.

Extraerlos a archivos separados implicaría cambiar lógica (mover estado de la
clase), lo cual viola la regla "cero cambio de lógica" del refactor. Por eso el
provider se movió como un único archivo cohesivo. Este `__init__` documenta la
decisión para que no se re-intente la división sin una refactorización real.
"""
