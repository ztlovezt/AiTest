<template>
  <div class="debug-log-panel">
    <div class="panel-header">
      <div>
        <h4>Debug Logs</h4>
        <p>Review workbench events and device logcat side by side.</p>
      </div>
      <div class="header-actions">
        <el-switch v-model="autoRefresh" active-text="Auto" />
        <el-select v-model="intervalMs" style="width: 110px">
          <el-option :value="3000" label="3s" />
          <el-option :value="5000" label="5s" />
          <el-option :value="8000" label="8s" />
        </el-select>
        <el-button :loading="loading" @click="loadLogs">Refresh</el-button>
      </div>
    </div>

    <div class="toolbar-row">
      <el-radio-group v-model="scope">
        <el-radio-button value="device">Device</el-radio-button>
        <el-radio-button value="app">App</el-radio-button>
      </el-radio-group>
      <el-select
        v-model="packageName"
        filterable
        clearable
        placeholder="Package name"
        style="min-width: 260px"
        :disabled="scope === 'device'"
      >
        <el-option v-for="pkg in installedPackages" :key="pkg" :label="pkg" :value="pkg" />
      </el-select>
      <el-select v-model="level" clearable placeholder="Level" style="width: 100px">
        <el-option label="All" value="" />
        <el-option label="Info+" value="I" />
        <el-option label="Warn+" value="W" />
        <el-option label="Error+" value="E" />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="Keyword" style="max-width: 220px" />
      <el-select v-model="lines" style="width: 120px">
        <el-option :value="200" label="200 lines" />
        <el-option :value="400" label="400 lines" />
        <el-option :value="800" label="800 lines" />
      </el-select>
      <el-button @click="copyLogs">Copy</el-button>
      <el-button @click="exportLogs">Export</el-button>
      <el-button type="warning" @click="clearDeviceLogs">Clear device log</el-button>
      <el-button @click="$emit('clear-events')">Clear workbench log</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      class="panel-alert"
      type="error"
      :closable="false"
      :title="errorMessage"
    />

    <div class="log-grid">
      <el-card shadow="never" class="log-card">
        <template #header>
          <div class="card-header">
            <span>Workbench Events</span>
            <span class="card-meta">{{ operationEvents.length }} items</span>
          </div>
        </template>
        <div ref="eventListRef" class="log-list">
          <div v-if="!operationEvents.length" class="empty-log">No workbench events</div>
          <div
            v-for="event in operationEvents"
            :key="event.id"
            class="event-row"
            :class="`level-${event.level || 'info'}`"
          >
            <div class="event-top">
              <span class="event-source">{{ sourceText(event.source) }}</span>
              <span class="event-time">{{ formatTime(event.timestamp) }}</span>
            </div>
            <div class="event-message">{{ event.message }}</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="log-card">
        <template #header>
          <div class="card-header">
            <span>Device Logcat</span>
            <span class="card-meta">{{ deviceLogs.length }} lines</span>
          </div>
        </template>
        <div ref="deviceLogListRef" class="log-list mono">
          <div v-if="!deviceLogs.length" class="empty-log">No logcat lines</div>
          <div
            v-for="(log, index) in deviceLogs"
            :key="`${log.time}-${log.pid}-${index}`"
            class="device-log-row"
            :class="`priority-${(log.priority || 'I').toLowerCase()}`"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-priority">{{ log.priority }}</span>
            <span class="log-tag">{{ log.tag }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  clearDeviceLogcat,
  getDeviceLogcat,
  getInstalledDevicePackages,
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
  events: {
    type: Array,
    default: () => [],
  },
  active: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['clear-events'])

const loading = ref(false)
const autoRefresh = ref(true)
const intervalMs = ref(5000)
const scope = ref('device')
const level = ref('')
const keyword = ref('')
const lines = ref(200)
const packageName = ref('')
const installedPackages = ref([])
const deviceLogs = ref([])
const errorMessage = ref('')
const deviceLogListRef = ref(null)
const eventListRef = ref(null)
const pageVisible = ref(typeof document === 'undefined' ? true : !document.hidden)

let pollTimer = null

const operationEvents = computed(() => props.events.slice().reverse())

const formatTime = (timestamp) => {
  const value = Number(timestamp)
  if (!Number.isFinite(value)) {
    return '-'
  }
  return new Date(value).toLocaleTimeString('zh-CN', { hour12: false })
}

const sourceText = (source) => {
  const mapping = {
    remote: 'Remote',
    apps: 'Apps',
    elements: 'Elements',
    'device-metrics': 'Device Metrics',
    'app-metrics': 'App Metrics',
    workbench: 'Workbench',
  }
  return mapping[source] || source || 'Workbench'
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
    loadLogs({ silent: true })
  }, intervalMs.value)
}

