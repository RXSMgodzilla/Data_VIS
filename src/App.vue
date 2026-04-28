<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import BarList from './components/BarList.vue'
import NetworkSummary from './components/NetworkSummary.vue'
import OrbitalGraph from './components/OrbitalGraph.vue'
import TimelineList from './components/TimelineList.vue'

const bundle = ref(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref('sailor')

const sailorYearMin = ref(2028)
const sailorYearMax = ref(2040)
const selectedSailorEdgeTypes = ref([])
const selectedCandidateId = ref('')

const tabMeta = {
  sailor: {
    eyebrow: 'Task 1',
    title: 'Sailor Shift Career Profile',
    blurb:
      'Trace how Sailor Shift absorbed influences, built collaborations, and then radiated her own style back into the wider network.',
  },
  spread: {
    eyebrow: 'Task 2',
    title: 'Oceanus Folk Influence Spread',
    blurb:
      'Measure whether Oceanus Folk expanded in bursts or through steady diffusion, then identify which genres and artists carried it outward.',
  },
  rising: {
    eyebrow: 'Task 3',
    title: 'Rising Star Predictor',
    blurb:
      'Compare benchmark trajectories and inspect the next three Oceanus Folk candidates through a weighted profile of focus, collaboration, and influence.',
  },
}

const currentMeta = computed(() => tabMeta[activeTab.value])
const tasks = computed(() => bundle.value?.tasks || {})
const sailorTask = computed(() => tasks.value.sailor)
const spreadTask = computed(() => tasks.value.spread)
const risingTask = computed(() => tasks.value.rising)

const statCards = computed(() => {
  if (!bundle.value) return []
  return [
    { label: 'Nodes', value: bundle.value.meta.nodeCount.toLocaleString() },
    { label: 'Edges', value: bundle.value.meta.edgeCount.toLocaleString() },
    { label: 'Sailor Breakout', value: sailorTask.value?.breakoutYear ?? 'N/A' },
    { label: 'Predicted Stars', value: risingTask.value?.topThree.length ?? 0 },
  ]
})

const sailorEdgeTypes = computed(() => {
  const edges = sailorTask.value?.graph?.edges || []
  return [...new Set(edges.map((edge) => edge.type))].sort()
})

const sailorGraphLookup = computed(() => {
  const nodes = new Map()
  for (const node of sailorTask.value?.graph?.nodes || []) {
    nodes.set(node.id, node)
  }
  return nodes
})

const filteredSailorGraph = computed(() => {
  if (!sailorTask.value) return { nodes: [], edges: [] }

  const allowed = new Set(selectedSailorEdgeTypes.value)
  const connected = new Set([sailorTask.value.artistId])
  const edges = []

  const withinRange = (node) => {
    if (!node) return false
    if (node.nodeType === 'Song' || node.nodeType === 'Album') {
      return !node.year || (node.year >= sailorYearMin.value && node.year <= sailorYearMax.value)
    }
    return true
  }

  for (const edge of sailorTask.value.graph.edges) {
    if (!allowed.has(edge.type)) continue
    const source = sailorGraphLookup.value.get(edge.source)
    const target = sailorGraphLookup.value.get(edge.target)
    if (!withinRange(source) || !withinRange(target)) continue
    edges.push(edge)
    connected.add(edge.source)
    connected.add(edge.target)
  }

  const nodes = sailorTask.value.graph.nodes.filter((node) => connected.has(node.id))
  return { nodes, edges }
})

const selectedCandidate = computed(() => {
  if (!risingTask.value) return null
  return (
    risingTask.value.candidates.find((candidate) => candidate.id === selectedCandidateId.value) ||
    risingTask.value.candidates[0] ||
    null
  )
})

const filteredSailorStats = computed(() => ({
  nodes: filteredSailorGraph.value.nodes.length,
  edges: filteredSailorGraph.value.edges.length,
  collaborators: filteredSailorGraph.value.nodes.filter((node) => node.tier === 'collaborator').length,
}))

const currentPredictionNames = computed(() => {
  if (!risingTask.value) return []
  const idSet = new Set(risingTask.value.topThree)
  return risingTask.value.candidates.filter((candidate) => idSet.has(candidate.id))
})

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

const risingOrbitalGraph = computed(() => risingTask.value?.graph || { nodes: [], edges: [] })

const sailorNetworkGroups = computed(() => [
  {
    label: 'Influenced by',
    items: (sailorTask.value?.topInfluencers || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.count} references`,
      tag: item.primaryGenre,
    })),
  },
  {
    label: 'Collaborators',
    items: (sailorTask.value?.collaborators || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.collaborations} shared works`,
      tag: item.roles.join(', '),
    })),
  },
  {
    label: 'Influenced artists',
    items: (sailorTask.value?.influencedArtists || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.directCount} direct echoes`,
      tag: item.primaryGenre,
    })),
  },
])

const spreadNetworkGroups = computed(() => [
  {
    label: 'Top influenced genres',
    items: (spreadTask.value?.topGenres || []).slice(0, 6).map((item) => ({
      name: item.genre,
      meta: `${item.count} borrowed works`,
      tag: 'Genre',
    })),
  },
  {
    label: 'Top influenced artists',
    items: (spreadTask.value?.topArtists || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.count} Oceanus links`,
      tag: item.primaryGenre,
    })),
  },
  {
    label: 'After Sailor breakout',
    items: (spreadTask.value?.inspirationShift?.after || []).slice(0, 6).map((item) => ({
      name: item.genre,
      meta: `${item.count} inspirations`,
      tag: 'Post-breakout',
    })),
  },
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
    items: (risingTask.value?.comparators || []).map((item) => ({
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

const selectedCandidateWorks = computed(() => {
  if (!selectedCandidate.value) return []
  const target = risingTask.value?.candidates?.find((candidate) => candidate.id === selectedCandidate.value.id)
  return target?.worksPreview || []
})

const sailorSummaryCards = computed(() => [
  { label: 'Visible nodes', value: filteredSailorStats.value.nodes },
  { label: 'Visible links', value: filteredSailorStats.value.edges },
  { label: 'Breakout year', value: sailorTask.value?.breakoutYear ?? 'N/A' },
  { label: 'Top collaborator', value: sailorTask.value?.collaborators?.[0]?.name ?? 'N/A' },
])

const spreadSummaryCards = computed(() => [
  { label: 'Spread years', value: spreadTask.value?.yearlySpread?.length ?? 0 },
  { label: 'Top genre', value: spreadTask.value?.topGenres?.[0]?.genre ?? 'N/A' },
  { label: 'Top artist', value: spreadTask.value?.topArtists?.[0]?.name ?? 'N/A' },
  { label: 'Breakout split', value: spreadTask.value?.inspirationShift?.breakoutYear ?? 'N/A' },
])

const risingSummaryCards = computed(() => [
  { label: 'Top 1', value: currentPredictionNames.value[0]?.name ?? 'N/A' },
  { label: 'Top 2', value: currentPredictionNames.value[1]?.name ?? 'N/A' },
  { label: 'Top 3', value: currentPredictionNames.value[2]?.name ?? 'N/A' },
  { label: 'Selected score', value: selectedCandidate.value?.score ?? 'N/A' },
])

const sailorTimelineRows = computed(() => (sailorTask.value?.timeline || []).slice(-10))
const spreadTimelineRows = computed(() => (spreadTask.value?.yearlySpread || []).slice(-10))
const sailorInfluencerBars = computed(() => (sailorTask.value?.topInfluencers || []).slice(0, 8).map((item) => ({
  label: item.name,
  value: item.count,
  meta: item.primaryGenre,
})))
const sailorCollaboratorBars = computed(() => (sailorTask.value?.collaborators || []).slice(0, 8).map((item) => ({
  label: item.name,
  value: item.collaborations,
  meta: item.roles.join(', '),
})))
const spreadGenreBars = computed(() => (spreadTask.value?.topGenres || []).slice(0, 8).map((item) => ({
  label: item.genre,
  value: item.count,
})))
const spreadArtistBars = computed(() => (spreadTask.value?.topArtists || []).slice(0, 8).map((item) => ({
  label: item.name,
  value: item.count,
  meta: item.primaryGenre,
})))
const spreadAfterBars = computed(() => (spreadTask.value?.inspirationShift?.after || []).slice(0, 8).map((item) => ({
  label: item.genre,
  value: item.count,
  meta: 'Post-breakout inspiration',
})))
const candidateScoreBars = computed(() => (risingTask.value?.candidates || []).slice(0, 8).map((item) => ({
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
  const rows = risingTask.value?.trajectories || []
  return rows.map((item) => ({
    year: item.name,
    releases: item.series.reduce((sum, row) => sum + row.releases, 0),
    notable: item.series.reduce((sum, row) => sum + row.notable, 0),
    influenceReceived: item.series.reduce((sum, row) => sum + row.influenceReceived, 0),
  }))
})

const loadBundle = async () => {
  try {
    const response = await fetch('/data/analysis_bundle.json')
    if (!response.ok) {
      throw new Error(`Failed to load data (${response.status})`)
    }
    bundle.value = await response.json()
    sailorYearMin.value = bundle.value.tasks.sailor.yearRange[0]
    sailorYearMax.value = bundle.value.tasks.sailor.yearRange[1]
    selectedSailorEdgeTypes.value = sailorEdgeTypes.value
    selectedCandidateId.value = bundle.value.tasks.rising.topThree[0]
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

watch(sailorEdgeTypes, (types) => {
  if (!selectedSailorEdgeTypes.value.length) {
    selectedSailorEdgeTypes.value = types
  }
})

onMounted(loadBundle)
</script>

<template>
  <div class="app-shell">
    <header class="hero-panel">
      <div class="hero-copy">
        <p class="eyebrow">VAST Challenge 2025 MC1</p>
        <h1>Oceanus Folk Intelligence Deck</h1>
        <p class="hero-text">
          A three-part interactive dashboard built from the MC1 knowledge graph to answer the official
          prompt with network analysis, temporal patterns, and star prediction.
        </p>
      </div>
      <div class="hero-stats">
        <div v-for="stat in statCards" :key="stat.label" class="stat-card">
          <span class="stat-label">{{ stat.label }}</span>
          <strong class="stat-value">{{ stat.value }}</strong>
        </div>
      </div>
    </header>

    <nav class="tab-strip">
      <button
        v-for="(meta, key) in tabMeta"
        :key="key"
        class="tab-button"
        :class="{ active: activeTab === key }"
        @click="activeTab = key"
      >
        <span>{{ meta.eyebrow }}</span>
        <strong>{{ meta.title }}</strong>
      </button>
    </nav>

    <section class="section-header">
      <div>
        <p class="eyebrow">{{ currentMeta.eyebrow }}</p>
        <h2>{{ currentMeta.title }}</h2>
      </div>
      <p class="section-text">{{ currentMeta.blurb }}</p>
    </section>

    <div v-if="loading" class="status-panel">Loading processed graph views…</div>
    <div v-else-if="error" class="status-panel error">{{ error }}</div>

    <template v-else>
      <section v-if="activeTab === 'sailor'" class="dashboard-grid">
        <aside class="panel control-panel">
          <div class="panel-header">
            <p class="eyebrow">Controls</p>
            <h3>Filter Sailor's orbit</h3>
          </div>
          <label class="control-block">
            <span>Start year</span>
            <input v-model="sailorYearMin" type="range" :min="sailorTask.yearRange[0]" :max="sailorTask.yearRange[1]" />
            <strong>{{ sailorYearMin }}</strong>
          </label>
          <label class="control-block">
            <span>End year</span>
            <input v-model="sailorYearMax" type="range" :min="sailorTask.yearRange[0]" :max="sailorTask.yearRange[1]" />
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
          <div class="panel-header">
            <p class="eyebrow">Interactive Orbit</p>
            <h3>Sailor Shift's orbit at a glance</h3>
          </div>
          <OrbitalGraph
            :graph-data="sailorOrbitalGraph"
            :center-id="sailorTask.artistId"
            title="Ego-network of influence and collaboration"
            subtitle="Click nodes to inspect who shaped Sailor Shift, who worked with her, and who later echoed her style."
          />
        </article>

        <article class="panel insight-panel">
          <div class="panel-header">
            <p class="eyebrow">Direct Answer</p>
            <h3>What defines Sailor's rise?</h3>
          </div>
          <ul class="fact-list">
            <li>Sailor's breakout year appears at {{ sailorTask.breakoutYear }}, when chart visibility begins to cluster.</li>
            <li>{{ sailorTask.topInfluencers[0]?.name }} and adjacent Oceanus artists appear most often as reference points.</li>
            <li>The collaboration map shows how songs, albums, and co-creators jointly scaffold her growth.</li>
          </ul>
          <div class="mini-table">
            <div v-for="artist in sailorTask.influencedArtists.slice(0, 5)" :key="artist.id" class="mini-row">
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

      <section v-else-if="activeTab === 'spread'" class="dashboard-grid">
        <aside class="panel control-panel">
          <div class="panel-header">
            <p class="eyebrow">Quick Read</p>
            <h3>Oceanus diffusion summary</h3>
          </div>
          <div class="summary-stack">
            <div v-for="stat in spreadSummaryCards" :key="stat.label" class="summary-card">
              <span>{{ stat.label }}</span>
              <strong>{{ stat.value }}</strong>
            </div>
          </div>
          <div class="bullet-card">
            <h4>How to read this page</h4>
            <p>
              Start with the time trend, then confirm which genres and artists carry the strongest Oceanus
              echoes, and finally compare inspiration before and after Sailor Shift's rise.
            </p>
          </div>
        </aside>

        <article class="panel graph-panel">
          <div class="panel-header">
            <p class="eyebrow">Diffusion Summary</p>
            <h3>Oceanus Folk to the broader music world</h3>
          </div>
          <NetworkSummary
            title="Spread pathways"
            subtitle="This page now emphasizes the strongest influenced genres, artists, and post-breakout inspiration sources."
            :groups="spreadNetworkGroups"
          />
        </article>

        <article class="panel insight-panel">
          <div class="panel-header">
            <p class="eyebrow">Direct Answer</p>
            <h3>How did the genre spread?</h3>
          </div>
          <ul class="fact-list">
            <li>The yearly trend line lets you judge whether influence rises steadily or through isolated bursts.</li>
            <li>Top genres expose where Oceanus Folk was most often borrowed, sampled, or echoed.</li>
            <li>The before/after chart compares Oceanus Folk's own inspirations around Sailor Shift's breakout.</li>
          </ul>
          <div class="bullet-card">
            <h4>Breakout threshold</h4>
            <p>Post-{{ spreadTask.inspirationShift.breakoutYear }} Oceanus works are treated as the Sailor era.</p>
          </div>
        </article>

        <article class="panel chart-panel wide">
          <div class="panel-header">
            <p class="eyebrow">Temporal Diffusion</p>
            <h3>Borrowing patterns across years</h3>
          </div>
          <TimelineList
            title="Recent spread timeline"
            subtitle="Last 10 years of Oceanus diffusion activity."
            :rows="spreadTimelineRows"
            :columns="[
              { key: 'influencedWorks', label: 'Influenced' },
              { key: 'directSamples', label: 'Samples' },
              { key: 'styleBorrowing', label: 'Style' },
            ]"
          />
        </article>

        <article class="panel chart-panel">
          <div class="panel-header">
            <p class="eyebrow">Genres</p>
            <h3>Most influenced genres</h3>
          </div>
          <BarList title="Top genres" subtitle="Genres most affected by Oceanus Folk." :items="spreadGenreBars" color="#f5c156" />
        </article>

        <article class="panel chart-panel">
          <div class="panel-header">
            <p class="eyebrow">Artists</p>
            <h3>Most influenced artists</h3>
          </div>
          <BarList title="Top artists" subtitle="Artists with the strongest Oceanus links." :items="spreadArtistBars" color="#55e1ff" />
        </article>

        <article class="panel chart-panel wide">
          <div class="panel-header">
            <p class="eyebrow">Genre Intake</p>
            <h3>What Oceanus Folk drew from before and after Sailor Shift</h3>
          </div>
          <BarList title="Post-breakout inspirations" subtitle="Genres feeding Oceanus Folk after Sailor's rise." :items="spreadAfterBars" color="#ff7eb8" />
        </article>
      </section>

      <section v-else class="dashboard-grid">
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
            <p>{{ risingTask.definition.summary }}</p>
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
            :center-id="sailorTask.artistId"
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
            <li v-for="criterion in risingTask.definition.criteria" :key="criterion">{{ criterion }}</li>
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
  </div>
</template>
