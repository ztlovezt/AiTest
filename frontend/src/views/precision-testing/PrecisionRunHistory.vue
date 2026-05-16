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

    <!-- 详情侧抽屉 -->
    <el-drawer v-model="showDrawer" title="执行记录详情" size="480px" direction="rtl">
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

        <div class="drawer-section">
          <div class="drawer-section-title">精准回归用例（{{ detailData.selected_cases?.length ?? 0 }} 个）</div>
          <el-table :data="detailData.selected_cases || []" size="small" border max-height="300">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="用例名称" show-overflow-tooltip />
            <el-table-column prop="risk_score" label="风险分" width="90" align="center">
              <template #default="{ row }">
                <span :style="{ color: riskColor(row.risk_score) }">{{ row.risk_score != null ? row.risk_score.toFixed(2) : '-' }}</span>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Loading } from '@element-plus/icons-vue'
import { getRunRecords, getRunRecordDetail } from '@/api/precision-testing'
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
</style>
