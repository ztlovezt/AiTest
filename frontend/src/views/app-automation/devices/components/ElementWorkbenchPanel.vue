<template>
  <div class="element-workbench">
    <div class="workbench-header">
      <div>
        <h4>元素创建</h4>
        <p>基于当前连接设备截图创建图片、坐标或区域元素。</p>
      </div>
      <div class="header-actions">
        <el-button :loading="capturing" @click="captureScreen">重新截图</el-button>
        <el-button @click="resetWorkspace">重置</el-button>
      </div>
    </div>

    <div class="workbench-body">
      <div class="capture-pane">
        <div v-if="capturedImage" ref="imageWrapper" class="image-wrapper" @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp" @mouseleave="handleMouseUp">
          <img ref="imageRef" :src="capturedImage" class="capture-image" @load="handleImageLoad" />
          <div v-if="selection" class="selection-box" :style="selectionStyle" @mousedown.stop="handleSelectionMouseDown">
            <button class="selection-close" @click.stop="clearSelection">×</button>
            <div class="selection-info">{{ selectionInfo }}</div>
            <span
              v-for="handle in resizeHandles"
              :key="handle"
              class="resize-handle"
              :class="`resize-handle-${handle}`"
              @mousedown.stop="handleResizeStart(handle, $event)"
            ></span>
          </div>
        </div>
        <el-empty v-else description="请先获取当前设备截图" />
      </div>

      <div class="form-pane">
        <el-form label-width="100px" size="small">
          <el-form-item label="设备">
            <el-input :model-value="deviceLabel" disabled />
          </el-form-item>

          <el-form-item label="元素名称" required>
            <el-input v-model="formData.name" placeholder="例如：登录按钮" />
          </el-form-item>

          <el-form-item label="所属项目">
            <el-select v-model="formData.project" clearable filterable placeholder="请选择项目" style="width: 100%">
              <el-option v-for="project in projectList" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>

          <el-form-item label="元素类型" required>
            <el-radio-group v-model="formData.element_type">
              <el-radio value="image">图片元素</el-radio>
              <el-radio value="pos">坐标元素</el-radio>
              <el-radio value="region">区域元素</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="标签">
            <el-select v-model="formData.tags" multiple filterable allow-create default-first-option placeholder="输入标签后回车" style="width: 100%" />
          </el-form-item>

          <template v-if="formData.element_type === 'image'">
            <el-divider content-position="left">图片配置</el-divider>

            <el-form-item label="图片分类" required>
              <div class="inline-row">
                <el-select v-model="formData.image_category" filterable placeholder="选择分类" style="flex: 1">
                  <el-option v-for="cat in imageCategories" :key="cat" :label="cat" :value="cat" />
                </el-select>
                <el-button @click="createCategoryVisible = true">新建分类</el-button>
              </div>
            </el-form-item>

            <el-form-item label="模板文件名" required>
              <el-input v-model="templateFileName" placeholder="例如：login_btn.png" />
            </el-form-item>

            <el-form-item label="保存路径">
              <el-input :model-value="imageSavePath" disabled />
            </el-form-item>

            <el-form-item label="匹配阈值">
              <el-slider v-model="formData.config.image_threshold" :min="0.5" :max="1" :step="0.05" show-input />
            </el-form-item>

            <el-form-item label="颜色模式">
              <el-switch v-model="formData.config.rgb" active-text="RGB彩色" inactive-text="灰度" />
            </el-form-item>
          </template>

          <template v-if="formData.element_type === 'pos'">
            <el-divider content-position="left">坐标配置</el-divider>
            <el-form-item label="Pos 值">
              <el-input :model-value="posValue" readonly placeholder="在截图上单击设置坐标" />
            </el-form-item>
          </template>

          <template v-if="formData.element_type === 'region'">
            <el-divider content-position="left">区域配置</el-divider>
            <el-form-item label="Region 值">
              <el-input :model-value="regionValue" readonly placeholder="在截图上拖拽框选区域" />
            </el-form-item>
          </template>

          <div class="form-actions">
            <el-button type="primary" :loading="submitting" :disabled="!canSave" @click="handleSubmit(false)">保存元素</el-button>
            <el-button :loading="submitting" :disabled="!canSave" @click="handleSubmit(true)">保存后继续</el-button>
          </div>
        </el-form>
      </div>
    </div>

    <el-dialog v-model="createCategoryVisible" title="新建分类" width="400px">
      <el-form>
        <el-form-item label="分类名称">
          <el-input v-model="newCategoryName" placeholder="请输入分类名称" @keyup.enter="handleCreateCategory" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createCategoryVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingCategory" @click="handleCreateCategory">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  captureDeviceScreenshot,
  createAppElement,
  createAppImageCategory,
  getAppImageCategories,
  getAppProjects,
  uploadAppElementImage,
} from '@/api/app-automation'

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
  deviceName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['created', 'operation'])

