/** 精准测试模块通用格式化工具函数 */
import dayjs from 'dayjs'

/** 格式化日期时间 */
export function formatDateTime(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}

/** 格式化日期 */
export function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD') : '-'
}

/** 格式化百分比（缩减率等） */
export function formatRate(rate) {
  if (rate == null) return '-'
  return `${(rate * 100).toFixed(1)}%`
}

/** 格式化耗时（秒） */
export function formatDuration(seconds) {
  if (seconds == null) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m${s}s`
}

/** 状态标签类型（Element Plus Tag type） */
export function statusType(status) {
  return (
    {
      completed: 'success',
      failed: 'danger',
      running: 'primary',
      pending: 'info',
    }[status] || 'info'
  )
}

/** 状态中文标签 */
export function statusLabel(status) {
  return (
    {
      completed: '已完成',
      failed: '失败',
      running: '运行中',
      pending: '等待中',
    }[status] || status
  )
}

/** 缩减率进度条颜色 */
export function reductionColor(rate) {
  if (rate >= 0.6) return '#67c23a'
  if (rate >= 0.3) return '#e6a23c'
  return '#f56c6c'
}

/** 风险分数文字颜色 */
export function riskColor(score) {
  if (score == null) return '#333'
  if (score > 0.7) return '#f56c6c'
  if (score > 0.4) return '#e6a23c'
  return '#67c23a'
}
