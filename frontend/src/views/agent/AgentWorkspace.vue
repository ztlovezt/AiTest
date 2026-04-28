<template>
  <div class="agent-workspace">
    <aside class="sessions">
      <div class="header">
        <div>
          <div class="title">全局助手调试台</div>
          <div class="sub">内部调试入口（会话、文档同步、模型状态）</div>
        </div>
        <el-button size="small" @click="newSession">新会话</el-button>
      </div>
      <div class="list">
        <div
          v-for="item in sessions"
          :key="item.id"
          class="session-item"
          :class="{ active: activeSession?.id === item.id }"
          @click="selectSession(item)"
        >
          <div class="name">{{ item.title || '新会话' }}</div>
          <el-button link type="danger" @click.stop="removeSession(item)">删除</el-button>
        </div>
      </div>
    </aside>
    <main class="chat">
      <div class="chat-head">
        <div>
          <div class="chat-title">{{ activeSession?.title || '新会话' }}</div>
          <div class="chat-sub">用于联调与排障；日常使用请走全站悬浮球</div>
        </div>
        <el-button link @click="syncDocs">同步平台文档</el-button>
      </div>
      <div class="status-banner" :class="{ warning: !runtimeStatus.model_configured }">
        <span v-if="runtimeStatus.model_configured">
          模型已连接{{ runtimeStatus.active_model_name ? ` · ${runtimeStatus.active_model_name}` : '' }}
        </span>
        <span v-else>未配置模型，请到 配置中心 -> 全局助手配置 启用配置</span>
        <span class="divider">|</span>
        <span v-if="runtimeStatus.docs_ready">平台文档已就绪 · {{ runtimeStatus.docs_count }} 篇</span>
        <span v-else>平台文档未同步</span>
      </div>
      <div class="messages" ref="messagesRef">
        <div v-if="loadingMessages" class="empty-state">
          <div class="empty-title">正在加载消息</div>
          <div class="empty-text">请稍候...</div>
        </div>
        <div v-else-if="messagesError" class="empty-state">
          <div class="empty-title">消息加载失败</div>
          <div class="empty-text">{{ messagesError }}</div>
        </div>
        <div v-else-if="!runtimeStatus.model_configured && messages.length === 0" class="empty-state">
          <div class="empty-title">当前调试页不可发送消息</div>
          <div class="empty-text">先在配置中心启用全局助手模型配置，悬浮球和调试页都会恢复可用。</div>
        </div>
        <div v-else-if="!runtimeStatus.docs_ready && messages.length === 0" class="empty-state">
          <div class="empty-title">平台文档未同步</div>
          <div class="empty-text">可继续调试，但文档问答完整性受影响。点击右上角可同步文档。</div>
        </div>
        <div v-else-if="messages.length === 0" class="empty-state">
          <div class="empty-title">暂无消息</div>
          <div class="empty-text">输入问题后开始对话。</div>
        </div>
        <div v-for="item in messages" :key="item.localKey" class="msg-row" :class="item.role">
          <div class="bubble">
            <div class="content" v-html="renderText(item.content)"></div>
            <div v-if="item.tool_calls?.length" class="tools">
              <div v-for="tool in item.tool_calls" :key="tool.id || tool.created_at">
                {{ tool.tool_name }} · {{ tool.status }}
              </div>
            </div>
            <div v-if="item.metadata?.citations?.length" class="citations">
              <div
                  v-for="cite in item.metadata.citations"
                  :key="`${cite.source_path}-${cite.chunk_index}`"
                  class="cite-item"
              >
                <div class="cite-title">{{ cite.title }}</div>
                <div class="cite-path">{{ cite.source_path }}</div>
                <div class="cite-snippet">{{ cite.content || '' }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="composer">
        <el-input
          v-model="input"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          :disabled="inputDisabled"
          :placeholder="inputPlaceholder"
          @keydown.enter.exact.prevent="send"
        />
        <el-button type="primary" :loading="sending" :disabled="inputDisabled || !input.trim()" @click="send">发送
        </el-button>
      </div>
    </main>
  </div>
</template>

<script setup>
import {computed, nextTick, onMounted, ref} from 'vue'
import {useRoute} from 'vue-router'
import {ElMessage} from 'element-plus'
import {agentApi} from '@/api/agent'

const route = useRoute()
const sessions = ref([])
const activeSession = ref(null)
const messages = ref([])
const input = ref('')
const sending = ref(false)
const messagesRef = ref(null)
const loadingMessages = ref(false)
const messagesError = ref('')
const runtimeStatus = ref({
  model_configured: false,
  active_model_name: '',
  docs_ready: false,
  docs_count: 0,
})

const routeContext = () => ({
  module: (route.path.split('/')[1] || 'home'),
  route_name: route.name || '',
  path: route.path,
  params: route.params || {},
  query: route.query || {},
})

const inputDisabled = computed(() => sending.value || !runtimeStatus.value.model_configured)
const inputPlaceholder = computed(() => (
  runtimeStatus.value.model_configured
    ? '输入你的问题，支持 /projects /testcases /docs /data ...'
      : '请先到 配置中心 -> 全局助手配置'
))

const renderText = (text) =>
  (text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')

const scrollBottom = async () => {
  await nextTick()
  if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
}

const loadSessions = async () => {
  const res = await agentApi.listSessions()
  sessions.value = res.data?.results ?? res.data
}

const loadStatus = async () => {
  try {
    const res = await agentApi.getStatus()
    runtimeStatus.value = res.data
  } catch (_error) {
    runtimeStatus.value = {
      model_configured: false,
      active_model_name: '',
      docs_ready: false,
      docs_count: 0,
    }
  }
}

const selectSession = async (session) => {
  activeSession.value = session
  loadingMessages.value = true
  messagesError.value = ''
  try {
    const res = await agentApi.getMessages(session.id)
    messages.value = res.data.map((item, index) => ({...item, localKey: `${item.id || index}-${index}`}))
    await scrollBottom()
  } catch (error) {
    messages.value = []
    messagesError.value = error.response?.data?.error || '获取消息失败'
  } finally {
    loadingMessages.value = false
  }
}

const newSession = () => {
  activeSession.value = null
  messages.value = []
}

const removeSession = async (item) => {
  await agentApi.deleteSession(item.id)
  if (activeSession.value?.id === item.id) {
    newSession()
  }
  await loadSessions()
}

const send = async () => {
  const text = input.value.trim()
  const draft = text
  if (!runtimeStatus.value.model_configured) {
    ElMessage.warning('请先到 配置中心 -> 全局助手配置 启用配置')
    return
  }
  if (!text || sending.value) return
  sending.value = true
  input.value = ''
  try {
    const res = await agentApi.sendMessage({
      session_id: activeSession.value?.session_id,
      message: text,
      route_context: routeContext(),
    })
    const payload = res.data
    activeSession.value = payload.session
    messages.value.push({ ...payload.user_message, localKey: `u-${Date.now()}` })
    messages.value.push({ ...payload.assistant_message, localKey: `a-${Date.now()}` })
    await loadSessions()
    await scrollBottom()
  } catch (error) {
    input.value = draft
    if (error.response?.data?.code === 'MODEL_NOT_CONFIGURED') {
      runtimeStatus.value.model_configured = false
    }
    ElMessage.error(error.response?.data?.error || '发送失败')
  } finally {
    sending.value = false
  }
}

const syncDocs = async () => {
  try {
    const res = await agentApi.syncBuiltinDocs()
    await loadStatus()
    ElMessage.success(`同步完成: created=${res.data.created} updated=${res.data.updated}`)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '同步失败')
  }
}

onMounted(async () => {
  await loadStatus()
  await loadSessions()
})
</script>

<style scoped lang="scss">
.agent-workspace {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100vh;
  background: radial-gradient(1200px 700px at 10% -20%, rgba(30, 122, 248, 0.14), transparent 60%), #f5f7fb;
}

.sessions {
  border-right: 1px solid #dbe1ec;
  background: #ffffff;
  .header {
    padding: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    .title {
      font-size: 16px;
      font-weight: 700;
    }
    .sub {
      font-size: 12px;
      color: #6f7785;
      margin-top: 4px;
    }
  }
  .list {
    overflow: auto;
    height: calc(100vh - 56px);
  }
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #edf1f7;
  cursor: pointer;
  &.active {
    background: rgba(31, 122, 248, 0.09);
  }
  .name {
    max-width: 170px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.chat {
  display: flex;
  flex-direction: column;
}

.chat-head {
  padding: 14px;
  border-bottom: 1px solid #dbe1ec;
  display: flex;
  justify-content: space-between;
}

.chat-title {
  font-weight: 700;
}

.chat-sub {
  margin-top: 4px;
  color: #6f7785;
  font-size: 12px;
}

.status-banner {
  padding: 12px 14px;
  background: rgba(31, 122, 248, 0.07);
  border-bottom: 1px solid #dbe1ec;
  font-size: 12px;

  &.warning {
    background: rgba(230, 162, 60, 0.12);
    color: #6f5a28;
  }
}

.divider {
  margin: 0 8px;
  opacity: 0.45;
}

.messages {
  flex: 1;
  overflow: auto;
  padding: 14px;
}

.empty-state {
  padding: 20px 18px;
  border: 1px dashed #d9c28c;
  border-radius: 16px;
  background: rgba(255, 248, 230, 0.9);
  color: #6f5a28;
  margin-bottom: 14px;
}

.empty-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 6px;
}

.empty-text {
  font-size: 12px;
  line-height: 1.6;
}

.msg-row {
  margin-bottom: 10px;
  display: flex;
  &.user {
    justify-content: flex-end;
  }
}

.bubble {
  max-width: 78%;
  background: #fff;
  border: 1px solid #dbe1ec;
  border-radius: 12px;
  padding: 10px;
}

.msg-row.user .bubble {
  background: #1f7af8;
  color: #fff;
  border-color: #1f7af8;
}

.tools,
.citations {
  margin-top: 8px;
  font-size: 12px;
}

.cite-item {
  border-left: 2px solid #c7d6f7;
  padding-left: 8px;
  margin-bottom: 6px;
}

.cite-title {
  font-weight: 600;
}

.cite-path,
.cite-snippet {
  font-size: 11px;
  line-height: 1.45;
  opacity: 0.86;
}

.composer {
  border-top: 1px solid #dbe1ec;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

@media (max-width: 960px) {
  .agent-workspace {
    grid-template-columns: 1fr;
  }
  .sessions {
    display: none;
  }
}
</style>
