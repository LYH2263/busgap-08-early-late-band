<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const tips = ref<any[]>([])
onMounted(async () => { tips.value = (await api('/reports/suggestions?line_id=1')).suggestions })
function isDev(t: any) { return t.kind === 'deviation' }
function statusLabel(t: any) {
  if (isDev(t)) return t.direction === 'early' ? '偏离 · 早到' : '偏离 · 晚到'
  return t.status === 'bunching' ? '串车' : '大间隔'
}
function statusBadge(t: any) {
  if (isDev(t)) return t.direction === 'early' ? 'badge-bad' : 'badge-warn'
  return t.status === 'bunching' ? 'badge-bad' : 'badge-warn'
}
function signed(v: number) {
  return (v > 0 ? '+' : '') + Number(v).toFixed(1)
}
</script>
<template>
  <h1>建议</h1>
  <p class="sub">针对偏离、串车与大间隔的调班提示</p>
  <div class="card" v-for="(t,i) in tips" :key="i">
    <div>
      <strong>{{ t.stop_name }}</strong>
      <span class="badge" :class="statusBadge(t)" style="margin-left:.4rem">{{ statusLabel(t) }}</span>
      <template v-if="isDev(t)">
        · {{ t.earlier_trip }} · 偏差 {{ signed(t.deviation_min) }} 分
      </template>
      <template v-else>
        · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分
      </template>
    </div>
    <p class="muted">{{ t.suggestion }}</p>
  </div>
  <p v-if="!tips.length" class="muted">暂无异常建议</p>
</template>
