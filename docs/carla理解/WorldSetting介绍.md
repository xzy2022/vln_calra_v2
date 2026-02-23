`src\vln_carla2\infrastructure\carla\client_factory.py`中的`world.get_settings()`。

world.get_settings() 返回的是 carla.WorldSettings 对象。
你这段代码改的是其中 3 个字段：synchronous_mode、fixed_delta_seconds、no_rendering_mode。

WorldSettings 主要属性（CARLA 0.9.16）

synchronous_mode (bool, 默认 False)：是否同步模式。True 时服务端等客户端 tick。
no_rendering_mode (bool, 默认 False)：是否关闭渲染（提速用）。
fixed_delta_seconds (float | None)：仿真步长（秒）。常用 0.05；变量步长一般设 0.0 或 None。
substepping (bool, 默认启用)：是否开启物理子步。
max_substep_delta_time (float, 默认 0.01)：单个物理子步最大时间（秒）。
max_substeps (int, 默认 10)：每帧最多物理子步数。
max_culling_distance (float, 默认 0.0)：网格最大绘制距离（米）。
deterministic_ragdolls (bool, 默认 False)：行人死亡动画是否走确定性物理。
tile_stream_distance (float, 默认 3000)：大地图流送距离（米）。
actor_active_distance (float, 默认 2000)：大地图 actor 激活距离（米）。
spectator_as_ego (bool, 默认 True)：无 ego 时 spectator 是否影响大地图加载。