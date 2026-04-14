<template>
  <div class="app-automation-dashboard">
    <!-- 统计卡片 -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-blue">
                <el-icon><Cellphone /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ statistics.devices.total }}</div>
                <div class="stat-label">{{ t('appAutomation.dashboard.totalDevices') }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-green">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ statistics.devices.online }}</div>
                <div class="stat-label">{{ t('appAutomation.dashboard.onlineDevices') }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-orange">
                <el-icon><Lock /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ statistics.devices.locked }}</div>
                <div class="stat-label">{{ t('appAutomation.dashboard.lockedDevices') }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon bg-purple">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ statistics.test_cases.total }}</div>
                <div class="stat-label">{{ t('appAutomation.dashboard.totalTestCases') }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <!-- 执行统计和最近执行 -->
    <el-row :gutter="20" class="content-section">
      <!-- 执行统计 -->
      <el-col :span="12">
        <el-card class="stat-chart" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>{{ t('appAutomation.dashboard.executionStats') }}</span>
            </div>
          </template>
          <div class="chart-container">
            <div class="stat-item">
              <div class="stat-label">{{ t('appAutomation.dashboard.totalExecutions') }}</div>
              <div class="stat-value large">{{ statistics.executions.total }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">{{ t('appAutomation.dashboard.successCount') }}</div>
              <div class="stat-value success">{{ statistics.executions.success }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">{{ t('appAutomation.dashboard.failedCount') }}</div>
              <div class="stat-value danger">{{ statistics.executions.failed }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">{{ t('appAutomation.dashboard.passRate') }}</div>
              <div class="stat-value" :class="getPassRateClass(statistics.executions.pass_rate)">
                {{ statistics.executions.pass_rate }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 最近执行记录 -->
      <el-col :span="12">
        <el-card class="recent-executions" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>{{ t('appAutomation.dashboard.recentExecutions') }}</span>
              <el-button type="primary" size="small" @click="$router.push('/app-automation/executions')">
                {{ t('appAutomation.dashboard.viewAll') }}
              </el-button>
            </div>
          </template>
          <div v-if="loading" class="loading-container">
            <el-empty :description="t('appAutomation.dashboard.loading')" />
          </div>
          <div v-else-if="statistics.recent_executions.length === 0" class="empty-container">
            <el-empty :description="t('appAutomation.dashboard.noExecutions')" />
          </div>
          <div v-else class="executions-list">
            <div v-for="execution in statistics.recent_executions" :key="execution.id" class="execution-item">
              <div class="execution-info">
                <div class="execution-name">{{ execution.case_name }}</div>
                <div class="execution-meta">
                  <el-tag :type="getStatusType(execution.status)" size="small">
                    {{ getStatusText(execution.status) }}
                  </el-tag>
                  <span class="device-name">{{ t('appAutomation.dashboard.device') }}: {{ execution.device_name }}</span>
                  <span class="execution-time">{{ formatTime(execution.created_at) }}</span>
                </div>
              </div>
              <div class="execution-actions">
                <el-button 
                  type="primary" 
                  size="small" 
                  text
                  @click="viewExecution(execution)"
                >
                  查看
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 快速操作 -->
    <el-row :gutter="20" class="quick-actions-section">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>{{ t('appAutomation.dashboard.quickActions') }}</span>
            </div>
          </template>
          <div class="actions-grid">
            <div class="action-item" @click="$router.push('/app-automation/devices')">
              <div class="action-icon bg-blue">
                <el-icon><Cellphone /></el-icon>
              </div>
              <div class="action-label">{{ t('appAutomation.dashboard.deviceManagement') }}</div>
            </div>
            <div class="action-item" @click="$router.push('/app-automation/elements')">
              <div class="action-icon bg-green">
                <el-icon><Picture /></el-icon>
              </div>
              <div class="action-label">{{ t('appAutomation.dashboard.elementManagement') }}</div>
            </div>
            <div class="action-item" @click="$router.push('/app-automation/test-cases')">
              <div class="action-icon bg-purple">
                <el-icon><Document /></el-icon>
              </div>
              <div class="action-label">{{ t('appAutomation.dashboard.testCaseManagement') }}</div>
            </div>
            <div class="action-item" @click="$router.push('/app-automation/executions')">
              <div class="action-icon bg-orange">
                <el-icon><Aim /></el-icon>
              </div>
              <div class="action-label">{{ t('appAutomation.dashboard.executionRecords') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getDashboardStatistics } from '@/api/app-automation'
import { getExecutionStatusType, getExecutionStatusText, formatRelativeTime } from '@/utils/app-automation-helpers'
import { 
  Cellphone, 
  CircleCheck, 
  Lock, 
  Document, 
  Picture,
  Aim
} from '@element-plus/icons-vue'

const { t } = useI18n()

const loading = ref(false)
const statistics = ref({
  devices: {
    total: 0,
    online: 0,
    locked: 0,
    available: 0
  },
  test_cases: {
    total: 0
  },
  executions: {
    total: 0,
    success: 0,
    failed: 0,
    pass_rate: 0
  },
  recent_executions: []
})

const loadStatistics = async (isRefresh = false) => {
  if (!isRefresh) {
    loading.value = true
  }
  try {
    const res = await getDashboardStatistics()
    if (res.data.success) {
      statistics.value = res.data.data
    } else {
      console.error('加载统计数据失败:', res.data)
      if (!isRefresh) {
        ElMessage.error(t('appAutomation.dashboard.loadStatsFailed'))
      }
    }
  } catch (error) {
    console.error('加载统计数据异常:', error)
    if (!isRefresh) {
      ElMessage.error(t('appAutomation.dashboard.loadStatsFailed') + ': ' + (error.message || t('common.unknown')))
    }
  } finally {
    if (!isRefresh) {
      loading.value = false
    }
  }
}

const getStatusType = getExecutionStatusType
const getStatusText = getExecutionStatusText
const formatTime = formatRelativeTime

const getPassRateClass = (rate) => {
  if (rate >= 90) return 'success'
  if (rate >= 70) return 'warning'
  return 'danger'
}

const viewExecution = (execution) => {
  if (!execution || !execution.id) {
    console.warn('查看执行记录失败: 执行记录ID无效', execution)
    ElMessage.warning(t('appAutomation.dashboard.invalidExecutionId'))
    return
  }
  
  if (execution.report_path) {
    console.log(`打开执行报告: execution_id=${execution.id}, report_path=${execution.report_path}`)
    const reportUrl = `/api/app-automation/executions/${execution.id}/report/index.html`
    window.open(reportUrl, '_blank')
  } else {
    console.warn(`执行记录无报告: execution_id=${execution.id}`)
    ElMessage.warning(t('appAutomation.dashboard.noReportAvailable'))
  }
}

let refreshTimer = null

onMounted(() => {
  loadStatistics()
  // 每30秒刷新一次统计数据（无感知刷新）
  refreshTimer = setInterval(() => loadStatistics(true), 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped lang="scss">
.app-automation-dashboard {
  padding: 20px;
}

.stats-section {
  margin-bottom: 20px;
}

.stat-card {
  cursor: pointer;
  transition: transform 0.3s;
  
  &:hover {
    transform: translateY(-5px);
  }
  
  .stat-content {
    display: flex;
    align-items: center;
    gap: 15px;
    
    .stat-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      color: white;
      
      &.bg-blue { background: linear-gradient(135deg, var(--th-color-info) 0%, #00f2fe 100%); }
      &.bg-green { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
      &.bg-orange { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
      &.bg-purple { background: linear-gradient(135deg, var(--th-color-primary) 0%, var(--th-color-primary-strong) 100%); }
    }
    
    .stat-info {
      flex: 1;
      
      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #303133;
        line-height: 1;
        margin-bottom: 8px;
      }
      
      .stat-label {
        font-size: 14px;
        color: #909399;
      }
    }
  }
}

.content-section {
  margin-bottom: 20px;
  
  .el-col {
    display: flex;
    
    .el-card {
      width: 100%;
      display: flex;
      flex-direction: column;
      
      :deep(.el-card__body) {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
    }
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.stat-chart {
  .chart-container {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    flex: 1;
    
    .stat-item {
      text-align: center;
      padding: 15px;
      border-radius: 8px;
      background: var(--th-color-surface-muted);
      
      .stat-label {
        font-size: 14px;
        color: #909399;
        margin-bottom: 10px;
      }
      
      .stat-value {
        font-size: 24px;
        font-weight: bold;
        
        &.large { font-size: 32px; color: var(--th-color-primary); }
        &.success { color: var(--th-color-success); }
        &.warning { color: #e6a23c; }
        &.danger { color: #f56c6c; }
      }
    }
  }
}

.recent-executions {
  :deep(.el-card__body) {
    padding: 0;
  }
  
  .loading-container,
  .empty-container {
    padding: 40px 20px;
  }
  
  .executions-list {
    flex: 1;
    max-height: 400px;
    overflow-y: auto;
    
    .execution-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      border-bottom: 1px solid #ebeef5;
      
      &:last-child {
        border-bottom: none;
      }
      
      &:hover {
        background: var(--th-color-surface-muted);
      }
      
      .execution-info {
        flex: 1;
        
        .execution-name {
          font-size: 14px;
          font-weight: 500;
          color: #303133;
          margin-bottom: 8px;
        }
        
        .execution-meta {
          display: flex;
          gap: 12px;
          align-items: center;
          font-size: 12px;
          color: #909399;
          
          .device-name {
            display: flex;
            align-items: center;
            gap: 4px;
          }
        }
      }
    }
  }
}

.quick-actions-section {
  .actions-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    
    .action-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding: 20px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s;
      background: var(--th-color-surface-muted);
      
      &:hover {
        background: var(--th-color-info-soft);
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      }
      
      .action-icon {
        width: 50px;
        height: 50px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        color: white;
        
        &.bg-blue { background: linear-gradient(135deg, var(--th-color-info) 0%, #00f2fe 100%); }
        &.bg-green { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        &.bg-orange { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        &.bg-purple { background: linear-gradient(135deg, var(--th-color-primary) 0%, var(--th-color-primary-strong) 100%); }
      }
      
      .action-label {
        font-size: 14px;
        font-weight: 500;
        color: #303133;
      }
    }
  }
}

.loading-container,
.empty-container {
  padding: 40px 0;
}

@media screen and (max-width: 1400px) {
  .executions-list {
    max-height: 350px;
  }
  
  .actions-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
  }
}

@media screen and (max-width: 1200px) {
  .stats-section {
    margin-bottom: 15px;
  }
  
  .stat-card {
    .stat-content {
      .stat-icon {
        width: 50px;
        height: 50px;
        font-size: 20px;
      }
      
      .stat-info {
        .stat-value {
          font-size: 24px;
        }
        
        .stat-label {
          font-size: 12px;
        }
      }
    }
  }
  
  .executions-list {
    max-height: 300px;
  }
  
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}

@media screen and (max-width: 768px) {
  .app-automation-dashboard {
    padding: 10px;
  }
  
  .stats-section {
    margin-bottom: 10px;
  }
  
  .content-section {
    margin-bottom: 15px;
  }
  
  .executions-list {
    max-height: 250px;
  }
  
  .action-item {
    padding: 15px;
    
    .action-icon {
      width: 40px;
      height: 40px;
      font-size: 20px;
    }
    
    .action-label {
      font-size: 12px;
    }
  }
}
</style>
