<script setup>
import { computed, onMounted, ref } from 'vue'
import Task1Sailor from './views/Task1Sailor.vue'
import Task2Spread from './views/Task2Spread.vue'
import Task3Rising from './views/Task3Rising.vue'

const bundle = ref(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref('sailor')

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

const statCards = computed(() => {
  if (!bundle.value) return []
  return [
    { label: 'Nodes', value: bundle.value.meta.nodeCount.toLocaleString() },
    { label: 'Edges', value: bundle.value.meta.edgeCount.toLocaleString() },
    { label: 'Sailor Breakout', value: tasks.value.sailor?.breakoutYear ?? 'N/A' },
    { label: 'Predicted Stars', value: tasks.value.rising?.topThree.length ?? 0 },
  ]
})

const loadBundle = async () => {
  try {
    const response = await fetch('/data/analysis_bundle.json')
    if (!response.ok) {
      throw new Error(`Failed to load data (${response.status})`)
    }
    bundle.value = await response.json()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

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
      <Task1Sailor v-if="activeTab === 'sailor'" :task="tasks.sailor" />
      <Task2Spread v-else-if="activeTab === 'spread'" :task="tasks.spread" />
      <Task3Rising v-else :task="tasks.rising" :center-id="tasks.sailor?.artistId || ''" />
    </template>
  </div>
</template>
