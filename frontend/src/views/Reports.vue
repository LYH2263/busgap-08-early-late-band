<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const loading = ref(false)
async function run() {
  loading.value = true
  try {
    events.value = (await api('/reports/run?line_id=1', { method: 'POST' })).events || []
  } finally { loading.value = false }
}
onMounted(async () => {
  trips.value = await api('/trips')
  await run()
})
const deviations = computed(() => events.value.filter(e => e.kind === 'deviation'))
const pairs = computed(() => events.value.filter(e => e.kind !== 'deviation'))
const counts = computed(() => ({
  deviation: deviations.value.length,
  bunching: pairs.value.filter(e => e.status === 'bunching').length,
  large_gap: pairs.value.filter(e => e.status === 'large_gap').length,
}))
function pairClass(s: string) {
  return s === 'bunching' ? 'bg-bunch' : s === 'large_gap' ? 'bg-large' : ''
}
function pairLabel(s: string) {
  return s === 'bunching' ? '串车' : s === 'large_gap' ? '大间隔' : '正常'
}
function devLabel(e: any) {
  return e.direction === 'early' ? '偏离 · 早到' : '偏离 · 晚到'
}
function signed(v: number) {
  return (v > 0 ? '+' : '') + Number(v).toFixed(1)
}
</script>
<template>
  <h1>串车报告</h1>
  <p class="sub">先按早到 / 晚到带宽标偏离（不参与配对），带宽内班次再按实际到站间隔两两判定</p>
  <div class="report-actions">
    <button class="btn" :disabled="loading" @click="run">重新检测</button>
    <span class="report-count"><span class="badge badge-dev">偏离 {{ counts.deviation }}</span></span>
    <span class="report-count"><span class="badge badge-bad">串车 {{ counts.bunching }}</span></span>
    <span class="report-count"><span class="badge badge-warn">大间隔 {{ counts.large_gap }}</span></span>
  </div>

  <section v-if="deviations.length">
    <h2 class="report-h2">偏离班次（相对计划发车 + 沿途计划走行）</h2>
    <div class="bg-strip-col">
      <article v-for="(e, i) in deviations" :key="'d' + i" class="bg-gap-strip bg-dev">
        <header>{{ e.stop_name }}</header>
        <div class="bg-gap-body">
          <div class="bg-gap-val">{{ signed(e.deviation_min) }}′</div>
          <div>{{ e.earlier_trip }}</div>
          <div>计划到站 {{ e.scheduled_arrive.slice(11, 16) }}</div>
          <span class="badge" :class="e.direction === 'early' ? 'badge-bad' : 'badge-warn'">{{ devLabel(e) }}</span>
          <p class="strip-suggest">{{ e.suggestion }}</p>
        </div>
      </article>
    </div>
  </section>

  <section>
    <h2 class="report-h2">邻班间隔配对（仅带宽内班次）</h2>
    <div class="bg-split">
      <aside class="bg-trip-col">
        <h2>关联班次</h2>
        <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
          <div>
            <div>{{ r.trip_no }}</div>
            <div class="bg-trip-meta">{{ r.vehicle_no }}</div>
          </div>
          <div class="bg-trip-meta">{{ r.planned_depart }}</div>
        </div>
      </aside>
      <div class="bg-strip-col">
        <article
          v-for="(e, i) in pairs"
          :key="i"
          class="bg-gap-strip"
          :class="pairClass(e.status)"
        >
          <header>{{ e.stop_name }}</header>
          <div class="bg-gap-body">
            <div class="bg-gap-val">{{ e.gap_min }}′</div>
            <div>计划 {{ e.planned_headway_min }}′</div>
            <div>{{ e.earlier_trip }} → {{ e.later_trip }}</div>
            <span class="badge" :class="e.status === 'bunching' ? 'badge-bad' : e.status === 'large_gap' ? 'badge-warn' : 'badge-ok'">
              {{ pairLabel(e.status) }}
            </span>
          </div>
        </article>
        <p v-if="!pairs.length" class="muted">该范围无带宽内班次配对。</p>
      </div>
    </div>
  </section>
</template>
