# VAST 2025 MC1 — Task1 数据契约与开发指南

> 本文档面向前端开发同学和后续接手的 AI 助手，说明 Task1（Sailor Shift Career Profile）的数据输出结构、字段语义、以及前后端协作边界。

---

## 一、数据输出位置

```
public/data/
├── task1.json              # Task1 独立输出（调试用）
└── analysis_bundle.json    # 全量打包输出（前端实际加载）
    └── tasks.sailor        # ← 前端读取的 Task1 数据根节点
```

前端入口：`App.vue` 通过 `fetch('/data/analysis_bundle.json')` 加载，将 `bundle.tasks.sailor` 作为 `task` prop 传入 `Task1Sailor.vue`。

---

## 二、Task1 数据根结构（`tasks.sailor`）

```typescript
interface Task1Sailor {
  artistId: string;           // Sailor Shift 的节点 ID（"17255"）
  artistName: string;         // "Sailor Shift"
  breakoutYear: number;       // 成名年份（2030），基于 notoriety_date 或首张作品年
  yearRange: [number, number];// 活跃年份区间 [2028, 2040]

  graph: EgoNetworkGraph;     // 完整的 ego-network 图数据（节点 + 边）
  timeline: TimelineEntry[];  // 年度时间线统计

  topInfluencers: Influencer[];      // 上游：谁影响了 Sailor（按引用次数排序）
  collaborators: Collaborator[];     // 合作者列表（按合作次数排序）
  influencedArtists: Influenced[];   // 下游：被 Sailor 直接影响的艺术家
  indirectOnlyArtists: Indirect[];   // 仅被间接影响的艺术家（传播路径已知）
  collaboratorDownstream: Downstream[]; // 合作者后续影响的下游（当前可能为空）
  communityInfluence: CommunityImpact[]; // Oceanus Folk 社区内的影响对象

  works: Work[];              // Sailor 的全部作品列表（按发行年排序）
}
```

---

## 三、各子结构详细说明

### 3.1 `graph` — Ego-network 图数据

保留 Sailor Shift 为中心的一跳/多跳网络，**不做后端裁剪**，前端按需筛选展示。

```typescript
interface EgoNetworkGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface GraphNode {
  id: string;           // 节点全局唯一 ID
  label: string;        // 显示名称（stage_name / name）
  nodeType: "Person" | "MusicalGroup" | "Song" | "Album";
  tier: "core" | "work" | "influencer" | "influenced" | "collaborator";
                        // core=Sailor本人, work=她的作品, influencer=影响了她的人,
                        // influenced=被她影响的人, collaborator=其他合作者
  genre: string | null; // 流派（作品有值，人常为 null）
  year: number | null;  // 发行年/相关年份
  size: number;         // 渲染大小：core=26, artist=16, work=10
  notable: boolean;     // 是否为知名作品
}

interface GraphEdge {
  id: string;           // 边唯一标识（如 "17255-17280-PerformerOf"）
  source: string;       // 源节点 ID
  target: string;       // 目标节点 ID
  type: EdgeType;       // 见下方边类型枚举
  year: number | null;  // 该关系发生的年份（合作/影响边可能为 null）
}

type EdgeType =
  | "PerformerOf" | "ComposerOf" | "LyricistOf" | "ProducerOf"  // 创作关系
  | "InStyleOf" | "InterpolatesFrom" | "CoverOf"
  | "LyricalReferenceTo" | "DirectlySamples";                    // 影响关系
```

**前端注意：**
- `tier` 是**互斥标签**，优先级：`core > work > influencer > influenced > collaborator`。如果一个艺术家同时是合作者和影响者，会被标记为 `influencer`。如需展示多角色，建议结合 `collaborators` / `influencedArtists` 列表做交叉查询。
- 影响边 ID 前缀 `in-` 表示 Sailor 的作品影响了别人（outbound），`out-` 表示别人的作品影响了 Sailor（inbound）。命名以 `influence_records()` 中 source_artist/target_artist 的语义为准。

---

### 3.2 `timeline` — 年度时间线

```typescript
interface TimelineEntry {
  year: number;         // 年份
  works: number;        // 该年发行的作品数
  notableWorks: number; // 该年发行的知名作品数
  influenceIn: number;  // 该年 Sailor 接收的影响引用次数
  influenceOut: number; // 该年 Sailor 施加的影响引用次数
}
```

**前端注意：**
- `influenceIn`/`influenceOut` 是**聚合计数**，如需展示"这一年具体是谁影响的"，需要结合 `topInfluencers[].yearlyCount` 做交叉。

---

### 3.3 `topInfluencers` — 上游影响者（谁影响了 Sailor）

按影响引用次数降序排列。

```typescript
interface Influencer {
  id: string;
  name: string;
  count: number;              // 影响引用总次数
  types: Record<EdgeType, number>; // 影响类型细分，如 { "InStyleOf": 3, "CoverOf": 1 }
  primaryGenre: string;       // 该艺术家的主要流派
  yearlyCount: Record<string, number>; // 新增：按年份的影响次数 { "2030": 1, "2034": 2 }
}
```

**前端应用场景：**
- 全局 Top N 排行 → `BarList` 组件
- 时序分析 → 用 `yearlyCount` 绘制"影响者随时间变化"的分面条形图或河流图

---

### 3.4 `collaborators` — 合作者

按合作次数降序排列，取 Top 12。

```typescript
interface Collaborator {
  id: string;
  name: string;
  roles: string[];            // 担任的角色，如 ["LyricistOf", "PerformerOf"]
  collaborations: number;     // 与 Sailor 的合作次数
  works: string[];            // 合作作品名称（最多展示 4 个）
  primaryGenre: string;       // 该艺术家的主要流派
}
```

