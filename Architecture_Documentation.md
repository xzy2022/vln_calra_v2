## 同心圆模型

[[domain]]  核心业务模型：实体、值对象、聚合、领域服务。
	`domain` 需要外部的帮助，`domain/ports/` 以待实现的接口范式规范了 `domain` 可以调用外部的内容。
[[usecases]]  应用层：用例（应用服务）、编排、应用级端口。
	`usecases` 也需要外层的帮助，`usecases/<slice>/ports/` 也以待实现的接口范式规范了 `usecases` 可以调用外部的内容。
[[adapters]]  主适配器（驱动侧）：HTTP、GraphQL、CLI、MQ 消费者、表现层
[[infrastructure]]  次适配器（被驱动侧）：数据库、缓存、MQ 生产者、外部客户端
[[app]]  仅组合根：依赖注入、配置、启动仅组合根：依赖注入、配置、启动

## 测试结构
`tests\` 下的路径与文件
[[unit]]
[[integration]]
[[fixtures]]
[[conftest.py]]

## 架构门禁（本轮新增）

- 架构依赖由 `tests/unit/architecture/test_layer_dependencies.py` 做 AST 静态检查并作为测试门禁。
- 规则如下：
  - `domain -> domain`
  - `usecases -> domain/usecases`
  - `adapters -> adapters/usecases`
  - `infrastructure -> infrastructure/domain/usecases/**/ports`
  - `app -> unrestricted`
- 说明：本轮**明确忽略** `usecases` 内部相互调用限制，不把它作为违规项。
