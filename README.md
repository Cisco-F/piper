# Piper

这个仓库当前的第一阶段目标是：

- 接入松灵 Piper 双臂从臂状态读取
- 验证 `piper` 环境和 `piper_sdk` 通信链路正常
- 为后续主从示教、数据采集和叠毛巾训练打基础

目前已经实现的功能是：

- 连接左右从臂 CAN 口
- 可选连接左右主臂 CAN 口
- 周期性读取左右臂 6 个关节角
- 读取左右夹爪状态
- 在终端打印观测结果
- 直接录制 LeRobot dataset，并保留 JSONL 调试格式

## 当前硬件映射

已经在工控机上实测确认：

- 左臂从臂: `can2`
- 右臂从臂: `can0`

因此当前推荐的读取命令是：

```bash
PYTHONPATH=src python tools/test_read_state.py --left-can can2 --right-can can0
```

仓库里也提供了配套脚本：

- [scripts/bringup_can.sh](scripts/bringup_can.sh)
  拉起左臂 `can2` 和右臂 `can0`
- [scripts/run_read_state.sh](scripts/run_read_state.sh)
  按当前映射运行关节状态读取
- [scripts/start_recording.sh](scripts/start_recording.sh)
  按配置文件启动抓方块 LeRobot 录制

## 代码结构

- [tools/test_read_state.py](tools/test_read_state.py)
  当前运行入口。连接双臂并按周期打印关节角度。
- [src/piper_towel_fold/piper.py](src/piper_towel_fold/piper.py)
  `LeRobot` 风格的 `PiperRobot` 实现，负责连接、读取观测、读取主臂 action、断开连接。
- [src/piper_towel_fold/recorder.py](src/piper_towel_fold/recorder.py)
  LeRobot episode recorder，直接写 `LeRobotDataset`；同时保留 JSONL 调试 recorder。
- [src/piper_towel_fold/record_episode.py](src/piper_towel_fold/record_episode.py)
  第一轮试采集入口，适合先录“抓方块”。
- [tools/test_cameras.py](tools/test_cameras.py)
  探测 OpenCV 摄像头编号，并保存每路快照。
- [src/piper_towel_fold/config.py](src/piper_towel_fold/config.py)
  `PiperRobotConfig` 定义。
- [technical-roadmap.md](technical-roadmap.md)
  长期技术路线。
- [PLAN.md](PLAN.md)
  当前阶段执行计划。

## 运行前提

需要在已经配置好的工控机上运行，并满足：

- 已安装并可用 `lerobot`
- 已安装并可用 `piper_sdk`
- 左右从臂 CAN 口已经配置好
- 当前终端对 CAN 设备有访问权限

我在当前本地工作区没有现成的 `piper` 环境，所以没有直接完成实机验证；下面的运行步骤是按仓库代码和你的“工控机环境已就绪”前提整理的。

## 如何通过 SSH 运行

### 1. SSH 登录工控机

```bash
ssh <username>@<ipc-ip>
```

示例：

```bash
ssh murphy@192.168.1.20
```

### 2. 进入项目目录

```bash
cd /path/to/piper
```

注意：当前代码使用了仓库根目录下的直接导入方式，所以要在项目根目录执行命令，不要在其他目录直接调用脚本。

### 3. 激活 `piper` 环境

如果你是 `conda`：

```bash
conda activate piper
```

如果你是 `venv`：

```bash
source /path/to/piper/bin/activate
```

如果工控机已经把环境做成固定 shell 初始化，也可以直接进入下一步。

### 4. 先检查依赖是否存在

```bash
python -c "import lerobot, piper_sdk; print('imports ok')"
```

如果这一步报错，先不要继续跑脚本，优先确认当前 shell 是否真的进入了工控机上的 `piper` 环境。

### 5. 运行关节角读取脚本

先拉起 CAN：

```bash
./scripts/bringup_can.sh
```

然后运行读取脚本：

```bash
./scripts/run_read_state.sh
```

如果你更想直接调用 Python，也可以：

