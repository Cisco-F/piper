# Piper Towel Fold

这个仓库当前的第一阶段目标是：

- 接入松灵 Piper 双臂从臂状态读取
- 验证 `lerobot` 环境和 `piper_sdk` 通信链路正常
- 为后续主从示教、数据采集和叠毛巾训练打基础

目前已经实现的功能是：

- 连接左右从臂 CAN 口
- 可选连接左右主臂 CAN 口
- 周期性读取左右臂 6 个关节角
- 读取左右夹爪状态
- 在终端打印观测结果
- 录制最小 JSONL episode，用于验证主从示教数据链路

## 当前硬件映射

已经在工控机上实测确认：

- 左臂从臂: `can2`
- 右臂从臂: `can0`

因此当前推荐的读取命令是：

```bash
python test_read_state.py --left-can can2 --right-can can0
```

仓库里也提供了配套脚本：

- [scripts/bringup_can.sh](/home/murphy/code/piper-towel-fold/scripts/bringup_can.sh:1)
  拉起左臂 `can2` 和右臂 `can0`
- [scripts/run_read_state.sh](/home/murphy/code/piper-towel-fold/scripts/run_read_state.sh:1)
  按当前映射运行关节状态读取

## 代码结构

- [test_read_state.py](/home/murphy/code/piper-towel-fold/test_read_state.py:1)
  当前运行入口。连接双臂并按周期打印关节角度。
- [piper.py](/home/murphy/code/piper-towel-fold/piper.py:1)
  `LeRobot` 风格的 `PiperRobot` 实现，负责连接、读取观测、读取主臂 action、断开连接。
- [recorder.py](/home/murphy/code/piper-towel-fold/recorder.py:1)
  LeRobot episode recorder，直接写 `LeRobotDataset`；同时保留 JSONL 调试 recorder。
- [record_episode.py](/home/murphy/code/piper-towel-fold/record_episode.py:1)
  第一轮试采集入口，适合先录“抓方块”。
- [test_cameras.py](/home/murphy/code/piper-towel-fold/test_cameras.py:1)
  探测 OpenCV 摄像头编号，并保存每路快照。
- [__init__.py](/home/murphy/code/piper-towel-fold/__init__.py:1)
  `PiperRobotConfig` 定义。
- [technical-roadmap.md](/home/murphy/code/piper-towel-fold/technical-roadmap.md:1)
  长期技术路线。
- [PLAN.md](/home/murphy/code/piper-towel-fold/PLAN.md:1)
  当前阶段执行计划。

## 运行前提

需要在已经配置好的工控机上运行，并满足：

- 已安装并可用 `lerobot`
- 已安装并可用 `piper_sdk`
- 左右从臂 CAN 口已经配置好
- 当前终端对 CAN 设备有访问权限

我在当前本地工作区没有现成的 `lerobot` / `piper_sdk` 环境，所以没有直接完成实机验证；下面的运行步骤是按仓库代码和你的“工控机环境已就绪”前提整理的。

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
cd /path/to/piper-towel-fold
```

注意：当前代码使用了仓库根目录下的直接导入方式，所以要在项目根目录执行命令，不要在其他目录直接调用脚本。

### 3. 激活 `lerobot` 环境

如果你是 `conda`：

```bash
conda activate <your-lerobot-env>
```

如果你是 `venv`：

```bash
source <venv-path>/bin/activate
```

如果工控机已经把环境做成固定 shell 初始化，也可以直接进入下一步。

### 4. 先检查依赖是否存在

```bash
python -c "import lerobot, piper_sdk; print('imports ok')"
```

如果这一步报错，先不要继续跑脚本，优先确认当前 shell 是否真的进入了工控机上的 `lerobot` 环境。

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
python test_read_state.py --left-can can2 --right-can can0
```

如果左右从臂对应的 CAN 口不同，按实际情况修改：

```bash
python test_read_state.py --left-can <left_can> --right-can <right_can>
```

如果你想调打印频率，可以加 `--period`：

```bash
python test_read_state.py --left-can can2 --right-can can0 --period 0.2
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
python record_episode.py \
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
python record_episode.py \
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
python test_cameras.py --indices 0,1,2,3,4,5
```

脚本会把能打开的画面保存到：

```text
data/camera_probe/
```

看快照确认 3 个可用编号后，用这些编号开始录制。示例中假设 3 个摄像头是 `0,2,4`：

```bash
python record_episode.py \
  --task pick_cube \
  --dataset-format lerobot \
  --repo-id local/piper_pick_cube \
  --root data/lerobot \
  --follower-left-can can2 \
  --follower-right-can can0 \
  --leader-left-can <leader_left_can> \
  --leader-right-can <leader_right_can> \
  --action-source leader \
  --camera-indices 0,2,4 \
  --camera-names cam_top,cam_left,cam_right \
  --camera-width 640 \
  --camera-height 480 \
  --camera-fps 30 \
  --fps 10
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

建议第一天只录 5 到 10 条短 episode，每条 20 到 40 秒。每条录完后先用 `LeRobotDataset` 加载检查 episode 数、帧数、图像和低维字段是否正常。

## 常见问题排查

### 1. `ModuleNotFoundError: No module named 'lerobot'`

说明当前 shell 没进入已配置好的环境，或者环境里没有安装 `lerobot`。

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
