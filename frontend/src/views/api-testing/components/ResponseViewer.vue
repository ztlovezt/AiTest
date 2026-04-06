<template>
  <div class="response-viewer">
    <!-- 响应元信息 -->
    <div class="response-meta">
      <el-tag :type="statusType" size="large" effect="dark" class="status-tag">
        {{ statusCode }}
      </el-tag>
      <div class="meta-item">
        <span class="meta-label">{{ $t('apiTesting.response.time') }}</span>
        <span class="meta-value" :class="timeClass">{{ responseTime }}ms</span>
      </div>
      <div class="meta-item" v-if="responseSize">
        <span class="meta-label">{{ $t('apiTesting.response.size') }}</span>
        <span class="meta-value">{{ responseSize }}</span>
      </div>
    </div>

    <!-- 功能标签页 -->
    <el-tabs v-model="activeTab" class="response-tabs">
      <!-- Body Tab -->
      <el-tab-pane :label="$t('apiTesting.response.body')" name="body">
        <div class="body-toolbar">
          <div class="toolbar-left">
            <el-radio-group v-model="bodyViewMode" size="small">
              <el-radio-button value="tree" v-if="isJson">
                <el-icon><DataBoard /></el-icon> {{ $t('apiTesting.response.treeView') }}
              </el-radio-button>
              <el-radio-button value="table" v-if="isJsonArray">
                <el-icon><Grid /></el-icon> {{ $t('apiTesting.response.tableView') }}
              </el-radio-button>
              <el-radio-button value="raw">
                <el-icon><Document /></el-icon> {{ $t('apiTesting.response.rawView') }}
              </el-radio-button>
              <el-radio-button value="preview" v-if="isHtml || isImage">
                <el-icon><View /></el-icon> {{ $t('apiTesting.response.preview') }}
              </el-radio-button>
            </el-radio-group>
            <div v-if="isJson" class="jsonpath-search">
              <el-input
                v-model="jsonPathQuery"
                :placeholder="$t('apiTesting.response.jsonPathPlaceholder')"
                size="small"
                clearable
                @keyup.enter="evaluateJsonPath"
                style="width: 260px;"
              />
              <el-button size="small" type="primary" @click="evaluateJsonPath">
                {{ $t('apiTesting.response.query') || '查询' }}
              </el-button>
              <el-tooltip :content="$t('apiTesting.response.jsonPathHelp') || '查看JSONPath语法文档'" placement="top">
                <el-link 
                  href="https://goessner.net/articles/JsonPath/" 
                  target="_blank" 
                  underline="never"
                  class="jsonpath-help-link"
                >
                  <el-icon><QuestionFilled /></el-icon>
                </el-link>
              </el-tooltip>
            </div>
          </div>
          <div class="toolbar-right">
            <el-button size="small" @click="copyBody">
              <el-icon><CopyDocument /></el-icon> {{ $t('apiTesting.response.copy') }}
            </el-button>
          </div>
        </div>

        <!-- JSONPath 查询结果 -->
        <el-collapse v-if="isJson && jsonPathQuery && jsonPathResult !== null" class="jsonpath-result-collapse" v-model="jsonPathCollapseActive">
          <el-collapse-item name="result">
            <template #title>
              <div class="result-header">
                <span class="result-label">{{ $t('apiTesting.response.jsonPathResult') }}</span>
                <el-tag size="small" type="success">{{ getJsonPathResultType() }}</el-tag>
              </div>
            </template>
            <div class="result-body">
              <pre class="result-content">{{ JSON.stringify(jsonPathResult, null, 2) }}</pre>
              <el-button size="small" @click="copyJsonPathResult" class="copy-result-btn">
                <el-icon><CopyDocument /></el-icon> {{ $t('apiTesting.response.copy') }}
              </el-button>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-alert 
          v-else-if="isJson && jsonPathQuery && jsonPathResult === null" 
          type="warning" 
          :title="$t('apiTesting.response.jsonPathError')" 
          :closable="false"
          show-icon
          class="jsonpath-error-alert"
        />

        <!-- 树形视图 -->
        <div v-if="bodyViewMode === 'tree' && isJson" class="body-content">
          <JsonTreeView :data="jsonData" @select-path="onSelectPath" />
        </div>

        <!-- 表格视图 -->
        <div v-else-if="bodyViewMode === 'table' && isJsonArray" class="body-content">
          <el-table :data="tableData" border stripe max-height="460" size="small" class="response-table">
            <el-table-column
              v-for="col in tableColumns"
              :key="col"
              :prop="col"
              :label="col"
              min-width="120"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                <span v-if="row[col] === null" class="cell-null">null</span>
                <span v-else-if="typeof row[col] === 'boolean'" class="cell-boolean">{{ row[col] }}</span>
                <span v-else-if="typeof row[col] === 'object'" class="cell-object" :title="JSON.stringify(row[col])">
                  {{ JSON.stringify(row[col]) }}
                </span>
                <span v-else>{{ row[col] }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 原始文本视图 -->
        <div v-else-if="bodyViewMode === 'raw'" class="body-content">
          <pre class="raw-body" v-html="highlightedBody"></pre>
        </div>

        <!-- 预览视图 -->
        <div v-else-if="bodyViewMode === 'preview'" class="body-content">
          <iframe v-if="isHtml" :srcdoc="rawBody" class="html-preview" sandbox="allow-same-origin"></iframe>
          <img v-else-if="isImage" :src="imageUrl" class="image-preview" />
        </div>
      </el-tab-pane>

      <!-- Headers Tab -->
      <el-tab-pane :label="headersLabel" name="headers">
        <el-input
          v-model="headerSearch"
          :placeholder="$t('apiTesting.response.searchHeaders')"
          size="small"
          clearable
          prefix-icon="Search"
          class="header-search"
        />
        <el-table :data="filteredHeaders" border size="small" max-height="400" class="headers-table">
          <el-table-column prop="key" label="Key" width="240">
            <template #default="{ row }">
              <span class="header-key">{{ row.key }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="Value" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="header-value">{{ row.value }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Assertions Tab -->
      <el-tab-pane v-if="assertions && assertions.length > 0" :label="assertionsLabel" name="assertions">
        <div class="assertions-list">
          <div
            v-for="(result, index) in assertions"
            :key="index"
            class="assertion-item"
            :class="result.passed ? 'passed' : 'failed'"
          >
            <div class="assertion-header">
              <el-tag :type="result.passed ? 'success' : 'danger'" size="small">
                {{ result.passed ? $t('apiTesting.response.passed') : $t('apiTesting.response.failed') }}
              </el-tag>
              <span class="assertion-name">{{ result.name || $t('apiTesting.response.unnamed') }}</span>
              <span class="assertion-type">{{ result.type }}</span>
            </div>
            <div class="assertion-detail">
              <div class="detail-row">
                <span class="detail-label">{{ $t('apiTesting.response.expected') }}:</span>
                <code class="detail-value">{{ formatAssertionValue(result.expected) }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ $t('apiTesting.response.actual') }}:</span>
                <code class="detail-value" :class="result.passed ? '' : 'error-value'">{{ formatAssertionValue(result.actual) }}</code>
              </div>
              <div class="detail-row" v-if="result.error">
                <span class="detail-label">{{ $t('apiTesting.response.error') }}:</span>
                <code class="detail-value error-value">{{ result.error }}</code>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { CopyDocument, DataBoard, Grid, Document, View, QuestionFilled } from '@element-plus/icons-vue'
import JsonTreeView from './JsonTreeView.vue'

const { t } = useI18n()

const props = defineProps({
  responseData: { type: Object, default: null },
  statusCode: { type: Number, default: 0 },
  responseTime: { type: Number, default: 0 },
  assertions: { type: Array, default: () => [] }
})

const emit = defineEmits(['select-path'])

const activeTab = ref('body')
const bodyViewMode = ref('tree')
const headerSearch = ref('')
const jsonPathQuery = ref('')
const jsonPathResult = ref(null)
const jsonPathCollapseActive = ref(['result'])

// 状态码颜色
const statusType = computed(() => {
  const code = props.statusCode
  if (code >= 200 && code < 300) return 'success'
  if (code >= 300 && code < 400) return 'warning'
  if (code >= 400 && code < 500) return 'danger'
  if (code >= 500) return 'danger'
  return 'info'
})

// 响应时间颜色
const timeClass = computed(() => {
  const time = props.responseTime
  if (time < 200) return 'time-fast'
  if (time < 1000) return 'time-normal'
  return 'time-slow'
})

// 响应体
const rawBody = computed(() => {
  if (!props.responseData) return ''
  if (props.responseData.json) return JSON.stringify(props.responseData.json, null, 2)
  return props.responseData.body || ''
})

// JSON 数据
const jsonData = computed(() => {
  if (!props.responseData) return null
  return props.responseData.json || null
})

const isJson = computed(() => jsonData.value !== null)

const isJsonArray = computed(() => Array.isArray(jsonData.value))

const isHtml = computed(() => {
  if (!props.responseData) return false
  const contentType = getHeaderValue('content-type') || ''
  return contentType.includes('text/html')
})

const isImage = computed(() => {
  if (!props.responseData) return false
  const contentType = getHeaderValue('content-type') || ''
  return contentType.startsWith('image/')
})

const imageUrl = computed(() => {
  if (!isImage.value || !props.responseData?.body) return ''
  const contentType = getHeaderValue('content-type') || 'image/png'
  return `data:${contentType};base64,${props.responseData.body}`
})

// 响应大小
const responseSize = computed(() => {
  const body = rawBody.value
  if (!body) return ''
  const bytes = new Blob([body]).size
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
})

// 默认视图模式
watch(isJson, (val) => {
  bodyViewMode.value = val ? 'tree' : 'raw'
}, { immediate: true })

// 语法高亮
const highlightedBody = computed(() => {
  const body = rawBody.value
  if (!body) return ''
  const escaped = body
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  if (isJson.value) {
    return escaped
      .replace(/"([^"]+)"\s*:/g, '<span class="hl-key">"$1"</span>:')
      .replace(/:\s*"([^"]*?)"/g, ': <span class="hl-string">"$1"</span>')
      .replace(/:\s*(true|false|null)/g, ': <span class="hl-keyword">$1</span>')
      .replace(/:\s*(-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?)/g, ': <span class="hl-number">$1</span>')
  }
  return escaped
})

