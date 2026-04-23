<template>
  <div class="device-metrics-panel">
    <div class="panel-header">
      <div>
        <h4>Device Metrics</h4>
        <p>Poll only when this tab is active to keep the workbench lightweight.</p>
      </div>
      <div class="header-actions">
        <el-switch v-model="autoRefresh" active-text="Auto" />
        <el-select v-model="intervalMs" style="width: 110px">
          <el-option :value="2000" label="2s" />
          <el-option :value="3000" label="3s" />
          <el-option :value="5000" label="5s" />
        </el-select>
        <el-button :loading="loading" @click="loadSnapshot">Refresh</el-button>
        <el-button @click="resetSampler">Reset</el-button>
      </div>
    </div>

    <el-alert
      v-if="errorMessage"
      class="panel-alert"
      type="error"
      :closable="false"
      :title="errorMessage"
    />

    <div class="summary-grid">
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">CPU</div>
        <div class="metric-value">{{ formatPercent(snapshot?.cpu?.usage_percent) }}</div>
        <div class="metric-sub">Cores {{ snapshot?.cpu?.cores || '-' }}</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Memory</div>
        <div class="metric-value">{{ formatPercent(snapshot?.memory?.usage_percent) }}</div>
        <div class="metric-sub">{{ snapshot?.memory?.used_mb || 0 }} / {{ snapshot?.memory?.total_mb || 0 }} MB</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Download</div>
        <div class="metric-value">{{ formatNumber(snapshot?.network?.download_kbps) }} KB/s</div>
        <div class="metric-sub">Total {{ formatNumber(snapshot?.network?.rx_total_mb) }} MB</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Upload</div>
        <div class="metric-value">{{ formatNumber(snapshot?.network?.upload_kbps) }} KB/s</div>
        <div class="metric-sub">Total {{ formatNumber(snapshot?.network?.tx_total_mb) }} MB</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Battery</div>
        <div class="metric-value">{{ snapshot?.battery?.level ?? '-' }}%</div>
        <div class="metric-sub">{{ snapshot?.battery?.temperature_c ?? '-' }} C / {{ thermalText }}</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Storage / Current App</div>
        <div class="metric-value">{{ formatPercent(snapshot?.storage?.usage_percent) }}</div>
        <div class="metric-sub ellipsis">{{ snapshot?.current_app?.package_name || 'No foreground app' }}</div>
      </el-card>
    </div>

    <div class="chart-grid">
      <el-card shadow="never" class="chart-card">
        <template #header>
          <span>System Trend</span>
        </template>
        <div ref="systemChartRef" class="chart-host"></div>
      </el-card>

      <el-card shadow="never" class="chart-card">
        <template #header>
          <span>Network Trend</span>
        </template>
        <div ref="networkChartRef" class="chart-host"></div>
      </el-card>
    </div>

    <div class="detail-grid">
      <el-card shadow="never" class="detail-card">
        <template #header>
          <span>Device Profile</span>
        </template>
        <div class="detail-list">
          <div class="detail-row">
            <span class="detail-label">Brand / Model</span>
            <span class="detail-value">{{ deviceProfileText }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Android</span>
            <span class="detail-value">{{ snapshot?.profile?.android_version || '-' }} / SDK {{ snapshot?.profile?.sdk || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Resolution / Density</span>
            <span class="detail-value">{{ snapshot?.profile?.resolution || '-' }} / {{ snapshot?.profile?.density || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">CPU ABI</span>
            <span class="detail-value">{{ snapshot?.profile?.abi || '-' }}</span>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="detail-card">
        <template #header>
          <span>Health</span>
        </template>
        <div class="detail-list">
          <div class="detail-row">
            <span class="detail-label">Battery Status</span>
            <span class="detail-value">{{ snapshot?.battery?.status || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Battery Health</span>
            <span class="detail-value">{{ snapshot?.battery?.health || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Thermal</span>
            <span class="detail-value">{{ thermalText }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Available Memory</span>
            <span class="detail-value">{{ snapshot?.memory?.available_mb || 0 }} MB</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getDevicePerformanceSnapshot, resetDevicePerformance } from '@/api/app-automation'

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
  active: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['operation'])

const loading = ref(false)
const autoRefresh = ref(true)
const intervalMs = ref(2000)
const errorMessage = ref('')
const snapshot = ref(null)
const history = ref([])
const systemChartRef = ref(null)
const networkChartRef = ref(null)
const pageVisible = ref(typeof document === 'undefined' ? true : !document.hidden)

let systemChart = null
let networkChart = null
let pollTimer = null

const deviceProfileText = computed(() => {
  const profile = snapshot.value?.profile || {}
  return [profile.brand, profile.model].filter(Boolean).join(' / ') || '-'
})

const thermalText = computed(() => {
  const thermal = snapshot.value?.thermal || {}
  return thermal.status || '-'
})

const logOperation = (message, level = 'info', extra = null) => {
  emit('operation', {
    source: 'device-metrics',
    level,
    message,
    extra,
    timestamp: Date.now(),
  })
}

const formatNumber = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(1) : '-'
const formatPercent = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)}%` : '-'
const formatTime = (timestamp) => new Date(timestamp).toLocaleTimeString('zh-CN', { hour12: false })

const ensureCharts = () => {
  if (systemChartRef.value && !systemChart) {
    systemChart = echarts.init(systemChartRef.value)
  }
  if (networkChartRef.value && !networkChart) {
    networkChart = echarts.init(networkChartRef.value)
  }
}

const renderCharts = () => {
  if (!history.value.length) {
    return
  }
  ensureCharts()
  const labels = history.value.map((item) => item.label)

  systemChart?.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0 },
    grid: { left: 44, right: 24, top: 42, bottom: 28 },
    xAxis: { type: 'category', data: labels, boundaryGap: false },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: 'CPU',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.cpu),
        lineStyle: { width: 2, color: '#2563eb' },
        areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
      },
      {
        name: 'Memory',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.mem),
        lineStyle: { width: 2, color: '#f97316' },
      },
      {
        name: 'Battery',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.battery),
        lineStyle: { width: 2, color: '#16a34a' },
      },
    ],
  })

  networkChart?.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0 },
    grid: { left: 54, right: 24, top: 42, bottom: 28 },
    xAxis: { type: 'category', data: labels, boundaryGap: false },
    yAxis: { type: 'value', min: 0, axisLabel: { formatter: '{value} KB/s' } },
    series: [
      {
        name: 'Download',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.down),
        lineStyle: { width: 2, color: '#0f766e' },
        areaStyle: { color: 'rgba(15, 118, 110, 0.10)' },
      },
      {
        name: 'Upload',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.up),
        lineStyle: { width: 2, color: '#dc2626' },
      },
    ],
  })
}

const pushHistory = (data) => {
  history.value = [
    ...history.value.slice(-59),
    {
      label: formatTime(data.timestamp),
      cpu: Number(data.cpu?.usage_percent || 0),
      mem: Number(data.memory?.usage_percent || 0),
      battery: Number(data.battery?.level || 0),
      down: Number(data.network?.download_kbps || 0),
      up: Number(data.network?.upload_kbps || 0),
    },
  ]
  renderCharts()
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const syncPolling = () => {
  stopPolling()
  if (!props.active || !autoRefresh.value || !pageVisible.value) {
    return
  }
  pollTimer = setInterval(() => {
    loadSnapshot({ silent: true })
  }, intervalMs.value)
}

const handleVisibilityChange = () => {
  pageVisible.value = !document.hidden
  if (!pageVisible.value) {
    stopPolling()
    return
  }
  if (props.active) {
    loadSnapshot({ silent: true })
  }
  syncPolling()
}

const loadSnapshot = async ({ silent = false } = {}) => {
  loading.value = !silent
  try {
    const response = await getDevicePerformanceSnapshot(props.deviceId)
    snapshot.value = response.data?.data || null
    errorMessage.value = ''
    if (snapshot.value) {
      pushHistory(snapshot.value)
    }
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || error.message || 'Failed to load device metrics'
    if (!silent) {
      ElMessage.error(errorMessage.value)
    }
    logOperation('Device metrics sampling failed', 'error', error?.response?.data || error?.message)
  } finally {
    loading.value = false
  }
}

const resetSampler = async () => {
  try {
    await resetDevicePerformance(props.deviceId)
    history.value = []
    logOperation('Device metrics sampler reset', 'info')
    await loadSnapshot()
  } catch (error) {
    const message = error?.response?.data?.message || error.message || 'Failed to reset sampler'
    ElMessage.error(message)
    logOperation('Device metrics sampler reset failed', 'error', error?.response?.data || error?.message)
  }
}

const resizeCharts = () => {
  systemChart?.resize()
  networkChart?.resize()
}

watch(() => props.active, async (active) => {
  if (active) {
    await nextTick()
    ensureCharts()
    await loadSnapshot({ silent: true })
    syncPolling()
  } else {
    stopPolling()
  }
}, { immediate: true })

watch(autoRefresh, syncPolling)
watch(intervalMs, syncPolling)

onMounted(() => {
  window.addEventListener('resize', resizeCharts)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopPolling()
  window.removeEventListener('resize', resizeCharts)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  systemChart?.dispose()
  networkChart?.dispose()
  systemChart = null
  networkChart = null
})
</script>

<style scoped>
.device-metrics-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.panel-header h4 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.panel-header p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.panel-alert {
  margin-bottom: 4px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  border-radius: 16px;
}

.metric-label {
  font-size: 12px;
  color: #64748b;
}

.metric-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.metric-sub {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.chart-grid,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.chart-card,
.detail-card {
  border-radius: 16px;
}

.chart-host {
  height: 300px;
}

.detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eef2f7;
}

.detail-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.detail-label {
  color: #64748b;
}

.detail-value {
  color: #111827;
  text-align: right;
  word-break: break-all;
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1400px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .chart-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