const imageRef = ref(null)
const imageWrapper = ref(null)
const capturing = ref(false)
const submitting = ref(false)
const capturedImage = ref('')
const projectList = ref([])
const imageCategories = ref(['common'])
const createCategoryVisible = ref(false)
const newCategoryName = ref('')
const creatingCategory = ref(false)

const selection = ref(null)
const selecting = ref(false)
const startPoint = ref(null)
const action = ref(null)
const resizeHandle = ref(null)
const moveOffset = ref(null)
const imageSize = ref({ width: 0, height: 0 })
const resizeHandles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

const formData = reactive({
  name: '',
  element_type: 'image',
  image_category: 'common',
  project: null,
  tags: [],
  config: {
    image_threshold: 0.7,
    rgb: false,
    x: null,
    y: null,
    x1: null,
    y1: null,
    x2: null,
    y2: null,
    image_path: '',
    file_hash: '',
  },
})

const templateFileName = ref('')

const deviceLabel = computed(() => props.deviceName || props.deviceId)

const logOperation = (message, level = 'info', extra = null) => {
  emit('operation', {
    source: 'elements',
    level,
    message,
    extra,
    timestamp: Date.now(),
  })
}

const selectionStyle = computed(() => {
  if (!selection.value) {
    return {}
  }
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  const x2 = Math.max(selection.value.x1, selection.value.x2)
  const y2 = Math.max(selection.value.y1, selection.value.y2)
  return {
    left: `${x1}px`,
    top: `${y1}px`,
    width: `${x2 - x1}px`,
    height: `${y2 - y1}px`,
  }
})

const selectionInfo = computed(() => {
  if (!selection.value) {
    return ''
  }
  const width = Math.abs(selection.value.x2 - selection.value.x1)
  const height = Math.abs(selection.value.y2 - selection.value.y1)
  return `${Math.round(width)} × ${Math.round(height)}`
})

const imageSavePath = computed(() => {
  const imageCategory = formData.image_category || 'common'
  const filename = templateFileName.value || 'template.png'
  return `Template/${imageCategory}/${filename}`
})

const posValue = computed(() => {
  if (formData.config.x === null || formData.config.y === null) {
    return ''
  }
  return `${formData.config.x},${formData.config.y}`
})

const regionValue = computed(() => {
  if ([formData.config.x1, formData.config.y1, formData.config.x2, formData.config.y2].some((item) => item === null || item === undefined)) {
    return ''
  }
  return `${formData.config.x1},${formData.config.y1},${formData.config.x2},${formData.config.y2}`
})

const hasPos = computed(() => Number.isFinite(formData.config.x) && Number.isFinite(formData.config.y))
const hasRegion = computed(() => [formData.config.x1, formData.config.y1, formData.config.x2, formData.config.y2].every((item) => Number.isFinite(item)))

const canSave = computed(() => {
  if (!formData.name.trim()) {
    return false
  }
  if (formData.element_type === 'image') {
    return Boolean(capturedImage.value && templateFileName.value.trim() && formData.image_category)
  }
  if (formData.element_type === 'pos') {
    return hasPos.value
  }
  if (formData.element_type === 'region') {
    return hasRegion.value
  }
  return false
})

const resetFormOnly = () => {
  formData.name = ''
  formData.element_type = 'image'
  formData.image_category = 'common'
  formData.project = null
  formData.tags = []
  formData.config = {
    image_threshold: 0.7,
    rgb: false,
    x: null,
    y: null,
    x1: null,
    y1: null,
    x2: null,
    y2: null,
    image_path: '',
    file_hash: '',
  }
  templateFileName.value = ''
  clearSelection()
}

const resetWorkspace = () => {
  resetFormOnly()
  capturedImage.value = ''
}

