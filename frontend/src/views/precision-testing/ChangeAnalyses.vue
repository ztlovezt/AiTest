<template>
  <div class="change-analyses">
    <div class="layout-container">
      <!-- 左侧列表 -->
      <div class="sidebar-panel">
        <div class="panel-header">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索提交 / 分支..."
            clearable
            size="small"
            @input="handleSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <div v-loading="loading" class="list-scroll">
          <div
            v-for="item in tableData"
            :key="item.id"
            class="list-item"
            :class="{ active: selected?.id === item.id }"
            @click="selectItem(item)"
          >
            <div class="item-header">
              <el-tag :type="statusType(item.status)" size="small" effect="plain">
                {{ statusLabel(item.status) }}
              </el-tag>
              <span class="item-time">{{ formatDate(item.created_at) }}</span>
            </div>
            <div class="item-commit" :title="item.commit_hash">
              {{ item.commit_hash?.slice(0, 8) || '-' }}
            </div>
            <div class="item-branch">{{ item.branch || '-' }}</div>
          </div>
          <div v-if="!loading && tableData.length === 0" class="empty-tip">暂无分析记录</div>
        </div>

        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          small
          layout="prev, pager, next"
          @change="loadData"
          class="sidebar-pagination"
        />
      </div>

      <!-- 右侧详情 -->
      <div class="detail-panel">
        <div v-if="!selected" class="empty-detail">
          <el-empty description="请选择左侧分析记录查看详情" />
        </div>

        <template v-else>
          <!-- 基本信息 -->
          <el-card class="detail-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span>分析详情</span>
                <el-tag :type="statusType(selected.status)" effect="plain">
                  {{ statusLabel(selected.status) }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="提交哈希">{{ selected.commit_hash }}</el-descriptions-item>
              <el-descriptions-item label="分支">{{ selected.branch }}</el-descriptions-item>
              <el-descriptions-item label="提交时间">{{ formatDate(selected.commit_time) }}</el-descriptions-item>
              <el-descriptions-item label="触发时间">{{ formatDate(selected.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="变更文件数">{{ selected.changed_files_count ?? '-' }}</el-descriptions-item>
              <el-descriptions-item label="变更函数数">{{ selected.changed_functions_count ?? '-' }}</el-descriptions-item>
              <el-descriptions-item label="提交信息" :span="2">{{ selected.commit_message || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 变更文件列表 -->
          <el-card class="detail-card" shadow="never">
            <template #header>变更文件</template>
            <div v-if="detailLoading" class="loading-center"><el-icon class="is-loading"><Loading /></el-icon> 加载中...</div>
            <el-collapse v-else accordion>
              <el-collapse-item
                v-for="(file, idx) in detail?.changed_files || []"
                :key="idx"
                :title="`${file.path}（+${file.added} -${file.removed}）`"
              >
                <el-table :data="file.functions || []" size="small" border>
                  <el-table-column prop="name" label="函数名" />
                  <el-table-column prop="change_type" label="变更类型" width="100">
                    <template #default="{ row }">
                      <el-tag :type="changeTypeTag(row.change_type)" size="small">{{ row.change_type }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="start_line" label="起始行" width="80" />
                </el-table>
              </el-collapse-item>
              <div v-if="!detail?.changed_files?.length" class="empty-tip">无变更文件数据</div>
            </el-collapse>
          </el-card>

          <!-- 进度（若仍在运行） -->
          <el-card v-if="selected.status === 'running' || selected.status === 'pending'" class="detail-card" shadow="never">
            <template #header>分析进度</template>
            <el-progress :percentage="progressPct" :striped="true" :striped-flow="true" :duration="10" />
            <p class="progress-label">{{ progressMsg }}</p>
          </el-card>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Loading } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getChangeAnalyses, getChangeAnalysisDetail, getAnalysisProgress } from '@/api/precision-testing'

const loading = ref(false)
const tableData = ref([])
const searchKeyword = ref('')
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const selected = ref(null)
const detail = ref(null)
const detailLoading = ref(false)
const progressPct = ref(0)
const progressMsg = ref('')
let progressTimer = null
let searchTimer = null
let progressPollingToken = 0 // 取消令牌：切换记录 / 卸载时使旧轮询失效
let progressErrorCount = 0    // 连续错误次数：避免单次抖动立即告警

const stopProgressPolling = () => {
  progressPollingToken++
  if (progressTimer) {
    clearTimeout(progressTimer)
    progressTimer = null
  }
  progressErrorCount = 0
}

const formatDate = (v) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-'

const statusType = (s) => ({ completed: 'success', failed: 'danger', running: 'primary', pending: 'info' }[s] || 'info')
const statusLabel = (s) => ({ completed: '已完成', failed: '失败', running: '运行中', pending: '等待中' }[s] || s)
const changeTypeTag = (t) => ({ added: 'success', modified: 'warning', deleted: 'danger' }[t] || 'info')

const loadData = async () => {
  loading.value = true
  try {
    const res = await getChangeAnalyses({ page: pagination.page, page_size: pagination.pageSize, search: searchKeyword.value || undefined })
    tableData.value = res.data.results ?? res.data
    pagination.total = res.data.count ?? 0
  } catch {
    ElMessage.error('加载分析记录失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { pagination.page = 1; loadData() }, 400)
}

const selectItem = async (item) => {
  selected.value = item
  detail.value = null
  stopProgressPolling()
  if (item.status === 'running' || item.status === 'pending') {
    pollProgress(item.id)
  }
  detailLoading.value = true
  try {
    const res = await getChangeAnalysisDetail(item.id)
    detail.value = res.data
  } catch {
    ElMessage.error('加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

const pollProgress = (id) => {
  const myToken = ++progressPollingToken
  clearTimeout(progressTimer)
  progressTimer = setTimeout(async () => {
    if (myToken !== progressPollingToken) return
    try {
      const res = await getAnalysisProgress(id)
      if (myToken !== progressPollingToken) return
      progressErrorCount = 0
      const { status, progress } = res.data
      progressPct.value = progress ?? Math.min(progressPct.value + 8, 95)
      progressMsg.value = status
      if (status === 'completed' || status === 'failed') {
        loadData()
        const updated = tableData.value.find(i => i.id === id)
        if (updated) selected.value = { ...selected.value, status: updated.status }
      } else {
        pollProgress(id)
      }
    } catch (err) {
      if (myToken !== progressPollingToken) return
      progressErrorCount++
      if (progressErrorCount >= 3) {
        ElMessage.warning('进度查询失败，已停止轮询')
        stopProgressPolling()
      } else {
        pollProgress(id)
      }
    }
  }, 2500)
}

onMounted(loadData)
onBeforeUnmount(() => { stopProgressPolling(); clearTimeout(searchTimer) })
</script>

<style scoped>
.change-analyses { padding: 20px; height: 100%; box-sizing: border-box; }
.layout-container { display: flex; gap: 16px; height: calc(100vh - 160px); }

.sidebar-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
}
.panel-header { padding: 12px; border-bottom: 1px solid var(--el-border-color); }
.list-scroll { flex: 1; overflow-y: auto; }
.list-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background 0.2s;
}
.list-item:hover { background: var(--el-fill-color-light); }
.list-item.active { background: var(--el-color-primary-light-9); }
.item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.item-time { font-size: 11px; color: var(--el-text-color-placeholder); }
.item-commit { font-family: monospace; font-size: 13px; color: var(--el-text-color-primary); }
.item-branch { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }
.sidebar-pagination { padding: 8px; justify-content: center; }

.detail-panel { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.empty-detail { display: flex; align-items: center; justify-content: center; height: 100%; }
.detail-card {}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.empty-tip { padding: 20px; text-align: center; color: var(--el-text-color-placeholder); }
.loading-center { display: flex; align-items: center; gap: 8px; color: var(--el-text-color-secondary); padding: 12px 0; }
.progress-label { margin-top: 8px; font-size: 12px; color: var(--el-text-color-secondary); }
</style>
