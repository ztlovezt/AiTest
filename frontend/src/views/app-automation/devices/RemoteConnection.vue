<template>
  <div class="remote-connection-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button @click="goBack" size="small">
          <el-icon><ArrowLeft /></el-icon>
          {{ t('appAutomation.remoteConnection.back') }}
        </el-button>
        <span class="device-name">{{ deviceName }}</span>
      </div>
      
      <div class="toolbar-center">
        <div class="timer-display">
          <el-icon><Clock /></el-icon>
          <span>{{ formatTime(sessionDuration) }}</span>
        </div>
      </div>
      
      <div class="toolbar-right">
        <el-button @click="takeScreenshot" size="small" :loading="screenshotLoading">
          <el-icon><Camera /></el-icon>
          {{ t('appAutomation.remoteConnection.screenshot') }}
        </el-button>
        <el-button @click="toggleFullscreen" size="small">
          <el-icon><FullScreen /></el-icon>
          {{ t('appAutomation.remoteConnection.fullscreen') }}
        </el-button>
        <el-button @click="endSession" type="danger" size="small">
          <el-icon><Close /></el-icon>
          {{ t('appAutomation.remoteConnection.endSession') }}
        </el-button>
      </div>
    </div>

    <!-- 视频显示区域 -->
    <div class="video-wrapper" ref="videoContainerRef">
      <div class="video-container">
        <!-- 加载中状态 -->
        <div v-if="!isConnected && !videoReady" class="connection-status">
          <el-icon class="loading-icon" :size="48"><Loading /></el-icon>
          <p>{{ connectionMessage }}</p>
        </div>
        
        <!-- 视频加载中提示 -->
        <div v-if="!videoReady && isConnected" class="video-loading">
          <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
          <p>{{ t('appAutomation.remoteConnection.videoLoading') }}</p>
        </div>
        
        <video 
          ref="videoRef" 
          autoplay 
          muted 
          webkit-playsinline 
          playsinline
          @mousedown="handleMouseDown"
          @mouseup="handleMouseUp"
          @mousemove="handleMouseMove"
          @wheel="handleWheel"
          tabindex="0"
        ></video>
        
        <!-- 缩放控制 -->
        <div class="zoom-controls" v-show="isConnected">
          <el-button @click="zoomOut" circle size="small">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <el-button @click="zoomIn" circle size="small">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
        </div>
      </div>
      
      <!-- 底部控制按钮 - 放在视频下方 -->
      <div class="bottom-controls" v-show="isConnected">
        <el-button @click="sendKeyCommand('back')" circle size="large">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-button @click="sendKeyCommand('home')" circle size="large">
          <el-icon><HomeFilled /></el-icon>
        </el-button>
        <el-button @click="sendKeyCommand('menu')" circle size="large">
          <el-icon><Menu /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  ArrowLeft, Clock, Camera, FullScreen, Close, 
  Loading, HomeFilled, Menu, ZoomIn, ZoomOut 
} from '@element-plus/icons-vue'

const { t } = useI18n()

// Global types from loaded scripts - declare for TypeScript
declare global {
  interface Window {
    JMUXER_LOADED?: boolean
  }
  
  // JMuxer constructor
  const JMuxer: new (options: any) => any
  
  // VideoParser constructor
  const VideoParser: new (callback: (data: {type: string, data: any}) => void) => {
    appendData: (data: Uint8Array) => void
  }
  
  // ScrcpyInput constructor
  const ScrcpyInput: new (
    callback: (data: any) => void,
    videoElement: HTMLVideoElement,
    width: number,
    height: number,
    rotate: boolean
  ) => {
    width: number
    height: number
    resizeScreen: (width: number, height: number) => void
    createTouchProtocolData: (...args: any[]) => any
    createScrollProtocolData: (...args: any[]) => any
    snedKeyCode: (event: any, action: number, keyCode: number) => void
    destroy: () => void
  }
}
const route = useRoute()
const router = useRouter()

// 状态变量
const deviceName = ref('')
const isConnected = ref(false)
const videoReady = ref(false) // 视频是否已准备好
const connectionMessage = ref(t('appAutomation.remoteConnection.connecting'))
const sessionStartTime = ref(null)
const sessionDuration = ref(0)
const screenshotLoading = ref(false)
const zoomLevel = ref(1)

// Refs
const videoRef = ref(null)
const videoContainerRef = ref(null)

