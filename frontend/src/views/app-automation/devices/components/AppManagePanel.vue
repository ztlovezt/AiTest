<template>
  <div class="app-manage-panel">
    <div class="panel-header">
      <div>
        <h4>应用管理</h4>
        <p>管理当前设备上的应用安装、启动、停止和卸载。</p>
      </div>
      <el-button :loading="loadingCurrentApp" @click="loadCurrentApp">刷新前台应用</el-button>
    </div>

    <div class="panel-grid">
      <el-card shadow="never" class="summary-card">
        <template #header>
          <span>当前前台应用</span>
        </template>
        <div class="summary-item">
          <span class="label">包名</span>
          <span class="value">{{ currentApp.package_name || '-' }}</span>
        </div>
        <div class="summary-item">
          <span class="label">Activity</span>
          <span class="value">{{ currentApp.activity || '-' }}</span>
        </div>
      </el-card>

      <el-card shadow="never" class="library-card">
        <template #header>
          <span>应用库操作</span>
        </template>

        <el-form label-width="88px" size="small">
          <el-form-item label="应用包">
            <el-select v-model="selectedPackageId" filterable placeholder="请选择应用包" style="width: 100%" @change="handlePackageChange">
              <el-option v-for="pkg in packages" :key="pkg.id" :label="`${pkg.name} (${pkg.package_name})`" :value="pkg.id" />
            </el-select>
          </el-form-item>

          <el-form-item label="应用名称">
            <el-input :model-value="selectedPackage?.name || ''" disabled />
          </el-form-item>

          <el-form-item label="包名">
            <el-input :model-value="selectedPackage?.package_name || ''" disabled />
          </el-form-item>

          <el-form-item label="APK文件">
            <el-tag :type="selectedPackageHasApk ? 'success' : 'info'" effect="plain">
              {{ selectedPackageHasApk ? '已上传' : '未上传' }}
            </el-tag>
          </el-form-item>

          <div class="action-row">
            <el-button type="primary" :disabled="!selectedPackageHasApk" :loading="installingFromLibrary" @click="installFromLibrary">安装到设备</el-button>
            <el-button :disabled="!selectedPackage" :loading="actionLoading.launch" @click="launchSelectedApp">启动</el-button>
            <el-button :disabled="!selectedPackage" :loading="actionLoading.stop" @click="stopSelectedApp">停止</el-button>
            <el-button :disabled="!selectedPackage" :loading="actionLoading.clear" @click="clearSelectedApp">清数据</el-button>
            <el-button type="danger" plain :disabled="!selectedPackage" :loading="actionLoading.uninstall" @click="uninstallSelectedApp">卸载</el-button>
          </div>
        </el-form>
      </el-card>

      <el-card shadow="never" class="upload-card">
        <template #header>
          <span>临时上传并安装</span>
        </template>

        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          drag
          accept=".apk"
          :on-change="handleApkChange"
          :on-remove="handleApkRemove"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽 APK 到此处，或 <em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 .apk，上传后会先提取信息再安装到当前设备。</div>
          </template>
        </el-upload>

        <div v-if="isUploading" class="upload-progress">
          <el-progress :percentage="uploadProgress" :status="uploadStatus" />
          <div class="upload-message">{{ uploadMessage }}</div>
        </div>

        <div v-if="tempApk.apk_filepath" class="temp-apk-summary">
          <div class="summary-item">
            <span class="label">应用名称</span>
            <span class="value">{{ tempApk.app_name || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">包名</span>
            <span class="value">{{ tempApk.package_name || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">文件</span>
            <span class="value ellipsis">{{ tempApk.apk_filename }}</span>
          </div>
          <div class="action-row compact">
            <el-button type="primary" :loading="installingTempApk" @click="installTempApk">安装到设备</el-button>
            <el-button :disabled="!tempApk.package_name" :loading="actionLoading.launchTemp" @click="launchTempApp">安装后启动</el-button>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="output-card">
        <template #header>
          <span>最近操作输出</span>
        </template>
        <pre>{{ lastOutput || '暂无输出' }}</pre>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import {
  clearDeviceAppData,
  getDeviceCurrentApp,
  getPackageList,
  installApkToDevice,
  launchDeviceApp,
  stopDeviceApp,
  uninstallDeviceApp,
  uploadAndExtractApk,
} from '@/api/app-automation'

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['current-app-change', 'operation'])

const loadingCurrentApp = ref(false)
const installingFromLibrary = ref(false)
const installingTempApk = ref(false)
const packages = ref([])
const selectedPackageId = ref(null)
const currentApp = ref({ package_name: '', activity: '' })
const lastOutput = ref('')
const uploadRef = ref(null)
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadMessage = ref('')
const tempApk = reactive({
  package_name: '',
  app_name: '',
  apk_filepath: '',
  apk_filename: '',
})
const actionLoading = reactive({
  launch: false,
  stop: false,
  clear: false,
  uninstall: false,
  launchTemp: false,
})

const selectedPackage = computed(() => packages.value.find((item) => item.id === selectedPackageId.value) || null)
const selectedPackageHasApk = computed(() => Boolean(selectedPackage.value?.apk_filepath || selectedPackage.value?.apk_file_url))

const logOperation = (message, level = 'info', extra = null) => {
  emit('operation', {
    source: 'apps',
    level,
    message,
    extra,
    timestamp: Date.now(),
  })
}

const setOutput = (message, payload = null) => {
  lastOutput.value = [message, payload ? JSON.stringify(payload, null, 2) : ''].filter(Boolean).join('\n\n')
}

const loadPackages = async () => {
  try {
    const response = await getPackageList({ page: 1, page_size: 1000 })
    const payload = response.data?.success !== undefined ? response.data?.data : response.data
    packages.value = payload?.results || payload || []
  } catch (error) {
    console.error('Failed to load package list:', error)
    ElMessage.error('加载应用包列表失败')
    logOperation('加载应用包列表失败', 'error', error?.response?.data || error?.message)
  }
}

const loadCurrentApp = async () => {
  loadingCurrentApp.value = true
  try {
    const response = await getDeviceCurrentApp(props.deviceId)
    currentApp.value = response.data?.data || { package_name: '', activity: '' }
    emit('current-app-change', currentApp.value)
  } catch (error) {
    console.error('Failed to load current app:', error)
    ElMessage.error(error?.response?.data?.message || error.message || '加载前台应用失败')
    logOperation('加载前台应用失败', 'error', error?.response?.data || error?.message)
  } finally {
    loadingCurrentApp.value = false
  }
}

const handlePackageChange = async () => {
  if (!selectedPackage.value) {
    return
  }
  if (selectedPackage.value.package_name) {
    currentApp.value.package_name = currentApp.value.package_name || ''
  }
}

const installFromLibrary = async () => {
  if (!selectedPackageId.value) {
    ElMessage.warning('请先选择应用包')
    return
  }
  installingFromLibrary.value = true
  try {
    const response = await installApkToDevice(props.deviceId, { package_id: selectedPackageId.value })
    setOutput('应用库安装成功', response.data?.data)
    ElMessage.success(response.data?.message || '安装成功')
    logOperation(`应用库安装成功: ${selectedPackage.value?.package_name || selectedPackageId.value}`, 'success', response.data?.data)
    await loadCurrentApp()
  } catch (error) {
    console.error('Install from library failed:', error)
    ElMessage.error(error?.response?.data?.message || error.message || '安装失败')
    logOperation(`应用库安装失败: ${selectedPackage.value?.package_name || selectedPackageId.value}`, 'error', error?.response?.data || error?.message)
  } finally {
    installingFromLibrary.value = false
  }
}

const launchSelectedApp = async () => {
  if (!selectedPackage.value) {
    ElMessage.warning('请先选择应用包')
    return
  }
  actionLoading.launch = true
  try {
    const response = await launchDeviceApp(props.deviceId, { package_name: selectedPackage.value.package_name })
    setOutput('应用启动成功', response.data?.data)
    ElMessage.success(response.data?.message || '启动成功')
    logOperation(`应用启动成功: ${selectedPackage.value.package_name}`, 'success', response.data?.data)
    await loadCurrentApp()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error.message || '启动失败')
    logOperation(`应用启动失败: ${selectedPackage.value.package_name}`, 'error', error?.response?.data || error?.message)
  } finally {
    actionLoading.launch = false
  }
}

const stopSelectedApp = async () => {
  if (!selectedPackage.value) {
    ElMessage.warning('请先选择应用包')
    return
  }
  actionLoading.stop = true
  try {
    const response = await stopDeviceApp(props.deviceId, { package_name: selectedPackage.value.package_name })
    setOutput('应用已停止', response.data?.data)
    ElMessage.success(response.data?.message || '应用已停止')
    logOperation(`应用已停止: ${selectedPackage.value.package_name}`, 'success', response.data?.data)
    await loadCurrentApp()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error.message || '停止失败')
    logOperation(`应用停止失败: ${selectedPackage.value.package_name}`, 'error', error?.response?.data || error?.message)
  } finally {
    actionLoading.stop = false
  }
}

const clearSelectedApp = async () => {
  if (!selectedPackage.value) {
    ElMessage.warning('请先选择应用包')
    return
  }
  actionLoading.clear = true
  try {
    const response = await clearDeviceAppData(props.deviceId, { package_name: selectedPackage.value.package_name })
    setOutput('应用数据已清理', response.data?.data)
    ElMessage.success(response.data?.message || '清理成功')
    logOperation(`应用数据已清理: ${selectedPackage.value.package_name}`, 'success', response.data?.data)
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error.message || '清理失败')
    logOperation(`应用清理失败: ${selectedPackage.value.package_name}`, 'error', error?.response?.data || error?.message)
  } finally {
    actionLoading.clear = false
  }
}

