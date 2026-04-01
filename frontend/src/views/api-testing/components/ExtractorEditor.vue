<template>
  <div class="extractor-editor">
    <div class="extractor-header">
      <span class="title">{{ $t('apiTesting.extractor.title') }}</span>
      <el-button type="primary" size="small" @click="addExtractor">
        <el-icon><Plus /></el-icon> {{ $t('apiTesting.extractor.add') }}
      </el-button>
    </div>

    <div v-if="!localExtractors.length" class="extractor-empty">
      <el-empty :description="$t('apiTesting.extractor.empty')" :image-size="60" />
    </div>

    <div v-else class="extractor-list">
      <div v-for="(ext, index) in localExtractors" :key="index" class="extractor-item">
        <div class="extractor-row">
          <el-input
            v-model="ext.variable_name"
            :placeholder="$t('apiTesting.extractor.variableName')"
            size="small"
            class="var-name-input"
            @input="emitChange"
          >
            <template #prepend>
              <span class="var-prefix" v-text="'{{'"></span>
            </template>
            <template #append>
              <span class="var-suffix" v-text="'}}'"></span>
            </template>
          </el-input>

          <el-select v-model="ext.source" size="small" class="source-select" @change="emitChange">
            <el-option value="body" :label="$t('apiTesting.extractor.sourceBody')" />
            <el-option value="header" :label="$t('apiTesting.extractor.sourceHeader')" />
            <el-option value="cookie" label="Cookie" />
            <el-option value="status_code" :label="$t('apiTesting.extractor.sourceStatus')" />
          </el-select>

          <el-select
            v-if="ext.source === 'body'"
            v-model="ext.extract_type"
            size="small"
            class="type-select"
            @change="emitChange"
          >
            <el-option value="json_path" label="JSONPath" />
            <el-option value="regex" :label="$t('apiTesting.extractor.regex')" />
          </el-select>

          <el-button type="danger" size="small" :icon="Delete" circle @click="removeExtractor(index)" />
        </div>

        <div class="extractor-row" v-if="ext.source !== 'status_code'">
          <el-input
            v-model="ext.expression"
            :placeholder="getExpressionPlaceholder(ext)"
            size="small"
            class="expression-input"
            @input="emitChange"
          />
          <el-input
            v-model="ext.default_value"
            :placeholder="$t('apiTesting.extractor.defaultValue')"
            size="small"
            class="default-input"
            @input="emitChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const localExtractors = ref([])

watch(() => props.modelValue, (val) => {
  localExtractors.value = JSON.parse(JSON.stringify(val || []))
}, { immediate: true, deep: true })

function addExtractor() {
  localExtractors.value.push({
    variable_name: '',
    source: 'body',
    extract_type: 'json_path',
    expression: '',
    default_value: '',
  })
  emitChange()
}

function removeExtractor(index) {
  localExtractors.value.splice(index, 1)
  emitChange()
}

function emitChange() {
  emit('update:modelValue', JSON.parse(JSON.stringify(localExtractors.value)))
}

function getExpressionPlaceholder(ext) {
  if (ext.source === 'body') {
    return ext.extract_type === 'json_path' ? '$.data.token' : '(token|access_token)[:=]\\s*"?([^"&\\s]+)'
  }
  if (ext.source === 'header') return 'Authorization'
  if (ext.source === 'cookie') return 'session_id'
  return ''
}
</script>

<style scoped>
.extractor-editor {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
  background: #fafbfc;
}

.extractor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.extractor-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.extractor-item {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.extractor-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.var-name-input {
  flex: 1;
  max-width: 220px;
}

.var-prefix, .var-suffix {
  color: #409eff;
  font-weight: bold;
  font-family: monospace;
}

.source-select {
  width: 120px;
}

.type-select {
  width: 120px;
}

.expression-input {
  flex: 1;
}

.default-input {
  width: 150px;
}

.extractor-empty {
  padding: 10px 0;
}
</style>
