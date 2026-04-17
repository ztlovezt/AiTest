<template>
  <div class="ocr-config">
    <div class="page-header">
      <h1>{{ $t('configuration.ocr.title') }}</h1>
      <p>{{ $t('configuration.ocr.description') }}</p>
    </div>

    <div class="main-content">
      <div class="configs-section">
        <div class="section-header">
          <h2>{{ $t('configuration.ocr.configList') }}</h2>
          <button class="add-config-btn" @click.stop="openAddModal" type="button">
            {{ $t('configuration.ocr.addConfig') }}
          </button>
        </div>

        <div class="configs-grid">
          <template v-for="config in configs" :key="config?.id || 'unknown'">
            <div v-if="config && config.id" class="config-card">
              <div class="config-header">
                <div class="config-title">
                  <h3 :title="config.name || $t('configuration.common.unnamed')">{{ config.name || $t('configuration.common.unnamed') }}</h3>
                  <div class="config-badges">
                    <span class="provider-badge" :class="config.provider">
                      {{ getProviderLabel(config.provider) }}
                    </span>
                    <span class="status-badge" :class="{ active: config.is_active }">
                      {{ config.is_active ? $t('configuration.common.enabled') : $t('configuration.common.disabled') }}
                    </span>
                    <span v-if="config.is_default" class="default-badge">
                      {{ $t('configuration.ocr.default') }}
                    </span>
                  </div>
                </div>
                <div class="config-actions">
                  <button class="test-btn" :disabled="testingConfigId === config.id" @click="testConnection(config)">
                    <span v-if="testingConfigId === config.id">{{ $t('configuration.ocr.testing') }}</span>
                    <span v-else>{{ $t('configuration.ocr.testConnection') }}</span>
                  </button>
                  <button v-if="!config.is_default" class="default-btn" @click="setDefault(config.id)">
                    {{ $t('configuration.ocr.setDefault') }}
                  </button>
                  <button class="edit-btn" @click="editConfig(config)">{{ $t('configuration.common.edit') }}</button>
                  <button class="delete-btn" @click="deleteConfig(config.id)">{{ $t('configuration.common.delete') }}</button>
                </div>
              </div>

              <div class="config-details">
                <div v-if="config.base_url" class="detail-item">
                  <label>{{ $t('configuration.ocr.baseUrl') }}:</label>
                  <span>{{ config.base_url }}</span>
                </div>
                <div v-if="config.model_name" class="detail-item">
                  <label>{{ $t('configuration.ocr.modelName') }}:</label>
                  <span>{{ config.model_name }}</span>
                </div>
                <div class="detail-item">
                  <label>{{ $t('configuration.ocr.language') }}:</label>
                  <span>{{ getLanguageLabel(config.language) }}</span>
                </div>
                <div class="detail-item">
                  <label>{{ $t('configuration.ocr.minConfidence') }}:</label>
                  <span>{{ config.min_confidence }}</span>
                </div>
                <div class="detail-item">
                  <label>{{ $t('configuration.common.createdAt') }}:</label>
                  <span>{{ formatDateTime(config.created_at) }}</span>
                </div>
              </div>
            </div>
          </template>
        </div>

        <div v-if="configs.length === 0" class="empty-state">
          <div class="empty-icon">🔍</div>
          <h3>{{ $t('configuration.ocr.emptyTitle') }}</h3>
          <p>{{ $t('configuration.ocr.emptyDescription') }}</p>
          <button class="add-first-config-btn" @click.stop="openAddModal" type="button">
            {{ $t('configuration.ocr.addFirstConfig') }}
          </button>
        </div>
      </div>
    </div>

    <div
      v-show="showModal"
      :class="['config-modal', { hidden: !showModal }]"
      @keydown.esc="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ isEditing ? $t('configuration.ocr.editConfig') : $t('configuration.ocr.addConfigTitle') }}</h3>
          <button class="close-btn" @click.stop="closeModal" type="button">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveConfig">
            <div class="form-group">
              <label>{{ $t('configuration.ocr.configName') }} <span class="required">*</span></label>
              <input
                v-model="configForm.name"
                type="text"
                class="form-input"
                :placeholder="$t('configuration.ocr.configNamePlaceholder')"
                required>
            </div>

            <div class="form-group">
              <label>{{ $t('configuration.ocr.provider') }} <span class="required">*</span></label>
              <select
                v-model="configForm.provider"
                class="form-select"
                required
                @change="onProviderChange">
                <option value="">{{ $t('configuration.ocr.selectProvider') }}</option>
                <option value="tesseract">{{ $t('configuration.ocr.providers.tesseract') }}</option>
                <option value="openai">{{ $t('configuration.ocr.providers.openai') }}</option>
                <option value="zhipu">{{ $t('configuration.ocr.providers.zhipu') }}</option>
                <option value="siliconflow">{{ $t('configuration.ocr.providers.siliconflow') }}</option>
                <option value="baidu">{{ $t('configuration.ocr.providers.baidu') }}</option>
                <option value="tencent">{{ $t('configuration.ocr.providers.tencent') }}</option>
                <option value="aliyun">{{ $t('configuration.ocr.providers.aliyun') }}</option>
                <option value="custom">{{ $t('configuration.ocr.providers.custom') }}</option>
              </select>
            </div>

            <div v-if="isOnlineProvider" class="form-group">
              <label>{{ $t('configuration.ocr.apiKey') }} <span v-if="!isBaiduProvider && !isTencentProvider && !isAliyunProvider" class="required">*</span></label>
              <input
                v-model="configForm.api_key"
                type="password"
                class="form-input"
                :placeholder="$t('configuration.ocr.apiKeyPlaceholder')"
                :required="isOnlineProvider && !isEditing && !isBaiduProvider && !isTencentProvider && !isAliyunProvider">
            </div>

            <div v-if="isBaiduProvider" class="form-group">
              <label>{{ $t('configuration.ocr.baiduSecretKey') }} <span class="required">*</span></label>
              <input
                v-model="configForm.extra_config.secret_key"
                type="password"
                class="form-input"
                :placeholder="$t('configuration.ocr.baiduSecretKeyPlaceholder')"
                :required="isBaiduProvider && !isEditing">
            </div>

            <div v-if="isTencentProvider" class="form-group">
              <label>{{ $t('configuration.ocr.tencentSecretId') }} <span class="required">*</span></label>
              <input
                v-model="configForm.extra_config.secret_id"
                type="password"
                class="form-input"
                :placeholder="$t('configuration.ocr.tencentSecretIdPlaceholder')"
                :required="isTencentProvider && !isEditing">
            </div>

            <div v-if="isTencentProvider" class="form-group">
              <label>{{ $t('configuration.ocr.tencentSecretKey') }} <span class="required">*</span></label>
              <input
                v-model="configForm.extra_config.secret_key"
                type="password"
                class="form-input"
                :placeholder="$t('configuration.ocr.tencentSecretKeyPlaceholder')"
                :required="isTencentProvider && !isEditing">
            </div>

            <div v-if="isTencentProvider" class="form-group">
              <label>{{ $t('configuration.ocr.tencentRegion') }}</label>
              <select v-model="configForm.extra_config.region" class="form-select">
                <option value="ap-guangzhou">{{ $t('configuration.ocr.regions.guangzhou') }}</option>
                <option value="ap-shanghai">{{ $t('configuration.ocr.regions.shanghai') }}</option>
                <option value="ap-beijing">{{ $t('configuration.ocr.regions.beijing') }}</option>
                <option value="ap-chengdu">{{ $t('configuration.ocr.regions.chengdu') }}</option>
              </select>
            </div>

            <div v-if="isAliyunProvider" class="form-group">
              <label>{{ $t('configuration.ocr.aliyunAccessKeyId') }} <span class="required">*</span></label>
              <input
                v-model="configForm.extra_config.access_key_id"
                type="password"
                class="form-input"
                :placeholder="$t('configuration.ocr.aliyunAccessKeyIdPlaceholder')"
                :required="isAliyunProvider && !isEditing">
            </div>

            <div v-if="isAliyunProvider" class="form-group">
              <label>{{ $t('configuration.ocr.aliyunAccessKeySecret') }} <span class="required">*</span></label>
              <input
                v-model="configForm.extra_config.access_key_secret"
                type="password"
                class="form-input"
                :placeholder="$t('configuration.ocr.aliyunAccessKeySecretPlaceholder')"
                :required="isAliyunProvider && !isEditing">
            </div>

            <div v-if="isCustomProvider" class="form-group">
              <label>{{ $t('configuration.ocr.customRequestMethod') }}</label>
              <select v-model="configForm.extra_config.request_method" class="form-select">
                <option value="POST">POST</option>
                <option value="GET">GET</option>
              </select>
            </div>

            <div v-if="isCustomProvider" class="form-group">
              <label>{{ $t('configuration.ocr.customRequestFormat') }}</label>
              <select v-model="configForm.extra_config.request_format" class="form-select">
                <option value="openai">OpenAI 格式</option>
                <option value="raw">Raw (image base64)</option>
                <option value="custom">{{ $t('configuration.ocr.customTemplate') }}</option>
              </select>
              <small class="form-hint">{{ $t('configuration.ocr.customRequestFormatHint') }}</small>
            </div>

            <div v-if="isCustomProvider && configForm.extra_config.request_format === 'custom'" class="form-group">
              <label>{{ $t('configuration.ocr.customBodyTemplate') }}</label>
              <textarea
                v-model="customBodyTemplateJson"
                class="form-textarea"
                rows="4"
                :placeholder="$t('configuration.ocr.customBodyTemplatePlaceholder')"></textarea>
              <small class="form-hint">{{ $t('configuration.ocr.customBodyTemplateHint') }}</small>
            </div>

            <div v-if="isCustomProvider" class="form-group">
              <label>{{ $t('configuration.ocr.customResponseFormat') }}</label>
              <select v-model="configForm.extra_config.response_format" class="form-select">
                <option value="openai">OpenAI 格式</option>
                <option value="text">{{ $t('configuration.ocr.responseText') }}</option>
                <option value="jsonpath">JSONPath</option>
              </select>
            </div>

            <div v-if="isCustomProvider && configForm.extra_config.response_format === 'jsonpath'" class="form-group">
              <label>{{ $t('configuration.ocr.customResponsePath') }}</label>
              <input
                v-model="configForm.extra_config.response_path"
                type="text"
                class="form-input"
                placeholder="choices[0].message.content">
              <small class="form-hint">{{ $t('configuration.ocr.customResponsePathHint') }}</small>
            </div>

            <div v-if="isCustomProvider" class="form-group">
              <label>{{ $t('configuration.ocr.customHeaders') }}</label>
              <textarea
                v-model="customHeadersJson"
                class="form-textarea"
                rows="3"
                :placeholder="$t('configuration.ocr.customHeadersPlaceholder')"></textarea>
              <small class="form-hint">{{ $t('configuration.ocr.customHeadersHint') }}</small>
            </div>

            <div v-if="isOnlineProvider" class="form-group">
              <label>{{ $t('configuration.ocr.baseUrl') }}</label>
              <input
                v-model="configForm.base_url"
                type="url"
                class="form-input"
                :placeholder="$t('configuration.ocr.baseUrlPlaceholder')">
              <small class="form-hint">{{ $t('configuration.ocr.baseUrlHint') }}</small>
            </div>

            <div v-if="showModelName" class="form-group">
              <label>{{ $t('configuration.ocr.modelName') }}</label>
              <input
                v-model="configForm.model_name"
                type="text"
                class="form-input"
                :placeholder="$t('configuration.ocr.modelNamePlaceholder')">
            </div>

            <div class="form-group">
              <label>{{ $t('configuration.ocr.language') }}</label>
              <select v-model="configForm.language" class="form-select">
                <option value="chi_sim+eng">{{ $t('configuration.ocr.languages.chineseEnglish') }}</option>
                <option value="chi_sim">{{ $t('configuration.ocr.languages.chinese') }}</option>
                <option value="eng">{{ $t('configuration.ocr.languages.english') }}</option>
                <option value="japan">{{ $t('configuration.ocr.languages.japanese') }}</option>
                <option value="korean">{{ $t('configuration.ocr.languages.korean') }}</option>
              </select>
            </div>

            <div class="form-group">
              <label>{{ $t('configuration.ocr.minConfidence') }}</label>
              <input
                v-model.number="configForm.min_confidence"
                type="number"
                min="0"
                max="1"
                step="0.1"
                class="form-input"
                placeholder="0.3">
              <small class="form-hint">{{ $t('configuration.ocr.minConfidenceHint') }}</small>
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input v-model="configForm.is_active" type="checkbox">
                <span class="checkmark"></span>
                {{ $t('configuration.ocr.enableConfig') }}
              </label>
            </div>

            <div class="modal-actions">
              <button type="button" class="cancel-btn" @click="closeModal">{{ $t('configuration.common.cancel') }}</button>
              <button type="submit" class="confirm-btn" :disabled="isSaving">
                <span v-if="isSaving">{{ $t('configuration.ocr.saving') }}</span>
                <span v-else>{{ $t('configuration.ocr.saveConfig') }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  getOCRConfigs,
  createOCRConfig,
  updateOCRConfig,
  deleteOCRConfig,
  setDefaultOCRConfig,
  testOCRConfig
} from '@/api/ocr'