const uninstallSelectedApp = async () => {
  if (!selectedPackage.value) {
    ElMessage.warning('请先选择应用包')
    return
  }
  try {
    await ElMessageBox.confirm(`确定卸载 ${selectedPackage.value.name} 吗？`, '卸载确认', {
      type: 'warning',
    })
  } catch {
    return
  }

  actionLoading.uninstall = true
  try {
    const response = await uninstallDeviceApp(props.deviceId, { package_name: selectedPackage.value.package_name })
    setOutput('应用卸载成功', response.data?.data)
    ElMessage.success(response.data?.message || '卸载成功')
    logOperation(`应用卸载成功: ${selectedPackage.value.package_name}`, 'success', response.data?.data)
    await loadCurrentApp()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error.message || '卸载失败')
    logOperation(`应用卸载失败: ${selectedPackage.value.package_name}`, 'error', error?.response?.data || error?.message)
  } finally {
    actionLoading.uninstall = false
  }
}

const handleApkChange = async (file) => {
  if (!file.raw?.name?.toLowerCase().endsWith('.apk')) {
    ElMessage.error('无效的文件类型，请选择 .apk 文件')
    uploadRef.value?.clearFiles()
    return
  }

  isUploading.value = true
  uploadStatus.value = ''
  uploadProgress.value = 0
  uploadMessage.value = '正在上传...'

  try {
    const response = await uploadAndExtractApk(file.raw, (progressEvent) => {
      if (progressEvent.total) {
        uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      }
    })

    const data = response.data?.data || {}
    tempApk.package_name = data.package_name || ''
    tempApk.app_name = data.app_name || ''
    tempApk.apk_filepath = data.apk_filepath || ''
    tempApk.apk_filename = data.apk_filename || ''
    uploadStatus.value = response.data.success ? 'success' : 'warning'
    uploadMessage.value = response.data.success ? 'APK 提取完成' : (response.data.message || 'APK 已上传')
    setOutput('临时 APK 上传完成', data)
    if (response.data.success) {
      ElMessage.success('APK 上传并提取成功')
      logOperation(`临时 APK 上传并提取成功: ${data.package_name || data.apk_filename}`, 'success', data)
    } else {
      ElMessage.warning(response.data.message || 'APK 已上传，但信息提取不完整')
      logOperation('临时 APK 上传成功，但提取信息不完整', 'warning', data)
    }
  } catch (error) {
    uploadStatus.value = 'exception'
    uploadMessage.value = error?.response?.data?.message || error.message || '上传失败'
    ElMessage.error(uploadMessage.value)
    logOperation('临时 APK 上传失败', 'error', error?.response?.data || error?.message)
  } finally {
    setTimeout(() => {
      isUploading.value = false
    }, 500)
  }
}

