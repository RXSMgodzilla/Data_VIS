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
  groups: {
    type: Array,
    default: () => [],
  },
})
</script>

<template>
  <div class="network-summary">
    <div class="network-summary__head">
      <h4>{{ title }}</h4>
      <p>{{ subtitle }}</p>
    </div>
    <div class="network-summary__grid">
      <section v-for="group in groups" :key="group.label" class="network-group">
        <div class="network-group__label">{{ group.label }}</div>
        <div class="network-group__items">
          <article v-for="item in group.items" :key="item.name" class="network-node-card">
            <div class="network-node-card__title">{{ item.name }}</div>
            <div v-if="item.meta" class="network-node-card__meta">{{ item.meta }}</div>
            <div v-if="item.tag" class="network-node-card__tag">{{ item.tag }}</div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>
