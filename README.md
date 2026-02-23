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
python -m vln_carla2.adapters.cli.main
```

常用参数示例：

```bash
python -m vln_carla2.adapters.cli.main --steps 100 --target-speed-mps 5.0 --map-name Town10HD_Opt
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
