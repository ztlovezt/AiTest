<template>
  <div class="scene-item-wrapper">
    <div
      class="scene-item"
      :class="[
        categoryClass,
        {
        active: isActive,
        'is-expanded': step._expanded,
        'sub-step-item': depth > 1,
        'nested-step-item': depth > 2,
        'third-level-item': depth > 3
      }]"
      @click.stop="emit('select', path)"
    >
      <div class="scene-item-main">
        <span class="scene-index" :class="{ 'sub-index': depth > 1 }">{{ displayIndex }}</span>
        <span class="scene-name">{{ getStepDisplayName(step) }}</span>
      </div>
      <div class="scene-item-actions">
        <el-button
          v-if="isExpandableStep(step)"
          link
          size="small"
          @click.stop="emit('toggle', path)"
        >
          {{ step._expanded ? t('appAutomation.sceneBuilder.collapse') : t('appAutomation.sceneBuilder.expand') }}
        </el-button>
        <el-button link size="small" @click.stop="emit('duplicate', path)">{{ t('appAutomation.sceneBuilder.copy') }}</el-button>
        <el-button link size="small" @click.stop="emit('remove', path)">{{ t('appAutomation.sceneBuilder.delete') }}</el-button>
      </div>
    </div>

    <div v-if="step._expanded && branchGroups.length" class="tree-node control-branches">
      <div
        v-for="branch in branchGroups"
        :key="`${branch.source}:${branch.key}:${branch.branchIndex ?? 'x'}`"
        class="if-branch-block"
      >
        <div class="if-branch-header">
          <span>{{ branch.label }}</span>
          <div v-if="step.type === 'if'" class="branch-actions">
            <template v-if="branch.optional">
              <el-button
                v-if="branch.enabled === false"
                link
                size="small"
                @click.stop="emit('enable-optional-branch', { stepPath: path, branch })"
              >
                {{ t('appAutomation.sceneBuilder.enable') }}
              </el-button>
              <el-button
                v-else
                link
                size="small"
                type="danger"
                @click.stop="emit('disable-optional-branch', { stepPath: path, branch })"
              >
                {{ t('appAutomation.sceneBuilder.delete') }}
              </el-button>
            </template>
            <el-button
              v-if="branch.removable"
              link
              size="small"
              type="danger"
              @click.stop="emit('remove-elseif-branch', { stepPath: path, branchIndex: branch.branchIndex })"
            >
              {{ t('appAutomation.sceneBuilder.removeBranch') }}
            </el-button>
          </div>
        </div>

        <div v-if="branch.conditionEditable" class="if-conditions-list">
          <div
            v-for="(condition, conditionIndex) in branch.conditions"
            :key="conditionIndex"
            class="if-condition-row"
          >
            <el-input v-model="condition.field" placeholder="left/value" size="small" style="width: 180px" />
            <el-select v-model="condition.operator" placeholder="operator" size="small" style="width: 130px">
              <el-option label="equals" value="equals" />
              <el-option label="not equals" value="not_equals" />
              <el-option label="contains" value="contains" />
              <el-option label="not contains" value="not_contains" />
              <el-option label="greater than" value="greater_than" />
              <el-option label="greater or equal" value="greater_or_equal" />
              <el-option label="less than" value="less_than" />
              <el-option label="less or equal" value="less_or_equal" />
              <el-option label="truthy" value="truthy" />
              <el-option label="falsy" value="falsy" />
              <el-option label="regex" value="regex" />
              <el-option label="startswith" value="startswith" />
              <el-option label="endswith" value="endswith" />
            </el-select>
            <el-input v-model="condition.value" placeholder="right/expected" size="small" />
            <el-button
              link
              size="small"
              type="danger"
              @click.stop="emit('remove-condition', { stepPath: path, branch, conditionIndex })"
            >
              {{ t('appAutomation.sceneBuilder.delete') }}
            </el-button>
          </div>
          <div class="sub-step-toolbar">
            <el-button
              size="small"
              type="primary"
              link
              @click.stop="emit('add-condition', { stepPath: path, branch })"
            >
              {{ t('appAutomation.sceneBuilder.addCondition') }}
            </el-button>
          </div>
        </div>

        <draggable
          v-if="branch.enabled !== false"
          :list="getBranchSteps(branch)"
          class="sub-steps-list"
          :group="{ name: 'ui-components', pull: true, put: true }"
          :animation="200"
          item-key="id"
          @add="handleBranchAdd(branch, $event)"
        >
          <template #item="{ element, index }">
            <SceneStepTreeNode
              :step="element"
              :path="createChildPath(branch, index)"
              :depth="depth + 1"
              :selected-path-key="selectedPathKey"
              @select="emit('select', $event)"
              @toggle="emit('toggle', $event)"
              @duplicate="emit('duplicate', $event)"
              @remove="emit('remove', $event)"
              @collection-add="emit('collection-add', $event)"
              @add-condition="emit('add-condition', $event)"
              @remove-condition="emit('remove-condition', $event)"
              @enable-optional-branch="emit('enable-optional-branch', $event)"
              @disable-optional-branch="emit('disable-optional-branch', $event)"
              @add-elseif-branch="emit('add-elseif-branch', $event)"
              @remove-elseif-branch="emit('remove-elseif-branch', $event)"
            />
          </template>
          <template #footer>
            <div v-if="!getBranchSteps(branch).length" class="empty-branch-placeholder">
              拖拽组件到此分支
            </div>
          </template>
        </draggable>
      </div>

      <div v-if="step.type === 'if'" class="sub-step-toolbar">
        <el-button size="small" type="primary" link @click.stop="emit('add-elseif-branch', { stepPath: path })">
          {{ t('appAutomation.sceneBuilder.addElseIfBranch') }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import draggable from "vuedraggable"
import {
  getStepBranches,
  isExpandableStep,
  serializeStepPath
} from "./scene-flow"

const { t, te } = useI18n()

const props = defineProps({
  step: {
    type: Object,
    required: true
  },
  path: {
    type: Array,
    required: true
  },
  depth: {
    type: Number,
    default: 1
  },
  selectedPathKey: {
    type: String,
    default: ""
  }
})

const emit = defineEmits([
  "select",
  "toggle",
  "duplicate",
  "remove",
  "collection-add",
  "add-condition",
  "remove-condition",
  "enable-optional-branch",
  "disable-optional-branch",
  "add-elseif-branch",
  "remove-elseif-branch"
])

const pathKey = computed(() => serializeStepPath(props.path))
const isActive = computed(() => props.selectedPathKey && props.selectedPathKey === pathKey.value)
const branchGroups = computed(() => getStepBranches(props.step))
const displayIndex = computed(() => formatDisplayIndex(props.path))
const categoryClass = computed(() => {
  const category = props.step?.category
  if (category === "control") return "category-control"
  if (category === "action") return "category-action"
  if (category === "utility") return "category-utility"
  if (category === "assert") return "category-assert"
  return ""
})

function createChildPath(branch, index) {
  return [
    ...props.path,
    {
      source: branch.source,
      key: branch.key,
      branchIndex: branch.branchIndex,
      index
    }
  ]
}

function handleBranchAdd(branch, event) {
  emit("collection-add", {
    parentPath: props.path,
    source: branch.source,
    key: branch.key,
    branchIndex: branch.branchIndex,
    newIndex: event.newIndex
  })
}

function getBranchSteps(branch) {
  return Array.isArray(branch?.steps) ? branch.steps : []
}

function getTranslatedComponentName(type) {
  if (!type) {
    return ""
  }
  const key = `appAutomation.sceneBuilder.componentNames.${type}`
  return te(key) ? t(key) : ""
}

function getStepDisplayName(step) {
  if (!step || typeof step !== "object") {
    return ""
  }

  if (step.kind === "custom") {
    return step.name || step.type || ""
  }

  const translatedName = getTranslatedComponentName(step.type)
  const currentName = step.name || ""
  const originName = step.origin_name || ""

  if (!translatedName) {
    return currentName || step.type || ""
  }

  if (!currentName || currentName === step.type || (originName && currentName === originName)) {
    return translatedName
  }

  return currentName
}

function formatDisplayIndex(path) {
  if (!Array.isArray(path) || path.length === 0) {
    return "1"
  }

  const lastSegment = path[path.length - 1]
  if (lastSegment.key === "root") {
    return String(lastSegment.index + 1)
  }

  return path
    .map((segment) => {
      if (segment.source === "elseif") {
        return `E${(segment.branchIndex ?? 0) + 1}.${segment.index + 1}`
      }
      if (segment.key === "then_steps") {
        return `T${segment.index + 1}`
      }
      if (segment.key === "else_steps") {
        return `F${segment.index + 1}`
      }
      if (segment.key === "try_steps") {
        return `TRY.${segment.index + 1}`
      }
      if (segment.key === "catch_steps") {
        return `CATCH.${segment.index + 1}`
      }
      if (segment.key === "finally_steps") {
        return `FINALLY.${segment.index + 1}`
      }
      return String(segment.index + 1)
    })
    .join(".")
}
</script>

<style scoped>
.scene-item-wrapper {
  margin-bottom: 8px;
}

.scene-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-left-width: 4px;
  border-radius: 8px;
  background: #fff;
  transition: all 0.2s ease;
}

