<template>
  <div class="app-package-list">
    <div class="page-header">
      <h3>{{ t('appAutomation.package.title') }}</h3>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadPackages">
          {{ t('appAutomation.common.refresh') }}
        </el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">
          {{ t('appAutomation.package.newPackage') }}
        </el-button>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="packages"
      style="width: 100%; margin-top: 16px"
      :empty-text="t('appAutomation.common.noData')"
    >
      <el-table-column prop="name" :label="t('appAutomation.package.packageName')" min-width="180" />
      <el-table-column prop="package_name" :label="t('appAutomation.package.packageId')" min-width="220" />
      <el-table-column prop="remarks" :label="t('appAutomation.package.remarks')" min-width="150">
        <template #default="{ row }">
          {{ row.remarks || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_by_name" :label="t('appAutomation.package.createdBy')" width="120">
        <template #default="{ row }">
          {{ row.created_by_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column :label="t('appAutomation.package.createTime')" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column :label="t('appAutomation.package.updateTime')" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column :label="t('appAutomation.common.operation')" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="openEditDialog(row)">
            {{ t('appAutomation.common.edit') }}
          </el-button>
          <el-button 
            v-if="row.apk_file_url" 
            link 
            size="small" 
            type="success" 
            @click="downloadApk(row)"
          >
            {{ t('appAutomation.package.downloadApk') }}
          </el-button>
          <el-button link size="small" type="danger" @click="handleDelete(row)">
            {{ t('appAutomation.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-show="total > 0"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      style="margin-top: 16px; text-align: right"
      @size-change="loadPackages"
      @current-change="loadPackages"
    />

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
      >
        <!-- 上传选项 -->
        <el-form-item :label="t('appAutomation.package.uploadApkOption')">
          <el-switch
            v-model="form.enable_apk_upload"
            :active-text="t('appAutomation.common.yes')"
            :inactive-text="t('appAutomation.common.no')"
            @change="handleUploadToggle"
          />
        </el-form-item>
        
        <!-- APK 上传区域（仅当启用上传时显示） -->
        <el-form-item v-if="form.enable_apk_upload" :label="t('appAutomation.package.apkFile')" prop="apk_file">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleApkChange"
            :on-remove="handleApkRemove"
            accept=".apk"
            drag
            :disabled="isUploading"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              {{ t('appAutomation.package.dragApkHere') }}
              <em>{{ t('appAutomation.package.clickToUpload') }}</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                {{ t('appAutomation.package.apkTip') }}
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <!-- 上传进度提示（放在上传区域下方） -->
        <div v-if="form.enable_apk_upload && isUploading" class="upload-progress">
          <el-progress :percentage="uploadProgress" :status="uploadStatus" />
          <el-text size="small" type="info">{{ uploadMessage }}</el-text>
        </div>
        
        <!-- 应用名称和包名 -->
        <el-form-item :label="t('appAutomation.package.packageName')" prop="name">
          <el-input 
            v-model="form.name" 
            :placeholder="t('appAutomation.package.packageNamePlaceholder')" 
            :disabled="isExtracting"
          />
        </el-form-item>
        <el-form-item :label="t('appAutomation.package.packageId')" prop="package_name">
          <el-input 
            v-model="form.package_name" 
            :placeholder="t('appAutomation.package.packageIdPlaceholder')"
            :disabled="isExtracting"
          />
          <!-- 提取状态提示 -->
          <div v-if="extractMessage" class="extract-message">
            <el-text size="small" :type="extractSuccess ? 'success' : 'warning'">
              {{ extractMessage }}
            </el-text>
          </div>
        </el-form-item>
        <!-- 备注字段 -->
        <el-form-item :label="t('appAutomation.package.remarks')">
          <el-input 
            v-model="form.remarks" 
            :placeholder="t('appAutomation.package.remarksPlaceholder')"
            maxlength="30"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('appAutomation.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">
          {{ t('appAutomation.common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'
import {
  getPackageList,
  createPackage,
  updatePackage,
  deletePackage,
  uploadAndExtractApk
} from '@/api/app-automation'
import { formatDateTime } from '@/utils/app-automation-helpers'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)
const packages = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const dialogVisible = ref(false)
const isEditing = ref(false)
const isExtracting = ref(false)
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadMessage = ref('')
const extractMessage = ref('')
const extractSuccess = ref(false)
const formRef = ref(null)
const uploadRef = ref(null)
const form = reactive({
  id: null,
  name: '',
  package_name: '',
  apk_file: null,
  apk_filepath: '',  // 保存上传后的文件路径
  apk_filename: '',  // 保存上传后的文件名
  remarks: '',       // 备注
  enable_apk_upload: false
})

const dialogTitle = computed(() => isEditing.value ? t('appAutomation.package.editPackage') : t('appAutomation.package.createPackage'))

const rules = computed(() => ({
  name: [{ required: true, message: t('appAutomation.package.packageNamePlaceholder'), trigger: 'blur' }],
  package_name: [{ required: true, message: t('appAutomation.package.packageIdPlaceholder'), trigger: 'blur' }]
}))

const handleApkChange = (file) => {
  // 验证文件类型
  if (!file.raw.name.toLowerCase().endsWith('.apk')) {
    ElMessage.error(t('appAutomation.messages.invalidApkFile'))
    uploadRef.value?.clearFiles()
    form.apk_file = null
    return
  }
  
  // 验证文件大小（500MB）
  const maxSize = 500 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error(t('appAutomation.messages.apkFileTooLarge'))
    uploadRef.value?.clearFiles()
    form.apk_file = null
    return
  }
  
  form.apk_file = file.raw
  extractMessage.value = ''
  extractSuccess.value = false
  
  // 自动提取 APK 信息
  simulateUploadAndExtract()
}

const handleUploadToggle = (enabled) => {
  if (!enabled) {
    // 关闭上传时清空文件
    form.apk_file = null
    uploadRef.value?.clearFiles()
    extractMessage.value = ''
    extractSuccess.value = false
  }
}

const simulateUploadAndExtract = async () => {
  if (!form.apk_file) return
  
  isUploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadMessage.value = t('appAutomation.messages.uploading')
  extractMessage.value = ''
  extractSuccess.value = false
  
  try {
    // 调用后端接口上传并提取
    const response = await uploadAndExtractApk(form.apk_file, (progressEvent) => {
      // 更新上传进度
      if (progressEvent.total) {
        const percentComplete = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress.value = percentComplete
      }
    })
    
    uploadMessage.value = t('appAutomation.messages.extracting')
    
    if (response.data.success) {
      // 提取成功，自动填充表单
      const data = response.data.data
      form.package_name = data.package_name || ''
      form.name = data.app_name || ''
      
      // 保存文件路径信息（用于后续提交）
      form.apk_filepath = data.apk_filepath || ''
      form.apk_filename = data.apk_filename || ''
      
      extractMessage.value = t('appAutomation.messages.apkExtractedAuto')
      extractSuccess.value = true
      uploadStatus.value = 'success'
      uploadMessage.value = t('appAutomation.messages.uploadSuccess')
      
      ElMessage.success(t('appAutomation.messages.apkInfoExtracted'))
    } else {
      // 提取失败，但文件已上传，保存路径信息
      const data = response.data.data || {}
      form.apk_filepath = data.apk_filepath || ''
      form.apk_filename = data.apk_filename || ''
      
      extractMessage.value = response.data.message || t('appAutomation.messages.extractFailedManual')
      extractSuccess.value = false
      uploadStatus.value = 'exception'
      uploadMessage.value = t('appAutomation.messages.uploadSuccess')
      
      ElMessage.warning(response.data.message || t('appAutomation.messages.extractFailedManual'))
    }
    
  } catch (error) {
    console.error('APK 上传失败:', error)
    uploadStatus.value = 'exception'
    uploadMessage.value = error.response?.data?.message || t('appAutomation.messages.uploadFailed')
    extractMessage.value = t('appAutomation.messages.extractFailedManual')
    extractSuccess.value = false
    ElMessage.error(error.response?.data?.message || error.message || t('appAutomation.messages.uploadFailed'))
  } finally {
    // 延迟隐藏进度条，让用户看到结果
    setTimeout(() => {
      isUploading.value = false
    }, 1500)
  }
}

const handleApkRemove = () => {
  form.apk_file = null
  extractMessage.value = ''
  extractSuccess.value = false
}

const extractApkInfo = async () => {
  if (!form.apk_file) {
    ElMessage.warning(t('appAutomation.messages.noApkFile'))
    return
  }
  
  isExtracting.value = true
  extractMessage.value = ''
  extractSuccess.value = false
  
  try {
    // 这里可以调用后端 API 来提取 APK 信息
    // 目前先模拟自动提取，实际应该在提交表单时由后端处理
    extractMessage.value = t('appAutomation.messages.apkExtracted')
    extractSuccess.value = true
    
    // 提示用户包名将自动提取
    ElMessage.info(t('appAutomation.messages.apkWillBeExtracted'))
  } catch (error) {
    extractMessage.value = t('appAutomation.messages.extractFailed')
    extractSuccess.value = false
    ElMessage.error(error.message || t('appAutomation.messages.extractFailed'))
  } finally {
    isExtracting.value = false
  }
}

const loadPackages = async () => {
  loading.value = true
  try {
    const res = await getPackageList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    const data = res.data
    const payload = data.success !== undefined ? data.data : data
    packages.value = payload?.results || payload || []
    total.value = payload?.count || packages.value.length || 0
  } catch (error) {
    console.error('加载应用包名失败:', error)
    packages.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.package_name = ''
  form.apk_file = null
  form.apk_filepath = ''
  form.apk_filename = ''
  form.remarks = ''
  form.enable_apk_upload = false
  formRef.value?.clearValidate()
}

const openCreateDialog = () => {
  isEditing.value = false
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEditing.value = true
  form.id = row.id
  form.name = row.name
  form.package_name = row.package_name
  dialogVisible.value = true
}

const submitForm = () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      // 注意：APK 文件已经在上一步 upload_apk 接口中上传并保存
      // 这里只需要提交基本信息和文件路径
      const payload = {
        name: form.name,
        package_name: form.package_name
      }
      
      // 如果有文件路径信息，添加到 payload
      if (form.apk_filepath) {
        payload.apk_filepath = form.apk_filepath
      }
      if (form.apk_filename) {
        payload.apk_filename = form.apk_filename
      }
      
      // 添加备注字段
      if (form.remarks) {
        payload.remarks = form.remarks
      }
      
      if (isEditing.value && form.id) {
        await updatePackage(form.id, payload)
        ElMessage.success(t('appAutomation.messages.updateSuccess'))
      } else {
        await createPackage(payload)
        ElMessage.success(t('appAutomation.messages.createSuccess'))
      }
      dialogVisible.value = false
      loadPackages()
    } catch (error) {
      console.error('保存应用包名失败:', error)
      ElMessage.error(error?.response?.data?.detail || t('appAutomation.messages.saveFailed'))
    } finally {
      saving.value = false
    }
  })
}

const handleDelete = (row) => {
  // 检查是否有 APK 文件
  const hasApkFile = row.apk_file_url || row.apk_filepath
  
  let confirmMessage = t('appAutomation.messages.deletePackageConfirm', { name: row.name })
  if (hasApkFile) {
    confirmMessage += '\n\n' + t('appAutomation.messages.deleteApkWarning')
  }
  
  ElMessageBox.confirm(
    confirmMessage,
    t('appAutomation.messages.deleteConfirmTitle'),
    { 
      type: 'warning',
      confirmButtonText: t('appAutomation.common.confirm'),
      cancelButtonText: t('appAutomation.common.cancel')
    }
  ).then(async () => {
    try {
      await deletePackage(row.id)
      ElMessage.success(t('appAutomation.messages.deleteSuccess'))
      loadPackages()
    } catch (error) {
      console.error('删除应用包名失败:', error)
      ElMessage.error(error?.response?.data?.detail || t('appAutomation.messages.deleteFailed'))
    }
  }).catch(() => {})
}

const downloadApk = (row) => {
  if (!row.apk_file_url) {
    ElMessage.warning(t('appAutomation.messages.noApkFile'))
    return
  }
  
  // 创建隐藏的 a 标签进行下载
  const link = document.createElement('a')
  link.href = row.apk_file_url
  link.download = `${row.name}_${row.package_name}.apk`
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  ElMessage.success(t('appAutomation.messages.downloadStarted'))
}

// formatDateTime 已从 app-automation-helpers 导入

onMounted(() => {
  loadPackages()
})
</script>

<style scoped lang="scss">
.app-package-list {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.extract-message {
  margin-top: 8px;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  border-left: 3px solid #67c23a;
}

.upload-progress {
  margin-top: 12px;
  padding: 12px;
  background-color: #f0f9ff;
  border-radius: 4px;
  border: 1px solid #d9ecff;
  
  .el-text {
    display: block;
    margin-top: 8px;
    text-align: center;
  }
}

:deep(.el-upload-dragger) {
  padding: 40px 20px;
}

:deep(.el-icon--upload) {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}

:deep(.el-upload__text) {
  color: #606266;
  font-size: 14px;
  
  em {
    color: #409eff;
    font-style: normal;
  }
}

:deep(.el-upload__tip) {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>
