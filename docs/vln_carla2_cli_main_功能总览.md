# vln_carla2.app.cli_main 功能总览

本文汇总 `python -m vln_carla2.app.cli_main` 的可用功能，按命令层级组织。

## 1. 命令入口与层级

### 1.1 标准入口

```bash
python -m vln_carla2.app.cli_main <resource> <action> [options]
```

命令树：

```text
main
├─ scene
│  └─ run
├─ operator
│  └─ run
├─ vehicle
│  ├─ list
│  └─ spawn
└─ spectator
   └─ follow
```

### 1.2 兼容入口说明

- 已移除 legacy 根命令兼容。
- 必须显式使用 `scene run` / `operator run` / `vehicle list` / `vehicle spawn` / `spectator follow`。

## 2. 通用连接参数

以下参数由 `scene run`、`operator run`、`vehicle list`、`vehicle spawn`、`spectator follow` 共用：

- `--host`：CARLA 主机，默认 `127.0.0.1`
- `--port`：CARLA RPC 端口，默认 `2000`
- `--timeout-seconds`：客户端超时秒数，默认 `10.0`
- `--map-name`：地图名，默认 `Town10HD_Opt`
- `--mode {sync,async}`：运行模式，默认 `sync`
- `--fixed-delta-seconds`：同步模式固定步长，默认 `0.05`
- `--no-rendering`：关闭世界渲染（布尔开关，默认False，即开启渲染）

## 3. scene run（场景运行）

### 3.1 功能

- 启动/连接 CARLA 后运行 scene editor 循环（同步/异步模式）。
- 可选自动拉起本地 CARLA 进程。
- 默认以 `Free` 模式运行。
- scene run 里，follow 目标目前被固定为 None。因此 / 切换到 Follow 时会检查 follow_vehicle_id，必然告警。因为这个功能似乎不是必须的，先不深究。

### 3.2 专属参数

- `--tick-sleep-seconds`：同步模式 tick 间 sleep，默认 `0.05`
- `--offscreen`：仅对 `--launch-carla` 启动的服务生效
- `--launch-carla`：本地拉起 CarlaUE4
- `--reuse-existing-carla`：端口已有 CARLA 时复用
- `--carla-exe`：CarlaUE4 可执行文件路径（可由 `CARLA_UE4_EXE` 提供默认值）
- `--carla-startup-timeout-seconds`：启动等待超时，默认 `45.0`
- `--quality-level {Low,Epic}`：渲染质量，默认 `Epic`
- `--with-sound`：启用声音（默认 `-nosound`）
- `--keep-carla-server`：命令退出时不关闭由本命令启动的 CARLA
- `--scene-import`：启动后、进入 loop 前导入场景 JSON
- `--scene-export-path`：`Ctrl+S` 导出场景时使用的目标文件路径（可选）

### 3.3 运行时交互（键盘）

- `↑/↓`：调整 spectator X 方向（按住持续生效）
- `←/→`：调整 spectator Y 方向（按住持续生效）
- `+/-`：
  - `Free` 模式：直接调整 spectator Z
  - `Follow` 模式：调整 `follow_z`（跟随高度）
- `/`：`Free` 与 `Follow` 之间切换（边沿触发，按住不重复切换）
- `1`：按下时读取 spectator 当前 `X/Y`，将其投影到道路 waypoint，按 `spawn_z = ground_z + vehicle_offset(默认 0.05)` 生成车辆（边沿触发，按住不重复）
- `2`：按下时读取 spectator 当前 `X/Y`，将其投影到道路 waypoint，按 `spawn_z = ground_z + vehicle_offset(默认 0.02)` 生成油桶（边沿触发，按住不重复）
- `Ctrl+S`：导出当前会话内按 `1/2` 成功生成的对象为场景 JSON（边沿触发，按住不重复）

### 3.4 说明

- `scene run` 不再支持 `--follow` 与 `--follow-vehicle-id`。
- `scene run` 默认未绑定跟随目标；若按 `/` 尝试进入 Follow，会告警并保持 `Free` 模式。
- `scene run` 中按 `1` 失败时会输出 `[ERROR] spawn vehicle failed: ...`，按 `2` 失败时会输出 `[ERROR] spawn barrel failed: ...`，两者都不会自动重试。
- 若按 `1` 或 `2` 时找不到可投影的道路 waypoint，会明确报错并终止本次生成。
- `Ctrl+S` 导出成功时输出 `[INFO] scene exported: <path>`；失败时输出 `[ERROR] scene export failed: ...`。
- 若未显式传 `--scene-export-path`，默认写入当前目录：`scene_export_<YYYYMMDD_HHMMSS>.json`。
- 通过 `--scene-import <path>` 导入时，若文件 `map_name` 与当前 `--map-name` 不一致会直接报错并退出。

