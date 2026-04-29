<template>
  <div class="assistant-layout">
    <!-- 左侧侧边栏 -->
    <div class="sidebar">
      <!-- Logo区域与面包屑 -->
      <div class="logo-area-nav" @click="router.push('/home')" style="cursor: pointer">
        <img src="@/assets/images/logo.svg" alt="TestHub" class="nav-logo" />
      </div>

      <div class="new-chat-btn-wrapper">
        <el-button type="primary" class="new-chat-btn" @click="startNewChat" :icon="Plus">
          {{ $t('assistant.newChat') }}
        </el-button>
      </div>
      
      <div class="history-list">
        <div class="history-label">{{ $t('assistant.historyChat') }}</div>
        <div class="session-scroll-area">
          <div 
            v-for="session in historySessionsDescending" 
            :key="session.id"
            :class="['session-item', { active: currentSession?.id === session.id }]"
            @click="switchToSession(session)"
          >
            <div class="session-title-wrapper">
              <el-icon class="chat-icon"><ChatDotRound /></el-icon>
              <span class="session-title" :title="session.title">{{ session.title || $t('assistant.newChat') }}</span>
            </div>
            <div class="session-actions" @click.stop>
              <el-popconfirm :title="$t('assistant.deleteSessionConfirm')" @confirm="deleteSession(session.id)">
                <template #reference>
                  <el-icon class="delete-icon"><Delete /></el-icon>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>
      </div>
      
      <div class="user-profile">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <el-avatar :size="32" :icon="UserFilled" />
            <span class="username">{{ userStore.user?.username || $t('assistant.user') }}</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="home">{{ $t('assistant.goHome') }}</el-dropdown-item>
              <el-dropdown-item command="logout" divided>{{ $t('assistant.logout') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 右侧主内容区 -->
    <div class="main-content">
      <!-- 顶部面包屑区域 -->
      <div class="header-content">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/home' }">{{ $t('nav.home') || '首页' }}</el-breadcrumb-item>
          <el-breadcrumb-item>{{ $t('assistant.title') || 'AI评测师' }}</el-breadcrumb-item>
        </el-breadcrumb>
      </div>

      <!-- 场景1：新会话（居中输入框） -->
      <div v-if="isNewChatMode" class="welcome-screen">
        <div class="welcome-content">
          <div class="logo-area">
            <div class="logo-circle">
              <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="1em" height="1em"><path fill="currentColor" d="M848.5 352.4h-54.7V256c0-35.3-28.7-64-64-64H294.2c-35.3 0-64 28.7-64 64v96.4h-54.7c-35.3 0-64 28.7-64 64v320c0 35.3 28.7 64 64 64h54.7V832c0 35.3 28.7 64 64 64h435.6c35.3 0 64-28.7 64-64v-31.6h54.7c35.3 0 64-28.7 64-64v-320c0-35.3-28.7-64-64-64zM294.2 256h435.6v96.4H294.2V256zm435.6 576H294.2v-31.6h435.6V832zm54.7-95.6H239.5v-320h544.9v320z"></path><path fill="currentColor" d="M375.4 512.2a64 64 0 1 0 128 0 64 64 0 1 0-128 0zm273.2 0a64 64 0 1 0 128 0 64 64 0 1 0-128 0z"></path></svg></el-icon>
            </div>
            <h1>{{ $t('assistant.title') }}</h1>
            <p>{{ $t('assistant.subtitle') }}</p>
          </div>
          
          <div class="center-input-wrapper">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              :placeholder="$t('assistant.inputPlaceholder')"
              class="center-input"
              resize="none"
              @keydown.enter.exact.prevent="handleEnter"
            />
            <div class="input-actions">
              <el-button 
                type="primary" 
                circle 
                :icon="Promotion" 
                :disabled="!inputMessage.trim()"
                @click="sendMessage"
              />
            </div>
          </div>
          
          <div class="suggestion-chips">
            <div class="chip" @click="useSuggestion($t('assistant.suggestions.apiTestQuestion'))">{{ $t('assistant.suggestions.apiTest') }}</div>
            <div class="chip" @click="useSuggestion($t('assistant.suggestions.performancePlanQuestion'))">{{ $t('assistant.suggestions.performancePlan') }}</div>
            <div class="chip" @click="useSuggestion($t('assistant.suggestions.testTheoryQuestion'))">{{ $t('assistant.suggestions.testTheory') }}</div>
            <div class="chip" @click="useSuggestion($t('assistant.suggestions.automationDebugQuestion'))">{{ $t('assistant.suggestions.automationDebug') }}</div>
          </div>
        </div>
      </div>

      <!-- 场景2：对话界面 -->
      <div v-else class="chat-screen">
        <div class="chat-header">
          <span class="chat-title">{{ currentSession?.title || $t('assistant.newChat') }}</span>
          <span class="chat-time" v-if="currentSession">{{ formatDate(currentSession.updated_at) }}</span>
        </div>
        
        <div class="messages-container" ref="messagesContainer">
          <div 
            v-for="(message, index) in messages" 
            :key="message.id || index"
            :class="['message-row', message.role]"
          >
            <div class="avatar">
              <el-avatar v-if="message.role === 'user'" :size="36" :icon="User" class="user-avatar" />
              <div v-else class="ai-avatar-wrapper">
                <el-avatar :size="36" class="ai-avatar">
                  <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="1em" height="1em"><path fill="currentColor" d="M848.5 352.4h-54.7V256c0-35.3-28.7-64-64-64H294.2c-35.3 0-64 28.7-64 64v96.4h-54.7c-35.3 0-64 28.7-64 64v320c0 35.3 28.7 64 64 64h54.7V832c0 35.3 28.7 64 64 64h435.6c35.3 0 64-28.7 64-64v-31.6h54.7c35.3 0 64-28.7 64-64v-320c0-35.3-28.7-64-64-64zM294.2 256h435.6v96.4H294.2V256zm435.6 576H294.2v-31.6h435.6V832zm54.7-95.6H239.5v-320h544.9v320z"></path><path fill="currentColor" d="M375.4 512.2a64 64 0 1 0 128 0 64 64 0 1 0-128 0zm273.2 0a64 64 0 1 0 128 0 64 64 0 1 0-128 0z"></path></svg></el-icon>
                </el-avatar>
              </div>
            </div>
            <div class="message-bubble">
              <div class="message-content" v-html="formatMessageContent(message.content)"></div>
              <div class="message-status" v-if="message.isPending">
                <el-icon class="is-loading"><Loading /></el-icon> {{ $t('assistant.thinking') }}
              </div>
            </div>
          </div>
          
          <!-- 底部占位，确保滚动到底部 -->
          <div style="height: 20px;"></div>
        </div>

        <div class="chat-footer">
          <div class="input-box">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="1"
              :autosize="{ minRows: 1, maxRows: 5 }"
              :placeholder="$t('assistant.chatInputPlaceholder')"
              resize="none"
              @keydown.enter.exact.prevent="handleEnter"
            />
            <el-button 
              type="primary" 
              class="send-btn"
              :disabled="!inputMessage.trim() || sending"
              @click="sendMessage"
            >
              <el-icon><Promotion /></el-icon>
            </el-button>
          </div>
          <div class="footer-tip">{{ $t('assistant.aiDisclaimer') }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, ChatDotRound, User, Cpu, Promotion, Loading, UserFilled, ArrowDown } from '@element-plus/icons-vue'
import api from '@/utils/api'

const router = useRouter()
const userStore = useUserStore()
const { t, locale } = useI18n()

// 状态
const historySessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const inputMessage = ref('')
const sending = ref(false)
const messagesContainer = ref(null)

const handleCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'home') {
    router.push('/home')
  }
}