```bash
PYTHONPATH=src python tools/test_read_state.py --left-can can2 --right-can can0
```

如果左右从臂对应的 CAN 口不同，按实际情况修改：

```bash
PYTHONPATH=src python tools/test_read_state.py --left-can <left_can> --right-can <right_can>
```

如果你想调打印频率，可以加 `--period`：

```bash
PYTHONPATH=src python tools/test_read_state.py --left-can can2 --right-can can0 --period 0.2
```

这里 `--period 0.2` 表示每 0.2 秒打印一次，也就是 5 Hz。

如果你想通过环境变量改脚本参数：

```bash
BITRATE=1000000 ./scripts/bringup_can.sh
PERIOD=0.2 ./scripts/run_read_state.sh
```

### 6. 正常输出示例

```text
Connected. Press Ctrl+C to stop.
2026-06-03 10:00:00
left: j1=  12.345 deg, j2= -30.210 deg, j3=  45.678 deg, j4=   1.234 deg, j5=  89.012 deg, j6=  -5.678 deg, gripper=0.012345
right: j1= -11.222 deg, j2=  22.333 deg, j3= -33.444 deg, j4=  44.555 deg, j5= -55.666 deg, j6=  66.777 deg, gripper=0.023456
```

按 `Ctrl+C` 停止。

## 录制第一段抓方块试采集

在确认主臂已经能稳定控制从臂后，可以直接录成 `LeRobotDataset`。LeRobot 官方格式会把低维状态和 action 存成 Parquet，把多路图像编码成视频，并写入 `meta/` 元数据。

先用从臂状态作为 action 做 smoke test：

```bash
PYTHONPATH=src python -m piper_towel_fold.record_episode \
  --task pick_cube \
  --dataset-format lerobot \
  --repo-id local/piper_pick_cube \
  --root data/lerobot \
  --follower-left-can can2 \
  --follower-right-can can0 \
  --action-source follower \
  --fps 10 \
  --duration 30
```

如果主臂也接到了工控机 CAN，并且可以读取主臂角度，则优先录主臂 action：

```bash
PYTHONPATH=src python -m piper_towel_fold.record_episode \
  --task pick_cube \
  --dataset-format lerobot \
  --repo-id local/piper_pick_cube \
  --root data/lerobot \
  --follower-left-can can2 \
  --follower-right-can can0 \
  --leader-left-can <leader_left_can> \
  --leader-right-can <leader_right_can> \
  --action-source leader \
  --fps 10
```

### 接入 3 个摄像头

先探测摄像头编号：

```bash
python tools/test_cameras.py --indices 0,1,2,3,4,5
```

脚本会把能打开的画面保存到：

```text
data/camera_probe/
```

摄像头编号不是按视角命名的，也不一定连续。它们是 Linux/OpenCV 看到的设备编号，和 USB 插口、系统枚举顺序有关，所以可能是 `0,1,2`，也可能是 `0,2,4` 或 `1,3,5`。必须以 `tools/test_cameras.py` 快照和实际录制视频为准。

当前实测视频内容是：

- `0`: 右侧摄像头
- `2`: 顶视摄像头
- `4`: 左侧摄像头

因此当前推荐映射是：

```bash
--camera-indices 2,4,0 \
--camera-names cam_top,cam_left,cam_right
```

也就是 `2 -> cam_top`，`4 -> cam_left`，`0 -> cam_right`。完整录制命令：

```bash
PYTHONPATH=src python -m piper_towel_fold.record_episode \
  --task pick_cube \
  --dataset-format lerobot \
  --repo-id local/piper_pick_cube \
  --root data/lerobot \
  --follower-left-can can2 \
  --follower-right-can can0 \
  --leader-left-can <leader_left_can> \
  --leader-right-can <leader_right_can> \
  --action-source leader \
  --camera-indices 2,4,0 \
  --camera-names cam_top,cam_left,cam_right \
  --camera-width 640 \
  --camera-height 480 \
  --camera-fps 30 \
  --fps 10 \
  --prompt-outcome
```

