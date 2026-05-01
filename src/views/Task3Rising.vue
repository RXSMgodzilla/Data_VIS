<script setup>
import { computed, ref, watch } from 'vue'
import BarList from '../components/BarList.vue'
import OrbitalGraph from '../components/OrbitalGraph.vue'
import TimelineList from '../components/TimelineList.vue'

const props = defineProps({
  task: {
    type: Object,
    required: true,
  },
  centerId: {
    type: String,
    default: '',
  },
})

const selectedCandidateId = ref('')

const selectedCandidate = computed(() => {
  if (!props.task) return null
  return (
    props.task.candidates.find((candidate) => candidate.id === selectedCandidateId.value) ||
    props.task.candidates[0] ||
    null
  )
})

const currentPredictionNames = computed(() => {
  if (!props.task) return []
  const idSet = new Set(props.task.topThree)
  return props.task.candidates.filter((candidate) => idSet.has(candidate.id))
})

const selectedCandidateWorks = computed(() => {
  if (!selectedCandidate.value) return []
  const target = props.task?.candidates?.find((candidate) => candidate.id === selectedCandidate.value.id)
  return target?.worksPreview || []
})

const risingSummaryCards = computed(() => [
  { label: 'Top 1', value: currentPredictionNames.value[0]?.name ?? 'N/A' },
  { label: 'Top 2', value: currentPredictionNames.value[1]?.name ?? 'N/A' },
  { label: 'Top 3', value: currentPredictionNames.value[2]?.name ?? 'N/A' },
  { label: 'Selected score', value: selectedCandidate.value?.score ?? 'N/A' },
])

const risingNetworkGroups = computed(() => [
  {
    label: 'Predicted stars',
    items: currentPredictionNames.value.map((item) => ({
      name: item.name,
      meta: `Score ${item.score}`,
      tag: item.primaryGenre,
    })),
  },
  {
    label: 'Comparator artists',
    items: (props.task?.comparators || []).map((item) => ({
      name: item.name,
      meta: `${item.worksCount} works`,
      tag: item.primaryGenre,
    })),
  },
  {
    label: 'Selected works',
    items: selectedCandidateWorks.value.map((item) => ({
      name: item.name,
      meta: `${item.releaseYear ?? 'N/A'}`,
      tag: item.genre,
    })),
  },
])

const candidateScoreBars = computed(() => (props.task?.candidates || []).slice(0, 8).map((item) => ({
  label: item.name,
  value: item.score,
  meta: `${item.primaryGenre} | latest ${item.latestYear}`,
})))

const candidateMixBars = computed(() => {
  if (!selectedCandidate.value) return []
  return [
    { label: 'Oceanus focus', value: Number((selectedCandidate.value.oceanusRatio * 100).toFixed(1)) },
    { label: 'Collaboration', value: Math.min(selectedCandidate.value.collaborationDegree * 8, 100) },
    { label: 'Influence', value: Math.min(selectedCandidate.value.influenceReceived * 10, 100) },
    { label: 'Notable works', value: Math.min(selectedCandidate.value.notableCount * 18, 100) },
    { label: 'Recency', value: Math.min((selectedCandidate.value.latestYear - 2030) * 12, 100) },
  ]
})

const candidateTrajectoryRows = computed(() => {
  const rows = props.task?.trajectories || []
  return rows.map((item) => ({
    year: item.name,
    releases: item.series.reduce((sum, row) => sum + row.releases, 0),
    notable: item.series.reduce((sum, row) => sum + row.notable, 0),
    influenceReceived: item.series.reduce((sum, row) => sum + row.influenceReceived, 0),
  }))
})

const risingOrbitalGraph = computed(() => props.task?.graph || { nodes: [], edges: [] })

watch(
  () => props.task,
  (t) => {
    if (t && t.topThree?.length) {
      selectedCandidateId.value = t.topThree[0]
    }
  },
  { immediate: true }
)
</script>

