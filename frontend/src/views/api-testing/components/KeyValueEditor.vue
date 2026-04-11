<template>
  <div class="key-value-editor">
    <div class="header">
      <div class="column key-column">{{ $t('apiTesting.component.keyValueEditor.key') }}</div>
      <div class="column value-column">{{ $t('apiTesting.component.keyValueEditor.value') }}</div>
      <div class="column description-column">{{ $t('apiTesting.component.keyValueEditor.description') }}</div>
      <div class="column action-column"></div>
    </div>

    <div class="rows">
      <div
        v-for="(row, index) in rows"
        :key="index"
        class="row"
        :class="{ disabled: !row.enabled }"
      >
        <div class="column key-column">
          <el-checkbox v-model="row.enabled" @change="updateValue" />
          <el-input
            v-model="row.key"
            :placeholder="placeholderKey"
            size="small"
            @input="updateValue"
          />
        </div>

        <div class="column value-column">
          <el-input
            v-if="!showFile || row.type !== 'file'"
            v-model="row.value"
            :placeholder="placeholderValue"
            size="small"
            @input="updateValue"
            :ref="el => setInputRef(el, index)"
          >
            <template #append>
              <el-button
                size="small"
                :icon="MagicStick"
                @click="openDataFactorySelector(index)"
                :title="$t('apiTesting.component.keyValueEditor.referDataFactory')"
                class="data-factory-btn"
              />
            </template>
          </el-input>
          <el-upload
            v-else
            :auto-upload="false"
            :show-file-list="false"
            @change="(file) => handleFileChange(index, file)"
          >
            <el-button size="small">{{ $t('apiTesting.component.keyValueEditor.selectFile') }}</el-button>
          </el-upload>
          <el-tooltip :content="$t('apiTesting.component.keyValueEditor.insertDynamicVariable')" placement="top" v-if="!showFile || row.type !== 'file'">
            <el-button size="small" style="margin-left: 5px" @click="openVariableHelper(index)" class="variable-helper-btn">
              <el-icon><MagicStick /></el-icon>
            </el-button>
          </el-tooltip>
          <span v-if="row.filename" class="file-name">{{ row.filename }}</span>
        </div>

        <div class="column description-column">
          <el-input
            v-model="row.description"
            :placeholder="$t('apiTesting.component.keyValueEditor.description')"
            size="small"
            @input="updateValue"
          />
        </div>
        
        <div class="column action-column">
          <el-select
            v-if="showFile"
            v-model="row.type"
            size="small"
            style="width: 80px; margin-right: 5px;"
            @change="updateValue"
            :placeholder="$t('apiTesting.component.keyValueEditor.type')"
          >
            <el-option :label="$t('apiTesting.component.keyValueEditor.text')" value="text" />
            <el-option :label="$t('apiTesting.component.keyValueEditor.file')" value="file" />
          </el-select>
          
          <el-button
            size="small"
            type="danger"
            :icon="Delete"
            @click="removeRow(index)"
            :disabled="rows.length <= 1"
          />
        </div>
      </div>
    </div>
    
    <div class="footer">
      <el-button size="small" @click="addRow">
        <el-icon><Plus /></el-icon>
        {{ $t('apiTesting.component.keyValueEditor.addRow') }}
      </el-button>
    </div>

    <DataFactorySelector
      v-model="showDataFactorySelector"
      @select="handleDataFactorySelect"
    />

    <el-dialog
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      v-model="showVariableHelper"
      :title="$t('apiTesting.component.keyValueEditor.variableHelper')"
      :close-on-click-modal="false"
      width="900px"
    >
      <el-tabs tab-position="left" style="height: 450px">
        <el-tab-pane
          v-for="(category, index) in variableCategories"
          :key="index"
          :label="category.label"
        >
          <div style="height: 450px; overflow-y: auto; padding: 10px;">
            <el-table :data="category.variables" style="width: 100%" @row-click="insertVariable" highlight-current-row>
              <el-table-column prop="name" :label="$t('apiTesting.component.keyValueEditor.functionName')" width="150" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tag size="small">{{ row.name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" :label="$t('apiTesting.component.keyValueEditor.desc')" min-width="150" />
              <el-table-column prop="syntax" :label="$t('apiTesting.component.keyValueEditor.syntax')" min-width="200" show-overflow-tooltip />
              <el-table-column prop="example" :label="$t('apiTesting.component.keyValueEditor.example')" min-width="200" show-overflow-tooltip />
              <el-table-column :label="$t('apiTesting.component.keyValueEditor.operation')" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small">{{ $t('apiTesting.component.keyValueEditor.insert') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Delete, MagicStick } from '@element-plus/icons-vue'
import DataFactorySelector from '@/components/DataFactorySelector.vue'
import { ElMessage } from 'element-plus'
import { getVariableFunctions } from '@/api/data-factory'

const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  },
  placeholderKey: {
    type: String,
    default: 'Key'
  },
  placeholderValue: {
    type: String,
    default: 'Value'
  },
  showFile: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const rows = ref([])
const showDataFactorySelector = ref(false)
const showVariableHelper = ref(false)
const currentRowIndex = ref(0)
const variableCategories = ref([])
const loading = ref(false)
const inputRefs = ref({})

// 设置输入框ref的函数
const setInputRef = (el, index) => {
  if (el) {
    inputRefs.value[index] = el
  }
}

// 获取输入框DOM元素的辅助函数
const getInputElement = (index) => {
  const inputRef = inputRefs.value[index]
  if (!inputRef) {
    console.warn(`Input ref not found for index ${index}`)
    return null
  }
  
  // el-input组件的$el是外层div，需要找到内部的input或textarea
  const inputEl = inputRef.$el
  if (!inputEl) {
    console.warn('Input $el not found')
    return null
  }
  
  // 尝试找到input元素
  let inputElement = inputEl.querySelector('.el-input__inner')
  if (!inputElement) {
    // 如果找不到，可能是textarea
    inputElement = inputEl.querySelector('textarea')
  }
  if (!inputElement) {
    // 如果还找不到，直接尝试inputEl本身
    if (inputEl.tagName === 'INPUT' || inputEl.tagName === 'TEXTAREA') {
      inputElement = inputEl
    }
  }
  
  return inputElement
}

// 加载变量函数
const loadVariableFunctions = async () => {
  try {
    loading.value = true
    console.log('开始加载变量函数...')
    const apiResponse = await getVariableFunctions()
    // console.log('变量函数响应:', apiResponse)
    // console.log('变量函数响应.data:', apiResponse.data)
    
    // 更灵活地处理响应数据结构
    let functionsData = null
    
    // 检查不同可能的数据结构
    if (apiResponse && apiResponse.data) {
      if (Array.isArray(apiResponse.data)) {
        // 后端返回的是数组，直接使用
        functionsData = apiResponse.data
      } else if (apiResponse.data.functions) {
        // 如果data中有functions字段，使用它
        functionsData = apiResponse.data.functions
      } else if (typeof apiResponse.data === 'object') {
        // 如果data是对象但没有functions字段，假设整个对象就是按分类组织的函数
        functionsData = apiResponse.data
      }
    }
    
    if (functionsData) {
      const groupedFunctions = functionsData
      console.log('处理后的 groupedFunctions:', groupedFunctions)

      // 后端已经按分类分组了，直接转换为标签页所需的格式
      if (typeof groupedFunctions === 'object' && !Array.isArray(groupedFunctions)) {
        // 对每个分类进行国际化处理
        const localizedCategories = []
        Object.entries(groupedFunctions).forEach(([key, variables]) => {
          let localizedLabel = key
          const categoryKey = key.toLowerCase().replace(/\s+/g, '')
          const i18nKey = `apiTesting.component.keyValueEditor.categories.${categoryKey}`
          try {
            const translated = t(i18nKey)
            if (translated !== i18nKey) {
              localizedLabel = translated
            }
          } catch (e) {
            // 如果国际化失败，使用原始分类名称
          }
          localizedCategories.push({
            label: localizedLabel,
            variables
          })
        })
        variableCategories.value = localizedCategories
      } else if (Array.isArray(groupedFunctions)) {
        // 如果是数组，按分类分组
        const grouped = {}
        
        // 创建分类名称映射表
        const categoryMapping = {
          '随机数': t('apiTesting.component.keyValueEditor.categories.randomNumber'),
          '测试数据': t('apiTesting.component.keyValueEditor.categories.testData'),
          '字符串': t('apiTesting.component.keyValueEditor.categories.string'),
          '编码转换': t('apiTesting.component.keyValueEditor.categories.encodingConversion'),
          '加密': t('apiTesting.component.keyValueEditor.categories.encryption'),
          '时间日期': t('apiTesting.component.keyValueEditor.categories.datetime'),
          'Crontab': t('apiTesting.component.keyValueEditor.categories.crontab'),
          '未分类': t('apiTesting.component.keyValueEditor.categories.uncategorized')
        }
        
        groupedFunctions.forEach(func => {
          const rawCategory = func.category || '未分类'
          // 使用映射表获取正确的分类名称
          const category = categoryMapping[rawCategory] || rawCategory
          if (!grouped[category]) {
            grouped[category] = []
          }
          grouped[category].push(func)
        })
        
        // 定义固定的分类顺序 ['随机数', '测试数据', '字符串', '编码转换', '加密', '时间日期', 'Crontab', '未分类']
        const categoryOrder = [
          t('apiTesting.component.keyValueEditor.categories.randomNumber'),
          t('apiTesting.component.keyValueEditor.categories.testData'),
          t('apiTesting.component.keyValueEditor.categories.string'),
          t('apiTesting.component.keyValueEditor.categories.encodingConversion'),
          t('apiTesting.component.keyValueEditor.categories.encryption'),
          t('apiTesting.component.keyValueEditor.categories.datetime'),
          t('apiTesting.component.keyValueEditor.categories.crontab'),
          t('apiTesting.component.keyValueEditor.categories.uncategorized')
        ]
        
        // 按固定顺序构建分类列表
        const orderedCategories = []
        categoryOrder.forEach(category => {
          if (grouped[category]) {
            orderedCategories.push({
              label: category,
              variables: grouped[category]
            })
            delete grouped[category]
          }
        })
        
        // 添加剩余的分类（如果有）
        Object.entries(grouped).forEach(([label, variables]) => {
          orderedCategories.push({
            label,
            variables
          })
        })
        
        variableCategories.value = orderedCategories
      }

      console.log('最终变量分类:', variableCategories.value)
    } else {
      console.error('响应数据格式错误，无法找到函数数据')
      console.error('完整响应:', apiResponse)
      // 加载失败时使用本地变量分类数据
      useLocalVariableCategories()
    }
  } catch (error) {
    console.error('加载变量函数失败:', error)
    ElMessage.error('加载变量函数失败，使用本地数据')
    // 加载失败时使用本地变量分类数据
    useLocalVariableCategories()
  } finally {
    loading.value = false
  }
}

// 使用本地变量分类数据
const useLocalVariableCategories = () => {
  variableCategories.value = [
    {
      label: t('apiTesting.component.keyValueEditor.categories.randomNumber'),
      variables: [
        { name: 'random_int', syntax: '${random_int(min, max, count)}', desc: t('apiTesting.component.keyValueEditor.variables.randomInt'), example: '${random_int(100, 999, 1)}' },
        { name: 'random_float', syntax: '${random_float(min, max, precision, count)}', desc: t('apiTesting.component.keyValueEditor.variables.randomFloat'), example: '${random_float(0, 1, 2, 1)}' },
        { name: 'random_boolean', syntax: '${random_boolean(count)}', desc: t('apiTesting.component.keyValueEditor.variables.randomBoolean'), example: '${random_boolean(1)}' },
        { name: 'random_date', syntax: '${random_date(start_date, end_date, count, date_format)}', desc: t('apiTesting.component.keyValueEditor.variables.randomDate'), example: '${random_date(2024-01-01, 2024-12-31, 1, %Y-%m-%d)}' }
      ]
    },
    {
      label: t('apiTesting.component.keyValueEditor.categories.randomString'),
      variables: [
        { name: 'random_string', syntax: '${random_string(length, char_type, count)}', desc: t('apiTesting.component.keyValueEditor.variables.randomString'), example: '${random_string(8, all, 1)}' },
        { name: 'random_uuid', syntax: '${random_uuid(version, count)}', desc: t('apiTesting.component.keyValueEditor.variables.randomUuid'), example: '${random_uuid(4, 1)}' },
        { name: 'random_mac_address', syntax: '${random_mac_address(separator, count)}', desc: t('apiTesting.component.keyValueEditor.variables.randomMacAddress'), example: '${random_mac_address(:, 1)}' },
        { name: 'random_ip_address', syntax: '${random_ip_address(ip_version, count)}', desc: t('apiTesting.component.keyValueEditor.variables.randomIpAddress'), example: '${random_ip_address(4, 1)}' },
        { name: 'random_sequence', syntax: '${random_sequence(sequence, count, unique)}', desc: t('apiTesting.component.keyValueEditor.variables.randomSequence'), example: '${random_sequence([a,b,c], 1, false)}' }
      ]
    }
  ]
  console.log('使用本地变量分类数据:', variableCategories.value)
}

const initializeRows = () => {
  const data = props.modelValue || {}
  console.log('KeyValueEditor initializeRows called with data:', data)
  const newRows = []
  
  if (Array.isArray(data)) {
    console.log('Data is array, processing...')
    newRows.push(...data.map(item => ({
      enabled: item.enabled !== false,
      key: item.key || '',
      value: item.value || '',
      description: item.description || '',
      type: item.type || 'text',
      file: item.file || null,
      filename: item.filename || null,
      fileData: item.fileData || null,
      contentType: item.contentType || null
    })))
  } else {
    console.log('Data is object, converting...')
    Object.keys(data).forEach(key => {
      if (key && data[key] !== undefined) {
        newRows.push({
          enabled: true,
          key,
          value: data[key],
          description: '',
          type: 'text',
          file: null,
          filename: null,
          fileData: null,
          contentType: null
        })
      }
    })
  }
  
  if (newRows.length === 0) {
    newRows.push({
      enabled: true,
      key: '',
      value: '',
      description: '',
      type: 'text',
      file: null,
      filename: null,
      fileData: null,
      contentType: null
    })
  }
  
  console.log('KeyValueEditor final rows:', newRows)
  rows.value = newRows
}

const updateValue = () => {
  const result = rows.value.filter(row => row.key || row.value || row.description).map(row => {
    const item = {
      key: row.key || '',
      value: row.value || '',
      description: row.description || '',
      enabled: row.enabled !== false,
      type: row.type || 'text'
    }
    
    if (row.type === 'file' && row.fileData) {
      item.filename = row.filename || row.value
      item.fileData = row.fileData
      item.contentType = row.contentType || 'application/octet-stream'
    }
    
    return item
  })
  
  console.log('KeyValueEditor updateValue result (full format):', result)
  emit('update:modelValue', result)
  
  const lastRow = rows.value[rows.value.length - 1]
  if (lastRow.key || lastRow.value) {
    addRow()
  }
}

const addRow = () => {
  rows.value.push({
    enabled: true,
    key: '',
    value: '',
    description: '',
    type: 'text',
    file: null,
    filename: null,
    fileData: null,
    contentType: null
  })
}

const removeRow = (index) => {
  if (rows.value.length > 1) {
    rows.value.splice(index, 1)
    updateValue()
  }
}

const handleFileChange = async (index, file) => {
  rows.value[index].file = file.raw
  rows.value[index].filename = file.name
  rows.value[index].value = file.name
  
  const reader = new FileReader()
  reader.onload = (e) => {
    const base64 = e.target.result.split(',')[1]
    rows.value[index].fileData = base64
    rows.value[index].contentType = file.raw.type || 'application/octet-stream'
    updateValue()
  }
  reader.readAsDataURL(file.raw)
}

const openDataFactorySelector = (index) => {
  currentRowIndex.value = index
  showDataFactorySelector.value = true
}

const handleDataFactorySelect = (record) => {
  const rowIndex = currentRowIndex.value
  if (record && record.output_data) {
    let valueToSet = ''

    if (typeof record.output_data === 'string') {
      valueToSet = record.output_data
    } else if (record.output_data.result) {
      valueToSet = record.output_data.result
    } else if (record.output_data.output_data) {
      valueToSet = record.output_data.output_data
    } else if (typeof record.output_data === 'object') {
      const possibleResultFields = ['result', 'value', 'data', 'output', 'content']
      let foundResult = false
      for (const field of possibleResultFields) {
        if (record.output_data[field] !== undefined) {
          valueToSet = record.output_data[field]
          foundResult = true
          break
        }
      }
      if (!foundResult) {
        valueToSet = JSON.stringify(record.output_data)
      }
    } else {
      valueToSet = JSON.stringify(record.output_data)
    }

    if (typeof valueToSet !== 'string') {
      valueToSet = JSON.stringify(valueToSet)
    }

    // 使用ref获取输入框元素
    const inputElement = getInputElement(rowIndex)
    
    if (inputElement) {
      // 确保输入框有焦点
      inputElement.focus()
      
      // 获取光标位置
      const cursorPosition = inputElement.selectionStart || inputElement.selectionEnd || 0
      const currentValue = rows.value[rowIndex].value || ''
      
      console.log(`Cursor position: ${cursorPosition}, Current value: "${currentValue}"`)
      
      // 在光标位置插入数据
      const newValue = currentValue.substring(0, cursorPosition) + valueToSet + currentValue.substring(cursorPosition)
      rows.value[rowIndex].value = newValue
      
      // 更新光标位置
      const newCursorPosition = cursorPosition + valueToSet.length
      setTimeout(() => {
        inputElement.focus()
        inputElement.setSelectionRange(newCursorPosition, newCursorPosition)
        console.log(`New cursor position: ${newCursorPosition}`)
      }, 10)
    } else {
      console.warn('Input element not found, appending to end')
      const currentValue = rows.value[rowIndex].value || ''
      if (!currentValue) {
        rows.value[rowIndex].value = valueToSet
      } else {
        rows.value[rowIndex].value = currentValue + valueToSet
      }
    }

    rows.value[rowIndex].description = t('apiTesting.component.keyValueEditor.fromDataFactory', { name: record.tool_name })
    ElMessage.success(t('apiTesting.component.keyValueEditor.dataFactoryInserted', { name: record.tool_name }))
    updateValue()
  }
  showDataFactorySelector.value = false
}

const openVariableHelper = (index) => {
  currentRowIndex.value = index
  showVariableHelper.value = true
}

const insertVariable = (variable) => {
  const rowIndex = currentRowIndex.value
  const example = variable.example

  // 使用ref获取输入框元素
  const inputElement = getInputElement(rowIndex)
  
  if (inputElement) {
    // 确保输入框有焦点
    inputElement.focus()
    
    // 获取光标位置
    const cursorPosition = inputElement.selectionStart || inputElement.selectionEnd || 0
    const currentValue = rows.value[rowIndex].value || ''
    
    console.log(`Cursor position: ${cursorPosition}, Current value: "${currentValue}"`)
    
    // 在光标位置插入变量
    const newValue = currentValue.substring(0, cursorPosition) + example + currentValue.substring(cursorPosition)
    rows.value[rowIndex].value = newValue
    
    // 更新光标位置
    const newCursorPosition = cursorPosition + example.length
    setTimeout(() => {
      inputElement.focus()
      inputElement.setSelectionRange(newCursorPosition, newCursorPosition)
      console.log(`New cursor position: ${newCursorPosition}`)
    }, 10)
  } else {
    // 回退到原来的逻辑（追加到末尾）
    console.warn('Input element not found, appending to end')
    const currentValue = rows.value[rowIndex].value || ''
    if (!currentValue) {
      rows.value[rowIndex].value = example
    } else {
      rows.value[rowIndex].value = currentValue + example
    }
  }

  ElMessage.success(t('apiTesting.component.keyValueEditor.variableInserted', { name: variable.name }))
  showVariableHelper.value = false
  updateValue()
}

// 监听props.modelValue变化
watch(
  () => props.modelValue,
  () => {
    initializeRows()
  },
  { immediate: true }
)

// 生命周期钩子
onMounted(async () => {
  await loadVariableFunctions()
})

// 暴露rows供父组件访问
defineExpose({
  rows
})
</script>

<style scoped>
.key-value-editor {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: white;
}

.header {
  display: flex;
  background: var(--th-color-surface-muted);
  border-bottom: 1px solid #e4e7ed;
  padding: 8px;
  font-weight: 500;
  font-size: 12px;
  color: #606266;
}

.rows {
  max-height: 300px;
  overflow-y: auto;
}

.row {
  display: flex;
  border-bottom: 1px solid var(--th-color-surface-muted);
  padding: 8px;
  min-height: 40px;
  align-items: center;
}

.row:hover {
  background: #fafbfc;
}

.row.disabled {
  opacity: 0.6;
}

.column {
  display: flex;
  align-items: center;
  gap: 5px;
}

.key-column {
  width: 25%;
  min-width: 150px;
}

.value-column {
  width: 25%;
  min-width: 200px;
}

.description-column {
  width: 30%;
  min-width: 120px;
}

.action-column {
  width: 20%;
  min-width: 120px;
  justify-content: flex-end;
  gap: 5px;
}

.data-factory-btn {
  background-color: var(--th-color-primary) !important;
  border-color: var(--th-color-primary) !important;
  color: white !important;
}

.data-factory-btn:hover {
  background-color: var(--th-color-primary) !important;
  border-color: var(--th-color-primary) !important;
}

.variable-helper-btn {
  background-color: var(--th-color-success);
  border-color: var(--th-color-success);
  color: white;
}

.variable-helper-btn:hover {
  background-color: var(--th-color-success);
  border-color: var(--th-color-success);
}

.file-name {
  font-size: 12px;
  color: #606266;
  margin-left: 8px;
}

.footer {
  padding: 8px;
  border-top: 1px solid var(--th-color-surface-muted);
  background: #fafbfc;
}

/* 变量助手弹窗样式优化 */
:deep(.el-dialog__body) {
  padding: 0;
}

:deep(.el-tabs__content) {
  height: 100%;
}

:deep(.el-tab-pane) {
  height: 100%;
}

:deep(.el-table) {
  font-size: 13px;
}

:deep(.el-table th) {
  background-color: var(--th-color-surface-muted);
  font-weight: 600;
  color: #303133;
}

:deep(.el-table td) {
  padding: 12px 0;
}

:deep(.el-table .cell) {
  padding: 0 10px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: var(--th-color-surface-muted);
}

:deep(.el-table__row.current-row) {
  background-color: var(--th-color-info-soft);
}
</style>