const handleApkRemove = () => {
  tempApk.package_name = ''
  tempApk.app_name = ''
  tempApk.apk_filepath = ''
  tempApk.apk_filename = ''
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadMessage.value = ''
}

const installTempApk = async ({ silent = false } = {}) => {
  if (!tempApk.apk_filepath) {
    if (!silent) {
      ElMessage.warning('请先上传 APK')
    }
    return false
  }
  installingTempApk.value = true
  try {
    const response = await installApkToDevice(props.deviceId, { apk_filepath: tempApk.apk_filepath })
    setOutput('临时 APK 安装成功', response.data?.data)
    if (!silent) {
      ElMessage.success(response.data?.message || '安装成功')
    }
    logOperation(`临时 APK 安装成功: ${tempApk.package_name || tempApk.apk_filename}`, 'success', response.data?.data)
    await loadCurrentApp()
    return true
  } catch (error) {
    if (!silent) {
      ElMessage.error(error?.response?.data?.message || error.message || '安装失败')
    }
    logOperation(`临时 APK 安装失败: ${tempApk.package_name || tempApk.apk_filename}`, 'error', error?.response?.data || error?.message)
    return false
  } finally {
    installingTempApk.value = false
  }
}

const launchTempApp = async () => {
  if (!tempApk.package_name) {
    ElMessage.warning('当前临时 APK 缺少包名')
    return
  }
  actionLoading.launchTemp = true
  try {
    const installed = await installTempApk({ silent: true })
    if (!installed) {
      ElMessage.error('安装失败，无法继续启动应用')
      return
    }
    const response = await launchDeviceApp(props.deviceId, { package_name: tempApk.package_name })
    setOutput('临时 APK 已安装并启动', response.data?.data)
    ElMessage.success(response.data?.message || '启动成功')
    logOperation(`临时 APK 已安装并启动: ${tempApk.package_name}`, 'success', response.data?.data)
    await loadCurrentApp()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error.message || '启动失败')
    logOperation(`临时 APK 启动失败: ${tempApk.package_name}`, 'error', error?.response?.data || error?.message)
  } finally {
    actionLoading.launchTemp = false
  }
}

onMounted(async () => {
  await Promise.all([loadPackages(), loadCurrentApp()])
})
</script>

<style scoped>
.app-manage-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.panel-header h4 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.panel-header p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.summary-card,
.library-card,
.upload-card,
.output-card {
  border-radius: 16px;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.action-row.compact {
  margin-top: 16px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
}

.summary-item:last-child {
  border-bottom: 0;
}

.label {
  color: #6b7280;
  flex-shrink: 0;
}

.value {
  color: #111827;
  text-align: right;
  word-break: break-all;
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 260px;
}

.upload-progress {
  margin-top: 16px;
}

.upload-message {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.temp-apk-summary {
  margin-top: 16px;
}

.output-card pre {
  margin: 0;
  min-height: 180px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1200px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }
}
</style>
