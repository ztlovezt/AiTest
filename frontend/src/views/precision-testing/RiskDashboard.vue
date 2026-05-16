<template>
  <div class="risk-dashboard" v-loading="loading">
    <!-- KPI 统计卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="hover" class="kpi-card">
          <el-statistic title="绑定仓库数" :value="stats.repo_count ?? 0">
            <template #prefix><el-icon class="kpi-icon kpi-blue"><Connection /></el-icon></template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="kpi-card">
          <el-statistic title="变更分析次数" :value="stats.analysis_count ?? 0">
            <template #prefix><el-icon class="kpi-icon kpi-green"><DataAnalysis /></el-icon></template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="kpi-card">
          <el-statistic title="映射关系总数" :value="stats.mapping_count ?? 0">
            <template #prefix><el-icon class="kpi-icon kpi-orange"><Link /></el-icon></template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="kpi-card">
          <el-statistic title="平均缩减率" :value="stats.avg_reduction_rate ?? 0" :precision="1" suffix="%">
            <template #prefix><el-icon class="kpi-icon kpi-purple"><TrendCharts /></el-icon></template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="16" class="chart-row">
      <!-- 风险分布饼图 -->
      <el-col :span="8">
        <el-card shadow="never" class="chart-card">
          <template #header>风险等级分布</template>
          <div ref="riskPieRef" class="chart-box"></div>
        </el-card>
      </el-col>

      <!-- 近期分析趋势折线图 -->
      <el-col :span="16">
        <el-card shadow="never" class="chart-card">
          <template #header>近 14 天变更分析趋势</template>
          <div ref="trendLineRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <!-- Top 变更文件 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>高风险文件 Top 10</template>
          <div ref="topFilesRef" class="chart-box"></div>
        </el-card>
      </el-col>

      <!-- 精准执行堆叠条形图 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>执行记录 — 精准 vs 全量</template>
          <div ref="runBarRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, DataAnalysis, Link, TrendCharts } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getDashboard } from '@/api/precision-testing'

const loading = ref(false)
const stats = ref({})
const riskPieRef = ref(null)
const trendLineRef = ref(null)
const topFilesRef = ref(null)
const runBarRef = ref(null)

let charts = []
const disposeAll = () => { charts.forEach(c => c?.dispose()); charts = [] }

const initRiskPie = (data) => {
  const c = echarts.init(riskPieRef.value)
  charts.push(c)
  c.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
    series: [{
      type: 'pie', radius: ['40%', '65%'], center: ['50%', '45%'],
      data: [
        { name: '高风险', value: data?.high ?? 0, itemStyle: { color: '#f56c6c' } },
        { name: '中风险', value: data?.medium ?? 0, itemStyle: { color: '#e6a23c' } },
        { name: '低风险', value: data?.low ?? 0, itemStyle: { color: '#67c23a' } },
      ],
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
    }],
  })
}

const initTrendLine = (data) => {
  const c = echarts.init(trendLineRef.value)
  charts.push(c)
  c.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['分析次数', '变更函数数'] },
    xAxis: { type: 'category', data: data?.dates ?? [], axisLabel: { rotate: 30, fontSize: 11 } },
    yAxis: { type: 'value' },
    series: [
      { name: '分析次数', type: 'line', smooth: true, data: data?.analysis_counts ?? [], itemStyle: { color: '#5470c6' }, areaStyle: { opacity: 0.1 } },
      { name: '变更函数数', type: 'line', smooth: true, data: data?.function_counts ?? [], itemStyle: { color: '#91cc75' } },
    ],
  })
}

const initTopFiles = (data) => {
  const c = echarts.init(topFilesRef.value)
  charts.push(c)
  const files = data?.slice(0, 10) ?? []
  c.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '8%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: files.map(f => f.file_path?.split('/').pop() || f.file_path),
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: files.map(f => ({
        value: f.risk_score ?? f.change_count ?? 0,
        itemStyle: { color: f.risk_score > 0.7 ? '#f56c6c' : f.risk_score > 0.4 ? '#e6a23c' : '#5470c6' },
      })),
    }],
  })
}

const initRunBar = (data) => {
  const c = echarts.init(runBarRef.value)
  charts.push(c)
  c.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['精准执行', '全量执行'] },
    xAxis: { type: 'category', data: data?.dates ?? [] },
    yAxis: { type: 'value' },
    series: [
      { name: '精准执行', type: 'bar', stack: 'run', data: data?.precision_counts ?? [], itemStyle: { color: '#5470c6' } },
      { name: '全量执行', type: 'bar', stack: 'run', data: data?.full_counts ?? [], itemStyle: { color: '#91cc75' } },
    ],
  })
}

const loadDashboard = async () => {
  loading.value = true
  try {
    const res = await getDashboard()
    const d = res.data
    stats.value = d.summary ?? {}
    initRiskPie(d.risk_distribution)
    initTrendLine(d.trend)
    initTopFiles(d.top_risky_files)
    initRunBar(d.run_stats)
  } catch {
    ElMessage.error('加载仪表盘数据失败')
    // 加载失败时用空数据初始化图表，避免空容器
    initRiskPie({}); initTrendLine({}); initTopFiles([]); initRunBar({})
  } finally {
    loading.value = false
  }
}

const handleResize = () => charts.forEach(c => c?.resize())

onMounted(() => {
  loadDashboard()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  disposeAll()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.risk-dashboard { padding: 20px; }
.kpi-row { margin-bottom: 16px; }
.kpi-card { cursor: default; }
.kpi-icon { font-size: 28px; margin-right: 8px; }
.kpi-blue { color: #5470c6; }
.kpi-green { color: #67c23a; }
.kpi-orange { color: #e6a23c; }
.kpi-purple { color: #9b59b6; }
.chart-row { margin-bottom: 16px; }
.chart-card {}
.chart-box { height: 240px; }
</style>
