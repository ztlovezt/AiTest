<template>
  <div class="app-performance-panel">
    <div class="panel-header">
      <div>
        <h4>App Metrics</h4>
        <p>Focus on one app process and follow the foreground app when needed.</p>
      </div>
      <div class="header-actions">
        <el-switch v-model="followForeground" active-text="Follow foreground" />
        <el-switch v-model="autoRefresh" active-text="Auto" />
        <el-select v-model="intervalMs" style="width: 110px">
          <el-option :value="2000" label="2s" />
          <el-option :value="3000" label="3s" />
          <el-option :value="5000" label="5s" />
        </el-select>
      </div>
    </div>

    <div class="toolbar-row">
      <el-select
        v-model="selectedPackage"
        filterable
        clearable
        placeholder="Select installed package"
        style="min-width: 320px"
        :disabled="followForeground"
      >
        <el-option v-for="pkg in installedPackages" :key="pkg" :label="pkg" :value="pkg" />
      </el-select>
      <el-button :loading="packageLoading" @click="loadInstalledPackages">Refresh packages</el-button>
      <el-button :loading="loading" @click="loadSnapshot">Refresh metrics</el-button>
      <el-button @click="resetSampler">Reset sampler</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      class="panel-alert"
      type="error"
      :closable="false"
      :title="errorMessage"
    />

    <div v-if="resolvedPackage" class="summary-grid">
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Package</div>
        <div class="metric-value metric-value--small ellipsis">{{ resolvedPackage }}</div>
        <div class="metric-sub">{{ snapshot?.foreground ? 'Foreground app' : 'Background / inactive' }}</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">App CPU</div>
        <div class="metric-value">{{ formatPercent(snapshot?.cpu?.usage_percent) }}</div>
        <div class="metric-sub">Normalized by CPU cores</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">PSS Memory</div>
        <div class="metric-value">{{ formatNumber(snapshot?.memory?.pss_mb) }} MB</div>
        <div class="metric-sub">RSS {{ formatNumber(snapshot?.memory?.rss_mb) }} MB</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Threads / FD</div>
        <div class="metric-value">{{ snapshot?.process?.threads || 0 }}</div>
        <div class="metric-sub">Open FD {{ snapshot?.process?.open_fds || 0 }}</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">FPS</div>
        <div class="metric-value">{{ formatNumber(snapshot?.frame_stats?.fps) }}</div>
        <div class="metric-sub">Total frames {{ snapshot?.frame_stats?.total_frames || 0 }}</div>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <div class="metric-label">Jank</div>
        <div class="metric-value">{{ formatPercent(snapshot?.frame_stats?.jank_percent) }}</div>
        <div class="metric-sub">Janky frames {{ snapshot?.frame_stats?.janky_frames || 0 }}</div>
      </el-card>
    </div>

    <el-empty v-else description="No target app. Pick an app or bring one to foreground first." />

    <template v-if="resolvedPackage">
      <div class="chart-grid">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>CPU / Memory Trend</span>
          </template>
          <div ref="resourceChartRef" class="chart-host"></div>
        </el-card>

        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>Rendering Trend</span>
          </template>
          <div ref="renderChartRef" class="chart-host"></div>
        </el-card>
      </div>

      <div class="detail-grid">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <span>Process Info</span>
          </template>
          <div class="detail-list">
            <div class="detail-row">
              <span class="detail-label">PID</span>
              <span class="detail-value">{{ snapshot?.pid || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Activity</span>
              <span class="detail-value">{{ snapshot?.activity || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">VM Size</span>
              <span class="detail-value">{{ formatNumber(snapshot?.process?.vm_size_mb) }} MB</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Private Dirty</span>
              <span class="detail-value">{{ formatNumber(snapshot?.memory?.private_dirty_mb) }} MB</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="detail-card">
          <template #header>
            <span>Frame Percentiles</span>
          </template>
          <div class="detail-list">
            <div class="detail-row">
              <span class="detail-label">P50</span>
              <span class="detail-value">{{ snapshot?.frame_stats?.frame_time_ms?.p50 || 0 }} ms</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">P90</span>
              <span class="detail-value">{{ snapshot?.frame_stats?.frame_time_ms?.p90 || 0 }} ms</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">P95</span>
              <span class="detail-value">{{ snapshot?.frame_stats?.frame_time_ms?.p95 || 0 }} ms</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">P99</span>
              <span class="detail-value">{{ snapshot?.frame_stats?.frame_time_ms?.p99 || 0 }} ms</span>
            </div>
          </div>
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getAppPerformanceSnapshot,
  getDeviceCurrentApp,
  getInstalledDevicePackages,
  resetDevicePerformance,
} from '@/api/app-automation'

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
  currentApp: {
    type: Object,
    default: () => ({ package_name: '', activity: '' }),
  },
  active: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['operation', 'current-app-change'])

const loading = ref(false)
const packageLoading = ref(false)
const autoRefresh = ref(true)
const followForeground = ref(true)
const intervalMs = ref(2000)
const selectedPackage = ref('')
const snapshot = ref(null)
const installedPackages = ref([])
const errorMessage = ref('')
const history = ref([])
const resourceChartRef = ref(null)
const renderChartRef = ref(null)
const pageVisible = ref(typeof document === 'undefined' ? true : !document.hidden)

let resourceChart = null
let renderChart = null
let pollTimer = null

const resolvedPackage = computed(() => {
  if (followForeground.value) {
    return props.currentApp?.package_name || selectedPackage.value || ''
  }
  return selectedPackage.value || ''
})

const logOperation = (message, level = 'info', extra = null) => {
  emit('operation', {
    source: 'app-metrics',
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
  if (resourceChartRef.value && !resourceChart) {
    resourceChart = echarts.init(resourceChartRef.value)
  }
  if (renderChartRef.value && !renderChart) {
    renderChart = echarts.init(renderChartRef.value)
  }
}

const renderCharts = () => {
  if (!history.value.length) {
    return
  }
  ensureCharts()
  const labels = history.value.map((item) => item.label)

  resourceChart?.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0 },
    grid: { left: 46, right: 48, top: 42, bottom: 28 },
    xAxis: { type: 'category', data: labels, boundaryGap: false },
    yAxis: [
      { type: 'value', min: 0, axisLabel: { formatter: '{value}%' } },
      { type: 'value', min: 0, axisLabel: { formatter: '{value} MB' } },
    ],
    series: [
      {
        name: 'CPU',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.cpu),
        lineStyle: { width: 2, color: '#2563eb' },
        areaStyle: { color: 'rgba(37, 99, 235, 0.10)' },
      },
      {
        name: 'PSS',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        showSymbol: false,
        data: history.value.map((item) => item.pss),
        lineStyle: { width: 2, color: '#9333ea' },
      },
    ],
  })

  renderChart?.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0 },
    grid: { left: 44, right: 48, top: 42, bottom: 28 },
    xAxis: { type: 'category', data: labels, boundaryGap: false },
    yAxis: [
      { type: 'value', min: 0, axisLabel: { formatter: '{value}' } },
      { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' } },
    ],
    series: [
      {
        name: 'FPS',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.fps),
        lineStyle: { width: 2, color: '#16a34a' },
        areaStyle: { color: 'rgba(22, 163, 74, 0.10)' },
      },
      {
        name: 'Jank',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        showSymbol: false,
        data: history.value.map((item) => item.jank),
        lineStyle: { width: 2, color: '#dc2626' },
      },
      {
        name: 'FD',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: history.value.map((item) => item.fds),
        lineStyle: { width: 2, color: '#0f766e' },
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
      pss: Number(data.memory?.pss_mb || 0),
      fps: Number(data.frame_stats?.fps || 0),
      jank: Number(data.frame_stats?.jank_percent || 0),
      fds: Number(data.process?.open_fds || 0),
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
  if (!props.active || !autoRefresh.value || !resolvedPackage.value || !pageVisible.value) {
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
  if (props.active && resolvedPackage.value) {
    loadSnapshot({ silent: true })
  }
  syncPolling()
}

const syncForegroundPackage = async () => {
  if (!followForeground.value) {
    return resolvedPackage.value
  }

  const response = await getDeviceCurrentApp(props.deviceId)
  const appInfo = response.data?.data || { package_name: '', activity: '' }
  if (appInfo.package_name) {
    selectedPackage.value = appInfo.package_name
    emit('current-app-change', appInfo)
  }
  return appInfo.package_name || selectedPackage.value || ''
}

const loadInstalledPackages = async () => {
  packageLoading.value = true
  try {
    const response = await getInstalledDevicePackages(props.deviceId)
    installedPackages.value = response.data?.data || []
  } catch (error) {
    const message = error?.response?.data?.message || error.message || 'Failed to load installed packages'
    ElMessage.error(message)
    logOperation('Installed package list load failed', 'error', error?.response?.data || error?.message)
  } finally {
    packageLoading.value = false
  }
}

const loadSnapshot = async ({ silent = false } = {}) => {
  loading.value = !silent
  try {
    const packageName = await syncForegroundPackage()
    if (!packageName) {
      snapshot.value = null
      history.value = []
      errorMessage.value = ''
      return
    }
    const response = await getAppPerformanceSnapshot(props.deviceId, { package_name: packageName })
    snapshot.value = response.data?.data || null
    errorMessage.value = ''
    if (snapshot.value) {
      pushHistory(snapshot.value)
    }
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || error.message || 'Failed to load app metrics'
    if (!silent) {
      ElMessage.error(errorMessage.value)
    }
    logOperation('App metrics sampling failed', 'error', error?.response?.data || error?.message)
  } finally {
    loading.value = false
  }
}

const resetSampler = async () => {
  if (!resolvedPackage.value) {
    ElMessage.warning('No target app selected')
    return
  }
  try {
    await resetDevicePerformance(props.deviceId, { package_name: resolvedPackage.value })
    history.value = []
    logOperation(`App metrics sampler reset: ${resolvedPackage.value}`, 'info')
    await loadSnapshot()
  } catch (error) {
    const message = error?.response?.data?.message || error.message || 'Failed to reset sampler'
    ElMessage.error(message)
    logOperation('App metrics sampler reset failed', 'error', error?.response?.data || error?.message)
  }
}

const resizeCharts = () => {
  resourceChart?.resize()
  renderChart?.resize()
}

watch(() => props.currentApp?.package_name, (packageName) => {
  if (followForeground.value && packageName) {
    selectedPackage.value = packageName
  }
})

watch(() => props.active, async (active) => {
  if (active) {
    await nextTick()
    ensureCharts()
    if (!installedPackages.value.length) {
      await loadInstalledPackages()
    }
    await loadSnapshot({ silent: true })
    syncPolling()
  } else {
    stopPolling()
  }
}, { immediate: true })

watch(autoRefresh, syncPolling)
watch(intervalMs, syncPolling)
watch(resolvedPackage, () => {
  history.value = []
  if (props.active) {
    loadSnapshot({ silent: true })
    syncPolling()
  }
})

onMounted(() => {
  if (props.currentApp?.package_name) {
    selectedPackage.value = props.currentApp.package_name
  }
  window.addEventListener('resize', resizeCharts)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopPolling()
  window.removeEventListener('resize', resizeCharts)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  resourceChart?.dispose()
  renderChart?.dispose()
  resourceChart = null
  renderChart = null
})
</script>

<style scoped>
.app-performance-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header,
.toolbar-row {
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
  font-size: 13px;
  color: #6b7280;
}

.header-actions,
.toolbar-row {
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.metric-card,
.chart-card,
.detail-card {
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
  color: #111827;
}

.metric-value--small {
  font-size: 16px;
  line-height: 1.5;
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
  .panel-header,
  .toolbar-row {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
