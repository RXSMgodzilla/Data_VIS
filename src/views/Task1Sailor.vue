<script setup>
import { computed, ref, watch } from 'vue'
import ArcBeltGraph from '../components/ArcBeltGraph.vue'
import BarList from '../components/BarList.vue'
import NetworkSummary from '../components/NetworkSummary.vue'
import OrbitalGraph from '../components/OrbitalGraph.vue'
import TimelineList from '../components/TimelineList.vue'

const props = defineProps({
  task: {
    type: Object,
    required: true,
  },
})

const sailorYearMin = ref(2028)
const sailorYearMax = ref(2040)
const selectedSailorEdgeTypes = ref([])
const graphView = ref('orbit') // 'orbit' | 'arc'

const sailorEdgeTypes = computed(() => {
  const edges = props.task?.graph?.edges || []
  return [...new Set(edges.map((edge) => edge.type))].sort()
})

const sailorGraphLookup = computed(() => {
  const nodes = new Map()
  for (const node of props.task?.graph?.nodes || []) {
    nodes.set(node.id, node)
  }
  return nodes
})

const filteredSailorGraph = computed(() => {
  if (!props.task) return { nodes: [], edges: [] }

  const allowed = new Set(selectedSailorEdgeTypes.value)
  const connected = new Set([props.task.artistId])
  const edges = []

  const withinRange = (node) => {
    if (!node) return false
    if (node.nodeType === 'Song' || node.nodeType === 'Album') {
      return !node.year || (node.year >= sailorYearMin.value && node.year <= sailorYearMax.value)
    }
    return true
  }

  for (const edge of props.task.graph.edges) {
    if (!allowed.has(edge.type)) continue
    const source = sailorGraphLookup.value.get(edge.source)
    const target = sailorGraphLookup.value.get(edge.target)
    if (!withinRange(source) || !withinRange(target)) continue
    edges.push(edge)
    connected.add(edge.source)
    connected.add(edge.target)
  }

  const nodes = props.task.graph.nodes.filter((node) => connected.has(node.id))
  return { nodes, edges }
})

const filteredSailorStats = computed(() => ({
  nodes: filteredSailorGraph.value.nodes.length,
  edges: filteredSailorGraph.value.edges.length,
  collaborators: filteredSailorGraph.value.nodes.filter((node) => node.tier === 'collaborator').length,
}))

const sailorOrbitalGraph = computed(() => {
  const nodes = filteredSailorGraph.value.nodes.filter(
    (node) => node.tier !== 'work' || node.notable
  )
  return {
    nodes,
    edges: filteredSailorGraph.value.edges.filter(
      (edge) =>
        nodes.find((node) => node.id === edge.source) &&
        nodes.find((node) => node.id === edge.target)
    ),
  }
})