export default {
  name: 'OCRConfig',
  setup() {
    const { t } = useI18n()
    return { t }
  },
  data() {
    return {
      configs: [],
      showModal: false,
      isEditing: false,
      isSaving: false,
      testingConfigId: null,
      editingConfigId: null,
      configForm: {
        name: '',
        provider: '',
        api_key: '',
        base_url: '',
        model_name: '',
        language: 'chi_sim+eng',
        min_confidence: 0.3,
        extra_config: {
          secret_key: '',
          secret_id: '',
          region: 'ap-guangzhou',
          access_key_id: '',
          access_key_secret: '',
          request_method: 'POST',
          request_format: 'openai',
          response_format: 'openai',
          response_path: 'choices[0].message.content',
          headers: {},
          body_template: {}
        },
        is_active: true
      },
      customBodyTemplateJson: '',
      customHeadersJson: '',
      providerBaseUrlMap: {
        openai: 'https://api.openai.com/v1',
        zhipu: 'https://open.bigmodel.cn/api/paas/v4',
        siliconflow: 'https://api.siliconflow.cn/v1',
        baidu: 'https://aip.baidubce.com/rest/2.0/ocr/v1',
        tencent: 'https://ocr.tencentcloudapi.com',
        aliyun: 'https://ocr.cn-shanghai.aliyuncs.com'
      }
    }
  },
  computed: {
    isOnlineProvider() {
      return ['openai', 'zhipu', 'siliconflow', 'baidu', 'tencent', 'aliyun', 'custom'].includes(this.configForm.provider)
    },
    isBaiduProvider() {
      return this.configForm.provider === 'baidu'
    },
    isTencentProvider() {
      return this.configForm.provider === 'tencent'
    },
    isAliyunProvider() {
      return this.configForm.provider === 'aliyun'
    },
    isCustomProvider() {
      return this.configForm.provider === 'custom'
    },
    showModelName() {
      return ['openai', 'zhipu', 'siliconflow'].includes(this.configForm.provider)
    }
  },
  mounted() {
    this.loadConfigs()
  },
  methods: {
    async loadConfigs() {
      try {
        const response = await getOCRConfigs()
        if (response.data && response.data.results && Array.isArray(response.data.results)) {
          this.configs = response.data.results.filter(config => config && config.id)
        } else if (response.data && Array.isArray(response.data)) {
          this.configs = response.data.filter(config => config && config.id)
        } else {
          this.configs = []
        }
      } catch (error) {
        console.error('Failed to load OCR configs:', error)
        this.configs = []
        ElMessage.error(this.t('configuration.ocr.messages.loadFailed'))
      }
    },

    getProviderLabel(provider) {
      const labels = {
        tesseract: this.t('configuration.ocr.providers.tesseract'),
        openai: this.t('configuration.ocr.providers.openai'),
        zhipu: this.t('configuration.ocr.providers.zhipu'),
        siliconflow: this.t('configuration.ocr.providers.siliconflow'),
        baidu: this.t('configuration.ocr.providers.baidu'),
        tencent: this.t('configuration.ocr.providers.tencent'),
        aliyun: this.t('configuration.ocr.providers.aliyun'),
        custom: this.t('configuration.ocr.providers.custom')
      }
      return labels[provider] || provider
    },

    getLanguageLabel(language) {
      const labels = {
        'chi_sim+eng': this.t('configuration.ocr.languages.chineseEnglish'),
        'chi_sim': this.t('configuration.ocr.languages.chinese'),
        'eng': this.t('configuration.ocr.languages.english'),
        'japan': this.t('configuration.ocr.languages.japanese'),
        'korean': this.t('configuration.ocr.languages.korean')
      }
      return labels[language] || language
    },

    onProviderChange() {
      if (this.providerBaseUrlMap[this.configForm.provider]) {
        this.configForm.base_url = this.providerBaseUrlMap[this.configForm.provider]
      }
      if (this.configForm.provider === 'openai') {
        this.configForm.model_name = 'gpt-4o'
      } else if (this.configForm.provider === 'zhipu') {
        this.configForm.model_name = 'glm-4v'
      }
    },

    openAddModal() {
      this.resetForm()
      this.isEditing = false
      this.showModal = true
    },

    resetForm() {
      Object.assign(this.configForm, {
        name: '',
        provider: '',
        api_key: '',
        base_url: '',
        model_name: '',
        language: 'chi_sim+eng',
        min_confidence: 0.3,
        extra_config: {
          secret_key: '',
          secret_id: '',
          region: 'ap-guangzhou',
          access_key_id: '',
          access_key_secret: '',
          request_method: 'POST',
          request_format: 'openai',
          response_format: 'openai',
          response_path: 'choices[0].message.content',
          headers: {},
          body_template: {}
        },
        is_active: true
      })
      this.customBodyTemplateJson = ''
      this.customHeadersJson = ''
    },

    editConfig(config) {
      this.isEditing = true
      this.editingConfigId = config.id
      const extraConfig = config.extra_config || {}
      Object.assign(this.configForm, {
        name: config.name,
        provider: config.provider,
        api_key: '',
        base_url: config.base_url || '',
        model_name: config.model_name || '',
        language: config.language,
        min_confidence: config.min_confidence,
        extra_config: {
          secret_key: extraConfig.secret_key || '',
          secret_id: extraConfig.secret_id || '',
          region: extraConfig.region || 'ap-guangzhou',
          access_key_id: extraConfig.access_key_id || '',
          access_key_secret: extraConfig.access_key_secret || '',
          request_method: extraConfig.request_method || 'POST',
          request_format: extraConfig.request_format || 'openai',
          response_format: extraConfig.response_format || 'openai',
          response_path: extraConfig.response_path || 'choices[0].message.content',
          headers: extraConfig.headers || {},
          body_template: extraConfig.body_template || {}
        },
        is_active: config.is_active
      })
      if (extraConfig.body_template && Object.keys(extraConfig.body_template).length > 0) {
        this.customBodyTemplateJson = JSON.stringify(extraConfig.body_template, null, 2)
      } else {
        this.customBodyTemplateJson = ''
      }
      if (extraConfig.headers && Object.keys(extraConfig.headers).length > 0) {
        this.customHeadersJson = JSON.stringify(extraConfig.headers, null, 2)
      } else {
        this.customHeadersJson = ''
      }
      this.showModal = true
    },

    async saveConfig() {
      if (!this.configForm.name || !this.configForm.provider) {
        ElMessage.error(this.t('configuration.ocr.messages.fillRequired'))
        return
      }

      try {
        if (this.customBodyTemplateJson && this.customBodyTemplateJson.trim()) {
          this.configForm.extra_config.body_template = JSON.parse(this.customBodyTemplateJson)
        } else {
          this.configForm.extra_config.body_template = {}
        }
        if (this.customHeadersJson && this.customHeadersJson.trim()) {
          this.configForm.extra_config.headers = JSON.parse(this.customHeadersJson)
        } else {
          this.configForm.extra_config.headers = {}
        }
      } catch (e) {
        ElMessage.error(this.t('configuration.ocr.messages.invalidJson'))
        return
      }

      this.isSaving = true
      try {
        const data = { ...this.configForm }
        data.extra_config = { ...this.configForm.extra_config }
        
        Object.keys(data.extra_config).forEach(key => {
          if (data.extra_config[key] === '' || data.extra_config[key] === null || data.extra_config[key] === undefined) {
            delete data.extra_config[key]
          }
        })
        
        if (Object.keys(data.extra_config).length === 0) {
          delete data.extra_config
        }
        
        if (this.isEditing && data.api_key && data.api_key.includes('*')) {
          delete data.api_key
        }

        if (this.isEditing) {
          await updateOCRConfig(this.editingConfigId, data)
          ElMessage.success(this.t('configuration.ocr.messages.updateSuccess'))
        } else {
          await createOCRConfig(data)
          ElMessage.success(this.t('configuration.ocr.messages.createSuccess'))
        }

        this.closeModal()
        this.loadConfigs()
      } catch (error) {
        console.error('Failed to save OCR config:', error)
        ElMessage.error(error.response?.data?.message || this.t('configuration.ocr.messages.saveFailed'))
      } finally {
        this.isSaving = false
      }
    },

    async deleteConfig(id) {
      try {
        await ElMessageBox.confirm(
          this.t('configuration.ocr.messages.deleteConfirm'),
          this.t('configuration.common.confirm'),
          { type: 'warning' }
        )
        await deleteOCRConfig(id)
        ElMessage.success(this.t('configuration.ocr.messages.deleteSuccess'))
        this.loadConfigs()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('Failed to delete OCR config:', error)
          ElMessage.error(this.t('configuration.ocr.messages.deleteFailed'))
        }
      }
    },

    async setDefault(id) {
      try {
        await setDefaultOCRConfig(id)
        ElMessage.success(this.t('configuration.ocr.messages.setDefaultSuccess'))
        this.loadConfigs()
      } catch (error) {
        console.error('Failed to set default OCR config:', error)
        ElMessage.error(this.t('configuration.ocr.messages.setDefaultFailed'))
      }
    },

    async testConnection(config) {
      this.testingConfigId = config.id
      try {
        const response = await testOCRConfig(config.id)
        if (response.data && response.data.success) {
          ElMessage.success(this.t('configuration.ocr.testSuccess'))
        } else {
          ElMessage.error(response.data?.message || this.t('configuration.ocr.testFailed'))
        }
      } catch (error) {
        console.error('Failed to test OCR config:', error)
        ElMessage.error(error.response?.data?.message || this.t('configuration.ocr.testFailed'))
      } finally {
        this.testingConfigId = null
      }
    },

    closeModal() {
      this.showModal = false
      this.isEditing = false
      this.editingConfigId = null
      this.resetForm()
    },

    formatDateTime(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return date.toLocaleString()
    }
  }
}
</script>