const loadProjects = async () => {
  try {
    const response = await getAppProjects({ page: 1, page_size: 1000 })
    const payload = response.data?.success !== undefined ? response.data?.data : response.data
    projectList.value = payload?.results || payload || []
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
}

const loadImageCategories = async () => {
  try {
    const response = await getAppImageCategories()
    if (response.data.success && Array.isArray(response.data.data)) {
      imageCategories.value = response.data.data.map((item) => item.name || item)
    }
  } catch (error) {
    console.error('Failed to load image categories:', error)
    imageCategories.value = ['common']
  }
}

const captureScreen = async () => {
  capturing.value = true
  try {
    const response = await captureDeviceScreenshot(props.deviceId)
    const result = response.data
    if (!result.success || !result.data?.content) {
      ElMessage.error(result.msg || '截图失败')
      logOperation('元素创建区截图失败', 'error', result)
      return
    }
    capturedImage.value = result.data.content
    clearSelection()
    ElMessage.success('截图成功')
    logOperation('元素创建区截图成功', 'success')
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || error.message || '截图失败')
    logOperation('元素创建区截图失败', 'error', error?.response?.data || error?.message)
  } finally {
    capturing.value = false
  }
}

const handleImageLoad = () => {
  if (!imageRef.value) {
    return
  }
  imageSize.value = {
    width: imageRef.value.naturalWidth || imageRef.value.width,
    height: imageRef.value.naturalHeight || imageRef.value.height,
  }
}

const getImageRect = () => {
  if (!imageWrapper.value || !imageRef.value) {
    return null
  }
  return imageWrapper.value.getBoundingClientRect()
}

const getSelectionInNatural = () => {
  if (!selection.value || !imageRef.value) {
    return null
  }
  const scaleX = imageSize.value.width / imageRef.value.clientWidth
  const scaleY = imageSize.value.height / imageRef.value.clientHeight
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  const x2 = Math.max(selection.value.x1, selection.value.x2)
  const y2 = Math.max(selection.value.y1, selection.value.y2)
  return {
    x1: Math.round(x1 * scaleX),
    y1: Math.round(y1 * scaleY),
    x2: Math.round(x2 * scaleX),
    y2: Math.round(y2 * scaleY),
  }
}

const updateSelectionValues = () => {
  const natural = getSelectionInNatural()
  if (!natural) {
    return
  }
  formData.config.x1 = natural.x1
  formData.config.y1 = natural.y1
  formData.config.x2 = natural.x2
  formData.config.y2 = natural.y2
}