<template>
  <section class="dashboard-grid">
    <aside class="panel control-panel">
      <div class="panel-header">
        <p class="eyebrow">Star Selector</p>
        <h3>Inspect a predicted candidate</h3>
      </div>
      <div class="chip-wrap vertical">
        <button
          v-for="candidate in currentPredictionNames"
          :key="candidate.id"
          class="chip large"
          :class="{ selected: selectedCandidateId === candidate.id }"
          @click="selectedCandidateId = candidate.id"
        >
          {{ candidate.name }}
        </button>
      </div>
      <div v-if="selectedCandidate" class="bullet-card">
        <h4>{{ selectedCandidate.name }}</h4>
        <p>
          {{ selectedCandidate.primaryGenre }} specialist with {{ selectedCandidate.oceanusCount }} Oceanus works
          and a score of {{ selectedCandidate.score }}.
        </p>
      </div>
      <div class="bullet-card">
        <h4>Prediction logic</h4>
        <p>{{ task.definition.summary }}</p>
      </div>
      <div class="summary-stack">
        <div v-for="stat in risingSummaryCards" :key="stat.label" class="summary-card">
          <span>{{ stat.label }}</span>
          <strong>{{ stat.value }}</strong>
        </div>
      </div>
    </aside>

    <article class="panel graph-panel">
      <div class="panel-header">
        <p class="eyebrow">Prediction Summary</p>
        <h3>Sailor anchor and next-wave candidates</h3>
      </div>
      <OrbitalGraph
        :graph-data="risingOrbitalGraph"
        :center-id="centerId"
        title="Sci-fi HUD predictor"
        subtitle="Gold anchors Sailor Shift, cyan highlights the predicted stars, and surrounding nodes show their nearest scene context."
      />
    </article>

    <article class="panel insight-panel">
      <div class="panel-header">
        <p class="eyebrow">Direct Answer</p>
        <h3>Top 3 future Oceanus stars</h3>
      </div>
      <ol class="rank-list">
        <li v-for="candidate in currentPredictionNames" :key="candidate.id">
          <strong>{{ candidate.name }}</strong>
          <span>{{ candidate.primaryGenre }} | score {{ candidate.score }}</span>
        </li>
      </ol>
      <ul class="fact-list compact">
        <li v-for="criterion in task.definition.criteria" :key="criterion">{{ criterion }}</li>
      </ul>
      <div class="mini-table">
        <div v-for="work in selectedCandidateWorks" :key="work.id" class="mini-row">
          <span>{{ work.name }}</span>
          <strong>{{ work.releaseYear ?? 'N/A' }}</strong>
        </div>
      </div>
    </article>

    <article class="panel chart-panel wide">
      <div class="panel-header">
        <p class="eyebrow">Benchmark Trajectories</p>
        <h3>Comparing Sailor Shift with the leading candidates</h3>
      </div>
      <TimelineList
        title="Comparator summary"
        subtitle="Total releases, notable works, and received influence for benchmark artists."
        :rows="candidateTrajectoryRows"
        :columns="[
          { key: 'releases', label: 'Releases' },
          { key: 'notable', label: 'Notable' },
          { key: 'influenceReceived', label: 'Influence' },
        ]"
      />
    </article>

    <article class="panel chart-panel">
      <div class="panel-header">
        <p class="eyebrow">Scoreboard</p>
        <h3>Weighted candidate ranking</h3>
      </div>
      <BarList title="Candidate scores" subtitle="Weighted prediction ranking." :items="candidateScoreBars" color="#55e1ff" />
    </article>

    <article class="panel chart-panel">
      <div class="panel-header">
        <p class="eyebrow">Candidate Mix</p>
        <h3>Selected star profile</h3>
      </div>
      <BarList title="Selected mix" subtitle="How the selected artist scores across the prediction profile." :items="candidateMixBars" color="#f5c156" :max-value="100" />
    </article>
  </section>
</template>
