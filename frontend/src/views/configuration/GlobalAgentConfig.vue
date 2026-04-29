<template>
  <div class="global-agent-config">
    <div class="page-header">
      <h1>{{ $t('configuration.globalAgent.title') }}</h1>
      <p>{{ $t('configuration.globalAgent.description') }}</p>
    </div>

    <div v-if="forbidden" class="forbidden-state">
      <h3>{{ $t('configuration.globalAgent.forbiddenTitle') }}</h3>
      <p>{{ $t('configuration.globalAgent.forbiddenDesc') }}</p>
    </div>

    <div v-else class="main-content">
      <div class="status-section">
        <div class="section-title">{{ $t('configuration.globalAgent.runtimeTitle') }}</div>
        <div class="status-row">
          <span>{{ $t('configuration.globalAgent.modelStatus') }}</span>
          <b>{{
              runtimeStatus.model_configured ? $t('configuration.common.configured') : $t('configuration.common.notConfigured')
            }}</b>
        </div>
        <div class="status-row">
          <span>{{ $t('configuration.globalAgent.activeModel') }}</span>
          <b>{{ runtimeStatus.active_model_name || $t('configuration.common.notSet') }}</b>
        </div>
        <div class="status-row">
          <span>{{ $t('configuration.globalAgent.docsStatus') }}</span>
          <b>{{
              runtimeStatus.docs_ready ? `${$t('configuration.common.configured')} · ${runtimeStatus.docs_count}` : $t('configuration.common.notConfigured')
            }}</b>
        </div>
        <div class="status-actions">
          <el-button size="small" :loading="syncingDocs" @click="syncDocs">{{
              $t('configuration.globalAgent.syncDocs')
            }}
          </el-button>
          <el-button size="small" @click="toDebugPage">{{ $t('configuration.globalAgent.goDebug') }}</el-button>
        </div>
      </div>

      <div class="configs-section">
        <div class="section-header">
          <div class="section-title">{{ $t('configuration.globalAgent.configList') }}</div>
          <el-button type="primary" size="small" @click="openCreate">{{
              $t('configuration.globalAgent.addConfig')
            }}
          </el-button>
        </div>

        <div v-if="configs.length === 0" class="empty-state">
          {{ $t('configuration.globalAgent.empty') }}
        </div>

        <div v-else class="configs-grid">
          <div v-for="item in configs" :key="item.id" class="config-card">
            <div class="config-header">
              <div class="config-name">{{ item.name }}</div>
              <el-tag size="small" :type="item.is_active ? 'success' : 'info'">
                {{ item.is_active ? $t('configuration.common.enabled') : $t('configuration.common.disabled') }}
              </el-tag>
            </div>
            <div class="config-detail">{{ item.provider }} · {{ item.model_name }}</div>
            <div class="config-detail">{{ item.base_url || $t('configuration.common.notSet') }}</div>
            <div class="config-actions">
              <el-button size="small" @click="openEdit(item)">{{ $t('configuration.common.edit') }}</el-button>
              <el-button size="small" @click="testSaved(item)">{{
                  $t('configuration.globalAgent.testConnection')
                }}
              </el-button>
              <el-button size="small" type="danger" @click="removeConfig(item)">{{
                  $t('configuration.common.delete')
                }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showDialog"
               :title="isEditing ? $t('configuration.globalAgent.editConfig') : $t('configuration.globalAgent.addConfig')"
               width="620px">
      <el-form label-position="top">
        <el-form-item :label="$t('configuration.globalAgent.configName')">
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item :label="$t('configuration.globalAgent.provider')">
          <el-select v-model="form.provider" style="width: 100%">
            <el-option value="openai_compatible" label="OpenAI Compatible"/>
            <el-option value="custom" :label="$t('configuration.globalAgent.customProvider')"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('configuration.globalAgent.modelName')">
          <el-input v-model="form.model_name"/>
        </el-form-item>
        <el-form-item :label="$t('configuration.globalAgent.baseUrl')">
          <el-input v-model="form.base_url"/>
        </el-form-item>
        <el-form-item :label="$t('configuration.globalAgent.apiKey')">
          <el-input v-model="form.api_key" type="password"
                    :placeholder="isEditing ? $t('configuration.globalAgent.apiKeyEditTip') : ''"/>
        </el-form-item>
        <el-form-item :label="$t('configuration.globalAgent.maxTokens')">
          <el-input-number v-model="form.max_tokens" :min="1" :max="32768"/>
        </el-form-item>
        <el-form-item :label="$t('configuration.globalAgent.temperature')">
          <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1"/>
        </el-form-item>
        <el-form-item :label="$t('configuration.globalAgent.topP')">
          <el-input-number v-model="form.top_p" :min="0" :max="1" :step="0.1"/>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.is_active">{{ $t('configuration.globalAgent.enableConfig') }}</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">{{ $t('configuration.common.cancel') }}</el-button>
        <el-button :loading="testingPreview" @click="testPreview">{{
            $t('configuration.globalAgent.testConnection')
          }}
        </el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ $t('configuration.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {onMounted, ref} from 'vue'
import {useRouter} from 'vue-router'
import {ElMessage, ElMessageBox} from 'element-plus'
import {agentApi} from '@/api/agent'

const router = useRouter()

const forbidden = ref(false)
const syncingDocs = ref(false)
const saving = ref(false)
const testingPreview = ref(false)
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

const runtimeStatus = ref({
  model_configured: false,
  active_model_name: '',
  docs_ready: false,
  docs_count: 0,
})

const configs = ref([])

const defaultForm = () => ({
  name: '',
  provider: 'openai_compatible',
  model_name: '',
  base_url: '',
  api_key: '',
  max_tokens: 2048,
  temperature: 0.3,
  top_p: 0.9,
  is_active: true,
})
const form = ref(defaultForm())

const toDebugPage = () => router.push('/agent')

const loadStatus = async () => {
  const res = await agentApi.getStatus()
  runtimeStatus.value = res.data || runtimeStatus.value
}

const loadConfigs = async () => {
  try {
    const res = await agentApi.listConfigs()
    configs.value = Array.isArray(res.data) ? res.data : (res.data?.results || [])
    forbidden.value = false
  } catch (error) {
    if (error.response?.status === 403) {
      forbidden.value = true
      return
    }
    ElMessage.error(error.response?.data?.error || '加载配置失败')
  }
}

const openCreate = () => {
  isEditing.value = false
  editingId.value = null
  form.value = defaultForm()
  showDialog.value = true
}

const openEdit = (item) => {
  isEditing.value = true
  editingId.value = item.id
  form.value = {
    name: item.name,
    provider: item.provider,
    model_name: item.model_name,
    base_url: item.base_url,
    api_key: item.api_key_masked || '',
    max_tokens: item.max_tokens,
    temperature: item.temperature,
    top_p: item.top_p,
    is_active: item.is_active,
  }
  showDialog.value = true
}

const syncDocs = async () => {
  syncingDocs.value = true
  try {
    await agentApi.syncBuiltinDocs()
    await loadStatus()
    ElMessage.success('文档同步完成')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '文档同步失败')
  } finally {
    syncingDocs.value = false
  }
}

const testPreview = async () => {
  testingPreview.value = true
  try {
    await agentApi.testConfigConnectionPreview({...form.value})
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || error.response?.data?.error || '连接测试失败')
  } finally {
    testingPreview.value = false
  }
}