const handleMouseDown = (event) => {
  if (!capturedImage.value || !imageWrapper.value) {
    return
  }
  const rect = getImageRect()
  if (!rect) {
    return
  }
  const x = Math.max(0, Math.min(event.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(event.clientY - rect.top, rect.height))
  selecting.value = true
  startPoint.value = { x, y }
  action.value = 'create'
  selection.value = { x1: x, y1: y, x2: x, y2: y }
  event.preventDefault()
}

const handleMouseMove = (event) => {
  if (!selecting.value || !selection.value) {
    return
  }
  const rect = getImageRect()
  if (!rect) {
    return
  }
  const x = Math.max(0, Math.min(event.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(event.clientY - rect.top, rect.height))

  if (action.value === 'create' && startPoint.value) {
    selection.value = { x1: startPoint.value.x, y1: startPoint.value.y, x2: x, y2: y }
  } else if (action.value === 'move' && moveOffset.value) {
    const width = Math.abs(selection.value.x2 - selection.value.x1)
    const height = Math.abs(selection.value.y2 - selection.value.y1)
    const left = Math.max(0, Math.min(x - moveOffset.value.x, rect.width - width))
    const top = Math.max(0, Math.min(y - moveOffset.value.y, rect.height - height))
    selection.value = { x1: left, y1: top, x2: left + width, y2: top + height }
  } else if (action.value === 'resize' && resizeHandle.value) {
    selection.value = resizeSelection(selection.value, resizeHandle.value, x, y, rect)
  }
  event.preventDefault()
}

const handleMouseUp = () => {
  if (!selecting.value) {
    return
  }

  if (action.value === 'create' && selection.value) {
    const width = Math.abs(selection.value.x2 - selection.value.x1)
    const height = Math.abs(selection.value.y2 - selection.value.y1)
    if (width < 5 && height < 5) {
      if (imageRef.value) {
        const scaleX = imageSize.value.width / imageRef.value.clientWidth
        const scaleY = imageSize.value.height / imageRef.value.clientHeight
        formData.config.x = Math.round(selection.value.x1 * scaleX)
        formData.config.y = Math.round(selection.value.y1 * scaleY)
      }
      selection.value = null
    } else {
      updateSelectionValues()
    }
  } else if (action.value === 'move' || action.value === 'resize') {
    updateSelectionValues()
  }

  selecting.value = false
  startPoint.value = null
  action.value = null
  resizeHandle.value = null
  moveOffset.value = null
}

const handleSelectionMouseDown = (event) => {
  const rect = getImageRect()
  if (!rect || !selection.value) {
    return
  }
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const x1 = Math.min(selection.value.x1, selection.value.x2)
  const y1 = Math.min(selection.value.y1, selection.value.y2)
  selecting.value = true
  action.value = 'move'
  moveOffset.value = { x: x - x1, y: y - y1 }
  event.preventDefault()
}

const handleResizeStart = (handle, event) => {
  selecting.value = true
  action.value = 'resize'
  resizeHandle.value = handle
  event.preventDefault()
}

const resizeSelection = (sel, handle, x, y, rect) => {
  let { x1, y1, x2, y2 } = sel
  const clampX = Math.max(0, Math.min(x, rect.width))
  const clampY = Math.max(0, Math.min(y, rect.height))
  if (handle.includes('n')) y1 = clampY
  if (handle.includes('s')) y2 = clampY
  if (handle.includes('w')) x1 = clampX
  if (handle.includes('e')) x2 = clampX
  return { x1, y1, x2, y2 }
}

const clearSelection = () => {
  selection.value = null
  action.value = null
  resizeHandle.value = null
  moveOffset.value = null
  formData.config.x1 = null
  formData.config.y1 = null
  formData.config.x2 = null
  formData.config.y2 = null
}

const base64ToBlob = (base64, type = 'image/png') => {
  const byteCharacters = atob(base64)
  const byteNumbers = new Array(byteCharacters.length)
  for (let i = 0; i < byteCharacters.length; i += 1) {
    byteNumbers[i] = byteCharacters.charCodeAt(i)
  }
  return new Blob([new Uint8Array(byteNumbers)], { type })
}

const buildImageBlob = async () => {
  if (!capturedImage.value) {
    return null
  }

  if (selection.value && imageRef.value) {
    const img = imageRef.value
    const sel = selection.value
    const scaleX = imageSize.value.width / img.clientWidth
    const scaleY = imageSize.value.height / img.clientHeight
    const x1 = Math.min(sel.x1, sel.x2)
    const y1 = Math.min(sel.y1, sel.y2)
    const x2 = Math.max(sel.x1, sel.x2)
    const y2 = Math.max(sel.y1, sel.y2)
    const cropX = Math.round(x1 * scaleX)
    const cropY = Math.round(y1 * scaleY)
    const cropWidth = Math.round((x2 - x1) * scaleX)
    const cropHeight = Math.round((y2 - y1) * scaleY)

    const canvas = document.createElement('canvas')
    canvas.width = cropWidth
    canvas.height = cropHeight
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.drawImage(img, cropX, cropY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight)
      return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    }
  }

  const base64Data = capturedImage.value.split(',')[1]
  return base64ToBlob(base64Data, 'image/png')
}

const handleSubmit = async (resetAfterSave) => {
  if (!formData.name.trim()) {
    ElMessage.warning('请输入元素名称')
    return
  }
  if (formData.element_type === 'image') {
    if (!capturedImage.value) {
      ElMessage.warning('请先获取截图')
      return
    }
    if (!templateFileName.value.trim()) {
      ElMessage.warning('请输入模板文件名')
      return
    }
    if (!formData.image_category) {
      ElMessage.warning('请选择图片分类')
      return
    }
  }
  if (formData.element_type === 'pos' && !hasPos.value) {
    ElMessage.warning('请在截图上单击设置坐标')
    return
  }
  if (formData.element_type === 'region' && !hasRegion.value) {
    ElMessage.warning('请在截图上拖拽框选区域')
    return
  }

  submitting.value = true
  try {
    if (formData.element_type === 'image') {
      const imageBlob = await buildImageBlob()
      if (!imageBlob) {
        ElMessage.error('图片处理失败')
        return
      }
      const file = new File([imageBlob], templateFileName.value.trim(), { type: 'image/png' })
      const uploadResponse = await uploadAppElementImage(file, formData.image_category || 'common')
      if (!uploadResponse.data.success) {
        ElMessage.error(uploadResponse.data.message || '图片上传失败')
        logOperation('元素图片上传失败', 'error', uploadResponse.data)
        return
      }
      formData.config.image_path = uploadResponse.data.data.image_path
      formData.config.file_hash = uploadResponse.data.data.file_hash
    }

    const submitData = {
      name: formData.name.trim(),
      element_type: formData.element_type,
      project: formData.project || null,
      tags: formData.tags,
      config: {
        ...formData.config,
        image_category: formData.image_category || 'common',
      },
    }

    await createAppElement(submitData)
    ElMessage.success('元素创建成功')
    logOperation(`元素创建成功: ${submitData.name}`, 'success', submitData)
    emit('created')
    if (resetAfterSave) {
      resetFormOnly()
    }
  } catch (error) {
    console.error('Create element failed:', error)
    ElMessage.error(error?.response?.data?.message || error?.response?.data?.detail || error.message || '元素创建失败')
    logOperation(`元素创建失败: ${formData.name || '未命名元素'}`, 'error', error?.response?.data || error?.message)
  } finally {
    submitting.value = false
  }
}

const handleCreateCategory = async () => {
  const name = newCategoryName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  creatingCategory.value = true
  try {
    const response = await createAppImageCategory(name)
    if (!response.data.success) {
      ElMessage.error(response.data.message || '创建分类失败')
      return
    }
    await loadImageCategories()
    formData.image_category = response.data.data.name
    newCategoryName.value = ''
    createCategoryVisible.value = false
    ElMessage.success('分类创建成功')
    logOperation(`图片分类创建成功: ${response.data.data.name}`, 'success')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error.message || '创建分类失败')
    logOperation(`图片分类创建失败: ${name}`, 'error', error?.response?.data || error?.message)
  } finally {
    creatingCategory.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadImageCategories()])
})
</script>