现在也可以直接用配置文件启动，默认配置在 [configs/record_pick_cube.json](configs/record_pick_cube.json)。常改的项目都已经放进去，包括：

- 录制帧率 `fps`
- 左右臂 CAN 口
- 相机映射 `cameras[].ref`
- 相机名称 `cameras[].name`
- 相机分辨率和采集帧率

默认启动：

```bash
./scripts/start_recording.sh
```

使用其他配置文件：

```bash
./scripts/start_recording.sh configs/your_record_config.json
```

也可以直接用配置文件启动脚本：

```bash
./scripts/start_recording.sh
```

如果要录 leader action，直接修改 [configs/record_pick_cube.json](configs/record_pick_cube.json) 里的 `leader_left_can` 和 `leader_right_can`。

## 训练 ACT 策略

采集完成后，先确认数据集里有 `meta/info.json` 和 `data/**/*.parquet`，再启动训练：

```bash
./scripts/train_act.sh
```

默认配置会读取：

```text
data/lerobot/local/piper_pick_cube
```

也可以用环境变量覆盖：

```bash
REPO_ID=local/piper_pick_cube \
ROOT=data/lerobot \
JOB_NAME=act_piper_pick_cube \
STEPS=20000 \
BATCH_SIZE=16 \
DEVICE=cuda \
./scripts/train_act.sh
```

ACT 默认从头训练，不需要先拉取模型；如果后续把 `POLICY_TYPE` 换成需要预训练权重的策略，LeRobot 可能会在第一次运行时从 Hugging Face 下载对应 checkpoint。训练跑到 `STEPS` 指定步数并写出 checkpoint 后结束，输出目录默认是：

```text
outputs/train/<job_name>
```

录制结果会写到：

```text
data/lerobot/local/piper_pick_cube/
├── data/
├── meta/
└── videos/
```

每一帧写入的 LeRobot keys 是：

- `observation.state`: 14 维，从臂左右关节和夹爪状态
- `action`: 14 维，优先来自主臂；也可以用 follower smoke test
- `observation.images.cam_top`
- `observation.images.cam_left`
- `observation.images.cam_right`

如果需要临时调试原始逐帧 JSON，也可以加：

```bash
--dataset-format jsonl
```

## 离线推理和真机测试

训练完成后，checkpoint 默认在：

```text
outputs/train/act_piper_pick_cube/checkpoints/last/pretrained_model
```

先用已录好的数据做离线回放检查：

```bash
PYTHONPATH=src python -m piper_towel_fold.offline_infer \
  --policy-path outputs/train/act_piper_pick_cube/checkpoints/last/pretrained_model \
  --repo-id local/piper_pick_cube \
  --dataset-root data/lerobot/local/piper_pick_cube \
  --episode-index 0 \
  --frame-offset 800 \
  --num-frames 50
```

真机测试分两步。第一步先 dry-run，只读实时相机和关节状态、加载 policy、打印预测 action，不会下发控制：

```bash
./scripts/run_policy_live.sh
```

确认预测值没有明显跳变后，再短时间执行。第一次建议只跑 3 到 5 秒，并把手放在急停附近：

```bash
EXECUTE=true DURATION=3 ./scripts/run_policy_live.sh
```

实时执行默认做了两层保守处理：

- `SMOOTHING_ALPHA=0.25`: 对 policy 输出做指数平滑
- `MAX_JOINT_STEP_RAD=0.025`: 每个控制周期每个关节最多走约 1.4 度
- `MAX_GRIPPER_STEP_M=0.001`: 每个控制周期夹爪最多变化 1 mm

如果真机动作太慢，可以逐步放宽，例如：

```bash
EXECUTE=true \
DURATION=5 \
MAX_JOINT_STEP_RAD=0.04 \
SMOOTHING_ALPHA=0.4 \
./scripts/run_policy_live.sh
```

不要在第一次执行时把限速直接调很大。离线误差即使看起来不错，实时相机延迟、起始姿态偏差、物体位置变化都会让第一版策略产生更大的动作误差。

