<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const savingId = ref<number | null>(null)
const savedId = ref<number | null>(null)

onMounted(load)

async function load() {
  rows.value = await api('/lines')
}

async function save(r: any) {
  const early = Number(r.early_tolerance_min)
  const late = Number(r.late_tolerance_min)
  if (!Number.isFinite(early) || !Number.isFinite(late) || early < 0 || late < 0) return
  savingId.value = r.id
  savedId.value = null
  try {
    const updated = await api(`/lines/${r.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ early_tolerance_min: early, late_tolerance_min: late }),
    })
    Object.assign(r, updated)
    savedId.value = r.id
  } finally {
    savingId.value = null
  }
}
</script>
<template>
  <h1>线路</h1>
  <p class="sub">运营线路与串车 / 大间隔判定阈值 · 相对计划发车的早到 / 晚到带宽</p>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th>编码</th><th>名称</th><th>计划间隔(分)</th><th>串车阈值</th><th>大间隔阈值</th>
          <th>允许早到(分)</th><th>允许晚到(分)</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td>
          <td>{{ r.name }}</td>
          <td>{{ r.planned_headway_min }}</td>
          <td>{{ r.bunch_threshold }}</td>
          <td>{{ r.large_threshold }}</td>
          <td><input class="band-input" type="number" min="0" step="0.5" v-model.number="r.early_tolerance_min" /></td>
          <td><input class="band-input" type="number" min="0" step="0.5" v-model.number="r.late_tolerance_min" /></td>
          <td>
            <button class="btn btn-sm" :disabled="savingId === r.id" @click="save(r)">
              {{ savingId === r.id ? '保存中' : '保存' }}
            </button>
            <span v-if="savedId === r.id" class="save-ok">已保存</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="muted band-hint">
      班次在某站相对「计划发车 + 沿途计划走行」的偏差超出带宽时先标偏离，不参与与邻班的串车 / 大间隔配对；带宽内的班次仍按阈值两两判定。两带宽都为 0 时只判间隔。
    </p>
  </div>
</template>
