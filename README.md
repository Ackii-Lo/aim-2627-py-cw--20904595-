# AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块

> **全部题目、规范、评分、提交见 [题面.pdf](题面.pdf)。** 本 README 只讲怎么把环境跑起来；没在这里出现的规格细节，一律以题面为准。

## 1. 环境要求

- Python 3.8+，仅标准库（不允许第三方运行时依赖）；
- 开发工具只需 `pytest`（测试）与 `autopep8`（风格，CI 会检查）；
- VS Code 打开仓库会推荐安装 `ms-python.autopep8` 插件（`.vscode/extensions.json`），保存即格式化即可过风格检查。

## 2. 快速开始

```bash
# 1. 用 GitHub 的 Use this template 创建你自己的仓库，然后 clone
git clone https://github.com/<你的用户名>/<你的仓库>.git
cd <你的仓库>   # 直接在 main 分支上开发

# 创建虚拟环境

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. 装依赖
python -m pip install pytest autopep8

# 3. 启用 AI 会话归档钩子（课程要求，见下方第 3 节）
python -m pip install 'agent-session-commit[pre-commit]==0.1.3' -i https://pypi.org/simple
agent-session-commit install --pre-commit   # 交互选择你的 AI 助手与会话目录

# 4. 跑测试（刚到手：全部 skip，CI 是绿的）
python -m pytest

# 5. 看演示
python main.py

# 6. 打开 题面.pdf 读题，开始实现 src/main/__init__.py 里的 TODO
```

## 3. AI 会话归档（pre-commit）

