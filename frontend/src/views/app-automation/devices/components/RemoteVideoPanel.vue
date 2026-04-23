<template>
  <div class="remote-video-panel">
    <div class="panel-toolbar">
      <div class="status-group">
        <el-tag :type="isConnected ? 'success' : 'info'" effect="plain">
          {{ isConnected ? '已连接' : '连接中' }}
        </el-tag>
        <span class="session-timer">{{ formatTime(sessionDuration) }}</span>
      </div>
      <div class="toolbar-actions">
        <el-button size="small" :loading="screenshotLoading" @click="takeScreenshot">
          <el-icon><Camera /></el-icon>
          截图
        </el-button>
        <el-button size="small" @click="toggleFullscreen">
          <el-icon><FullScreen /></el-icon>
          全屏
        </el-button>
      </div>
    </div>

    <div ref="videoContainerRef" class="video-wrapper">
      <div class="video-stage">
        <div v-if="!isConnected && !videoReady" class="status-overlay">
          <el-icon class="loading-icon" :size="40"><Loading /></el-icon>
          <p>{{ connectionMessage }}</p>
        </div>
        <div v-else-if="isConnected && !videoReady" class="status-overlay">
          <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
          <p>视频流加载中...</p>
        </div>

        <video
          ref="videoRef"
          autoplay
          muted
          webkit-playsinline
          playsinline
          tabindex="0"
        ></video>

        <div v-show="isConnected" class="zoom-controls">
          <el-button circle size="small" @click="zoomOut">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
          <span>{{ Math.round(zoomLevel * 100) }}%</span>
          <el-button circle size="small" @click="zoomIn">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
        </div>
      </div>

      <div v-show="isConnected" class="bottom-controls">
        <el-button circle size="large" @click="sendKeyCommand('back')">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-button circle size="large" @click="sendKeyCommand('home')">
          <el-icon><HomeFilled /></el-icon>
        </el-button>
        <el-button circle size="large" @click="sendKeyCommand('menu')">
          <el-icon><Menu /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Camera,
  FullScreen,
  HomeFilled,
  Loading,
  Menu,
  ZoomIn,
  ZoomOut,
} from '@element-plus/icons-vue'
import { captureDeviceScreenshot } from '@/api/app-automation'

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['status-change', 'session-ended', 'operation'])

const isConnected = ref(false)
const videoReady = ref(false)
const connectionMessage = ref('正在连接设备...')
const screenshotLoading = ref(false)
const zoomLevel = ref(1)
const sessionDuration = ref(0)
const sessionStartTime = ref(null)

const videoRef = ref(null)
const videoContainerRef = ref(null)

let ws = null
let scrcpyInput = null
let videoParser = null
let jmuxer = null
let timerInterval = null
let userInitiatedClose = false
let componentUnmounting = false

const wsBackendUrl = computed(() => import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')

const logOperation = (message, level = 'info', extra = null) => {
  emit('operation', {
    source: 'remote',
    level,
    message,
    extra,
    timestamp: Date.now(),
  })
}

const formatTime = (seconds) => {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

const startTimer = () => {
  sessionStartTime.value = Date.now()
  stopTimer()
  timerInterval = setInterval(() => {
    sessionDuration.value = Math.floor((Date.now() - sessionStartTime.value) / 1000)
  }, 1000)
}

const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

const loadScripts = async () => {
  if (window.JMUXER_LOADED) {
    return
  }

  const scripts = [
    '/scrcpy/jmuxer.min.js',
    '/scrcpy/exp-golomb.js',
    '/scrcpy/h264-sps-parser.js',
    '/scrcpy/video_parser.js',
    '/scrcpy/input.js',
  ]

  for (const src of scripts) {
    await new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = src
      script.onload = resolve
      script.onerror = reject
      document.head.appendChild(script)
    })
  }

  window.JMUXER_LOADED = true
}

const initJMuxer = () => {
  jmuxer = new JMuxer({
    node: videoRef.value,
    mode: 'video',
    flushingTime: 0,
    fps: 30,
    clearBuffer: true,
    debug: false,
    onReady: () => {
      videoReady.value = true
    },
    onError: (error) => {
      console.error('JMuxer error:', error)
      ElMessage.error('视频解码错误')
    },
  })
}

const initInput = (width, height) => {
  if (scrcpyInput) {
    return
  }

  const inputDataCallback = (data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  }

  scrcpyInput = new ScrcpyInput(inputDataCallback, videoRef.value, width, height, false)
}

const initVideoParser = () => {
  videoParser = new VideoParser(({ type, data }) => {
    if (type === 'nalu') {
      jmuxer.feed({ video: data })
    } else if (type === 'init') {
      jmuxer.feed({ video: data.sps })
      jmuxer.feed({ video: data.pps })
    } else if (type === 'screen_size') {
      initInput(data.width, data.height)
    } else if (type === 'size_change' && scrcpyInput) {
      scrcpyInput.resizeScreen(data.width, data.height)
    }
  })
}

const emitStatus = () => {
  emit('status-change', {
    connected: isConnected.value,
    message: connectionMessage.value,
  })
}