## 4. operator run（大闭环编排）

### 4.1 功能

- 单命令执行完整链路：启动环境 -> 创建/发现车辆 -> 解析引用 -> 跟随观察 -> 控制运行。
- 在一个会话中组合 operator/control 两轨，支持串行或交错并行策略。

### 4.2 参数

- 继承 `scene run` 的全部运行参数：
  - `--tick-sleep-seconds`
  - `--offscreen`
  - `--launch-carla`
  - `--reuse-existing-carla`
  - `--carla-exe`
  - `--carla-startup-timeout-seconds`
  - `--quality-level`
  - `--with-sound`
  - `--keep-carla-server`
- 工作流参数：
  - `--follow`：目标车辆引用，默认 `role:ego`
  - `--z`：俯视高度，默认 `20.0`
  - `--blueprint-filter`：默认 `vehicle.tesla.model3`
  - `--spawn-x`：默认 `0.038`
  - `--spawn-y`：默认 `15.320`
  - `--spawn-z`：默认 `0.15`
  - `--spawn-yaw`：默认 `180.0`
  - `--role-name`：默认 `ego`
  - `--spawn-if-missing`：解析不到 `follow` 时按 spawn 参数创建（默认开启）
  - `--no-spawn-if-missing`：解析不到时直接失败
  - `--strategy {serial,parallel}`：默认 `parallel`
  - `--steps`：控制步数，默认 `80`
  - `--target-speed-mps`：目标速度，默认 `5.0`
  - `--operator-warmup-ticks`：仅 `serial` 策略生效，默认 `1`

### 4.3 执行策略

- `serial`：先运行 `operator` 预热（`operator_warmup_ticks`），再运行 `control`。
- `parallel`：单线程交错并行，每个控制步前先执行一次 operator 逻辑，再执行控制步。

## 5. vehicle list（车辆列表）

### 5.1 功能

- 枚举当前世界内车辆 actor。

### 5.2 参数

- 继承通用连接参数
- `--format {table,json}`：输出格式，默认 `table`

### 5.3 输出

- `table`：列包含 `actor_id/type_id/role_name/x/y/z`
- `json`：返回数组，每项字段同上

## 6. vehicle spawn（生成车辆）

### 6.1 功能

- 按蓝图与位姿生成一辆车，并输出其描述信息

### 6.2 参数

- 继承“全局通用连接参数”
- `--blueprint-filter`：蓝图过滤，默认 `vehicle.tesla.model3`
- `--spawn-x`：默认 `0.038`
- `--spawn-y`：默认 `15.320`
- `--spawn-z`：默认 `0.15`
- `--spawn-yaw`：默认 `180.0`
- `--role-name`：默认 `ego`
- `--output {table,json}`：输出格式，默认 `table`

### 6.3 输出

- 与 `vehicle list` 的单车字段一致：`actor_id/type_id/role_name/x/y/z`

## 7. spectator follow（观察者持续跟随）

### 7.1 功能

- 启动持续跟随循环，将 spectator 视角持续绑定到目标车辆上方俯视。
- 运行直到 `Ctrl+C`。
- 内部使用 scene editor 编排层并锁定为 `Follow` 模式（不允许 `/` 切回 `Free`）。
- 运行中可用 `+/-` 动态调整跟随高度（`follow_z`）。

### 7.2 参数

- 继承通用连接参数
- `--follow`（必填）：目标车辆引用
- `--z`：俯视高度，默认 `20.0`

- offscreen 由 CARLA 运行会话读取
- 当 `scene run --launch-carla ... --offscreen` 启动 CARLA 时，会按 `host:port` 记录会话 offscreen 状态。
- `spectator follow --host ... --port ...` 会读取该记录；若为 offscreen，则告警并跳过执行。

告警输出：

```text
[WARN] spectator follow skipped in offscreen mode.
```

## 8. 车辆引用格式（`--follow` / `--vehicle-ref`）

