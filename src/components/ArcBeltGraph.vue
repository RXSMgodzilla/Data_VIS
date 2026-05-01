<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  graphData: {
    type: Object,
    required: true,
  },
  centerId: {
    type: String,
    default: '',
  },
  yearRange: {
    type: Array,
    default: () => [2028, 2040],
  },
  title: {
    type: String,
    default: '',
  },
  subtitle: {
    type: String,
    default: '',
  },
})

const width = 920
const height = 520

const arcCx = width / 2
const arcCy = -40
const arcRadius = 420
const startAngle = (Math.PI * 30) / 180
const endAngle = (Math.PI * 150) / 180

const tierStyle = {
  core: { offset: -10, color: '#f5c156', size: 14, label: true },
  anchor: { offset: -10, color: '#f5c156', size: 14, label: true },
  influencer: { offset: -38, color: '#ff7eb8', size: 9, label: false },
  collaborator: { offset: 18, color: '#74f0c0', size: 10, label: false },
  influenced: { offset: 38, color: '#a890ff', size: 9, label: false },
  work: { offset: 56, color: '#6074a7', size: 6, label: false },
  community: { offset: 28, color: '#8ea3d6', size: 8, label: false },
  oceanus: { offset: 22, color: '#55e1ff', size: 11, label: false },
  external: { offset: 44, color: '#7f90b7', size: 8, label: false },
}

const edgeStyle = {
  PerformerOf: '#7bd4ff',
  ComposerOf: '#74f0c0',
  LyricistOf: '#f5c156',
  ProducerOf: '#ff9bb0',
  InStyleOf: '#a890ff',
  InterpolatesFrom: '#ff7eb8',
  CoverOf: '#ffd166',
  LyricalReferenceTo: '#9ae6b4',
  DirectlySamples: '#ff6b6b',
  OceanusInfluence: '#55e1ff',
}

const hoveredId = ref(null)
const selectedId = ref(props.centerId)

watch(
  () => props.centerId,
  (value) => {
    selectedId.value = value
  },
  { immediate: true }
)

const minYear = computed(() => props.yearRange[0] || 2028)
const maxYear = computed(() => props.yearRange[1] || 2040)

const yearSpan = computed(() => Math.max(maxYear.value - minYear.value, 1))

const angleForYear = (year) => {
  const t = (year - minYear.value) / yearSpan.value
  return startAngle + t * (endAngle - startAngle)
}

const arcPoint = (angle, radius) => ({
  x: arcCx + radius * Math.cos(angle),
  y: arcCy + radius * Math.sin(angle),
})

const arcPath = computed(() => {
  const p1 = arcPoint(startAngle, arcRadius)
  const p2 = arcPoint(endAngle, arcRadius)
  return `M ${p1.x} ${p1.y} A ${arcRadius} ${arcRadius} 0 0 1 ${p2.x} ${p2.y}`
})

const yearTicks = computed(() => {
  const ticks = []
  const step = yearSpan.value <= 12 ? 1 : 2
  for (let y = minYear.value; y <= maxYear.value; y += step) {
    const angle = angleForYear(y)
    const p = arcPoint(angle, arcRadius)
    const pOut = arcPoint(angle, arcRadius + 14)
    const labelPos = arcPoint(angle, arcRadius + 30)
    ticks.push({
      year: y,
      x1: p.x,
      y1: p.y,
      x2: pOut.x,
      y2: pOut.y,
      labelX: labelPos.x,
      labelY: labelPos.y,
    })
  }
  return ticks
})

const inferNodeYear = (node, edges) => {
  if (node.year) return node.year
  const related = edges.filter((e) => e.source === node.id || e.target === node.id)
  const years = related.map((e) => e.year).filter(Boolean)
  if (years.length) return Math.round(years.reduce((a, b) => a + b, 0) / years.length)
  return Math.round((minYear.value + maxYear.value) / 2)
}

const positionedNodes = computed(() => {
  const nodes = props.graphData?.nodes || []
  const edges = props.graphData?.edges || []

  const nodeYears = new Map()
  for (const node of nodes) {
    nodeYears.set(node.id, inferNodeYear(node, edges))
  }

  const byYear = new Map()
  for (const node of nodes) {
    const y = nodeYears.get(node.id)
    if (!byYear.has(y)) byYear.set(y, [])
    byYear.get(y).push(node)
  }

  const output = []
  for (const [year, group] of byYear.entries()) {
    const baseAngle = angleForYear(year)
    const sorted = [...group].sort((a, b) => {
      const rankA = tierStyle[a.tier]?.offset ?? 0
      const rankB = tierStyle[b.tier]?.offset ?? 0
      return rankA - rankB
    })

    const count = sorted.length
    const spread = count > 1 ? (4 * Math.PI) / 180 : 0
    const start = baseAngle - spread / 2

    sorted.forEach((node, index) => {
      const tier = node.id === props.centerId ? 'core' : node.tier
      const style = tierStyle[tier] || tierStyle.community
      const angle = count > 1 ? start + (index / (count - 1)) * spread : baseAngle
      const r = arcRadius + style.offset
      const pos = arcPoint(angle, r)

      output.push({
        ...node,
        x: pos.x,
        y: pos.y,
        baseAngle: angle,
        color: style.color,
        nodeSize: style.size + Math.min(node.size || 0, 10) * 0.25,
        label: style.label || node.id === selectedId.value || node.id === hoveredId.value,
        year: nodeYears.get(node.id),
      })
    })
  }
  return output
})