const connectWebSocket = () => {
  const backendUrl = wsBackendUrl.value
  const token = localStorage.getItem('access_token')
  let wsUrl = backendUrl.replace(/^http/, 'ws') + `/ws/app-automation/remote-device/${encodeURIComponent(props.deviceId)}/`

  if (token) {
    wsUrl += `?token=${token}`
  }

  ws = new WebSocket(wsUrl)
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    connectionMessage.value = '等待视频流...'
    emitStatus()
  }

  ws.onmessage = (event) => {
    if (typeof event.data === 'string') {
      let message = null
      try {
        message = JSON.parse(event.data)
      } catch (error) {
        console.error('Invalid websocket message:', event.data, error)
        return
      }
      if (message.type === 'connected') {
        isConnected.value = true
        connectionMessage.value = '连接成功'
        emitStatus()
        startTimer()
        logOperation(`远程会话已连接: ${props.deviceId}`, 'success')
      } else if (message.type === 'error') {
        connectionMessage.value = message.message || '连接失败'
        emitStatus()
        ElMessage.error(connectionMessage.value)
        logOperation(`远程会话错误: ${connectionMessage.value}`, 'error')
      }
      return
    }

    if (videoParser) {
      videoParser.appendData(new Uint8Array(event.data))
    }
  }

  ws.onclose = (event) => {
    isConnected.value = false
    videoReady.value = false
    connectionMessage.value = '连接已断开'
    stopTimer()
    emitStatus()

    if (userInitiatedClose) {
      logOperation(`远程会话已结束: ${props.deviceId}`, 'info')
      emit('session-ended')
      userInitiatedClose = false
    } else if (!componentUnmounting && event.code !== 1000) {
      ElMessage.warning('远程连接意外断开')
      logOperation(`远程连接意外断开: ${props.deviceId}`, 'warning', { code: event.code, reason: event.reason })
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    connectionMessage.value = '连接失败'
    emitStatus()
    ElMessage.error('WebSocket 连接错误')
    logOperation(`远程连接错误: ${props.deviceId}`, 'error')
  }
}

const applyZoom = () => {
  if (videoRef.value) {
    videoRef.value.style.transform = `scale(${zoomLevel.value})`
  }
}

const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value + 0.1, 3)
  applyZoom()
}

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value - 0.1, 0.5)
  applyZoom()
}

const sendKeyCommand = (key) => {
  if (!scrcpyInput) {
    return
  }

  let keyCode = null
  if (key === 'back') {
    keyCode = 4
  } else if (key === 'home') {
    keyCode = 3
  } else if (key === 'menu') {
    keyCode = 187
  }

  if (!keyCode) {
    return
  }

  const keyEvent = {
    getModifierState: () => false,
    shiftKey: false,
    ctrlKey: false,
    altKey: false,
    metaKey: false,
    repeat: 0,
  }

  scrcpyInput.snedKeyCode(keyEvent, 0, keyCode)
  setTimeout(() => {
    scrcpyInput.snedKeyCode(keyEvent, 1, keyCode)
  }, 100)
}

const takeScreenshot = async () => {
  screenshotLoading.value = true
  try {
    const response = await captureDeviceScreenshot(props.deviceId)
    const result = response.data
    if (!result.success) {
      ElMessage.error(result.msg || '截图失败')
      return
    }

    const link = document.createElement('a')
    link.href = result.data.content
    link.download = result.data.filename
    link.click()
    ElMessage.success('截图已保存')
    logOperation(`远控截图成功: ${result.data.filename}`, 'success')
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || error.message || '截图失败')
    logOperation('远控截图失败', 'error', error?.response?.data || error?.message)
  } finally {
    screenshotLoading.value = false
  }
}

const toggleFullscreen = async () => {
  if (!document.fullscreenElement) {
    try {
      await videoContainerRef.value.requestFullscreen()
      logOperation('远控面板进入全屏', 'info')
    } catch (error) {
      ElMessage.error(`全屏失败: ${error.message}`)
      logOperation('远控面板全屏失败', 'error', error?.message)
    }
    return
  }

  await document.exitFullscreen()
  logOperation('远控面板退出全屏', 'info')
}

const closeSession = () => {
  const canCloseSocket = ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  userInitiatedClose = true
  if (canCloseSocket) {
    ws.close(1000, 'User ended session')
  } else {
    emit('session-ended')
  }
}

onMounted(async () => {
  try {
    await loadScripts()
    initJMuxer()
    initVideoParser()
    connectWebSocket()
  } catch (error) {
    console.error('Remote panel init failed:', error)
    connectionMessage.value = '初始化失败'
    emitStatus()
    ElMessage.error(`初始化失败: ${error.message}`)
  }
})

onUnmounted(() => {
  componentUnmounting = true
  stopTimer()
  if (ws) {
    ws.close(1000, 'Component unmounted')
  }
  if (jmuxer) {
    jmuxer.destroy()
  }
  if (scrcpyInput) {
    scrcpyInput.destroy()
    scrcpyInput = null
  }
})

defineExpose({
  closeSession,
  takeScreenshot,
})
</script>

<style scoped lang="scss">
.remote-video-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f7;
  background: #fafcff;
}

.status-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.session-timer {
  font-size: 13px;
  font-family: Consolas, monospace;
  color: #4b5563;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.video-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.video-stage {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #f6f8fb 0%, #eef2f7 100%);
  overflow: hidden;
}

.status-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #6b7280;
  z-index: 2;
}

.loading-icon {
  animation: rotate 1.8s linear infinite;
}

video {
  max-width: 100%;
  max-height: 100%;
  outline: none;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.14);
  transform-origin: center center;
}

.zoom-controls {
  position: absolute;
  top: 14px;
  right: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.12);
}

.bottom-controls {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 16px;
  border-top: 1px solid #eef2f7;
  background: #fff;
}

@media (max-width: 768px) {
  .panel-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }

  .bottom-controls {
    gap: 16px;
    padding: 12px;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
