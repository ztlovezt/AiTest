<template>
  <div class="knowledge-base-detail-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="router.back()">
          <el-icon><ArrowLeft /></el-icon>
          {{ $t('common.back') }}
        </el-button>
        <h2>{{ knowledgeBase.name }}</h2>
        <el-tag :type="knowledgeBase.is_active ? 'success' : 'danger'" size="small">
          {{ knowledgeBase.is_active ? $t('knowledgeBase.active') : $t('knowledgeBase.inactive') }}
        </el-tag>
      </div>
    </div>

    <!-- 基本信息卡片 -->
    <el-card class="info-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('knowledgeBase.basicInfo') }}</span>
        </div>
      </template>
      <el-descriptions :column="4" border>
        <el-descriptions-item :label="$t('knowledgeBase.project')">
          {{ knowledgeBase.project_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('knowledgeBase.chunkSize')">
          {{ knowledgeBase.chunk_size || 500 }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('knowledgeBase.chunkOverlap')">
          {{ knowledgeBase.chunk_overlap || 50 }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('knowledgeBase.vectorizationStatus')">
          <el-tag :type="getVectorStatusType(knowledgeBase.vectorization_status)" size="small">
            {{ knowledgeBase.vectorization_status_display || knowledgeBase.vectorization_status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('knowledgeBase.totalSize')">
          {{ formatFileSize(stats.total_size) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 文档列表卡片 -->
    <el-card class="document-list-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('knowledgeBase.documents') || '文档列表' }} ({{ stats.total_documents }})</span>
          <el-button type="primary" link @click="handleUploadDocument">
            <el-icon><Upload /></el-icon>
            {{ $t('knowledgeBase.uploadDocument') }}
          </el-button>
        </div>
      </template>
      <div class="document-list-wrapper">
        <el-table
          v-loading="documentListLoading"
          :data="documentList"
          style="width: 100%"
          height="280"
          border
        >
          <el-table-column type="index" width="60" :label="$t('common.index') || '序号'" align="center" />
          <el-table-column prop="title" :label="$t('knowledgeBase.documentTitle') || '文档名称'" min-width="200" show-overflow-tooltip />
          <el-table-column prop="document_type_display" :label="$t('knowledgeBase.documentType') || '类型'" width="115" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ (row.document_type_display || row.document_type || '').replace(/\.$/, '') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="vector_status" :label="$t('knowledgeBase.vectorizationStatus') || '向量化状态'" width="120" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="getVectorStatusType(row.vector_status)">
                {{ row.vector_status_display || row.vector_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="$t('knowledgeBase.createdAt') || '上传时间'" width="160" align="center">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('common.actions') || '操作'" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                @click="handleViewOriginal(row)"
              >
                {{ $t('knowledgeBase.viewOriginal') || '查看原文' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 混合检索测试 -->
    <el-card class="search-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('knowledgeBase.hybridSearch') }}</span>
        </div>
      </template>

      <!-- 搜索类型选择 -->
      <div class="search-type-row">
        <el-radio-group v-model="searchType" size="small">
          <el-radio-button value="hybrid">{{ $t('knowledgeBase.hybridSearchType') }}</el-radio-button>
          <el-radio-button value="semantic">{{ $t('knowledgeBase.semanticSearchType') }}</el-radio-button>
          <el-radio-button value="keyword">{{ $t('knowledgeBase.keywordSearchType') }}</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 搜索输入 -->
      <div class="search-input-row">
        <el-input
          v-model="searchQuery"
          :placeholder="$t('knowledgeBase.searchPlaceholder')"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" :loading="searchLoading" @click="handleSearch">
          {{ $t('knowledgeBase.search') }}
        </el-button>
      </div>

      <!-- 参数设置行 -->
      <div class="params-row">
        <div class="param-item">
          <span class="param-label">{{ $t('knowledgeBase.similarityThreshold') }}:</span>
          <el-slider
            v-model="similarityThreshold"
            :min="0"
            :max="1"
            :step="0.05"
            style="width: 120px;"
          />
          <span class="param-value">{{ (similarityThreshold * 100).toFixed(0) }}%</span>
        </div>
        <div class="param-item">
          <span class="param-label">{{ $t('knowledgeBase.topK') }}:</span>
          <el-select v-model="searchTopK" style="width: 80px;">
            <el-option v-for="i in 10" :key="i" :label="i" :value="i" />
          </el-select>
        </div>
        <div v-if="searchType === 'hybrid'" class="param-item">
          <span class="param-label">
            {{ $t('knowledgeBase.keywordWeight') }}
            <el-tooltip :content="$t('knowledgeBase.keywordWeightTip')" placement="top">
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
          <el-slider
            v-model="keywordWeight"
            :min="0"
            :max="1"
            :step="0.1"
            style="width: 120px;"
          />
          <span class="param-value">{{ formatWeightPercentage(keywordWeight) }}</span>
        </div>
      </div>

      <!-- 搜索结果 -->
      <div v-if="searchResults.length > 0" class="search-results">
        <div
          v-for="(result, index) in filteredResults"
          :key="index"
          class="result-item"
        >
          <div class="result-header">
            <span class="result-index">#{{ index + 1 }}</span>
            <span class="result-title">{{ result.document_title || result.documentTitle }}</span>
            <el-tag size="small" :type="getSourceType(result.source)">
              {{ result.source === 'hybrid' ? $t('knowledgeBase.hybridSource') :
                 result.source === 'semantic' ? $t('knowledgeBase.semanticSource') :
                 $t('knowledgeBase.keywordSource') }}
            </el-tag>
            <el-tag size="small" type="info">
              {{ $t('knowledgeBase.score') }}: {{ ((result.similarity || result.combined_score || 0) * 100).toFixed(1) }}%
            </el-tag>
            <el-button
              v-if="result.document_id"
              type="primary"
              link
              size="small"
              @click="handleViewOriginal(result)"
            >
              <el-icon><Document /></el-icon>
              {{ $t('knowledgeBase.viewOriginal') }}
            </el-button>
          </div>
          <div class="result-content">
            {{ result.content }}
          </div>
          <div class="result-meta">
            <span>{{ $t('knowledgeBase.chunkIndex') }}: {{ result.chunk_index || result.chunkIndex || 0 }}</span>
            <template v-if="result.semantic_score !== undefined || result.keyword_score !== undefined">
              <span style="margin-left: 15px;">
                {{ $t('knowledgeBase.semanticScore') }}: {{ (result.semantic_score * 100).toFixed(1) }}%
              </span>
              <span style="margin-left: 15px;">
                {{ $t('knowledgeBase.keywordScore') }}: {{ (result.keyword_score * 100).toFixed(1) }}%
              </span>
            </template>
            <!-- 向量检索占比 -->
            <div v-if="searchType === 'hybrid'" class="vector-ratio">
              <el-icon><InfoFilled /></el-icon>
              <span>{{ $t('knowledgeBase.vectorRatio') }}: {{ getVectorRatio(result) }}</span>
            </div>
          </div>
        </div>
      </div>

      <el-empty v-else-if="!searchLoading && searchQuerySearched" :description="$t('knowledgeBase.noResults')" />
    </el-card>

    <!-- 查看原文对话框 -->
    <el-dialog
      v-model="originalDialogVisible"
      :title="$t('knowledgeBase.originalDocument')"
      width="70%"
      top="5vh"
    >
      <div class="original-content">
        <div class="original-header">
          <h3>{{ currentOriginal.title }}</h3>
          <el-tag size="small" type="info">{{ (currentOriginal.document_type || '').replace(/\.$/, '') }}</el-tag>
        </div>
        <el-divider />
        <div class="original-text">
          <pre>{{ currentOriginal.content }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="originalDialogVisible = false">{{ $t('common.close') }}</el-button>
      </template>
    </el-dialog>

    <!-- 上传文档对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      :title="$t('knowledgeBase.uploadDocument')"
      width="500px"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="100px">
        <el-form-item :label="$t('knowledgeBase.file')" prop="fileList">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            multiple
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept=".pdf,.doc,.docx,.txt,.md"
          >
            <template #trigger>
              <el-button type="primary">{{ $t('knowledgeBase.selectFile') }}</el-button>
            </template>
            <template #tip>
              <div class="el-upload__tip">
                {{ $t('knowledgeBase.uploadTip') }}
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item :label="$t('knowledgeBase.tags')">
          <el-select
            v-model="uploadForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            :placeholder="$t('knowledgeBase.tagsPlaceholder')"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item :label="$t('knowledgeBase.status')">
          <el-radio-group v-model="uploadForm.status">
            <el-radio value="draft">{{ $t('knowledgeBase.preview') }}</el-radio>
            <el-radio value="published">{{ $t('knowledgeBase.published') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="uploadLoading" @click="handleSubmitUpload">
          {{ $t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Upload, Search, Document, QuestionFilled, InfoFilled
} from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import {
  getKnowledgeBaseDetail,
  getKnowledgeBaseStats,
  uploadDocument,
  semanticSearch,
  hybridSearch,
  getDocumentDetail,
  getDocumentList
} from '@/api/knowledge-base'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const knowledgeBaseId = route.params.id

// 数据
const uploadLoading = ref(false)
const searchLoading = ref(false)
const documentListLoading = ref(false)
const knowledgeBase = ref({})
const documentList = ref([])

// 统计
const stats = reactive({
  total_documents: 0,
  total_size: 0,
  published_count: 0,
  draft_count: 0
})

// 对话框
const uploadDialogVisible = ref(false)
const originalDialogVisible = ref(false)

// 当前查看的原文
const currentOriginal = reactive({
  id: null,
  title: '',
  content: '',
  document_type: '',
  file_url: null
})

// 表单
const uploadFormRef = ref(null)
const uploadRef = ref(null)

const uploadForm = reactive({
  fileList: [],
  tags: [],
  status: 'draft'
})

// 搜索
const searchType = ref('hybrid')
const searchQuery = ref('')
const searchQuerySearched = ref(false)
const similarityThreshold = ref(0)
const searchTopK = ref(5)
const keywordWeight = ref(0.3)
const searchResults = ref([])

// 轮询定时器
let pollingTimer = null

// 根据阈值过滤结果
const filteredResults = computed(() => {
  return searchResults.value.filter(result => {
    const score = result.similarity || result.combined_score || 0
    return score >= similarityThreshold.value
  })
})

// 格式化权重提示
const formatWeightTooltip = (val) => {
  return `${Math.round(val * 100)}%`
}

// 格式化权重百分比
const formatWeightPercentage = (val) => {
  return `${Math.round(val * 100)}%`
}

// 计算向量检索占比
const getVectorRatio = (result) => {
  if (result.semantic_score === undefined || result.keyword_score === undefined) {
    return '-'
  }
  const semanticWeight = result.semantic_score || 0
  const keywordWeightVal = result.keyword_score || 0
  const total = semanticWeight + keywordWeightVal
  if (total === 0) {
    return '-'
  }
  return `${Math.round((semanticWeight / total) * 100)}%`
}

// 开始轮询向量化状态
const startPolling = () => {
  if (pollingTimer) return
  pollingTimer = setInterval(async () => {
    if (knowledgeBase.value.vectorization_status === 'processing') {
      try {
        const response = await getKnowledgeBaseDetail(knowledgeBaseId)
        knowledgeBase.value = response.data
        fetchDocuments() // 轮询期间也要刷新文档列表以显示进度
        if (knowledgeBase.value.vectorization_status !== 'processing') {
          stopPolling()
          fetchStats()
        }
      } catch (error) {
        console.error('轮询状态失败:', error)
      }
    } else {
      stopPolling()
    }
  }, 3000)
}

// 停止轮询
const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

// 表单规则
const uploadRules = {
  fileList: [{ required: true, message: t('knowledgeBase.fileRequired'), trigger: 'change', type: 'array' }]
}

// 获取知识库详情
const fetchKnowledgeBase = async () => {
  try {
    const response = await getKnowledgeBaseDetail(knowledgeBaseId)
    knowledgeBase.value = response.data
  } catch (error) {
    ElMessage.error(t('common.fetchFailed'))
  }
}

// 获取统计信息
const fetchStats = async () => {
  try {
    const response = await getKnowledgeBaseStats(knowledgeBaseId)
    Object.assign(stats, response.data)
  } catch (error) {
    console.error('获取统计失败:', error)
  }
}

// 获取文档列表
const fetchDocuments = async () => {
  documentListLoading.value = true
  try {
    const response = await getDocumentList({
      knowledge_base_id: knowledgeBaseId,
      page_size: 1000 // 取足够多的文档显示在列表中
    })
    documentList.value = response.data.results || response.data
  } catch (error) {
    console.error('获取文档列表失败:', error)
  } finally {
    documentListLoading.value = false
  }
}

// 上传文档
const handleUploadDocument = () => {
  uploadForm.fileList = []
  uploadForm.tags = []
  uploadForm.status = 'draft'
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  uploadDialogVisible.value = true
}

const handleFileChange = (file, fileList) => {
  uploadForm.fileList = fileList.map(f => f.raw || f)
}

const handleFileRemove = (file, fileList) => {
  uploadForm.fileList = fileList.map(f => f.raw || f)
}

const handleSubmitUpload = async () => {
  if (!uploadFormRef.value) return
  await uploadFormRef.value.validate(async (valid) => {
    if (valid && uploadForm.fileList.length > 0) {
      uploadLoading.value = true
      try {
        const formData = new FormData()
        
        uploadForm.fileList.forEach(file => {
          formData.append('files', file)
        })
        
        formData.append('knowledge_base', knowledgeBaseId)
        formData.append('tags', JSON.stringify(uploadForm.tags))
        formData.append('status', uploadForm.status)
        
        await uploadDocument(formData)
        ElMessage.success(t('common.uploadSuccess'))
        uploadDialogVisible.value = false
        await fetchKnowledgeBase() // 重新获取知识库状态，触发轮询
        fetchStats()
        fetchDocuments()
        startPolling()
      } catch (error) {
        ElMessage.error(t('common.uploadFailed'))
      } finally {
        uploadLoading.value = false
      }
    } else if (uploadForm.fileList.length === 0) {
      ElMessage.warning(t('knowledgeBase.fileRequired'))
    }
  })
}

// 统一搜索处理
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning(t('knowledgeBase.searchQueryRequired'))
    return
  }

  searchLoading.value = true
  searchQuerySearched.value = true
  try {
    let response
    if (searchType.value === 'hybrid') {
      response = await hybridSearch(knowledgeBaseId, {
        query: searchQuery.value,
        top_k: searchTopK.value,
        similarity_threshold: similarityThreshold.value,
        keyword_weight: keywordWeight.value,
        semantic_weight: 1 - keywordWeight.value
      })
    } else if (searchType.value === 'semantic') {
      response = await semanticSearch(knowledgeBaseId, {
        query: searchQuery.value,
        top_k: searchTopK.value,
        similarity_threshold: similarityThreshold.value
      })
    } else {
      response = await hybridSearch(knowledgeBaseId, {
        query: searchQuery.value,
        top_k: searchTopK.value,
        similarity_threshold: similarityThreshold.value,
        keyword_weight: 1.0,
        semantic_weight: 0.0
      })
    }
    let results = response.data.results || []
    // 根据搜索类型设置正确的 source
    if (searchType.value === 'keyword') {
      results = results.map(item => ({ ...item, source: 'keyword' }))
    } else if (searchType.value === 'semantic') {
      results = results.map(item => ({ ...item, source: 'semantic' }))
    }
    searchResults.value = results
  } catch (error) {
    ElMessage.error(t('knowledgeBase.searchFailed'))
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

// 查看原文
const handleViewOriginal = async (result) => {
  const documentId = result.document_id || result.documentId || result.id
  if (!documentId) {
    ElMessage.warning(t('knowledgeBase.noDocumentId'))
    return
  }

  try {
    if (result.full_content) {
      currentOriginal.id = documentId
      currentOriginal.title = result.document_title || result.documentTitle || result.title
      currentOriginal.content = result.full_content
      currentOriginal.document_type = result.document_type || 'Unknown'
      currentOriginal.file_url = result.file_url
      originalDialogVisible.value = true
      return
    }

    const response = await getDocumentDetail(documentId)
    const doc = response.data
    currentOriginal.id = doc.id
    currentOriginal.title = doc.title
    currentOriginal.content = doc.content
    currentOriginal.document_type = doc.document_type_display || doc.document_type
    currentOriginal.file_url = doc.file || doc.file_url
    originalDialogVisible.value = true
  } catch (error) {
    ElMessage.error(t('knowledgeBase.fetchDocumentFailed'))
  }
}

// 获取来源类型
const getSourceType = (source) => {
  const types = {
    hybrid: 'success',
    semantic: 'primary',
    keyword: 'warning'
  }
  return types[source] || 'info'
}

// 工具函数
const getVectorStatusType = (status) => {
  const types = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

onMounted(() => {
  fetchKnowledgeBase()
  fetchStats()
  fetchDocuments()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.knowledge-base-detail-container {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 15px;

      h2 {
        margin: 0;
        font-size: 20px;
      }
    }

    .header-right {
      display: flex;
      gap: 10px;
    }
  }

  .info-card {
    margin-bottom: 20px;
  }

  .document-list-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .search-card {
    .search-type-row {
      margin-bottom: 15px;
    }

    .search-input-row {
      display: flex;
      align-items: center;
      margin-bottom: 20px;

      .el-input {
        flex: 1;
        margin-right: 10px;
      }
    }

    .params-row {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 30px;
      margin-bottom: 20px;
      padding: 15px;
      background: var(--th-color-surface-muted);
      border-radius: 8px;

      .param-item {
        display: flex;
        align-items: center;
        gap: 10px;

        .param-label {
          font-size: 14px;
          color: #606266;
          white-space: nowrap;
        }

        .param-value {
          min-width: 40px;
          font-size: 14px;
          color: var(--th-color-primary);
        }

        .help-icon {
          margin-left: 5px;
          color: #909399;
          cursor: help;
        }
      }

      .param-item-wide {
        flex: 1;
        min-width: 300px;
      }

      .weight-slider-container {
        display: flex;
        align-items: center;
        gap: 10px;
        flex: 1;

        .weight-percentage {
          min-width: 50px;
          font-size: 14px;
          font-weight: 500;
          color: var(--th-color-primary);
        }
      }
    }

    .search-results {
      .result-item {
        background: var(--th-color-surface-muted);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 3px solid var(--th-color-primary);

        .result-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 10px;
          flex-wrap: wrap;

          .result-index {
            background: var(--th-color-primary);
            color: var(--th-color-surface);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
          }

          .result-title {
            font-weight: 600;
            color: #303133;
          }
        }

        .result-content {
          color: #606266;
          font-size: 14px;
          line-height: 1.6;
          background: var(--th-color-surface);
          padding: 12px;
          border-radius: 4px;
          margin-bottom: 8px;
          max-height: 200px;
          overflow-y: auto;
        }

        .result-meta {
          font-size: 12px;
          color: #909399;

          .vector-ratio {
            margin-top: 8px;
            padding: 5px 10px;
            background: var(--th-color-info-soft);
            border-radius: 4px;
            font-size: 12px;
            color: var(--th-color-primary);
            display: inline-flex;
            align-items: center;

            .el-icon {
              margin-right: 5px;
            }
          }
        }
      }
    }
  }

  .original-content {
    .original-header {
      display: flex;
      align-items: center;
      gap: 15px;

      h3 {
        margin: 0;
      }
    }

    .original-text {
      max-height: 60vh;
      overflow-y: auto;
      background: var(--th-color-surface-muted);
      padding: 15px;
      border-radius: 8px;

      pre {
        margin: 0;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-family: inherit;
        font-size: 14px;
        line-height: 1.6;
      }
    }
  }
}
</style>
