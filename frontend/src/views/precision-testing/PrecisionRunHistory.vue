<template>
  <div class="run-history">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="filterStatus" placeholder="执行状态" clearable style="width: 130px" @change="handleFilter">
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
          <el-option label="运行中" value="running" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px; margin-left: 8px"
          value-format="YYYY-MM-DD"
          @change="handleFilter"
        />
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="openTriggerDialog">触发精准回归</el-button>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table v-loading="loading" :data="tableData" border stripe style="width: 100%" @row-click="openDetail">
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column prop="repo_name" label="仓库" min-width="140" show-overflow-tooltip />
      <el-table-column prop="commit_hash" label="提交" width="100">
        <template #default="{ row }">{{ row.commit_hash?.slice(0, 8) || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="95" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="精准用例数" width="110" align="center">
        <template #default="{ row }">{{ row.selected_case_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="全量用例数" width="110" align="center">
        <template #default="{ row }">{{ row.total_case_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="缩减率" width="160" align="center">
        <template #default="{ row }">
          <el-progress
            v-if="row.reduction_rate != null"
            :percentage="Math.round(row.reduction_rate * 100)"
            :color="reductionColor(row.reduction_rate)"
            :stroke-width="8"
          />
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="triggered_at" label="触发时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.triggered_at) }}</template>
      </el-table-column>
      <el-table-column prop="duration_seconds" label="耗时(s)" width="90" align="center">
        <template #default="{ row }">{{ row.duration_seconds ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click.stop="openDetail(row)">详情</el-button>
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

    <!-- 触发流水线对话框 -->
    <el-dialog v-model="showTriggerDialog" title="触发精准回归流水线" width="500px">
      <el-form :model="triggerForm" label-width="100px">
        <el-form-item label="选择仓库" required>
          <el-select v-model="triggerForm.repo_binding_id" placeholder="请选择仓库" style="width: 100%">
            <el-option v-for="r in repoOptions" :key="r.id" :label="r.project?.name || r.repo_path" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base Commit" required>
          <el-input v-model="triggerForm.base_commit" placeholder="如: HEAD~1 或完整 hash" />
        </el-form-item>
        <el-form-item label="Head Commit" required>
          <el-input v-model="triggerForm.head_commit" placeholder="如: HEAD 或完整 hash" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTriggerDialog = false">取消</el-button>
        <el-button type="primary" :loading="triggerLoading" @click="submitTrigger">触发执行</el-button>
      </template>
    </el-dialog>

    <!-- 详情侧抽屉 -->
    <el-drawer v-model="showDrawer" title="执行记录详情" size="560px" direction="rtl">
      <div v-if="detailLoading" class="drawer-loading"><el-icon class="is-loading"><Loading /></el-icon> 加载中...</div>
      <template v-else-if="detailData">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="ID">{{ detailData.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(detailData.status)" size="small">{{ statusLabel(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="仓库">{{ detailData.repo_name }}</el-descriptions-item>
          <el-descriptions-item label="分支">{{ detailData.branch }}</el-descriptions-item>
          <el-descriptions-item label="提交">{{ detailData.commit_hash?.slice(0, 12) }}</el-descriptions-item>
          <el-descriptions-item label="触发时间">{{ formatDateTime(detailData.triggered_at) }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ formatDuration(detailData.duration_seconds) }}</el-descriptions-item>
          <el-descriptions-item label="缩减率">{{ formatRate(detailData.reduction_rate) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 执行统计 -->
        <div v-if="caseStats" class="drawer-section">
          <div class="drawer-section-title">测试执行结果</div>
          <div class="stats-row">
            <div class="stat-item">
              <div class="stat-value">{{ caseStats.total }}</div>
              <div class="stat-label">总用例</div>
            </div>
            <div class="stat-item success">
              <div class="stat-value">{{ caseStats.passed }}</div>
              <div class="stat-label">通过</div>
            </div>
            <div class="stat-item danger">
              <div class="stat-value">{{ caseStats.failed }}</div>
              <div class="stat-label">失败</div>
            </div>
            <div class="stat-item warning">
              <div class="stat-value">{{ caseStats.blocked }}</div>
              <div class="stat-label">阻塞</div>
            </div>
            <div class="stat-item info">
              <div class="stat-value">{{ caseStats.untested }}</div>
              <div class="stat-label">未测</div>
            </div>
          </div>
          <el-progress
            :percentage="caseStats.progress"
            :stroke-width="10"
            :color="['#67c23a', '#e6a23c', '#f56c6c', '#909399']"
            style="margin-top: 10px"
          />
        </div>

        <!-- 全量用例 -->
        <div class="drawer-section">
          <div class="drawer-section-title">
            全量用例（{{ detailData.total_cases?.length ?? 0 }} 个）
            <el-tag v-if="detailData.total_cases?.length > 0" type="info" size="small" style="margin-left: 8px">
              选中 {{ (detailData.selected_cases?.length ?? 0) + (detailData.supplement_testcases?.length ?? 0) }} 个
            </el-tag>
          </div>
          <div v-if="detailData.total_cases?.length > 0" style="margin-bottom: 8px;">
            <el-button
              type="primary"
              size="small"
              :loading="supplementLoading"
              :disabled="!supplementSelection.length"
              @click="submitSupplement"
            >
              批量补充执行 ({{ supplementSelection.length }})
            </el-button>
          </div>
          <el-table
            :data="detailData.total_cases || []"
            size="small"
            border
            max-height="300"
            @selection-change="handleSupplementSelectionChange"
          >
            <el-table-column type="selection" width="55" :selectable="(row) => !row.selected" />
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="用例名称" show-overflow-tooltip min-width="140" />
            <el-table-column prop="priority" label="优先级" width="80" align="center" />
            <el-table-column label="是否选中" width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.selected" type="success" size="small">已选中</el-tag>
                <el-tag v-else type="info" size="small">未选中</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="drawer-section">
          <div class="drawer-section-title">
            精准回归用例（{{ detailData.selected_cases?.length ?? 0 }} 个）
            <el-tag v-if="detailData.supplement_testcases?.length > 0" type="warning" size="small" style="margin-left: 8px">
              含补充 {{ detailData.supplement_testcases.length }} 个
            </el-tag>
          </div>
          <el-table :data="detailData.selected_cases || []" size="small" border max-height="300">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="用例名称" show-overflow-tooltip min-width="140" />
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="caseStatusType(row.status)" size="small">{{ caseStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="risk_score" label="风险分" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ color: riskColor(row.risk_score) }">{{ row.risk_score != null ? row.risk_score.toFixed(2) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="actual_result" label="实际结果" show-overflow-tooltip min-width="100">
              <template #default="{ row }">
                <span>{{ row.actual_result || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="detailData.error_message" class="drawer-section">
          <div class="drawer-section-title error-title">错误信息</div>
          <el-alert :title="detailData.error_message" type="error" :closable="false" show-icon />
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Loading } from '@element-plus/icons-vue'
import { getRunRecords, getRunRecordDetail, triggerPipeline, getRepoBindings, supplementRunRecord } from '@/api/precision-testing'
import {
  formatDateTime,
  formatRate,
  formatDuration,
  statusType,
  statusLabel,
  reductionColor,
  riskColor,
} from '@/utils/precision-formatters'

const loading = ref(false)
const tableData = ref([])
const filterStatus = ref('')
const dateRange = ref(null)
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const showDrawer = ref(false)
const detailLoading = ref(false)
const detailData = ref(null)

// 补充执行选择
const supplementSelection = ref([])
const supplementLoading = ref(false)
const handleSupplementSelectionChange = (selection) => {
  supplementSelection.value = selection
}

// 触发流水线对话框
const showTriggerDialog = ref(false)
const triggerLoading = ref(false)
const repoOptions = ref([])
const triggerForm = reactive({
  repo_binding_id: null,
  base_commit: '',
  head_commit: '',
})

const loadData = async () => {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (filterStatus.value) params.status = filterStatus.value
    if (dateRange.value?.[0]) params.start_date = dateRange.value[0]
    if (dateRange.value?.[1]) params.end_date = dateRange.value[1]
    const res = await getRunRecords(params)
    tableData.value = res.data.results ?? res.data
    pagination.total = res.data.count ?? 0
  } catch {
    ElMessage.error('加载执行记录失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => { pagination.page = 1; loadData() }

const openDetail = async (row) => {
  showDrawer.value = true
  detailData.value = null
  detailLoading.value = true
  try {
    const res = await getRunRecordDetail(row.id)
    detailData.value = res.data
  } catch {
    ElMessage.error('加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

// 触发流水线
const openTriggerDialog = async () => {
  showTriggerDialog.value = true
  triggerForm.repo_binding_id = null
  triggerForm.base_commit = ''
  triggerForm.head_commit = ''
  try {
    const res = await getRepoBindings({ is_active: true, page_size: 100 })
    repoOptions.value = res.data.results ?? res.data ?? []
  } catch {
    ElMessage.error('加载仓库列表失败')
  }
}

const submitTrigger = async () => {
  if (!triggerForm.repo_binding_id || !triggerForm.base_commit || !triggerForm.head_commit) {
    ElMessage.warning('请填写完整信息')
    return
  }
  triggerLoading.value = true
  try {
    await triggerPipeline({
      repo_binding_id: triggerForm.repo_binding_id,
      base_commit: triggerForm.base_commit,
      head_commit: triggerForm.head_commit,
    })
    ElMessage.success('精准回归流水线已触发，请稍后刷新查看结果')
    showTriggerDialog.value = false
    loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '触发失败')
  } finally {
    triggerLoading.value = false
  }
}

// 提交补充执行
const submitSupplement = async () => {
  if (!supplementSelection.value.length) {
    ElMessage.warning('请先选择要补充执行的用例')
    return
  }
  supplementLoading.value = true
  try {
    const testcaseIds = supplementSelection.value.map(row => row.id)
    await supplementRunRecord(detailData.value.id, { testcase_ids: testcaseIds })
    ElMessage.success(`成功补充 ${testcaseIds.length} 个用例`)
    // 刷新详情
    const res = await getRunRecordDetail(detailData.value.id)
    detailData.value = res.data
    supplementSelection.value = []
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '补充执行失败')
  } finally {
    supplementLoading.value = false
  }
}

// 执行状态标签类型
const caseStatusType = (status) => {
  const map = { passed: 'success', failed: 'danger', blocked: 'warning', retest: 'info', untested: 'info' }
  return map[status] || 'info'
}
const caseStatusLabel = (status) => {
  const map = { passed: '通过', failed: '失败', blocked: '阻塞', retest: '重测', untested: '未测试' }
  return map[status] || status
}

// 详情用例执行统计
const caseStats = computed(() => {
  const cases = detailData.value?.selected_cases || []
  const total = cases.length
  if (total === 0) return null
  const stats = { total, passed: 0, failed: 0, blocked: 0, retest: 0, untested: 0 }
  cases.forEach(c => { stats[c.status || 'untested'] = (stats[c.status || 'untested'] || 0) + 1 })
  stats.tested = stats.passed + stats.failed + stats.blocked + stats.retest
  stats.progress = Math.round((stats.tested / total) * 100)
  return stats
})

onMounted(loadData)
</script>

<style scoped>
.run-history { padding: 20px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.toolbar-left { display: flex; align-items: center; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
.drawer-loading { display: flex; align-items: center; gap: 8px; color: var(--el-text-color-secondary); padding: 20px 0; }
.drawer-section { margin-top: 20px; }
.drawer-section-title { font-size: 13px; font-weight: 600; color: var(--el-text-color-primary); margin-bottom: 8px; }
.error-title { color: var(--el-color-danger); }
.stats-row { display: flex; gap: 16px; justify-content: space-between; }
.stat-item { text-align: center; flex: 1; padding: 10px 0; background: var(--el-fill-color-light); border-radius: 6px; }
.stat-item.success .stat-value { color: #67c23a; }
.stat-item.danger .stat-value { color: #f56c6c; }
.stat-item.warning .stat-value { color: #e6a23c; }
.stat-item.info .stat-value { color: #909399; }
.stat-value { font-size: 20px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }
</style>