// Headers
function getHeaderValue(name) {
  const headers = props.responseData?.headers
  if (!headers) return null
  const lowerName = name.toLowerCase()
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() === lowerName) return headers[key]
  }
  return null
}

const headersList = computed(() => {
  const headers = props.responseData?.headers
  if (!headers) return []
  return Object.entries(headers).map(([key, value]) => ({ key, value: String(value) }))
})

const filteredHeaders = computed(() => {
  if (!headerSearch.value) return headersList.value
  const kw = headerSearch.value.toLowerCase()
  return headersList.value.filter(h =>
    h.key.toLowerCase().includes(kw) || h.value.toLowerCase().includes(kw)
  )
})

const headersLabel = computed(() => {
  const count = headersList.value.length
  return `Headers (${count})`
})

const assertionsLabel = computed(() => {
  const total = props.assertions.length
  const passed = props.assertions.filter(a => a.passed).length
  return `${t('apiTesting.response.assertions')} (${passed}/${total})`
})

// 表格视图
const tableColumns = computed(() => {
  if (!isJsonArray.value || !jsonData.value.length) return []
  const firstItem = jsonData.value[0]
  if (typeof firstItem !== 'object' || firstItem === null) return ['value']
  return Object.keys(firstItem)
})

const tableData = computed(() => {
  if (!isJsonArray.value) return []
  const data = jsonData.value
  if (!data.length) return []
  if (typeof data[0] !== 'object' || data[0] === null) {
    return data.map(v => ({ value: v }))
  }
  return data.slice(0, 500) // 限制显示行数
})

