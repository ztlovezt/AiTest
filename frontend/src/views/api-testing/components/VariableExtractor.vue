<template>
  <div class="variable-extractor">
    <div class="extractor-header">
      <span class="title">{{ $t('apiTesting.interface.extractVariablesConfig.title') || '变量提取' }}</span>
      <div class="extractor-actions">
        <slot name="actions" />
        <el-button type="primary" size="small" @click="addExtractor">
          <el-icon><Plus /></el-icon>
          {{ $t('apiTesting.common.add') || '添加' }}
        </el-button>
      </div>
    </div>
    
    <div class="extractor-list" v-if="localExtractors && localExtractors.length > 0">
      <div 
        v-for="(extractor, index) in localExtractors" 
        :key="index" 
        class="extractor-item"
      >
        <div class="extractor-row">
          <el-input
            :model-value="extractor.name"
            @update:model-value="updateField(index, 'name', $event)"
            :placeholder="$t('apiTesting.interface.extractVariablesConfig.variableName') || '变量名'"
            size="small"
            class="var-name-input"
          />
          
          <el-select
            :model-value="extractor.source"
            @update:model-value="updateField(index, 'source', $event)"
            :placeholder="$t('apiTesting.interface.extractVariablesConfig.source') || '来源'"
            size="small"
            class="source-select"
          >
            <el-option :label="$t('apiTesting.interface.extractVariablesConfig.sourceBody')" value="body" />
            <el-option :label="$t('apiTesting.interface.extractVariablesConfig.sourceHeader')" value="header" />
            <el-option :label="$t('apiTesting.interface.extractVariablesConfig.sourceStatusCode')" value="status_code" />
          </el-select>
          
          <el-select
            :model-value="extractor.type"
            @update:model-value="updateField(index, 'type', $event)"
            :placeholder="$t('apiTesting.interface.extractVariablesConfig.type') || '类型'"
            size="small"
            class="type-select"
            :disabled="extractor.source === 'status_code'"
          >
            <el-option :label="$t('apiTesting.interface.extractVariablesConfig.typeJsonPath')" value="json_path" />
            <el-option :label="$t('apiTesting.interface.extractVariablesConfig.typeRegex')" value="regex" />
          </el-select>
        </div>
        
        <div class="extractor-row">
          <el-input
            :model-value="extractor.expression"
            @update:model-value="updateField(index, 'expression', $event)"
            :placeholder="getExpressionPlaceholder(extractor)"
            size="small"
            class="expression-input"
            :disabled="extractor.source === 'status_code'"
          />
          
          <el-input
            :model-value="extractor.default"
            @update:model-value="updateField(index, 'default', $event)"
            :placeholder="$t('apiTesting.interface.extractVariablesConfig.defaultValue') || '默认值'"
            size="small"
            class="default-input"
          />
          
          <el-button
            type="danger"
            size="small"
            @click="removeExtractor(index)"
            :icon="Delete"
            circle
          />
        </div>
        
        <div class="extractor-example" v-if="extractor.type === 'json_path'">
          <span class="example-label">{{ $t('apiTesting.interface.extractVariablesConfig.example') }}:</span>
          <code>$.data.token</code>
          <code>$.items[0].id</code>
        </div>
        <div class="extractor-example" v-else-if="extractor.type === 'regex'">
          <span class="example-label">{{ $t('apiTesting.interface.extractVariablesConfig.example') }}:</span>
          <code>"token":"([^"]+)"</code>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-hint">
      <el-empty :description="$t('apiTesting.interface.extractVariablesConfig.noExtractors') || '暂无变量提取规则'" :image-size="60" />
    </div>
    
    <div class="extractor-help">
      <el-collapse>
        <el-collapse-item :title="$t('apiTesting.interface.extractVariablesConfig.help') || '使用说明'" name="help">
          <div class="help-content">
            <h4>{{ $t('apiTesting.interface.extractVariablesConfig.helpJsonPathTitle') }}</h4>
            <p>{{ $t('apiTesting.interface.extractVariablesConfig.helpJsonPathDesc') }}</p>
            <ul>
              <li><code>$.data.token</code> - {{ $t('apiTesting.interface.extractVariablesConfig.helpJsonPathExample1') }}</li>
              <li><code>$.items[0].id</code> - {{ $t('apiTesting.interface.extractVariablesConfig.helpJsonPathExample2') }}</li>
              <li><code>$.users[*].name</code> - {{ $t('apiTesting.interface.extractVariablesConfig.helpJsonPathExample3') }}</li>
            </ul>
            
            <h4>{{ $t('apiTesting.interface.extractVariablesConfig.helpRegexTitle') }}</h4>
            <p>{{ $t('apiTesting.interface.extractVariablesConfig.helpRegexDesc') }}</p>
            <ul>
              <li><code>"token":"([^"]+)"</code> - {{ $t('apiTesting.interface.extractVariablesConfig.helpRegexExample1') }}</li>
              <li><code>userId=(\d+)</code> - {{ $t('apiTesting.interface.extractVariablesConfig.helpRegexExample2') }}</li>
            </ul>
            
            <h4>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageTitle') }}</h4>
            <p>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageDesc') }}</p>
            <ul>
              <li><strong>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageExampleUrl') }}:</strong> <code>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageExampleUrlContent') }}</code></li>
              <li><strong>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageExampleHeader') }}:</strong> <code>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageExampleHeaderContent') }}</code></li>
              <li><strong>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageExampleBody') }}:</strong> <code>{{ $t('apiTesting.interface.extractVariablesConfig.helpUsageExampleBodyContent') }}</code></li>
            </ul>

            <div class="help-workflow-example">
              <h4>{{ $t('apiTesting.interface.extractVariablesConfig.helpWorkflowTitle') }}</h4>
              <p>{{ $t('apiTesting.interface.extractVariablesConfig.helpWorkflowDesc') }}</p>
              <ol class="workflow-steps">
                <li>{{ $t('apiTesting.interface.extractVariablesConfig.helpWorkflowStep1') }}</li>
                <li>{{ $t('apiTesting.interface.extractVariablesConfig.helpWorkflowStep2') }}</li>
                <li>{{ $t('apiTesting.interface.extractVariablesConfig.helpWorkflowStep3') }}</li>
              </ol>
            </div>

            <div class="help-note">
              <p><strong>{{ $t('apiTesting.interface.extractVariablesConfig.helpNoteImportant') }}:</strong> {{ $t('apiTesting.interface.extractVariablesConfig.helpNoteContent') }}</p>
            </div>

            <div class="help-dynamic-func">
              <h4>{{ $t('apiTesting.interface.extractVariablesConfig.helpDynamicFuncTitle') }}</h4>
              <p>{{ $t('apiTesting.interface.extractVariablesConfig.helpDynamicFuncDesc') }}</p>
              <code class="dynamic-func-example">{{ $t('apiTesting.interface.extractVariablesConfig.helpDynamicFuncExample') }}</code>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { Plus, Delete } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { computed, ref, watch } from 'vue'