const testSaved = async (item) => {
  try {
    await agentApi.testConfigConnection(item.id)
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || error.response?.data?.error || '连接测试失败')
  }
}

const save = async () => {
  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      await agentApi.updateConfig(editingId.value, {...form.value})
      ElMessage.success('配置更新成功')
    } else {
      await agentApi.createConfig({...form.value})
      ElMessage.success('配置创建成功')
    }
    showDialog.value = false
    await loadConfigs()
    await loadStatus()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeConfig = async (item) => {
  try {
    await ElMessageBox.confirm(`确定删除配置「${item.name}」吗？`, '删除确认', {type: 'warning'})
    await agentApi.deleteConfig(item.id)
    ElMessage.success('删除成功')
    await loadConfigs()
    await loadStatus()
  } catch (error) {
    if (error === 'cancel') return
    ElMessage.error(error.response?.data?.error || '删除失败')
  }
}

onMounted(async () => {
  await loadStatus()
  await loadConfigs()
})
</script>

<style scoped lang="scss">
.global-agent-config {
  padding: 16px;
}

.page-header h1 {
  margin: 0;
  font-size: 20px;
}

.page-header p {
  margin-top: 6px;
  color: #6f7785;
}

.forbidden-state,
.status-section,
.configs-section {
  margin-top: 14px;
  border: 1px solid #dbe1ec;
  border-radius: 10px;
  background: #fff;
  padding: 14px;
}

.section-title {
  font-weight: 700;
  margin-bottom: 10px;
}

.status-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
}

.status-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.configs-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 10px;
}

.config-card {
  border: 1px solid #e7ebf3;
  border-radius: 8px;
  padding: 10px;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-name {
  font-weight: 700;
}

.config-detail {
  margin-top: 6px;
  font-size: 12px;
  color: #5a6475;
  word-break: break-all;
}

.config-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.empty-state {
  margin-top: 10px;
  color: #6f7785;
}
</style>