本课程允许使用 AI，提交的 commit 需要携带 AI 会话归档作为透明化记录：每次 `git commit` 后，钩子会把新增会话自动 amend 进同一个提交（`.agent-sessions/bundles/`），不产生额外的归档提交。支持 Claude Code、OpenAI Codex CLI、GitHub Copilot CLI、Qoder、ZCode、Trae、Tencent CodeBuddy 等（完整名单见 [AgentLedger](https://github.com/Gentle-Lijie/AgentLedger)）。

- 配置是仓库本地的：每个 clone 运行一次 `agent-session-commit install --pre-commit`，方向键选择 agent、确认其会话目录即可；
- 不想用 TUI 可手动配置：`git config --local agent-session.agent claude`、`git config --local agent-session.source "<会话目录>"`，然后 `python -m pip install 'pre-commit>=3.2.0' && pre-commit install`；
- 归档是普通 Git 内容且会推送到公开仓库——不要在 AI 会话里粘贴令牌等敏感信息；
- 换了 agent 或目录就重跑一次安装命令；卸载：从 `.pre-commit-config.yaml` 移除该条目后重跑 `pre-commit install`。

## 4. 本地开发循环

- **写代码**：全部作业在 `src/main/__init__.py`，按题面各题规范补全每个标有 TODO 的函数；注释里标注了对应的题面主题，推荐顺序 Q1 → Q6。
- **跑测试**：`python -m pytest` —— 可见测试是规格书的一部分，未实现的函数自动 skip，实现一个、对应测试亮一个。本地全绿 ≠ 满分（见题面）。
- **看演示**：`python main.py`（等价于 `PYTHONPATH=src python -m main`），随实现进度逐段点亮，不进测试。
- **Q6 自测**：`python tools/run_seeds.py --q6`（200 张固定地图统计），单 seed 渲染 `python tools/run_seeds.py --q6 --seed <N> --render`，Bonus 模式 `python tools/run_seeds.py --bonus`。

## 5. 仓库结构（哪些能改）

| 路径 | 说明 | 能否修改 |
|---|---|---|
| `src/main/__init__.py` | 你的全部作业（TODO 所在） | ✅ |
| `README.md` | 仅末尾两个"你来写"小节 | ✅ |
| `题面.pdf` | 题面（唯一规格说明） | ❌ 勿改 |
| `src/main/legacy_patrol.py` | Q7 模块（与主体同步发布，修复其缺陷） | Q7 时 ✅ |
| `.pre-commit-config.yaml` | AI 会话归档钩子配置 | ❌ 勿改 |
| `src/tests/`、`tools/`、`.github/`、`conftest.py`、`pytest.ini`、`main.py` | 测试与基础设施 | ❌ 勿改 |

CI 只允许修改 `src/main/**`、`README.md` 与 `.agent-sessions/**`（AI 会话归档）——其余文件改了直接红；autopep8 `--diff` 非空即败。提交方式（push、问卷、commit 粒度）见题面"提交与验收"一节。

## 6. Q7 缺陷逐条分析（src/main/legacy_patrol.py）

题面要求逐条写明"错在哪、你是怎么定位到的"。以下 6 处按我实际排查的顺序记录，每处给出症状、定位过程与修法。

### 缺陷 1：`total_route_meters` 单位错误

- **症状**：`total_route_meters([(0, 0), (3, 0), (3, 4)])` 期望 7（米），实际返回 700。
- **定位过程**：跑 `pytest -k Q7` 时这一条断言最先失败。反查调用链，`total_route_meters` 把 `segment_length_cm` 的返回值直接累加——而被调用方的名字和 docstring 都写明"单位：厘米"，函数出口却没有做任何换算。函数名里的 `_meters` 与被累加值的单位直接矛盾，是这一处最明显的 fingerprint。
- **修法**：先按厘米累加为整数，最后整体 `/ 100.0` 换算成米返回。

### 缺陷 2：`calibrate` 在没有正样本时崩溃

- **症状**：`calibrate([-1, -2])`（有样本但全为负）抛 `TypeError: unsupported operand type(s) for -: 'int' and 'NoneType'`，而不是按契约返回 0；而 `calibrate([])` 恰好返回 0。
- **定位过程**：docstring 写明"样本为空或没有正样本时，漂移为 0"。继续往上看 `first_positive`——它在没有正数时按上游约定返回 `None`，于是 `calibrate` 里的 `drift += s - baseline` 就成了 `s - None`。空列表进不去循环所以侥幸正确，这正是它一开始没被发现的原因。
- **修法**：`baseline is None` 时提前 `return 0`，不再进循环。这样空列表与"全非正样本"两条路径统一。
- **遮蔽关系**：这一处与 `first_positive` 构成一对互相遮蔽的 bug——不看清 `first_positive` 会返回 `None`，就永远看不到 `calibrate` 里的这个异常；而只测 `calibrate([])` 又恰好测不到它，必须用非空的负样本才暴露。

### 缺陷 3：`log` 的可变默认参数

- **症状**：`log("a")` 返回 `["a"]`，紧接着 `log("b")` 却返回 `["a", "b"]`，两次调用互相污染。
- **定位过程**：docstring 说"不显式传入 `history` 时，每次调用都从空历史开始"，而签名写的是 `def log(message, history=[])`。默认参数只在函数定义时求值一次，这个列表被之后所有调用共享，`append` 自然越堆越长。
- **修法**：默认值改为 `None`，函数体内 `if history is None: history = []`。

### 缺陷 4：`summarize_events` 漏掉 `max_id` 本身

- **症状**：`summarize_events(events, 2)` 期望统计到 2 个事件（id 为 1 和 2），实际只有 1 个。
- **定位过程**：docstring 的表述是"统计 id **不超过** `max_id` 的事件"，即 `id <= max_id`；代码里写的是 `if e["id"] < max_id`，把恰好等于边界的那一条排除了。这是典型的差一错误，读 docstring 的措辞就能定位。
- **修法**：`<` 改为 `<=`。

### 缺陷 5：`run_legacy_sim` 的 `round_` 从不自增

- **症状**：函数不返回、trace 无限增长（可见测试 `test_sim_stops_at_threshold` 会挂死），且 trace 里看不到"第 4 轮起额外 -5"的任何表现。
- **定位过程**：docstring 说"第 4 轮起（轮号 >= 3）每轮额外消耗 5 点"，而 `while` 循环体里根本没有 `round_ += 1`——`round_` 恒为 0，`if round_ >= 3` 永远不成立，`while round_ < rounds` 也永远不退出。两个症状其实同源。
- **修法**：每轮结尾补 `round_ += 1`。

### 缺陷 6：`run_legacy_sim` 终止条件写反

- **症状**：修完缺陷 5 之后才暴露——`run_legacy_sim(2, 28)` 本应只执行 1 轮就停，实际会跑满 2 轮。
- **定位过程**：修好 `round_` 自增、循环能正常推进后，再对照 docstring"任一轮结束后体力 <= 20 时立即终止"，发现代码写的是 `if stamina > 20: break`，语义正好相反：体力还够的时候退出，该退的时候反而不退。
- **修法**：改成 `if stamina <= 20: break`。

### 踩坑记录：为什么这一题不能按代码位置排查

这 6 处里有两对是互相遮蔽的，排查顺序不能顺着代码从上往下走。**必须先修表层的（单位换算、可变默认值这类独立可见的），再修被表层盖住的那个异常**：`first_positive` 不确认会返回 `None`，就看不到 `calibrate` 崩溃；`round_` 不自增，循环根本走不到终止条件那一行，也就看不到缺陷 6。所以缺陷 2 与缺陷 6 的发现都依赖"前一处已经修好"这个前提。

另外，本题**不能用 git log 判断对错**。模板仓库压缩了历史，本仓库只有一条 Initial commit，题面里提到的那次"标注 fix、实际把正确实现改错方向"的提交在这里根本不存在——无论提交信息写了什么，一律以各函数 docstring 的契约和可见测试的报错为准。

## 7. 设计决策与 AI 使用说明

### 实现方式分工

Q1–Q5 是在 CodeBuddy CLI 中实现的。我负责读题面、锁定每题的边界条件，再逐题 review，遇到分歧由我裁定——例如 Q1 用 `hp * 100 // max_hp` 先乘后除以避免浮点误差导致结果偏小 1、Q5 收到的 `hp` 是绝对血量必须先换算成百分比才能套用规则表、Q5 的 `enemy_dist` 为 `None` 或负数时统一归一为 99。

Q6 的主循环骨架是我本人写的：主循环结构、贪心选向、贴墙状态机的入口、以及 `visited_count` / `steps` 的统计口径。中途我低估了脱困策略的调参难度，把这部分交回 CLI 完成，最后以 200 seed 的三项阈值作为验收依据。

Q7 由我定位出全部 6 处缺陷，并给出每一处的症状与修法，CLI 按此实施并跑通测试；上面的逐条分析即出自这次排查。

### 几个题面未明示、由数据或口径裁定的边界

Q1 的电量档位阈值题面没有给数字，只给了 75=OK / 30=WARNING / 5=LOW 三个样本。我决定采用 `>50` 为 OK、`20 < b <= 50` 为 WARNING、`<= 20` 为 LOW，即阈值本身归入较低档——三个样本全部落在正确的档位，且 20 与 50 这两个边界都不悬空。

Q5 的 R2 恢复阈值题面只说"恢复到安全血量"，同样未给数字。我采用 `hp_pct > 60` 才从 RETREAT 转出，60 本身仍保持 RETREAT：R1 的保命线是 30，恢复线取 60 既高于保命线、又不至于刚脱离危险就立刻复出。

Q3 的碰撞计数只统计撞障碍，不统计界外撞墙。这直接影响 Q6 的"平均碰撞 <= 1.5"这条阈值。但需要把两件事严格区分开：**碰撞计数排除界外是对的**（撞地图边缘不算机器人的失误），而**贴墙时判断"能不能走"必须把界外算作走不通**——这两件事服务于完全不同的目的，下一节会给出实测依据。

Q6 的贪心方向改用 Q4 的 `next_step_toward`（题面 Q6 规范第 1 条本来就要求"用 Q4 贪心策略选取方向"）。它优先走 `|Δ|` 较大的轴，路径更直，步数/BFS 比从 1.45 降到 1.07。

### Q6 脱困策略的结构，与一次被实测推翻的判断

结构上分四段：贪心 → 卡住（四个方向都无法让曼哈顿距离严格变小）则进入左手贴墙 → 贴墙走满 4 步仍未脱困则改用 BFS 领航（在四邻域中挑 BFS 距离最小者）→ 距离小于进入贴墙时记录的 `entry` 则退出贴墙、回到贪心。

这里有一次判断被数据推翻，是本题最关键的取舍。我最初认为贴墙模式必须用"只看 `obstacles`"来判断走不通，理由是贴墙要允许撞界外、地图边界才是要找的那面墙。200 seed 实测该写法只有 **24.5%**：机器人把界外当成空地，永远贴不上任何一面墙，左手规则退化为在开阔地原地绕圈（seed 1 可复现，机器人在一个 2×2 空腔里循环了近 500 步）。改用 `is_blocked`（界外算墙）后立刻升到 **81.5%**。最终结论就是上一节说的那句话：碰撞计数排除界外、走不通判定包含界外，两者必须分开处理——前者服务于碰撞统计，后者服务于贴墙策略。

至于为什么还必须加 BFS 兜底：纯左手贴墙我做了换手阈值扫描，`mult=0.25` 得 92.5% / 1.36，`mult=0.5` 得 95.5% / 1.45，`mult=0.75` 得 97.5% / 1.62——成功率与步数比是**同向**变化的，没有任何参数点能同时满足 92% 与 1.35。加入"4 步贴墙窗口 + BFS 领航"之后，三项收敛到 **100% / 0.11 / 1.07**。需要说明的是，纯贴墙能脱的困（绝大多数）仍由左手贴墙处理，BFS 只兜那 4 步还没脱出来的少数情况，并没有取代它。

### Q6 统计口径

- `steps` 只统计 `move_forward()` 之后的一次推进，转向不计入步数；
- `collisions` 直接取 `grid.collision_count`；
- `visited_count = len(trail)`，`trail` 用 `set` 以自动去重；
- `success` 与 `found_enemy` 同义。

### AI 使用方式与归档

本作业的 AI 参与方式如上所述：Q1–Q5 由 CodeBuddy CLI 直接实现，Q6 由我在其协助下完成主循环与策略调试，Q7 我给出定位结论后由 CLI 实施。`src/main/__init__.py` 与 `src/main/legacy_patrol.py` 首行均标记 `# aim-py-cw-known`，说明这两个文件有AI 直接参与生成。

会话归档经pre-commit 钩子落在 `.agent-sessions/bundles/`，可直接在公开仓库中查阅。这里有一个需要说明的配置细节：钩子默认的 `codebuddy` 适配器按`user` / `assistant` 类型的记录识别会话，而当前 CodeBuddy CLI 写出的记录类型是 `message`，两者不匹配——`agent-session-commit status` 会显示 4 个候选全部被判为 unverifiable、找到 0 个会话。因此我把 `agent-session.agent` 从 `codebuddy` 改为 `custom`，指向同一个 `~/.codebuddy/projects` 目录：该适配器只校验记录顶层`cwd` 是否精确等于本仓库根目录。归档内容是原始会话文件的逐字节拷贝，未做任何删改。

首次 commit 时钩子报了 `[WinError 4551]`（Windows 应用程序控制策略拦截）而未落盘——这是环境层面的拦截，钩子的 post-commit 阶段失败、不影响提交本身。手动重跑同一条钩子命令后归档正常写入：3 个会话文件（共约 1.75 MB 原始 JSONL）打包进提交 `dc67105` 的一个 bundle，压缩后 300 KB。后续 commit 只归档增量（`mode: append`，记录偏移量而非重复全量），所以每个 bundle 都很小。