// WebSocket
let ws = null
let scrcpyInput = null
let videoParser = null
let jmuxer = null
let timerInterval = null

// 设备ID
const deviceId = computed(() => route.params.device_id)

// 格式化时间
const formatTime = (seconds) => {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

// 初始化计时器
const startTimer = () => {
  sessionStartTime.value = Date.now()
  timerInterval = setInterval(() => {
    sessionDuration.value = Math.floor((Date.now() - sessionStartTime.value) / 1000)
  }, 1000)
}

// 停止计时器
const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// 加载必要的脚本
const loadScripts = async () => {
  // 检查是否已经加载过，避免重复声明
  if (window['JMUXER_LOADED']) {
    console.log('Scripts already loaded, skipping...')
    return
  }
  
  const scripts = [
    '/scrcpy/jmuxer.min.js',
    '/scrcpy/exp-golomb.js',
    '/scrcpy/h264-sps-parser.js',
    '/scrcpy/video_parser.js',
    '/scrcpy/input.js'
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
  
  // 标记为已加载
  window['JMUXER_LOADED'] = true
  console.log('All scripts loaded successfully')
}

// 初始化 JMuxer
const initJMuxer = () => {
  jmuxer = new JMuxer({
    node: videoRef.value,
    mode: 'video',
    flushingTime: 0,        // 立即刷新，不等待
    fps: 30,                // 匹配后端 30fps，避免等待多余帧
    clearBuffer: true,      // 清除旧缓冲，减少延迟
    debug: false,           // 生产环境关闭调试
    onReady: () => {
      console.log('JMuxer ready')
      videoReady.value = true
    },
    onError: (err) => {
      console.error('JMuxer error:', err)
      ElMessage.error('视频解码错误')
    }
  })
}

// 初始化视频解析器
const initVideoParser = () => {
  videoParser = new VideoParser(({type, data}) => {
    if (type === 'nalu') {
      jmuxer.feed({ video: data })
    } else if (type === 'init') {
      jmuxer.feed({ video: data.sps })
      jmuxer.feed({ video: data.pps })
    } else if (type === 'screen_size') {
      initInput(data.width, data.height)
    } else if (type === 'size_change') {
      if (scrcpyInput) {
        scrcpyInput.resizeScreen(data.width, data.height)
      }
    }
  })
}

// 初始化输入处理
const initInput = (width, height) => {
  // 防止重复初始化
  if (scrcpyInput) {
    console.log('ScrcpyInput already initialized, skipping...')
    return
  }
  
  function input_data_cb(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  }
  
  scrcpyInput = new ScrcpyInput(input_data_cb, videoRef.value, width, height, false)
  console.log('ScrcpyInput initialized')
}

// 建立 WebSocket 连接
const connectWebSocket = async () => {
  try {
    // 从环境变量获取后端地址（.env 文件中的 VITE_API_BASE_URL）
    // 如果使用局域网访问，请在 .env 中配置实际的后端服务器IP，例如：http://192.168.3.208:8000
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
    
    // 获取 JWT Token（从 localStorage）
    const token = localStorage.getItem('access_token')
    let wsUrl = backendUrl.replace('http', 'ws') + `/ws/app-automation/remote-device/${deviceId.value}/`
    
    // 如果有 token，添加到 URL 参数中
    if (token) {
      wsUrl += `?token=${token}`
      console.log('Using JWT token authentication')
    } else {
      console.warn('No access token found, connection may fail')
    }
    
    console.log('Connecting to WebSocket:', wsUrl)
    
    ws = new WebSocket(wsUrl)
    ws.binaryType = 'arraybuffer'
    
    ws.onopen = () => {
      console.log('WebSocket connected')
      connectionMessage.value = t('appAutomation.remoteConnection.waitingVideo')
    }
    
    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        // 文本消息
        const message = JSON.parse(event.data)
        handleTextMessage(message)
      } else {
        // 二进制数据 - 视频帧
        if (videoParser) {
          const newData = new Uint8Array(event.data)
          videoParser.appendData(newData)
        }
      }
    }
    
    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
      isConnected.value = false
      connectionMessage.value = t('appAutomation.remoteConnection.disconnected')
      stopTimer()
      
      if (event.code !== 1000) {
        ElMessage.warning(t('appAutomation.remoteConnection.connectionInterrupted'))
      }
      
      // 重置视频状态
      videoReady.value = false
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      connectionMessage.value = t('appAutomation.remoteConnection.connectionFailed')
      ElMessage.error(t('appAutomation.remoteConnection.websocketError'))
    }
    
  } catch (error) {
    console.error('Failed to connect:', error)
    ElMessage.error('连接失败: ' + error.message)
  }
}

