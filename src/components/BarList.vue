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
  items: {
    type: Array,
    default: () => [],
  },
  color: {
    type: String,
    default: '#55e1ff',
  },
  maxValue: {
    type: Number,
    default: 0,
  },
})

const getWidth = (value) => {
  const max = props.maxValue || Math.max(...props.items.map((item) => item.value), 1)
  return `${Math.max(8, (value / max) * 100)}%`
}
</script>

<template>
  <div class="viz-card">
    <div class="viz-head">
      <h4>{{ title }}</h4>
      <p>{{ subtitle }}</p>
    </div>
    <div class="bar-list">
      <div v-for="item in items" :key="item.label" class="bar-row">
        <div class="bar-row__top">
          <span class="bar-row__label">{{ item.label }}</span>
          <strong class="bar-row__value">{{ item.value }}</strong>
        </div>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: getWidth(item.value), background: color }"></div>
        </div>
        <div v-if="item.meta" class="bar-row__meta">{{ item.meta }}</div>
      </div>
    </div>
  </div>
</template>
