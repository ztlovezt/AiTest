<template>
  <el-dialog
    v-model="visible"
    :title="t('execution.selectTestcasesDialog')"
    width="1100px"
    :close-on-click-modal="false"
    @opened="handleDialogOpened"
    @close="handleClose"
    class="testcase-selector-dialog"
  >
    <!-- 筛选区域 -->
    <div class="filter-bar">
      <el-form :inline="true" @submit.prevent="fetchTestcases">
        <el-form-item :label="t('execution.keyword')">
          <el-input
            v-model="filters.keyword"
            :placeholder="t('execution.searchByTitleOrNumber')"
            clearable
            style="width: 220px"
            @keyup.enter="fetchTestcases"
          />
        </el-form-item>
        <el-form-item :label="t('execution.priority')">
          <el-select
            v-model="filters.priority"
            :placeholder="t('execution.allPriorities')"
            clearable
            style="width: 140px"
          >
            <el-option label="紧急" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('execution.testType')">
          <el-select
            v-model="filters.testType"
            :placeholder="t('execution.allTypes')"
            clearable
            style="width: 140px"
          >
            <el-option label="功能测试" value="functional" />
            <el-option label="集成测试" value="integration" />
            <el-option label="API测试" value="api" />
            <el-option label="UI测试" value="ui" />
            <el-option label="性能测试" value="performance" />
            <el-option label="安全测试" value="security" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchTestcases">{{ t('common.search') }}</el-button>
          <el-button @click="resetFilters">{{ t('common.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 已选提示 -->
    <div class="selected-summary" v-if="selectedIds.length > 0">
      {{ t('execution.selectedCount', { count: selectedIds.length }) }}
      <el-button type="primary" link @click="showSelectedDrawer">{{ t('execution.viewSelected') }}</el-button>
    </div>

    <!-- 表格区域 -->
    <el-table
      ref="tableRef"
      :data="testcases"
      v-loading="loading"
      @selection-change="handleSelectionChange"
      @row-click="handleRowClick"
      row-key="id"
      style="width: 100%"
      max-height="400"
      highlight-current-row
    >
      <el-table-column type="selection" width="55" :reserve-selection="true" />
      <el-table-column prop="id" :label="$t('execution.caseId')" width="80" />
      <el-table-column prop="title" :label="$t('execution.caseTitle')" min-width="200" show-overflow-tooltip />
      <el-table-column :label="$t('execution.priority')" width="90">
        <template #default="scope">
          <el-tag :type="getPriorityType(scope.row.priority)" size="small">
            {{ getPriorityLabel(scope.row.priority) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('execution.testType')" width="100">
        <template #default="scope">
          {{ getTestTypeLabel(scope.row.test_type) }}
        </template>
      </el-table-column>
      <el-table-column prop="project__name" :label="$t('execution.projectName')" width="120" show-overflow-tooltip />
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleConfirm">
          {{ t('execution.confirmSelect') }} ({{ selectedIds.length }})
        </el-button>
      </span>
    </template>
  </el-dialog>

  <!-- 已选用例侧边抽屉 -->
  <el-drawer
    v-model="selectedDrawerVisible"
    :title="t('execution.selectedTestcases')"
    size="400px"
  >
    <div class="selected-drawer-content">
      <el-table :data="selectedTestcasesFull" v-loading="loadingSelected" style="width: 100%">
        <el-table-column prop="title" :label="$t('execution.caseTitle')" show-overflow-tooltip />
        <el-table-column :label="$t('execution.actions')" width="60" fixed="right">
          <template #default="scope">
            <el-button type="danger" link size="small" @click="removeSelected(scope.row.id)">
              {{ t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, reactive, watch, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  projectIds: {
    type: Array,
    default: () => []
  },
  selectedIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    // 弹窗打开时初始化已选 ID
    currentPage.value = 1
    selectedIds.value = [...props.selectedIds]
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// 弹窗完全打开后加载数据并同步选中状态
const handleDialogOpened = () => {
  fetchTestcases()
}

// 表格数据
const tableRef = ref()
const testcases = ref([])
const loading = ref(false)
const isSyncingSelection = ref(false)

// 筛选条件
const filters = reactive({
  keyword: '',
  priority: null,
  testType: null
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 已选项
const selectedIds = ref([])
const selectedTestcasesFull = ref([])
const selectedDrawerVisible = ref(false)
const loadingSelected = ref(false)

// 获取测试用例列表
const fetchTestcases = async () => {
  if (!props.projectIds || props.projectIds.length === 0) {
    ElMessage.warning(t('execution.selectProjectFirst'))
    return
  }

  loading.value = true
  try {
    const params = new URLSearchParams()
    props.projectIds.forEach(id => params.append('project_ids', id))
    params.append('page', currentPage.value)
    params.append('page_size', pageSize.value)

    // 添加筛选条件
    if (filters.keyword) params.append('keyword', filters.keyword)
    if (filters.priority) params.append('priority', filters.priority)
    if (filters.testType) params.append('test_type', filters.testType)

    const response = await api.get(`/executions/plans/testcases_by_projects/?${params.toString()}`)
    testcases.value = response.data.results || []
    total.value = response.data.count || testcases.value.length

    // 同步选中状态（弹窗已完全打开，DOM 已就绪）
    syncSelection()
  } catch (error) {
    console.error('Load testcases error:', error)
    ElMessage.error(t('execution.fetchTestcasesFailed'))
    testcases.value = []
  } finally {
    loading.value = false
  }
}

// 同步表格选中状态
const syncSelection = () => {
  if (!tableRef.value) return

  isSyncingSelection.value = true

  // 清除当前选中
  tableRef.value.clearSelection()

  // 选中在当前页且已选择的行
  testcases.value.forEach(row => {
    if (selectedIds.value.includes(row.id)) {
      tableRef.value.toggleRowSelection(row, true)
    }
  })

  // 更新已选完整数据
  selectedTestcasesFull.value = testcases.value.filter(row =>
    selectedIds.value.includes(row.id)
  )

  isSyncingSelection.value = false
}

// 处理表格选择变化
const handleSelectionChange = (selection) => {
  // 同步过程中跳过，避免 clearSelection 干扰
  if (isSyncingSelection.value) return

  const currentPageIds = testcases.value.map(row => row.id)
  const newSelected = selection
    .filter(row => selectedIds.value.includes(row.id) || currentPageIds.includes(row.id))
    .map(row => row.id)

  // 保留非当前页的已选 ID
  const otherSelected = selectedIds.value.filter(id => !currentPageIds.includes(id))

  selectedIds.value = [...otherSelected, ...newSelected]

  // 更新已选完整数据
  selectedTestcasesFull.value = testcases.value.filter(row =>
    selectedIds.value.includes(row.id)
  )
}

// 点击行切换选中
const handleRowClick = (row) => {
  const idx = selectedIds.value.indexOf(row.id)
  if (idx > -1) {
    selectedIds.value.splice(idx, 1)
  } else {
    selectedIds.value.push(row.id)
  }

  tableRef.value.toggleRowSelection(row)
}

// 移除已选项
const removeSelected = (id) => {
  selectedIds.value = selectedIds.value.filter(sid => sid !== id)
  selectedTestcasesFull.value = selectedTestcasesFull.filter(item => item.id !== id)

  // 更新表格选中状态
  if (tableRef.value) {
    const row = testcases.value.find(r => r.id === id)
    if (row) {
      tableRef.value.toggleRowSelection(row, false)
    }
  }
}

// 显示已选抽屉
const showSelectedDrawer = () => {
  selectedDrawerVisible.value = true
  loadingSelected.value = true

  // 获取所有已选项的完整数据
  if (selectedIds.value.length > 0) {
    const params = new URLSearchParams()
    props.projectIds.forEach(id => params.append('project_ids', id))
    params.append('ids', selectedIds.value.join(','))
    params.append('page', 1)
    params.append('page_size', selectedIds.value.length)

    api.get(`/executions/plans/testcases_by_projects/?${params.toString()}`)
      .then(response => {
        selectedTestcasesFull.value = response.data.results || []
      })
      .catch(error => {
        console.error('Load selected testcases error:', error)
      })
      .finally(() => {
        loadingSelected.value = false
      })
  } else {
    selectedTestcasesFull.value = []
    loadingSelected.value = false
  }
}

// 获取优先级标签类型
const getPriorityType = (priority) => {
  const types = { critical: 'danger', high: 'warning', medium: 'success', low: 'info' }
  return types[priority] || 'info'
}

// 获取优先级标签
const getPriorityLabel = (priority) => {
  const labels = {
    critical: '紧急',
    high: '高',
    medium: '中',
    low: '低'
  }
  return labels[priority] || priority
}

// 获取测试类型标签
const getTestTypeLabel = (type) => {
  const labels = {
    functional: t('testcase.functional'),
    integration: t('testcase.integration'),
    api: t('testcase.api'),
    ui: t('testcase.ui'),
    performance: t('testcase.performance'),
    security: t('testcase.security')
  }
  return labels[type] || type
}

// 重置筛选
const resetFilters = () => {
  Object.assign(filters, {
    keyword: '',
    priority: null,
    testType: null
  })
  currentPage.value = 1
  fetchTestcases()
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchTestcases()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchTestcases()
}

// 确认选择
const handleConfirm = () => {
  emit('confirm', [...selectedIds.value])
  visible.value = false
}

// 关闭弹窗
const handleClose = () => {
  visible.value = false
}

onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.testcase-selector-dialog .filter-bar {
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 4px;
  margin-bottom: 12px;
}

.selected-summary {
  padding: 8px 16px;
  background: #ecf5ff;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #409eff;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.selected-drawer-content {
  padding: 0 16px;
}

/* 表格行点击样式 */
:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
