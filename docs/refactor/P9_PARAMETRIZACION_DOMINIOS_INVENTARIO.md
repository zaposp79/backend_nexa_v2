# P.9 Inventario de Parametrizacion por Dominio

| Archivo actual | Tipo | Dominio real | Ubicacion actual | Ubicacion objetivo | Accion |
| -------------- | ---- | ------------ | ---------------- | ------------------ | ------ |
| `modules/parametrizacion/upload/gn/dto/dto.py` | DTO | GN | `upload/gn/dto/dto.py` | `gn/dto/dto.py` | MOVE |
| `modules/parametrizacion/upload/gn/models/models.py` | Model | GN | `upload/gn/models/models.py` | `gn/models/models.py` | MOVE |
| `modules/parametrizacion/upload/gn/repositories/repository.py` | Repository | GN | `upload/gn/repositories/repository.py` | `gn/repositories/repository.py` | MOVE |
| `modules/parametrizacion/upload/gn/services/service.py` | Service | GN | `upload/gn/services/service.py` | `gn/services/service.py` | MOVE |
| `modules/parametrizacion/upload/gn/validators/validator.py` | Validator | GN | `upload/gn/validators/validator.py` | `gn/validators/validator.py` | MOVE |
| `modules/parametrizacion/upload/gn/mappers/mapper.py` | Mapper | GN | `upload/gn/mappers/mapper.py` | `gn/mappers/mapper.py` | MOVE |
| `modules/parametrizacion/upload/gn/helpers/__init__.py` | Helper | GN | `upload/gn/helpers/__init__.py` | `gn/helpers/__init__.py` | MOVE |
| `modules/parametrizacion/api/gn_router.py` | API | GN | `api/gn_router.py` | `gn/api/router.py` | MOVE |
| `modules/parametrizacion/api/gn_router.py` | API | GN | `api/gn_router.py` | `api/gn_router.py` | RE-EXPORT |
| `modules/parametrizacion/upload/hr/dto/dto.py` | DTO | HR | `upload/hr/dto/dto.py` | `hr/dto/dto.py` | MOVE |
| `modules/parametrizacion/upload/hr/models/models.py` | Model | HR | `upload/hr/models/models.py` | `hr/models/models.py` | MOVE |
| `modules/parametrizacion/upload/hr/repositories/repository.py` | Repository | HR | `upload/hr/repositories/repository.py` | `hr/repositories/repository.py` | MOVE |
| `modules/parametrizacion/upload/hr/services/service.py` | Service | HR | `upload/hr/services/service.py` | `hr/services/service.py` | MOVE |
| `modules/parametrizacion/upload/hr/validators/validator.py` | Validator | HR | `upload/hr/validators/validator.py` | `hr/validators/validator.py` | MOVE |
| `modules/parametrizacion/upload/hr/mappers/mapper.py` | Mapper | HR | `upload/hr/mappers/mapper.py` | `hr/mappers/mapper.py` | MOVE |
| `modules/parametrizacion/upload/hr/helpers/__init__.py` | Helper | HR | `upload/hr/helpers/__init__.py` | `hr/helpers/__init__.py` | MOVE |
| `modules/parametrizacion/api/hr_router.py` | API | HR | `api/hr_router.py` | `hr/api/router.py` | MOVE |
| `modules/parametrizacion/api/hr_router.py` | API | HR | `api/hr_router.py` | `api/hr_router.py` | RE-EXPORT |
| `modules/parametrizacion/upload/op/dto/dto.py` | DTO | OP | `upload/op/dto/dto.py` | `op/dto/dto.py` | MOVE |
| `modules/parametrizacion/upload/op/models/models.py` | Model | OP | `upload/op/models/models.py` | `op/models/models.py` | MOVE |
| `modules/parametrizacion/upload/op/repositories/repository.py` | Repository | OP | `upload/op/repositories/repository.py` | `op/repositories/repository.py` | MOVE |
| `modules/parametrizacion/upload/op/services/service.py` | Service | OP | `upload/op/services/service.py` | `op/services/service.py` | MOVE |
| `modules/parametrizacion/upload/op/validators/validator.py` | Validator | OP | `upload/op/validators/validator.py` | `op/validators/validator.py` | MOVE |
| `modules/parametrizacion/upload/op/mappers/mapper.py` | Mapper | OP | `upload/op/mappers/mapper.py` | `op/mappers/mapper.py` | MOVE |
| `modules/parametrizacion/upload/op/helpers/__init__.py` | Helper | OP | `upload/op/helpers/__init__.py` | `op/helpers/__init__.py` | MOVE |
| `modules/parametrizacion/api/op_router.py` | API | OP | `api/op_router.py` | `op/api/router.py` | MOVE |
| `modules/parametrizacion/api/op_router.py` | API | OP | `api/op_router.py` | `api/op_router.py` | RE-EXPORT |
| `modules/parametrizacion/upload/excel_reader.py` | Helper | Shared infrastructure | `upload/excel_reader.py` | `shared/helpers/excel_reader.py` | MOVE |
| `modules/parametrizacion/upload/__init__.py` | Orphan | Orphan | `upload/__init__.py` | N/A | DELETE_ONLY_IF_ORPHAN |
| `modules/parametrizacion/api/router.py` | API | Shared infrastructure | `api/router.py` | `api/router.py` | KEEP |
| `modules/parametrizacion/shared/ports/parametrization_repository.py` | Port | Shared infrastructure | `shared/ports/parametrization_repository.py` | `shared/ports/parametrization_repository.py` | KEEP |
| `modules/parametrizacion/shared/repositories/json_parametrization_repository.py` | Shared infrastructure | Shared infrastructure | `shared/repositories/json_parametrization_repository.py` | `shared/repositories/json_parametrization_repository.py` | KEEP |
| `modules/parametrizacion/shared/repositories/cosmos_parametrization_repository.py` | Shared infrastructure | Shared infrastructure | `shared/repositories/cosmos_parametrization_repository.py` | `shared/repositories/cosmos_parametrization_repository.py` | KEEP |
| `modules/parametrizacion/shared/services/repository_factory.py` | Shared infrastructure | Shared infrastructure | `shared/services/repository_factory.py` | `shared/services/repository_factory.py` | KEEP |
| `modules/parametrizacion/shared/models/parametrization_version.py` | Model | Shared infrastructure | `shared/models/parametrization_version.py` | `shared/models/parametrization_version.py` | KEEP |
| `modules/parametrizacion/shared/constants/storage_constants.py` | Constant | Shared infrastructure | `shared/constants/storage_constants.py` | `shared/constants/storage_constants.py` | KEEP |
| `modules/parametrizacion/shared/enums/storage_backend.py` | Enum | Shared infrastructure | `shared/enums/storage_backend.py` | `shared/enums/storage_backend.py` | KEEP |
| `modules/parametrizacion/services/provider.py` | Provider | Shared infrastructure | `services/provider.py` | `services/provider.py` | POSTPONE_WITH_REASON: moverlo puede alterar hashes, cache y contratos de snapshot; se conserva y se valida import/resolver. |
| `modules/parametrizacion/services/resolver.py` | Resolver | Shared infrastructure | `services/resolver.py` | `services/resolver.py` | KEEP |
| `modules/parametrizacion/repositories/*.py` | Repository | Shared infrastructure | `repositories/*.py` | `repositories/*.py` | POSTPONE_WITH_REASON: repositorios historicos usados por provider/calculo; moverlos requiere auditoria de parity fuera del alcance estructural. |
| `modules/parametrizacion/mixins/*.py` | Helper | Shared infrastructure | `mixins/*.py` | `mixins/*.py` | POSTPONE_WITH_REASON: mixins acoplados al provider; moverlos puede cambiar rutas internas y trazabilidad. |
| `modules/parametrizacion/canonicalization.py` | Helper | Shared infrastructure | `canonicalization.py` | `canonicalization.py` | KEEP |
| `modules/parametrizacion/value_normalizer.py` | Helper | Shared infrastructure | `value_normalizer.py` | `value_normalizer.py` | KEEP |
| `modules/parametrizacion/validator_utils.py` | Helper | Shared infrastructure | `validator_utils.py` | `validator_utils.py` | KEEP |
| `modules/parametrizacion/frozen_parametrization.py` | Model | Shared infrastructure | `frozen_parametrization.py` | `frozen_parametrization.py` | KEEP |
| `modules/parametrizacion/frozen_parametrization_adapter.py` | Shared infrastructure | Shared infrastructure | `frozen_parametrization_adapter.py` | `frozen_parametrization_adapter.py` | KEEP |
| `modules/parametrizacion/loader.py` | Helper | Shared infrastructure | `loader.py` | `loader.py` | KEEP |