function copyBody() {
  if (rawBody.value) {
    navigator.clipboard.writeText(rawBody.value)
    ElMessage.success(t('apiTesting.response.copied'))
  }
}

function onSelectPath(path) {
  emit('select-path', path)
}

function formatAssertionValue(value) {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// JSONPath 查询
const evaluateJsonPath = () => {
  if (!jsonPathQuery.value || !jsonData.value) {
    jsonPathResult.value = null
    return
  }

  try {
    // 简单的 JSONPath 实现
    // 支持: $ (根), $.key, $.key.subkey, $[index], $[index].key
    const result = simpleJsonPath(jsonData.value, jsonPathQuery.value)
    jsonPathResult.value = result
  } catch (error) {
    console.error('JSONPath 查询失败:', error)
    jsonPathResult.value = null
  }
}

function simpleJsonPath(obj, path) {
  if (!path || path === '$') return obj

  const tokens = tokenize(path)
  if (tokens.length === 0) return obj

  let results = [obj]

  for (const token of tokens) {
    const newResults = []
    
    for (const current of results) {
      if (current === null || current === undefined) continue
      
      if (token.type === 'child') {
        if (current !== null && typeof current === 'object') {
          if (token.value === '*') {
            if (Array.isArray(current)) {
              newResults.push(...current)
            } else {
              newResults.push(...Object.values(current))
            }
          } else if (token.value in current) {
            newResults.push(current[token.value])
          }
        }
      } else if (token.type === 'index') {
        if (Array.isArray(current) && token.value >= 0 && token.value < current.length) {
          newResults.push(current[token.value])
        }
      } else if (token.type === 'slice') {
        if (Array.isArray(current)) {
          const start = token.start ?? 0
          const end = token.end ?? current.length
          const step = token.step ?? 1
          for (let i = start; i < end; i += step) {
            if (i >= 0 && i < current.length) {
              newResults.push(current[i])
            }
          }
        }
      } else if (token.type === 'wildcard') {
        if (Array.isArray(current)) {
          newResults.push(...current)
        } else if (current !== null && typeof current === 'object') {
          newResults.push(...Object.values(current))
        }
      } else if (token.type === 'recursive') {
        const key = token.value
        collectRecursive(current, key, newResults)
      }
    }
    
    results = newResults
  }

  if (results.length === 0) return null
  if (results.length === 1) return results[0]
  return results
}

function tokenize(path) {
  const tokens = []
  let i = 0
  
  if (path[i] === '$') i++
  
  while (i < path.length) {
    if (path[i] === '.' && path[i + 1] === '.') {
      i += 2
      let key = ''
      while (i < path.length && path[i] !== '.' && path[i] !== '[') {
        key += path[i]
        i++
      }
      if (key === '*') {
        tokens.push({ type: 'recursiveWildcard' })
      } else {
        tokens.push({ type: 'recursive', value: key })
      }
    } else if (path[i] === '.') {
      i++
      let key = ''
      while (i < path.length && path[i] !== '.' && path[i] !== '[') {
        key += path[i]
        i++
      }
      if (key === '*') {
        tokens.push({ type: 'wildcard' })
      } else {
        tokens.push({ type: 'child', value: key })
      }
    } else if (path[i] === '[') {
      i++
      if (path[i] === "'") {
        i++
        let key = ''
        while (i < path.length && path[i] !== "'") {
          key += path[i]
          i++
        }
        i++
        if (path[i] === ']') i++
        tokens.push({ type: 'child', value: key })
      } else if (path[i] === '"') {
        i++
        let key = ''
        while (i < path.length && path[i] !== '"') {
          key += path[i]
          i++
        }
        i++
        if (path[i] === ']') i++
        tokens.push({ type: 'child', value: key })
      } else if (path[i] === '*') {
        i++
        if (path[i] === ']') i++
        tokens.push({ type: 'wildcard' })
      } else if (path[i] === ':') {
        i++
        let end = ''
        while (i < path.length && path[i] !== ']') {
          end += path[i]
          i++
        }
        i++
        tokens.push({ type: 'slice', start: 0, end: end ? parseInt(end) : undefined, step: 1 })
      } else {
        let content = ''
        while (i < path.length && path[i] !== ']' && path[i] !== ':') {
          content += path[i]
          i++
        }
        if (path[i] === ':') {
          i++
          const start = content ? parseInt(content) : undefined
          let end = ''
          while (i < path.length && path[i] !== ']' && path[i] !== ':') {
            end += path[i]
            i++
          }
          let step = 1
          if (path[i] === ':') {
            i++
            let stepStr = ''
            while (i < path.length && path[i] !== ']') {
              stepStr += path[i]
              i++
            }
            step = stepStr ? parseInt(stepStr) : 1
          }
          i++
          tokens.push({ type: 'slice', start, end: end ? parseInt(end) : undefined, step })
        } else {
          i++
          const indices = content.split(',').map(s => s.trim())
          for (const idx of indices) {
            if (idx.includes("'") || idx.includes('"')) {
              tokens.push({ type: 'child', value: idx.replace(/['"]/g, '') })
            } else {
              tokens.push({ type: 'index', value: parseInt(idx) })
            }
          }
        }
      }
    } else {
      i++
    }
  }
  
  return tokens
}

function collectRecursive(obj, key, results) {
  if (obj === null || obj === undefined) return
  
  if (Array.isArray(obj)) {
    for (const item of obj) {
      collectRecursive(item, key, results)
    }
  } else if (typeof obj === 'object') {
    if (key in obj) {
      results.push(obj[key])
    }
    for (const value of Object.values(obj)) {
      collectRecursive(value, key, results)
    }
  }
}

function getJsonPathResultType() {
  if (jsonPathResult.value === null) return 'null'
  if (Array.isArray(jsonPathResult.value)) return `Array[${jsonPathResult.value.length}]`
  if (typeof jsonPathResult.value === 'object') return 'Object'
  return typeof jsonPathResult.value
}

function copyJsonPathResult() {
  if (jsonPathResult.value !== null) {
    navigator.clipboard.writeText(JSON.stringify(jsonPathResult.value, null, 2))
    ElMessage.success(t('apiTesting.response.copied'))
  }
}
</script>

<style scoped>
.response-viewer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.response-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.status-tag {
  font-size: 14px;
  font-weight: bold;
  min-width: 50px;
  text-align: center;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-label {
  color: #909399;
  font-size: 13px;
}

.meta-value {
  font-weight: 600;
  font-size: 13px;
}

.time-fast { color: var(--th-color-success); }
.time-normal { color: #e6a23c; }
.time-slow { color: #f56c6c; }

.response-tabs {
  margin-top: -4px;
}

.body-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.jsonpath-search {
  display: flex;
  align-items: center;
  gap: 8px;
}

.jsonpath-help-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  color: #909399;
  transition: all 0.2s;
}

.jsonpath-help-link:hover {
  background: #e6e8eb;
  color: #409eff;
}

.body-content {
  min-height: 100px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fff;
}

.raw-body {
  background: var(--th-color-surface-muted);
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 12px;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  max-height: 500px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.raw-body :deep(.hl-key) { color: #268bd2; }
.raw-body :deep(.hl-string) { color: #2aa198; }
.raw-body :deep(.hl-keyword) { color: #cb4b16; }
.raw-body :deep(.hl-number) { color: #d33682; }

.html-preview {
  width: 100%;
  min-height: 400px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.image-preview {
  max-width: 100%;
  max-height: 500px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.response-table {
  width: 100%;
}

.cell-null { color: #93a1a1; font-style: italic; }
.cell-boolean { color: #cb4b16; }
.cell-object { color: #586e75; font-size: 12px; }

/* Headers */
.header-search {
  width: 240px;
  margin-bottom: 8px;
}

.headers-table {
  width: 100%;
}

.header-key {
  font-weight: 600;
  color: #303133;
}

.header-value {
  color: #606266;
  word-break: break-all;
}

/* Assertions */
.assertions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assertion-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 14px;
  border-left: 3px solid;
}

.assertion-item.passed {
  border-left-color: var(--th-color-success);
  background: var(--th-color-success-soft);
}

.assertion-item.failed {
  border-left-color: #f56c6c;
  background: var(--th-color-danger-soft);
}

.assertion-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.assertion-name {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
}

.assertion-type {
  color: #909399;
  font-size: 12px;
  margin-left: auto;
}

.assertion-detail {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.detail-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
}

.detail-label {
  color: #909399;
  min-width: 50px;
  flex-shrink: 0;
}

.detail-value {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  color: #303133;
  background: rgba(0, 0, 0, 0.04);
  padding: 1px 6px;
  border-radius: 3px;
  word-break: break-all;
}

.error-value {
  color: #f56c6c;
}

/* JSONPath 查询结果 */
.jsonpath-result-collapse {
  margin-bottom: 12px;
  border: 1px solid #e6f7ff;
  border-radius: 6px;
  overflow: hidden;
}

.jsonpath-result-collapse :deep(.el-collapse-item__header) {
  background: #e6f7ff;
  padding: 0 12px;
  height: 40px;
}

.jsonpath-result-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.jsonpath-result-collapse :deep(.el-collapse-item__content) {
  padding: 0;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-label {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
}

.result-body {
  padding: 12px;
  background: #fafafa;
}

.result-content {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 10px;
  margin: 0 0 10px 0;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  max-height: 300px;
  overflow: auto;
}

.copy-result-btn {
  float: right;
}

.jsonpath-error-alert {
  margin-bottom: 12px;
}
</style>
