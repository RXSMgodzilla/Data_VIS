# Task 1 数据层扩充设计

**日期：** 2026-05-02  
**范围：** `Data_VIS/scripts/tasks/task1_sailor.py`  
**目标：** 补齐 VAST Challenge 2025 MC1 Task 1 三个子问题所需的数据字段

---

## 背景

Task 1 要求回答三个问题：

1. Sailor Shift 随时间推移受到了谁的影响？
2. 她与谁合作，并直接或间接影响了谁？
3. 她如何影响了更广泛 Oceanus Folk 社区的合作者？

当前 `build_sailor_task` 输出能部分回答以上问题，但存在以下缺口：
- `topInfluencers` 只有总计数，缺少时间维度
- 间接影响仅作为附加字段附在直接影响列表上，纯2跳艺术家完全丢失
- Q3 所需的合作者下游传导和社区受影响分布完全缺失
- `graph.edges` 没有 `year` 字段，前端无法做时间过滤
- 多处 `.most_common(N)` 截断导致数据不完整

---

## 决策

- **方案：** 原地扩充（在现有函数里新增字段，不动整体结构）
- **间接影响深度：** 2跳
- **数据上限：** 全量输出，移除所有 `.most_common()` 截断
- **图边年份：** 加，支持前端时间过滤

---

## 新增字段规范

### 1. `topInfluencers[i].yearlyCount`（Q1）

每个影响者新增逐年计数。

```json
{
  "id": "123",
  "name": "Artist X",
  "count": 10,
  "types": { "InStyleOf": 6, "CoverOf": 4 },
  "primaryGenre": "Oceanus Folk",
  "yearlyCount": { "2028": 3, "2033": 5, "2037": 2 }
}
```

**计算方式：** 在遍历 `influence_in[sailor_id]` 的循环里同步累计 `influencer_yearly[influencer_id][sourceYear] += 1`。

---

### 2. `indirectOnlyArtists`（Q2 间接部分）

纯2跳影响艺术家列表（不在直接影响列表里的）。

```json
[
  {
    "id": "456",
    "name": "Artist Y",
    "indirectCount": 5,
    "viaArtists": [{ "id": "789", "name": "Artist Z" }],
    "primaryGenre": "Pop"
  }
]
```

**计算方式：**
1. 在现有 `indirect_influence` 计算的同时，用 `indirect_via = defaultdict(set)` 记录 `indirect_via[downstream_artist].add(direct_artist)` 路径。
2. 过滤掉已在 `influenced_counter` 里的艺术家。
3. 按 `indirectCount` 降序全量输出。

---

### 3. `collaboratorDownstream`（Q3 合作者传导链）

每个合作者影响了哪些下游艺术家。

```json
[
  {
    "collaboratorId": "111",
    "collaboratorName": "Producer A",
    "downstream": [
      { "id": "222", "name": "Artist B", "count": 3, "year": 2033, "primaryGenre": "Indie Folk" }
    ]
  }
]
```

**计算方式：** 遍历 `collaborator_counter` 的所有键 → 查 `influence_out[collaborator_id]` → 按 `artist` 字段聚合，`year` 取该合作者对该下游艺术家所有影响记录里 `sourceYear` 的最小值（即首次影响时间），`None` 时跳过年份字段。

---

### 4. `communityInfluence`（Q3 社区受影响分布）

被 Sailor 直接影响的 Oceanus Folk 社区艺术家。

```json
[
  {
    "id": "333",
    "name": "Artist C",
    "count": 4,
    "isOceanus": true,
    "primaryGenre": "Oceanus Folk",
    "year": 2035
  }
]
```

**计算方式：** 遍历 `influence_out[sailor_id]` → 用 `artist_primary_genre` 判断目标艺术家是否为 Oceanus Folk → 聚合计数，按 count 降序全量输出。

---

### 5. `graph.edges[i].year`（时间过滤）

每条边附加年份字段。

```json
{ "id": "...", "source": "...", "target": "...", "type": "InStyleOf", "year": 2031 }
```

**取值规则：**
- 影响类边（InStyleOf / InterpolatesFrom / CoverOf / LyricalReferenceTo / DirectlySamples）：使用 influence record 里的 `sourceYear`
- 创作类边（PerformerOf / ComposerOf / LyricistOf / ProducerOf）：使用 work 节点的 `release_date`，通过现有 `parse_year` 解析

---

## 全量输出改动

移除以下截断，改为全量按计数降序：

| 字段 | 当前 | 改后 |
|---|---|---|
| `topInfluencers` | `.most_common(10)` | 全量降序 |
| `collaborators` | `.most_common(12)` | 全量降序 |
| `influencedArtists` | `.most_common(12)` | 全量降序 |
| `indirectOnlyArtists` | 无（新增） | 全量降序 |

---

## 改动文件

只改一个文件：`Data_VIS/scripts/tasks/task1_sailor.py`

改动顺序（依赖顺序）：
1. 扩充 `influence_in` 循环 → 同步计算 `influencer_yearly`
2. 扩充 `indirect_influence` 计算 → 同步计算 `indirect_via`，生成 `indirectOnlyArtists`
3. 在 `collaborators` 构建之后新增 `collaboratorDownstream` 循环
4. 新增 `communityInfluence` 循环
5. 扩充 `edge_payload` 构建 → 加 `year` 字段
6. 移除所有 `.most_common(N)` 截断

---

## 不改动的内容

- `lib/common.py`：无需改动
- `graph.nodes`：结构不变
- Task 2 / Task 3 的数据：不受影响
- 前端代码：本次只改后端，前端另行规划
