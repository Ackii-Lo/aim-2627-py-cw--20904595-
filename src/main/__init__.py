# aim-py-cw-known
# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from collections import deque
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """血量百分比：0-100 的 int。

    全整数运算（hp * 100 // max_hp，先乘后整除）避免浮点误差导致结果偏小 1，
    最后夹取到 [0, 100]。
    """
    if max_hp <= 0:
        raise ValueError("max_hp 必须为正")
    ratio = hp * 100 // max_hp
    if ratio < 0:
        return 0
    if ratio > 100:
        return 100
    return int(ratio)


def status_report(name, robot_type, hp, max_hp, battery):
    """一行自检报告：名称左对齐 10 字符、机型居中 10 字符、百分比右对齐 3 字符。"""
    pct = hp_ratio(hp, max_hp)
    # 电量显示用 int() 向零截断：与 Q3 坐标规范化的取整方式保持一致，
    # 且 battery=75 时显示为 75（可见测试的基准样例）。
    level = int(battery)
    # 档位阈值（题面未给数字，阈值本身归入较低档）：>50 OK，20<b<=50 WARNING，<=20 LOW
    if level > 50:
        tier = "OK"
    elif level > 20:
        tier = "WARNING"
    else:
        tier = "LOW"
    return "{:<10}|{:^10}|HP {:>3}%|BAT {:>3}%|{}".format(
        name, robot_type, pct, level, tier)


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
# ---- Q2 私有辅助 ----
# 以下为 Q2 日志解析的私有工具函数，只服务于 analyze_damage_log，
# 不属于任何其它题目，也不对外暴露。
# 传感器行段字母 -> 部位；most_hit 并列时的固定优先级
_SENSOR_ARMOR = {"F": "front", "L": "left", "R": "right"}
_ARMOR_PRIORITY = ("front", "left", "right")


def _positive_int(value):
    """是否为严格正整数（bool 不算 int）。"""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _parse_sensor_line(text):
    """传感器行 -> {部位: 伤害}；任一段不合法则整行按脏行返回 None。"""
    hits = {}
    for segment in text.split(","):
        letter, sep, raw = segment.strip().partition(":")
        armor = _SENSOR_ARMOR.get(letter)
        if not sep or armor is None:
            return None
        try:
            damage = int(raw.strip())
        except ValueError:
            return None
        if damage <= 0:
            return None
        hits[armor] = hits.get(armor, 0) + damage
    return hits or None


def _parse_json_line(text):
    """JSON 行 -> (部位, 伤害, id 或 None)；缺字段/字段非法返回 None。"""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    armor = data.get("armor")
    damage = data.get("damage")
    if armor not in _ARMOR_PRIORITY or not _positive_int(damage):
        return None
    event_id = data.get("id")
    if not isinstance(event_id, (int, float, str)):
        event_id = None
    return armor, damage, event_id