<style scoped>
.ocr-config {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 24px;
  color: #303133;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
  font-size: 14px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  font-size: 18px;
  color: #303133;
}

.add-config-btn {
  padding: 10px 20px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.add-config-btn:hover {
  background: #66b1ff;
}

.configs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.config-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.config-title {
  flex: 1;
  min-width: 0;
}

.config-title h3 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.config-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.provider-badge,
.status-badge,
.default-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.provider-badge {
  background: #f0f9ff;
  color: #409eff;
}

.provider-badge.tesseract {
  background: #f0f9ff;
  color: #67c23a;
}

.provider-badge.openai,
.provider-badge.zhipu {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-badge {
  background: #f4f4f5;
  color: #909399;
}

.status-badge.active {
  background: #f0f9ff;
  color: #67c23a;
}

.default-badge {
  background: #ecf5ff;
  color: #409eff;
}

.config-actions {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
  white-space: nowrap;
  flex-shrink: 0;
}

.config-actions button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.test-btn {
  background: #e6a23c;
  color: white;
}

.test-btn:hover {
  background: #ebb563;
}

.test-btn:disabled {
  background: #f5deb3;
  cursor: not-allowed;
  opacity: 0.7;
}

.default-btn {
  background: #409eff;
  color: white;
}

.default-btn:hover {
  background: #66b1ff;
}

.edit-btn {
  background: #909399;
  color: white;
}

.edit-btn:hover {
  background: #a6a9ad;
}

.delete-btn {
  background: #f56c6c;
  color: white;
}

.delete-btn:hover {
  background: #f78989;
}

.config-details {
  border-top: 1px solid #ebeef5;
  padding-top: 15px;
}

.detail-item {
  display: flex;
  margin-bottom: 8px;
}

.detail-item label {
  width: 100px;
  color: #909399;
  font-size: 13px;
}

.detail-item span {
  color: #303133;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 8px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.empty-state h3 {
  color: #303133;
  margin-bottom: 10px;
}

.empty-state p {
  color: #909399;
  margin-bottom: 20px;
}

.add-first-config-btn {
  padding: 10px 20px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.config-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.config-modal.hidden {
  display: none;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #ebeef5;
}

.modal-header h3 {
  font-size: 18px;
  color: #303133;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #909399;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #606266;
  font-size: 14px;
}

.required {
  color: #f56c6c;
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: #409eff;
  outline: none;
}

.form-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  resize: vertical;
}

.form-hint {
  display: block;
  margin-top: 5px;
  color: #909399;
  font-size: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.checkbox-label input {
  margin-right: 8px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.cancel-btn {
  padding: 10px 20px;
  background: #f4f4f5;
  color: #606266;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-btn {
  padding: 10px 20px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-btn:disabled {
  background: #a0cfff;
  cursor: not-allowed;
}

.test-result-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001;
}

.test-result {
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.test-result.success {
  background: #f0f9ff;
}

.test-result.error {
  background: #fef0f0;
}

.result-icon {
  font-size: 48px;
  margin-bottom: 15px;
}

.result-content h4 {
  margin-bottom: 10px;
  color: #303133;
}

.ocr-result {
  margin-top: 15px;
  text-align: left;
  background: white;
  padding: 10px;
  border-radius: 4px;
}

.ocr-result label {
  display: block;
  color: #909399;
  font-size: 12px;
  margin-bottom: 5px;
}

.ocr-result p {
  color: #303133;
  word-break: break-all;
}
</style>