---

### 3.5 `influencedArtists` — 被 Sailor 直接影响的艺术家

按 `directCount` 降序排列。

```typescript
interface Influenced {
  id: string;
  name: string;
  directCount: number;        // 直接影响次数
  indirectCount: number;      // 间接影响次数（二级传播计数）
  primaryGenre: string;
  types: Record<EdgeType, number>; // 影响类型细分
}
```

---

### 3.6 `indirectOnlyArtists` — 仅被间接影响的艺术家（新增）

这些艺术家**没有被 Sailor 直接影响**，但通过 Sailor → 中间人 → 该艺术家的路径受到了影响。

```typescript
interface Indirect {
  id: string;
  name: string;
  indirectCount: number;      // 间接影响路径数
  viaArtists: ViaArtist[];    // 传播路径上的中间艺术家（可能多个）
  primaryGenre: string;
}

interface ViaArtist {
  id: string;
  name: string;
}
```

**前端应用场景：**
- 展示影响传播树/路径图
- 与 `influencedArtists` 合并展示完整的 downstream 影响网络

---

### 3.7 `collaboratorDownstream` — 合作者的下游影响（新增）

分析 Sailor 的合作者后续又去影响了谁，用于回答"合作网络如何扩展了 Sailor 的间接影响"。

```typescript
interface Downstream {
  collaboratorId: string;     // 合作者 ID
  collaboratorName: string;
  influencedArtists: {
    id: string;
    name: string;
    count: number;
    primaryGenre: string;
  }[];
}
```

**当前状态：** 数据集中可能为空数组（合作者暂无下游影响记录），前端需做空值处理。

---

### 3.8 `communityInfluence` — Oceanus Folk 社区影响（新增）

专门提取被 Sailor 影响的 **Oceanus Folk 流派** 艺术家，回答 Task1 第三个问题。

```typescript
interface CommunityImpact {
  id: string;
  name: string;
  count: number;              // 影响引用次数
  isOceanus: boolean;         // 是否为 Oceanus Folk 流派（冗余校验字段）
  primaryGenre: string;       // 主要流派（应为 "Oceanus Folk"）
  year: number | null;        // 影响发生的年份
}
```

---

### 3.9 `works` — Sailor 的全部作品

按 `releaseYear` 升序排列。

```typescript
interface Work {
  id: number;                 // 注意：作品 ID 是 number 类型（与其他 string ID 不同）
  name: string;
  type: "Song" | "Album";
  genre: string;              // 通常为 "Oceanus Folk"
  releaseYear: number;
  notable: boolean;
}
```

**前端注意：** `works[].id` 是 `number` 类型，而 `graph.nodes[].id` 是 `string` 类型。做 ID 匹配时需要类型转换。

---

## 四、边类型颜色映射（前端统一规范）

```javascript
const EDGE_COLORS = {
  PerformerOf:        '#7bd4ff',
  ComposerOf:         '#74f0c0',
  LyricistOf:         '#f5c156',
  ProducerOf:         '#ff9bb0',
  InStyleOf:          '#a890ff',
  InterpolatesFrom:   '#ff7eb8',
  CoverOf:            '#ffd166',
  LyricalReferenceTo: '#9ae6b4',
  DirectlySamples:    '#ff6b6b',
  OceanusInfluence:   '#55e1ff',
};
```

---

## 五、前端开发 checklist

- [ ] `graph.nodes` / `graph.edges` 可能很大，OrbitalGraph 渲染时建议按 tier 优先级做**前端分层筛选**，不要一次性画所有节点
- [ ] `works[].id` 为 number，`graph.nodes[].id` 为 string，做匹配时统一转 string
- [ ] `collaboratorDownstream` 可能为空数组，UI 需展示"暂无数据"状态
- [ ] `yearlyCount` 中的 key 是字符串年份（如 `"2030"`），使用时需 `parseInt`
- [ ] `tier` 互斥标签如需展示"多角色"，建议用 `collaborators` 和 `influencedArtists` 的 ID 集合做交叉判断

---

## 六、后端代码关键路径

```
scripts/
├── lib/common.py           # 图数据加载、索引构建、影响关系展开（供三个 Task 共用）
│   ├── load_graph()        # 读取 MC1_graph.json
│   ├── build_indexes()     # 构建 work→artist / artist→work 等索引
│   └── influence_records() # 将作品级影响边展开为艺术家级影响记录
│
└── tasks/task1_sailor.py   # Task1 专属数据加工
    └── build_sailor_task() # 产出本文件描述的全部数据结构

scripts/merge.py            # 合并三个 Task 的输出为 analysis_bundle.json
```

---

## 七、常见问题

**Q: `influencer` 和 `influenced` 的命名容易混淆？**
A: 记住这个口诀：
- `topInfluencers` → **别人影响 Sailor**（上游， inbound）
- `influencedArtists` → **Sailor 影响别人**（下游， outbound）

**Q: 为什么 `graph.nodes` 中有 tier=`collaborator` 的作品节点？**
A: `tier` 判定优先级是 `core > work > influencer > influenced > collaborator`。如果一个作品节点没有被归类为 Sailor 的 `work`（可能因为索引漏配），会 fallback 到 `collaborator`。实际使用中建议按 `nodeType`（Song/Album/Person）做展示区分。

**Q: `indirectCount` 为什么很多是 0？**
A: 间接影响只计算了二级传播（Sailor → A → B）。数据集中很多被影响者没有继续影响他人，所以 `indirectCount` 为 0 是正常的。更深层的路径在 `indirectOnlyArtists` 中通过 `viaArtists` 展示。