const nodeMap = computed(() => new Map(positionedNodes.value.map((n) => [n.id, n])))

const drawnEdges = computed(() => {
  const edges = props.graphData?.edges || []
  const ids = new Set(positionedNodes.value.map((n) => n.id))
  return edges
    .filter((e) => ids.has(e.source) && ids.has(e.target))
    .map((edge) => {
      const source = nodeMap.value.get(edge.source)
      const target = nodeMap.value.get(edge.target)
      if (!source || !target) return null

      const mx = (source.x + target.x) / 2
      const my = (source.y + target.y) / 2
      const dx = target.x - source.x
      const dy = target.y - source.y
      const dist = Math.hypot(dx, dy)
      const curve = Math.max(18, Math.min(70, dist * 0.18))

      const isActive =
        hoveredId.value && (edge.source === hoveredId.value || edge.target === hoveredId.value)
      const isSelected =
        selectedId.value && (edge.source === selectedId.value || edge.target === selectedId.value)

      return {
        ...edge,
        path: `M ${source.x} ${source.y} Q ${mx - dy / curve} ${my + dx / curve} ${target.x} ${target.y}`,
        stroke: edgeStyle[edge.type] || '#7f90b7',
        opacity: isActive || isSelected ? 0.92 : 0.22,
        width: isActive || isSelected ? 2.2 : 1,
      }
    })
    .filter(Boolean)
})

const selectedNode = computed(() => nodeMap.value.get(selectedId.value))

const shouldShowLabel = (node) =>
  node.id === props.centerId ||
  node.id === selectedId.value ||
  node.id === hoveredId.value ||
  ['core', 'anchor'].includes(node.tier)
</script>

<template>
  <div class="arc-belt-card">
    <div class="arc-belt-head">
      <h4>{{ title }}</h4>
      <p>{{ subtitle }}</p>
    </div>

    <div class="arc-belt-stage">
      <svg class="arc-belt-svg" :viewBox="`0 0 ${width} ${height}`" role="img" aria-label="Arc timeline graph">
        <defs>
          <filter id="belt-glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <path
          :d="arcPath"
          fill="none"
          stroke="rgba(120, 154, 211, 0.35)"
          stroke-width="1.5"
          stroke-linecap="round"
        />

        <g v-for="tick in yearTicks" :key="tick.year">
          <line
            :x1="tick.x1"
            :y1="tick.y1"
            :x2="tick.x2"
            :y2="tick.y2"
            stroke="rgba(120, 154, 211, 0.45)"
            stroke-width="1"
          />
          <text
            :x="tick.labelX"
            :y="tick.labelY"
            text-anchor="middle"
            dominant-baseline="middle"
            fill="#8ea3d6"
            font-size="11"
            font-weight="500"
          >
            {{ tick.year }}
          </text>
        </g>

        <path
          v-for="edge in drawnEdges"
          :key="edge.id"
          :d="edge.path"
          fill="none"
          :stroke="edge.stroke"
          :stroke-opacity="edge.opacity"
          :stroke-width="edge.width"
          stroke-linecap="round"
        />

        <g
          v-for="node in positionedNodes"
          :key="node.id"
          class="arc-belt-node"
          @mouseenter="hoveredId = node.id"
          @mouseleave="hoveredId = null"
          @click="selectedId = node.id"
        >
          <circle
            :cx="node.x"
            :cy="node.y"
            :r="node.id === selectedId ? node.nodeSize + 3 : node.nodeSize"
            :fill="node.color"
            :fill-opacity="node.id === selectedId || node.id === hoveredId ? 0.95 : 0.75"
            stroke="#dbe7ff"
            :stroke-width="node.id === selectedId ? 2 : 1"
            filter="url(#belt-glow)"
          />
          <text
            v-if="shouldShowLabel(node)"
            :x="node.x"
            :y="node.y - node.nodeSize - 9"
            text-anchor="middle"
            fill="#eff5ff"
            font-size="10.5"
            font-weight="500"
          >
            {{ node.label }}
          </text>
        </g>
      </svg>
    </div>

    <div v-if="selectedNode" class="arc-belt-detail">
      <div>
        <span class="arc-belt-detail__label">Selected</span>
        <strong>{{ selectedNode.label }}</strong>
      </div>
      <div>
        <span class="arc-belt-detail__label">Type</span>
        <strong>{{ selectedNode.nodeType }}</strong>
      </div>
      <div>
        <span class="arc-belt-detail__label">Tier</span>
        <strong>{{ selectedNode.tier }}</strong>
      </div>
      <div>
        <span class="arc-belt-detail__label">Year</span>
        <strong>{{ selectedNode.year || 'N/A' }}</strong>
      </div>
    </div>
  </div>
</template>
