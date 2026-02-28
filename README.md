### 1.1 环境基线

- OS: Windows 11
- Python: 3.12
- CARLA:
  - `0.9.16`（UE4.26）
- CARLA 安装路径：
  - UE4：`D:\Workspace\02_Playground\CARLA_Latest`（启动：`CarlaUE4.exe`）
- 项目根目录：`D:\Workspace\00_MyRepo\vln_carla_v2`
- Python 环境：
  - UE4：`conda activate vln_carla_py312`

新的cli执行命令
```
python -m vln_carla2.app.cli_main scene run --launch-carla --no-rendering
```

scene editor 场景导入/导出（按键 `1/2` 生成对象，`Ctrl+S` 导出）：

```bash
python -m vln_carla2.app.cli_main scene run --host 127.0.0.1 --port 2000 --mode sync --scene-export-path artifacts/scene_out.json --launch-carla 
```

### 1.2 参考文档说明
`Docs_Carla_UE4` 是 CARLA 官方文档。
`PythonAPI_Carla_UE4` 是 CARLA 安装路径下的 Python API 文档。

### 2. 第0切片：最小可运行闭环

实现目标：单车闭环 `read -> compute -> apply -> tick`，固定步数后退出。

默认配置：

- 地图：`Town10HD_Opt`
- 出生点：`(x=0.038, y=15.320, z=0.15, yaw=180)`
- 控制：`VehicleControl`（Raw）
- 目标速度：`5.0 m/s`
- 步长：`fixed_delta_seconds=0.05`

运行命令：

```bash
python -m vln_carla2.app.cli_main
```

常用参数示例：

```bash
python -m vln_carla2.app.cli_main --steps 100 --target-speed-mps 5.0 --map-name Town10HD_Opt
```

日志会输出：`step/frame/speed_mps/throttle/brake`。

### 3. 测试

仅运行单元测试：

```bash
pytest tests/unit -q
```

集成 smoke（需要本地已启动 CARLA）：

```bash
pytest tests/integration/test_control_loop_smoke.py -m integration -q
```

### Scene Episode Spec 工作流

- Scene editor 快捷键：
  - `1`：生成 ego 小车（`role_name=ego`, `kind=vehicle`）
  - `2`：生成桶障碍物（`role_name=barrel`, `kind=barrel`）
  - `4`：生成目标标记小车（`role_name=goal`, `kind=_vehicle`）
  - `Ctrl+S`：导出 scene JSON；可选同时导出 `episode_spec.json`

- 开启 episode spec 导出：

```bash
python -m vln_carla2.app.cli_main scene run --export-episode-spec --launch-carla 
```

- scene 导入现在要求传入 `episode_spec.json`：

```bash
python -m vln_carla2.app.cli_main scene run --scene-import datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json
```

- 在 `.env` 中配置 episode spec 默认导出目录：

```ini
EPISODE_SPEC_EXPORT_DIR=datasets/town10hd_val_v1/episodes/ep_000001
```

`episode_spec.json` 的导出路径优先级：

1. 若显式传入 `--scene-export-path`，spec 输出到该 scene JSON 的同级目录。
2. 否则，若配置了 `EPISODE_SPEC_EXPORT_DIR`，spec 输出到该目录。
3. 否则，回退到 scene JSON 的实际导出目录。
