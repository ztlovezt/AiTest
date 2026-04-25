<template>
  <div class="global-agent">
    <el-button class="floating-btn" type="primary" circle @click="visible = true">
      <el-icon><ChatDotRound /></el-icon>
    </el-button>

    <el-drawer v-model="visible" direction="rtl" size="420px" :with-header="false" class="agent-drawer">
      <div class="panel">
        <div class="panel-header">
          <div class="title-wrap">
            <div class="title">全局助手</div>
            <div class="sub">悬浮入口，支持平台文档问答 / 项目用例查询 / 数据工具</div>
          </div>
        </div>

        <div class="status-strip" :class="{ warning: !runtimeStatus.model_configured }">
          <div class="status-line">
            <span v-if="runtimeStatus.model_configured">
              模型已连接{{ runtimeStatus.active_model_name ? ` · ${runtimeStatus.active_model_name}` : '' }}
            </span>
            <span v-else>未配置模型，请到 Django Admin -> 全局助手 -> Agent模型配置 启用配置</span>
          </div>
          <div class="status-line muted">
            <span v-if="runtimeStatus.docs_ready">平台文档已就绪 · {{ runtimeStatus.docs_count }} 篇</span>
            <span v-else>平台文档未同步，文档问答可能不完整</span>
          </div>
        </div>

        <div class="messages" ref="messagesRef">
          <div v-if="!runtimeStatus.model_configured && messages.length === 0" class="empty-state">
            <div class="empty-title">全局助手还不能发送消息</div>
            <div class="empty-text">先在 Django Admin 中启用一条 Agent 模型配置，悬浮球会自动恢复可用。</div>
          </div>
          <div v-for="item in messages" :key="item.localKey" class="msg-row" :class="item.role">
            <div class="bubble">
              <div class="content" v-html="renderText(item.content)"></div>
              <div v-if="item.tool_calls?.length" class="tools">
                <div v-for="tool in item.tool_calls" :key="tool.id || tool.created_at" class="tool-item">
                  {{ tool.tool_name }} · {{ tool.status }}
                </div>
              </div>
              <div v-if="item.metadata?.citations?.length" class="citations">
                <div v-for="cite in item.metadata.citations" :key="`${cite.source_path}-${cite.chunk_index}`" class="cite-item">
                  {{ cite.title }} · {{ cite.source_path }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="input"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            :disabled="inputDisabled"
            :placeholder="inputPlaceholder"
            @keydown.enter.exact.prevent="send"
          />
          <el-button type="primary" :disabled="inputDisabled || !input.trim()" @click="send">发送</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound } from '@element-plus/icons-vue'
import { agentApi } from '@/api/agent'

const route = useRoute()

const visible = ref(false)
const input = ref('')
const sending = ref(false)
const session = ref(null)
const messages = ref([])
const messagesRef = ref(null)
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
    ? '问我：这个平台怎么用？/projects /testcases /data ...'
    : '请先到 Django Admin 配置全局助手模型'
))

const renderText = (text) =>
  (text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')

const scrollBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
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

const send = async () => {
  const text = input.value.trim()
  if (!runtimeStatus.value.model_configured) {
    ElMessage.warning('请先到 Django Admin -> 全局助手 -> Agent模型配置 启用配置')
    return
  }
  if (!text || sending.value) return
  sending.value = true
  input.value = ''
  try {
    const res = await agentApi.sendMessage({
      session_id: session.value?.session_id,
      message: text,
      route_context: routeContext(),
    })
    const payload = res.data
    session.value = payload.session
    messages.value.push({ ...payload.user_message, localKey: `u-${Date.now()}` })
    messages.value.push({ ...payload.assistant_message, localKey: `a-${Date.now()}` })
    await scrollBottom()
  } catch (error) {
    if (error.response?.data?.code === 'MODEL_NOT_CONFIGURED') {
      runtimeStatus.value.model_configured = false
    }
    ElMessage.error(error.response?.data?.error || '发送失败')
  } finally {
    sending.value = false
  }
}

watch(visible, async (open) => {
  if (!open) return
  await loadStatus()
  if (!session.value) return
  try {
    const list = await agentApi.getMessages(session.value.id)
    messages.value = list.data.map((item, index) => ({ ...item, localKey: `${item.id || index}-${index}` }))
    await scrollBottom()
  } catch (_error) {
    // ignore
  }
})
</script>

<style scoped lang="scss">
.global-agent {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 2500;
}

.floating-btn {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.2);
}

.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: 16px 14px;
  border-bottom: 1px solid var(--th-color-border, #e7eaf0);
}

.title {
  font-size: 16px;
  font-weight: 700;
}

.sub {
  font-size: 12px;
  color: #6f7785;
}

.status-strip {
  padding: 12px 14px;
  border-bottom: 1px solid var(--th-color-border, #e7eaf0);
  background: rgba(31, 122, 248, 0.06);

  &.warning {
    background: rgba(230, 162, 60, 0.12);
  }
}

.status-line {
  font-size: 12px;
  line-height: 1.5;

  &.muted {
    color: #6f7785;
  }
}

.messages {
  flex: 1;
  overflow: auto;
  padding: 14px;
  background: linear-gradient(180deg, #f7f9fc 0%, #f2f5fa 100%);
}

.empty-state {
  padding: 20px 18px;
  border: 1px dashed #d9c28c;
  border-radius: 16px;
  background: rgba(255, 248, 230, 0.9);
  color: #6f5a28;
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
  display: flex;
  margin-bottom: 10px;
  &.user {
    justify-content: flex-end;
  }
}

.bubble {
  max-width: 82%;
  border-radius: 14px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e2e6ef;
}

.msg-row.user .bubble {
  background: #1f7af8;
  color: #fff;
  border-color: #1f7af8;
}

.tools, .citations {
  margin-top: 8px;
  font-size: 12px;
}

.tool-item, .cite-item {
  opacity: 0.86;
}

.input-area {
  border-top: 1px solid var(--th-color-border, #e7eaf0);
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

@media (max-width: 768px) {
  .global-agent {
    right: 14px;
    bottom: 14px;
  }
}
</style>