const handleLogout = () => {
  ElMessageBox.confirm(t('assistant.logoutConfirm'), t('assistant.logoutTitle'), {
    confirmButtonText: t('assistant.confirm'),
    cancelButtonText: t('assistant.cancel'),
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
    ElMessage.success(t('assistant.loggedOut'))
  }).catch(() => {})
}

// 计算属性
const historySessionsDescending = computed(() => {
  return [...historySessions.value].sort((a, b) => 
    new Date(b.updated_at) - new Date(a.updated_at)
  )
})

const isNewChatMode = computed(() => {
  // 如果没有当前会话，或者当前会话没有消息且没有ID（临时会话），则显示新会话模式
  return !currentSession.value || (!currentSession.value.id && messages.value.length === 0)
})

// 方法
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const localeCode = locale.value === 'zh-cn' ? 'zh-CN' : 'en-US'
  // 如果是今天，只显示时间
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString(localeCode, { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString(localeCode, { month: '2-digit', day: '2-digit' })
}

const formatMessageContent = (content) => {
  if (!content) return ''
  // 简单的 markdown 处理，实际项目中建议使用 markdown-it
  return content
    .replace(/\n/g, '<br>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 开启新会话
const startNewChat = () => {
  currentSession.value = { title: t('assistant.newChat') } // 临时会话对象
  messages.value = []
  inputMessage.value = ''
}

// 切换会话
const switchToSession = async (session) => {
  if (currentSession.value?.id === session.id) return
  
  try {
    currentSession.value = { ...session }
    const response = await api.get(`/assistant/sessions/${session.id}/messages/`)
    messages.value = response.data
    scrollToBottom()
  } catch (error) {
    console.error('Load messages failed:', error)
    ElMessage.error(t('assistant.messages.loadMessageFailed'))
  }
}

// 删除会话
const deleteSession = async (sessionId) => {
  try {
    await api.delete(`/assistant/sessions/${sessionId}/`)
    historySessions.value = historySessions.value.filter(s => s.id !== sessionId)
    
    if (currentSession.value?.id === sessionId) {
      startNewChat()
    }
    ElMessage.success(t('assistant.messages.sessionDeleted'))
  } catch (error) {
    console.error('Delete session failed:', error)
    ElMessage.error(t('assistant.messages.deleteSessionFailed'))
  }
}

// 使用建议
const useSuggestion = (text) => {
  inputMessage.value = text
  sendMessage()
}

// 处理回车发送
const handleEnter = (e) => {
  if (!e.shiftKey && !sending.value) {
    sendMessage()
  }
}

// 发送消息
const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || sending.value) return
  
  inputMessage.value = ''
  sending.value = true
  
  // 1. 立即上屏用户消息
  const tempUserMsg = {
    role: 'user',
    content: text,
    created_at: new Date().toISOString()
  }
  messages.value.push(tempUserMsg)
  
  // 2. 添加一个临时的"思考中"消息
  const tempAiMsg = {
    role: 'assistant',
    content: '',
    isPending: true
  }
  messages.value.push(tempAiMsg)
  scrollToBottom()
  
  try {
    // 如果是新会话（没有ID），先创建会话
    let sessionId = currentSession.value?.id
    let isFirstMessage = false
    
    if (!sessionId) {
      isFirstMessage = true
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`
      // 智能生成标题（取前10个字）
      const title = text.length > 10 ? text.substring(0, 10) + '...' : text
      
      const sessionRes = await api.post('/assistant/sessions/', {
        session_id: newSessionId,
        title: title
      })
      
      currentSession.value = sessionRes.data
      sessionId = currentSession.value.session_id // 注意：后端返回的是对象，这里需要用 session_id 字段
      
      // 立即添加到历史列表
      historySessions.value.unshift(currentSession.value)
    } else {
      // 如果是已有会话，使用 session_id 字段
      sessionId = currentSession.value.session_id
    }
    
    // 3. 发送请求
    const response = await api.post('/assistant/chat/send_message/', {
      session_id: sessionId,
      message: text
    }, {
      timeout: 60000
    })
    
    // 4. 替换临时消息为真实消息
    messages.value.pop() // 移除思考中
    messages.value.pop() // 移除临时用户消息（因为后端返回了完整的用户消息对象）
    
    messages.value.push(response.data.user_message)
    messages.value.push(response.data.assistant_message)
    
    // 更新会话的 conversation_id
    if (response.data.conversation_id && currentSession.value) {
      currentSession.value.conversation_id = response.data.conversation_id
    }
    
    // 如果是第一次对话，更新历史列表中的会话信息（比如 updated_at）
    if (!isFirstMessage) {
      const index = historySessions.value.findIndex(s => s.id === currentSession.value.id)
      if (index !== -1) {
        historySessions.value[index] = { ...currentSession.value, updated_at: new Date().toISOString() }
        // 重新排序（移到最前）
        const updatedSession = historySessions.value.splice(index, 1)[0]
        historySessions.value.unshift(updatedSession)
      }
    }
    
  } catch (error) {
    console.error('Send failed:', error)
    // 移除临时消息，显示错误
    messages.value.pop() // 移除思考中
    ElMessage.error(error.response?.data?.error || t('assistant.messages.sendFailed'))
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

// 加载历史
const loadHistory = async () => {
  try {
    const response = await api.get('/assistant/sessions/')
    historySessions.value = response.data.results || response.data || []
  } catch (error) {
    console.error('Load history failed:', error)
  }
}

onMounted(() => {
  loadHistory()
  startNewChat()
})
</script>

<style scoped lang="scss">
.assistant-layout {
  display: flex;
  height: 100vh;
  background: var(--th-color-surface);
  overflow: hidden;
}

/* 左侧侧边栏 */
.sidebar {
  width: 260px;
  background: var(--th-color-surface); /* 浅色背景 */
  border-right: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  color: var(--el-text-color-primary);

  .logo-area-nav {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--th-sidebar-bg);
    border-bottom: 1px solid var(--th-sidebar-border);
    flex-shrink: 0;
    
    .nav-logo {
      width: 100%;
      height: 100%;
      object-fit: fill;
    }
  }
  
  .new-chat-btn-wrapper {
    padding: 20px;
    
    .new-chat-btn {
      width: 100%;
      height: 40px;
      border-radius: 4px;
      font-size: 14px;
      background: var(--el-color-primary-light-9);
      border-color: var(--el-color-primary-light-8);
      color: var(--th-color-primary);
      
      &:hover {
        background: var(--th-color-primary);
        border-color: var(--th-color-primary);
        color: white;
      }
    }
  }
  
  .history-list {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    
    .history-label {
      padding: 0 20px 10px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
    
    .session-scroll-area {
      flex: 1;
      overflow-y: auto;
      padding: 0 10px;
      
      &::-webkit-scrollbar {
        width: 4px;
      }
      &::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.1);
        border-radius: 2px;
      }
    }
    
    .session-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      margin-bottom: 4px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
      color: var(--el-text-color-regular);
      
      &:hover {
        background: var(--el-fill-color-light);
        color: var(--el-text-color-primary);
        
        .session-actions {
          opacity: 1;
        }
      }
      
      &.active {
        background: var(--el-color-primary-light-9);
        color: var(--th-color-primary);
      }
      
      .session-title-wrapper {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
        overflow: hidden;
        
        .chat-icon {
          font-size: 16px;
        }
        
        .session-title {
          font-size: 14px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }
      
      .session-actions {
        opacity: 0;
        transition: opacity 0.2s;
        
        .delete-icon {
          font-size: 14px;
          color: var(--el-text-color-secondary);
          &:hover {
            color: #ff4d4f;
          }
        }
      }
    }
  }
  
  .user-profile {
    padding: 16px;
    border-top: 1px solid var(--el-border-color-light);
    
    .user-info {
      display: flex;
      align-items: center;
      cursor: pointer;
      padding: 8px;
      border-radius: 4px;
      transition: all 0.2s;
      
      &:hover {
        background: var(--el-fill-color-light);
      }
      
      .username {
        margin: 0 8px;
        font-size: 14px;
        color: var(--el-text-color-primary);
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      
      .el-icon {
        color: var(--el-text-color-secondary);
      }
    }
  }
}

/* 右侧主内容区 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  background: var(--th-color-surface);
  overflow: hidden;

  .header-content {
    height: 60px;
    display: flex;
    align-items: center;
    padding: 0 20px;
    background: var(--th-header-bg);
    border-bottom: 1px solid var(--th-header-border);
    box-shadow: var(--th-header-shadow);
    backdrop-filter: blur(10px);
    flex-shrink: 0;

    :deep(.el-breadcrumb) {
      font-size: 14px;
    }
  }
}

/* 场景1：欢迎页（新会话） */
.welcome-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-bottom: 100px;
  
  .welcome-content {
    width: 100%;
    max-width: 800px;
    padding: 0 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  
  .logo-area {
    text-align: center;
    margin-bottom: 40px;
    
    .logo-circle {
      width: 80px;
      height: 80px;
      background: linear-gradient(135deg, var(--th-color-info) 0%, #00f2fe 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 20px;
      box-shadow: 0 10px 20px rgba(79, 172, 254, 0.3);
      
      .el-icon {
        font-size: 40px;
        color: white;
      }
    }
    
    h1 {
      font-size: 28px;
      color: #303133;
      margin: 0 0 10px;
    }
    
    p {
      color: #909399;
      font-size: 16px;
      margin: 0;
    }
  }
  
  .center-input-wrapper {
    width: 100%;
    position: relative;
    margin-bottom: 30px;
    
    .center-input {
      :deep(.el-textarea__inner) {
        border-radius: 16px;
        padding: 16px 50px 16px 20px;
        font-size: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        border: 1px solid #e4e7ed;
        transition: all 0.3s;
        
        &:focus {
          box-shadow: 0 4px 20px rgba(64, 158, 255, 0.15);
          border-color: var(--th-color-primary);
        }
      }
    }
    
    .input-actions {
      position: absolute;
      right: 10px;
      bottom: 10px;
    }
  }
  
  .suggestion-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    
    .chip {
      padding: 8px 16px;
      background: var(--th-color-surface-muted);
      border-radius: 20px;
      font-size: 14px;
      color: #606266;
      cursor: pointer;
      transition: all 0.2s;
      
      &:hover {
        background: #e6f1fc;
        color: var(--th-color-primary);
      }
    }
  }
}

/* 场景2：对话页 */
.chat-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  
  .chat-header {
    height: 60px;
    border-bottom: 1px solid #f0f2f5;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    flex-shrink: 0;
    
    .chat-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
    
    .chat-time {
      font-size: 12px;
      color: #909399;
    }
  }
  
  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    background: var(--th-color-surface);
    
    .message-row {
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      
      &.user {
        flex-direction: row-reverse;
        
        .message-bubble {
          background: var(--th-color-primary);
          color: white;
          border-radius: 12px 12px 0 12px;
          
          :deep(pre) {
            background: rgba(0, 0, 0, 0.1);
          }
          
          :deep(code) {
            background: rgba(0, 0, 0, 0.1);
            color: var(--th-color-surface);
          }
        }
      }
      
      &.assistant {
        .message-bubble {
          background: var(--th-color-surface-muted);
          color: #303133;
          border-radius: 12px 12px 12px 0;
        }
      }
      
      .avatar {
        flex-shrink: 0;
        margin-top: 2px;
        
        .user-avatar {
          background: #c0c4cc;
        }
        
        .ai-avatar {
          background: linear-gradient(135deg, var(--th-color-info) 0%, #00f2fe 100%);
        }
      }
      
      .message-bubble {
        max-width: 70%;
        padding: 12px 16px;
        font-size: 15px;
        line-height: 1.6;
        position: relative;
        
        .message-content {
          word-wrap: break-word;
          
          :deep(p) {
            margin: 0 0 8px 0;
            &:last-child { margin: 0; }
          }
          
          :deep(pre) {
            background: #282c34;
            color: #abb2bf;
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
          }
          
          :deep(code) {
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
          }
        }
        
        .message-status {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: #909399;
          
          .is-loading {
            animation: rotating 2s linear infinite;
          }
        }
      }
    }
  }
  
  .chat-footer {
    padding: 20px 24px;
    border-top: 1px solid #f0f2f5;
    background: var(--th-color-surface);
    
    .input-box {
      position: relative;
      border: 1px solid #e4e7ed;
      border-radius: 12px;
      padding: 8px;
      background: var(--th-color-surface);
      transition: all 0.3s;
      
      &:focus-within {
        border-color: var(--th-color-primary);
        box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
      }
      
      :deep(.el-textarea__inner) {
        border: none;
        box-shadow: none;
        padding: 8px 50px 8px 8px;
        background: transparent;
      }
      
      .send-btn {
        position: absolute;
        right: 8px;
        bottom: 8px;
        width: 32px;
        height: 32px;
        padding: 0;
        border-radius: 8px;
      }
    }
    
    .footer-tip {
      text-align: center;
      font-size: 12px;
      color: #c0c4cc;
      margin-top: 8px;
    }
  }
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>