# vln_carla2.adapters.cli.main 功能总览

本文汇总 `python -m vln_carla2.adapters.cli.main` 的全部可用功能，按命令层级组织。

## 1. 命令入口与层级

### 1.1 标准分层入口（推荐）

```bash
python -m vln_carla2.adapters.cli.main <resource> <action> [options]
```

命令树：

```text
main
├─ scene
│  └─ run
├─ vehicle
│  ├─ list
│  └─ spawn
└─ spectator
   └─ follow
```

### 1.2 兼容旧入口（已弃用但仍可用）

不写 `scene run`，直接把 `scene run` 的参数放在根命令后也能运行，会打印一次弃用提示：

```text
[DEPRECATED] legacy root args are still supported. Please migrate to: scene run ...
```

## 2. 全局通用连接参数（各子命令通用）

以下参数由 `scene run`、`vehicle list`、`vehicle spawn`、`spectator follow` 共用：

- `--host`：CARLA 主机，默认 `127.0.0.1`
- `--port`：CARLA RPC 端口，默认 `2000`
- `--timeout-seconds`：客户端超时秒数，默认 `10.0`
- `--map-name`：地图名，默认 `Town10HD_Opt`
- `--mode {sync,async}`：运行模式，默认 `sync`
- `--fixed-delta-seconds`：同步模式固定步长，默认 `0.05`
- `--no-rendering`：关闭世界渲染（布尔开关，默认False，即开启渲染）

## 3. scene run（场景运行）

### 3.1 功能

- 启动/连接 CARLA 后运行操作循环（支持同步/异步模式）
- 可选跟随某辆车（持续跟随）
- 可选自动拉起本地 CARLA 进程

### 3.2 专属参数

- `--tick-sleep-seconds`：同步模式 tick 间 sleep，默认 `0.05`
- `--follow`：跟随引用（`actor:<id>` / `role:<name>` / `first` / 正整数 id）
- `--follow-vehicle-id`：旧版跟随参数（与 `--follow` 互斥）
- `--offscreen`：仅对 `--launch-carla` 启动的服务生效
- `--launch-carla`：本地拉起 CarlaUE4
- `--reuse-existing-carla`：端口已有 CARLA 时复用，不报错退出
- `--carla-exe`：CarlaUE4 可执行文件路径（可由 `CARLA_UE4_EXE` 提供默认值）
- `--carla-startup-timeout-seconds`：启动等待超时，默认 `45.0`
- `--quality-level {Low,Epic} (default: Epic)`：渲染质量
- `--with-sound`：启用声音（默认用 `-nosound`）
- `--keep-carla-server`：命令退出时不关闭由本命令启动的 CARLA

### 3.3 行为说明

- `--launch-carla` 仅支持本机回环地址（如 `127.0.0.1`）
- 指定 `--launch-carla` 且端口已有 CARLA：
  - 未加 `--reuse-existing-carla`：报错并退出
  - 加了 `--reuse-existing-carla`：复用现有服务
- `--offscreen` 但未 `--launch-carla`：打印警告（不会影响现有外部服务）
- `--no-rendering` 但未 `--launch-carla`：打印警告
- `Ctrl+C`：优雅退出，返回成功码

## 4. vehicle list（车辆列表）

### 4.1 功能

- 枚举当前世界内车辆 actor

### 4.2 参数

- 继承“全局通用连接参数”
- `--format {table,json}`：输出格式，默认 `table`

### 4.3 输出

- `table`：列包含 `actor_id/type_id/role_name/x/y/z`
- `json`：返回数组，每项字段同上

## 5. vehicle spawn（生成车辆）

### 5.1 功能

- 按蓝图与位姿生成一辆车，并输出其描述信息

### 5.2 参数

- 继承“全局通用连接参数”
- `--blueprint-filter`：蓝图过滤，默认 `vehicle.tesla.model3`
- `--spawn-x`：默认 `0.038`
- `--spawn-y`：默认 `15.320`
- `--spawn-z`：默认 `0.15`
- `--spawn-yaw`：默认 `180.0`
- `--role-name`：默认 `ego`
- `--output {table,json}`：输出格式，默认 `table`

### 5.3 输出

- 与 `vehicle list` 的单车字段一致：`actor_id/type_id/role_name/x/y/z`

## 6. spectator follow（观察者视角对齐）

### 6.1 功能

- 将 spectator 视角一次性对齐到目标车辆上方俯视（不是持续绑定）

### 6.2 参数

- 继承“全局通用连接参数”
- `--ref`（必填）：目标车辆引用
- `--z`：俯视高度，默认 `20.0`

### 6.3 输出

- 成功时打印：

```text
[INFO] spectator aligned ref=<ref> actor_id=<id> z=<z>
```

## 7. 车辆引用格式（`--follow` / `--ref`）

支持格式：

- `actor:<id>`：按 actor id
- `role:<name>`：按 `role_name`
- `first`：当前车辆列表中最小 actor id
- `<正整数>`：等价于 `actor:<id>`

约束：

- `actor id` 必须是正整数
- `first` 不能带值（例如 `first:1` 非法）
- 非法格式会报 `Invalid vehicle ref ...`

## 8. 退出码约定

- `0`：成功
- `1`：运行期错误（连接/执行失败等）
- `2`：参数或语义错误（argparse 错误、引用格式错误、互斥参数冲突等）

## 9. 环境变量与 .env 读取

- 启动 parser 时会尝试读取当前目录 `.env`
- 支持 `utf-8-sig`（含 BOM）编码
- 已存在的环境变量不会被 `.env` 覆盖
- 成对引号会被去掉（`"..."` 或 `'...'`）
- `CARLA_UE4_EXE` 可作为 `--carla-exe` 默认值来源

## 10. 示例命令

### 10.1 启动场景运行并拉起 CARLA

```bash
python -m vln_carla2.adapters.cli.main scene run --launch-carla --host 127.0.0.1 --port 2000 --mode sync
```

### 10.2 生成 ego 车辆并以 JSON 输出

```bash
python -m vln_carla2.adapters.cli.main vehicle spawn --host 127.0.0.1 --port 2000 --mode sync --blueprint-filter vehicle.tesla.model3 --spawn-x 0.038 --spawn-y 15.320 --spawn-z 0.15 --spawn-yaw 180 --role-name ego --output json
```

### 10.3 运行时持续跟随 ego（scene run 级别）

```bash
python -m vln_carla2.adapters.cli.main scene run --host 127.0.0.1 --port 2000 --mode sync --follow role:ego
```

### 10.4 单次对齐 spectator 到 ego 上方（spectator 级别）

```bash
python -m vln_carla2.adapters.cli.main spectator follow --host 127.0.0.1 --port 2000 --mode sync --ref role:ego --z 20
```

