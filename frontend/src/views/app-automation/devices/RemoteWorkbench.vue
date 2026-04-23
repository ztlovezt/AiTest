<template>
  <div class="remote-workbench-page">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div class="device-meta">
          <h2>{{ pageTitle }}</h2>
          <!-- <div class="meta-line"> -->
            <!-- <el-tag :type="connectionStatus.connected ? 'success' : 'info'" effect="plain">
              {{ connectionStatus.connected ? '远控已连接' : '远控连接中' }}
            </el-tag> -->
            <!-- <span>{{ deviceId }}</span> -->
            <!-- <span v-if="currentApp.package_name">当前应用：{{ currentApp.package_name }}</span>
          </div> -->
        </div>
        <div v-if="currentApp.package_name">当前应用：{{ currentApp.package_name }}</div>
      </div>
      <div class="toolbar-right">
        <el-button @click="openLegacyPage">旧版远控</el-button>
        <el-button type="danger" @click="confirmEndSession">结束调试</el-button>
      </div>
    </div>

    <div class="page-body">
      <div class="left-panel">
        <RemoteVideoPanel
          ref="videoPanelRef"
          :device-id="deviceId"
          @status-change="handleStatusChange"
          @session-ended="handleSessionEnded"
          @operation="appendWorkbenchEvent"
        />
      </div>

      <div class="right-panel">
        <el-tabs v-model="activeTab" class="workbench-tabs" stretch>
          <el-tab-pane label="元素创建" name="elements" lazy>
            <ElementWorkbenchPanel
              :device-id="deviceId"
              :device-name="pageTitle"
              @created="handleElementCreated"
              @operation="appendWorkbenchEvent"
            />
          </el-tab-pane>
          <el-tab-pane label="应用管理" name="apps" lazy>
            <AppManagePanel
              :device-id="deviceId"
              @current-app-change="handleCurrentAppChange"
              @operation="appendWorkbenchEvent"
            />
          </el-tab-pane>
          <el-tab-pane label="设备性能" name="deviceMetrics" lazy>
            <DeviceMetricsPanel
              :device-id="deviceId"
              :active="activeTab === 'deviceMetrics'"
              @operation="appendWorkbenchEvent"
            />
          </el-tab-pane>
          <el-tab-pane label="App 性能" name="appMetrics" lazy>
            <AppPerformancePanel
              :device-id="deviceId"
              :current-app="currentApp"
              :active="activeTab === 'appMetrics'"
              @operation="appendWorkbenchEvent"
              @current-app-change="handleCurrentAppChange"
            />
          </el-tab-pane>
          <el-tab-pane label="调试日志" name="logs" lazy>
            <DebugLogPanel
              :device-id="deviceId"
              :current-app="currentApp"
              :events="workbenchEvents"
              :active="activeTab === 'logs'"
              @clear-events="clearWorkbenchEvents"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import AppManagePanel from './components/AppManagePanel.vue'
import AppPerformancePanel from './components/AppPerformancePanel.vue'
import DebugLogPanel from './components/DebugLogPanel.vue'
import DeviceMetricsPanel from './components/DeviceMetricsPanel.vue'
import ElementWorkbenchPanel from './components/ElementWorkbenchPanel.vue'
import RemoteVideoPanel from './components/RemoteVideoPanel.vue'

const route = useRoute()
const router = useRouter()

const videoPanelRef = ref(null)
const activeTab = ref('elements')
const connectionStatus = ref({ connected: false, message: '正在连接设备...' })
const currentApp = ref({ package_name: '', activity: '' })
const workbenchEvents = ref([])

const deviceId = computed(() => String(route.params.id || ''))
const pageTitle = computed(() => String(route.query.name || route.params.id || '远程工作台'))

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push({ name: 'AppDeviceList' })
}

const openLegacyPage = () => {
  router.push(`/app-automation/remote-connection/${encodeURIComponent(deviceId.value)}`)
  appendWorkbenchEvent({
    source: 'workbench',
    level: 'info',
    message: '切换到旧版远控页面',
  })
}

const handleStatusChange = (status) => {
  connectionStatus.value = status
}

const handleCurrentAppChange = (appInfo) => {
  currentApp.value = appInfo || { package_name: '', activity: '' }
}

const appendWorkbenchEvent = (event) => {
  workbenchEvents.value = [
    ...workbenchEvents.value.slice(-199),
    {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: event?.timestamp || Date.now(),
      source: event?.source || 'workbench',
      level: event?.level || 'info',
      message: event?.message || '工作台事件',
      extra: event?.extra || null,
    },
  ]
}

const clearWorkbenchEvents = () => {
  workbenchEvents.value = []
}

const handleElementCreated = () => {
  ElMessage.success('元素已保存到元素库')
}

const handleSessionEnded = () => {
  ElMessage.success('调试会话已结束')
  appendWorkbenchEvent({
    source: 'workbench',
    level: 'info',
    message: '调试会话已结束并返回上一页',
  })
  goBack()
}

const confirmEndSession = async () => {
  try {
    await ElMessageBox.confirm('确定要结束当前调试会话吗？', '结束调试', {
      type: 'warning',
      confirmButtonText: '确定结束',
      cancelButtonText: '取消',
    })
    appendWorkbenchEvent({
      source: 'workbench',
      level: 'warning',
      message: '用户手动结束调试会话',
    })
    videoPanelRef.value?.closeSession()
  } catch {
    // noop
  }
}

onMounted(() => {
  appendWorkbenchEvent({
    source: 'workbench',
    level: 'info',
    message: `远程工作台已打开: ${deviceId.value}`,
  })
})
</script>

<style scoped lang="scss">
.remote-workbench-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
  box-sizing: border-box;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px 0;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.device-meta h2 {
  margin: 0;
  font-size: 22px;
  color: #111827;
}

.meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  font-size: 13px;
  color: #6b7280;
}

.toolbar-right {
  display: flex;
  gap: 10px;
}

.page-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(720px, 2fr);
  gap: 16px;
  padding: 0 24px 24px;
  overflow: hidden;
  box-sizing: border-box;
}

.left-panel,
.right-panel {
  min-height: 0;
  overflow: hidden;
}

.right-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  overflow: hidden;
}

.workbench-tabs {
  height: 100%;
}

:deep(.workbench-tabs .el-tabs__header) {
  margin: 0;
  padding: 0 16px;
  border-bottom: 1px solid #edf2f7;
}

:deep(.workbench-tabs .el-tabs__content) {
  height: calc(100% - 56px);
  overflow: hidden;
}

:deep(.workbench-tabs .el-tab-pane) {
  height: 100%;
  padding: 16px;
  overflow: auto;
}

.placeholder-card {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 1280px) {
  .page-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .remote-workbench-page {
    height: 100%;
  }

  .page-toolbar {
    flex-direction: column;
    align-items: stretch;
    padding: 16px 16px 0;
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
  }

  .toolbar-right {
    justify-content: flex-end;
  }

  .page-body {
    padding: 0 16px 16px;
  }
}
</style>
