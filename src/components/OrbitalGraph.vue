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
const height = 560
const cx = width / 2
const cy = height / 2

const tierStyle = {
  core: { radius: 0, color: '#f5c156', size: 20 },
  anchor: { radius: 0, color: '#f5c156', size: 20 },
  predicted: { radius: 140, color: '#55e1ff', size: 14 },
  collaborator: { radius: 170, color: '#74f0c0', size: 11 },
  influencer: { radius: 230, color: '#ff7eb8', size: 10 },
  influenced: { radius: 280, color: '#a890ff', size: 10 },
  work: { radius: 325, color: '#6074a7', size: 8 },
  community: { radius: 250, color: '#8ea3d6', size: 9 },
  oceanus: { radius: 180, color: '#55e1ff', size: 12 },
  external: { radius: 290, color: '#7f90b7', size: 9 },
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

const selectedId = ref(props.centerId)

watch(
  () => props.centerId,
  (value) => {
    selectedId.value = value
  },
  { immediate: true }
)

const curatedGraph = computed(() => {
  const nodes = props.graphData?.nodes || []
  const edges = props.graphData?.edges || []
  const centerNode = nodes.find((node) => node.id === props.centerId) || nodes[0]
  const rankWeight = {
    core: 100,
    anchor: 100,
    predicted: 90,
    oceanus: 80,
    collaborator: 70,
    influencer: 60,
    influenced: 50,
    community: 45,
    external: 35,
    work: 25,
  }

  const selectedNodes = [...nodes]
    .sort((a, b) => (rankWeight[b.tier] || 0) - (rankWeight[a.tier] || 0) || (b.size || 0) - (a.size || 0))
    .slice(0, 28)

  if (centerNode && !selectedNodes.find((node) => node.id === centerNode.id)) {
    selectedNodes.unshift(centerNode)
  }

  const selectedIds = new Set(selectedNodes.map((node) => node.id))
  const selectedEdges = edges.filter((edge) => selectedIds.has(edge.source) && selectedIds.has(edge.target)).slice(0, 40)
  return { nodes: selectedNodes, edges: selectedEdges }
})

const positionedNodes = computed(() => {
  const nodes = curatedGraph.value.nodes
  const grouped = new Map()
  for (const node of nodes) {
    const tier = node.id === props.centerId ? 'core' : node.tier
    if (!grouped.has(tier)) grouped.set(tier, [])
    grouped.get(tier).push(node)
  }

  const output = []
  for (const [tier, group] of grouped.entries()) {
    const style = tierStyle[tier] || tierStyle.community
    group.forEach((node, index) => {
      if (style.radius === 0) {
        output.push({ ...node, x: cx, y: cy, color: style.color, nodeSize: style.size })
        return
      }
      const angle = (-Math.PI / 2) + (index / Math.max(group.length, 1)) * Math.PI * 2
      output.push({
        ...node,
        x: cx + Math.cos(angle) * style.radius,
        y: cy + Math.sin(angle) * style.radius,
        color: style.color,
        nodeSize: style.size + Math.min(node.size || 0, 10) * 0.3,
      })
    })
  }
  return output
})

const nodeMap = computed(() => new Map(positionedNodes.value.map((node) => [node.id, node])))

const drawnEdges = computed(() =>
  curatedGraph.value.edges
    .map((edge) => {
      const source = nodeMap.value.get(edge.source)
      const target = nodeMap.value.get(edge.target)
      if (!source || !target) return null
      const mx = (source.x + target.x) / 2
      const my = (source.y + target.y) / 2
      const dx = target.x - source.x
      const dy = target.y - source.y
      const curve = Math.max(16, Math.min(60, Math.hypot(dx, dy) * 0.16))
      return {
        ...edge,
        path: `M ${source.x} ${source.y} Q ${mx - dy / curve} ${my + dx / curve} ${target.x} ${target.y}`,
        stroke: edgeStyle[edge.type] || '#7f90b7',
      }
    })
    .filter(Boolean)
)

const selectedNode = computed(
  () => positionedNodes.value.find((node) => node.id === selectedId.value) || positionedNodes.value[0]
)

const visibleRings = computed(() => {
  const radii = [...new Set(positionedNodes.value.map((node) => {
    const tier = node.id === props.centerId ? 'core' : node.tier
    return (tierStyle[tier] || tierStyle.community).radius
  }))].filter(Boolean)
  return radii.sort((a, b) => a - b)
})

const shouldLabel = (node) =>
  node.id === props.centerId ||
  node.id === selectedId.value ||
  ['predicted', 'oceanus', 'anchor', 'core'].includes(node.tier)
</script>

<template>
  <div class="orbital-card">
    <div class="orbital-head">
      <h4>{{ title }}</h4>
      <p>{{ subtitle }}</p>
    </div>

    <div class="orbital-stage">
      <svg class="orbital-svg" :viewBox="`0 0 ${width} ${height}`" role="img" aria-label="Orbital relationship graph">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <circle
          v-for="ring in visibleRings"
          :key="ring"
          :cx="cx"
          :cy="cy"
          :r="ring"
          fill="none"
          stroke="rgba(120, 154, 211, 0.16)"
          stroke-dasharray="4 8"
        />

        <path
          v-for="edge in drawnEdges"
          :key="edge.id"
          :d="edge.path"
          fill="none"
          :stroke="edge.stroke"
          :stroke-opacity="selectedId && (edge.source === selectedId || edge.target === selectedId) ? 0.95 : 0.32"
          :stroke-width="selectedId && (edge.source === selectedId || edge.target === selectedId) ? 2.4 : 1.2"
        />

        <g
          v-for="node in positionedNodes"
          :key="node.id"
          class="orbital-node"
          @click="selectedId = node.id"
        >
          <circle
            :cx="node.x"
            :cy="node.y"
            :r="node.id === selectedId ? node.nodeSize + 3 : node.nodeSize"
            :fill="node.color"
            :fill-opacity="node.id === selectedId ? 0.95 : 0.82"
            stroke="#dbe7ff"
            stroke-width="1.1"
            filter="url(#glow)"
          />
          <text
            v-if="shouldLabel(node)"
            :x="node.x"
            :y="node.y - node.nodeSize - 10"
            text-anchor="middle"
            fill="#eff5ff"
            font-size="11"
          >
            {{ node.label }}
          </text>
        </g>
      </svg>
    </div>

    <div v-if="selectedNode" class="orbital-detail">
      <div>
        <span class="orbital-detail__label">Selected</span>
        <strong>{{ selectedNode.label }}</strong>
      </div>
      <div>
        <span class="orbital-detail__label">Type</span>
        <strong>{{ selectedNode.nodeType }}</strong>
      </div>
      <div>
        <span class="orbital-detail__label">Tier</span>
        <strong>{{ selectedNode.tier }}</strong>
      </div>
      <div>
        <span class="orbital-detail__label">Genre</span>
        <strong>{{ selectedNode.genre || 'N/A' }}</strong>
      </div>
    </div>
  </div>
</template>