const handleVisibilityChange = () => {
  pageVisible.value = !document.hidden
  if (!pageVisible.value) {
    stopPolling()
    return
  }
  if (props.active) {
    loadLogs({ silent: true })
  }
  syncPolling()
}

const scrollToBottom = async (targetRef) => {
  await nextTick()
  const el = targetRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

const loadInstalledPackages = async () => {
  try {
    const response = await getInstalledDevicePackages(props.deviceId)
    installedPackages.value = response.data?.data || []
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || error.message || 'Failed to load installed packages'
  }
}

const loadLogs = async ({ silent = false } = {}) => {
  loading.value = !silent
  try {
    const response = await getDeviceLogcat(props.deviceId, {
      scope: scope.value,
      package_name: scope.value === 'app' ? packageName.value : '',
      level: level.value,
      keyword: keyword.value,
      lines: lines.value,
    })
    deviceLogs.value = response.data?.data?.lines || []
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || error.message || 'Failed to load logcat'
    if (!silent) {
      ElMessage.error(errorMessage.value)
    }
  } finally {
    loading.value = false
  }
}

const clearDeviceLogs = async () => {
  try {
    await clearDeviceLogcat(props.deviceId)
    deviceLogs.value = []
    ElMessage.success('Device log cleared')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error.message || 'Failed to clear device log')
  }
}

const copyLogs = async () => {
  const payload = deviceLogs.value.map((item) => item.raw || `${item.time} ${item.priority} ${item.tag}: ${item.message}`).join('\n')
  if (!payload) {
    ElMessage.warning('No logs to copy')
    return
  }
  try {
    await navigator.clipboard.writeText(payload)
    ElMessage.success('Logs copied')
  } catch (error) {
    ElMessage.error(`Copy failed: ${error?.message || 'clipboard unavailable'}`)
  }
}

const exportLogs = () => {
  const payload = deviceLogs.value.map((item) => item.raw || `${item.time} ${item.priority} ${item.tag}: ${item.message}`).join('\n')
  const blob = new Blob([payload], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `device-log-${props.deviceId}-${Date.now()}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

watch(() => props.currentApp?.package_name, (value) => {
  if (scope.value === 'app' && value && !packageName.value) {
    packageName.value = value
  }
}, { immediate: true })

watch(scope, (value) => {
  if (value === 'app' && !packageName.value && props.currentApp?.package_name) {
    packageName.value = props.currentApp.package_name
  }
  if (props.active) {
    loadLogs({ silent: true })
  }
})

watch([autoRefresh, intervalMs], syncPolling)
watch([level, keyword, lines, packageName], () => {
  if (props.active) {
    loadLogs({ silent: true })
    syncPolling()
  }
})

watch(deviceLogs, () => {
  scrollToBottom(deviceLogListRef)
})

watch(operationEvents, () => {
  scrollToBottom(eventListRef)
})

watch(() => props.active, async (active) => {
  if (active) {
    if (!installedPackages.value.length) {
      await loadInstalledPackages()
    }
    await loadLogs({ silent: true })
    syncPolling()
  } else {
    stopPolling()
  }
}, { immediate: true })

onMounted(() => {
  if (props.currentApp?.package_name) {
    packageName.value = props.currentApp.package_name
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopPolling()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.debug-log-panel {
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

.log-grid {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
}

.log-card {
  border-radius: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.card-meta {
  color: #6b7280;
  font-size: 12px;
}

.log-list {
  height: 560px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
}

.empty-log {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.event-row {
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.event-row.level-success {
  border-color: rgba(22, 163, 74, 0.2);
}

.event-row.level-warning {
  border-color: rgba(245, 158, 11, 0.25);
}

.event-row.level-error {
  border-color: rgba(220, 38, 38, 0.22);
}

.event-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
}

.event-message {
  margin-top: 8px;
  color: #111827;
  line-height: 1.6;
}

.device-log-row {
  display: grid;
  grid-template-columns: 110px 28px 180px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f8fafc;
  color: #0f172a;
}

.priority-e,
.priority-f {
  background: rgba(254, 226, 226, 0.85);
}

.priority-w {
  background: rgba(254, 243, 199, 0.85);
}

.priority-i {
  background: rgba(239, 246, 255, 0.85);
}

.log-tag {
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-message {
  word-break: break-word;
}

@media (max-width: 1200px) {
  .log-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .panel-header,
  .toolbar-row {
    flex-direction: column;
  }

  .device-log-row {
    grid-template-columns: 1fr;
  }
}
</style>
