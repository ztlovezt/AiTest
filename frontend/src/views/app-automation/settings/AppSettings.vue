<template>
  <div class="app-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span><el-icon><Setting /></el-icon> {{ t('appAutomation.settings.title') }}</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleSave" :loading="saving">
              <el-icon><Check /></el-icon>
              {{ t('appAutomation.settings.saveConfig') }}
            </el-button>
            <el-button @click="handleReset">
              <el-icon><RefreshLeft /></el-icon>
              {{ t('appAutomation.settings.reset') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
      >
        <el-row :gutter="40">
          <el-col :span="12">
            <div class="section-title">
              <el-icon><Monitor /></el-icon>
              {{ t('appAutomation.settings.adbConfig') }}
            </div>
            
            <el-form-item :label="t('appAutomation.settings.adbPath')" prop="adb_path">
              <el-input
                v-model="form.adb_path"
                :placeholder="t('appAutomation.settings.adbPathPlaceholder')"
                clearable
              >
                <template #prepend>
                  <el-icon><FolderOpened /></el-icon>
                </template>
              </el-input>
              <div class="form-item-tip">
                <el-text size="small" type="info">
                  {{ t('appAutomation.settings.adbPathTip') }}
                </el-text>
              </div>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <div class="section-title">
              <el-icon><Document /></el-icon>
              {{ t('appAutomation.settings.ocrConfig') }}
            </div>

            <el-form-item :label="t('appAutomation.settings.ocrEngine')" prop="ocr_engine">
              <el-select v-model="form.ocr_engine" style="width: 100%">
                <el-option
                  v-for="item in ocrEngineOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
              <div class="form-item-tip">
                <el-text size="small" type="info">
                  {{ t('appAutomation.settings.ocrEngineTip') }}
                </el-text>
              </div>
            </el-form-item>

            <el-form-item :label="t('appAutomation.settings.ocrLanguage')" prop="ocr_language">
              <el-select v-model="form.ocr_language" style="width: 100%">
                <el-option
                  v-for="item in ocrLanguageOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
              <div class="form-item-tip">
                <el-text size="small" type="info">
                  {{ t('appAutomation.settings.ocrLanguageTip') }}
                </el-text>
              </div>
            </el-form-item>

            <el-form-item :label="t('appAutomation.settings.ocrMinConfidence')" prop="ocr_min_confidence">
              <el-slider
                v-model="form.ocr_min_confidence"
                :min="0"
                :max="1"
                :step="0.1"
                show-input
                :show-input-controls="false"
              />
              <div class="form-item-tip">
                <el-text size="small" type="info">
                  {{ t('appAutomation.settings.ocrMinConfidenceTip') }}
                </el-text>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <el-divider />

      <div class="config-info">
        <div class="section-title">
          <el-icon><InfoFilled /></el-icon>
          {{ t('appAutomation.settings.currentConfigInfo') }}
        </div>
        <el-descriptions :column="3" border class="config-descriptions">
          <el-descriptions-item :label="t('appAutomation.settings.adbPathLabel')">
            <el-tag>{{ currentConfig.adb_path || 'adb' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('appAutomation.settings.ocrEngineLabel')">
            <el-tag type="success">{{ currentConfig.ocr_engine_display || 'Tesseract OCR' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('appAutomation.settings.ocrLanguageLabel')">
            <el-tag type="info">{{ getOcrLanguageLabel(currentConfig.ocr_language) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('appAutomation.settings.ocrMinConfidence')">
            <el-tag type="warning">{{ currentConfig.ocr_min_confidence || 0.3 }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('appAutomation.settings.updateTime')">
            {{ formatTime(currentConfig.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Setting, FolderOpened, Check, RefreshLeft, Monitor, Document, InfoFilled } from '@element-plus/icons-vue'
import { getAppConfig, updateAppConfig } from '@/api/app-automation'
import { formatDateTime } from '@/utils/app-automation-helpers'

const { t } = useI18n()

const formRef = ref(null)
const saving = ref(false)

const form = reactive({
  adb_path: 'adb',
  ocr_engine: 'tesseract',
  ocr_language: 'chi_sim+eng',
  ocr_min_confidence: 0.3
})

const currentConfig = reactive({
  adb_path: '',
  ocr_engine: '',
  ocr_engine_display: '',
  ocr_language: '',
  ocr_min_confidence: 0.3,
  created_at: '',
  updated_at: ''
})

const ocrEngineOptions = [
  { value: 'tesseract', label: 'Tesseract OCR' }
]

const ocrLanguageOptions = [
  { value: 'chi_sim', label: t('appAutomation.settings.ocrLangChinese') },
  { value: 'eng', label: t('appAutomation.settings.ocrLangEnglish') },
  { value: 'chi_sim+eng', label: t('appAutomation.settings.ocrLangChineseEnglish') }
]

const rules = {
  adb_path: [
    { required: true, message: t('appAutomation.settings.adbPathRequired'), trigger: 'blur' }
  ],
  ocr_engine: [
    { required: true, message: t('appAutomation.settings.ocrEngineRequired'), trigger: 'change' }
  ],
  ocr_language: [
    { required: true, message: t('appAutomation.settings.ocrLanguageRequired'), trigger: 'change' }
  ]
}

const getOcrLanguageLabel = (lang) => {
  const option = ocrLanguageOptions.find(item => item.value === lang)
  return option ? option.label : lang
}

const loadConfig = async () => {
  try {
    const res = await getAppConfig()
    if (res.data.success && res.data.data) {
      Object.assign(form, res.data.data)
      Object.assign(currentConfig, res.data.data)
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error(t('appAutomation.settings.loadConfigFailed'))
  }
}

const handleSave = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    saving.value = true

    const res = await updateAppConfig(form)
    if (res.data.success) {
      ElMessage.success(t('appAutomation.settings.saveConfigSuccess'))
      await loadConfig()
    } else {
      ElMessage.error(res.data.message || t('appAutomation.settings.saveConfigFailed'))
    }
  } catch (error) {
    if (error !== false) {
      console.error('保存配置失败:', error)
      ElMessage.error(t('appAutomation.settings.saveConfigFailed'))
    }
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  Object.assign(form, currentConfig)
}

const formatTime = formatDateTime

onMounted(() => {
  loadConfig()
})
</script>

<style scoped lang="scss">
.app-settings {
  padding: 20px;

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: bold;
    
    span {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #ebeef5;
  }

  .form-item-tip {
    margin-top: 8px;
  }

  .config-info {
    margin-top: 20px;

    .config-descriptions {
      margin-top: 16px;
    }
  }
}
</style>