const sailorNetworkGroups = computed(() => [
  {
    label: 'Influenced by',
    items: (props.task?.topInfluencers || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.count} references`,
      tag: item.primaryGenre,
    })),
  },
  {
    label: 'Collaborators',
    items: (props.task?.collaborators || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.collaborations} shared works`,
      tag: item.roles.join(', '),
    })),
  },
  {
    label: 'Influenced artists',
    items: (props.task?.influencedArtists || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.directCount} direct echoes`,
      tag: item.primaryGenre,
    })),
  },
])

const sailorSummaryCards = computed(() => [
  { label: 'Visible nodes', value: filteredSailorStats.value.nodes },
  { label: 'Visible links', value: filteredSailorStats.value.edges },
  { label: 'Breakout year', value: props.task?.breakoutYear ?? 'N/A' },
  { label: 'Top collaborator', value: props.task?.collaborators?.[0]?.name ?? 'N/A' },
])

const sailorTimelineRows = computed(() => (props.task?.timeline || []).slice(-10))

const sailorInfluencerBars = computed(() => (props.task?.topInfluencers || []).slice(0, 8).map((item) => ({
  label: item.name,
  value: item.count,
  meta: item.primaryGenre,
})))

const sailorCollaboratorBars = computed(() => (props.task?.collaborators || []).slice(0, 8).map((item) => ({
  label: item.name,
  value: item.collaborations,
  meta: item.roles.join(', '),
})))

watch(
  () => props.task,
  (t) => {
    if (t) {
      sailorYearMin.value = t.yearRange[0]
      sailorYearMax.value = t.yearRange[1]
      selectedSailorEdgeTypes.value = sailorEdgeTypes.value
    }
  },
  { immediate: true }
)

watch(sailorEdgeTypes, (types) => {
  if (!selectedSailorEdgeTypes.value.length) {
    selectedSailorEdgeTypes.value = types
  }
})
</script>

<template>
  <section class="dashboard-grid">
    <aside class="panel control-panel">
      <div class="panel-header">
        <p class="eyebrow">Controls</p>
        <h3>Filter Sailor's orbit</h3>
      </div>
      <label class="control-block">
        <span>Start year</span>
        <input v-model="sailorYearMin" type="range" :min="task.yearRange[0]" :max="task.yearRange[1]" />
        <strong>{{ sailorYearMin }}</strong>
      </label>
      <label class="control-block">
        <span>End year</span>
        <input v-model="sailorYearMax" type="range" :min="task.yearRange[0]" :max="task.yearRange[1]" />
        <strong>{{ sailorYearMax }}</strong>
      </label>
      <div class="control-block">
        <span>Edge types</span>
        <div class="chip-wrap">
          <button
            v-for="edgeType in sailorEdgeTypes"
            :key="edgeType"
            class="chip"
            :class="{ selected: selectedSailorEdgeTypes.includes(edgeType) }"
            @click="
              selectedSailorEdgeTypes = selectedSailorEdgeTypes.includes(edgeType)
                ? selectedSailorEdgeTypes.filter((item) => item !== edgeType)
                : [...selectedSailorEdgeTypes, edgeType]
            "
          >
            {{ edgeType }}
          </button>
        </div>
      </div>
      <div class="bullet-card">
        <h4>Reading hint</h4>
        <p>
          Gold marks Sailor Shift, violet nodes are upstream influences, and magenta lines indicate
          stylistic or lyrical borrowing.
        </p>
      </div>
      <div class="summary-stack">
        <div v-for="stat in sailorSummaryCards" :key="stat.label" class="summary-card">
          <span>{{ stat.label }}</span>
          <strong>{{ stat.value }}</strong>
        </div>
      </div>
    </aside>

    <article class="panel graph-panel">
      <div class="panel-header" style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
        <div>
          <p class="eyebrow">Interactive Orbit</p>
          <h3>Sailor Shift's orbit at a glance</h3>
        </div>
        <div class="view-toggle">
          <button
            class="view-toggle__btn"
            :class="{ active: graphView === 'orbit' }"
            @click="graphView = 'orbit'"
          >
            Orbit
          </button>
          <button
            class="view-toggle__btn"
            :class="{ active: graphView === 'arc' }"
            @click="graphView = 'arc'"
          >
            Arc Belt
          </button>
        </div>
      </div>
      <OrbitalGraph
        v-if="graphView === 'orbit'"
        :graph-data="sailorOrbitalGraph"
        :center-id="task.artistId"
        title="Ego-network of influence and collaboration"
        subtitle="Click nodes to inspect who shaped Sailor Shift, who worked with her, and who later echoed her style."
      />
      <ArcBeltGraph
        v-else
        :graph-data="sailorOrbitalGraph"
        :center-id="task.artistId"
        :year-range="task.yearRange"
        title="Temporal arc of influence and collaboration"
        subtitle="Nodes arranged along a time arc by year. Inner ring = upstream influences, outer ring = downstream echoes."
      />
    </article>

    <article class="panel insight-panel">
      <div class="panel-header">
        <p class="eyebrow">Direct Answer</p>
        <h3>What defines Sailor's rise?</h3>
      </div>
      <ul class="fact-list">
        <li>Sailor's breakout year appears at {{ task.breakoutYear }}, when chart visibility begins to cluster.</li>
        <li>{{ task.topInfluencers[0]?.name }} and adjacent Oceanus artists appear most often as reference points.</li>
        <li>The collaboration map shows how songs, albums, and co-creators jointly scaffold her growth.</li>
      </ul>
      <div class="mini-table">
        <div v-for="artist in task.influencedArtists.slice(0, 5)" :key="artist.id" class="mini-row">
          <span>{{ artist.name }}</span>
          <strong>{{ artist.directCount }}</strong>
        </div>
      </div>
    </article>

    <article class="panel chart-panel wide">
      <div class="panel-header">
        <p class="eyebrow">Temporal View</p>
        <h3>Career output and influence received over time</h3>
      </div>
      <TimelineList
        title="Recent timeline"
        subtitle="Last 10 visible years of Sailor Shift's activity."
        :rows="sailorTimelineRows"
        :columns="[
          { key: 'works', label: 'Works' },
          { key: 'notableWorks', label: 'Notable' },
          { key: 'influenceIn', label: 'Received' },
        ]"
      />
    </article>

    <article class="panel chart-panel">
      <div class="panel-header">
        <p class="eyebrow">Upstream</p>
        <h3>Most visible influences</h3>
      </div>
      <BarList title="Top influencers" subtitle="Who shows up most often around Sailor's references." :items="sailorInfluencerBars" color="#a890ff" />
    </article>

    <article class="panel chart-panel">
      <div class="panel-header">
        <p class="eyebrow">Collaborators</p>
        <h3>Frequent creative partners</h3>
      </div>
      <BarList title="Top collaborators" subtitle="Shared works and repeated collaboration." :items="sailorCollaboratorBars" color="#74f0c0" />
    </article>
  </section>
</template>