支持格式：

- `actor:<id>`：按 actor id
- `role:<name>`：按 `role_name`
- `first`：当前车辆列表中最小 actor id
- `<正整数>`：等价于 `actor:<id>`

约束：

- `actor id` 必须是正整数
- `first` 不能带值（例如 `first:1` 非法）
- 非法格式会报 `Invalid vehicle ref ...`

## 9. 退出码

- `0`：成功
- `1`：运行期错误（连接/执行失败等）
- `2`：参数或语义错误（argparse 错误、引用格式错误、互斥参数冲突等）

## 10. 环境变量与 .env 读取

- 启动 parser 时会尝试读取当前目录 `.env`
- 支持 `utf-8-sig`（含 BOM）编码
- 已存在的环境变量不会被 `.env` 覆盖
- 成对引号会被去掉（`"..."` 或 `'...'`）
- `CARLA_UE4_EXE` 可作为 `--carla-exe` 默认值来源

## 11. 示例命令

### 11.1 激活环境

```bash
conda activate vln_carla_py312
```

### 11.2 启动 scene run（可交互移动）

```bash
python -m vln_carla2.app.cli_main scene run --launch-carla --host 127.0.0.1 --port 2000 --mode sync
```

运行后可直接使用按键：

- `↑/↓/←/→` 平移 spectator
- `+/-` 调整高度
- `/` 尝试切换 Follow（若未配置跟随目标会告警并保持 Free）
- `1` 按当前 spectator `X/Y` 生成一辆车（道路 ground z + vehicle_z_offset=0.05 偏移）
- `2` 按当前 spectator `X/Y` 生成一个油桶（道路 ground z + vehicle_z_offset=0.02 偏移）
- `Ctrl+S` 导出当前会话场景到 JSON

导入：
```bash
python -m vln_carla2.app.cli_main scene run --host 127.0.0.1 --port 2000 --mode sync --scene-import artifacts/scene_in.json  --launch-carla 
```
导出：
```bash
python -m vln_carla2.app.cli_main scene run --host 127.0.0.1 --port 2000 --mode sync --scene-export-path artifacts/scene_out.json --launch-carla 
```

### 11.3 单命令执行大闭环（按 role 发现或按需创建）

```bash
python -m vln_carla2.app.cli_main operator run --launch-carla --host 127.0.0.1 --port 2000 --mode sync --follow role:ego --strategy parallel --steps 80 --target-speed-mps 5.0 --z 20
```

### 11.4 生成 ego 车辆并以 JSON 输出

```bash
python -m vln_carla2.app.cli_main vehicle spawn --host 127.0.0.1 --port 2000 --mode sync --blueprint-filter vehicle.tesla.model3 --spawn-x 0.038 --spawn-y 15.320 --spawn-z 0.15 --spawn-yaw 180 --role-name ego --output json
```

### 11.5 持续跟随 ego（spectator 级别）

```bash
python -m vln_carla2.app.cli_main spectator follow --host 127.0.0.1 --port 2000 --mode sync --follow role:ego --z 20
```

### 11.6 禁区是否进入实验

```bash
python -m vln_carla2.app.cli_main exp run --host 127.0.0.1 --port 2000 --mode sync --scene-json artifacts/scene_out.json --launch-carla --keep-carla-server
```

运行后可使用 `+/-` 调整跟随高度；`/` 不会切换模式（锁定 Follow）。

## 12. Python 调用示例（非 CLI）

### 12.1 scene editor（Free 模式）

```python
from vln_carla2.app.wiring.scene import SceneEditorSettings, run_scene_editor

settings = SceneEditorSettings(
    host="127.0.0.1",
    port=2000,
    synchronous_mode=True,
    tick_sleep_seconds=0.05,
    start_in_follow_mode=False,
    allow_mode_toggle=True,
)
run_scene_editor(settings)
```

### 12.2 scene editor（锁定 Follow，等价 spectator follow 风格）

```python
from vln_carla2.app.wiring.scene import SceneEditorSettings, run_scene_editor

settings = SceneEditorSettings(
    host="127.0.0.1",
    port=2000,
    synchronous_mode=True,
    follow_vehicle_id=42,
    spectator_initial_z=20.0,
    start_in_follow_mode=True,
    allow_mode_toggle=False,
)
run_scene_editor(settings)
```
