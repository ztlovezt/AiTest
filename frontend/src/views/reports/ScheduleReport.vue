<template>
  <div class="schedule-report-page">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack" :icon="ArrowLeft" circle />
        <h1 class="page-title">{{ scheduleName }}</h1>
        <el-tag :type="statusTagType" size="large">{{ statusDisplay }}</el-tag>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="refreshData" :loading="loading" :icon="Refresh">
          {{ $t('common.refresh') }}
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="error" class="error-container">
      <el-empty :description="error" />
    </div>

    <div v-else class="content-container">
      <el-row :gutter="20">
        <el-col :span="16">
          <el-card class="info-card">
            <template #header>
              <div class="card-header">
                <span>{{ $t('report.scheduleReport.basicInfo') }}</span>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item :label="$t('report.scheduleReport.taskName')">
                {{ scheduleName }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('report.scheduleReport.taskType')">
                {{ taskTypeDisplay }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('report.scheduleReport.module')">
                {{ moduleDisplay }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('report.scheduleReport.status')">
                <el-tag :type="statusTagType">{{ statusDisplay }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('report.scheduleReport.createdBy')">
                {{ createdBy }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('report.scheduleReport.createdAt')">
                {{ createdAt }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card v-if="allureReportUrl" class="report-card">
            <template #header>
              <div class="card-header">
                <span>{{ $t('report.scheduleReport.allureReport') }}</span>
                <el-button type="primary" size="small" @click="openAllureReport">
                  {{ $t('report.scheduleReport.viewReport') }}
                </el-button>
              </div>
            </template>
            <div class="allure-info">
              <el-icon size="48" color="#409EFF"><Document /></el-icon>
              <p>{{ $t('report.scheduleReport.allureReportAvailable') }}</p>
            </div>
          </el-card>

          <el-card v-if="executionDetail && isApiRequest" class="detail-card">
            <template #header>
              <div class="card-header">
                <span>{{ $t('report.scheduleReport.executionDetail') }}</span>
              </div>
            </template>
            <div class="api-request-detail">
              <el-descriptions :column="2" border>
                <el-descriptions-item :label="$t('report.scheduleReport.requestName')" v-if="executionDetail.request_info">
                  {{ executionDetail.request_info.name }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.requestMethod')" v-if="executionDetail.request_info">
                  <el-tag :type="getMethodTagType(executionDetail.request_info.method)">
                    {{ executionDetail.request_info.method }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.requestUrl')" :span="2" v-if="executionDetail.request_info">
                  {{ executionDetail.request_info.url }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.statusCode')">
                  <el-tag :type="executionDetail.status_code === 200 ? 'success' : 'danger'">
                    {{ executionDetail.status_code }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.responseTime')">
                  {{ executionDetail.response_time ? executionDetail.response_time.toFixed(2) + ' ms' : '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.duration')">
                  {{ executionDetail.duration ? executionDetail.duration.toFixed(2) + ' s' : '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.environment')" v-if="executionDetail.environment">
                  {{ executionDetail.environment.name }}
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="executionDetail.assertions_results && executionDetail.assertions_results.length > 0" class="assertions-section">
                <h4>{{ $t('report.scheduleReport.assertions') }}</h4>
                <el-table :data="executionDetail.assertions_results" border stripe>
                  <el-table-column prop="name" :label="$t('report.scheduleReport.assertionName')" width="180" />
                  <el-table-column prop="type" :label="$t('report.scheduleReport.assertionType')" width="120">
                    <template #default="{ row }">
                      <el-tag size="small">{{ getAssertionTypeLabel(row.type) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="passed" :label="$t('report.scheduleReport.result')" width="100">
                    <template #default="{ row }">
                      <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                        {{ row.passed ? $t('report.scheduleReport.passed') : $t('report.scheduleReport.failed') }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="error" :label="$t('report.scheduleReport.error')" show-overflow-tooltip />
                </el-table>
              </div>

              <div v-if="executionDetail.error" class="error-section">
                <el-alert type="error" :title="$t('report.scheduleReport.executionError')" :description="executionDetail.error" show-icon />
              </div>
            </div>
          </el-card>

          <el-card v-if="executionDetail && isTestCase" class="detail-card">
            <template #header>
              <div class="card-header">
                <span>{{ $t('report.scheduleReport.executionDetail') }}</span>
              </div>
            </template>
            <div class="test-case-detail">
              <el-row :gutter="20">
                <el-col :span="6">
                  <el-statistic :title="$t('report.scheduleReport.totalCases')" :value="executionDetail.total_count || 0" />
                </el-col>
                <el-col :span="6">
                  <el-statistic :title="$t('report.scheduleReport.passedCases')" :value="executionDetail.passed_count || 0">
                    <template #suffix>
                      <el-icon color="#67C23A"><SuccessFilled /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <el-statistic :title="$t('report.scheduleReport.failedCases')" :value="executionDetail.failed_count || 0">
                    <template #suffix>
                      <el-icon color="#F56C6C"><CircleCloseFilled /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <el-statistic :title="$t('report.scheduleReport.skippedCases')" :value="executionDetail.skipped_count || 0" />
                </el-col>
              </el-row>

              <el-descriptions :column="2" border style="margin-top: 20px;">
                <el-descriptions-item :label="$t('report.scheduleReport.duration')">
                  {{ executionDetail.duration ? executionDetail.duration.toFixed(2) + ' s' : '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.startTime')">
                  {{ executionDetail.start_time || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.endTime')">
                  {{ executionDetail.end_time || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('report.scheduleReport.result')">
                  <el-tag :type="executionDetail.success ? 'success' : 'danger'">
                    {{ executionDetail.success ? $t('report.scheduleReport.success') : $t('report.scheduleReport.failed') }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="executionDetail.error" class="error-section">
                <el-alert type="error" :title="$t('report.scheduleReport.executionError')" :description="executionDetail.error" show-icon />
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :span="8">
          <el-card class="history-card">
            <template #header>
              <div class="card-header">
                <span>{{ $t('report.scheduleReport.executionHistory') }}</span>
              </div>
            </template>
            <el-timeline v-if="executionHistory.length > 0">
              <el-timeline-item
                v-for="record in executionHistory"
                :key="record.id"
                :type="record.type === 'success' ? 'success' : 'danger'"
                :timestamp="record.started"
                placement="top"
              >
                <el-card shadow="hover" class="history-item">
                  <div class="history-header">
                    <el-tag :type="record.type === 'success' ? 'success' : 'danger'" size="small">
                      {{ record.type === 'success' ? $t('report.scheduleReport.success') : $t('report.scheduleReport.failed') }}
                    </el-tag>
                    <span class="history-time">{{ record.stopped }}</span>
                  </div>
                </el-card>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else :description="$t('report.scheduleReport.noHistory')" :image-size="80" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Refresh, Document, SuccessFilled, CircleCloseFilled
} from '@element-plus/icons-vue'
import api from '@/utils/api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const loading = ref(false)
const error = ref(null)
const scheduleId = computed(() => route.params.id)

const scheduleName = ref('')
const taskType = ref('')
const taskTypeDisplay = ref('')
const module = ref('')
const moduleDisplay = ref('')
const status = ref('')
const statusDisplay = ref('')
const createdBy = ref('')
const createdAt = ref('')
const executionHistory = ref([])
const latestExecution = ref(null)
const executionDetail = ref(null)
const allureReportUrl = ref('')

const isApiRequest = computed(() => taskType.value === 'API_REQUEST')
const isTestCase = computed(() => ['UI_TEST_CASE', 'APP_TEST_CASE'].includes(taskType.value))

const statusTagType = computed(() => {
  switch (status.value) {
    case 'active':
      return 'success'
    case 'paused':
      return 'warning'
    case 'completed':
      return 'info'
    default:
      return 'info'
  }
})

const getMethodTagType = (method) => {
  const types = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return types[method] || 'info'
}

const getAssertionTypeLabel = (type) => {
  const labels = {
    status_code: t('report.scheduleReport.assertionTypes.statusCode'),
    response_time: t('report.scheduleReport.assertionTypes.responseTime'),
    contains: t('report.scheduleReport.assertionTypes.contains'),
    json_path: t('report.scheduleReport.assertionTypes.jsonPath'),
    header: t('report.scheduleReport.assertionTypes.header'),
    equals: t('report.scheduleReport.assertionTypes.equals'),
    not_empty: t('report.scheduleReport.assertionTypes.notEmpty'),
    json_schema: t('report.scheduleReport.assertionTypes.jsonSchema')
  }
  return labels[type] || type
}

const fetchData = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await api.get(`/scheduler/schedules/${scheduleId.value}/execution_detail/`)
    const data = response.data
    
    scheduleName.value = data.schedule_name || ''
    taskType.value = data.task_type || ''
    taskTypeDisplay.value = data.task_type_display || ''
    module.value = data.module || ''
    moduleDisplay.value = data.module_display || ''
    status.value = data.status || ''
    statusDisplay.value = data.status_display || ''
    createdBy.value = data.created_by || ''
    createdAt.value = data.created_at || ''
    executionHistory.value = data.execution_history || []
    latestExecution.value = data.latest_execution || null
    executionDetail.value = data.execution_detail || null
    allureReportUrl.value = data.allure_report_url || ''
  } catch (err) {
    error.value = err.response?.data?.error || t('report.scheduleReport.fetchError')
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchData()
}

const goBack = () => {
  router.back()
}

const openAllureReport = () => {
  if (allureReportUrl.value) {
    window.open(allureReportUrl.value, '_blank')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.schedule-report-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.loading-container,
.error-container {
  padding: 40px;
  text-align: center;
}

.content-container {
  margin-top: 20px;
}

.info-card,
.report-card,
.detail-card,
.history-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.allure-info {
  text-align: center;
  padding: 40px;
}

.allure-info p {
  margin-top: 16px;
  color: #606266;
}

.assertions-section {
  margin-top: 20px;
}

.assertions-section h4 {
  margin-bottom: 12px;
  color: #303133;
}

.error-section {
  margin-top: 20px;
}

.test-case-detail {
  padding: 10px 0;
}

.history-card {
  max-height: 600px;
  overflow-y: auto;
}

.history-item {
  padding: 10px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-time {
  font-size: 12px;
  color: #909399;
}
</style>