.scene-item:hover {
  border-color: #c0c4cc;
}

.scene-item.active {
  border-color: #409eff;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.18);
}

.scene-item.is-expanded {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.scene-item-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.scene-index {
  min-width: 40px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f4f4f5;
  color: #606266;
  text-align: center;
  font-size: 12px;
}

.sub-index {
  min-width: 54px;
}

.scene-name {
  font-weight: 600;
  color: #303133;
}

.category-control {
  border-left-color: #7c3aed !important;
  background: rgba(124, 58, 237, 0.06);
}

.category-action {
  border-left-color: #2563eb !important;
  background: rgba(37, 99, 235, 0.06);
}

.category-utility {
  border-left-color: #0f766e !important;
  background: rgba(15, 118, 110, 0.06);
}

.category-assert {
  border-left-color: #d97706 !important;
  background: rgba(217, 119, 6, 0.06);
}

.scene-item-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tree-node {
  margin-left: 20px;
  padding: 12px 0 0 18px;
  position: relative;
}

.tree-node::before {
  content: "";
  position: absolute;
  left: 2px;
  top: 0;
  bottom: 8px;
  width: 2px;
  border-radius: 999px;
  background: #ebeef5;
}

.control-branches {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sub-steps-list {
  min-height: 48px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
}

.if-branch-block {
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 12px;
}

.if-branch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  color: #303133;
  font-weight: 600;
}

.branch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.if-conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.if-condition-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-step-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.empty-branch-placeholder {
  min-height: 56px;
  border: 1px dashed #c0d3f7;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  background: #f8fbff;
  font-size: 13px;
}
</style>
