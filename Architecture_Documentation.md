## 同心圆模型

[[domain]] 核心业务模型：实体、值对象、聚合、领域服务。  
`domain` 只依赖 `domain`，通过 `domain/ports/` 声明外部能力接口，禁止 import 外层。

[[usecases]] 应用层：用例（应用服务）、编排、应用级端口。  
`usecases` 仅允许依赖 `domain` 与 `usecases`。本仓库当前切片如下：

- `control`
- `runtime`（operator + spectator）
- `scene`（scene_editor + safety）
- `exp`
- `cli`
- `shared`（跨切片 DTO / 轻协议）

[[adapters]] 主适配器（驱动侧）：HTTP、GraphQL、CLI、MQ 消费者、表现层。  
`adapters` 允许依赖 `usecases`，负责外部格式与 usecase DTO 的转换。

[[infrastructure]] 次适配器（被驱动侧）：数据库、缓存、MQ 生产者、外部客户端。  
`infrastructure` 允许依赖 `domain` 与 `usecases/**/ports`。

[[app]] 仅组合根：依赖注入、配置、启动。  
`app` 允许 import 所有层，但不承载业务逻辑。

## Usecases 跨切片规则

- 默认禁止直接 import 其他切片内部模块。
- 允许复用方式仅有两种：
  - `usecases.shared.*`
  - `usecases.<slice>.api`
- `shared` 只允许依赖 `domain` 与 `shared` 自身，不允许依赖其他 usecase 切片。

## 测试结构
`tests\` 下的路径与文件
[[unit]]
[[integration]]
[[fixtures]]
[[conftest.py]]

## 架构门禁

- 分层门禁：`tests/unit/architecture/test_layer_dependencies.py`
  - `domain -> domain`
  - `usecases -> domain/usecases`
  - `adapters -> adapters/usecases`
  - `infrastructure -> infrastructure/domain/usecases/**/ports`
  - `app -> unrestricted`
- usecases 切片门禁：`tests/unit/architecture/test_usecase_slice_dependencies.py`
  - `source_slice -> same_slice | shared | other_slice.api`
  - `shared -> shared`（且可依赖 `domain`）

