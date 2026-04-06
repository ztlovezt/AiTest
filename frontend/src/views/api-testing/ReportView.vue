<template>
  <div class="report-view">
    <div class="header">
      <h3>{{ $t('apiTesting.report.title') }}</h3>
      <div class="actions">
        <el-button type="primary" @click="refreshReports">{{ $t('apiTesting.report.refreshReport') }}</el-button>
      </div>
    </div>

    <div class="content">
      <el-table :data="reports" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="test_suite_name" :label="$t('apiTesting.report.testSuite')" min-width="200" />
        <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="130">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_requests" :label="$t('apiTesting.report.totalRequests')" width="100" />
        <el-table-column prop="passed_requests" :label="$t('apiTesting.report.passedCount')" width="100">
          <template #default="scope">
            <span style="color: var(--th-color-success)">{{ scope.row.passed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="failed_requests" :label="$t('apiTesting.report.failedCount')" width="100">
          <template #default="scope">
            <span style="color: #f56c6c">{{ scope.row.failed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="executed_by.username" :label="$t('apiTesting.report.executor')" width="120" />
        <el-table-column prop="created_at" :label="$t('apiTesting.report.executionTime')" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.common.operation')" width="280">
          <template #default="scope">
            <el-button link type="success" size="small" @click="viewSimpleReport(scope.row)">{{ $t('apiTesting.report.simpleReport') }}</el-button>
            <el-button link type="primary" size="small" @click="viewOnlineReport(scope.row)">{{ $t('apiTesting.report.onlineReport') }}</el-button>
            <el-button link type="warning" size="small" @click="downloadOfflineReport(scope.row)">{{ $t('apiTesting.report.downloadOfflineReport') }}</el-button>
            <el-popconfirm
              v-if="!scope.row.is_system"
              :title="$t('apiTesting.common.confirmDelete')"
              :confirmButtonText="$t('apiTesting.common.confirm')"
              :cancelButtonText="$t('apiTesting.common.cancel')"
              @confirm="deleteExecution(scope.row)"
            >
              <template #reference>
                <el-button link type="danger" size="small">{{ $t('apiTesting.common.delete') }}</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 15, 30]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 简易报告弹窗 -->
    <el-dialog v-model="showDetailDialog" :title="$t('apiTesting.report.executionDetail')" width="1000px" destroy-on-close>
      <div v-if="currentReport" class="report-detail">
        <!-- 执行概览卡片 -->
        <div class="execution-overview">
          <div class="overview-header">
            <div class="overview-title">
              <el-icon class="title-icon"><Document /></el-icon>
              <span>{{ currentReport.test_suite_name || '-' }}</span>
            </div>
            <el-tag :type="getStatusType(currentReport.status)" size="large">
              {{ getStatusText(currentReport.status) }}
            </el-tag>
          </div>
          
          <div class="overview-meta">
            <div class="meta-item">
              <span class="meta-label">{{ $t('apiTesting.automation.belongProject') }}</span>
              <span class="meta-value">{{ currentReport.project_name || '-' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ $t('apiTesting.automation.executionEnvironment') }}</span>
              <span class="meta-value">{{ currentReport.environment_name || '-' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ $t('apiTesting.report.executor') }}</span>
              <span class="meta-value">{{ currentReport.executed_by?.username || '-' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ $t('apiTesting.report.executionTime') }}</span>
              <span class="meta-value">{{ formatDate(currentReport.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 统计卡片 -->
        <div class="stats-cards">
          <div class="stat-card total">
            <div class="stat-value">{{ currentReport.total_requests || (currentReport.results?.length || 0) }}</div>
            <div class="stat-label">{{ $t('apiTesting.report.totalRequests') }}</div>
          </div>
          <div class="stat-card passed">
            <div class="stat-value">{{ currentReport.passed_requests ?? getPassedCount() }}</div>
            <div class="stat-label">{{ $t('apiTesting.report.passedCount') }}</div>
          </div>
          <div class="stat-card failed">
            <div class="stat-value">{{ currentReport.failed_requests ?? getFailedCount() }}</div>
            <div class="stat-label">{{ $t('apiTesting.report.failedCount') }}</div>
          </div>
          <div class="stat-card skipped">
            <div class="stat-value">{{ currentReport.skipped_requests ?? getSkippedCount() }}</div>
            <div class="stat-label">{{ $t('apiTesting.report.skippedCount') }}</div>
          </div>
          <div class="stat-card rate">
            <div class="stat-value" :style="{ color: getPassRateColor(getPassRate()) }">{{ getPassRate() }}%</div>
            <div class="stat-label">{{ $t('apiTesting.report.passRate') }}</div>
          </div>
        </div>

        <!-- 请求结果表格 -->
        <div class="results-section">
          <h4>{{ $t('apiTesting.report.requestResults') }}</h4>
          <el-table :data="currentReport.results || []" border size="small" max-height="400">
            <el-table-column prop="name" :label="$t('apiTesting.common.name')" min-width="150" />
            <el-table-column prop="method" :label="$t('apiTesting.common.method')" width="90" />
            <el-table-column prop="status_code" :label="$t('apiTesting.report.statusCode')" width="90" />
            <el-table-column :label="$t('apiTesting.report.responseTime')" width="110">
              <template #default="{ row }">
                {{ row.response_time != null && row.response_time !== undefined ? row.response_time.toFixed(0) + 'ms' : '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('apiTesting.report.result')" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="getResultType(row)" size="small">
                  {{ getResultText(row) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('apiTesting.report.error')" min-width="200">
              <template #default="{ row }">
                <el-tooltip 
                  v-if="row.error" 
                  :content="row.error" 
                  placement="top" 
                  :disabled="row.error.length <= 50"
                >
                  <span class="error-text">{{ truncateText(row.error, 50) }}</span>
                </el-tooltip>
                <span v-else style="color: #909399;">-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()
const reports = ref([])
const loading = ref(false)
const showDetailDialog = ref(false)
const currentReport = ref(null)

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 15,
  total: 0
})

const loadReports = async () => {
  loading.value = true
  try {
    const response = await api.get('/api-testing/test-executions/', {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize
      }
    })
    const data = response.data
    reports.value = data.results || data
    pagination.total = data.count || (data.results ? data.length : 0)
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadReports'))
  } finally {
    loading.value = false
  }
}

const refreshReports = async () => {
  await loadReports()
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  loadReports()
}

const handlePageChange = (val) => {
  pagination.page = val
  loadReports()
}

// 查看简易报告
const viewSimpleReport = (report) => {
  // 先获取最新状态（避免缓存导致的状态不一致）
  api.get(`/api-testing/test-executions/${report.id}/`).then(res => {
    currentReport.value = res.data
    showDetailDialog.value = true
  }).catch(() => {
    currentReport.value = report
    showDetailDialog.value = true
  })
}

// 查看在线报告 - 异步获取最新状态后判断
const viewOnlineReport = async (report) => {
  try {
    const res = await api.get(`/api-testing/test-executions/${report.id}/`)
    const latest = res.data
    
    if (!latest.report_status || latest.report_status === 'PENDING' || latest.report_status === 'GENERATING') {
      ElMessage.warning(t('apiTesting.report.reportGenerating'))
      return
    }
    
    if (latest.report_url && latest.report_status === 'SUCCESS') {
      window.open(`${window.location.origin}${latest.report_url}`, '_blank')
    } else if (latest.report_status === 'SKIPPED') {
      ElMessage.info(t('apiTesting.report.reportNotGenerated'))
    } else {
      ElMessage.warning(t('apiTesting.report.reportNotGenerated'))
    }
  } catch (e) {
    ElMessage.error(t('apiTesting.messages.error.loadReports'))
  }
}

// 下载离线报告
const downloadOfflineReport = async (report) => {
  try {
    const res = await api.get(`/api-testing/test-executions/${report.id}/`)
    const latest = res.data
    
    if (!latest.report_status || latest.report_status !== 'SUCCESS') {
      ElMessage.warning(t('apiTesting.report.reportGenerating'))
      return
    }
    
    // 尝试下载 single-file 报告
    const url = `/api/api-testing-single-file-reports/execution_${report.id}/index.html`
    const a = document.createElement('a')
    a.href = url
    a.download = `test-report-${report.id}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } catch (e) {
    ElMessage.error(t('apiTesting.report.downloadFailed'))
  }
}

// 删除执行记录
const deleteExecution = async (report) => {
  try {
    await api.delete(`/api-testing/test-executions/${report.id}/`)
    ElMessage.success(t('apiTesting.common.deleteSuccess'))
    await loadReports()
  } catch (e) {
    ElMessage.error(t('apiTesting.common.deleteFailed'))
  }
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
  return statusKey ? t(`apiTesting.report.status.${statusKey}`) : status
}

const getPassRate = () => {
  if (!currentReport.value?.results) return 0
  const results = currentReport.value.results
  const total = results.length
  if (total === 0) return 0
  const passed = results.filter(r => r.passed !== false).length
  return Math.round((passed / total) * 100)
}

const getPassedCount = () => {
  if (!currentReport.value?.results) return 0
  return currentReport.value.results.filter(r => r.passed !== false).length
}

const getFailedCount = () => {
  if (!currentReport.value?.results) return 0
  return currentReport.value.results.filter(r => r.passed === false).length
}

const getSkippedCount = () => {
  if (!currentReport.value?.results) return 0
  return currentReport.value.results.filter(r => r.skipped === true).length
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`
  }
  const minutes = Math.floor(seconds / 60)
  const secs = (seconds % 60).toFixed(0)
  return `${minutes}m ${secs}s`
}

const getPassRateColor = (rate) => {
  if (rate >= 90) return '#67c23a'
  if (rate >= 70) return '#e6a23c'
  return '#f56c6c'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

const getResultType = (row) => {
  if (row.passed === true) return 'success'
  if (row.passed === false) return 'danger'
  if (row.skipped === true) return 'warning'
  return 'info'
}

const getResultText = (row) => {
  if (row.passed === true) return t('apiTesting.automation.resultPassed')
  if (row.passed === false) return t('apiTesting.automation.resultFailed')
  if (row.skipped === true) return t('apiTesting.report.skipped') || '跳过'
  return '-'
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.report-view {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #303133;
}

.content {
  flex: 1;
  overflow: auto;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 10px 0;
}

/* 简易报告样式 - 现代风格 */
.execution-overview {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  color: #fff;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.overview-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
}

.overview-title .title-icon {
  font-size: 22px;
}

.overview-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  opacity: 0.8;
}

.meta-value {
  font-size: 14px;
  font-weight: 500;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #ebeef5;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.stat-card .stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-card .stat-label {
  font-size: 13px;
  color: #909399;
}

.stat-card.total .stat-value {
  color: #409eff;
}

.stat-card.passed .stat-value {
  color: #67c23a;
}

.stat-card.failed .stat-value {
  color: #f56c6c;
}

.stat-card.skipped .stat-value {
  color: #909399;
}

.stat-card.rate .stat-value {
  color: #e6a23c;
}

.results-section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 15px;
  font-weight: 600;
}

.error-text {
  color: #f56c6c;
  font-size: 13px;
}
</style>
