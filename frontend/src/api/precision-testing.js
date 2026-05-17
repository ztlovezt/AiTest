import request from '@/utils/api'

// ===== 仓库绑定 =====
export function getRepoBindings(params) {
  return request({ url: '/precision-testing/repos/', method: 'get', params })
}
export function getProjectOptions() {
  return request({ url: '/projects/list/', method: 'get' })
}
export function createRepoBinding(data) {
  return request({ url: '/precision-testing/repos/', method: 'post', data })
}
export function getRepoBindingDetail(id) {
  return request({ url: `/precision-testing/repos/${id}/`, method: 'get' })
}
export function updateRepoBinding(id, data) {
  return request({ url: `/precision-testing/repos/${id}/`, method: 'patch', data })
}
export function deleteRepoBinding(id) {
  return request({ url: `/precision-testing/repos/${id}/`, method: 'delete' })
}
export function triggerAnalysis(id) {
  return request({ url: `/precision-testing/repos/${id}/analyze/`, method: 'post' })
}


// ===== 变更分析 =====
export function getChangeAnalyses(params) {
  return request({ url: '/precision-testing/analyses/', method: 'get', params })
}
export function getChangeAnalysisDetail(id) {
  return request({ url: `/precision-testing/analyses/${id}/`, method: 'get' })
}
export function getAnalysisProgress(id) {
  return request({ url: `/precision-testing/analyses/${id}/progress/`, method: 'get' })
}

// ===== 用例映射 =====
export function getMappings(params) {
  return request({ url: '/precision-testing/mappings/', method: 'get', params })
}
export function createMapping(data) {
  return request({ url: '/precision-testing/mappings/', method: 'post', data })
}
export function updateMapping(id, data) {
  return request({ url: `/precision-testing/mappings/${id}/`, method: 'patch', data })
}
export function deleteMapping(id) {
  return request({ url: `/precision-testing/mappings/${id}/`, method: 'delete' })
}
export function autoBuildMappings(data) {
  return request({ url: '/precision-testing/mappings/auto-build/', method: 'post', data })
}

// ===== 影响分析 =====
export function getImpactAnalyses(params) {
  return request({ url: '/precision-testing/impact/', method: 'get', params })
}
export function queryImpact(data) {
  return request({ url: '/precision-testing/impact/query/', method: 'post', data })
}

// ===== 图谱数据 =====
export function getGraphData(params) {
  return request({ url: '/precision-testing/graph/', method: 'get', params })
}

// ===== 风险预测 =====
export function getRiskPredictions(params) {
  return request({ url: '/precision-testing/predictions/', method: 'get', params })
}

// ===== 执行记录 =====
export function getRunRecords(params) {
  return request({ url: '/precision-testing/runs/', method: 'get', params })
}
export function getRunRecordDetail(id) {
  return request({ url: `/precision-testing/runs/${id}/`, method: 'get' })
}
export function triggerPipeline(data) {
  return request({ url: '/precision-testing/runs/trigger-pipeline/', method: 'post', data })
}
export function supplementRunRecord(id, data) {
  return request({ url: `/precision-testing/runs/${id}/supplement/`, method: 'post', data })
}

// ===== 仪表盘 =====
export function getDashboard(params) {
  return request({ url: '/precision-testing/dashboard/', method: 'get', params })
}
