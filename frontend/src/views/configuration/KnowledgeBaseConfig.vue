<template>
  <div class="knowledge-base-config-container">
    <div class="page-header">
      <h1>{{ $t('configuration.knowledgeBase.title') }}</h1>
      <p>{{ $t('configuration.knowledgeBase.description') }}</p>
    </div>

    <div class="config-content">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>{{ $t('configuration.knowledgeBase.apiConfig') }}</span>
            <el-tag v-if="currentConfig?.configured" type="success">{{ $t('configuration.common.configured') }}</el-tag>
            <el-tag v-else type="info">{{ $t('configuration.common.notConfigured') }}</el-tag>
          </div>
        </template>

        <el-form :model="form" ref="configForm" label-width="160px" label-position="right">
          
          <!-- Embedding 模型配置 -->
          <div class="section-title">
            <el-icon><DataAnalysis /></el-icon>
            {{ $t('configuration.knowledgeBase.embeddingTitle') }}
          </div>
          <el-form-item :label="$t('configuration.aiMode.apiKey')" prop="embedding_api_key">
            <el-input
              v-model="form.embedding_api_key"
              type="password"
              :placeholder="currentConfig?.configured ? $t('configuration.aiMode.apiKeyPlaceholderEdit') : $t('configuration.aiMode.apiKeyPlaceholder')"
              show-password
              clearable>
              <template #prepend><el-icon><Key /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item :label="$t('configuration.aiMode.baseUrl')" prop="embedding_base_url">
            <el-input v-model="form.embedding_base_url" placeholder="如: https://dashscope.aliyuncs.com/compatible-mode/v1" clearable>
              <template #prepend><el-icon><Link /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item :label="$t('configuration.knowledgeBase.modelName')" prop="embedding_model">
            <el-input v-model="form.embedding_model" placeholder="默认: text-embedding-v3" clearable></el-input>
          </el-form-item>

          <el-divider border-style="dashed" />

          <!-- Refiner 模型配置 -->
          <div class="section-title">
            <el-icon><EditPen /></el-icon>
            {{ $t('configuration.knowledgeBase.refinerTitle') }}
          </div>
          <el-form-item :label="$t('configuration.aiMode.apiKey')" prop="refiner_api_key">
            <el-input
              v-model="form.refiner_api_key"
              type="password"
              :placeholder="currentConfig?.configured ? $t('configuration.aiMode.apiKeyPlaceholderEdit') : $t('configuration.aiMode.apiKeyPlaceholder')"
              show-password
              clearable>
              <template #prepend><el-icon><Key /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item :label="$t('configuration.aiMode.baseUrl')" prop="refiner_base_url">
            <el-input v-model="form.refiner_base_url" placeholder="如: https://dashscope.aliyuncs.com/compatible-mode/v1" clearable>
              <template #prepend><el-icon><Link /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item :label="$t('configuration.knowledgeBase.modelName')" prop="refiner_model">
            <el-input v-model="form.refiner_model" placeholder="默认: qwen-plus" clearable></el-input>
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="$t('configuration.knowledgeBase.maxTokens')" prop="refiner_max_tokens">
                <el-input-number v-model="form.refiner_max_tokens" :min="100" :max="128000" :step="1000" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="$t('configuration.knowledgeBase.temperature')" prop="refiner_temperature">
                <el-slider v-model="form.refiner_temperature" :min="0" :max="2" :step="0.1" show-input />
              </el-form-item>
            </el-col>
          </el-row>

          <el-divider border-style="dashed" />

          <!-- Tika Server 配置 -->
          <div class="section-title">
            <el-icon><Document /></el-icon>
            {{ $t('configuration.knowledgeBase.tikaTitle', '文档解析服务 (Tika Server)') }}
          </div>
          <el-alert
            :title="$t('configuration.knowledgeBase.tikaHint', '用于解析 PDF、Word 等文档内容，提取纯文本供向量化使用。')"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 20px;"
          />
          <el-form-item :label="$t('configuration.knowledgeBase.tikaServerUrl', 'Tika 服务地址')" prop="tika_server_url">
            <el-input v-model="form.tika_server_url" placeholder="如: http://localhost:9987" clearable>
              <template #prepend><el-icon><Link /></el-icon></template>
            </el-input>
          </el-form-item>

          <div class="form-actions">
            <el-button type="primary" @click="saveConfig" :loading="saving">
              <el-icon><Check /></el-icon>
              {{ $t('configuration.common.save') }}
            </el-button>
            <el-button @click="resetForm">
              <el-icon><RefreshLeft /></el-icon>
              {{ $t('configuration.common.reset') }}
            </el-button>
          </div>
        </el-form>
      </el-card>

      <!-- 侧边信息栏 -->
      <el-card class="info-card" v-if="currentConfig?.configured">
        <template #header>
          <span>{{ $t('configuration.knowledgeBase.currentConfig') }}</span>
        </template>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="Embedding API Key">{{ currentConfig.embedding_api_key_masked || '未配置' }}</el-descriptions-item>
          <el-descriptions-item label="Refiner API Key">{{ currentConfig.refiner_api_key_masked || '未配置' }}</el-descriptions-item>
          <el-descriptions-item label="Tika Server URL">{{ currentConfig.tika_server_url || '未配置' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.common.createdAt')">{{ formatDate(currentConfig.created_at) }}</el-descriptions-item>
          <el-descriptions-item :label="$t('configuration.common.updatedAt')">{{ formatDate(currentConfig.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Link, Key, Check, RefreshLeft, DataAnalysis, EditPen, Document } from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t } = useI18n()

const configForm = ref(null)
const saving = ref(false)
const currentConfig = ref(null)

const form = ref({
  embedding_api_key: '',
  embedding_base_url: '',
  embedding_model: 'text-embedding-v3',
  refiner_api_key: '',
  refiner_base_url: '',
  refiner_model: 'qwen-plus',
  refiner_max_tokens: 8192,
  refiner_temperature: 0.3,
  tika_server_url: 'http://localhost:9987'
})




const loadConfig = async () => {
  try {
    const response = await api.get('/knowledge-base/configs/')
    currentConfig.value = response.data
    
    if (response.data.configured) {
      form.value = {
        embedding_api_key: response.data.embedding_api_key_masked ? '****' : '',
        embedding_base_url: response.data.embedding_base_url || '',
        embedding_model: response.data.embedding_model || 'text-embedding-v3',
        refiner_api_key: response.data.refiner_api_key_masked ? '****' : '',
        refiner_base_url: response.data.refiner_base_url || '',
        refiner_model: response.data.refiner_model || 'qwen-plus',
        refiner_max_tokens: response.data.refiner_max_tokens || 8192,
        refiner_temperature: response.data.refiner_temperature || 0.3,
        tika_server_url: response.data.tika_server_url || 'http://localhost:9987'
      }
    } else {
      resetForm()
    }
  } catch (error) {
    console.error('Failed to load knowledge base config:', error)
    ElMessage.error(t('configuration.knowledgeBase.messages.loadFailed'))
  }
}

const saveConfig = async () => {
  if (!configForm.value) return
  
  await configForm.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        const payload = { ...form.value }
        if (payload.embedding_api_key === '****') delete payload.embedding_api_key
        if (payload.refiner_api_key === '****') delete payload.refiner_api_key
        

        await api.post('/knowledge-base/configs/', payload)
        ElMessage.success(t('configuration.knowledgeBase.messages.saveSuccess'))
        await loadConfig()
      } catch (error) {
        console.error('Failed to save config:', error)
        ElMessage.error(t('configuration.knowledgeBase.messages.saveFailed'))
      } finally {
        saving.value = false
      }
    }
  })
}

const resetForm = () => {
  if (currentConfig.value?.configured) {
    loadConfig()
  } else {
    form.value = {
      embedding_api_key: '',
      embedding_base_url: '',
      embedding_model: 'text-embedding-v3',
      refiner_api_key: '',
      refiner_base_url: '',
      refiner_model: 'qwen-plus',
      refiner_max_tokens: 8192,
      refiner_temperature: 0.3,
      vision_api_key: '',
      vision_base_url: '',
      vision_model: 'glm-4v-flash',
      vision_provider: 'zhipu'
    }
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.knowledge-base-config-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 24px;
  color: #303133;
  margin: 0 0 8px 0;
}

.page-header p {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.config-content {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 24px;
  align-items: start;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 20px;
  margin-top: 10px;
}

.form-actions {
  margin-top: 40px;
  display: flex;
  gap: 16px;
  justify-content: center;
}

@media (max-width: 1024px) {
  .config-content {
    grid-template-columns: 1fr;
  }
}
</style>
