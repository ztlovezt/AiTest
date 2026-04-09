<template>
  <div class="parameterized-data">
    <div class="page-header">
      <h2>{{ $t('apiTesting.parameterized.title') }}</h2>
      <div class="header-actions">
        <el-select v-model="selectedProject" :placeholder="$t('apiTesting.parameterized.selectProject')" @change="loadDatasets" style="width: 200px; margin-right: 10px">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-button type="primary" @click="showUploadDialog = true" :disabled="!selectedProject">
          <el-icon><Upload /></el-icon> {{ $t('apiTesting.parameterized.upload') }}
        </el-button>
        <el-button @click="showCreateDialog = true" :disabled="!selectedProject">
          <el-icon><Plus /></el-icon> {{ $t('apiTesting.parameterized.manual') }}
        </el-button>
      </div>
    </div>

    <!-- 数据集列表 -->
    <el-table :data="datasets" border stripe v-loading="loading">
      <el-table-column prop="name" :label="$t('apiTesting.parameterized.name')" min-width="150" />
      <el-table-column prop="data_type" :label="$t('apiTesting.parameterized.type')" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ row.data_type.toUpperCase() }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="row_count" :label="$t('apiTesting.parameterized.rows')" width="80" />
      <el-table-column :label="$t('apiTesting.parameterized.variables')" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="v in row.variables" :key="v" size="small" type="info" style="margin: 2px">{{ v }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_by_name" :label="$t('apiTesting.parameterized.creator')" width="100" />
      <el-table-column prop="created_at" :label="$t('apiTesting.parameterized.createdAt')" width="170">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('apiTesting.parameterized.actions')" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="previewDataset(row)">{{ $t('apiTesting.parameterized.preview') }}</el-button>
          <el-button size="small" type="primary" @click="openExecuteDialog(row)">{{ $t('apiTesting.parameterized.execute') }}</el-button>
          <el-button size="small" type="danger" @click="deleteDataset(row)">{{ $t('apiTesting.parameterized.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" :title="$t('apiTesting.parameterized.uploadTitle')" width="500px">
      <el-form label-width="100px">
        <el-form-item :label="$t('apiTesting.parameterized.name')">
          <el-input v-model="uploadForm.name" :placeholder="$t('apiTesting.parameterized.datasetName')" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.parameterized.file')">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".csv,.xlsx,.xls,.json"
            :on-change="(f) => uploadForm.file = f.raw"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">CSV / Excel / JSON</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">{{ $t('apiTesting.parameterized.cancel') }}</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">{{ $t('apiTesting.parameterized.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 手动创建对话框 -->
    <el-dialog v-model="showCreateDialog" :title="$t('apiTesting.parameterized.manualTitle')" width="700px">
      <el-form label-width="100px">
        <el-form-item :label="$t('apiTesting.parameterized.name')">
          <el-input v-model="manualForm.name" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.parameterized.columns')">
          <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center">
            <el-tag v-for="(col, i) in manualForm.columns" :key="i" closable @close="manualForm.columns.splice(i, 1)">{{ col }}</el-tag>
            <el-input v-model="newColumn" size="small" style="width: 120px" @keyup.enter="addColumn" :placeholder="$t('apiTesting.parameterized.addColumn')" />
            <el-button size="small" @click="addColumn">+</el-button>
          </div>
        </el-form-item>
        <el-form-item :label="$t('apiTesting.parameterized.data')">
          <el-table :data="manualForm.rows" border size="small" max-height="300">
            <el-table-column v-for="col in manualForm.columns" :key="col" :label="col" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row[col]" size="small" />
              </template>
            </el-table-column>
            <el-table-column width="60" fixed="right">
              <template #default="{ $index }">
                <el-button size="small" type="danger" :icon="Delete" circle @click="manualForm.rows.splice($index, 1)" />
              </template>
            </el-table-column>
          </el-table>
          <el-button size="small" style="margin-top: 8px" @click="addRow">+ {{ $t('apiTesting.parameterized.addRow') }}</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('apiTesting.parameterized.cancel') }}</el-button>
        <el-button type="primary" @click="handleManualCreate">{{ $t('apiTesting.parameterized.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog v-model="showPreviewDialog" :title="$t('apiTesting.parameterized.previewTitle')" width="700px">
      <el-table :data="previewRows" border size="small" max-height="400">
        <el-table-column v-for="col in previewColumns" :key="col" :prop="col" :label="col" min-width="120" show-overflow-tooltip />
      </el-table>
    </el-dialog>

    <!-- 执行对话框 -->
    <el-dialog v-model="showExecuteDialog" :title="$t('apiTesting.parameterized.executeTitle')" width="500px">
      <el-form label-width="100px">
        <el-form-item :label="$t('apiTesting.parameterized.dataset')">
          <span>{{ executeForm.datasetName }} ({{ executeForm.rowCount }} {{ $t('apiTesting.parameterized.rows') }})</span>
        </el-form-item>
        <el-form-item :label="$t('apiTesting.parameterized.targetApi')">
          <el-select v-model="executeForm.requestId" :placeholder="$t('apiTesting.parameterized.selectApi')" style="width: 100%" filterable>
            <el-option v-for="r in apiRequests" :key="r.id" :label="`${r.method} ${r.name}`" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('apiTesting.parameterized.environment')">
          <el-select v-model="executeForm.environmentId" :placeholder="$t('apiTesting.parameterized.optional')" style="width: 100%" clearable>
            <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExecuteDialog = false">{{ $t('apiTesting.parameterized.cancel') }}</el-button>
        <el-button type="primary" :loading="executing" @click="handleExecute">{{ $t('apiTesting.parameterized.runNow') }}</el-button>
      </template>
    </el-dialog>

    <!-- 执行结果对话框 -->
    <el-dialog v-model="showResultDialog" :title="$t('apiTesting.parameterized.resultTitle')" width="800px">
      <div v-if="executionResult" class="result-summary">
        <el-tag :type="executionResult.status === 'COMPLETED' ? 'success' : 'danger'" size="large" effect="dark">
          {{ executionResult.status }}
        </el-tag>
        <span style="margin-left: 12px">
          {{ $t('apiTesting.parameterized.total') }}: {{ executionResult.total_rows }} |
          {{ $t('apiTesting.parameterized.passed') }}: {{ executionResult.passed_rows }} |
          {{ $t('apiTesting.parameterized.failed') }}: {{ executionResult.failed_rows }}
        </span>
      </div>
      <el-table v-if="executionResult" :data="executionResult.results" border size="small" max-height="400" style="margin-top: 12px">
        <el-table-column prop="row" :label="$t('apiTesting.parameterized.rowNum')" width="60" />
        <el-table-column :label="$t('apiTesting.parameterized.data')" min-width="200">
          <template #default="{ row }">
            <span style="font-size: 12px; color: #606266">{{ JSON.stringify(row.data) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status_code" :label="$t('apiTesting.parameterized.statusCode')" width="90" />
        <el-table-column :label="$t('apiTesting.parameterized.time')" width="90">
          <template #default="{ row }">{{ row.response_time ? `${row.response_time}ms` : '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.parameterized.result')" width="80">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
              {{ row.passed ? $t('apiTesting.parameterized.pass') : $t('apiTesting.parameterized.fail') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.parameterized.error')" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled, Plus, Delete } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()

const projects = ref([])
const selectedProject = ref(null)
const datasets = ref([])
const apiRequests = ref([])
const environments = ref([])
const loading = ref(false)
const uploading = ref(false)
const executing = ref(false)

const showUploadDialog = ref(false)
const showCreateDialog = ref(false)
const showPreviewDialog = ref(false)
const showExecuteDialog = ref(false)
const showResultDialog = ref(false)

const uploadForm = ref({ name: '', file: null })
const manualForm = ref({ name: '', columns: [], rows: [] })
const newColumn = ref('')
const executeForm = ref({ datasetId: null, datasetName: '', rowCount: 0, requestId: null, environmentId: null })
const executionResult = ref(null)
const previewColumns = ref([])
const previewRows = ref([])

onMounted(async () => {
  try {
    const res = await api.get('/api-testing/projects/')
    projects.value = res.data.results || res.data || []
    if (projects.value.length) {
      selectedProject.value = projects.value[0].id
      loadDatasets()
    }
  } catch (e) { /* ignore */ }
})

async function loadDatasets() {
  if (!selectedProject.value) return
  loading.value = true
  try {
    const [dsRes, reqRes, envRes] = await Promise.all([
      api.get('/api-testing/parameterized-datasets/', { params: { project: selectedProject.value } }),
      api.get('/api-testing/requests/'),
      api.get('/api-testing/environments/', { params: { scope: 'GLOBAL' } }),
    ])
    datasets.value = dsRes.data.results || dsRes.data || []
    apiRequests.value = reqRes.data.results || reqRes.data || []
    environments.value = envRes.data.results || envRes.data || []
  } catch (e) {
    ElMessage.error(t('apiTesting.parameterized.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  if (!uploadForm.value.file) {
    ElMessage.warning(t('apiTesting.parameterized.selectFile'))
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadForm.value.file)
    formData.append('name', uploadForm.value.name || uploadForm.value.file.name)
    formData.append('project', selectedProject.value)
    await api.post('/api-testing/parameterized-datasets/upload/', formData)
    ElMessage.success(t('apiTesting.parameterized.uploadSuccess'))
    showUploadDialog.value = false
    uploadForm.value = { name: '', file: null }
    loadDatasets()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || t('apiTesting.parameterized.uploadFailed'))
  } finally {
    uploading.value = false
  }
}

function addColumn() {
  if (newColumn.value.trim() && !manualForm.value.columns.includes(newColumn.value.trim())) {
    manualForm.value.columns.push(newColumn.value.trim())
    manualForm.value.rows.forEach(row => { row[newColumn.value.trim()] = '' })
    newColumn.value = ''
  }
}

function addRow() {
  const row = {}
  manualForm.value.columns.forEach(c => { row[c] = '' })
  manualForm.value.rows.push(row)
}

async function handleManualCreate() {
  if (!manualForm.value.name || !manualForm.value.columns.length || !manualForm.value.rows.length) {
    ElMessage.warning(t('apiTesting.parameterized.fillRequired'))
    return
  }
  try {
    await api.post('/api-testing/parameterized-datasets/', {
      name: manualForm.value.name,
      project: selectedProject.value,
      data_type: 'manual',
      data: manualForm.value.rows,
    })
    ElMessage.success(t('apiTesting.parameterized.createSuccess'))
    showCreateDialog.value = false
    manualForm.value = { name: '', columns: [], rows: [] }
    loadDatasets()
  } catch (e) {
    ElMessage.error(t('apiTesting.parameterized.createFailed'))
  }
}

function previewDataset(row) {
  previewColumns.value = row.variables || []
  previewRows.value = row.data || []
  showPreviewDialog.value = true
}

function openExecuteDialog(row) {
  executeForm.value = {
    datasetId: row.id,
    datasetName: row.name,
    rowCount: row.row_count,
    requestId: null,
    environmentId: null,
  }
  showExecuteDialog.value = true
}

async function handleExecute() {
  if (!executeForm.value.requestId) {
    ElMessage.warning(t('apiTesting.parameterized.selectApi'))
    return
  }
  executing.value = true
  try {
    const res = await api.post('/api-testing/parameterized-executions/execute/', {
      request_id: executeForm.value.requestId,
      dataset_id: executeForm.value.datasetId,
      environment_id: executeForm.value.environmentId,
    })
    executionResult.value = res.data
    showExecuteDialog.value = false
    showResultDialog.value = true
    ElMessage.success(t('apiTesting.parameterized.executeSuccess'))
  } catch (e) {
    ElMessage.error(e.response?.data?.error || t('apiTesting.parameterized.executeFailed'))
  } finally {
    executing.value = false
  }
}

async function deleteDataset(row) {
  try {
    await ElMessageBox.confirm(t('apiTesting.parameterized.confirmDelete'), { type: 'warning' })
    await api.delete(`/api-testing/parameterized-datasets/${row.id}/`)
    ElMessage.success(t('apiTesting.parameterized.deleteSuccess'))
    loadDatasets()
  } catch (e) { /* cancelled */ }
}

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm:ss') : '-'
}
</script>

<style scoped>
.parameterized-data {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
}
.header-actions {
  display: flex;
  align-items: center;
}
.result-summary {
  display: flex;
  align-items: center;
  font-size: 14px;
}
</style>