def analyze_damage_log(lines):
    """解析混合格式伤害日志：脏行一律跳过，解析全程不抛异常。"""
    by_armor = {"front": 0, "left": 0, "right": 0}
    total = 0
    events = 0
    seen_ids = set()
    for line in lines or ():
        if not isinstance(line, str):
            continue
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("{"):
            parsed = _parse_json_line(text)
            if parsed is None:
                continue
            armor, damage, event_id = parsed
            if event_id is not None:
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)
            by_armor[armor] += damage
            total += damage
        else:
            hits = _parse_sensor_line(text)
            if hits is None:
                continue
            for armor, damage in hits.items():
                by_armor[armor] += damage
                total += damage
        events += 1
    most_hit = None
    for armor in _ARMOR_PRIORITY:
        if by_armor[armor] and (most_hit is None
                                or by_armor[armor] > by_armor[most_hit]):
            most_hit = armor
    avg = round(total / events, 2) if events else 0.0
    return {"total": total, "by_armor": by_armor,
            "most_hit": most_hit, "avg": avg}


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    # 顺时针朝向环，供 turn_left / turn_right 取相邻项
    _FACING_RING = (Facing.UP, Facing.RIGHT, Facing.DOWN, Facing.LEFT)

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """位置 setter：三重校验（类型 -> 长度 -> 元素 int() 规范化）。"""
        if not isinstance(value, (tuple, list)):
            raise TypeError("current_pos 只接受 tuple 或 list")
        if len(value) != 2:
            raise TypeError("current_pos 长度必须为 2")
        # int() 为向零截断（如 -2.7 -> -2）；元素无法转 int 时由其自行抛出
        self._pos = (int(value[0]), int(value[1]))

    def move_forward(self):
        """朝当前 facing 前进一格，返回执行后的位置。

        电量耗尽：不移动、不计碰撞、不耗电；前方是障碍：原地不动、朝向不变、
        collision_count 加 1 且不耗电；前方是界外：只原地返回，不计碰撞、
        不耗电（碰撞只绑定"前方格为障碍"）；可通行则移动并扣 1 点电量。
        """
        if self._fuel <= 0:
            return self._pos
        delta = self._facing.delta
        nxt = (self._pos[0] + delta[0], self._pos[1] + delta[1])
        if nxt in self._obstacles:
            self._collision_count += 1
            return self._pos
        if not (0 <= nxt[0] < self._width and 0 <= nxt[1] < self._height):
            return self._pos
        self._fuel -= 1
        self._pos = nxt
        return self._pos

    def turn_left(self):
        """原地左转 90°，返回新的 Facing（不耗电）。"""
        index = self._FACING_RING.index(self._facing)
        self._facing = self._FACING_RING[(index - 1) % 4]
        return self._facing

    def turn_right(self):
        """原地右转 90°，返回新的 Facing（不耗电）。"""
        index = self._FACING_RING.index(self._facing)
        self._facing = self._FACING_RING[(index + 1) % 4]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """返回下一步应朝向的 Facing（单步贪心）。

    候选 = 相邻格不是障碍、且移动后曼哈顿距离严格减小（持平不算）；
    多候选时先走 |Δ| 较大的轴，|dx| == |dy| 时先走 X 轴；无候选返回 current_facing。
    本函数不感知地图边界。
    """
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    distance = abs(dx) + abs(dy)
    candidates = []
    if dx:
        candidates.append((abs(dx), Facing.RIGHT if dx > 0 else Facing.LEFT))
    if dy:
        candidates.append((abs(dy), Facing.UP if dy > 0 else Facing.DOWN))
    # 按 |Δ| 降序排；sort 稳定，|dx| == |dy| 时保持 X 轴在前
    candidates.sort(key=lambda item: item[0], reverse=True)
    for _, facing in candidates:
        delta = facing.delta
        nxt = (pos[0] + delta[0], pos[1] + delta[1])
        if nxt in obstacles:
            continue
        gap = abs(nxt[0] - target[0]) + abs(nxt[1] - target[1])
        if gap < distance:
            return facing
    return current_facing


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """纯函数决策：返回 (action: str, new_state: SentryState)。

    hp 是绝对血量，血量百分比由 hp_ratio(hp, sensor["max_hp"]) 计算；
    heat 只接收不使用——规则表 R1-R7 中没有任何热量条款。
    契约外输入（enemy_frames 空或长度 >6、state 非 SentryState、sensor 缺字段）
    一律 raise ValueError；字段存在但取值非法则防御式规范化，不抛异常。
    """
    frames = sensor.get("enemy_frames") if isinstance(sensor, dict) else None
    if not isinstance(sensor, dict) or frames is None:
        raise ValueError("sensor 缺少 enemy_frames 字段")
    if not isinstance(frames, (tuple, list)) or not 1 <= len(frames) <= 6:
        raise ValueError("enemy_frames 必须是长度 1-6 的 tuple 或 list")
    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState 成员")
    for field in ("enemy_dist", "robot_type", "max_hp"):
        if field not in sensor:
            raise ValueError("sensor 缺少字段：" + field)
    frames = [bool(frame) for frame in frames]
    try:
        dist = int(sensor["enemy_dist"])
    except (TypeError, ValueError):
        dist = 99
    if dist < 0:
        dist = 99
    hero = sensor["robot_type"] == "HERO"
    hp_pct = hp_ratio(hp, sensor["max_hp"])
    visible = frames[-1]
    if dist <= 3:
        engage = ("SHOOT", SentryState.ENGAGE)
    elif hero:
        engage = ("MOVE_RIGHT", SentryState.ENGAGE)
    else:
        engage = ("MOVE_LEFT", SentryState.ENGAGE)
    if hp_pct <= 30:                                    # R1 保命优先
        return "RETREAT", SentryState.RETREAT
    if state is SentryState.RETREAT:                    # R2 撤退保持
        if hp_pct > 60:
            return "RETURN", SentryState.RETURN
        return "RETREAT", SentryState.RETREAT
    if state is SentryState.RETURN:                     # R3 返航单帧
        return "MOVE_BASE", SentryState.PATROL
    if state is SentryState.ENGAGE and visible:         # R4 交火决策
        return engage
    if state is SentryState.ENGAGE:                     # R5 交火保持
        if len(frames) >= 2 and frames[-2]:
            return "HOLD_FIRE", SentryState.ENGAGE
        return "SCAN", SentryState.SUSPECT
    if visible:                                         # R6 敌情确认
        if len(frames) >= 2 and frames[-2]:
            return engage
        return "SCAN", SentryState.SUSPECT
    if state is SentryState.PATROL:                     # R7 默认行为
        return "PATROL_MOVE", SentryState.PATROL
    return "SCAN", SentryState.SUSPECT


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """sense → decide → act 主循环：贪心导航 + 左手贴墙脱困 + BFS 兜底领航。

    终止条件：抵达 grid.enemy_pos / 步数用尽（max_steps）/ 电量耗尽。
    返回 {"steps", "collisions", "visited_count", "found_enemy", "success"}。
    """
    steps = 0
    wall_mode = False
    wall_steps = 0
    entry = 0
    trail = {grid.current_pos}
    left_of = {Facing.UP: Facing.LEFT, Facing.LEFT: Facing.DOWN,
               Facing.DOWN: Facing.RIGHT, Facing.RIGHT: Facing.UP}
    # 贴墙最多走这么多步；仍未脱困就交给 BFS 领航，避免绕远把步数比拖爆。
    wall_budget = 4
    # 界外一圈也视作障碍：BFS 领航需要它来封闭搜索空间（Bonus 规范第 2 条）。
    blocked = set(grid.obstacles)
    for x in range(-1, grid.width + 1):
        blocked.add((x, -1))
        blocked.add((x, grid.height))
    for y in range(-1, grid.height + 1):
        blocked.add((-1, y))
        blocked.add((grid.width, y))

    def manhattan(a, b):
        return abs(a[0]-b[0])+abs(a[1]-b[1])

    def greedy_step(pos, target, obs):
        """Q4 贪心：优先 |Δ| 较大的轴；无法缩短距离时返回 None。"""
        wanted = next_step_toward(pos, target, obs, Facing.UP)
        delta = wanted.delta
        nxt = (pos[0] + delta[0], pos[1] + delta[1])
        if nxt in obs or manhattan(nxt, target) >= manhattan(pos, target):
            return None
        return wanted

    def bfs_step(pos, target, obs):
        """脱困领航：四邻格里 BFS 距离最小者；全不通返回 None。"""
        best = None
        best_len = None
        for facing in (Facing.UP, Facing.DOWN, Facing.LEFT, Facing.RIGHT):
            delta = facing.delta
            nxt = (pos[0] + delta[0], pos[1] + delta[1])
            if nxt in obs:
                continue
            length = bfs_path_length(nxt, target, obs)
            if length >= 0 and (best_len is None or length < best_len):
                best = facing
                best_len = length
        return best

    def face_towards(wanted):
        while grid.facing != wanted:
            grid.turn_right()

    while steps < max_steps and grid.fuel > 0 and not grid.found_enemy:
        pos = grid.current_pos
        dist_now = manhattan(pos, grid.enemy_pos)
        greedy = greedy_step(pos, grid.enemy_pos, grid.obstacles)

        if greedy is None:
            if not wall_mode:
                wall_mode = True
                entry = dist_now
                wall_steps = 0
        elif wall_mode and dist_now < entry:
            wall_mode = False

        if wall_mode:
            if wall_steps >= wall_budget:
                turn = bfs_step(pos, grid.enemy_pos, blocked)
            else:
                # 左手贴墙：先试左前方，再试正前方，都不通就右转。
                # 用 is_blocked 把界外也算作墙——地图边界正是要贴的那面墙，
                # 只判 obstacles 会让机器人在开阔地绕圈，永远贴不上墙。
                left = left_of[grid.facing]
                d_left = left.delta
                cell_left = (pos[0] + d_left[0], pos[1] + d_left[1])
                d_front = grid.facing.delta
                cell_front = (pos[0] + d_front[0], pos[1] + d_front[1])
                if not grid.is_blocked(*cell_left):
                    turn = left
                elif not grid.is_blocked(*cell_front):
                    turn = grid.facing
                else:
                    grid.turn_right()
                    turn = grid.facing
        else:
            turn = greedy

        if turn is not None:
            face_towards(turn)
        grid.move_forward()
        trail.add(grid.current_pos)
        steps += 1
        if wall_mode:
            wall_steps += 1

    return {"steps": steps, "collisions": grid.collision_count,
            "visited_count": len(trail), "found_enemy": grid.found_enemy,
            "success": grid.found_enemy}


def report_to_json(stats):
    """把 stats 序列化为确定性 JSON 字符串。

    sort_keys=True 保证键序与字典插入顺序无关；ensure_ascii=False 保留中文原样。
    """
    return json.dumps(stats, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """BFS 全局最短路步数：start == target 返回 0，目标不可达返回 -1。

    obstacles 由调用方负责包含地图边界（如外圈障碍环），否则对不可达目标的
    搜索不会终止；本函数不感知地图宽高。
    """
    if start == target:
        return 0
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        cur, dist = queue.popleft()
        for delta in ((0, 1), (0, -1), (-1, 0), (1, 0)):
            nxt = (cur[0] + delta[0], cur[1] + delta[1])
            if nxt in obstacles or nxt in seen:
                continue
            if nxt == target:
                return dist + 1
            seen.add(nxt)
            queue.append((nxt, dist + 1))
    return -1


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
