"""modules.lineage — lineage bounded context.

Layers:
  domain/         — immutable data classes (LineageRef, LineageNode, LineageGraph, LineageQuery)
  infrastructure/ — emitters, snapshot repository
  application/    — builder (seeds emitter from PricingRequest / PricingResult)

Consumers must import from explicit layer paths:
  from nexa_engine.modules.lineage.domain.models import LineageRef
  from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository
  from nexa_engine.modules.lineage.application.builder import seed_lineage_from_request
"""
