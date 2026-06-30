"""
application.lineage.query
=========================

`LineageQuery` — read-only helper that answers human-friendly questions
on top of a `LineageGraph`.

Examples:

    >>> q = LineageQuery(graph)
    >>> q.find_value("vision_tarifas.tarifa[WhatsApp]")
    LineageNode(...)
    >>> q.trace_back("vision_tarifas.tarifa[WhatsApp]")
    [LineageRef(...), LineageRef(...), ...]
    >>> print(q.explain("vision_tarifas.tarifa[WhatsApp]"))
    vision_tarifas.tarifa[WhatsApp] = 8421.33
      ← computed:PricingCalculator.calcular_factor_billing
      ← Panel.margen_a = 0.21 (request)
      ← Excel:Rot Ausent y Rentabilidad!G11
"""

from __future__ import annotations

from typing import Optional

from nexa_engine.modules.lineage.domain.models import (
    LineageGraph,
    LineageNode,
    LineageRef,
    SOURCE_TYPE_COMPUTED,
)


class LineageQuery:
    """Read-only query layer over an immutable `LineageGraph`."""

    def __init__(self, graph: LineageGraph) -> None:
        self._graph = graph
        # build index { value_name → last LineageNode } (last writer wins)
        self._by_value: dict[str, LineageNode] = {}
        for n in graph.nodes:
            self._by_value[n.value_name] = n

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def graph(self) -> LineageGraph:
        return self._graph

    def find_value(self, value_name: str) -> Optional[LineageNode]:
        """Return the node whose `value_name` matches (last writer wins)."""
        return self._by_value.get(value_name)

    def trace_back(self, value_name: str, *, max_depth: int = 16) -> list[LineageRef]:
        """
        Walk parents of `value_name` until non-computed refs are found.

        Returns a flat ordered list of LineageRefs traversed. Avoids cycles
        by tracking visited nodes. Truncates at `max_depth` to keep the
        helper safe on pathological graphs.
        """
        out: list[LineageRef] = []
        node = self.find_value(value_name)
        if node is None:
            return out

        stack: list[tuple[LineageNode, int]] = [(node, 0)]
        seen_traces: set[str] = set()

        while stack:
            current, depth = stack.pop()
            if current.trace_id in seen_traces or depth > max_depth:
                continue
            seen_traces.add(current.trace_id)
            for ref in current.inputs:
                out.append(ref)
                # if the ref points to another computed node we recurse
                if ref.source_type == SOURCE_TYPE_COMPUTED:
                    target_id = ref.source_id.removeprefix("computed:trace:")
                    target = self._graph.by_trace_id(target_id)
                    if target is not None:
                        stack.append((target, depth + 1))
        return out

    def explain(self, value_name: str, *, max_depth: int = 8) -> str:
        """
        Render a human-readable explanation of how `value_name` was built.

        Output uses ASCII back-arrows so it renders in any terminal.
        """
        node = self.find_value(value_name)
        if node is None:
            return f"{value_name} -> <not found in lineage graph>"

        lines: list[str] = [f"{node.value_name} = {_render_value(node.value)}"]
        if node.formula:
            lines.append(f"  formula: {node.formula}")
        lines.append(f"  <- {node.calculator}  [{node.stage}]")
        self._render_refs(node, lines, depth=1, max_depth=max_depth, seen=set())
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _render_refs(
        self,
        node: LineageNode,
        lines: list[str],
        *,
        depth: int,
        max_depth: int,
        seen: set[str],
    ) -> None:
        if depth > max_depth or node.trace_id in seen:
            return
        seen.add(node.trace_id)
        indent = "  " * (depth + 1)
        for ref in node.inputs:
            if ref.source_type == "excel":
                loc = f"Excel:{ref.sheet}!{ref.cell}" if ref.sheet else ref.source_id
                lines.append(
                    f"{indent}<- {ref.source_id} = {_render_value(ref.value)}  ({loc})"
                )
            elif ref.source_type == "computed":
                target_id = ref.source_id.removeprefix("computed:trace:")
                target = self._graph.by_trace_id(target_id)
                if target is not None:
                    lines.append(
                        f"{indent}<- {target.value_name} = {_render_value(target.value)}"
                    )
                    self._render_refs(
                        target, lines, depth=depth + 1, max_depth=max_depth, seen=seen
                    )
                else:
                    lines.append(
                        f"{indent}<- {ref.source_id} = {_render_value(ref.value)}"
                    )
            else:
                lines.append(
                    f"{indent}<- {ref.source_id} = {_render_value(ref.value)}  ({ref.source_type})"
                )


def _render_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return "<none>"
    return str(value)


__all__ = ["LineageQuery"]
