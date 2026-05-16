<template>
  <div class="repo-bindings">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索仓库名称..."
          clearable
          style="width: 260px"
          @input="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" :icon="Plus" @click="openDialog()">绑定仓库</el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column label="仓库名称" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ displayValue(row.name) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="仓库地址" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ displayValue(row.repo_url) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分支" width="120">
        <template #default="{ row }">
          <span>{{ displayValue(row.branch) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="所属项目" width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ getProjectDisplayName(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_analyzed_at" label="最近分析" width="160">
        <template #default="{ row }">
          <span>{{ row.last_analyzed_at ? formatDate(row.last_analyzed_at) : '从未' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="triggerAnalyze(row)">
            <el-icon><VideoPlay /></el-icon> 触发分析
          </el-button>
          <el-button size="small" @click="openDialog(row)"><el-icon><Edit /></el-icon></el-button>
          <el-button size="small" type="danger" plain @click="handleDelete(row)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @change="loadData"
      />
    </div>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="showDialog"
      :title="editingRecord ? '编辑仓库绑定' : '绑定新仓库'"
      width="560px"
      @close="resetForm"
    >
      <el-form
        v-loading="dialogLoading"
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        label-position="right"
      >
        <el-form-item label="仓库名称" prop="name">
          <el-input v-model="form.name" placeholder="例：backend-service" />
        </el-form-item>
        <el-form-item label="仓库地址" prop="repo_url">
          <el-input v-model="form.repo_url" placeholder="https://github.com/org/repo.git" />
        </el-form-item>
        <el-form-item label="分支" prop="branch">
          <el-input v-model="form.branch" placeholder="main" />
        </el-form-item>
        <el-form-item label="本地路径" prop="local_path">
          <el-input v-model="form.local_path" placeholder="服务器上的本地克隆路径" />
        </el-form-item>
        <el-form-item label="所属项目" prop="project">
          <el-select
            v-model="form.project"
            placeholder="请选择所属项目"
            filterable
            clearable
            style="width: 100%"
            :loading="projectsLoading"
          >
            <el-option
              v-for="item in projectOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="dialogLoading" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分析进度弹窗 -->
    <el-dialog
      v-model="showProgress"
      title="触发分析"
      width="420px"
      :close-on-click-modal="false"
      @close="stopPolling"
    >
      <div class="progress-content">
        <el-icon class="progress-icon" :class="progressStatus"><Loading v-if="progressStatus === 'running'" /><CircleCheck v-else-if="progressStatus === 'done'" /><CircleClose v-else /></el-icon>
        <p class="progress-msg">{{ progressMsg }}</p>
        <el-progress v-if="progressStatus === 'running'" :percentage="progressPct" :striped="true" :striped-flow="true" :duration="10" />
      </div>
      <template #footer>
        <el-button @click="handleCancelProgress">{{ progressStatus === 'running' ? '取消' : '关闭' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search, VideoPlay, Loading, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import {
  getRepoBindings,
  getProjectOptions,
  createRepoBinding,
  getRepoBindingDetail,
  updateRepoBinding,
  deleteRepoBinding,
  triggerAnalysis,
  getAnalysisProgress,
} from '@/api/precision-testing'

const createDefaultForm = () => ({
  name: '',
  repo_url: '',
  branch: 'main',
  local_path: '',
  project: null,
  is_active: true,
})

// ── 列表状态 ──
const loading = ref(false)
const tableData = ref([])
const searchKeyword = ref('')
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const projectOptions = ref([])
const projectsLoading = ref(false)

// ── 弹窗状态 ──
const showDialog = ref(false)
const dialogLoading = ref(false)
const saving = ref(false)
const editingRecord = ref(null)
const formRef = ref(null)
const form = reactive(createDefaultForm())
const rules = {
  name: [{ required: true, message: '请输入仓库名称', trigger: 'blur' }],
  repo_url: [{ required: true, message: '请输入仓库地址', trigger: 'blur' }],
  branch: [{ required: true, message: '请输入分支名称', trigger: 'blur' }],
  local_path: [{ required: true, message: '请输入本地路径', trigger: 'blur' }],
  project: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
}

// ── 进度状态 ──
const showProgress = ref(false)
const progressStatus = ref('running') // running | done | error
const progressMsg = ref('正在触发分析...')
const progressPct = ref(0)
let progressTimer = null
let pollingAnalysisId = null
let pollingToken = 0 // 取消令牌：每次新轮询自增，旧轮询通过比对失效

// 停止当前轮询（清理定时器 + 失效令牌 + 重置状态）
const stopPolling = () => {
  pollingToken++
  if (progressTimer) {
    clearTimeout(progressTimer)
    progressTimer = null
  }
  pollingAnalysisId = null
}

// 用户点击「取消/关闭」
const handleCancelProgress = () => {
  stopPolling()
  showProgress.value = false
}

// ── 工具函数 ──
const formatDate = (val) => dayjs(val).format('YYYY-MM-DD HH:mm')
const displayValue = (value, fallback = '-') => (value === 0 || value ? value : fallback)

const toProjectId = (value) => {
  if (value === null || value === undefined || value === '') return null
  const rawValue = typeof value === 'object' ? value.id : value
  const normalizedValue = Number(rawValue)
  return Number.isFinite(normalizedValue) ? normalizedValue : null
}

const findProjectNameById = (projectId) => {
  const normalizedId = toProjectId(projectId)
  if (normalizedId === null) return ''
  const target = projectOptions.value.find((item) => Number(item.id) === normalizedId)
  return target?.name || ''
}

const normalizeRepoBinding = (raw = {}) => {
  const projectId = toProjectId(raw.project)
  return {
    ...raw,
    name: raw.name || '',
    repo_url: raw.repo_url || '',
    branch: raw.branch || raw.default_branch || '',
    local_path: raw.local_path || raw.repo_path || '',
    project: projectId,
    project_name: raw.project_name || raw.project?.name || findProjectNameById(projectId),
    is_active: raw.is_active ?? true,
    last_analyzed_at: raw.last_analyzed_at || null,
  }
}

const getProjectDisplayName = (row = {}) => normalizeRepoBinding(row).project_name || '-'
const getRepoDisplayName = (row = {}) => normalizeRepoBinding(row).name || '未命名仓库'

const applyFormData = (raw = {}) => {
  const normalized = normalizeRepoBinding(raw)
  Object.assign(form, {
    name: normalized.name,
    repo_url: normalized.repo_url,
    branch: normalized.branch || 'main',
    local_path: normalized.local_path,
    project: normalized.project,
    is_active: normalized.is_active,
  })
  return normalized
}

// ── 数据加载 ──
const loadProjects = async () => {
  if (projectOptions.value.length > 0) return projectOptions.value

  projectsLoading.value = true
  try {
    const res = await getProjectOptions()
    projectOptions.value = res.data?.results ?? res.data ?? []
    return projectOptions.value
  } catch {
    ElMessage.error('加载项目列表失败')
    return []
  } finally {
    projectsLoading.value = false
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getRepoBindings({
      page: pagination.page,
      page_size: pagination.pageSize,
      search: searchKeyword.value || undefined,
    })
    const rows = res.data?.results ?? res.data ?? []
    tableData.value = Array.isArray(rows) ? rows.map(normalizeRepoBinding) : []
    pagination.total = res.data?.count ?? tableData.value.length
  } catch {
    ElMessage.error('加载仓库列表失败')
  } finally {
    loading.value = false
  }
}

let searchTimer = null
const handleSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.page = 1
    loadData()
  }, 400)
}

// ── 弹窗操作 ──
const openDialog = async (row = null) => {
  resetForm()
  if (row) {
    editingRecord.value = normalizeRepoBinding(row)
  }

  showDialog.value = true
  await loadProjects()

  if (!row) {
    formRef.value?.clearValidate()
    return
  }

  dialogLoading.value = true
  try {
    const res = await getRepoBindingDetail(row.id)
    editingRecord.value = applyFormData(res.data)
  } catch {
    editingRecord.value = applyFormData(row)
    ElMessage.warning('仓库详情加载失败，已使用列表数据回填')
  } finally {
    dialogLoading.value = false
    formRef.value?.clearValidate()
  }
}

const resetForm = () => {
  formRef.value?.clearValidate()
  Object.assign(form, createDefaultForm())
  editingRecord.value = null
  dialogLoading.value = false
}

const handleSave = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const payload = {
    ...form,
    project: toProjectId(form.project),
  }

  saving.value = true
  try {
    if (editingRecord.value) {
      await updateRepoBinding(editingRecord.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createRepoBinding(payload)
      ElMessage.success('绑定成功')
    }
    showDialog.value = false
    await loadData()
  } catch (e) {
    const data = e?.response?.data
    let msg = '操作失败'
    if (data) {
      if (data.detail) {
        msg = data.detail
      } else if (typeof data === 'object') {
        const first = Object.entries(data).find(([key]) => key !== 'non_field_errors')
        if (first) {
          const [field, errors] = first
          const fieldLabel = {
            project: '所属项目',
            name: '仓库名称',
            repo_url: '仓库地址',
            branch: '分支',
            default_branch: '分支',
            local_path: '本地路径',
            repo_path: '本地路径',
          }[field] || field
          msg = `${fieldLabel}：${Array.isArray(errors) ? errors[0] : errors}`
        } else if (data.non_field_errors) {
          msg = Array.isArray(data.non_field_errors) ? data.non_field_errors[0] : data.non_field_errors
        }
      }
    }
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确认删除仓库绑定「${getRepoDisplayName(row)}」？`, '警告', { type: 'warning' })
  try {
    await deleteRepoBinding(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch {
    ElMessage.error('删除失败')
  }
}

// ── 触发分析 + 进度轮询 ──
const triggerAnalyze = async (row) => {
  stopPolling()
  showProgress.value = true
  progressStatus.value = 'running'
  progressMsg.value = '正在触发分析任务...'
  progressPct.value = 10
  try {
    const res = await triggerAnalysis(row.id)
    pollingAnalysisId = res.data?.analysis_id
    progressMsg.value = '分析任务已启动，正在处理...'
    progressPct.value = 30
    if (pollingAnalysisId) {
      startPolling(pollingAnalysisId)
    } else {
      progressStatus.value = 'done'
      progressMsg.value = '触发成功'
      progressPct.value = 100
      await loadData()
    }
  } catch (e) {
    progressStatus.value = 'error'
    progressMsg.value = e?.response?.data?.detail || '触发失败'
  }
}

const startPolling = (analysisId) => {
  const myToken = ++pollingToken
  clearTimeout(progressTimer)
  progressTimer = setTimeout(async () => {
    if (!showProgress.value || myToken !== pollingToken) return
    try {
      const res = await getAnalysisProgress(analysisId)
      if (!showProgress.value || myToken !== pollingToken) return
      const { status, progress } = res.data
      progressPct.value = Math.min(progress ?? progressPct.value + 10, 95)
      if (status === 'completed') {
        progressStatus.value = 'done'
        progressMsg.value = '分析完成！'
        progressPct.value = 100
        pollingAnalysisId = null
        await loadData()
      } else if (status === 'failed') {
        progressStatus.value = 'error'
        progressMsg.value = res.data.error_message || '分析失败'
        pollingAnalysisId = null
      } else {
        progressMsg.value = `分析中（${status}）...`
        startPolling(analysisId)
      }
    } catch {
      if (!showProgress.value || myToken !== pollingToken) return
      progressStatus.value = 'error'
      progressMsg.value = '进度查询失败'
    }
  }, 2000)
}

onMounted(async () => {
  await loadProjects()
  await loadData()
})

onBeforeUnmount(() => {
  stopPolling()
  clearTimeout(searchTimer)
})
</script>

<style scoped>
.repo-bindings { padding: 20px; }
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.progress-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  gap: 12px;
}
.progress-icon { font-size: 40px; }
.progress-icon.running { color: var(--el-color-primary); animation: spin 1s linear infinite; }
.progress-icon.done { color: var(--el-color-success); }
.progress-icon.error { color: var(--el-color-danger); }
.progress-msg { font-size: 14px; color: var(--el-text-color-regular); }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