// 处理文本消息
const handleTextMessage = (message) => {
  console.log('Received message:', message)
  
  if (message.type === 'connected') {
    isConnected.value = true
    connectionMessage.value = t('appAutomation.remoteConnection.connected')
    startTimer()
    ElMessage.success(t('appAutomation.remoteConnection.deviceConnected'))
  } else if (message.type === 'error') {
    ElMessage.error(message.message || t('appAutomation.common.failed'))
    connectionMessage.value = message.message
  }
}

// 鼠标事件处理 - 已禁用，使用 input.js 中的事件处理器
// 避免重复绑定导致双击问题
const handleMouseDown = (event) => {
  // 不再在此处处理，由 ScrcpyInput 统一处理
}

const handleMouseUp = (event) => {
  // 不再在此处处理，由 ScrcpyInput 统一处理
}

const handleMouseMove = (event) => {
  // 不再在此处处理，由 ScrcpyInput 统一处理
}

const handleWheel = (event) => {
  // 不再在此处处理，由 ScrcpyInput 统一处理
}

// 发送按键命令
const sendKeyCommand = (key) => {
  if (!scrcpyInput) return
  
  let keyCode
  switch (key) {
    case 'back':
      keyCode = 4
      break
    case 'home':
      keyCode = 3
      break
    case 'menu':
      keyCode = 187
      break
    default:
      return
  }
  
  // 按下
  const downEvent = { getModifierState: () => false, shiftKey: false, ctrlKey: false, altKey: false, metaKey: false, repeat: 0 }
  scrcpyInput.snedKeyCode(downEvent, 0, keyCode)
  
  // 释放
  setTimeout(() => {
    scrcpyInput.snedKeyCode(downEvent, 1, keyCode)
  }, 100)
}

