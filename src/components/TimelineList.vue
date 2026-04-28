<script setup>
const props = defineProps({
  title: {
    type: String,
    default: '',
  },
  subtitle: {
    type: String,
    default: '',
  },
  rows: {
    type: Array,
    default: () => [],
  },
  columns: {
    type: Array,
    default: () => [],
  },
})
</script>

<template>
  <div class="viz-card">
    <div class="viz-head">
      <h4>{{ title }}</h4>
      <p>{{ subtitle }}</p>
    </div>
    <div class="timeline-table">
      <div class="timeline-table__header">
        <span>Year</span>
        <span v-for="column in columns" :key="column.key">{{ column.label }}</span>
      </div>
      <div v-for="row in rows" :key="row.year" class="timeline-table__row">
        <span class="timeline-year">{{ row.year }}</span>
        <span v-for="column in columns" :key="column.key">{{ row[column.key] }}</span>
      </div>
    </div>
  </div>
</template>
