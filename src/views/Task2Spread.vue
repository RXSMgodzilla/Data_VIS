<script setup>
import { computed } from 'vue'
import BarList from '../components/BarList.vue'
import NetworkSummary from '../components/NetworkSummary.vue'
import TimelineList from '../components/TimelineList.vue'

const props = defineProps({
  task: {
    type: Object,
    required: true,
  },
})

const spreadSummaryCards = computed(() => [
  { label: 'Spread years', value: props.task?.yearlySpread?.length ?? 0 },
  { label: 'Top genre', value: props.task?.topGenres?.[0]?.genre ?? 'N/A' },
  { label: 'Top artist', value: props.task?.topArtists?.[0]?.name ?? 'N/A' },
  { label: 'Breakout split', value: props.task?.inspirationShift?.breakoutYear ?? 'N/A' },
])

const spreadNetworkGroups = computed(() => [
  {
    label: 'Top influenced genres',
    items: (props.task?.topGenres || []).slice(0, 6).map((item) => ({
      name: item.genre,
      meta: `${item.count} borrowed works`,
      tag: 'Genre',
    })),
  },
  {
    label: 'Top influenced artists',
    items: (props.task?.topArtists || []).slice(0, 6).map((item) => ({
      name: item.name,
      meta: `${item.count} Oceanus links`,
      tag: item.primaryGenre,
    })),
  },
  {
    label: 'After Sailor breakout',
    items: (props.task?.inspirationShift?.after || []).slice(0, 6).map((item) => ({
      name: item.genre,
      meta: `${item.count} inspirations`,
      tag: 'Post-breakout',
    })),
  },
])

const spreadTimelineRows = computed(() => (props.task?.yearlySpread || []).slice(-10))

const spreadGenreBars = computed(() => (props.task?.topGenres || []).slice(0, 8).map((item) => ({
  label: item.genre,
  value: item.count,
})))

const spreadArtistBars = computed(() => (props.task?.topArtists || []).slice(0, 8).map((item) => ({
  label: item.name,
  value: item.count,
  meta: item.primaryGenre,
})))

const spreadAfterBars = computed(() => (props.task?.inspirationShift?.after || []).slice(0, 8).map((item) => ({
  label: item.genre,
  value: item.count,
  meta: 'Post-breakout inspiration',
})))
</script>

<template>
  <section class="dashboard-grid">
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
        <p>Post-{{ task.inspirationShift.breakoutYear }} Oceanus works are treated as the Sailor era.</p>
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
</template>