// 截图功能
const takeScreenshot = async () => {
  screenshotLoading.value = true
  try {
    // 获取 JWT Token
    const token = localStorage.getItem('access_token')
    
    const response = await fetch(`/api/app-automation/devices/${deviceId.value}/screenshot/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-CSRFToken': getCookie('csrftoken')
      }
    })
    
    const result = await response.json()
    
    if (result.success) {
      // 创建下载链接
      const link = document.createElement('a')
      link.href = result.data.content
      link.download = result.data.filename
      link.click()
      ElMessage.success(t('appAutomation.remoteConnection.screenshotSaved'))
    } else {
      ElMessage.error(result.msg || t('appAutomation.remoteConnection.screenshotFailed'))
    }
  } catch (error) {
    console.error('Screenshot failed:', error)
    ElMessage.error(t('appAutomation.remoteConnection.screenshotFailed') + ': ' + error.message)
  } finally {
    screenshotLoading.value = false
  }
}

// 获取 CSRF token
const getCookie = (name) => {
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

// 全屏切换
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    videoContainerRef.value.requestFullscreen().catch(err => {
      ElMessage.error(t('appAutomation.remoteConnection.fullscreenFailed') + ': ' + err.message)
    })
  } else {
    document.exitFullscreen()
  }
}

// 缩放控制
const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value + 0.1, 3)
  applyZoom()
}

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value - 0.1, 0.5)
  applyZoom()
}

const applyZoom = () => {
  if (videoRef.value) {
    videoRef.value.style.transform = `translate(-50%, -50%) scale(${zoomLevel.value})`
  }
}

// 结束会话
const endSession = () => {
  ElMessageBox.confirm(
    t('appAutomation.remoteConnection.confirmEndSession'),
    t('appAutomation.remoteConnection.endSessionTitle'),
    {
      confirmButtonText: t('appAutomation.remoteConnection.confirmEnd'),
      cancelButtonText: t('appAutomation.remoteConnection.cancel'),
      type: 'warning',
      center: true,
      roundButton: true,
    }
  ).then(() => {
    if (ws) {
      ws.close(1000, 'User ended session')
    }
    ElMessage.success(t('appAutomation.remoteConnection.sessionEnded'))
    goBack()
  }).catch(() => {
    // 用户取消
  })
}

// 返回
const goBack = () => {
  router.back()
}

// 生命周期
onMounted(async () => {
  // 检查 device_id
  if (!deviceId.value) {
    ElMessage.error(t('appAutomation.remoteConnection.missingDeviceId'))
    router.back()
    return
  }
  
  try {
    // 加载脚本
    await loadScripts()
    
    // 初始化 JMuxer
    initJMuxer()
    
    // 初始化视频解析器
    initVideoParser()
    
    // 连接 WebSocket
    connectWebSocket()
    
    // 设置设备名称
    deviceName.value = `${t('appAutomation.device.deviceName')}: ${deviceId.value}`
    
  } catch (error) {
    console.error('Initialization failed:', error)
    ElMessage.error(t('appAutomation.remoteConnection.initializationFailed') + ': ' + error.message)
  }
})

onUnmounted(() => {
  // 清理资源
  stopTimer()
  
  if (ws) {
    ws.close(1000, 'Component unmounted')
  }
  
  if (jmuxer) {
    jmuxer.destroy()
  }
  
  // 清理 ScrcpyInput，移除事件监听器
  if (scrcpyInput) {
    scrcpyInput.destroy()
    scrcpyInput = null
  }
})
</script>

<style scoped lang="scss">
.remote-connection-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa; // 灰白色背景，与主界面保持一致
  overflow: hidden;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  
  // 隐藏所有滚动条
  * {
    scrollbar-width: none; // Firefox
    -ms-overflow-style: none; // IE/Edge
    
    &::-webkit-scrollbar {
      display: none; // Chrome/Safari
      width: 0;
      height: 0;
    }
  }
  
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    background-color: #ffffff; // 白色工具栏
    border-bottom: 1px solid #e4e7ed; // 浅灰色边框
    color: #303133; // 深灰色文字
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); // 轻微阴影
    
    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .device-name {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }
    }
    
    .toolbar-center {
      .timer-display {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 18px;
        font-family: 'Courier New', monospace;
        background-color: #f5f7fa;
        padding: 8px 16px;
        border-radius: 4px;
        color: #409EFF;
        
        .el-icon {
          color: #409EFF;
        }
      }
    }
    
    .toolbar-right {
      display: flex;
      gap: 8px;
    }
  }
  
  .video-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background-color: #f5f7fa;
    
    .video-container {
      flex: 1;
      position: relative;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      
      .connection-status {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
        color: #606266;
        
        .loading-icon {
          animation: rotate 2s linear infinite;
          color: #409EFF;
        }
        
        p {
          margin-top: 16px;
          font-size: 16px;
          color: #606266;
        }
      }
      
      .video-loading {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
        color: #909399;
        
        .loading-icon {
          animation: rotate 2s linear infinite;
          color: #409EFF;
        }
        
        p {
          margin-top: 12px;
          font-size: 14px;
          color: #909399;
        }
      }
      
      video {
        position: relative;
        max-width: 100%;
        max-height: 100%;
        width: auto;
        height: auto;
        outline: none;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border-radius: 8px;
        
        &::-webkit-media-controls {
          display: none !important;
        }
      }
      
      .zoom-controls {
        position: absolute;
        top: 20px;
        right: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        background-color: rgba(255, 255, 255, 0.95);
        padding: 8px 12px;
        border-radius: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        z-index: 10;
        
        .zoom-level {
          color: #606266;
          font-size: 14px;
          min-width: 50px;
          text-align: center;
          font-weight: 500;
        }
        
        .el-button {
          background-color: transparent;
          border-color: #dcdfe6;
          color: #606266;
          
          &:hover {
            background-color: #409EFF;
            border-color: #409EFF;
            color: #ffffff;
          }
        }
      }
    }
    
    .bottom-controls {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 30px;
      padding: 16px 40px;
      background-color: #ffffff;
      border-top: 1px solid #e4e7ed;
      box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
      
      .el-button {
        width: 56px;
        height: 56px;
        font-size: 24px;
        background-color: #f5f7fa;
        border: 1px solid #dcdfe6;
        color: #606266;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        transition: all 0.3s;
        
        &:hover {
          background-color: #409EFF;
          border-color: #409EFF;
          color: #ffffff;
          box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
          transform: translateY(-2px);
        }
        
        &:active {
          transform: translateY(0);
        }
      }
    }
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