const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const localExtractors = ref([])

watch(() => props.modelValue, (newVal) => {
  localExtractors.value = JSON.parse(JSON.stringify(newVal || []))
}, { immediate: true, deep: true })

const updateField = (index, field, value) => {
  localExtractors.value[index][field] = value
  emit('update:modelValue', JSON.parse(JSON.stringify(localExtractors.value)))
}

const addExtractor = () => {
  localExtractors.value.push({
    name: '',
    source: 'body',
    type: 'json_path',
    expression: '',
    default: ''
  })
  emit('update:modelValue', JSON.parse(JSON.stringify(localExtractors.value)))
}

const removeExtractor = (index) => {
  localExtractors.value.splice(index, 1)
  emit('update:modelValue', JSON.parse(JSON.stringify(localExtractors.value)))
}

const getExpressionPlaceholder = (extractor) => {
  if (extractor.source === 'status_code') {
    return t('apiTesting.interface.extractVariablesConfig.placeholderAutoExtract')
  }
  if (extractor.source === 'header') {
    return t('apiTesting.interface.extractVariablesConfig.placeholderHeaderName')
  }
  if (extractor.type === 'json_path') {
    return t('apiTesting.interface.extractVariablesConfig.placeholderJsonPath')
  }
  if (extractor.type === 'regex') {
    return t('apiTesting.interface.extractVariablesConfig.placeholderRegex')
  }
  return ''
}
</script>

<style scoped>
.variable-extractor {
  padding: 10px;
}

.extractor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.extractor-header .title {
  font-weight: 600;
  font-size: 14px;
}

.extractor-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.extractor-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.extractor-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #e9ecef;
}

.extractor-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.extractor-row:last-child {
  margin-bottom: 0;
}

.var-name-input {
  width: 150px;
}

.source-select {
  width: 140px;
}
.type-select {
  width: 120px;
}
.expression-input {
  flex: 1;
}
.default-input {
  width: 120px;
}
.extractor-example {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #dee2e6;
  font-size: 12px;
  color: #6c757d;
}

.extractor-example .example-label {
  margin-right: 8px;
}

.extractor-example code {
  background: #e9ecef;
  padding: 2px 6px;
  border-radius: 4px;
  margin-right: 8px;
  font-size: 11px;
}

.empty-hint {
  padding: 20px 0;
}

.extractor-help {
  margin-top: 15px;
}

/* 确保 el-collapse 内容区域可滚动，不被父容器截断 */
.extractor-help :deep(.el-collapse-item__wrap) {
  overflow: visible;
}

.extractor-help :deep(.el-collapse-item__content) {
  overflow: visible;
}

/* 兜底：如果父容器仍然限制高度，help-content 自身允许溢出可见 */
.help-content {
  font-size: 13px;
  line-height: 1.6;
  padding: 12px 16px;
  max-height: none;
  overflow: visible;
}

.help-content h4 {
  margin: 10px 0 5px;
  color: #303133;
}

.help-content ul {
  padding-left: 20px;
  margin: 5px 0;
}

.help-content li {
  margin: 3px 0;
}

.help-content code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  color: #409eff;
}

.help-content .help-workflow-example {
  margin-top: 12px;
  padding: 12px;
  background: #f0f9eb;
  border-radius: 6px;
  border-left: 3px solid #67c23a;
}

.help-content .workflow-steps {
  padding-left: 20px;
  margin: 5px 0;
}

.help-content .workflow-steps li {
  margin: 4px 0;
  line-height: 1.7;
}

.help-content .help-note {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fdf6ec;
  border-radius: 6px;
  border-left: 3px solid #e6a23c;
}

.help-content .help-note p {
  margin: 0;
  font-size: 12.5px;
  color: #e6a23c;
  font-weight: 500;
}

.help-content .help-dynamic-func {
  margin-top: 12px;
  padding: 10px 14px;
  background: #ecf5ff;
  border-radius: 6px;
  border-left: 3px solid #409eff;
}

.help-content .dynamic-func-example {
  display: block;
  margin-top: 8px;
  padding: 8px 12px;
  background: #fff;
  border-radius: 4px;
  word-break: break-all;
  font-size: 12px;
}
</style>