<style scoped>
.element-workbench {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workbench-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.workbench-header h4 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.workbench-header p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.workbench-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 16px;
}

.capture-pane,
.form-pane {
  min-height: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
}

.capture-pane {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
}

.form-pane {
  padding: 16px;
  overflow: auto;
}

.image-wrapper {
  position: relative;
  cursor: crosshair;
  display: inline-block;
  max-width: 100%;
  max-height: 100%;
}

.capture-image {
  max-width: 100%;
  max-height: calc(100vh - 280px);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
}

.selection-box {
  position: absolute;
  border: 2px solid #409eff;
  background: rgba(64, 158, 255, 0.12);
  box-sizing: border-box;
}

.selection-close {
  position: absolute;
  top: -12px;
  right: -12px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: #f56c6c;
  color: #fff;
  cursor: pointer;
}

.selection-info {
  position: absolute;
  left: 0;
  top: -28px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(17, 24, 39, 0.72);
  color: #fff;
  font-size: 12px;
}

.resize-handle {
  position: absolute;
  width: 10px;
  height: 10px;
  background: #fff;
  border: 1px solid #409eff;
  border-radius: 50%;
}

.resize-handle-nw { left: -6px; top: -6px; cursor: nwse-resize; }
.resize-handle-n { left: calc(50% - 5px); top: -6px; cursor: ns-resize; }
.resize-handle-ne { right: -6px; top: -6px; cursor: nesw-resize; }
.resize-handle-e { right: -6px; top: calc(50% - 5px); cursor: ew-resize; }
.resize-handle-se { right: -6px; bottom: -6px; cursor: nwse-resize; }
.resize-handle-s { left: calc(50% - 5px); bottom: -6px; cursor: ns-resize; }
.resize-handle-sw { left: -6px; bottom: -6px; cursor: nesw-resize; }
.resize-handle-w { left: -6px; top: calc(50% - 5px); cursor: ew-resize; }

.inline-row {
  display: flex;
  width: 100%;
  gap: 8px;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 20px;
}

@media (max-width: 1200px) {
  .workbench-body {
    grid-template-columns: 1fr;
  }
}
</style>
