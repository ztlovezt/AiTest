<template>
  <div class="automation-testing">
    <div class="page-header">
      <div class="header-left">
        <h3>{{ $t('apiTesting.automation.title') }}</h3>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showCreateSuiteDialog = true">
          <el-icon><Plus /></el-icon>
          {{ $t('apiTesting.automation.createSuite') }}
        </el-button>
      </div>
    </div>

    <div class="content-layout">
      <!-- 左侧项目选择和测试套件列表 -->
      <div class="sidebar">
        <div class="project-selector">
          <el-select
            v-model="selectedProject"
            :placeholder="$t('apiTesting.common.selectProject')"
            @change="onProjectChange"
            size="default"
          >
            <el-option
              v-for="project in httpProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </div>
        
        <div class="suite-list">
          <div class="list-header">
            <span class="list-title">{{ $t('apiTesting.automation.testSuites') }}</span>
            <el-button size="small" text type="primary" @click="loadTestSuites">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
          
          <el-scrollbar height="calc(100vh - 280px)">
            <div
              v-for="suite in testSuites"
              :key="suite.id"
              class="suite-item"
              :class="{ active: selectedSuite?.id === suite.id }"
              @click="selectSuite(suite)"
            >
              <div class="suite-info">
                <div class="suite-name">{{ suite.name }}</div>
                <div class="suite-meta">
                  {{ suite.suite_requests?.length || 0 }} {{ $t('apiTesting.automation.requests') }}
                </div>
              </div>
              <el-dropdown trigger="click" @command="(cmd) => handleSuiteAction(cmd, suite)">
                <span class="more-actions">
                  <el-icon><MoreFilled /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="run">
                      <el-icon><VideoPlay /></el-icon> {{ $t('apiTesting.automation.run') }}
                    </el-dropdown-item>
                    <el-dropdown-item command="edit">
                      <el-icon><Edit /></el-icon> {{ $t('apiTesting.common.edit') }}
                    </el-dropdown-item>
                    <el-dropdown-item command="duplicate">
                      <el-icon><DocumentCopy /></el-icon> {{ $t('apiTesting.common.copy') }}
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <el-icon><Delete /></el-icon> {{ $t('apiTesting.common.delete') }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div v-if="testSuites.length === 0" class="empty-suite">
              <el-empty :description="$t('apiTesting.automation.noSuites')" :image-size="60" />
            </div>
          </el-scrollbar>
        </div>
      </div>

      <!-- 右侧测试套件详情 -->
      <div class="main-content">
        <div v-if="!selectedSuite" class="empty-state">
          <el-empty :description="$t('apiTesting.automation.selectSuiteHint')" />
        </div>
        
        <div v-else class="suite-detail">
          <!-- 套件信息 -->
          <div class="suite-header">
            <div class="suite-title-row">
              <h4 class="suite-title-text">{{ selectedSuite.name }}</h4>
              <div class="suite-action-buttons">
                <el-button type="success" @click="runTestSuite(selectedSuite)" :loading="running" size="small">
                  <el-icon><VideoPlay /></el-icon>
                  {{ $t('apiTesting.automation.executeTest') }}
                </el-button>
                <el-button @click="editSuite(selectedSuite)" size="small">
                  {{ $t('apiTesting.common.edit') }}
                </el-button>
              </div>
            </div>
            <div v-if="selectedSuite.description" class="suite-description">
              {{ selectedSuite.description }}
            </div>
          </div>

          <!-- 请求列表 -->
          <div class="requests-section">
            <div class="section-header">
              <h5 class="section-title">{{ $t('apiTesting.automation.testRequests') }}</h5>
              <el-button size="small" type="primary" plain @click="showAddRequest">
                <el-icon><Plus /></el-icon>
                {{ $t('apiTesting.automation.addRequest') }}
              </el-button>
            </div>
            
            <el-table :data="selectedSuite.suite_requests" style="width: 100%" size="small" border>
              <el-table-column type="index" width="45" align="center" />
              <el-table-column prop="request.name" :label="$t('apiTesting.automation.requestName')" min-width="180" show-overflow-tooltip />
              <el-table-column prop="request.method" :label="$t('apiTesting.automation.method')" width="70" align="center">
                <template #default="scope">
                  <el-tag :type="getMethodType(scope.row.request.method)" size="small">
                    {{ scope.row.request.method }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="request.url" label="URL" min-width="220" show-overflow-tooltip>
                <template #default="scope">
                  <span class="url-text">{{ scope.row.request.url }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="enabled" :label="$t('apiTesting.automation.enabled')" width="65" align="center">
                <template #default="scope">
                  <el-switch
                    v-model="scope.row.enabled"
                    size="small"
                    @change="updateRequestEnabled(scope.row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.skipCondition')" width="80" align="center">
                <template #default="scope">
                  <el-tag v-if="scope.row.skip_condition" type="warning" size="small">
                    {{ $t('apiTesting.automation.yes') }}
                  </el-tag>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.variableExtractors')" width="80" align="center">
                <template #default="scope">
                  <span class="count-badge">{{ scope.row.extractors?.length || 0 }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.assertions')" width="70" align="center">
                <template #default="scope">
                  <span class="count-badge">{{ scope.row.assertions?.length || 0 }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.common.operation')" width="110" align="center" fixed="right">
                <template #default="scope">
                  <el-button link type="primary" @click="editAssertions(scope.row)" size="small">
                    {{ $t('apiTesting.automation.configure') }}
                  </el-button>
                  <el-button link type="danger" @click="removeRequest(scope.row)" size="small">
                    {{ $t('apiTesting.automation.remove') }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 执行历史 -->
          <div class="executions-section">
            <div class="section-header">
              <h5 class="section-title">{{ $t('apiTesting.automation.executionHistory') }}</h5>
              <el-button size="small" text type="primary" @click="loadExecutions">
                <el-icon><RefreshRight /></el-icon>
                {{ $t('apiTesting.automation.refresh') }}
              </el-button>
            </div>

            <el-table :data="executions" v-loading="executionsLoading" size="small" border stripe>
              <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="100" align="center">
                <template #default="scope">
                  <el-tag :type="getStatusType(scope.row.status)" size="small">
                    {{ getStatusText(scope.row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="total_requests" :label="$t('apiTesting.automation.totalRequests')" min-width="90" align="center" />
              <el-table-column prop="passed_requests" :label="$t('apiTesting.automation.passedCount')" min-width="80" align="center">
                <template #default="scope">
                  <span class="text-success">{{ scope.row.passed_requests }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="failed_requests" :label="$t('apiTesting.automation.failedCount')" min-width="80" align="center">
                <template #default="scope">
                  <span class="text-danger">{{ scope.row.failed_requests }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.automation.averageTime')" min-width="100" align="center">
                <template #default="scope">
                  {{ getAverageExecutionTime(scope.row) }}
                </template>
              </el-table-column>
              <el-table-column prop="executed_by.username" :label="$t('apiTesting.automation.executor')" min-width="100" align="center" />
              <el-table-column prop="created_at" :label="$t('apiTesting.automation.executionTime')" min-width="160" align="center">
                <template #default="scope">
                  {{ formatDate(scope.row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column :label="$t('apiTesting.common.operation')" width="100" align="center">
                <template #default="scope">
                  <el-button link type="primary" @click="viewExecutionDetail(scope.row)" size="small">
                    {{ $t('apiTesting.automation.viewDetails') }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 执行历史分页 -->
            <div class="execution-pagination" v-if="executionPagination.total > 0">
              <el-pagination
                v-model:current-page="executionPagination.page"
                v-model:page-size="executionPagination.pageSize"
                :page-sizes="[10, 15, 20, 50]"
                :total="executionPagination.total"
                layout="total, sizes, prev, pager, next, jumper"
                size="small"
                @size-change="handleExecutionSizeChange"
                @current-change="handleExecutionPageChange"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑测试套件对话框 -->
    <el-dialog
      v-model="showCreateSuiteDialog"
      :title="editingSuite ? $t('apiTesting.automation.editSuite') : $t('apiTesting.automation.createSuite')"
      width="600px"
      :close-on-click-modal="false"
      @close="resetSuiteForm"
    >
      <el-form
        ref="suiteFormRef"
        :model="suiteForm"
        :rules="suiteRules"
        label-width="100px"
      >
        <el-form-item :label="$t('apiTesting.automation.suiteName')" prop="name">
          <el-input v-model="suiteForm.name" :placeholder="$t('apiTesting.automation.inputSuiteName')" />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.suiteDescription')" prop="description">
          <el-input
            v-model="suiteForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('apiTesting.automation.inputSuiteDescription')"
          />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.belongProject')" prop="project">
          <el-select v-model="suiteForm.project" :placeholder="$t('apiTesting.automation.selectProject')">
            <el-option
              v-for="project in httpProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.executionEnvironment')" prop="environment">
          <el-select v-model="suiteForm.environment" :placeholder="$t('apiTesting.automation.selectEnvironment')" clearable>
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateSuiteDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="submitSuiteForm" :loading="submittingSuite">
          {{ editingSuite ? $t('apiTesting.common.update') : $t('apiTesting.common.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加请求对话框 -->
    <el-dialog
      v-model="showAddRequestDialog"
      :title="$t('apiTesting.automation.addRequestToSuite')"
      width="800px"
      :close-on-click-modal="false"
    >
      <div class="add-request-content">
        <div class="request-selector">
          <el-tree
            ref="requestTreeRef"
            :data="requestTree"
            :props="requestTreeProps"
            show-checkbox
            node-key="id"
            :check-on-click-node="false"
            @check="onRequestCheck"
          >
            <template #default="{ node, data }">
              <div class="request-tree-node">
                <el-icon v-if="data.type === 'collection'">
                  <Folder />
                </el-icon>
                <el-icon v-else>
                  <Document />
                </el-icon>
                <span>{{ data.name }}</span>
                <span v-if="data.type === 'request'" class="method-tag" :class="data.method?.toLowerCase()">
                  {{ data.method }}
                </span>
              </div>
            </template>
          </el-tree>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showAddRequestDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="addSelectedRequests" :loading="addingRequests">
          {{ $t('apiTesting.automation.addSelectedRequests') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行结果对话框 -->
    <el-dialog
      v-model="showExecutionDialog"
      :title="$t('apiTesting.automation.testExecutionResult')"
      width="80%"
      :top="'5vh'"
    >
      <div v-if="currentExecution" class="execution-detail">
        <div class="execution-summary">
          <!-- RUNNING 状态进度提示 -->
          <el-alert
            v-if="currentExecution.status === 'RUNNING'"
            :title="$t('apiTesting.automation.executing')"
            type="info"
            :closable="false"
            style="margin-bottom: 20px;"
          >
            <template #default>
              <div class="running-indicator">
                <span>{{ $t('apiTesting.automation.executingMessage') }}</span>
              </div>
            </template>
          </el-alert>

          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.totalRequests')" :value="currentExecution.total_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.passedCount')" :value="currentExecution.passed_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.failedCount')" :value="currentExecution.failed_requests" />
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('apiTesting.automation.passRate')" :value="getPassRate(currentExecution)" suffix="%" />
            </el-col>
          </el-row>
        </div>

        <div class="execution-results">
          <h4>{{ $t('apiTesting.automation.detailedResults') }}</h4>
          <el-table :data="formatExecutionResults(currentExecution.results)" border>
            <el-table-column prop="name" :label="$t('apiTesting.automation.requestName')" min-width="200" />
            <el-table-column prop="method" :label="$t('apiTesting.automation.method')" width="80">
              <template #default="scope">
                <el-tag :type="getMethodType(scope.row.method)" size="small">
                  {{ scope.row.method }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="$t('apiTesting.automation.result')" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.passed !== false ? 'success' : 'danger'" size="small">
                  {{ scope.row.passed !== false ? $t('apiTesting.automation.resultPassed') : $t('apiTesting.automation.resultFailed') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status_code" :label="$t('apiTesting.automation.statusCode')" width="100" />
            <el-table-column prop="response_time" :label="$t('apiTesting.automation.responseTime')" width="120">
              <template #default="scope">
                {{ scope.row.response_time != null ? `${scope.row.response_time.toFixed(0)}ms` : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="error" :label="$t('apiTesting.automation.errorMessage')" min-width="200" show-overflow-tooltip />
          </el-table>
        </div>
      </div>

      <template #footer>
        <el-button @click="showExecutionDialog = false">{{ $t('apiTesting.common.close') }}</el-button>
      </template>
    </el-dialog>

    <!-- 断言配置对话框 -->
    <el-dialog
      v-model="showAssertionDialog"
      :title="$t('apiTesting.automation.configureRequest')"
      width="720px"
      :top="'8vh'"
      class="request-config-dialog"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 跳过条件 Tab -->
        <el-tab-pane :label="$t('apiTesting.automation.skipCondition')" name="skip">
          <div class="skip-condition-editor">
            <el-form label-width="100px" size="default">
              <el-form-item :label="$t('apiTesting.automation.skipCondition')">
                <el-input
                  v-model="requestForm.skip_condition"
                  type="textarea"
                  :rows="4"
                  :placeholder="$t('apiTesting.automation.skipConditionPlaceholder')"
                />
              </el-form-item>
              <el-form-item>
                <el-alert type="info" :closable="false" show-icon>
                  <template #title>
                    {{ $t('apiTesting.automation.skipConditionHelp') }}
                  </template>
                </el-alert>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 变量提取 Tab -->
        <el-tab-pane :label="$t('apiTesting.automation.extractVariables')" name="variables">
          <VariableExtractor v-model="requestForm.extractors">
            <template #actions>
              <el-button type="success" @click="syncFromApiRequest" size="small">
                <el-icon><Refresh /></el-icon>
                {{ $t('apiTesting.automation.syncFromApi') }}
              </el-button>
            </template>
          </VariableExtractor>
        </el-tab-pane>

        <!-- 断言配置 Tab -->
        <el-tab-pane :label="$t('apiTesting.automation.assertionConfig')" name="assertions">
          <div class="assertion-toolbar">
            <el-button type="success" @click="syncFromApiRequest" size="small">
              <el-icon><Refresh /></el-icon>
              {{ $t('apiTesting.automation.syncFromApi') }}
            </el-button>
            <el-button type="danger" v-if="requestForm.assertions.length > 0" @click="clearAssertions" size="small">
              {{ $t('apiTesting.automation.clearAssertions') }}
            </el-button>
          </div>
          <div class="assertion-list">
            <div v-for="(assertion, index) in requestForm.assertions" :key="index" class="assertion-item">
              <div class="assertion-header-row">
                <el-input v-model="assertion.name" :placeholder="$t('apiTesting.automation.assertionName')" style="width: 160px;" size="small" />
                <el-select v-model="assertion.type" :placeholder="$t('apiTesting.automation.assertionType')" style="flex: 1; margin-left: 12px;" size="small" @change="onAssertionTypeChange(assertion)">
                  <el-option
                    v-for="opt in assertionTypeOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
                <el-button type="danger" text @click="removeAssertionConfig(index)" size="small" style="margin-left: 8px;">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <div class="assertion-detail-row">
                <!-- JSONPath 表达式（仅 json_path 类型显示） -->
                <el-input
                  v-if="assertion.type === 'json_path'"
                  v-model="assertion.json_path"
                  :placeholder="$t('apiTesting.automation.jsonPathPlaceholder')"
                  style="width: 280px;"
                  size="small"
                />
                <!-- Header 名称（仅 header 类型显示） -->
                <el-input
                  v-if="assertion.type === 'header'"
                  v-model="assertion.header_name"
                  :placeholder="$t('apiTesting.automation.headerName')"
                  style="width: 180px;"
                  size="small"
                />
                <!-- 期望值 -->
                <el-input
                  v-model="assertion.expected"
                  :placeholder="getExpectedPlaceholder(assertion.type)"
                  style="flex: 1;"
                  size="small"
                />
              </div>
            </div>
            <el-empty v-if="requestForm.assertions.length === 0" :description="$t('apiTesting.automation.noAssertions')" :image-size="80" />
          </div>
          <el-button type="primary" class="add-assertion-btn" @click="addAssertionConfig" size="default">
            <el-icon><Plus /></el-icon>
            {{ $t('apiTesting.automation.addAssertion') }}
          </el-button>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showAssertionDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
          <el-button type="primary" @click="saveAssertionConfig">{{ $t('apiTesting.common.save') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  Plus, Refresh, MoreFilled, VideoPlay, Edit,
  Folder, Document, Delete, DocumentCopy, RefreshRight
} from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import VariableExtractor from './components/VariableExtractor.vue'

const { t } = useI18n()

const projects = ref([])
const selectedProject = ref(null)
const testSuites = ref([])
const selectedSuite = ref(null)
const executions = ref([])
const environments = ref([])
const requestTree = ref([])
const running = ref(false)
const executionsLoading = ref(false)
const showCreateSuiteDialog = ref(false)
const showAddRequestDialog = ref(false)
const showExecutionDialog = ref(false)
const editingSuite = ref(null)
const submittingSuite = ref(false)
const addingRequests = ref(false)
const currentExecution = ref(null)
const suiteFormRef = ref()
const requestTreeRef = ref()

// 执行历史分页
const executionPagination = reactive({
  page: 1,
  pageSize: 15,
  total: 0
})

// 断言编辑相关
const showAssertionDialog = ref(false)
const editingSuiteRequest = ref(null)
const activeTab = ref('assertions')
let requestId = ref(null)
const requestForm = reactive({
  assertions: [],
  extractors: [],
  skip_condition: ''
})

// 断言类型选项
const assertionTypeOptions = computed(() => [
  { value: 'status_code', label: t('apiTesting.automation.assertionTypes.statusCode') },
  { value: 'contains', label: t('apiTesting.automation.assertionTypes.contains') },
  { value: 'response_time', label: t('apiTesting.automation.assertionTypes.responseTime') },
  { value: 'json_path', label: t('apiTesting.automation.assertionTypes.jsonPath') },
  { value: 'header', label: t('apiTesting.automation.assertionTypes.header') },
  { value: 'equals', label: t('apiTesting.automation.assertionTypes.equals') },
  { value: 'not_empty', label: t('apiTesting.automation.assertionTypes.notEmpty') },
  { value: 'json_schema', label: t('apiTesting.automation.assertionTypes.jsonSchema') }
])

const suiteForm = reactive({
  name: '',
  description: '',
  project: null,
  environment: null
})

const suiteRules = computed(() => ({
  name: [{ required: true, message: t('apiTesting.automation.inputSuiteName'), trigger: 'blur' }],
  project: [{ required: true, message: t('apiTesting.automation.selectProject'), trigger: 'change' }]
}))

const requestTreeProps = {
  children: 'children',
  label: 'name'
}

const httpProjects = computed(() => {
  return projects.value.filter(project => project.project_type !== 'WEBSOCKET')
})

const getMethodType = (method) => {
  const typeMap = {
    'GET': 'success',
    'POST': 'primary',
    'PUT': 'warning', 
    'DELETE': 'danger',
    'PATCH': 'info'
  }
  return typeMap[method] || 'info'
}

const getExpectedPlaceholder = (type) => {
  const placeholderMap = {
    'status_code': t('apiTesting.automation.expectedStatusCode'),
    'response_time': t('apiTesting.automation.expectedResponseTime'),
    'contains': t('apiTesting.automation.expectedContainsText'),
    'json_path': t('apiTesting.automation.expectedValue'),
    'header': t('apiTesting.automation.expectedHeaderValue'),
    'equals': t('apiTesting.automation.expectedEqualsValue'),
    'not_empty': '',
    'json_schema': '{}'
  }
  return placeholderMap[type] || t('apiTesting.automation.expectedValue')
}

const getStatusType = (status) => {
  const typeMap = {
    'PENDING': 'info',
    'RUNNING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'info',
    'PARTIAL_FAILED': 'warning'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusKey = {
    'PENDING': 'pending',
    'RUNNING': 'running',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled',
    'PARTIAL_FAILED': 'partialFailed'
  }[status]
  
  if (statusKey) {
    return t(`apiTesting.report.status.${statusKey}`)
  }
  return status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const getExecutionTime = (execution) => {
  if (!execution.start_time || !execution.end_time) return '-'
  const start = dayjs(execution.start_time)
  const end = dayjs(execution.end_time)
  return `${end.diff(start, 'second')}s`
}

const getAverageExecutionTime = (execution) => {
  if (!execution.results || !Array.isArray(execution.results) || execution.results.length === 0) {
    return '-'
  }
  
  // 计算所有请求的平均响应时间
  const totalResponseTime = execution.results.reduce((sum, result) => sum + (result.response_time || 0), 0)
  const averageTime = totalResponseTime / execution.results.length
  
  if (averageTime < 1000) {
    return `${Math.round(averageTime)}ms`
  } else {
    return `${(averageTime / 1000).toFixed(1)}s`
  }
}

const getPassRate = (execution) => {
  if (execution.total_requests === 0) return 0
  return ((execution.passed_requests / execution.total_requests) * 100).toFixed(1)
}

const getEnvironmentName = (environmentId) => {
  if (!environmentId) return t('apiTesting.automation.noEnvironment')
  const env = environments.value.find(e => e.id === environmentId)
  return env ? env.name : t('apiTesting.automation.noEnvironment')
}

const loadProjects = async () => {
  try {
    const response = await api.get('/api-testing/projects/')
    projects.value = response.data.results || response.data

    // 过滤出HTTP项目
    const httpProjects = projects.value.filter(project => project.project_type !== 'WEBSOCKET')

    if (httpProjects.length > 0 && !selectedProject.value) {
      selectedProject.value = httpProjects[0].id
      await onProjectChange()
    } else if (httpProjects.length === 0) {
      // 如果没有HTTP项目，清空选择
      selectedProject.value = null
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadProjects'))
  }
}

const loadTestSuites = async () => {
  if (!selectedProject.value) return

  try {
    const response = await api.get('/api-testing/test-suites/', {
      params: { project: selectedProject.value }
    })
    testSuites.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadTestSuites'))
  }
}

const loadEnvironments = async () => {
  try {
    // 获取全局环境 + 当前项目环境
    const response = await api.get('/api-testing/environments/', {
      // 不传递project参数，让后端返回所有可访问的环境（全局+当前项目）
    })
    const allEnvironments = response.data.results || response.data

    // 过滤当前项目相关或全局环境
    environments.value = allEnvironments.filter(env =>
      env.scope === 'GLOBAL' ||
      (env.scope === 'LOCAL' && (!selectedProject.value || env.project === selectedProject.value))
    )
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadEnvironments'))
  }
}

const loadRequestTree = async () => {
  if (!selectedProject.value) return

  try {
    // 加载集合
    const collectionsRes = await api.get('/api-testing/collections/', {
      params: { project: selectedProject.value }
    })
    const collections = collectionsRes.data.results || collectionsRes.data

    // 加载请求
    const requestsRes = await api.get('/api-testing/requests/')
    const requests = requestsRes.data.results || requestsRes.data

    // 构建树形结构
    requestTree.value = buildRequestTree(collections, requests)
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadRequestTree'))
  }
}

const buildRequestTree = (collections, requests) => {
  const map = {}
  const roots = []
  
  // 创建集合节点
  collections.forEach(collection => {
    map[collection.id] = {
      ...collection,
      type: 'collection',
      children: []
    }
  })
  
  // 构建集合层级关系
  collections.forEach(collection => {
    if (collection.parent && map[collection.parent]) {
      map[collection.parent].children.push(map[collection.id])
    } else {
      roots.push(map[collection.id])
    }
  })
  
  // 添加请求到对应集合
  requests.forEach(request => {
    if (map[request.collection]) {
      map[request.collection].children.push({
        ...request,
        type: 'request',
        id: `request_${request.id}`
      })
    }
  })
  
  return roots
}

const loadExecutions = async () => {
  if (!selectedSuite.value) return

  executionsLoading.value = true
  try {
    const params = {
      page: executionPagination.page,
      page_size: executionPagination.pageSize,
      test_suite: selectedSuite.value.id
    }
    const response = await api.get('/api-testing/test-executions/', { params })
    executions.value = response.data.results || response.data
    executionPagination.total = response.data.count || (response.data.results ? response.data.length : 0)
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadExecutionHistory'))
  } finally {
    executionsLoading.value = false
  }
}

// 执行历史分页切换
const handleExecutionPageChange = (page) => {
  executionPagination.page = page
  loadExecutions()
}

const handleExecutionSizeChange = (size) => {
  executionPagination.pageSize = size
  executionPagination.page = 1
  loadExecutions()
}

const onProjectChange = async () => {
  // 检查选中的项目是否为HTTP项目
  const selectedProjectData = projects.value.find(p => p.id === selectedProject.value)
  if (selectedProjectData && selectedProjectData.project_type === 'WEBSOCKET') {
    ElMessage.warning(t('apiTesting.messages.warning.websocketNotSupported'))
    // 重置为第一个HTTP项目或清空选择
    const httpProjects = projects.value.filter(project => project.project_type !== 'WEBSOCKET')
    if (httpProjects.length > 0) {
      selectedProject.value = httpProjects[0].id
    } else {
      selectedProject.value = null
    }
    return
  }

  selectedSuite.value = null
  await Promise.all([
    loadTestSuites(),
    loadEnvironments(),
    loadRequestTree()
  ])
}

const selectSuite = (suite) => {
  selectedSuite.value = suite
  loadExecutions()
}

const handleSuiteAction = async (action, suite) => {
  switch (action) {
    case 'run':
      await runTestSuite(suite)
      break
    case 'edit':
      editSuite(suite)
      break
    case 'duplicate':
      await duplicateSuite(suite)
      break
    case 'delete':
      await deleteSuite(suite)
      break
  }
}

// 轮询执行状态
let pollingTimer = null
const startPolling = async (executionId) => {
  if (pollingTimer) clearInterval(pollingTimer)
  
  try {
    const res = await api.get(`/api-testing/test-executions/${executionId}/`)
    const execution = res.data
    
    if (execution.status === 'RUNNING') {
      // 更新当前执行记录
      currentExecution.value = execution
      // 继续轮询
      pollingTimer = setTimeout(() => startPolling(executionId), 2000)
    } else {
      // 执行完成，停止轮询，刷新列表
      clearInterval(pollingTimer)
      pollingTimer = null
      await loadExecutions()
      
      // 如果详情弹窗打开着，更新数据
      if (showExecutionDialog.value) {
        currentExecution.value = execution
        showResultDetail(execution)
      }
      
      // 显示完成消息
      if (execution.status === 'COMPLETED') {
        ElMessage.success(t('apiTesting.messages.success.suiteExecuted'))
      } else if (execution.status === 'FAILED' || execution.status === 'PARTIAL_FAILED') {
        ElMessage.warning(t('apiTesting.messages.warning.executionCompleted'))
      }
    }
  } catch (e) {
    console.error('轮询失败:', e)
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  }
}

const runTestSuite = async (suite) => {
  running.value = true
  try {
    // 异步执行：发送请求后立即返回（后端返回202）
    const response = await api.post(`/api-testing/test-suites/${suite.id}/execute/`, null, {
      timeout: 300000  // 5分钟超时
    })
    
    // 获取执行ID（从响应中获取）
    const executionId = response.data.id || response.data.execution_id
    
    // 立即打开执行详情弹窗
    currentExecution.value = response.data
    showExecutionDialog.value = true
    
    ElMessage.info(t('apiTesting.automation.suiteSubmitted'))
    
    // 开始轮询执行状态
    if (executionId) {
      startPolling(executionId)
    } else {
      await loadExecutions()
    }
  } catch (error) {
    console.error('执行测试套件失败:', error)
    ElMessage.error(t('apiTesting.messages.error.executeSuite'))
  } finally {
    running.value = false
  }
}

const editSuite = (suite) => {
  editingSuite.value = suite
  suiteForm.name = suite.name
  suiteForm.description = suite.description
  suiteForm.project = suite.project
  // 修复：environment字段直接是ID，不需要?.id
  suiteForm.environment = suite.environment || null
  showCreateSuiteDialog.value = true
}

const duplicateSuite = async (suite) => {
  try {
    const newSuite = {
      name: `${suite.name} - ${t('apiTesting.common.copyText')}`,
      description: suite.description,
      project: suite.project,
      environment: suite.environment || null  // 修复：直接使用environment ID
    }
    await api.post('/api-testing/test-suites/', newSuite)
    ElMessage.success(t('apiTesting.messages.success.copy'))
    await loadTestSuites()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.copyFailed'))
  }
}

const deleteSuite = async (suite) => {
  try {
    await ElMessageBox.confirm(
      t('apiTesting.automation.confirmDeleteSuite', { name: suite.name }),
      t('apiTesting.messages.confirm.deleteTitle'),
      {
        confirmButtonText: t('apiTesting.common.confirm'),
        cancelButtonText: t('apiTesting.common.cancel'),
        type: 'warning'
      }
    )

    await api.delete(`/api-testing/test-suites/${suite.id}/`)
    ElMessage.success(t('apiTesting.messages.success.delete'))

    if (selectedSuite.value?.id === suite.id) {
      selectedSuite.value = null
    }
    await loadTestSuites()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.deleteFailed'))
    }
  }
}

const submitSuiteForm = async () => {
  if (!suiteFormRef.value) return

  const valid = await suiteFormRef.value.validate().catch(() => false)
  if (!valid) return

  submittingSuite.value = true
  try {
    if (editingSuite.value) {
      await api.put(`/api-testing/test-suites/${editingSuite.value.id}/`, suiteForm)
      ElMessage.success(t('apiTesting.messages.success.suiteUpdated'))
    } else {
      await api.post('/api-testing/test-suites/', suiteForm)
      ElMessage.success(t('apiTesting.messages.success.suiteCreated'))
    }

    showCreateSuiteDialog.value = false
    await loadTestSuites()
  } catch (error) {
    ElMessage.error(editingSuite.value ? t('apiTesting.messages.error.updateFailed') : t('apiTesting.messages.error.createFailed'))
  } finally {
    submittingSuite.value = false
  }
}

const resetSuiteForm = () => {
  editingSuite.value = null
  Object.assign(suiteForm, {
    name: '',
    description: '',
    project: selectedProject.value,
    environment: null
  })
  suiteFormRef.value?.resetFields()
}

const showAddRequest = async () => {
  await loadRequestTree()
  showAddRequestDialog.value = true
  
  // 等待对话框显示完成后再设置勾选状态
  nextTick(() => {
    setTimeout(() => {
      if (requestTreeRef.value && selectedSuite.value) {
        // 获取当前已关联的请求ID
        const existingRequestIds = selectedSuite.value.suite_requests?.map(sr => 
          `request_${sr.request.id}`
        ) || []
        
        // 设置已关联接口为已勾选状态
        requestTreeRef.value.setCheckedKeys(existingRequestIds, false)
        console.log('设置已关联接口ID:', existingRequestIds)
      }
    }, 200)
  })
}

const onRequestCheck = () => {
  // 请求选择变化处理
}

const addSelectedRequests = async () => {
  const checkedNodes = requestTreeRef.value.getCheckedNodes()
  const requestIds = checkedNodes
    .filter(node => node.type === 'request')
    .map(node => node.id.replace('request_', ''))

  if (requestIds.length === 0) {
    ElMessage.warning(t('apiTesting.messages.warning.selectAtLeastOneRequest'))
    return
  }

  addingRequests.value = true
  try {
    // 这里需要调用添加请求到套件的API
    await api.post(`/api-testing/test-suites/${selectedSuite.value.id}/add-requests/`, {
      request_ids: requestIds
    })

    ElMessage.success(t('apiTesting.messages.success.addSuccess'))
    showAddRequestDialog.value = false
    // 重新加载当前测试套件详情
    await reloadCurrentSuite()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.addFailed'))
  } finally {
    addingRequests.value = false
  }
}

const updateRequestEnabled = async (suiteRequest) => {
  try {
    await api.put(`/api-testing/test-suite-requests/${suiteRequest.id}/`, {
      enabled: suiteRequest.enabled
    })
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.updateFailed'))
    suiteRequest.enabled = !suiteRequest.enabled
  }
}

const editAssertions = (suiteRequest) => {
  editingSuiteRequest.value = suiteRequest
  requestId.value = suiteRequest.request.id
  // 复制断言和变量提取数据到表单（避免直接修改原数据）
  requestForm.assertions = JSON.parse(JSON.stringify(suiteRequest.assertions || []))
  requestForm.extractors = JSON.parse(JSON.stringify(suiteRequest.extractors || []))
  requestForm.skip_condition = suiteRequest.skip_condition || ''
  showAssertionDialog.value = true
}

// 从接口同步断言和变量提取
const syncFromApiRequest = async () => {
  if (!requestId.value) return

  try {
    const response = await api.get(`/api-testing/requests/${requestId.value}/`)
    const apiRequest = response.data

    // 同步断言
    requestForm.assertions = JSON.parse(JSON.stringify(apiRequest.assertions || []))
    
    // 同步变量提取 - 直接使用 extractors 字段
    requestForm.extractors = JSON.parse(JSON.stringify(apiRequest.extractors || []))

    ElMessage.success(t('apiTesting.messages.success.syncSuccess'))
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.syncFailed'))
  }
}

// 清空所有断言
const clearAssertions = () => {
  requestForm.assertions = []
  ElMessage.info(t('apiTesting.messages.info.assertionsCleared'))
}

// 添加新断言
const addAssertionConfig = () => {
  const newAssertion = {
    name: `断言${requestForm.assertions.length + 1}`,
    type: 'status_code',
    expected: 200,
    json_path: '',
    header_name: ''
  }
  requestForm.assertions.push(newAssertion)
}

// 删除断言
const removeAssertionConfig = (index) => {
  requestForm.assertions.splice(index, 1)
  // 重新命名剩余断言
  requestForm.assertions.forEach((item, idx) => {
    if (item.name.startsWith('断言')) {
      item.name = `断言${idx + 1}`
    }
  })
}

// 断言类型变化时处理
const onAssertionTypeChange = (item) => {
  // 切换断言类型时设置合理的默认值
  switch (item.type) {
    case 'status_code':
      item.expected = 200
      item.json_path = ''
      break
    case 'response_time':
      item.expected = 1000
      item.json_path = ''
      break
    case 'json_path':
      item.json_path = '$.'
      item.expected = ''
      break
    case 'header':
      item.header_name = ''
      item.expected = ''
      item.json_path = ''
      break
    case 'contains':
      item.expected = ''
      item.json_path = ''
      break
    case 'equals':
      item.expected = ''
      item.json_path = ''
      break
    case 'not_empty':
      item.expected = ''
      item.json_path = ''
      break
    case 'json_schema':
      item.expected = '{}'
      item.json_path = ''
      break
  }
}

// 保存断言配置
const saveAssertionConfig = async () => {
  if (!editingSuiteRequest.value) return

  try {
    await api.put(`/api-testing/test-suite-requests/${editingSuiteRequest.value.id}/`, {
      assertions: requestForm.assertions,
      extractors: requestForm.extractors,
      skip_condition: requestForm.skip_condition
    })
    ElMessage.success(t('apiTesting.messages.success.saveSuccess'))
    showAssertionDialog.value = false
    // 重新加载当前套件
    await reloadCurrentSuite()
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.saveFailed'))
  }
}

const removeRequest = async (suiteRequest) => {
  try {
    await ElMessageBox.confirm(t('apiTesting.automation.confirmRemoveRequest'), t('apiTesting.automation.confirmRemove'), {
      confirmButtonText: t('apiTesting.common.confirm'),
      cancelButtonText: t('apiTesting.common.cancel'),
      type: 'warning'
    })

    await api.delete(`/api-testing/test-suite-requests/${suiteRequest.id}/`)
    ElMessage.success(t('apiTesting.messages.success.removeSuccess'))
    // 重新加载当前测试套件详情
    await reloadCurrentSuite()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('apiTesting.messages.error.removeFailed'))
    }
  }
}

const reloadCurrentSuite = async () => {
  if (!selectedSuite.value) return

  try {
    // 重新加载当前测试套件的详细信息
    const response = await api.get(`/api-testing/test-suites/${selectedSuite.value.id}/`)
    const updatedSuite = response.data

    // 强制重新设置响应式数据
    selectedSuite.value = { ...updatedSuite }

    // 同时更新测试套件列表中对应的套件
    const index = testSuites.value.findIndex(suite => suite.id === updatedSuite.id)
    if (index !== -1) {
      testSuites.value[index] = { ...updatedSuite }
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.refreshSuiteFailed'))
  }
}

const viewExecutionDetail = (execution) => {
  currentExecution.value = execution
  showExecutionDialog.value = true

  // 如果执行记录正在运行，开始轮询
  if (execution.status === 'RUNNING') {
    startPolling()
  }
}

// 显示执行结果详情（轮询完成时调用）
const showResultDetail = (execution) => {
  currentExecution.value = execution
  // 如果有报告URL，可以在这里处理
}

const formatExecutionResults = (results) => {
  if (!results) return []
  if (Array.isArray(results)) return results
  if (typeof results === 'object' && Object.keys(results).length === 0) return []
  return []
}

// 监听执行详情弹窗关闭，清理轮询
watch(showExecutionDialog, (val) => {
  if (!val && pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
})

onMounted(() => {
  loadProjects()
})

onUnmounted(() => {
  // 清理轮询定时器
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
})
</script>

<style scoped>
.automation-testing {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.header-left h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  gap: 10px;
}

/* 内容布局 */
.content-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  overflow: hidden;
}

/* 侧边栏 */
.sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
}

.project-selector {
  background: white;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.suite-list {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.list-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.suite-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #f2f3f5;
  cursor: pointer;
  transition: all 0.2s;
}

.suite-item:hover {
  background: #f5f7fa;
}

.suite-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.suite-info {
  flex: 1;
  min-width: 0;
}

.suite-name {
  font-weight: 500;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suite-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.more-actions {
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  color: #909399;
  transition: all 0.2s;
}

.more-actions:hover {
  background: #e8e8e8;
  color: #606266;
}

.empty-suite {
  padding: 30px 20px;
  text-align: center;
}

/* 主内容区 */
.main-content {
  flex: 1;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.suite-detail {
  flex: 1;
  padding: 20px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 套件头部 */
.suite-header {
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.suite-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.suite-title-text {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.suite-action-buttons {
  display: flex;
  gap: 8px;
}

.suite-description {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

/* 区块通用样式 */
.requests-section,
.executions-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 200px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

/* 表格样式优化 */
.url-text {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #606266;
}

.text-muted {
  color: #c0c4cc;
}

.text-success {
  color: #67c23a;
  font-weight: 500;
}

.text-danger {
  color: #f56c6c;
  font-weight: 500;
}

.count-badge {
  display: inline-block;
  min-width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  background: #f0f2f5;
  border-radius: 11px;
  font-size: 12px;
  color: #606266;
  padding: 0 8px;
}

/* 执行历史分页 */
.execution-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

/* 添加请求对话框 */
.add-request-content {
  max-height: 400px;
  overflow-y: auto;
}

.request-tree-node {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 1;
}

.method-tag {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 2px;
  color: white;
  font-weight: bold;
  margin-left: auto;
}

.method-tag.get { background: var(--th-color-success); }
.method-tag.post { background: var(--th-color-primary); }
.method-tag.put { background: #e6a23c; }
.method-tag.delete { background: #f56c6c; }
.method-tag.patch { background: #909399; }

/* 执行详情对话框 */
.execution-detail {
  max-height: 70vh;
  overflow-y: auto;
}

/* 断言配置对话框样式 */
.request-config-dialog :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.tab-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 6px;
  flex-wrap: wrap;
}

.assertion-list {
  max-height: 450px;
  overflow-y: auto;
  padding: 0 4px;
}

.assertion-item {
  padding: 14px 16px;
  background: #fafbfc;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  margin-bottom: 12px;
  transition: box-shadow 0.2s;
}

.assertion-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.assertion-header-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.assertion-detail-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.assertion-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.add-assertion-btn {
  width: 100%;
  margin-top: 16px;
}

.skip-condition-editor {
  padding: 16px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.running-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.running-indicator::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  background: #409eff;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 输入框 placeholder 样式 - 浅灰色显示 */
.request-config-dialog :deep(.el-input__wrapper input::placeholder),
.request-config-dialog :deep(.el-textarea__inner::placeholder) {
  color: #a8abb2;
  font-weight: normal;
}

.skip-condition-editor :deep(.el-textarea__inner::placeholder) {
  color: #a8abb2;
  font-weight: normal;
}
</style>