"""Payroll parametrization repository.

Manages payroll parameters from HR parametrization:
- Base salaries by role and type
- Social security contributions
- Benefits (cesantías, primas, vacaciones, interés)

Data sources: HR-Nomina, HR-SegSocial, HR-Prestaciones sheets
"""

from __future__ import annotations

import json
import logging
import unicodedata
from typing import Any, Dict, Optional

from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.shared.exceptions import ParametrizationError, ParametrizationNotFoundError, DomainError

logger = logging.getLogger(__name__)


class RoleNotFoundError(DomainError):
    """Raised when a role is not found in parametrization."""
    pass


class ContributionNotFoundError(DomainError):
    """Raised when a contribution type is not found."""
    pass


class BenefitNotFoundError(DomainError):
    """Raised when a benefit is not found."""
    pass


class PayrollParametrizationRepository:
    """Repository for payroll parameters from HR parametrization.

    Access patterns:
    - get_salary_for_role(rol: str, tipo: str) → float: Salary for role/type
    - get_contributions(ssparafiscales: str) → Dict: SS contribution rates
    - get_benefits(prestaciones: str) → float: Benefit rate
    """

from nexa_engine.modules.parametrizacion.mixins.payroll_salary_mixin import PayrollSalaryMixin
from nexa_engine.modules.parametrizacion.mixins.payroll_rotacion_mixin import PayrollRotacionMixin
from nexa_engine.modules.parametrizacion.mixins.payroll_staffing_mixin import PayrollStaffingMixin


class PayrollParametrizationRepository(
    PayrollSalaryMixin,
    PayrollRotacionMixin,
    PayrollStaffingMixin,
):
    """Repository for payroll parameters from HR parametrization.

    Methods organized in mixins (FASE Z.2):
      PayrollSalaryMixin    — salary, contributions, benefits, costo_operativo
      PayrollRotacionMixin  — rotacion, ausentismo, cache loader
      PayrollStaffingMixin  — staff ratios, reglas, _ensure_hr_loaded
    """

    def __init__(self, resolver: ParametrizationResolver):
        """Initialize with resolver.

        Args:
            resolver: ParametrizationResolver instance.
        """
        self._resolver = resolver
        self._hr_data: Optional[Dict[str, Any]] = None
        # Cache for rotacion_ausentismo — populated on first access
        self._rotacion_ausentismo: Optional[Dict[str, Any]] = None
        self._rotacion_loaded = False

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