建议第一天只录 5 到 10 条短 episode，每条 20 到 40 秒。每条录完后先用 `LeRobotDataset` 加载检查 episode 数、帧数、图像和低维字段是否正常。

### 手动结束一条 episode

如果不传 `--duration`，录制会一直进行。任务成功、失败或你想丢弃这次尝试时，按一次 `Ctrl+C` 停止；脚本会等当前帧完整写完后再正常 `save_episode()`，不会在图片写入中途切断 episode。

如果加了 `--prompt-outcome`，停止后会让你输入：

```text
s = success
f = failure
u = unknown
```

结果会追加到：

```text
data/lerobot/local/piper_pick_cube/episode_outcomes.jsonl
```

这份文件用于后续筛选成功/失败 episode。现在它是旁路标注文件，不会改变 LeRobot 原始 dataset schema。

### 为什么录制中会看到 PNG

LeRobot 在录制视频特征时，会先把每帧图像写成临时 PNG，再在 `save_episode()` / `finalize()` 阶段编码成 `videos/` 里的视频，同时把 `observation.state`、`action`、episode index 等低维数据写入 `data/` 下的 Parquet。

所以如果录制被中途强行打断，可能只看到临时 PNG，看不到完整 Parquet，或者出现类似 `episode_index expected length ...` 的列长度错误。当前脚本已经把 `Ctrl+C` 改成帧边界停止，正常停止后应该能同时得到：

- `videos/`: 三路相机视频
- `data/`: 低维状态和 action 的 Parquet
- `meta/`: 数据集元信息

## 常见问题排查

### 1. `ModuleNotFoundError: No module named 'lerobot'`

说明当前 shell 没进入已配置好的 `piper` 环境，或者环境里没有安装 `lerobot`。

先检查：

```bash
which python
python -c "import lerobot; print(lerobot.__file__)"
```

### 2. `ImportError: piper_sdk is not installed in the current Python environment.`

说明 `piper_sdk` 不在当前 Python 环境中。

先检查：

```bash
python -c "import piper_sdk; print(piper_sdk.__file__)"
```

### 3. 脚本启动了，但角度不变化或一直是 0

优先检查：

- CAN 口名字是否填对
- 从臂是否上电
- `piper_sdk` 是否能独立读到状态
- 左右臂是否和当前映射一致

### 4. 脚本卡在连接阶段

优先检查：

- CAN 设备是否真的起来了
- 工控机是否能看到 `can0` / `can2`
- SDK 使用的接口名是否和系统接口名一致

可以先看网口状态：

```bash
ip link show can0
ip link show can2
```

如果脚本拉起失败，也可以手动执行：

```bash
sudo ip link set can2 down
sudo ip link set can2 type can bitrate 1000000
sudo ip link set can2 up

sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
```

## 当前脚本的边界

当前版本还只是“读状态”的最小闭环，暂时还没有：

- 主臂到从臂的 teleop
- `LeRobot` 正式数据录制流程
- 动作下发控制
- 相机观测接入到采集流程
- 叠毛巾任务数据集定义

所以这一步更适合当作硬件打通和观测字段确认。

## 下一步建议

建议按下面顺序继续推进：

1. 先稳定读取双臂状态，确认左右 CAN 映射、零位和单位都正确。
2. 用脚本固定 CAN 启动和读取流程，减少环境误差。
3. 然后补“最小控制闭环”或 teleop，而不是立刻开始正式采集。
4. 接入相机并统一时间戳。
5. 最后再进入 `LeRobot` 数据采集和训练。

## 下一步是不是直接正式采集数据

现在可以开始 LeRobot 格式的最小试采集，但还不建议直接进入正式大规模采集。

当前适合做的是：

- 用“抓方块”验证 LeRobot episode 录制
- 固定 task、fps、开始/结束规则
- 确认 action 字段到底来自主臂还是从臂状态
- 录几条短 episode 后检查数据质量

正式训练前还需要补：

- 图像、状态、action 的时间戳质量检查
- 数据集加载、可视化和训练配置
- 成功/失败标签和 episode SOP
