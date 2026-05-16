<template>
  <div class="mapping-manager">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="filterType" placeholder="映射类型" clearable style="width: 140px" @change="handleFilter">
          <el-option label="手工标注" value="manual" />
          <el-option label="自动构建" value="auto" />
          <el-option label="AI 推断" value="ai" />
        </el-select>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索函数 / 测试用例..."
          clearable
          style="width: 260px; margin-left: 8px"
          @input="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
      <div class="toolbar-right">
        <el-button @click="openAutoBuild">
          <el-icon><MagicStick /></el-icon> 自动构建
        </el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog()">手工标注</el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table v-loading="loading" :data="tableData" border stripe style="width: 100%">
      <el-table-column prop="function_name" label="函数" min-width="200" show-overflow-tooltip />
      <el-table-column prop="file_path" label="文件路径" min-width="220" show-overflow-tooltip />
      <el-table-column prop="testcase_name" label="测试用例" min-width="200" show-overflow-tooltip />
      <el-table-column label="映射类型" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="mappingTypeTag(row.mapping_type)" size="small">{{ mappingTypeLabel(row.mapping_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="confidence_score" label="置信度" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            v-if="row.confidence_score != null"
            type="circle"
            :percentage="Math.round(row.confidence_score * 100)"
            :width="36"
            :stroke-width="4"
          />
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="155">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openDialog(row)"><el-icon><Edit /></el-icon></el-button>
          <el-button size="small" type="danger" plain @click="handleDelete(row)"><el-icon><Delete /></el-icon></el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="loadData"
      />
    </div>

    <!-- 手工标注弹窗 -->
    <el-dialog
      v-model="showDialog"
      :title="editingRecord ? '编辑映射' : '手工标注映射'"
      width="520px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="函数名" prop="function_name">
          <el-input v-model="form.function_name" placeholder="模块.函数名" />
        </el-form-item>
        <el-form-item label="文件路径" prop="file_path">
          <el-input v-model="form.file_path" placeholder="相对于仓库根目录" />
        </el-form-item>
        <el-form-item label="测试用例ID" prop="testcase">
          <el-input v-model.number="form.testcase" type="number" placeholder="测试用例 ID" />
        </el-form-item>
        <el-form-item label="映射类型">
          <el-radio-group v-model="form.mapping_type">
            <el-radio value="manual">手工标注</el-radio>
            <el-radio value="auto">自动构建</el-radio>
            <el-radio value="ai">AI 推断</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="置信度">
          <el-slider v-model="form.confidence_score" :min="0" :max="1" :step="0.01" show-input />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 自动构建进度弹窗 -->
    <el-dialog v-model="showAutoBuild" title="自动构建映射" width="460px" :close-on-click-modal="false">
      <div v-if="buildStatus === 'idle'">
        <el-form label-width="100px">
          <el-form-item label="仓库 ID">
            <el-input v-model.number="buildRepoId" type="number" placeholder="选填，不填则构建所有" />
          </el-form-item>
        </el-form>
      </div>
      <div v-else class="build-progress">
        <el-icon class="build-icon" :class="buildStatus">
          <Loading v-if="buildStatus === 'running'" />
          <CircleCheck v-else-if="buildStatus === 'done'" />
          <CircleClose v-else />
        </el-icon>
        <p>{{ buildMsg }}</p>
        <el-progress v-if="buildStatus === 'running'" :percentage="buildPct" :striped="true" :striped-flow="true" />
      </div>
      <template #footer>
        <el-button @click="showAutoBuild = false" :disabled="buildStatus === 'running'">关闭</el-button>
        <el-button v-if="buildStatus === 'idle'" type="primary" :loading="buildStatus === 'running'" @click="startAutoBuild">开始构建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search, MagicStick, Loading, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getMappings, createMapping, updateMapping, deleteMapping, autoBuildMappings } from '@/api/precision-testing'

const loading = ref(false)
const tableData = ref([])
const searchKeyword = ref('')
const filterType = ref('')
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const showDialog = ref(false)
const saving = ref(false)
const editingRecord = ref(null)
const formRef = ref(null)
const form = reactive({ function_name: '', file_path: '', testcase: null, mapping_type: 'manual', confidence_score: 1.0 })
const rules = {
  function_name: [{ required: true, message: '请输入函数名', trigger: 'blur' }],
  file_path: [{ required: true, message: '请输入文件路径', trigger: 'blur' }],
  testcase: [{ required: true, message: '请输入测试用例 ID', trigger: 'blur' }],
}

const showAutoBuild = ref(false)
const buildStatus = ref('idle') // idle | running | done | error
const buildMsg = ref('')
const buildPct = ref(0)
const buildRepoId = ref(null)

const formatDate = (v) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-'
const mappingTypeTag = (t) => ({ manual: 'success', auto: 'primary', ai: 'warning' }[t] || 'info')
const mappingTypeLabel = (t) => ({ manual: '手工标注', auto: '自动构建', ai: 'AI 推断' }[t] || t)

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (searchKeyword.value) params.search = searchKeyword.value
    if (filterType.value) params.mapping_type = filterType.value
    const res = await getMappings(params)
    tableData.value = res.data.results ?? res.data
    pagination.total = res.data.count ?? 0
  } catch {
    ElMessage.error('加载映射列表失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => { pagination.page = 1; loadData() }
let searchTimer = null
const handleSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { pagination.page = 1; loadData() }, 400)
}

const openDialog = (row = null) => {
  editingRecord.value = row
  if (row) Object.assign(form, { function_name: row.function_name, file_path: row.file_path, testcase: row.testcase, mapping_type: row.mapping_type, confidence_score: row.confidence_score ?? 1.0 })
  else resetForm()
  showDialog.value = true
}
const resetForm = () => {
  formRef.value?.resetFields()
  Object.assign(form, { function_name: '', file_path: '', testcase: null, mapping_type: 'manual', confidence_score: 1.0 })
}

const handleSave = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingRecord.value) {
      await updateMapping(editingRecord.value.id, { ...form })
      ElMessage.success('更新成功')
    } else {
      await createMapping({ ...form })
      ElMessage.success('标注成功')
    }
    showDialog.value = false; loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm('确认删除该映射关系？', '警告', { type: 'warning' })
  try { await deleteMapping(row.id); ElMessage.success('已删除'); loadData() } catch { ElMessage.error('删除失败') }
}

const openAutoBuild = () => { buildStatus.value = 'idle'; buildMsg.value = ''; buildPct.value = 0; buildRepoId.value = null; showAutoBuild.value = true }

const startAutoBuild = async () => {
  buildStatus.value = 'running'
  buildMsg.value = '正在自动构建映射关系...'
  buildPct.value = 20
  try {
    const data = buildRepoId.value ? { repo_id: buildRepoId.value } : {}
    await autoBuildMappings(data)
    buildStatus.value = 'done'
    buildMsg.value = '自动构建完成！'
    buildPct.value = 100
    loadData()
  } catch (e) {
    buildStatus.value = 'error'
    buildMsg.value = e?.response?.data?.detail || '构建失败'
  }
}

onMounted(loadData)
onBeforeUnmount(() => clearTimeout(searchTimer))
</script>

<style scoped>
.mapping-manager { padding: 20px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.toolbar-right { display: flex; gap: 8px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
.build-progress { display: flex; flex-direction: column; align-items: center; padding: 16px 0; gap: 10px; }
.build-icon { font-size: 40px; }
.build-icon.running { color: var(--el-color-primary); animation: spin 1s linear infinite; }
.build-icon.done { color: var(--el-color-success); }
.build-icon.error { color: var(--el-color-danger); }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
