<template>
  <el-dialog
    v-model="visible"
    :title="$t('apiTesting.importExport.importTitle')"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <!-- 步骤一：选择格式并上传 -->
    <div v-if="step === 'upload'">
      <el-form label-width="100px">
        <el-form-item :label="$t('apiTesting.importExport.format')">
          <el-radio-group v-model="format" size="default">
            <el-radio-button value="openapi">Swagger/OpenAPI</el-radio-button>
            <el-radio-button value="postman">Postman</el-radio-button>
            <el-radio-button value="curl">cURL</el-radio-button>
            <el-radio-button value="har">HAR</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 文件上传（非 cURL） -->
        <el-form-item v-if="format !== 'curl'" :label="$t('apiTesting.importExport.file')">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :accept="acceptTypes"
            :on-change="handleFileChange"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              {{ $t('apiTesting.importExport.dragOrClick') }}
            </div>
            <template #tip>
              <div class="el-upload__tip">{{ formatTip }}</div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- cURL 文本输入 -->
        <el-form-item v-else :label="$t('apiTesting.importExport.curlCommand')">
          <el-input
            v-model="curlContent"
            type="textarea"
            :rows="8"
            :placeholder="$t('apiTesting.importExport.curlPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.importExport.targetProject')">
          <el-select v-model="targetProjectId" :placeholder="$t('apiTesting.importExport.selectProject')" style="width: 100%">
            <el-option
              v-for="p in projects"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <!-- 步骤二：预览 -->
    <div v-else-if="step === 'preview'">
      <el-alert
        :title="`${previewData.title} - ${$t('apiTesting.importExport.totalApis', { count: previewData.total_requests })}`"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />

      <div v-for="(col, ci) in previewData.collections" :key="ci" class="preview-collection">
        <div class="collection-header">
          <el-checkbox v-model="col._selected" @change="toggleCollection(col)">
            <strong>{{ col.name }}</strong>
            <el-tag size="small" type="info" style="margin-left: 8px">{{ col.requests.length }}</el-tag>
          </el-checkbox>
        </div>
        <div class="collection-requests">
          <div v-for="(req, ri) in col.requests" :key="ri" class="request-item">
            <el-checkbox v-model="req._selected" size="small">
              <el-tag :type="methodTagType(req.method)" size="small" style="margin-right: 6px">{{ req.method }}</el-tag>
              <span class="request-name">{{ req.name }}</span>
              <span class="request-url">{{ req.url }}</span>
            </el-checkbox>
          </div>
        </div>
      </div>
    </div>

    <!-- 步骤三：完成 -->
    <div v-else-if="step === 'done'">
      <el-result
        icon="success"
        :title="$t('apiTesting.importExport.importSuccess')"
        :sub-title="importResult"
      />
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">{{ $t('apiTesting.importExport.cancel') }}</el-button>
        <el-button v-if="step === 'upload'" type="primary" :loading="parsing" @click="handlePreview">
          {{ $t('apiTesting.importExport.preview') }}
        </el-button>
        <el-button v-if="step === 'preview'" @click="step = 'upload'">
          {{ $t('apiTesting.importExport.back') }}
        </el-button>
        <el-button v-if="step === 'preview'" type="primary" :loading="importing" @click="handleImport">
          {{ $t('apiTesting.importExport.confirmImport', { count: selectedCount }) }}
        </el-button>
        <el-button v-if="step === 'done'" type="primary" @click="handleDone">
          {{ $t('apiTesting.importExport.done') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import api from '@/utils/api'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projects: { type: Array, default: () => [] },
  currentProjectId: { type: [Number, String], default: null },
})

const emit = defineEmits(['update:modelValue', 'imported'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const step = ref('upload')
const format = ref('openapi')
const curlContent = ref('')
const targetProjectId = ref(null)
const selectedFile = ref(null)
const parsing = ref(false)
const importing = ref(false)
const previewData = ref({ title: '', collections: [], total_requests: 0 })
const importResult = ref('')

watch(() => props.modelValue, (val) => {
  if (val) {
    step.value = 'upload'
    targetProjectId.value = props.currentProjectId
    selectedFile.value = null
    curlContent.value = ''
    previewData.value = { title: '', collections: [], total_requests: 0 }
  }
})

const acceptTypes = computed(() => {
  const map = {
    openapi: '.json,.yaml,.yml',
    postman: '.json',
    har: '.har,.json',
  }
  return map[format.value] || ''
})

const formatTip = computed(() => {
  const map = {
    openapi: 'Swagger 2.0 / OpenAPI 3.0 (JSON/YAML)',
    postman: 'Postman Collection v2.1 (JSON)',
    har: 'HTTP Archive (HAR) file',
  }
  return map[format.value] || ''
})

const selectedCount = computed(() => {
  let count = 0
  for (const col of previewData.value.collections) {
    for (const req of col.requests) {
      if (req._selected) count++
    }
  }
  return count
})

function handleFileChange(file) {
  selectedFile.value = file.raw
}

function toggleCollection(col) {
  col.requests.forEach(req => { req._selected = col._selected })
}

function methodTagType(method) {
  const map = { GET: 'success', POST: 'warning', PUT: '', DELETE: 'danger', PATCH: 'info' }
  return map[method] || 'info'
}

async function handlePreview() {
  if (!targetProjectId.value) {
    ElMessage.warning(t('apiTesting.importExport.selectProject'))
    return
  }

  if (format.value === 'curl') {
    if (!curlContent.value.trim()) {
      ElMessage.warning(t('apiTesting.importExport.enterCurl'))
      return
    }
  } else {
    if (!selectedFile.value) {
      ElMessage.warning(t('apiTesting.importExport.selectFile'))
      return
    }
  }

  parsing.value = true
  try {
    const formData = new FormData()
    formData.append('format', format.value)

    if (format.value === 'curl') {
      formData.append('content', curlContent.value)
    } else {
      formData.append('file', selectedFile.value)
    }

    const res = await api.post('/api-testing/import/preview/', formData, {
      headers: { 'Content-Type': undefined },
    })
    previewData.value = res.data

    // 默认全选
    previewData.value.collections.forEach(col => {
      col._selected = true
      col.requests.forEach(req => { req._selected = true })
    })

    step.value = 'preview'
  } catch (error) {
    const msg = error.response?.data?.error || t('apiTesting.importExport.parseFailed')
    ElMessage.error(msg)
  } finally {
    parsing.value = false
  }
}

async function handleImport() {
  if (selectedCount.value === 0) {
    ElMessage.warning(t('apiTesting.importExport.selectAtLeastOne'))
    return
  }

  importing.value = true
  try {
    // 只提交勾选的接口
    const collections = previewData.value.collections
      .map(col => ({
        ...col,
        requests: col.requests.filter(r => r._selected),
      }))
      .filter(col => col.requests.length > 0)

    const res = await api.post('/api-testing/import/confirm/', {
      project_id: targetProjectId.value,
      collections,
    })

    importResult.value = res.data.message
    step.value = 'done'
    emit('imported')
  } catch (error) {
    const msg = error.response?.data?.error || t('apiTesting.importExport.importFailed')
    ElMessage.error(msg)
  } finally {
    importing.value = false
  }
}

function handleClose() {
  visible.value = false
}

function handleDone() {
  visible.value = false
}
</script>

<style scoped>
.preview-collection {
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}

.collection-header {
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.collection-requests {
  padding: 6px 12px 6px 32px;
  max-height: 300px;
  overflow-y: auto;
}

.request-item {
  padding: 4px 0;
}

.request-name {
  font-weight: 500;
  margin-right: 8px;
}

.request-url {
  color: #909399;
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
