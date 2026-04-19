<template>
  <div class="execution-list">
    <div class="header">
      <h1>{{ $t('execution.testPlan') }}</h1>
      <div class="header-actions">
        <el-button
          v-if="selectedPlans.length > 0"
          type="danger"
          :icon="Delete"
          @click="batchDeletePlans"
          :disabled="isDeleting">
          {{ $t('execution.batchDelete') }} ({{ selectedPlans.length }})
        </el-button>
        <el-button type="primary" @click="openCreatePlanDialog">
          <el-icon><Plus /></el-icon>
          {{ $t('execution.newPlan') }}
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true">
        <el-form-item :label="$t('execution.project')">
          <el-select v-model="filters.project" :placeholder="$t('execution.selectProject')" clearable style="width: 200px">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.status')">
          <el-select v-model="filters.is_active" :placeholder="$t('execution.selectStatus')" clearable style="width: 120px">
            <el-option :label="$t('execution.filterActive')" :value="true"></el-option>
            <el-option :label="$t('execution.filterClosed')" :value="false"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">{{ $t('common.search') }}</el-button>
          <el-button @click="resetFilters">{{ $t('common.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table
      :data="testPlans"
      style="width: 100%"
      v-loading="loading"
      @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column
        type="index"
        :label="$t('execution.serialNumber')"
        width="80"
        :index="getSerialNumber" />
      <el-table-column prop="name" :label="$t('execution.planName')" min-width="200">
        <template #default="scope">
          <el-link type="primary" @click="viewPlan(scope.row.id)">
            {{ scope.row.name }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="projects" :label="$t('execution.projects')" width="200">
        <template #default="scope">
          <span v-if="scope.row.projects && scope.row.projects.length > 0">
            {{ scope.row.projects.join(', ') }}
          </span>
          <span v-else>{{ $t('execution.noData') }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="version" :label="$t('execution.version')" width="120"></el-table-column>
      <el-table-column prop="creator.username" :label="$t('execution.creator')" width="120"></el-table-column>
      <el-table-column :label="$t('execution.status')" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">
            {{ scope.row.is_active ? $t('execution.active') : $t('execution.closed') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="$t('execution.createdAt')" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('execution.actions')" width="200" fixed="right">
        <template #default="scope">
          <el-button size="small" type="primary" @click="viewPlan(scope.row.id)">
            {{ $t('execution.viewExecution') }}
          </el-button>
          <el-button size="small" type="warning" @click="editPlan(scope.row)">
            {{ $t('common.edit') }}
          </el-button>
          <el-button
            size="small"
            :type="scope.row.is_active ? 'danger' : 'success'"
            @click="togglePlanStatus(scope.row)">
            {{ scope.row.is_active ? $t('execution.closePlan') : $t('execution.activatePlan') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :small="false"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 创建测试计划对话框 -->
    <el-dialog :title="$t('execution.createPlanDialog')" v-model="isCreatePlanDialogOpen" width="600px" :close-on-click-modal="false">
      <el-form :model="newPlanForm" :rules="planRules" ref="planFormRef" label-width="100px">
        <el-form-item :label="$t('execution.planName')" prop="name">
          <el-input v-model="newPlanForm.name" :placeholder="$t('execution.planNamePlaceholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.planDescription')">
          <el-input
            v-model="newPlanForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('execution.planDescriptionPlaceholder')">
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedProjects')" prop="projects">
          <el-select
            v-model="newPlanForm.projects"
            multiple
            :placeholder="$t('execution.selectProjects')"
            style="width: 100%"
            @change="handleProjectChange">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedVersion')">
          <el-select v-model="newPlanForm.version" :placeholder="$t('execution.selectVersion')" style="width: 100%">
            <el-option v-for="item in versions" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.testCases')" prop="testcases">
          <div class="testcase-selector-wrapper">
            <el-button
              type="primary"
              plain
              @click="openTestCaseSelector"
              :disabled="!newPlanForm.projects || newPlanForm.projects.length === 0">
              <el-icon><Search /></el-icon>
              {{ $t('execution.selectTestcases') }}
            </el-button>
            <div class="testcase-summary" v-if="newPlanForm.testcases.length > 0">
              {{ $t('execution.selectedCount', { count: newPlanForm.testcases.length }) }}
              <el-button type="primary" link @click="openTestCaseSelector">
                {{ $t('execution.modifySelection') }}
              </el-button>
            </div>
            <div class="testcase-hint" v-else>
              {{ $t('execution.noTestcaseSelected') }}
            </div>
          </div>
        </el-form-item>
        <el-form-item :label="$t('execution.assignees')">
          <el-select v-model="newPlanForm.assignees" multiple :placeholder="$t('execution.selectAssignees')" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isCreatePlanDialogOpen = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="createPlan" :loading="creating">{{ $t('execution.createPlan') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑测试计划对话框 -->
    <el-dialog :title="$t('execution.editPlanDialog')" v-model="isEditPlanDialogOpen" width="600px" :close-on-click-modal="false">
      <el-form :model="editPlanForm" :rules="planRules" ref="editPlanFormRef" label-width="100px">
        <el-form-item :label="$t('execution.planName')" prop="name">
          <el-input v-model="editPlanForm.name" :placeholder="$t('execution.planNamePlaceholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.planDescription')">
          <el-input
            v-model="editPlanForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('execution.planDescriptionPlaceholder')">
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedProjects')" prop="projects">
          <el-select v-model="editPlanForm.projects" multiple :placeholder="$t('execution.selectProjects')" style="width: 100%">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.testCases')">
          <div class="testcase-selector-wrapper">
            <el-button
              type="primary"
              plain
              @click="openEditTestCaseSelector"
              :disabled="!editPlanForm.projects || editPlanForm.projects.length === 0">
              <el-icon><Search /></el-icon>
              {{ $t('execution.selectTestcases') }}
            </el-button>
            <div class="testcase-summary" v-if="editPlanForm.testcases && editPlanForm.testcases.length > 0">
              {{ $t('execution.selectedCount', { count: editPlanForm.testcases.length }) }}
              <el-button type="primary" link @click="openEditTestCaseSelector">
                {{ $t('execution.modifySelection') }}
              </el-button>
            </div>
            <div class="testcase-hint" v-else>
              {{ $t('execution.noTestcaseSelected') }}
            </div>
          </div>
        </el-form-item>
        <el-form-item :label="$t('execution.relatedVersion')">
          <el-select v-model="editPlanForm.version" :placeholder="$t('execution.selectVersion')" style="width: 100%">
            <el-option v-for="item in versions" :key="item.id" :label="item.name" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.assignees')">
          <el-select v-model="editPlanForm.assignees" multiple :placeholder="$t('execution.selectAssignees')" style="width: 100%">
            <el-option v-for="item in users" :key="item.id" :label="item.username" :value="item.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('execution.planStatus')">
          <el-switch
            v-model="editPlanForm.is_active"
            :active-text="$t('execution.activeText')"
            :inactive-text="$t('execution.inactiveText')">
          </el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="isEditPlanDialogOpen = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="updatePlan" :loading="updating">{{ $t('execution.updatePlan') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 测试用例表格选择器（新建） -->
    <TestCaseTableSelector
      v-model="isTestCaseSelectorVisible"
      :project-ids="newPlanForm.projects"
      :selected-ids="newPlanForm.testcases"
      @confirm="handleTestcaseConfirm"
    />

    <!-- 测试用例表格选择器（编辑） -->
    <TestCaseTableSelector
      v-model="isEditTestCaseSelectorVisible"
      :project-ids="editPlanForm.projects"
      :selected-ids="editPlanForm.testcases"
      @confirm="handleEditTestcaseConfirm"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Search } from '@element-plus/icons-vue'
import api from '@/utils/api'
import TestCaseTableSelector from '@/components/executions/TestCaseTableSelector.vue'

const { t } = useI18n()

const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const testPlans = ref([])
const projects = ref([])
const versions = ref([])
const testcases = ref([])
const users = ref([])
const selectedPlans = ref([])
const isDeleting = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const filters = reactive({
  project: null,
  is_active: null
})

// 表单
const isCreatePlanDialogOpen = ref(false)
const isEditPlanDialogOpen = ref(false)
const isTestCaseSelectorVisible = ref(false)
const isEditTestCaseSelectorVisible = ref(false)
const planFormRef = ref()
const editPlanFormRef = ref()
const currentEditingPlan = ref(null)
const newPlanForm = reactive({
  name: '',
  description: '',
  projects: [], // 改为数组
  version: null,
  testcases: [],
  assignees: []
})

const editPlanForm = reactive({
  id: null,
  name: '',
  description: '',
  projects: [],
  version: null,
  testcases: [],
  assignees: [],
  is_active: true
})

const planRules = {
  name: [
    { required: true, message: computed(() => t('execution.planNameRequired')), trigger: 'blur' }
  ],
  projects: [
    { required: true, message: computed(() => t('execution.projectsRequired')), trigger: 'change' }
  ],
  testcases: [
    {
      required: true,
      message: computed(() => t('execution.testcasesRequired')),
      trigger: 'change',
      validator: (rule, value, callback) => {
        if (!newPlanForm.projects || newPlanForm.projects.length === 0) {
          callback(new Error(t('execution.selectProjectBeforeTestcases')))
        } else if (!value || value.length === 0) {
          callback(new Error(t('execution.testcasesRequired')))
        } else {
          callback()
        }
      }
    }
  ]
}

const fetchTestPlans = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      ...filters
    }
    // 过滤掉空值
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === '') {
        delete params[key]
      }
    })

    const response = await api.get('/executions/plans/', { params })
    testPlans.value = response.data.results || response.data || []
    total.value = response.data.count || testPlans.value.length
  } catch (error) {
    ElMessage.error(t('execution.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const fetchBasicData = async () => {
  try {
    const [projectsRes, versionsRes, usersRes] = await Promise.all([
      api.get('/projects/'), // 只显示用户参与的项目
      api.get('/versions/'),
      api.get('/users/users/') // 修正用户API路径
    ])
    
    projects.value = (projectsRes.data.results || projectsRes.data || []).filter(item => item !== null && item !== undefined)
    versions.value = (versionsRes.data.results || versionsRes.data || []).filter(item => item !== null && item !== undefined)
    users.value = (usersRes.data.results || usersRes.data || []).filter(item => item !== null && item !== undefined)
  } catch (error) {
    console.error('获取基础数据失败:', error)
  }
}

// 打开测试用例表格选择器
const openTestCaseSelector = () => {
  if (!newPlanForm.projects || newPlanForm.projects.length === 0) {
    ElMessage.warning(t('execution.selectProjectFirst'))
    return
  }
  isTestCaseSelectorVisible.value = true
}

// 处理测试用例选择确认
const handleTestcaseConfirm = (selectedIds) => {
  newPlanForm.testcases = selectedIds
}

// 打开编辑测试计划用例选择器
const openEditTestCaseSelector = () => {
  if (!editPlanForm.projects || editPlanForm.projects.length === 0) {
    ElMessage.warning(t('execution.selectProjectFirst'))
    return
  }
  isEditTestCaseSelectorVisible.value = true
}

// 处理编辑测试用例选择确认
const handleEditTestcaseConfirm = (selectedIds) => {
  editPlanForm.testcases = selectedIds
}

// 处理项目选择变化
const handleProjectChange = (selectedProjects) => {
  // 清空已选择的测试用例
  newPlanForm.testcases = []
  // 同步清空选择器中的已选
  isTestCaseSelectorVisible.value = false
}

const createPlan = async () => {
  try {
    await planFormRef.value.validate()
    creating.value = true

    await api.post('/executions/plans/', newPlanForm)
    ElMessage.success(t('execution.createSuccess'))
    isCreatePlanDialogOpen.value = false
    resetPlanForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error(t('execution.createFailed'))
    }
  } finally {
    creating.value = false
  }
}

const viewPlan = (id) => {
  router.push(`/ai-generation/executions/${id}`)
}

const editPlan = async (plan) => {
  try {
    // 获取完整的测试计划详情
    const response = await api.get(`/executions/plans/${plan.id}/`)
    const planDetail = response.data

    // 设置当前编辑的计划
    currentEditingPlan.value = planDetail

    // 从 test_runs 中提取所有已关联的测试用例 ID
    const testcaseIds = []
    if (planDetail.test_runs) {
      for (const run of planDetail.test_runs) {
        if (run.run_cases) {
          for (const runCase of run.run_cases) {
            if (runCase.testcase_id && !testcaseIds.includes(runCase.testcase_id)) {
              testcaseIds.push(runCase.testcase_id)
            }
          }
        }
      }
    }

    // 填充编辑表单数据
    Object.assign(editPlanForm, {
      id: planDetail.id,
      name: planDetail.name,
      description: planDetail.description || '',
      projects: planDetail.projects?.map(p => {
        // 如果是字符串，需要找到对应的项目ID
        const project = projects.value.find(proj => proj.name === p)
        return project ? project.id : p
      }) || [],
      version: planDetail.version ? versions.value.find(v => v.name === planDetail.version)?.id : null,
      testcases: testcaseIds,
      assignees: planDetail.assignees || [],
      is_active: planDetail.is_active
    })

    isEditPlanDialogOpen.value = true
  } catch (error) {
    ElMessage.error(t('execution.fetchDetailFailed'))
  }
}

const updatePlan = async () => {
  try {
    await editPlanFormRef.value.validate()
    updating.value = true

    const updateData = {
      name: editPlanForm.name,
      description: editPlanForm.description,
      projects: editPlanForm.projects,
      version: editPlanForm.version,
      assignees: editPlanForm.assignees,
      is_active: editPlanForm.is_active
    }

    await api.put(`/executions/plans/${editPlanForm.id}/`, updateData)
    ElMessage.success(t('execution.updateSuccess'))
    isEditPlanDialogOpen.value = false
    resetEditForm()
    fetchTestPlans()
  } catch (error) {
    if (error.name !== 'ValidateError') {
      ElMessage.error(t('execution.updateFailed'))
    }
  } finally {
    updating.value = false
  }
}

const resetEditForm = () => {
  Object.assign(editPlanForm, {
    id: null,
    name: '',
    description: '',
    projects: [],
    version: null,
    assignees: [],
    is_active: true
  })
  currentEditingPlan.value = null
  editPlanFormRef.value?.resetFields()
}

const togglePlanStatus = async (plan) => {
  try {
    const action = plan.is_active ? t('execution.closePlan') : t('execution.activatePlan')
    await ElMessageBox.confirm(t('execution.toggleStatusConfirm', { action }), t('common.confirm'), {
      type: 'warning'
    })

    await api.patch(`/executions/plans/${plan.id}/`, {
      is_active: !plan.is_active
    })

    ElMessage.success(t('execution.toggleStatusSuccess', { action }))
    fetchTestPlans()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('execution.toggleStatusFailed'))
    }
  }
}

const openCreatePlanDialog = () => {
  resetPlanForm()
  isCreatePlanDialogOpen.value = true
}

const resetPlanForm = () => {
  Object.assign(newPlanForm, {
    name: '',
    description: '',
    projects: [],
    version: null,
    testcases: [],
    assignees: []
  })
  planFormRef.value?.resetFields()
}

const applyFilters = () => {
  currentPage.value = 1
  fetchTestPlans()
}

const resetFilters = () => {
  Object.assign(filters, {
    project: null,
    is_active: null
  })
  currentPage.value = 1
  fetchTestPlans()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchTestPlans()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchTestPlans()
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedPlans.value = selection
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除
const batchDeletePlans = async () => {
  if (selectedPlans.value.length === 0) {
    ElMessage.warning(t('execution.selectFirst'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('execution.batchDeleteConfirm', { count: selectedPlans.value.length }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    let successCount = 0
    let failCount = 0

    for (const plan of selectedPlans.value) {
      try {
        await api.delete(`/executions/plans/${plan.id}/`)
        successCount++
      } catch (error) {
        console.error(`删除测试计划 ${plan.id} 失败:`, error)
        failCount++
      }
    }

    if (successCount > 0) {
      if (failCount > 0) {
        ElMessage.success(t('execution.batchDeletePartialSuccess', { successCount, failCount }))
      } else {
        ElMessage.success(t('execution.batchDeleteSuccess', { successCount }))
      }
    } else {
      ElMessage.error(t('execution.batchDeleteFailed'))
    }

    selectedPlans.value = []
    fetchTestPlans()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error(t('execution.batchDeleteFailed'))
    }
  } finally {
    isDeleting.value = false
  }
}

// 监听项目选择变化
watch(
  () => newPlanForm.projects,
  () => {
    // 清空已选择的测试用例
    newPlanForm.testcases = []
  },
  { deep: true }
)

onMounted(() => {
  fetchTestPlans()
  fetchBasicData()
})
</script>

<style scoped>
.execution-list {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.testcase-selector-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.testcase-summary {
  font-size: 14px;
  color: #409eff;
}

.testcase-hint {
  font-size: 14px;
  color: #909399;
}
</style>
