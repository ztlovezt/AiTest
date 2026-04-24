<template>
    <div class="ui-test-scene-builder">
        <div class="page-header">
            <h3>{{ t('appAutomation.sceneBuilder.title') }}</h3>
            <div class="header-actions">
                <el-button type="primary" size="small" :icon="Check" :loading="saving" @click="saveScene">
                    {{ t('appAutomation.sceneBuilder.saveCase') }}
                </el-button>
                <el-button size="small" :icon="Refresh" @click="resetScene">
                    {{ t('appAutomation.sceneBuilder.reset') }}
                </el-button>
            </div>
        </div>

        <el-card class="scene-config">
            <el-form :model="sceneForm" label-width="120px" size="small">
                <el-row :gutter="16">
                    <el-col :span="8">
                        <el-form-item :label="t('appAutomation.sceneBuilder.sceneName')" required>
                            <el-input v-model.trim="sceneForm.name"
                                :placeholder="t('appAutomation.sceneBuilder.sceneNamePlaceholder')" clearable />
                        </el-form-item>
                    </el-col>
                    <el-col :span="8">
                        <el-form-item :label="t('appAutomation.sceneBuilder.project')">
                            <el-select v-model="sceneForm.project"
                                :placeholder="t('appAutomation.sceneBuilder.selectProject')" clearable filterable
                                style="width:100%">
                                <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
                            </el-select>
                        </el-form-item>
                    </el-col>
                    <el-col :span="8">
                        <el-form-item :label="t('appAutomation.sceneBuilder.sceneDescription')">
                            <el-input v-model.trim="sceneForm.description"
                                :placeholder="t('appAutomation.sceneBuilder.optional')" clearable />
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-row :gutter="16">
                    <el-col :span="24">
                        <el-form-item :label="t('appAutomation.sceneBuilder.sceneVariables')">
                            <div class="scene-variables">
                                <div v-for="(item, index) in sceneVariables" :key="`var_${index}`"
                                    class="scene-variable-item">
                                    <el-input v-model.trim="item.name"
                                        :placeholder="t('appAutomation.sceneBuilder.variableName')" size="small" />
                                    <el-select v-model="item.scope" :placeholder="t('appAutomation.sceneBuilder.scope')"
                                        size="small">
                                        <el-option label="local" value="local" />
                                        <el-option label="global" value="global" />
                                    </el-select>
                                    <el-select v-model="item.type" :placeholder="t('appAutomation.sceneBuilder.type')"
                                        size="small">
                                        <el-option label="string" value="string" />
                                        <el-option label="number" value="number" />
                                        <el-option label="boolean" value="boolean" />
                                        <el-option label="array" value="array" />
                                        <el-option label="object" value="object" />
                                    </el-select>
                                    <el-input v-model.trim="item.value"
                                        :placeholder="t('appAutomation.sceneBuilder.defaultValue')" size="small" />
                                    <el-input v-model.trim="item.description"
                                        :placeholder="t('appAutomation.sceneBuilder.description')" size="small" />
                                    <el-button link size="small" @click="removeSceneVariable(index)">
                                        {{ t('appAutomation.sceneBuilder.delete') }}
                                    </el-button>
                                </div>
                                <el-button link size="small" @click="addSceneVariable">
                                    {{ t('appAutomation.sceneBuilder.addVariable') }}
                                </el-button>
                            </div>
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-row :gutter="16">
                    <el-col :span="10">
                        <el-form-item label="API_BASE_URL">
                            <el-input v-model.trim="sceneRuntime.base_url" placeholder="http://127.0.0.1:8000"
                                size="small" />
                        </el-form-item>
                    </el-col>
                </el-row>
                <el-row :gutter="16">
                    <el-col :span="8">
                        <el-form-item :label="t('appAutomation.sceneBuilder.retryTimes')">
                            <el-input v-model.number="sceneRuntime.retry_times" type="number"
                                :placeholder="t('appAutomation.sceneBuilder.retryPlaceholder')" size="small" />
                        </el-form-item>
                    </el-col>
                    <el-col :span="8">
                        <el-form-item :label="t('appAutomation.sceneBuilder.retryInterval')">
                            <el-input v-model.number="sceneRuntime.retry_interval" type="number"
                                :placeholder="t('appAutomation.sceneBuilder.retryIntervalPlaceholder')" size="small" />
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>
        </el-card>

        <el-row :gutter="16" class="scene-layout">
            <el-col :span="6">
                <el-card class="palette-card" shadow="never">
                    <template #header>
                        <div class="card-title">
                            <span>{{ t('appAutomation.sceneBuilder.componentLibrary') }}</span>
                            <div class="palette-toolbar">
                                <el-button type="primary" size="small" :icon="Upload" @click="openPackageDialog">
                                    {{ t('appAutomation.sceneBuilder.importPackage') }}
                                </el-button>
                                <el-button type="success" size="small" :icon="Download" @click="openExportDialog">
                                    {{ t('appAutomation.sceneBuilder.exportPackage') }}
                                </el-button>
                            </div>
                        </div>
                    </template>
                    <el-tabs v-model="paletteTab" stretch>
                        <el-tab-pane :label="t('appAutomation.sceneBuilder.baseComponents')" name="base">
                            <draggable class="palette-list" :list="componentPalette"
                                :group="{ name: 'ui-components', pull: 'clone', put: false }" :clone="cloneComponent"
                                :sort="false" item-key="type">
                                <template #item="{ element }">
                                    <div class="palette-item" :class="getCategoryClass(element.category)">
                                        <div class="palette-left">
                                            <span class="palette-name">{{ getComponentDisplayName(element) }}</span>
                                        </div>
                                    </div>
                                </template>
                                <template #footer>
                                    <div v-if="componentPalette.length === 0" class="palette-empty">
                                        {{ t('appAutomation.sceneBuilder.noBaseComponents') }}
                                    </div>
                                </template>
                            </draggable>
                        </el-tab-pane>
                        <el-tab-pane :label="t('appAutomation.sceneBuilder.customComponents')" name="custom">
                            <draggable class="palette-list" :list="customComponentPalette"
                                :group="{ name: 'ui-components', pull: 'clone', put: false }" :clone="cloneComponent"
                                :sort="false" item-key="id">
                                <template #item="{ element }">
                                    <div class="palette-item" :class="getCategoryClass(element.category)">
                                        <div class="palette-left">
                                            <span class="palette-name">{{ getComponentDisplayName(element) }}</span>
                                        </div>
                                        <div class="palette-actions">
                                            <el-button link size="small" @click.stop="openEditCustomComponent(element)">
                                                {{ t('appAutomation.sceneBuilder.edit') }}
                                            </el-button>
                                            <el-button link size="small" style="color: #f56c6c"
                                                @click.stop="deleteCustomComponent(element)">
                                                {{ t('appAutomation.sceneBuilder.delete') }}
                                            </el-button>
                                        </div>
                                    </div>
                                </template>
                                <template #footer>
                                    <div v-if="customComponentPalette.length === 0" class="palette-empty">
                                        {{ t('appAutomation.sceneBuilder.noCustomComponents') }}
                                    </div>
                                </template>
                            </draggable>
                        </el-tab-pane>
                    </el-tabs>
                </el-card>
            </el-col>

            <el-col :span="12">
                <el-card class="scene-card" shadow="never">
                    <template #header>
                        <div class="card-title">
                            <span>{{ t('appAutomation.sceneBuilder.sceneSteps') }}</span>
                            <el-button type="primary" size="small" :icon="FolderAdd"
                                :disabled="scenarioSteps.length === 0" @click="openCustomComponentDialog">
                                {{ t('appAutomation.sceneBuilder.saveAsCustom') }}
                            </el-button>
                        </div>
                    </template>
                    <div class="scene-hint" v-if="scenarioSteps.length === 0">
                        {{ t('appAutomation.sceneBuilder.dragHint') }}
                    </div>
                    <draggable v-model="scenarioSteps" class="scene-list"
                        :group="{ name: 'ui-components', pull: true, put: true }" :animation="200" item-key="id"
                        @add="handleRootCollectionAdd">
                        <template #item="{ element, index }">
                            <SceneStepTreeNode
                                :step="element"
                                :path="[{ source: 'root', key: 'root', index }]"
                                :depth="1"
                                :selected-path-key="selectedStepPathKey"
                                @select="selectStepPath"
                                @toggle="toggleStepExpand"
                                @duplicate="duplicateStepPath"
                                @remove="removeStepPath"
                                @collection-add="handleTreeCollectionAdd"
                                @add-condition="handleAddCondition"
                                @remove-condition="handleRemoveCondition"
                                @enable-optional-branch="handleEnableOptionalBranch"
                                @disable-optional-branch="handleDisableOptionalBranch"
                                @add-elseif-branch="handleAddElseIfBranch"
                                @remove-elseif-branch="handleRemoveElseIfBranch"
                            />
                        </template>
                    </draggable>
                </el-card>
            </el-col>

            <el-col :span="6">
                <el-card class="config-card" shadow="never">
                    <template #header>
                        <div class="card-title">
                            {{ t('appAutomation.sceneBuilder.componentConfig') }}
                            <el-button type="success" size="small" :icon="Camera" style="margin-left: auto;"
                                @click="openCaptureElementDialog">
                                {{ t('appAutomation.sceneBuilder.createElementTool') }}
                            </el-button>
                        </div>
                    </template>
                    <div v-if="!activeStep" class="config-empty">
                        {{ t('appAutomation.sceneBuilder.selectStepConfig') }}
                    </div>
                    <!-- 选中自定义组件父级时提示展开编辑 -->
                    <div v-else-if="activeStep && activeStep.kind === 'custom' && selectedStepDepth === 1"
                        class="config-form">
                        <el-form label-width="110px" size="small">
                            <el-form-item label="步骤名称">
                                <el-input v-model.trim="activeStepDisplayName" />
                            </el-form-item>
                            <el-form-item label="组件类型">
                                <el-input :model-value="activeStep.type" disabled />
                            </el-form-item>
                            <el-form-item label="子步骤数">
                                <span>{{ (activeStep.steps || []).length }} 个</span>
                            </el-form-item>
                            <el-alert type="info" :closable="false" style="margin-top: 8px;">
                                点击左侧"展开"按钮可查看和编辑子步骤，修改仅影响当前用例。
                            </el-alert>
                        </el-form>
                    </div>
                    <div v-else class="config-form">
                        <el-form :model="activeStep" label-width="110px" size="small">
                            <el-form-item label="步骤名称">
                                <el-input v-model.trim="activeStepDisplayName" />
                            </el-form-item>
                            
                            
                            <div class="variable-hint" v-text="fixI18nBraces(t('appAutomation.sceneBuilder.variableSupport'))">
                            </div>
                            <div v-if="activeStep && activeStep.type === 'image_exists_click'"
                                class="variable-hint hint-danger">
                                {{ t('appAutomation.sceneBuilder.imageExistsClickLogic') }}
                            </div>
                            <div v-if="activeStep && activeStep.type === 'image_exists_click_chain'"
                                class="variable-hint hint-danger">
                                {{ t('appAutomation.sceneBuilder.imageExistsClickChainLogic') }}
                            </div>
                            <div v-if="activeStep && activeStep.type === 'key_event'" class="variable-hint hint-danger">
                                {{ t('appAutomation.sceneBuilder.keyEventLogic') }}
                            </div>
                            <div v-if="activeStep && activeStep.type === 'foreach_assert'"
                                class="variable-hint hint-danger">
                                {{ t('appAutomation.sceneBuilder.foreachAssertLogic') }}
                            </div>
                            <div v-if="activeStep && activeStep.type === 'api_request'" class="api-template-block">
                                <div class="tool-hint">{{ t('appAutomation.sceneBuilder.apiTemplate') }}</div>
                                <div class="template-list">
                                    <div v-for="item in apiRequestTemplates" :key="item.name" class="template-item">
                                        <span class="template-name">{{ item.name }}</span>
                                        <div class="template-actions">
                                            <el-button link size="small"
                                                @click="applyApiRequestTemplate(item, activeStep)">
                                                使用
                                            </el-button>
                                        </div>
                                    </div>
                                    <div v-if="apiRequestTemplates.length === 0" class="tool-hint">暂无模板</div>
                                </div>
                            </div>
                            <!-- 统一的字段分组显示 -->
                            <template v-if="schemaFields.length > 0">
                                <div v-for="group in getFieldGroups()" :key="group.key" class="field-group">
                                    <div class="group-header">
                                        <span class="group-title">{{ group.title }}</span>
                                        <!-- 定位类分组显示选择按钮 -->
                                        <el-button v-if="group.key !== 'other'" type="primary" size="small"
                                            @click="openElementSelector(group.key)">
                                            <el-icon>
                                                <Link />
                                            </el-icon>
                                            {{ linkedElements[group.key] ? '更换元素' : '选择元素' }}
                                        </el-button>
                                    </div>

                                    <!-- 关联状态提示 -->
                                    <el-alert v-if="linkedElements[group.key]" type="success" :closable="false"
                                        class="element-linked-alert">
                                        已关联: {{ linkedElements[group.key].name }} ({{ linkedElements[group.key].type }})
                                        <el-button link type="danger" @click="clearLinkedElement(group.key)"
                                            style="margin-left: 10px;">
                                            清除
                                        </el-button>
                                    </el-alert>

                                    <!-- 字段列表 -->
                                    <el-form-item
                                        v-for="field in group.fields"
                                        :key="field"
                                        :label="getFieldLabel(field)"
                                        :required="schemaRequired.includes(field)"
                                    >
                                        <div v-if="needsHelperButtons(field)" style="display: flex; gap: 5px; flex: 1;">
                                            <el-input
                                                v-if="field === 'expected_list'"
                                                type="textarea"
                                                :rows="4"
                                                :model-value="getExpectedListValue(activeStep && activeStep.config)"
                                                :placeholder="getFieldPlaceholder(field)"
                                                @update:model-value="updateExpectedList(activeStep.config, $event)"
                                                @focus="onInputFocus"
                                                style="flex: 1;"
                                            />
                                            <el-input
                                                v-else-if="isJsonField(field)"
                                                type="textarea"
                                                :rows="getJsonFieldRows(field)"
                                                :value="getJsonFieldValue(activeStep && activeStep.config, field)"
                                                :placeholder="getFieldPlaceholder(field)"
                                                @input="updateJsonField(activeStep.config, field, $event)"
                                                @focus="onInputFocus"
                                                style="flex: 1;"
                                            />
                                            <el-input
                                                v-else
                                                v-model.trim="activeStep.config[field]"
                                                :placeholder="getFieldPlaceholder(field)"
                                                @focus="onInputFocus"
                                                style="flex: 1;"
                                            />
                                            <el-tooltip :content="t('appAutomation.sceneBuilder.referenceDataFactory')" placement="top">
                                                <el-button size="small" @click="openDataFactorySelector(activeStep, field)" class="data-factory-btn">
                                                    <el-icon><MagicStick /></el-icon>
                                                </el-button>
                                            </el-tooltip>
                                            <el-tooltip :content="t('appAutomation.sceneBuilder.insertVariable')" placement="top">
                                                <el-button size="small" @click="openVariableHelper(activeStep, field)" class="variable-helper-btn">
                                                    <el-icon><MagicStick /></el-icon>
                                                </el-button>
                                            </el-tooltip>
                                        </div>
                                        <el-input
                                            v-else-if="field === 'expected_list'"
                                            type="textarea"
                                            :rows="4"
                                            :model-value="getExpectedListValue(activeStep && activeStep.config)"
                                            :placeholder="getFieldPlaceholder(field)"
                                            @update:model-value="updateExpectedList(activeStep.config, $event)"
                                        />
                                        <el-input
                                            v-else-if="isJsonField(field)"
                                            type="textarea"
                                            :rows="getJsonFieldRows(field)"
                                            :value="getJsonFieldValue(activeStep && activeStep.config, field)"
                                            :placeholder="getFieldPlaceholder(field)"
                                            @input="updateJsonField(activeStep.config, field, $event)" />
                                        <el-select v-else-if="getFieldOptions(field).length"
                                            v-model="activeStep.config[field]" placeholder="请选择"
                                            :filterable="isImageScopeField(field)">
                                            <el-option v-for="option in getFieldOptions(field)" :key="option.value"
                                                :label="option.label" :value="option.value" />
                                        </el-select>
                                        <el-switch v-else-if="getFieldType(field) === 'boolean'"
                                            v-model="activeStep.config[field]" />
                                        <el-input-number v-else-if="getFieldType(field) === 'number'"
                                            v-model="activeStep.config[field]" :min="getFieldNumberRule(field).min"
                                            :max="getFieldNumberRule(field).max" :step="getFieldNumberRule(field).step"
                                            controls-position="right" />
                                        <el-input v-else v-model.trim="activeStep.config[field]"
                                            :placeholder="getFieldPlaceholder(field)" />
                                    </el-form-item>
                                </div>
                            </template>

                            <!-- 无配置字段 -->
                            <div v-else class="config-empty">该组件未配置 schema</div>
                        </el-form>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <!-- 从设备创建元素对话框 -->
        <CaptureElementDialog v-model="captureElementDialogVisible" @success="handleElementCreated" />

        <el-dialog :title="t('appAutomation.sceneBuilder.importPackage')" v-model="packageDialogVisible" width="520px"
            :close-on-click-modal="false" @close="resetPackageDialog">
            <el-form label-width="110px" size="small">
                <el-form-item :label="t('appAutomation.sceneBuilder.overwriteExistingComponents')">
                    <el-switch v-model="packageOverwrite" />
                </el-form-item>
                <el-form-item :label="t('appAutomation.sceneBuilder.selectFile')">
                    <el-upload :show-file-list="false" :http-request="handlePackageUpload" accept=".json,.yaml,.yml">
                        <el-button size="small" type="primary" :loading="packageUploading">
                            {{ t('appAutomation.sceneBuilder.selectPackage') }}
                        </el-button>
                        <template #tip>
                            <div class="el-upload__tip">{{ t('appAutomation.sceneBuilder.supportedFormats') }}</div>
                        </template>
                    </el-upload>
                </el-form-item>
                <el-divider></el-divider>
                <div class="package-title">{{ t('appAutomation.sceneBuilder.importedPackages') }}</div>
                <div class="package-list" v-loading="packageLoading">
                    <div v-for="item in packageList" :key="item.id" class="package-item">
                        <div class="package-name">{{ item.name }}</div>
                        <div class="package-meta">
                            <span>{{ item.version || "-" }}</span>
                            <span>{{ item.updated_at || item.created_at || "-" }}</span>
                        </div>
                    </div>
                    <div v-if="packageList.length === 0" class="package-empty">暂无组件包</div>
                </div>
            </el-form>
            <template #footer>
                <div class="dialog-footer">
                    <el-button @click="packageDialogVisible = false">关闭</el-button>
                </div>
            </template>
        </el-dialog>

        <el-dialog :title="t('appAutomation.sceneBuilder.exportPackage')" v-model="exportDialogVisible" width="420px"
            :close-on-click-modal="false" @close="resetExportDialog">
            <el-form label-width="110px" size="small">
                <el-form-item :label="t('appAutomation.sceneBuilder.exportIncludeDisabled')">
                    <el-switch v-model="packageIncludeDisabled" />
                </el-form-item>
            </el-form>
            <template #footer>
                <div class="dialog-footer">
                    <el-button type="primary" plain @click="exportPackage('yaml')">{{
                        t('appAutomation.sceneBuilder.exportYAML') }}</el-button>
                    <el-button type="primary" plain @click="exportPackage('json')">{{
                        t('appAutomation.sceneBuilder.exportJSON') }}</el-button>
                    <el-button @click="exportDialogVisible = false">{{ t('appAutomation.sceneBuilder.close')
                        }}</el-button>
                </div>
            </template>
        </el-dialog>

        <el-dialog :title="customDialogTitle" v-model="customDialogVisible" width="50vw" :close-on-click-modal="false"
            @close="resetCustomDialog">
            <el-form ref="customFormRef" :model="customForm" :rules="customRules" label-width="110px">
                <el-form-item label="组件名称" prop="name">
                    <el-input v-model.trim="customForm.name" placeholder="请输入组件名称" />
                </el-form-item>
                <el-form-item label="组件类型" prop="type">
                    <el-input v-model.trim="customForm.type" placeholder="例如 login_flow" />
                </el-form-item>
                <el-form-item label="组件描述">
                    <el-input v-model.trim="customForm.description" placeholder="可选" />
                </el-form-item>
            </el-form>
            <!-- 组件步骤编辑区域（独占整行，不受 form label-width 约束） -->
            <div v-if="customDialogMode === 'edit'" class="custom-steps-section">
                <div class="custom-steps-label">组件步骤</div>
                <div class="custom-edit-steps">
                        <div class="custom-step-list">
                            <div class="custom-step-toolbar">
                                <el-select v-model="editStepType" placeholder="选择基础组件" size="small">
                                    <el-option
                                        v-for="item in componentPalette"
                                        :key="item.type"
                                        :label="getComponentDisplayName(item)"
                                        :value="item.type"
                                    />
                                </el-select>
                                <el-button size="small" @click="addEditStep">添加</el-button>
                            </div>
                            <draggable
                                v-model="editingCustomSteps"
                                class="custom-step-items"
                                :group="{ name: 'ui-custom-edit', pull: false, put: false }"
                                :animation="200"
                                item-key="id"
                            >
                                <template #item="{ element, index }">
                                    <div
                                        class="custom-step-item scene-item"
                                        :class="{ active: editingSelectedIndex === index }"
                                        @click="selectEditStep(index)"
                                    >
                                        <div class="scene-item-main">
                                            <span class="scene-index">{{ index + 1 }}</span>
                                            <span class="scene-name">{{ getComponentDisplayName(element) }}</span>
                                        </div>
                                        <div class="scene-item-actions">
                                            <el-button
                                                link
                                                size="small"
                                                @click.stop="duplicateEditStep(index)"
                                            >
                                                复制
                                            </el-button>
                                            <el-button
                                                link
                                                size="small"
                                                @click.stop="removeEditStep(index)"
                                            >
                                                删除
                                            </el-button>
                                        </div>
                                    </div>
                                </template>
                            </draggable>
                        </div>
                        <div class="custom-step-config">
                            <div v-if="!editingActiveStep" class="config-empty">
                                请选择步骤进行配置
                            </div>
                            <div v-else class="config-form">
                                <el-form :model="editingActiveStep" label-width="110px" size="small">
                                    <el-form-item label="步骤名称">
                                        <el-input v-model.trim="editingActiveStepDisplayName" />
                                    </el-form-item>
                                    <div class="variable-hint" v-text="fixI18nBraces(t('appAutomation.sceneBuilder.variableSupport'))">
                                    </div>
                                    <div v-if="editingActiveStep && editingActiveStep.type === 'api_request'" class="api-template-block">
                                        <div class="tool-hint">API 示例模板</div>
                                        <div class="template-list">
                                            <div v-for="item in apiRequestTemplates" :key="item.name" class="template-item">
                                                <span class="template-name">{{ item.name }}</span>
                                                <div class="template-actions">
                                                    <el-button link size="small" @click="applyApiRequestTemplate(item, editingActiveStep)">
                                                        使用
                                                    </el-button>
                                                </div>
                                            </div>
                                            <div v-if="apiRequestTemplates.length === 0" class="tool-hint">暂无模板</div>
                                        </div>
                                    </div>
                                    <!-- 分组显示（与场景步骤配置面板一致） -->
                                    <template v-if="editingSchemaFields.length > 0">
                                        <div
                                            v-for="group in getEditingFieldGroups()"
                                            :key="group.key"
                                            class="field-group"
                                        >
                                            <div class="group-header">
                                                <span class="group-title">{{ group.title }}</span>
                                                <el-button
                                                    v-if="group.key !== 'other'"
                                                    type="primary"
                                                    size="small"
                                                    @click="openElementSelector(group.key)"
                                                >
                                                    <el-icon><Link /></el-icon>
                                                    {{ linkedElements[group.key] ? '更换元素' : '选择元素' }}
                                                </el-button>
                                            </div>
                                            <el-alert
                                                v-if="linkedElements[group.key]"
                                                type="success"
                                                :closable="false"
                                                class="element-linked-alert"
                                            >
                                                已关联: {{ linkedElements[group.key].name }} ({{ linkedElements[group.key].type }})
                                                <el-button
                                                    link
                                                    type="danger"
                                                    @click="clearLinkedElement(group.key)"
                                                    style="margin-left: 10px;"
                                                >
                                                    清除
                                                </el-button>
                                            </el-alert>
                                            <el-form-item
                                                v-for="field in group.fields"
                                                :key="field"
                                                :label="getFieldLabel(field)"
                                                :required="editingSchemaRequired.includes(field)"
                                            >
                                                <div v-if="needsHelperButtons(field)" style="display: flex; gap: 5px; flex: 1;">
                                                    <el-input
                                                        v-if="field === 'expected_list'"
                                                        type="textarea"
                                                        :rows="4"
                                                        :model-value="getExpectedListValue(editingActiveStep && editingActiveStep.config)"
                                                        :placeholder="getFieldPlaceholder(field)"
                                                        @update:model-value="updateExpectedList(editingActiveStep.config, $event)"
                                                        @focus="onInputFocus"
                                                        style="flex: 1;"
                                                    />
                                                    <el-input
                                                        v-else-if="isJsonField(field)"
                                                        type="textarea"
                                                        :rows="getJsonFieldRows(field)"
                                                        :value="getJsonFieldValue(editingActiveStep && editingActiveStep.config, field)"
                                                        :placeholder="getFieldPlaceholder(field)"
                                                        @input="updateJsonField(editingActiveStep.config, field, $event)"
                                                        @focus="onInputFocus"
                                                        style="flex: 1;"
                                                    />
                                                    <el-input
                                                        v-else
                                                        v-model.trim="editingActiveStep.config[field]"
                                                        :placeholder="getFieldPlaceholder(field)"
                                                        @focus="onInputFocus"
                                                        style="flex: 1;"
                                                    />
                                                    <el-tooltip :content="t('appAutomation.sceneBuilder.referenceDataFactory')" placement="top">
                                                        <el-button size="small" @click="openDataFactorySelector(editingActiveStep, field, true)" class="data-factory-btn">
                                                            <el-icon><MagicStick /></el-icon>
                                                        </el-button>
                                                    </el-tooltip>
                                                    <el-tooltip :content="t('appAutomation.sceneBuilder.insertVariable')" placement="top">
                                                        <el-button size="small" @click="openVariableHelper(editingActiveStep, field, true)" class="variable-helper-btn">
                                                            <el-icon><MagicStick /></el-icon>
                                                        </el-button>
                                                    </el-tooltip>
                                                </div>
                                                <el-input
                                                    v-else-if="field === 'expected_list'"
                                                    type="textarea"
                                                    :rows="4"
                                                    :model-value="getExpectedListValue(editingActiveStep && editingActiveStep.config)"
                                                    :placeholder="getFieldPlaceholder(field)"
                                                    @update:model-value="updateExpectedList(editingActiveStep.config, $event)"
                                                />
                                                <el-input
                                                    v-else-if="isJsonField(field)"
                                                    type="textarea"
                                                    :rows="getJsonFieldRows(field)"
                                                    :value="getJsonFieldValue(editingActiveStep && editingActiveStep.config, field)"
                                                    :placeholder="getFieldPlaceholder(field)"
                                                    @input="updateJsonField(editingActiveStep.config, field, $event)"
                                                />
                                                <el-select
                                                    v-else-if="getFieldOptions(field).length"
                                                    v-model="editingActiveStep.config[field]"
                                                    placeholder="请选择"
                                                    :filterable="isImageScopeField(field)"
                                                >
                                                    <el-option
                                                        v-for="option in getFieldOptions(field)"
                                                        :key="option.value"
                                                        :label="option.label"
                                                        :value="option.value"
                                                    />
                                                </el-select>
                                                <el-switch
                                                    v-else-if="getFieldTypeForDef(editingActiveDef, field) === 'boolean'"
                                                    v-model="editingActiveStep.config[field]"
                                                />
                                                <el-input-number
                                                    v-else-if="getFieldTypeForDef(editingActiveDef, field) === 'number'"
                                                    v-model="editingActiveStep.config[field]"
                                                    :min="getFieldNumberRuleForDef(editingActiveDef, field).min"
                                                    :max="getFieldNumberRuleForDef(editingActiveDef, field).max"
                                                    :step="getFieldNumberRuleForDef(editingActiveDef, field).step"
                                                    controls-position="right"
                                                />
                                                <el-input
                                                    v-else
                                                    v-model.trim="editingActiveStep.config[field]"
                                                    :placeholder="getFieldPlaceholder(field)"
                                                />
                                            </el-form-item>
                                        </div>
                                    </template>
                                    <div v-else class="config-empty">该组件未配置 schema</div>
                                </el-form>
                            </div>
                        </div>
                    </div>
                </div>
            <template #footer>
                <div class="dialog-footer">
                    <el-button @click="customDialogVisible = false">取消</el-button>
                    <el-button type="primary" :loading="customSaving" @click="saveCustomComponent">保存</el-button>
                </div>
            </template>
        </el-dialog>

        <!-- 元素选择对话框 -->
        <el-dialog v-model="elementSelectorVisible" title="选择元素" width="1200px" destroy-on-close>
            <div class="element-selector-container">
                <!-- 筛选条件 -->
                <div class="element-selector-filter">
                    <el-space wrap>
                        <el-radio-group v-model="elementFilterType" @change="loadElementsForSelector">
                            <el-radio-button value="">全部</el-radio-button>
                            <el-radio-button value="image">图片</el-radio-button>
                            <el-radio-button value="pos">坐标</el-radio-button>
                            <el-radio-button value="region">区域</el-radio-button>
                        </el-radio-group>

                        <el-input v-model="elementSearchKeyword" placeholder="搜索元素" style="width: 250px" clearable
                            @change="loadElementsForSelector">
                            <template #prefix>
                                <el-icon>
                                    <Search />
                                </el-icon>
                            </template>
                        </el-input>
                    </el-space>
                </div>

                <!-- 元素列表 -->
                <el-table :data="selectorElements" border v-loading="elementSelectorLoading" max-height="450px"
                    highlight-current-row @row-click="handleElementRowClick">
                    <el-table-column prop="name" label="元素名称" width="200">
                        <template #default="{ row }">
                            <el-link type="primary">{{ row.name }}</el-link>
                        </template>
                    </el-table-column>

                    <el-table-column prop="element_type" label="类型" width="100">
                        <template #default="{ row }">
                            <el-tag :type="getTypeTagColor(row.element_type)">
                                {{ row.element_type_display }}
                            </el-tag>
                        </template>
                    </el-table-column>

                    <el-table-column label="图片分类" width="120">
                        <template #default="{ row }">
                            <el-tag v-if="row.element_type === 'image' && row.config?.image_category" type="info"
                                size="small">
                                {{ row.config.image_category }}
                            </el-tag>
                            <span v-else style="color: #909399;">-</span>
                        </template>
                    </el-table-column>

                    <el-table-column prop="tags" label="标签" width="180">
                        <template #default="{ row }">
                            <el-tag v-for="tag in row.tags" :key="tag" size="small" style="margin-right: 5px">
                                {{ tag }}
                            </el-tag>
                        </template>
                    </el-table-column>

                    <el-table-column label="预览" width="200" align="center">
                        <template #default="{ row }">
                            <div v-if="row.element_type === 'image'" class="preview-image">
                                <el-image :src="row.preview_url" fit="contain" style="width: 150px; height: 60px" />
                            </div>
                            <div v-else-if="row.element_type === 'pos'" class="preview-pos">
                                <el-space :size="4">
                                    <el-tag type="primary" size="small">X: {{ row.config?.x }}</el-tag>
                                    <el-tag type="primary" size="small">Y: {{ row.config?.y }}</el-tag>
                                </el-space>
                            </div>
                            <div v-else-if="row.element_type === 'region'" class="preview-region">
                                <el-space direction="vertical" :size="4">
                                    <el-space :size="4">
                                        <el-tag type="success" size="small">X1: {{ row.config?.x1 }}</el-tag>
                                        <el-tag type="success" size="small">Y1: {{ row.config?.y1 }}</el-tag>
                                    </el-space>
                                    <el-space :size="4">
                                        <el-tag type="warning" size="small">X2: {{ row.config?.x2 }}</el-tag>
                                        <el-tag type="warning" size="small">Y2: {{ row.config?.y2 }}</el-tag>
                                    </el-space>
                                </el-space>
                            </div>
                        </template>
                    </el-table-column>

                    <el-table-column label="操作" width="100" fixed="right">
                        <template #default="{ row }">
                            <el-button size="small" type="primary" @click.stop="applyElement(row)">
                                应用
                            </el-button>
                        </template>
                    </el-table-column>
                </el-table>

                <!-- 分页 -->
                <el-pagination v-model:current-page="elementCurrentPage" v-model:page-size="elementPageSize"
                    :total="elementTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next"
                    @current-change="loadElementsForSelector" @size-change="loadElementsForSelector"
                    style="margin-top: 15px; justify-content: flex-end" />
            </div>

            <template #footer>
                <el-button @click="elementSelectorVisible = false">关闭</el-button>
            </template>
        </el-dialog>

        <!-- 数据工厂选择器对话框 -->
        <DataFactorySelector
            v-model="showDataFactorySelector"
            @select="handleDataFactorySelect"
        />

        <!-- 变量助手对话框 -->
        <el-dialog
            :close-on-press-escape="false"
            :modal="true"
            :destroy-on-close="false"
            v-model="showVariableHelper"
            :title="t('appAutomation.sceneBuilder.variableHelper')"
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
                            <el-table-column prop="name" :label="t('appAutomation.sceneBuilder.functionName')" width="150" show-overflow-tooltip>
                                <template #default="{ row }">
                                    <el-tag size="small">{{ row.name }}</el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column prop="desc" :label="t('appAutomation.sceneBuilder.description')" min-width="150" />
                            <el-table-column prop="syntax" :label="t('appAutomation.sceneBuilder.syntax')" min-width="200" show-overflow-tooltip />
                            <el-table-column prop="example" :label="t('appAutomation.sceneBuilder.example')" min-width="200" show-overflow-tooltip />
                            <el-table-column :label="t('appAutomation.sceneBuilder.operation')" width="80" fixed="right">
                                <template #default="{ row }">
                                    <el-button link type="primary" size="small">{{ t('appAutomation.sceneBuilder.insert') }}</el-button>
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
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Download, FolderAdd, DocumentCopy, Check, Search, Link, Refresh, Camera, MagicStick } from '@element-plus/icons-vue'
import draggable from "vuedraggable"
import CaptureElementDialog from '../elements/components/CaptureElementDialog.vue'
import SceneStepTreeNode from './components/SceneStepTreeNode.vue'
import DataFactorySelector from '@/components/DataFactorySelector.vue'
import {
    MAX_CONTROL_NESTING,
    createDefaultCondition,
    ensureIfConfig,
    ensureStepContainers,
    getControlDepthForPath,
    getControlMaxDepth,
    normalizeIfConfigForSave,
    resolveCollectionByPath,
    resolveParentInfoByPath,
    resolveStepByPath,
    serializeStepPath
} from './components/scene-flow'
import {
    getComponents,
    getCustomComponents,
    createCustomComponent as apiCreateCustomComponent,
    updateCustomComponent as apiUpdateCustomComponent,
    deleteCustomComponent as apiDeleteCustomComponent,
    importComponentPackage,
    exportComponentPackage,
    getTestCaseDetail,
    createTestCase,
    updateTestCase,
    getAppElementList,
    getAppImageCategories,
    getDeviceList,
    getAppProjects
} from '@/api/app-automation'
import { getVariableFunctions } from '@/api/data-factory'

// Route
const route = useRoute()
const router = useRouter()

// Internationalization
const { t, te } = useI18n()

// Reactive state
const saving = ref(false)
const paletteTab = ref("base")
const projectList = ref([])
const sceneForm = ref({
    name: "",
    description: "",
    project: null
})
const sceneVariables = ref([])
const sceneRuntime = ref({
    base_url: "http://127.0.0.1:8000",
    retry_times: 0,
    retry_interval: 0.5
})
// 组件库初始化为空数组，完全从后端 API 加载
const componentPalette = ref([])
const defaultPalette = ref([])
const customComponentPalette = ref([])
const defaultCustomPalette = ref([])
const scenarioSteps = ref([])
const selectedStepPath = ref(null)
const selectedIndex = ref(null)
const selectedSubIndex = ref(null)    // 当前选中的子步骤索引（展开编辑用）
const selectedNestedIndex = ref(null) // 当前选中的嵌套子步骤索引（子步骤的子步骤，第二层）
const selectedThirdLevelIndex = ref(null) // 当前选中的第三层子步骤索引（第三层）
const selectedIfBranchType = ref(null) // 'then' | 'elseif' | 'else'
const selectedElseIfIndex = ref(null)  // else if 分支索引
const componentDefinitions = ref({})
const customComponentDefinitions = ref({})
const editingCaseId = ref(null)
const sceneSavedSnapshot = ref('')
const apiRequestTemplates = ref([
    {
        name: "VIP初始化",
        config: {
            method: "POST",
            url: "/api/ui_test/configs/vip-setup/",
            headers: {
                "Content-Type": "application/json"
            },
            json: {
                user_id: "",
                vip_level: 16,
                level: 0,
                coin: 68510000000
            },
            timeout: 10,
            expected_status: 200,
            response_type: "json"
        }
    }
])
const customDialogVisible = ref(false)
const customSaving = ref(false)
const customDialogMode = ref("create")
const editingCustomId = ref(null)
const editingCustomSteps = ref([])
const editingSelectedIndex = ref(null)
const editStepType = ref("")
const customForm = ref({
    name: "",
    type: "",
    description: ""
})
const packageDialogVisible = ref(false)
const packageUploading = ref(false)
const packageOverwrite = ref(true)
const packageIncludeDisabled = ref(false)
const packageList = ref([])
const packageLoading = ref(false)
const exportDialogVisible = ref(false)
const captureElementDialogVisible = ref(false)
const customRules = ref({
    name: [{ required: true, message: "请输入组件名称", trigger: "blur" }],
    type: [{ required: true, message: "请输入组件类型", trigger: "blur" }]
})

// 元素选择器相关状态
const elementSelectorVisible = ref(false)
const elementSelectorLoading = ref(false)
const selectorElements = ref([])
const elementFilterType = ref('')
const elementSearchKeyword = ref('')
const elementCurrentPage = ref(1)
const elementPageSize = ref(10)
const elementTotal = ref(0)
const imageCategoryOptions = ref([])  // 图片分类选项

// 关联元素信息追踪
const elementSelectorTarget = ref('') // 当前选择器的目标：'selector' | 'fallback' | 'click' | 'ocr' | 'start' | 'end' | 'target'
const linkedElements = ref({
    selector: null,  // 通用定位关联的元素: { id, name, type }
    fallback: null,  // 备用定位关联的元素
    click: null,     // 点击定位关联的元素
    ocr: null,       // OCR定位关联的元素
    start: null,     // 起始定位关联的元素
    end: null,       // 结束定位关联的元素
    target: null,    // 目标定位关联的元素
    expected: null   // 期望值关联的元素
})

// Refs
const customFormRef = ref(null)

// 数据工厂选择器和变量助手相关状态
const showDataFactorySelector = ref(false)
const showVariableHelper = ref(false)
const currentFocusedInput = ref(null)
const currentDataFactoryTarget = ref(null)  // { step, field, isEditing }
const variableCategories = ref([])
const variableLoading = ref(false)

// Computed properties
const activeStep = computed(() => {
    return resolveStepByPath(scenarioSteps.value, selectedStepPath.value)
})

const selectedStepPathKey = computed(() => serializeStepPath(selectedStepPath.value))
const selectedStepDepth = computed(() => (
    Array.isArray(selectedStepPath.value) ? selectedStepPath.value.length : 0
))
const defaultSceneRuntime = Object.freeze({
    base_url: "http://127.0.0.1:8000",
    retry_times: 0,
    retry_interval: 0.5
})
const CATEGORY_CLASS_MAP = Object.freeze({
    control: 'category-control',
    action: 'category-action',
    utility: 'category-utility',
    assert: 'category-assert'
})

const hasMeaningfulVariable = (item) => {
    if (!item || typeof item !== 'object') {
        return false
    }

    return ['name', 'scope', 'type', 'defaultValue', 'description', 'default_value']
        .some(key => {
            const value = item[key]
            return typeof value === 'number' || typeof value === 'boolean' || String(value ?? '').trim() !== ''
        })
}

const buildSceneSnapshot = () => JSON.stringify({
    form: sceneForm.value,
    variables: sceneVariables.value,
    runtime: sceneRuntime.value,
    steps: scenarioSteps.value
})

const getCategoryClass = (category) => CATEGORY_CLASS_MAP[category] || ''

const formatCategoryLabel = (category) => {
    if (!category) {
        return ''
    }
    return String(category).replace(/_/g, ' ').toUpperCase()
}

const getTranslatedComponentName = (type) => {
    if (!type) {
        return ''
    }
    const key = `appAutomation.sceneBuilder.componentNames.${type}`
    return te(key) ? t(key) : ''
}

const getComponentDisplayName = (item) => {
    if (!item || typeof item !== 'object') {
        return ''
    }

    if (item.kind === 'custom') {
        return item.name || item.type || ''
    }

    const translatedName = getTranslatedComponentName(item.type)
    const currentName = item.name || ''
    const originName = item.origin_name || ''

    if (item.name_is_default) {
        return translatedName || currentName || item.type || ''
    }

    if (!translatedName) {
        return currentName || item.type || ''
    }

    if (!currentName || currentName === item.type || (originName && currentName === originName)) {
        return translatedName
    }

    return currentName
}

const isStepNameCustomized = (step) => {
    if (!step || typeof step !== 'object') {
        return false
    }

    if (step.kind === 'custom') {
        return true
    }

    if (step.name_is_default) {
        return false
    }

    const currentName = String(step.name || '').trim()
    if (!currentName) {
        return false
    }

    const translatedName = getTranslatedComponentName(step.type)
    const originName = String(step.origin_name || '').trim()

    return ![step.type, translatedName, originName].filter(Boolean).includes(currentName)
}

const getEditableStepName = (step) => {
    if (!step || typeof step !== 'object') {
        return ''
    }

    if (step.kind === 'custom') {
        return step.name || ''
    }

    if (step.name_is_default) {
        return getTranslatedComponentName(step.type) || step.name || step.type || ''
    }

    if (isStepNameCustomized(step)) {
        return step.name || ''
    }

    return getTranslatedComponentName(step.type) || step.name || step.type || ''
}

const updateStepDisplayName = (step, value) => {
    if (!step || typeof step !== 'object') {
        return
    }

    step.name_is_default = false
    step.name = value
}

const hasSceneContent = computed(() => {
    const hasFormContent = Boolean(
        String(sceneForm.value.name || '').trim() ||
        String(sceneForm.value.description || '').trim() ||
        sceneForm.value.project
    )

    const hasVariableContent = sceneVariables.value.some(item => hasMeaningfulVariable(item))
    const hasRuntimeContent = JSON.stringify(sceneRuntime.value) !== JSON.stringify(defaultSceneRuntime)

    return hasFormContent || hasVariableContent || hasRuntimeContent || scenarioSteps.value.length > 0
})

const isSceneDirty = computed(() => {
    if (!sceneSavedSnapshot.value) {
        return hasSceneContent.value
    }
    return buildSceneSnapshot() !== sceneSavedSnapshot.value
})

const activeParentStep = computed(() => {
    if (!Array.isArray(selectedStepPath.value) || selectedStepPath.value.length === 0) return null
    const parentPath = selectedStepPath.value.slice(0, -1)
    if (parentPath.length === 0) return null
    return resolveStepByPath(scenarioSteps.value, parentPath)
})

const activeComponentDef = computed(() => {
    if (!activeStep.value) {
        return null
    }
    if (activeStep.value.kind === "custom") {
        return customComponentDefinitions.value[activeStep.value.type] || null
    }
    return componentDefinitions.value[activeStep.value.type] || null
})

const editingActiveStep = computed(() => {
    if (editingSelectedIndex.value === null) {
        return null
    }
    return editingCustomSteps.value[editingSelectedIndex.value] || null
})

const editingActiveDef = computed(() => {
    if (!editingActiveStep.value) {
        return null
    }
    return componentDefinitions.value[editingActiveStep.value.type] || null
})

const activeStepDisplayName = computed({
    get() {
        return getEditableStepName(activeStep.value)
    },
    set(value) {
        updateStepDisplayName(activeStep.value, value)
    }
})

const editingActiveStepDisplayName = computed({
    get() {
        return getEditableStepName(editingActiveStep.value)
    },
    set(value) {
        updateStepDisplayName(editingActiveStep.value, value)
    }
})

const editingSchemaFields = computed(() => {
    if (!editingActiveDef.value || !editingActiveDef.value.schema) {
        return []
    }
    const properties = editingActiveDef.value.schema.properties || {}
    const required = editingSchemaRequired.value
    const fields = Object.keys(properties)
    const ordered = [
        ...fields.filter(field => required.includes(field)),
        ...fields.filter(field => !required.includes(field))
    ]
    let visible = ordered.filter(field => shouldShowField(field, editingActiveStep.value))
    return getFieldOrder(visible)
})

const editingSchemaRequired = computed(() => {
    if (!editingActiveDef.value || !editingActiveDef.value.schema) {
        return []
    }
    return editingActiveDef.value.schema.required || []
})

const customDialogTitle = computed(() => {
    return customDialogMode.value === "edit" ? "编辑自定义组件" : "另存为自定义组件"
})

const schemaFields = computed(() => {
    if (!activeComponentDef.value || !activeComponentDef.value.schema) {
        return []
    }
    const properties = activeComponentDef.value.schema.properties || {}
    const required = schemaRequired.value
    const fields = Object.keys(properties)
    const ordered = [
        ...fields.filter(field => required.includes(field)),
        ...fields.filter(field => !required.includes(field))
    ]
    let visible = ordered.filter(field => shouldShowField(field, activeStep.value))
    return getFieldOrder(visible)
})

const schemaRequired = computed(() => {
    if (!activeComponentDef.value || !activeComponentDef.value.schema) {
        return []
    }
    return activeComponentDef.value.schema.required || []
})

// 修复 i18n 翻译中的占位符（将 __OPEN__ 和 __CLOSE__ 替换为 {{ 和 }}）
const fixI18nBraces = (text) => {
    if (!text) return text
    return text.replace(/__OPEN__/g, '{{').replace(/__CLOSE__/g, '}}')
}

watch(() => activeStep.value?.config?.assert_type, (value) => {
    if (!activeStep.value || !activeStep.value.config) {
        return
    }
    if (value === "number" && activeStep.value.config.match_mode !== "exact") {
        activeStep.value.config.match_mode = "exact"
    }
})

// Lifecycle hooks
onMounted(async () => {
    // console.log('UiTestSceneBuilder mounted, $api:', $api)
    try {
        await Promise.all([
            loadComponentPalette(),
            loadCustomComponentPalette(),
            loadImageCategoryOptions(),  // 加载图片分类选项
            getAppProjects({ page_size: 100 }).then(res => { projectList.value = res.data.results || res.data || [] })
        ])

        const caseId = route.query.case_id
        if (caseId) {
            editingCaseId.value = caseId
            loadCaseDetail(caseId)
        }
    } catch (error) {
        console.error('初始化组件数据失败:', error)
    }
})


// Methods
const shouldShowField = (field, step) => {
    if (!step || !step.config) {
        return field !== "image_scope"
    }

    const hiddenControlFields = ["steps", "then_steps", "else_steps", "try_steps", "catch_steps", "finally_steps", "conditions", "else_ifs"]
    if (hiddenControlFields.includes(field)) {
        return false
    }

    if (step.type === "if" && ["left", "operator", "right"].includes(field)) {
        return false
    }

    const assertType = step.config.assert_type
    if (field === "image_scope") {
        const typeFields = [
            "selector_type",
            "start_selector_type",
            "end_selector_type",
            "target_selector_type",
            "click_selector_type"
        ]
        if (assertType === "image") {
            return true
        }
        return typeFields.some(key => step.config[key] === "image")
    }

    if (field === "image_threshold") {
        const typeFields = [
            "selector_type",
            "start_selector_type",
            "end_selector_type",
            "target_selector_type",
            "click_selector_type"
        ]
        if (assertType === "image") {
            return true
        }
        return typeFields.some(key => step.config[key] === "image")
    }


    if (field === "expected_image_scope") {
        return assertType === "image"
    }


    if (assertType === "image") {
        if (field === "ocr_selector_type" || field === "ocr_selector" || field === "match_mode" || field === "selector_type" || field === "selector") {
            return false
        }
        if (field === "min" || field === "max" || field === "expected_exists") {
            return false
        }
    }

    if (assertType === "exists") {
        if (field === "expected" || field === "match_mode" || field === "min" || field === "max" || field === "ocr_selector_type" || field === "ocr_selector") {
            return false
        }
    }

    if (assertType === "range") {
        if (field === "expected" || field === "match_mode" || field === "expected_exists") {
            return false
        }
    }

    if (assertType === "regex") {
        if (field === "match_mode" || field === "expected_exists" || field === "min" || field === "max") {
            return false
        }
    }

    if (step.type === "loop") {
        const mode = step.config.mode
        if (field === "times" && mode !== "count") {
            return false
        }
        if ((field === "left" || field === "operator" || field === "right") && mode !== "condition") {
            return false
        }
        if ((field === "items" || field === "item_var" || field === "item_scope") && mode !== "foreach") {
            return false
        }
    }

    return true
}

const formatExpectedList = (value) => {
    if (Array.isArray(value)) {
        return value.join(",")
    }
    if (typeof value === "string") {
        return value
    }
    return ""
}

const getExpectedListValue = (config) => {
    if (!config) {
        return ""
    }
    if (typeof config.expected_list_input === "string") {
        return config.expected_list_input
    }
    return formatExpectedList(config.expected_list)
}

const getActiveConfigForField = () => {
    if (activeStep.value && activeStep.value.config) {
        return activeStep.value.config
    }
    if (editingActiveStep.value && editingActiveStep.value.config) {
        return editingActiveStep.value.config
    }
    return null
}

const updateExpectedList = (config, rawValue) => {
    if (!config) {
        return
    }
    if (Array.isArray(rawValue)) {
        config.expected_list = rawValue
        return
    }
    const inputValue = String(rawValue || "")
    config.expected_list_input = inputValue
    const parts = inputValue
        .split(/\n|,|，/)
        .map(item => item.trim())
        .filter(Boolean)
    config.expected_list = parts
}

const isJsonField = (field) => {
    const def = editingActiveDef.value || activeComponentDef.value
    const type = def ? getFieldTypeForDef(def, field) : getFieldType(field)
    return type === "array" || type === "object"
}

const getJsonFieldRows = (field) => {
    const largeFields = ["steps", "then_steps", "else_steps", "try_steps", "catch_steps", "finally_steps", "branches"]
    return largeFields.includes(field) ? 16 : 8
}

const getJsonFieldValue = (config, field) => {
    if (!config) {
        return ""
    }
    const inputKey = `${field}_input`
    if (typeof config[inputKey] === "string") {
        return config[inputKey]
    }
    const value = config[field]
    if (value === undefined || value === null || value === "") {
        return ""
    }
    try {
        return JSON.stringify(value, null, 2)
    } catch (error) {
        return String(value)
    }
}

const updateJsonField = (config, field, rawValue) => {
    if (!config) {
        return
    }
    const inputValue = String(rawValue || "")
    config[`${field}_input`] = inputValue
    if (!inputValue.trim()) {
        const def = editingActiveDef.value || activeComponentDef.value
        const fieldType = def ? getFieldTypeForDef(def, field) : getFieldType(field)
        if (fieldType === "array") {
            config[field] = []
        } else {
            config[field] = {}
        }
        return
    }
    try {
        config[field] = JSON.parse(inputValue)
    } catch (error) {
        // 保留原始输入
    }
}

const addSceneVariable = () => {
    sceneVariables.value.push({
        name: "",
        value: "",
        type: "string",
        scope: "local",
        description: ""
    })
}

const removeSceneVariable = (index) => {
    sceneVariables.value.splice(index, 1)
}

const formatSceneVariables = () => {
    return sceneVariables.value
        .filter(item => item && item.name)
        .map(item => ({
            name: item.name,
            scope: item.scope || "local",
            type: item.type || "string",
            value: parseSceneVariableValue(item.value, item.type),
            description: item.description || ""
        }))
}

const parseSceneVariableValue = (value, type) => {
    if (type === "number") {
        const num = Number(value)
        return Number.isNaN(num) ? 0 : num
    }
    if (type === "boolean") {
        if (typeof value === "boolean") {
            return value
        }
        return String(value).trim().toLowerCase() === "true"
    }
    if (type === "array" || type === "object") {
        if (typeof value === "string") {
            try {
                return JSON.parse(value)
            } catch (error) {
                return type === "array" ? [] : {}
            }
        }
        return value
    }
    return value
}

const loadSceneVariables = (rawVariables) => {
    if (!Array.isArray(rawVariables)) {
        sceneVariables.value = []
        return
    }
    sceneVariables.value = rawVariables.map(item => ({
        name: item.name || "",
        scope: item.scope || "local",
        type: item.type || "string",
        value: (item.type === "array" || item.type === "object")
            ? JSON.stringify(item.value || (item.type === "array" ? [] : {}))
            : (item.value !== undefined && item.value !== null ? String(item.value) : ""),
        description: item.description || ""
    }))
}

const generateStepId = () => {
    return `step_${Date.now()}_${Math.floor(Math.random() * 10000)}`
}

const resetLinkedElements = () => {
    linkedElements.value = {
        selector: null,
        fallback: null,
        click: null,
        ocr: null,
        start: null,
        end: null,
        target: null,
        expected: null
    }
}

const clearLegacySelectionState = () => {
    selectedIndex.value = null
    selectedSubIndex.value = null
    selectedNestedIndex.value = null
    selectedThirdLevelIndex.value = null
    selectedIfBranchType.value = null
    selectedElseIfIndex.value = null
}

const applyStepDefaultsDeep = (step) => {
    if (!step || typeof step !== 'object') {
        return
    }

    if (!step.id) {
        step.id = generateStepId()
    }

    ensureStepContainers(step)
    applyDefaultConfig(step)

    const definition = step.kind === "custom"
        ? customComponentDefinitions.value[step.type]
        : componentDefinitions.value[step.type]
    if (!step.origin_name && definition?.name) {
        step.origin_name = definition.name
    }
    if (step.kind !== 'custom' && step.name_is_default === undefined) {
        const currentName = String(step.name || '').trim()
        step.name_is_default = !currentName || currentName === step.type || currentName === step.origin_name
    }
    if (!step.category && definition?.category) {
        step.category = definition.category
    }

    const childCollections = []

    if (Array.isArray(step.steps)) {
        childCollections.push(step.steps)
    }
    if (Array.isArray(step.config?.steps)) {
        childCollections.push(step.config.steps)
    }
    if (Array.isArray(step.config?.then_steps)) {
        childCollections.push(step.config.then_steps)
    }
    if (Array.isArray(step.config?.else_steps)) {
        childCollections.push(step.config.else_steps)
    }
    if (Array.isArray(step.config?.try_steps)) {
        childCollections.push(step.config.try_steps)
    }
    if (Array.isArray(step.config?.catch_steps)) {
        childCollections.push(step.config.catch_steps)
    }
    if (Array.isArray(step.config?.finally_steps)) {
        childCollections.push(step.config.finally_steps)
    }
    ;(step.config?.elseif_branches || []).forEach(branch => {
        if (!Array.isArray(branch.conditions_input)) {
            branch.conditions_input = [createDefaultCondition()]
        }
        if (!Array.isArray(branch.steps)) {
            branch.steps = []
        }
        childCollections.push(branch.steps)
    })

    childCollections.forEach(collection => {
        collection.forEach(childStep => applyStepDefaultsDeep(childStep))
    })
}

const cloneStepDeep = (step) => {
    const clonedStep = JSON.parse(JSON.stringify(step))

    const walk = (currentStep) => {
        if (!currentStep || typeof currentStep !== 'object') {
            return
        }
        currentStep.id = generateStepId()
        delete currentStep._expanded
        applyStepDefaultsDeep(currentStep)
    }

    walk(clonedStep)
    return clonedStep
}

const selectStepPath = (path) => {
    selectedStepPath.value = Array.isArray(path) ? JSON.parse(JSON.stringify(path)) : null
    const step = resolveStepByPath(scenarioSteps.value, selectedStepPath.value)
    if (step) {
        applyStepDefaultsDeep(step)
    }
    clearLegacySelectionState()
    resetLinkedElements()
}

const toggleStepExpand = (path) => {
    const step = resolveStepByPath(scenarioSteps.value, path)
    if (!step) {
        return
    }
    ensureStepContainers(step)
    step._expanded = !step._expanded
}

const canInsertControlStep = (parentPath, newStep) => {
    const parentDepth = Array.isArray(parentPath) ? getControlDepthForPath(scenarioSteps.value, parentPath) : 0
    const maxDepth = getControlMaxDepth(newStep, parentDepth)
    if (maxDepth > MAX_CONTROL_NESTING) {
        return {
            allowed: false,
            message: `控制流组件最多支持 ${MAX_CONTROL_NESTING} 层嵌套`
        }
    }
    return {
        allowed: true,
        message: ''
    }
}

const handleRootCollectionAdd = (evt) => {
    const newStep = scenarioSteps.value[evt.newIndex]
    if (!newStep) {
        return
    }

    applyStepDefaultsDeep(newStep)
    const check = canInsertControlStep([], newStep)
    if (!check.allowed) {
        scenarioSteps.value.splice(evt.newIndex, 1)
        ElMessage.warning(check.message)
        return
    }

    selectStepPath([{ source: 'root', key: 'root', index: evt.newIndex }])
}

const handleTreeCollectionAdd = ({ parentPath, source, key, branchIndex, newIndex }) => {
    const collection = resolveCollectionByPath(scenarioSteps.value, parentPath, { source, key, branchIndex })
    if (!Array.isArray(collection) || !collection[newIndex]) {
        return
    }

    const newStep = collection[newIndex]
    applyStepDefaultsDeep(newStep)

    const check = canInsertControlStep(parentPath, newStep)
    if (!check.allowed) {
        collection.splice(newIndex, 1)
        ElMessage.warning(check.message)
        return
    }

    selectStepPath([
        ...(parentPath || []),
        { source, key, branchIndex, index: newIndex }
    ])
}

const duplicateStepPath = (path) => {
    const parentInfo = resolveParentInfoByPath(scenarioSteps.value, path)
    if (!parentInfo || !Array.isArray(parentInfo.collection)) {
        return
    }

    const sourceStep = parentInfo.collection[parentInfo.currentSegment.index]
    if (!sourceStep) {
        return
    }

    const duplicatedStep = cloneStepDeep(sourceStep)
    duplicatedStep.name = `${sourceStep.name || sourceStep.type}-复制`

    const newIndex = parentInfo.currentSegment.index + 1
    parentInfo.collection.splice(newIndex, 0, duplicatedStep)
    selectStepPath([
        ...parentInfo.parentPath,
        {
            ...parentInfo.currentSegment,
            index: newIndex
        }
    ])
}

const removeStepPath = (path) => {
    const parentInfo = resolveParentInfoByPath(scenarioSteps.value, path)
    if (!parentInfo || !Array.isArray(parentInfo.collection)) {
        return
    }

    parentInfo.collection.splice(parentInfo.currentSegment.index, 1)
    selectedStepPath.value = null
    clearLegacySelectionState()
    resetLinkedElements()
}

const handleAddCondition = ({ stepPath, branch }) => {
    const step = resolveStepByPath(scenarioSteps.value, stepPath)
    if (!step || step.type !== 'if') {
        return
    }

    ensureIfConfig(step)
    if (branch.branchType === 'elseif') {
        step.config.elseif_branches?.[branch.branchIndex]?.conditions_input?.push(createDefaultCondition())
        return
    }

    step.config.conditions_input.push(createDefaultCondition())
}

const handleRemoveCondition = ({ stepPath, branch, conditionIndex }) => {
    const step = resolveStepByPath(scenarioSteps.value, stepPath)
    if (!step || step.type !== 'if') {
        return
    }

    let targetConditions = null
    if (branch.branchType === 'elseif') {
        targetConditions = step.config.elseif_branches?.[branch.branchIndex]?.conditions_input
    } else {
        targetConditions = step.config.conditions_input
    }

    if (!Array.isArray(targetConditions)) {
        return
    }
    if (targetConditions.length <= 1) {
        ElMessage.warning('至少保留一个条件')
        return
    }

    targetConditions.splice(conditionIndex, 1)
}

const handleEnableOptionalBranch = ({ stepPath, branch }) => {
    const step = resolveStepByPath(scenarioSteps.value, stepPath)
    if (!step || step.type !== 'if' || branch.branchType !== 'else') {
        return
    }

    ensureIfConfig(step)
    step.config.else_steps = []
}

const handleDisableOptionalBranch = ({ stepPath, branch }) => {
    const step = resolveStepByPath(scenarioSteps.value, stepPath)
    if (!step || step.type !== 'if' || branch.branchType !== 'else') {
        return
    }

    step.config.else_steps = null
}

const handleAddElseIfBranch = ({ stepPath }) => {
    const step = resolveStepByPath(scenarioSteps.value, stepPath)
    if (!step || step.type !== 'if') {
        return
    }

    ensureIfConfig(step)
    step.config.elseif_branches.push({
        conditions_input: [createDefaultCondition()],
        steps: []
    })
}

const handleRemoveElseIfBranch = ({ stepPath, branchIndex }) => {
    const step = resolveStepByPath(scenarioSteps.value, stepPath)
    if (!step || step.type !== 'if' || !Array.isArray(step.config?.elseif_branches)) {
        return
    }

    step.config.elseif_branches.splice(branchIndex, 1)
}

const cloneComponent = (item) => {
    const cloned = {
        id: generateStepId(),
        type: item.type,
        name: item.kind === "custom" ? item.name : (getTranslatedComponentName(item.type) || item.name),
        origin_name: item.name || "",
        name_is_default: item.kind !== "custom",
        kind: item.kind || "atomic",
        category: item.category || "",
        config: {
            ...item.defaultConfig
        }
    }
    // 自定义组件：深拷贝子步骤到实例中（后续编辑不影响原始定义）
    if (item.kind === "custom" && item.steps && item.steps.length > 0) {
        cloned.steps = JSON.parse(JSON.stringify(item.steps)).map(s => ({
            ...s,
            id: s.id || generateStepId(),
            config: s.config || {}
        }))
        cloned._expanded = false  // 展开/收起状态
    }
    if (cloned.type === "if") {
        ensureIfConfig(cloned)
        delete cloned.config.else_steps
        delete cloned.config.else_steps_input
        cloned._expanded = false
    }
    if (cloned.type === "loop") {
        if (!cloned.config) cloned.config = {}
        if (!cloned.config.steps) cloned.config.steps = []
        cloned._expanded = false
    }
    if (cloned.type === "sequence" || cloned.type === "try") {
        ensureStepContainers(cloned)
        cloned._expanded = false
    }
    applyStepDefaultsDeep(cloned)
    return cloned
}

const selectStep = (index) => {
    selectedIndex.value = index
    selectedSubIndex.value = null  // 切换主步骤时清除子步骤选中
    selectedNestedIndex.value = null  // 清除嵌套层选中状态
    selectedThirdLevelIndex.value = null  // 清除第三层选中状态
    const step = scenarioSteps.value[index]
    if (step) {
        applyDefaultConfig(step)
    }
    // 清除所有关联元素信息（切换步骤时重置）
    linkedElements.value = {
        selector: null,
        fallback: null,
        click: null,
        ocr: null,
        start: null,
        end: null,
        target: null,
        expected: null
    }
}

const selectSubStep = (parentIndex, subIndex) => {
    selectedIndex.value = parentIndex
    selectedSubIndex.value = subIndex
    selectedNestedIndex.value = null  // 清除嵌套层选中状态
    selectedThirdLevelIndex.value = null  // 清除第三层选中状态
    const parentStep = scenarioSteps.value[parentIndex]
    
    let subStep = null
    if (parentStep) {
        // 根据步骤类型获取子步骤
        if (parentStep.type === 'loop') {
            subStep = parentStep.config?.steps?.[subIndex]
        } else if (parentStep.kind === 'custom') {
            subStep = parentStep.steps?.[subIndex]
        }
        
        if (subStep) {
            applyDefaultConfig(subStep)
        }
    }
    
    linkedElements.value = {
        selector: null, fallback: null, click: null, ocr: null,
        start: null, end: null, target: null, expected: null
    }
}

const toggleExpandCustomStep = (index) => {
    const step = scenarioSteps.value[index]
    if (step) {
        step._expanded = !step._expanded
        if (!step._expanded) {
            // 收起时清除子步骤选中
            if (selectedIndex.value === index && selectedSubIndex.value !== null) {
                selectedSubIndex.value = null
                selectedNestedIndex.value = null
            }
        } else {
            // 展开时确保 steps 数组存在
            if (step.type === 'loop') {
                if (!step.config) step.config = {}
                if (!step.config.steps) step.config.steps = []
            } else if (step.type === 'if') {
                ensureIfConfig(step)
            } else if (step.kind === 'custom' && !step.steps) {
                step.steps = []
            }
        }
    }
}

// 切换子步骤的展开/收起状态（用于嵌套的控制组件）
const toggleExpandSubStep = (parentIndex, subIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    // 根据父步骤类型获取子步骤
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    subStep._expanded = !subStep._expanded
    
    if (!subStep._expanded) {
        // 收起时清除选中
        if (selectedIndex.value === parentIndex && selectedSubIndex.value === subIndex) {
            selectedNestedIndex.value = null
        }
    } else {
        // 展开时确保子步骤的 steps 数组存在
        if (subStep.type === 'loop') {
            if (!subStep.config) subStep.config = {}
            if (!subStep.config.steps) subStep.config.steps = []
        } else if (subStep.type === 'if') {
            ensureIfConfig(subStep)
        } else if (subStep.kind === 'custom' && !subStep.steps) {
            subStep.steps = []
        }
    }
}

// 计算控制组件的嵌套层级
const getControlNestingLevel = (step, currentLevel = 1) => {
    if (!step) return currentLevel
    
    let maxLevel = currentLevel
    
    // 检查当前步骤是否是控制组件
    const isControlComponent = step.type === 'loop' || step.type === 'if'
    
    if (isControlComponent) {
        // 获取子步骤
        let subSteps = []
        if (step.type === 'loop') {
            subSteps = step.config?.steps || []
        } else if (step.type === 'if') {
            subSteps = [
                ...(step.config?.then_steps || []),
                ...(step.config?.else_steps || []),
                ...(step.config?.elseif_branches || []).flatMap(branch => branch.steps || [])
            ]
        }
        
        // 递归检查子步骤中的控制组件
        for (const subStep of subSteps) {
            if (subStep.type === 'loop' || subStep.type === 'if') {
                const level = getControlNestingLevel(subStep, currentLevel + 1)
                maxLevel = Math.max(maxLevel, level)
            }
        }
    }
    
    return maxLevel
}

// 检查是否可以添加控制组件（不超过3层嵌套）
const canAddControlComponent = (parentStep, newStepType) => {
    if (newStepType !== 'loop' && newStepType !== 'if') {
        return { allowed: true, message: '' }
    }
    
    const currentLevel = getControlNestingLevel(parentStep, 1)
    if (currentLevel >= 3) {
        return { 
            allowed: false, 
            message: '控制组件（循环/条件）嵌套不能超过3层' 
        }
    }
    
    return { allowed: true, message: '' }
}

const addSubStep = (parentIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    // 根据步骤类型确定子步骤数组的位置
    let stepsArray = null
    if (parentStep.type === 'loop') {
        // loop 类型的子步骤在 config.steps 中
        if (!parentStep.config) parentStep.config = {}
        if (!parentStep.config.steps) parentStep.config.steps = []
        stepsArray = parentStep.config.steps
    } else if (parentStep.kind === 'custom') {
        // 自定义组件的子步骤在 steps 中
        if (!parentStep.steps) parentStep.steps = []
        stepsArray = parentStep.steps
    } else {
        // 其他类型不支持添加子步骤
        return
    }
    
    // 创建新的点击步骤
    const newStep = {
        id: generateStepId(),
        type: 'click',
        name: '点击',
        config: { ...(componentDefinitions.value['click']?.default_config || { selector_type: 'image', timeout: 5 }) }
    }
    
    stepsArray.push(newStep)
    
    // 选中新添加的子步骤
    if (parentStep.type === 'loop') {
        selectSubStep(parentIndex, stepsArray.length - 1)
    } else if (parentStep.kind === 'custom') {
        selectSubStep(parentIndex, stepsArray.length - 1)
    }
}

// 添加控制组件子步骤（带嵌套层级检查）
const addControlSubStep = (parentIndex, stepType) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    // 检查嵌套层级
    const check = canAddControlComponent(parentStep, stepType)
    if (!check.allowed) {
        ElMessage.warning(check.message)
        return
    }
    
    // 根据步骤类型确定子步骤数组的位置
    let stepsArray = null
    if (parentStep.type === 'loop') {
        if (!parentStep.config) parentStep.config = {}
        if (!parentStep.config.steps) parentStep.config.steps = []
        stepsArray = parentStep.config.steps
    } else if (parentStep.kind === 'custom') {
        if (!parentStep.steps) parentStep.steps = []
        stepsArray = parentStep.steps
    } else {
        return
    }
    
    // 创建新的控制组件步骤
    const componentDef = componentDefinitions.value[stepType]
    const newStep = {
        id: generateStepId(),
        type: stepType,
        name: componentDef?.name || stepType,
        config: { ...(componentDef?.default_config || {}) },
        _expanded: false
    }
    
    // 初始化控制组件的配置
    if (stepType === 'loop') {
        if (!newStep.config.steps) newStep.config.steps = []
    } else if (stepType === 'if') {
        ensureIfConfig(newStep)
    }
    
    stepsArray.push(newStep)
    selectSubStep(parentIndex, stepsArray.length - 1)
}

// 处理拖拽添加子步骤事件（检查嵌套层级）
const handleSubStepAdd = (parentIndex, evt) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    // 获取被拖入的元素
    const newIndex = evt.newIndex
    let stepsArray = null
    
    if (parentStep.type === 'loop') {
        stepsArray = parentStep.config?.steps
    } else if (parentStep.kind === 'custom') {
        stepsArray = parentStep.steps
    }
    
    if (!stepsArray || !stepsArray[newIndex]) return
    
    const addedStep = stepsArray[newIndex]
    
    // 检查是否是控制组件
    if (addedStep.type === 'loop' || addedStep.type === 'if') {
        const check = canAddControlComponent(parentStep, addedStep.type)
        if (!check.allowed) {
            ElMessage.warning(check.message)
            // 移除刚添加的步骤
            stepsArray.splice(newIndex, 1)
        }
    }
}

// 处理拖拽添加主步骤事件（检查嵌套层级）
const handleMainStepAdd = (evt) => {
    const newIndex = evt.newIndex
    if (!scenarioSteps.value[newIndex]) return
    
    const addedStep = scenarioSteps.value[newIndex]
    
    // 主步骤没有父级，所以嵌套层级始终为1，不需要检查
    // 这里只是为了完整性保留
}

// 处理拖拽添加嵌套子步骤事件
const handleNestedSubStepAdd = (parentIndex, subIndex, evt) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    const newIndex = evt.newIndex
    let stepsArray = null
    
    if (subStep.type === 'loop') {
        stepsArray = subStep.config?.steps
    } else if (subStep.kind === 'custom') {
        stepsArray = subStep.steps
    }
    
    if (!stepsArray || !stepsArray[newIndex]) return
    
    const addedStep = stepsArray[newIndex]
    
    // 检查是否是控制组件
    if (addedStep.type === 'loop' || addedStep.type === 'if') {
        const check = canAddControlComponent(subStep, addedStep.type)
        if (!check.allowed) {
            ElMessage.warning(check.message)
            stepsArray.splice(newIndex, 1)
        }
    }
}

// 选择嵌套子步骤
const selectNestedSubStep = (parentIndex, subIndex, nestedIndex) => {
    selectedIndex.value = parentIndex
    selectedSubIndex.value = subIndex
    selectedNestedIndex.value = nestedIndex
    selectedThirdLevelIndex.value = null  // 清除第三层选中状态
    
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let nestedStep = null
    if (subStep.type === 'loop') {
        nestedStep = subStep.config?.steps?.[nestedIndex]
    } else if (subStep.kind === 'custom') {
        nestedStep = subStep.steps?.[nestedIndex]
    }
    
    if (nestedStep) {
        applyDefaultConfig(nestedStep)
    }
    
    linkedElements.value = {
        selector: null, fallback: null, click: null, ocr: null,
        start: null, end: null, target: null, expected: null
    }
}

// 选择第三层子步骤
const selectThirdLevelStep = (parentIndex, subIndex, nestedIndex, thirdIndex) => {
    // 先保存 IF 分支状态（用于导航）
    const savedIfBranchType = selectedIfBranchType.value
    const savedElseIfIndex = selectedElseIfIndex.value
    
    // 设置选择索引
    selectedIndex.value = parentIndex
    selectedSubIndex.value = subIndex
    selectedNestedIndex.value = nestedIndex
    selectedThirdLevelIndex.value = thirdIndex
    
    // 清除 IF 分支状态（避免与主步骤 IF 分支混淆）
    selectedIfBranchType.value = null
    selectedElseIfIndex.value = null
    
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    } else if (parentStep.type === 'if') {
        // IF 分支的情况 - 使用保存的分支类型
        if (savedIfBranchType === 'then') {
            subStep = parentStep.config.then_steps?.[subIndex]
        } else if (savedIfBranchType === 'elseif' && savedElseIfIndex !== null) {
            const branch = parentStep.config.elseif_branches?.[savedElseIfIndex]
            subStep = branch?.steps?.[subIndex]
        } else if (savedIfBranchType === 'else') {
            subStep = parentStep.config.else_steps?.[subIndex]
        }
    }
    
    if (!subStep) return
    
    let nestedStep = null
    if (subStep.type === 'loop') {
        nestedStep = subStep.config?.steps?.[nestedIndex]
    } else if (subStep.kind === 'custom') {
        nestedStep = subStep.steps?.[nestedIndex]
    } else if (subStep.type === 'if') {
        // 嵌套的 IF 分支 - 使用保存的分支类型
        if (savedIfBranchType === 'then') {
            nestedStep = subStep.config.then_steps?.[nestedIndex]
        } else if (savedIfBranchType === 'else') {
            nestedStep = subStep.config.else_steps?.[nestedIndex]
        }
    }
    
    if (!nestedStep) return
    
    // 获取第三层子步骤
    let thirdStep = null
    if (nestedStep.type === 'loop') {
        thirdStep = nestedStep.config?.steps?.[thirdIndex]
    } else if (nestedStep.kind === 'custom') {
        thirdStep = nestedStep.steps?.[thirdIndex]
    } else if (nestedStep.type === 'if') {
        // 嵌套的 IF 分支 - 使用保存的分支类型
        if (savedIfBranchType === 'then') {
            thirdStep = nestedStep.config.then_steps?.[thirdIndex]
        } else if (savedIfBranchType === 'else') {
            thirdStep = nestedStep.config.else_steps?.[thirdIndex]
        }
    }
    
    if (thirdStep) {
        applyDefaultConfig(thirdStep)
    }
    
    linkedElements.value = {
        selector: null, fallback: null, click: null, ocr: null,
        start: null, end: null, target: null, expected: null
    }
}

// 添加嵌套子步骤
const addNestedSubStep = (parentIndex, subIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let stepsArray = null
    if (subStep.type === 'loop') {
        if (!subStep.config) subStep.config = {}
        if (!subStep.config.steps) subStep.config.steps = []
        stepsArray = subStep.config.steps
    } else if (subStep.kind === 'custom') {
        if (!subStep.steps) subStep.steps = []
        stepsArray = subStep.steps
    }
    
    if (!stepsArray) return
    
    const newStep = {
        id: generateStepId(),
        type: 'click',
        name: '点击',
        config: { ...(componentDefinitions.value['click']?.default_config || { selector_type: 'image', timeout: 5 }) }
    }
    
    stepsArray.push(newStep)
    selectNestedSubStep(parentIndex, subIndex, stepsArray.length - 1)
}

// 删除嵌套子步骤
const removeNestedSubStep = (parentIndex, subIndex, nestedIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let stepsArray = null
    if (subStep.type === 'loop') {
        stepsArray = subStep.config?.steps
    } else if (subStep.kind === 'custom') {
        stepsArray = subStep.steps
    }
    
    if (!stepsArray) return
    
    stepsArray.splice(nestedIndex, 1)
    
    if (selectedIndex.value === parentIndex && selectedSubIndex.value === subIndex && selectedNestedIndex.value === nestedIndex) {
        selectedNestedIndex.value = null
    } else if (selectedIndex.value === parentIndex && selectedSubIndex.value === subIndex && selectedNestedIndex.value > nestedIndex) {
        selectedNestedIndex.value -= 1
    }
}

// 添加嵌套 IF 分支步骤
const addNestedIfBranchStep = (parentIndex, subIndex, branchType) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep || subStep.type !== 'if') return
    
    // 复用现有的 addIfBranchStep 函数
    // 需要临时将 subStep 放入一个虚拟数组中
    const virtualSteps = [subStep]
    scenarioSteps.value[parentIndex] = subStep  // 临时替换
    
    addIfBranchStep(0, branchType, null, null, 'click')
    
    scenarioSteps.value[parentIndex] = parentStep  // 恢复
}

// 切换第三层嵌套子步骤的展开/收起
const toggleExpandNestedStep = (parentIndex, subIndex, nestedIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let nestedStep = null
    if (subStep.type === 'loop') {
        nestedStep = subStep.config?.steps?.[nestedIndex]
    } else if (subStep.kind === 'custom') {
        nestedStep = subStep.steps?.[nestedIndex]
    }
    
    if (!nestedStep) return
    
    nestedStep._expanded = !nestedStep._expanded
    
    if (!nestedStep._expanded) {
        // 收起时清除选中
        if (selectedIndex.value === parentIndex && selectedSubIndex.value === subIndex && selectedNestedIndex.value === nestedIndex) {
            // 保持选中状态，但清除更深层的选择（如果有）
        }
    } else {
        // 展开时确保子步骤的 steps 数组存在
        if (nestedStep.type === 'loop') {
            if (!nestedStep.config) nestedStep.config = {}
            if (!nestedStep.config.steps) nestedStep.config.steps = []
        } else if (nestedStep.kind === 'custom' && !nestedStep.steps) {
            nestedStep.steps = []
        }
    }
}

// 复制第三层嵌套子步骤
const duplicateNestedSubStep = (parentIndex, subIndex, nestedIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let stepsArray = null
    if (subStep.type === 'loop') {
        stepsArray = subStep.config?.steps
    } else if (subStep.kind === 'custom') {
        stepsArray = subStep.steps
    }
    
    if (!stepsArray || !stepsArray[nestedIndex]) return
    
    const originalStep = stepsArray[nestedIndex]
    const duplicatedStep = JSON.parse(JSON.stringify(originalStep))
    duplicatedStep.id = generateStepId()
    duplicatedStep._expanded = false
    
    stepsArray.splice(nestedIndex + 1, 0, duplicatedStep)
    selectNestedSubStep(parentIndex, subIndex, nestedIndex + 1)
}

// 处理第三层拖拽添加子步骤（只允许基础组件）
const handleThirdLevelSubStepAdd = (parentIndex, subIndex, nestedIndex, evt) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let nestedStep = null
    if (subStep.type === 'loop') {
        nestedStep = subStep.config?.steps?.[nestedIndex]
    } else if (subStep.kind === 'custom') {
        nestedStep = subStep.steps?.[nestedIndex]
    }
    
    if (!nestedStep) return
    
    const newIndex = evt.newIndex
    let stepsArray = null
    
    if (nestedStep.type === 'loop') {
        stepsArray = nestedStep.config?.steps
    } else if (nestedStep.kind === 'custom') {
        stepsArray = nestedStep.steps
    }
    
    if (!stepsArray || !stepsArray[newIndex]) return
    
    const addedStep = stepsArray[newIndex]
    
    // 第三层只允许基础组件，不允许控制组件
    if (addedStep.type === 'loop' || addedStep.type === 'if') {
        ElMessage.warning('第三层嵌套只支持添加基础组件，不支持控制组件')
        stepsArray.splice(newIndex, 1)
    }
}

// 添加第三层子步骤（只允许基础组件）
const addThirdLevelSubStep = (parentIndex, subIndex, nestedIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let nestedStep = null
    if (subStep.type === 'loop') {
        nestedStep = subStep.config?.steps?.[nestedIndex]
    } else if (subStep.kind === 'custom') {
        nestedStep = subStep.steps?.[nestedIndex]
    }
    
    if (!nestedStep) return
    
    let stepsArray = null
    if (nestedStep.type === 'loop') {
        if (!nestedStep.config) nestedStep.config = {}
        if (!nestedStep.config.steps) nestedStep.config.steps = []
        stepsArray = nestedStep.config.steps
    } else if (nestedStep.kind === 'custom') {
        if (!nestedStep.steps) nestedStep.steps = []
        stepsArray = nestedStep.steps
    }
    
    if (!stepsArray) return
    
    const newStep = {
        id: generateStepId(),
        type: 'click',
        name: '点击',
        config: { ...(componentDefinitions.value['click']?.default_config || { selector_type: 'image', timeout: 5 }) }
    }
    
    stepsArray.push(newStep)
    // Select the newly added third-level step
    selectThirdLevelStep(parentIndex, subIndex, nestedIndex, stepsArray.length - 1)
}

// 删除第三层子步骤
const removeThirdLevelSubStep = (parentIndex, subIndex, nestedIndex, thirdIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let nestedStep = null
    if (subStep.type === 'loop') {
        nestedStep = subStep.config?.steps?.[nestedIndex]
    } else if (subStep.kind === 'custom') {
        nestedStep = subStep.steps?.[nestedIndex]
    }
    
    if (!nestedStep) return
    
    let stepsArray = null
    if (nestedStep.type === 'loop') {
        stepsArray = nestedStep.config?.steps
    } else if (nestedStep.kind === 'custom') {
        stepsArray = nestedStep.steps
    }
    
    if (!stepsArray) return
    
    stepsArray.splice(thirdIndex, 1)
}

// 添加第三层 IF 分支步骤（只允许基础组件）
const addThirdLevelIfBranchStep = (parentIndex, subIndex, nestedIndex, branchType) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    let subStep = null
    if (parentStep.type === 'loop') {
        subStep = parentStep.config?.steps?.[subIndex]
    } else if (parentStep.kind === 'custom') {
        subStep = parentStep.steps?.[subIndex]
    }
    
    if (!subStep) return
    
    let nestedStep = null
    if (subStep.type === 'loop') {
        nestedStep = subStep.config?.steps?.[nestedIndex]
    } else if (subStep.kind === 'custom') {
        nestedStep = subStep.steps?.[nestedIndex]
    }
    
    if (!nestedStep || nestedStep.type !== 'if') return
    
    // 直接操作 nestedStep 的分支
    if (branchType === 'then') {
        if (!nestedStep.config) nestedStep.config = {}
        if (!Array.isArray(nestedStep.config.then_steps)) nestedStep.config.then_steps = []
        
        const newStep = {
            id: generateStepId(),
            type: 'click',
            name: '点击',
            config: { ...(componentDefinitions.value['click']?.default_config || { selector_type: 'image', timeout: 5 }) }
        }
        
        nestedStep.config.then_steps.push(newStep)
    }
}

const duplicateSubStep = (parentIndex, subIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    // 根据步骤类型获取子步骤数组
    let stepsArray = null
    if (parentStep.type === 'loop') {
        stepsArray = parentStep.config?.steps
    } else if (parentStep.kind === 'custom') {
        stepsArray = parentStep.steps
    }
    
    if (!stepsArray || !stepsArray[subIndex]) return
    
    const source = stepsArray[subIndex]
    const copy = JSON.parse(JSON.stringify(source))
    copy.id = generateStepId()
    copy.name = `${source.name || source.type}-复制`
    stepsArray.splice(subIndex + 1, 0, copy)
}

const removeSubStep = (parentIndex, subIndex) => {
    const parentStep = scenarioSteps.value[parentIndex]
    if (!parentStep) return
    
    // 根据步骤类型获取子步骤数组
    let stepsArray = null
    if (parentStep.type === 'loop') {
        stepsArray = parentStep.config?.steps
    } else if (parentStep.kind === 'custom') {
        stepsArray = parentStep.steps
    }
    
    if (!stepsArray) return
    
    stepsArray.splice(subIndex, 1)
    
    // 调整选中状态
    if (selectedIndex.value === parentIndex && selectedSubIndex.value === subIndex) {
        selectedSubIndex.value = null
        selectedNestedIndex.value = null
    } else if (selectedIndex.value === parentIndex && selectedSubIndex.value > subIndex) {
        selectedSubIndex.value -= 1
    }
}

// IF 组件相关方法
const addIfCondition = (index) => {
    const step = scenarioSteps.value[index]
    if (!step || step.type !== 'if') return
    ensureIfConfig(step)
    step.config.conditions_input.push({ field: '', operator: 'equals', value: '' })
}

const removeIfCondition = (index, cIdx) => {
    const step = scenarioSteps.value[index]
    if (!step || !step.config?.conditions_input) return
    if (step.config.conditions_input.length > 1) {
        step.config.conditions_input.splice(cIdx, 1)
    } else {
        ElMessage.warning('至少保留一个条件')
    }
}

const addElseIfBranch = (index) => {
    const step = scenarioSteps.value[index]
    if (!step || step.type !== 'if') return
    ensureIfConfig(step)
    if (!Array.isArray(step.config.elseif_branches)) {
        step.config.elseif_branches = []
    }
    step.config.elseif_branches.push({
        conditions_input: [{ field: '', operator: 'equals', value: '' }],
        steps: []
    })
}

const removeElseIfBranch = (index, branchIndex) => {
    const step = scenarioSteps.value[index]
    if (!step || !step.config?.elseif_branches) return
    step.config.elseif_branches.splice(branchIndex, 1)
    if (selectedIfBranchType.value === 'elseif' && selectedElseIfIndex.value === branchIndex) {
        selectedIfBranchType.value = null
        selectedElseIfIndex.value = null
    }
}

const addElseIfCondition = (index, branchIndex) => {
    const step = scenarioSteps.value[index]
    if (!step || !step.config?.elseif_branches?.[branchIndex]) return
    step.config.elseif_branches[branchIndex].conditions_input.push({ field: '', operator: 'equals', value: '' })
}

const removeElseIfCondition = (index, branchIndex, cIdx) => {
    const step = scenarioSteps.value[index]
    if (!step || !step.config?.elseif_branches?.[branchIndex]) return
    const branch = step.config.elseif_branches[branchIndex]
    if (branch.conditions_input.length > 1) {
        branch.conditions_input.splice(cIdx, 1)
    } else {
        ElMessage.warning('至少保留一个条件')
    }
}

const enableElseBranch = (index) => {
    const step = scenarioSteps.value[index]
    if (!step || step.type !== 'if') return
    ensureIfConfig(step)
    step.config.else_steps = []
}

const disableElseBranch = (index) => {
    const step = scenarioSteps.value[index]
    if (!step || step.type !== 'if') return
    if (selectedIfBranchType.value === 'else') {
        selectedIfBranchType.value = null
    }
    step.config.else_steps = null
}

const addIfBranchStep = (index, branchType, subIdx = null, branchIndex = null, stepType = 'click') => {
    const step = scenarioSteps.value[index]
    if (!step || step.type !== 'if') return
    
    // 如果是控制组件，检查嵌套层级
    if (stepType === 'loop' || stepType === 'if') {
        const check = canAddControlComponent(step, stepType)
        if (!check.allowed) {
            ElMessage.warning(check.message)
            return
        }
    }
    
    const componentDef = componentDefinitions.value[stepType]
    const newStep = {
        id: generateStepId(),
        type: stepType,
        name: componentDef?.name || stepType,
        config: { ...(componentDef?.default_config || {}) },
        _expanded: false
    }
    
    // 初始化控制组件的配置
    if (stepType === 'loop') {
        if (!newStep.config.steps) newStep.config.steps = []
    } else if (stepType === 'if') {
        ensureIfConfig(newStep)
    }
    
    if (branchType === 'then') {
        ensureIfConfig(step)
        step.config.then_steps.push(newStep)
        selectIfBranchStep(index, 'then', step.config.then_steps.length - 1)
    } else if (branchType === 'elseif' && branchIndex !== null) {
        if (step.config.elseif_branches?.[branchIndex]) {
            step.config.elseif_branches[branchIndex].steps.push(newStep)
            selectIfBranchStep(index, 'elseif', step.config.elseif_branches[branchIndex].steps.length - 1, branchIndex)
        }
    } else if (branchType === 'else') {
        ensureIfConfig(step)
        if (Array.isArray(step.config.else_steps)) {
            step.config.else_steps.push(newStep)
            selectIfBranchStep(index, 'else', step.config.else_steps.length - 1)
        }
    }
}

const duplicateIfBranchStep = (index, branchType, subIdx, branchIndex = null) => {
    const step = scenarioSteps.value[index]
    if (!step || step.type !== 'if') return
    
    let source = null
    let targetArray = null
    
    if (branchType === 'then') {
        source = step.config.then_steps?.[subIdx]
        targetArray = step.config.then_steps
    } else if (branchType === 'elseif' && branchIndex !== null) {
        source = step.config.elseif_branches?.[branchIndex]?.steps?.[subIdx]
        targetArray = step.config.elseif_branches?.[branchIndex]?.steps
    } else if (branchType === 'else') {
        source = step.config.else_steps?.[subIdx]
        targetArray = step.config.else_steps
    }
    
    if (!source || !targetArray) return
    
    const copy = JSON.parse(JSON.stringify(source))
    copy.id = generateStepId()
    copy.name = `${source.name || source.type}-复制`
    targetArray.splice(subIdx + 1, 0, copy)
}

const removeIfBranchStep = (index, branchType, subIdx, branchIndex = null) => {
    const step = scenarioSteps.value[index]
    if (!step || step.type !== 'if') return
    
    let targetArray = null
    
    if (branchType === 'then') {
        targetArray = step.config.then_steps
    } else if (branchType === 'elseif' && branchIndex !== null) {
        targetArray = step.config.elseif_branches?.[branchIndex]?.steps
    } else if (branchType === 'else') {
        targetArray = step.config.else_steps
    }
    
    if (!targetArray) return
    
    targetArray.splice(subIdx, 1)
    
    // 调整选中状态
    if (selectedIndex.value === index && selectedSubIndex.value === subIdx && selectedIfBranchType.value === branchType) {
        if (branchType === 'elseif' && selectedElseIfIndex.value === branchIndex) {
            selectedIfBranchType.value = null
            selectedElseIfIndex.value = null
        } else if (branchType !== 'elseif') {
            selectedIfBranchType.value = null
        }
    }
}

const selectIfBranchStep = (index, branchType, subIdx, branchIndex = null) => {
    selectedIndex.value = index
    selectedSubIndex.value = subIdx
    selectedIfBranchType.value = branchType
    selectedElseIfIndex.value = branchIndex
    selectedNestedIndex.value = null  // 清除嵌套层选中状态
    selectedThirdLevelIndex.value = null  // 清除第三层选中状态
    
    const parentStep = scenarioSteps.value[index]
    if (!parentStep || parentStep.type !== 'if') return
    
    let subStep = null
    if (branchType === 'then') {
        subStep = parentStep.config.then_steps?.[subIdx]
    } else if (branchType === 'elseif' && branchIndex !== null) {
        subStep = parentStep.config.elseif_branches?.[branchIndex]?.steps?.[subIdx]
    } else if (branchType === 'else') {
        subStep = parentStep.config.else_steps?.[subIdx]
    }
    
    if (subStep) {
        applyDefaultConfig(subStep)
    }
    linkedElements.value = {
        selector: null, fallback: null, click: null, ocr: null,
        start: null, end: null, target: null, expected: null
    }
}

const removeStep = (index) => {
    scenarioSteps.value.splice(index, 1)
    if (selectedIndex.value === index) {
        selectedIndex.value = null
    } else if (selectedIndex.value > index) {
        selectedIndex.value -= 1
    }
}

const duplicateStep = (index) => {
    const source = scenarioSteps.value[index]
    if (!source) {
        return
    }
    const copy = JSON.parse(JSON.stringify(source))
    copy.id = generateStepId()
    const baseName = source.name || source.type || "步骤"
    copy.name = `${baseName}-复制`
    scenarioSteps.value.splice(index + 1, 0, copy)
    selectStep(index + 1)
}

const resetScene = () => {
    sceneForm.value = {
        name: "",
        description: "",
        project: null
    }
    sceneVariables.value = []
    sceneRuntime.value = {
        base_url: "http://127.0.0.1:8000",
        retry_times: 0,
        retry_interval: 0.5
    }
    scenarioSteps.value = []
    selectedIndex.value = null
}

const openCustomComponentDialog = () => {
    if (scenarioSteps.value.length === 0) {
        ElMessage.warning(t('appAutomation.messages.selectStepsFirst'))
        return
    }
    const hasCustomStep = scenarioSteps.value.some(step => step.kind === "custom")
    if (hasCustomStep) {
        ElMessage.warning(t('appAutomation.messages.noNestedCustomComponent'))
        return
    }
    customDialogVisible.value = true
}

const resetCustomDialog = () => {
    customForm.value = {
        name: "",
        type: "",
        description: ""
    }
    customDialogMode.value = "create"
    editingCustomId.value = null
    editingCustomSteps.value = []
    editingSelectedIndex.value = null
    editStepType.value = ""
    if (customFormRef.value) {
        customFormRef.value.resetFields()
    }
}

const openEditCustomComponent = (item) => {
    customDialogMode.value = "edit"
    customDialogVisible.value = true
    editingCustomId.value = item.id
    customForm.value = {
        name: item.name || "",
        type: item.type || "",
        description: item.description || ""
    }
    const rawSteps = (item.steps && Array.isArray(item.steps))
        ? item.steps
        : (customComponentDefinitions.value[item.type] && customComponentDefinitions.value[item.type].steps) || []
    editingCustomSteps.value = JSON.parse(JSON.stringify(rawSteps)).map(step => ({
        id: step.id || generateStepId(),
        type: step.type,
        name: step.name,
        origin_name: step.origin_name || step.name || "",
        name_is_default: step.name_is_default !== undefined ? step.name_is_default : true,
        config: step.config || {}
    }))
    editingCustomSteps.value.forEach(step => applyDefaultConfig(step))
    editingSelectedIndex.value = null
}

const selectEditStep = (index) => {
    editingSelectedIndex.value = index
    const step = editingCustomSteps.value[index]
    if (step) {
        applyDefaultConfig(step)
    }
}

const addEditStep = () => {
    if (!editStepType.value) {
        ElMessage.warning(t('appAutomation.messages.selectBaseComponent'))
        return
    }
    const item = componentPalette.value.find(component => component.type === editStepType.value)
    if (!item) {
        ElMessage.warning(t('appAutomation.messages.baseComponentNotExist'))
        return
    }
    const step = {
        id: generateStepId(),
        type: item.type,
        name: getTranslatedComponentName(item.type) || item.name,
        origin_name: item.name || "",
        name_is_default: true,
        config: {
            ...item.defaultConfig
        }
    }
    editingCustomSteps.value.push(step)
    editingSelectedIndex.value = editingCustomSteps.value.length - 1
}

const removeEditStep = (index) => {
    editingCustomSteps.value.splice(index, 1)
    if (editingSelectedIndex.value === index) {
        editingSelectedIndex.value = null
    } else if (editingSelectedIndex.value > index) {
        editingSelectedIndex.value -= 1
    }
}

const duplicateEditStep = (index) => {
    const source = editingCustomSteps.value[index]
    if (!source) {
        return
    }
    const copy = JSON.parse(JSON.stringify(source))
    copy.id = generateStepId()
    const baseName = source.name || source.type || "步骤"
    copy.name = `${baseName}-复制`
    editingCustomSteps.value.splice(index + 1, 0, copy)
    editingSelectedIndex.value = index + 1
}

const deleteCustomComponent = async (item) => {
    try {
        await ElMessageBox.confirm(t('appAutomation.messages.deleteCustomComponentConfirm', { name: item.name }), t('appAutomation.messages.tip'), {
            confirmButtonText: t('appAutomation.messages.confirm'),
            cancelButtonText: t('appAutomation.messages.cancel'),
            type: "warning"
        })
    } catch (error) {
        return
    }
    try {
        await apiDeleteCustomComponent(item.id)
        ElMessage.success(t('appAutomation.messages.deleteSuccess'))
        customComponentPalette.value = customComponentPalette.value.filter(
            component => component.id !== item.id
        )
        await loadCustomComponentPalette()
        paletteTab.value = "custom"
    } catch (error) {
        console.error("删除自定义组件失败:", error)
        ElMessage.error(t('appAutomation.messages.deleteFailed'))
    }
}

const saveCustomComponent = () => {
    customFormRef.value.validate(async valid => {
        if (!valid) {
            return
        }
        if (customDialogMode.value === "create" && scenarioSteps.value.length === 0) {
            ElMessage.warning(t('appAutomation.messages.addSceneStepsFirst'))
            return
        }
        if (customDialogMode.value === "edit" && editingCustomSteps.value.length === 0) {
            ElMessage.warning(t('appAutomation.messages.addComponentStepsFirst'))
            return
        }
        customSaving.value = true
        try {
            const steps = (customDialogMode.value === "edit"
                ? editingCustomSteps.value
                : scenarioSteps.value
            ).map(step => ({
                type: step.type,
                name: step.name,
                config: step.config || {}
            }))
            const payload = {
                name: customForm.value.name,
                type: customForm.value.type,
                description: customForm.value.description || ""
            }
            if (customDialogMode.value === "create") {
                payload.schema = {}
                payload.default_config = {}
                payload.steps = steps
                payload.enabled = true
                payload.sort_order = 0
            } else {
                payload.steps = steps
            }

            const response = customDialogMode.value === "edit"
                ? await apiUpdateCustomComponent(editingCustomId.value, payload)
                : await apiCreateCustomComponent(payload)
            const data = response?.data || response
            if (data && (data.success || data.id)) {
                ElMessage.success(customDialogMode.value === "edit" ? t('appAutomation.messages.customComponentUpdated') : t('appAutomation.messages.customComponentSaved'))
                customDialogVisible.value = false
                await loadCustomComponentPalette()
                paletteTab.value = "custom"
            } else {
                ElMessage.error(response.data?.message || t('appAutomation.messages.saveFailed'))
            }
        } catch (error) {
            console.error("保存自定义组件失败:", error)
            const errorMsg = (error.response && error.response.data && error.response.data.msg) || error.message
            ElMessage.error(`${t('appAutomation.messages.saveFailed')}: ${errorMsg}`)
        } finally {
            customSaving.value = false
        }
    })
}

const loadComponentPalette = async () => {
    try {
        const response = await getComponents({ enabled: 1 })

        const list = response.data?.data || response.data || []

        if (list.length > 0) {
            const mergedList = list.map(item => ({
                type: item.type,
                name: item.name,
                category: item.category || '',
                schema: item.schema || {},
                defaultConfig: item.default_config || {},
                raw: item
            }))
            componentPalette.value = mergedList.map(item => ({
                type: item.type || '',
                name: item.name || '',
                category: item.category || '',
                schema: item.schema || {},
                defaultConfig: item.defaultConfig || {}
            })).filter(item => item.type)
            componentDefinitions.value = mergedList.reduce((acc, item) => {
                acc[item.type] = {
                    ...item.raw,
                    schema: item.schema,
                    default_config: item.defaultConfig
                }
                return acc
            }, {})
        } else {
            componentPalette.value = []
            componentDefinitions.value = {}
            ElMessage.warning(t('appAutomation.messages.initComponentsHint'))
        }
    } catch (error) {
        console.error("加载组件库失败:", error)
        ElMessage.error(t('appAutomation.messages.loadComponentsFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
        componentPalette.value = []
        componentDefinitions.value = {}
    }
}

const loadCustomComponentPalette = async () => {
    defaultCustomPalette.value = JSON.parse(JSON.stringify(customComponentPalette.value))
    try {
        const response = await getCustomComponents({ enabled: 1 })

        const list = response.data?.data || response.data || []

        if (list.length > 0) {
            customComponentPalette.value = list.map(item => ({
                id: item.id || `custom_${item.type}_${Date.now()}_${Math.random()}`,
                type: item.type || '',
                name: item.name || '',
                kind: "custom",
                category: item.category || '',
                schema: item.schema || {},
                defaultConfig: item.default_config || {},
                steps: item.steps || []
            })).filter(item => item.id && item.type)
            customComponentDefinitions.value = list.reduce((acc, item) => {
                acc[item.type] = item
                return acc
            }, {})
        } else {
            customComponentPalette.value = defaultCustomPalette.value.map(item => ({
                ...item,
                id: item.id || `custom_${item.type}_${Date.now()}_${Math.random()}`
            })).filter(item => item.id && item.type)
            customComponentDefinitions.value = customComponentPalette.value.reduce((acc, item) => {
                if (item && item.type) {
                    acc[item.type] = item
                }
                return acc
            }, {})
        }
    } catch (error) {
        console.error("加载自定义组件库失败:", error)
        customComponentPalette.value = defaultCustomPalette.value.map(item => ({
            ...item,
            id: item.id || `custom_${item.type}_${Date.now()}_${Math.random()}`
        })).filter(item => item.id && item.type)
        customComponentDefinitions.value = customComponentPalette.value.reduce((acc, item) => {
            if (item && item.type) {
                acc[item.type] = item
            }
            return acc
        }, {})
    }
}

const loadCaseDetail = async (caseId) => {
    try {
        const response = await getTestCaseDetail(caseId)
        const data = response.data || response
        if (data && data.id) {
            sceneForm.value.name = data.name || ""
            sceneForm.value.description = data.description || ""
            sceneForm.value.project = data.project || null
            loadSceneVariables(data.variables || [])
            sceneRuntime.value = {
                base_url: data.runtime?.base_url || "http://127.0.0.1:8000",
                retry_times: data.runtime?.retry_times || 0,
                retry_interval: data.runtime?.retry_interval || 0.5
            }
            scenarioSteps.value = (Array.isArray(data.ui_flow) ? data.ui_flow : []).map(step => {
                const clonedStep = JSON.parse(JSON.stringify(step))
                clonedStep._expanded = false
                applyStepDefaultsDeep(clonedStep)
                return clonedStep
            })
            selectedStepPath.value = null
            clearLegacySelectionState()
            resetLinkedElements()
        }
    } catch (error) {
        console.error("??????:", error)
        ElMessage.error(t('appAutomation.messages.loadCaseFailed'))
    }
}

const applyDefaultConfig = (step) => {
    if (!step || !step.config) {
        return
    }
    const def = step.kind === "custom"
        ? customComponentDefinitions.value[step.type]
        : componentDefinitions.value[step.type]
    if (!def || !def.default_config) {
        return
    }
    const defaults = def.default_config
    Object.keys(defaults).forEach(key => {
        if (step.config[key] === undefined) {
            step.config[key] = defaults[key]
        }
    })
}

// 字段分组辅助函数（通用：支持场景步骤和自定义组件编辑）
const getFieldGroups = (fieldsOverride = null) => {
    const groups = []
    const allFields = fieldsOverride || schemaFields.value
    if (!allFields || allFields.length === 0) return []
    const usedFields = new Set()

    // 定义字段组规则
    const groupRules = [
        {
            key: 'selector',
            title: '定位',
            fields: ['selector_type', 'selector', 'image_scope', 'image_threshold'],
            hasFields: () => allFields.includes('selector_type')
        },
        {
            key: 'fallback',
            title: '备用定位',
            fields: ['fallback_selector_type', 'fallback_selector', 'fallback_image_scope', 'fallback_image_threshold'],
            hasFields: () => allFields.includes('fallback_selector_type')
        },
        {
            key: 'click',
            title: '点击定位',
            fields: ['click_selector_type', 'click_selector', 'image_scope', 'image_threshold'],
            hasFields: () => allFields.includes('click_selector_type')
        },
        {
            key: 'ocr',
            title: 'OCR定位',
            fields: ['ocr_selector_type', 'ocr_selector'],
            hasFields: () => allFields.includes('ocr_selector_type')
        },
        {
            key: 'start',
            title: '起始定位',
            fields: ['start_selector_type', 'start_selector', 'image_scope', 'image_threshold'],
            hasFields: () => allFields.includes('start_selector_type')
        },
        {
            key: 'end',
            title: '结束定位',
            fields: ['end_selector_type', 'end_selector', 'image_scope', 'image_threshold'],
            hasFields: () => allFields.includes('end_selector_type')
        },
        {
            key: 'target',
            title: '目标定位',
            fields: ['target_selector_type', 'target_selector', 'image_scope', 'image_threshold'],
            hasFields: () => allFields.includes('target_selector_type')
        },
        {
            key: 'expected',
            title: '断言配置',
            fields: ['assert_type', 'expected', 'expected_list', 'expected_image_scope', 'match_mode'],
            hasFields: () => allFields.includes('assert_type') || allFields.includes('expected')
        }
    ]

    // 检测每个组是否存在
    groupRules.forEach(rule => {
        if (rule.hasFields()) {
            const groupFields = rule.fields.filter(f => allFields.includes(f))
            if (groupFields.length > 0) {
                groups.push({
                    key: rule.key,
                    title: rule.title,
                    fields: groupFields
                })
                groupFields.forEach(f => usedFields.add(f))
            }
        }
    })

    // 其他字段
    const otherFields = allFields.filter(f => !usedFields.has(f))
    if (otherFields.length > 0) {
        // 计算定位类分组的数量（排除 'other'）
        const selectorGroupCount = groups.length

        // 如果没有定位类分组，标题为"配置"；否则为"其他配置"
        const otherTitle = selectorGroupCount === 0 ? '配置' : '其他配置'

        groups.push({
            key: 'other',
            title: otherTitle,
            fields: otherFields
        })
    }

    return groups
}

const getEditingFieldGroups = () => {
    return getFieldGroups(editingSchemaFields.value)
}

const getFieldLabel = (field) => {
    const labels = {
        selector_type: "定位方式",
        selector: "定位值",
        fallback_selector_type: "备用定位方式",
        fallback_selector: "备用定位值",
        fallback_image_scope: "备用图片路径",
        fallback_image_threshold: "备用图片匹配阈值",
        value: "输入内容",
        direction: "滑动方向",
        timeout: "超时时间",
        expected: "断言文本",
        assert_type: "断言类型",
        expected_exists: "断言存在",
        duration: "耗时",
        image_scope: "图片路径",
        expected_image_scope: "期望图片路径",
        image_threshold: "图片匹配阈值",
        expected_list: "期望列表",
        click_selector_type: "点击定位方式",
        click_selector: "点击定位值",
        ocr_selector_type: "OCR定位方式",
        ocr_selector: "OCR定位值",
        start_selector_type: "起点定位方式",
        start_selector: "起点定位值",
        end_selector_type: "终点定位方式",
        end_selector: "终点定位值",
        target_selector_type: "目标定位方式",
        target_selector: "目标定位值",
        max_swipes: "最大次数",
        interval: "间隔(秒)",
        max_loops: "循环次数",
        note: "备注",
        match_mode: "匹配模式",
        name: "变量名",
        value_type: "变量类型",
        scope: "作用域",
        source: "来源",
        path: "提取路径",
        method: "请求方法",
        url: "请求地址",
        headers: "请求头",
        params: "查询参数",
        data: "请求体(data)",
        json: "请求体(json)",
        expected_status: "期望状态码",
        response_type: "响应类型",
        save_as: "保存为变量",
        extracts: "批量提取",
        left: "条件左值",
        operator: "条件运算",
        right: "条件右值",
        then_steps: "条件为真步骤",
        else_steps: "条件为假步骤",
        mode: "循环模式",
        times: "循环次数",
        items: "遍历列表",
        item_var: "遍历变量名",
        item_scope: "遍历变量域",
        steps: "子步骤列表",
        branches: "并行分支",
        merge_strategy: "合并策略",
        try_steps: "Try步骤",
        catch_steps: "Catch步骤",
        finally_steps: "Finally步骤",
        error_var: "错误变量名",
        error_scope: "错误变量域",
        min: "最小值",
        max: "最大值",
        retry_times: "重试次数",
        retry_interval: "重试间隔(秒)",
        key_event: "按键",
        repeat: "重复次数"
    }
    const config = getActiveConfigForField()
    const currentStep = activeStep.value || editingActiveStep.value
    if (field === "value" && currentStep && currentStep.type === "set_variable") {
        return "变量值"
    }
    if (config && config.assert_type === "image") {
        if (field === "expected") {
            return "期望图片"
        }
        if (field === "expected_list") {
            return "期望图片列表"
        }
    }
    return labels[field] || field
}

const getFieldPlaceholder = (field) => {
    const config = getActiveConfigForField()

    // 动态占位符：根据定位方式返回不同提示
    const getDynamicPlaceholder = (selectorField, typeField) => {
        if (!config) return null
        const type = config[typeField] || 'image'
        if (type === 'image') return 'image: 文件名'
        if (type === 'pos') return 'pos: x,y'
        if (type === 'region') return 'region: x1,y1,x2,y2'
        return null
    }

    if (field === 'selector') {
        return getDynamicPlaceholder('selector', 'selector_type') || "image: 文件名 | pos: x,y | region: x1,y1,x2,y2"
    }
    if (field === 'fallback_selector') {
        return getDynamicPlaceholder('fallback_selector', 'fallback_selector_type') || "image: 文件名 | pos: x,y | region: x1,y1,x2,y2"
    }
    if (field === 'click_selector') {
        return getDynamicPlaceholder('click_selector', 'click_selector_type') || "image: 文件名 | pos: x,y"
    }
    if (field === 'start_selector') {
        return getDynamicPlaceholder('start_selector', 'start_selector_type') || "image: 文件名 | pos: x,y"
    }
    if (field === 'end_selector') {
        return getDynamicPlaceholder('end_selector', 'end_selector_type') || "image: 文件名 | pos: x,y"
    }
    if (field === 'target_selector') {
        return getDynamicPlaceholder('target_selector', 'target_selector_type') || "image: 文件名"
    }
    if (field === 'ocr_selector') {
        return getDynamicPlaceholder('ocr_selector', 'ocr_selector_type') || "region: x1,y1,x2,y2 | pos: x,y"
    }

    const placeholders = {
        selector: "image: 文件名 | pos: x,y | region: x1,y1,x2,y2",
        fallback_selector: "image: 文件名 | pos: x,y | region: x1,y1,x2,y2",
        start_selector: "image: 文件名 | pos: x,y",
        end_selector: "image: 文件名 | pos: x,y",
        target_selector: "image: 文件名",
        click_selector: "image: 文件名 | pos: x,y",
        ocr_selector: "region: x1,y1,x2,y2 | pos: x,y",
        value: "请输入内容",
        expected: "期望文本，如是数字匹配：格式为1,000,000",
        note: "备注",
        image_scope: "图片目录名（位于 Template/ 下），默认 common 或输入自定义目录名",
        expected_image_scope: "图片目录名（位于 Template/ 下），默认 common 或输入自定义目录名",
        fallback_image_scope: "图片目录名（位于 Template/ 下），默认 common 或输入自定义目录名",
        image_threshold: "0.7 ~ 1.0",
        fallback_image_threshold: "0.7 ~ 1.0",
        expected_list: "例如 100,200,300 或多行",
        name: "例如 token 或 user.id",
        value_type: "string/number/boolean/array/object",
        scope: "local 或 global",
        source: "例如 outputs.last 或 steps.step_id",
        path: "例如 data.id",
        method: "GET/POST/PUT/PATCH/DELETE",
        url: "例如 https://api.example.com/login",
        headers: "JSON 对象，如 {\"Authorization\": \"Bearer ...\"}",
        params: "JSON 对象，如 {\"page\":1}",
        data: "JSON 对象或字符串",
        json: "JSON 对象",
        expected_status: "例如 200",
        response_type: "auto/json/text",
        save_as: "变量名，如 login_response",
        extracts: "[{\"name\":\"token\",\"path\":\"data.token\"}]",
        left: "支持变量表达式",
        operator: "== != > >= < <= contains regex truthy",
        right: "支持变量表达式",
        items: "JSON 数组，如 [\"a\",\"b\"]",
        item_var: "默认 item",
        item_scope: "local 或 global",
        steps: "JSON 数组，填入子步骤",
        then_steps: "JSON 数组，填入子步骤",
        else_steps: "JSON 数组，填入子步骤",
        branches: "JSON 数组，形如 [[...],[...]]",
        try_steps: "JSON 数组，填入子步骤",
        catch_steps: "JSON 数组，填入子步骤",
        finally_steps: "JSON 数组，填入子步骤",
        key_event: "按键,如 backspace,enter,delete,home,end,back",
        repeat: "重复次数"
    }
    const currentStep = activeStep.value || editingActiveStep.value
    if (field === "value" && currentStep && currentStep.type === "set_variable") {
        return "支持变量表达式或字面量"
    }
    if (config && config.assert_type === "image") {
        if (field === "expected") {
            return "例如 upgrade_button.png"
        }
        if (field === "expected_list") {
            return "例如 a.png,b.png 或多行"
        }
    }
    return placeholders[field] || ""
}

const applyApiRequestTemplate = (template, targetStep) => {
    const step = targetStep || activeStep.value || editingActiveStep.value
    if (!step || !step.config) {
        ElMessage.warning(t('appAutomation.messages.selectStepFirst'))
        return
    }
    const config = template && template.config
        ? JSON.parse(JSON.stringify(template.config))
        : {}
    Object.keys(config).forEach(key => {
        step.config[key] = config[key]
    })
    ElMessage.success(t('appAutomation.messages.templateApplied', { name: template.name }))
}

// 判断是否是图片分类相关字段
const isImageScopeField = (field) => {
    return ['image_scope', 'expected_image_scope', 'fallback_image_scope'].includes(field)
}

const getFieldType = (field) => {
    if (!activeComponentDef.value || !activeComponentDef.value.schema) {
        return "string"
    }
    const properties = activeComponentDef.value.schema.properties || {}
    return properties[field] && properties[field].type ? properties[field].type : "string"
}

const getFieldTypeForDef = (def, field) => {
    if (!def || !def.schema) {
        return "string"
    }
    const properties = def.schema.properties || {}
    return properties[field] && properties[field].type ? properties[field].type : "string"
}

const getFieldOptions = (field) => {
    const optionsMap = {
        image_scope: imageCategoryOptions.value,  // 动态加载的图片分类选项
        expected_image_scope: imageCategoryOptions.value,  // 动态加载的图片分类选项
        fallback_image_scope: imageCategoryOptions.value,  // 动态加载的图片分类选项
        selector_type: [
            { label: "image", value: "image" },
            { label: "pos", value: "pos" },
            { label: "region", value: "region" },
            { label: "text", value: "text" }
        ],
        fallback_selector_type: [
            { label: "image", value: "image" },
            { label: "pos", value: "pos" },
            { label: "region", value: "region" }
        ],
        assert_type: [
            { label: "number", value: "number" },
            { label: "text", value: "text" },
            { label: "regex", value: "regex" },
            { label: "range", value: "range" },
            { label: "exists", value: "exists" },
            { label: "image", value: "image" }
        ],
        start_selector_type: [
            { label: "image", value: "image" },
            { label: "pos", value: "pos" }
        ],
        end_selector_type: [
            { label: "image", value: "image" },
            { label: "pos", value: "pos" }
        ],
        target_selector_type: [
            { label: "image", value: "image" }
        ],
        click_selector_type: [
            { label: "image", value: "image" },
            { label: "pos", value: "pos" }
        ],
        ocr_selector_type: [
            { label: "region", value: "region" },
            { label: "pos", value: "pos" }
        ],
        direction: [
            { label: "up", value: "up" },
            { label: "down", value: "down" },
            { label: "left", value: "left" },
            { label: "right", value: "right" }
        ],
        match_mode: [
            { label: "contains", value: "contains" },
            { label: "exact", value: "exact" }
        ],
        operator: [
            { label: "==", value: "==" },
            { label: "!=", value: "!=" },
            { label: ">", value: ">" },
            { label: ">=", value: ">=" },
            { label: "<", value: "<" },
            { label: "<=", value: "<=" },
            { label: "contains", value: "contains" },
            { label: "regex", value: "regex" },
            { label: "truthy", value: "truthy" },
            { label: "falsy", value: "falsy" }
        ],
        scope: [
            { label: "local", value: "local" },
            { label: "global", value: "global" }
        ],
        item_scope: [
            { label: "local", value: "local" },
            { label: "global", value: "global" }
        ],
        error_scope: [
            { label: "local", value: "local" },
            { label: "global", value: "global" }
        ],
        value_type: [
            { label: "string", value: "string" },
            { label: "number", value: "number" },
            { label: "boolean", value: "boolean" },
            { label: "array", value: "array" },
            { label: "object", value: "object" }
        ],
        mode: [
            { label: "count", value: "count" },
            { label: "condition", value: "condition" },
            { label: "foreach", value: "foreach" }
        ],
        method: [
            { label: "GET", value: "GET" },
            { label: "POST", value: "POST" },
            { label: "PUT", value: "PUT" },
            { label: "PATCH", value: "PATCH" },
            { label: "DELETE", value: "DELETE" }
        ],
        response_type: [
            { label: "auto", value: "auto" },
            { label: "json", value: "json" },
            { label: "text", value: "text" }
        ],
        merge_strategy: [
            { label: "last", value: "last" },
            { label: "first", value: "first" }
        ],
        key_event: [
            { label: "backspace", value: "backspace" },
            { label: "enter", value: "enter" },
            { label: "delete", value: "delete" },
            { label: "home", value: "home" },
            { label: "back", value: "back" }
        ]
    }
    if (field === "assert_type") {
        const currentStep = activeStep.value || editingActiveStep.value
        if (currentStep && currentStep.type === "foreach_assert") {
            return [
                { label: "number", value: "number" },
                { label: "text", value: "text" },
                { label: "image", value: "image" }
            ]
        }
    }
    const currentStep = activeStep.value || editingActiveStep.value
    if (field === "match_mode" && currentStep && currentStep.config) {
        if (currentStep.config.assert_type === "number") {
            return [{ label: "exact", value: "exact" }]
        }
    }
    return optionsMap[field] || []
}

const getFieldOrder = (fields) => {
    const baseOrder = [
        "expected_list",
        "expected",
        "assert_type",
        "match_mode",
        "min",
        "max",
        "click_selector_type",
        "image_scope",
        "image_threshold",
        "click_selector",
        "ocr_selector_type",
        "ocr_selector",
        "max_loops",
        "interval",
        "selector_type",
        "selector",
        "value",
        "direction",
        "duration",
        "expected_exists",
        "start_selector_type",
        "start_selector",
        "end_selector_type",
        "end_selector",
        "target_selector_type",
        "target_selector",
        "max_swipes",
        "note",
        "name",
        "value_type",
        "scope",
        "source",
        "path",
        "method",
        "url",
        "headers",
        "params",
        "data",
        "json",
        "expected_status",
        "response_type",
        "save_as",
        "extracts",
        "left",
        "operator",
        "right",
        "then_steps",
        "else_steps",
        "mode",
        "times",
        "items",
        "item_var",
        "item_scope",
        "steps",
        "branches",
        "merge_strategy",
        "try_steps",
        "catch_steps",
        "finally_steps",
        "error_var",
        "error_scope",
        "retry_times",
        "retry_interval",
        "timeout"
    ]
    const orderIndex = baseOrder.reduce((acc, item, index) => {
        acc[item] = index
        return acc
    }, {})
    const currentStep = activeStep.value || editingActiveStep.value
    let ordered = [...fields].sort((a, b) => {
        const aIndex = orderIndex[a] !== undefined ? orderIndex[a] : 999
        const bIndex = orderIndex[b] !== undefined ? orderIndex[b] : 999
        return aIndex - bIndex
    })
    if (currentStep && currentStep.type === "foreach_assert") {
        const assertType = currentStep.config && currentStep.config.assert_type
        if (assertType === "image") {
            if (ordered.includes("expected_image_scope")) {
                ordered = ordered.filter(item => item !== "expected_image_scope")
                const expectedIndex = ordered.indexOf("expected_list")
                if (expectedIndex >= 0) {
                    ordered.splice(expectedIndex + 1, 0, "expected_image_scope")
                } else {
                    ordered.unshift("expected_image_scope")
                }
            }
        } else {
            ordered = ordered.filter(item => item !== "expected_image_scope")
        }
    }
    if (currentStep && (currentStep.type === "image_exists_click" || currentStep.type === "image_exists_click_chain")) {
        const timeoutIndex = ordered.indexOf("timeout")
        const imageFields = [
            "image_threshold"
        ]
        ordered = ordered.filter(item => !imageFields.includes(item))
        ordered = [
            ...imageFields.filter(item => fields.includes(item)),
            ...ordered
        ]
        if (timeoutIndex >= 0) {
            ordered = ordered.filter(item => item !== "timeout")
            ordered.push("timeout")
        }
    }
    return ordered
}

const getFieldNumberRule = (field) => {
    const rules = {
        timeout: { min: 1, max: 60, step: 1 },
        duration: { min: 0.1, max: 5, step: 0.1 },
        interval: { min: 0.1, max: 5, step: 0.1 },
        max_swipes: { min: 1, max: 20, step: 1 },
        max_loops: { min: 1, max: 50, step: 1 },
        times: { min: 1, max: 100, step: 1 },
        min: { min: -999999, max: 999999, step: 1 },
        max: { min: -999999, max: 999999, step: 1 },
        retry_times: { min: 0, max: 10, step: 1 },
        retry_interval: { min: 0.1, max: 10, step: 0.1 },
        expected_status: { min: 100, max: 600, step: 1 },
        image_threshold: { min: 0.1, max: 1, step: 0.01 }
    }
    return rules[field] || { min: 0, max: 999, step: 1 }
}

const getFieldNumberRuleForDef = (def, field) => {
    if (!def || !def.schema) {
        return getFieldNumberRule(field)
    }
    return getFieldNumberRule(field)
}

const openPackageDialog = async () => {
    packageDialogVisible.value = true
    await loadPackageList()
}

const resetPackageDialog = () => {
    packageUploading.value = false
    packageLoading.value = false
    packageList.value = []
}

const openExportDialog = () => {
    exportDialogVisible.value = true
}

const resetExportDialog = () => {
    exportDialogVisible.value = false
}

const openCaptureElementDialog = () => {
    captureElementDialogVisible.value = true
}

const handleElementCreated = () => {
    ElMessage.success(t('appAutomation.messages.elementCreateSuccess'))
    // 如果元素选择器对话框打开，可以刷新元素列表
    if (elementSelectorVisible.value) {
        loadElementsForSelector()
    }
}

const loadPackageList = async () => {
    packageLoading.value = true
    try {
        // 组件包列表暂不显示历史记录，仅保留导入功能
        packageList.value = []
    } catch (error) {
        console.error("加载组件包失败:", error)
        packageList.value = []
    } finally {
        packageLoading.value = false
    }
}

const handlePackageUpload = async (option) => {
    if (!option || !option.file) {
        return
    }
    packageUploading.value = true
    try {
        const formData = new FormData()
        formData.append("file", option.file)
        formData.append("overwrite", packageOverwrite.value ? "1" : "0")
        const response = await importComponentPackage(formData)
        const data = response.data || response
        if (data.success || data.data) {
            ElMessage.success(t('appAutomation.messages.componentPackageImported'))
            await loadComponentPalette()
            await loadPackageList()
        } else {
            ElMessage.error(data.message || t('appAutomation.messages.importFailed'))
        }
    } catch (error) {
        console.error("导入组件包失败:", error)
        const errorMsg = (error.response && error.response.data && error.response.data.msg) || error.message
        ElMessage.error(errorMsg || t('appAutomation.messages.importFailed'))
    } finally {
        packageUploading.value = false
    }
}

const exportPackage = async (format) => {
    try {
        const response = await exportComponentPackage({
            export_format: format || "yaml",
            include_disabled: packageIncludeDisabled.value ? 1 : 0
        })
        const blob = new Blob([response.data], { type: response.headers["content-type"] || "application/octet-stream" })
        const filename = getDownloadFilename(response.headers["content-disposition"])
            || `ui-component-pack.${format === "json" ? "json" : "yaml"}`
        downloadBlob(blob, filename)
        ElMessage.success(t('appAutomation.messages.componentPackageExported'))
        exportDialogVisible.value = false
    } catch (error) {
        console.error("导出组件包失败:", error)
        const errorMsg = (error.response && error.response.data && error.response.data.msg) || error.message
        ElMessage.error(errorMsg || t('appAutomation.messages.exportFailed'))
    }
}

const getDownloadFilename = (contentDisposition) => {
    if (!contentDisposition) {
        return ""
    }
    const match = /filename="?([^"]+)"?/i.exec(contentDisposition)
    if (match && match[1]) {
        return decodeURIComponent(match[1])
    }
    return ""
}

const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
}


const SELECTOR_VALIDATION_GROUPS = [
    { typeField: 'selector_type', valueField: 'selector', elementIdField: 'element_id', label: '\u4e3b\u5b9a\u4f4d\u5143\u7d20' },
    { typeField: 'fallback_selector_type', valueField: 'fallback_selector', elementIdField: 'fallback_element_id', label: '\u5907\u7528\u5b9a\u4f4d\u5143\u7d20' },
    { typeField: 'click_selector_type', valueField: 'click_selector', elementIdField: 'click_element_id', label: '\u70b9\u51fb\u5b9a\u4f4d\u5143\u7d20' },
    { typeField: 'ocr_selector_type', valueField: 'ocr_selector', elementIdField: 'ocr_element_id', label: 'OCR\u5b9a\u4f4d\u5143\u7d20' },
    { typeField: 'start_selector_type', valueField: 'start_selector', elementIdField: 'start_element_id', label: '\u8d77\u70b9\u5143\u7d20' },
    { typeField: 'end_selector_type', valueField: 'end_selector', elementIdField: 'end_element_id', label: '\u7ec8\u70b9\u5143\u7d20' },
    { typeField: 'target_selector_type', valueField: 'target_selector', elementIdField: 'target_element_id', label: '\u76ee\u6807\u5143\u7d20' }
]

const getStepDisplayName = (step) => {
    if (!step || typeof step !== 'object') {
        return '\u672a\u547d\u540d\u6b65\u9aa4'
    }
    return step.name || step.title || step.label || step.type || '\u672a\u547d\u540d\u6b65\u9aa4'
}

const hasFilledValue = (value) => {
    if (Array.isArray(value)) {
        return value.length > 0
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
        return true
    }
    return String(value ?? '').trim() !== ''
}

const isConditionComplete = (condition) => {
    if (!condition || typeof condition !== 'object') {
        return false
    }

    const field = String(condition.field ?? condition.left ?? '').trim()
    const operator = String(condition.operator ?? '').trim()
    const value = condition.value ?? condition.right ?? ''

    if (!field || !operator) {
        return false
    }

    if (operator === 'truthy' || operator === 'falsy') {
        return true
    }

    return hasFilledValue(value)
}

const validateConditionList = (conditions, branchLabel) => {
    if (!Array.isArray(conditions) || conditions.length === 0) {
        return `${branchLabel}\u7f3a\u5c11\u6761\u4ef6`
    }

    for (let index = 0; index < conditions.length; index += 1) {
        if (!isConditionComplete(conditions[index])) {
            return `${branchLabel}\u7684\u7b2c ${index + 1} \u4e2a\u6761\u4ef6\u672a\u586b\u5199\u5b8c\u6574`
        }
    }

    return null
}

const validateSelectorBindings = (step, stepPath) => {
    const config = step?.config
    if (!config || typeof config !== 'object') {
        return null
    }

    for (const group of SELECTOR_VALIDATION_GROUPS) {
        const hasRelatedField = [group.typeField, group.valueField, group.elementIdField]
            .some(field => Object.prototype.hasOwnProperty.call(config, field))

        if (!hasRelatedField) {
            continue
        }

        const selectorType = config[group.typeField]
        const elementId = config[group.elementIdField]
        const selectorValue = config[group.valueField]
        const hasElementId = hasFilledValue(elementId)
        const hasSelectorValue = hasFilledValue(selectorValue)

        if (!hasFilledValue(selectorType)) {
            return `${stepPath} \u7684${group.label}\u7f3a\u5c11\u5b9a\u4f4d\u65b9\u5f0f`
        }

        if (!hasElementId && !hasSelectorValue) {
            return `${stepPath} \u7684${group.label}\u672a\u7ed1\u5b9a\u5143\u7d20`
        }
    }

    return null
}

const validateStepTree = (steps, ancestors = []) => {
    if (!Array.isArray(steps)) {
        return null
    }

    for (const step of steps) {
        if (!step || typeof step !== 'object') {
            continue
        }

        ensureStepContainers(step)

        const stepLabel = getStepDisplayName(step)
        const stepPath = [...ancestors, stepLabel].join(' > ')

        if (getControlMaxDepth(step, 0) > MAX_CONTROL_NESTING) {
            return `${stepPath} \u7684\u63a7\u5236\u6d41\u5d4c\u5957\u8d85\u8fc7 ${MAX_CONTROL_NESTING} \u5c42\uff0c\u65e0\u6cd5\u4fdd\u5b58`
        }

        const selectorError = validateSelectorBindings(step, stepPath)
        if (selectorError) {
            return selectorError
        }

        if (step.type === 'if') {
            const ifConditionError = validateConditionList(step.config?.conditions_input, `${stepPath} \u7684 IF \u6761\u4ef6`)
            if (ifConditionError) {
                return ifConditionError
            }

            if (!Array.isArray(step.config?.then_steps) || step.config.then_steps.length === 0) {
                return `${stepPath} \u7684 IF \u5206\u652f\u4e0d\u80fd\u4e3a\u7a7a`
            }

            const thenError = validateStepTree(step.config.then_steps, [...ancestors, stepLabel, 'IF'])
            if (thenError) {
                return thenError
            }

            const elseIfBranches = Array.isArray(step.config?.elseif_branches) ? step.config.elseif_branches : []
            for (let branchIndex = 0; branchIndex < elseIfBranches.length; branchIndex += 1) {
                const branch = elseIfBranches[branchIndex]
                const branchLabel = `${stepPath} \u7684 Else If ${branchIndex + 1} \u5206\u652f`
                const branchConditionError = validateConditionList(branch?.conditions_input, `${branchLabel}\u6761\u4ef6`)
                if (branchConditionError) {
                    return branchConditionError
                }

                if (!Array.isArray(branch?.steps) || branch.steps.length === 0) {
                    return `${branchLabel}\u4e0d\u80fd\u4e3a\u7a7a`
                }

                const branchError = validateStepTree(branch.steps, [...ancestors, stepLabel, `Else If ${branchIndex + 1}`])
                if (branchError) {
                    return branchError
                }
            }

            if (Array.isArray(step.config?.else_steps)) {
                if (step.config.else_steps.length === 0) {
                    return `${stepPath} \u7684 Else \u5206\u652f\u4e0d\u80fd\u4e3a\u7a7a`
                }

                const elseError = validateStepTree(step.config.else_steps, [...ancestors, stepLabel, 'Else'])
                if (elseError) {
                    return elseError
                }
            }

            continue
        }

        if (step.type === 'loop' || step.type === 'sequence') {
            if (!Array.isArray(step.config?.steps) || step.config.steps.length === 0) {
                return `${stepPath} \u7684\u5b50\u6b65\u9aa4\u4e0d\u80fd\u4e3a\u7a7a`
            }

            const childError = validateStepTree(step.config.steps, [...ancestors, stepLabel])
            if (childError) {
                return childError
            }

            continue
        }

        if (step.type === 'try') {
            if (!Array.isArray(step.config?.try_steps) || step.config.try_steps.length === 0) {
                return `${stepPath} \u7684 Try \u5206\u652f\u4e0d\u80fd\u4e3a\u7a7a`
            }

            const tryError = validateStepTree(step.config.try_steps, [...ancestors, stepLabel, 'Try'])
            if (tryError) {
                return tryError
            }

            if (Array.isArray(step.config?.catch_steps) && step.config.catch_steps.length > 0) {
                const catchError = validateStepTree(step.config.catch_steps, [...ancestors, stepLabel, 'Catch'])
                if (catchError) {
                    return catchError
                }
            }

            if (Array.isArray(step.config?.finally_steps) && step.config.finally_steps.length > 0) {
                const finallyError = validateStepTree(step.config.finally_steps, [...ancestors, stepLabel, 'Finally'])
                if (finallyError) {
                    return finallyError
                }
            }

            continue
        }

        if (Array.isArray(step.steps) && step.steps.length > 0) {
            const customError = validateStepTree(step.steps, [...ancestors, stepLabel])
            if (customError) {
                return customError
            }
        }
    }

    return null
}

const saveScene = async () => {
    if (!sceneForm.value.name) {
        ElMessage.warning(t('appAutomation.messages.enterSceneName'))
        return
    }
    if (scenarioSteps.value.length === 0) {
        ElMessage.warning(t('appAutomation.messages.addAtLeastOneStep'))
        return
    }

    const validationError = validateStepTree(scenarioSteps.value)
    if (validationError) {
        ElMessage.warning(validationError)
        return
    }

    saving.value = true
    try {
        const sanitizeStep = (step) => {
            if (!step || typeof step !== 'object') {
                return step
            }

            const clonedStep = JSON.parse(JSON.stringify(step))
            delete clonedStep._expanded
            ensureStepContainers(clonedStep)

            if (Array.isArray(clonedStep.steps)) {
                clonedStep.steps = clonedStep.steps.map(childStep => sanitizeStep(childStep))
            }
            if (Array.isArray(clonedStep.config?.steps)) {
                clonedStep.config.steps = clonedStep.config.steps.map(childStep => sanitizeStep(childStep))
            }
            if (Array.isArray(clonedStep.config?.then_steps)) {
                clonedStep.config.then_steps = clonedStep.config.then_steps.map(childStep => sanitizeStep(childStep))
            }
            if (Array.isArray(clonedStep.config?.else_steps)) {
                clonedStep.config.else_steps = clonedStep.config.else_steps.map(childStep => sanitizeStep(childStep))
            }
            if (Array.isArray(clonedStep.config?.try_steps)) {
                clonedStep.config.try_steps = clonedStep.config.try_steps.map(childStep => sanitizeStep(childStep))
            }
            if (Array.isArray(clonedStep.config?.catch_steps)) {
                clonedStep.config.catch_steps = clonedStep.config.catch_steps.map(childStep => sanitizeStep(childStep))
            }
            if (Array.isArray(clonedStep.config?.finally_steps)) {
                clonedStep.config.finally_steps = clonedStep.config.finally_steps.map(childStep => sanitizeStep(childStep))
            }
            if (Array.isArray(clonedStep.config?.elseif_branches)) {
                clonedStep.config.elseif_branches = clonedStep.config.elseif_branches.map(branch => ({
                    ...branch,
                    steps: Array.isArray(branch.steps) ? branch.steps.map(childStep => sanitizeStep(childStep)) : [],
                    conditions_input: Array.isArray(branch.conditions_input) ? branch.conditions_input : [createDefaultCondition()]
                }))
            }
            if (clonedStep.type === 'if') {
                normalizeIfConfigForSave(clonedStep)
            }

            return clonedStep
        }

        const cleanedSteps = JSON.parse(JSON.stringify(scenarioSteps.value)).map(step => sanitizeStep(step))
        const caseData = {
            name: sceneForm.value.name,
            description: sceneForm.value.description,
            project: sceneForm.value.project || null,
            ui_flow: cleanedSteps,
            variables: formatSceneVariables(),
            runtime: { ...sceneRuntime.value }
        }

        let caseResponse = null
        if (editingCaseId.value) {
            caseResponse = await updateTestCase(editingCaseId.value, caseData)
        } else {
            caseResponse = await createTestCase(caseData)
        }

        const responseData = caseResponse.data || caseResponse
        if (responseData && (responseData.id || responseData.success)) {
            ElMessage.success(editingCaseId.value ? t('appAutomation.messages.sceneUpdateSuccess') : t('appAutomation.messages.sceneSaveSuccess'))
            if (responseData.id && !editingCaseId.value) {
                editingCaseId.value = responseData.id
            }
        } else {
            ElMessage.success(t('appAutomation.messages.sceneSubmitted'))
        }
    } catch (error) {
        console.error("保存场景失败:", error)
        const errorMsg = (error.response && error.response.data && error.response.data.msg) || error.message
        ElMessage.error(`${t('appAutomation.messages.saveSceneFailed')}: ${errorMsg}`)
    } finally {
        saving.value = false
    }
}

// 元素选择器相关方法
const openElementSelector = (target = '') => {
    elementSelectorTarget.value = target
    elementSelectorVisible.value = true
    loadElementsForSelector()
}

const loadElementsForSelector = async () => {
    elementSelectorLoading.value = true
    try {
        const params = {
            page: elementCurrentPage.value,
            size: elementPageSize.value,
            element_type: elementFilterType.value,
            keyword: elementSearchKeyword.value
        }

        const response = await getAppElementList(params)
        const data = response.data?.data || response.data
        selectorElements.value = data?.results || data || []
        elementTotal.value = data?.count || selectorElements.value.length
    } catch (error) {
        console.error('加载元素列表失败:', error)
        ElMessage.error(t('appAutomation.messages.loadElementsFailed'))
    } finally {
        elementSelectorLoading.value = false
    }
}

// 加载图片分类选项（从 Template 目录扫描）
const loadImageCategoryOptions = async () => {
    try {
        console.log('=== 开始加载图片分类选项（从Template目录） ===')
        const response = await getAppImageCategories()
        console.log('API响应:', response)

        const categories = response.data?.data || response.data || []
        console.log('获取到的分类:', categories)

        // 转换为选项格式
        // 如果 categories 是对象数组（包含 name 字段），则使用 name；否则直接使用值
        imageCategoryOptions.value = categories.map(cat => {
            const categoryName = typeof cat === 'object' && cat.name ? cat.name : cat
            return {
                label: categoryName,
                value: categoryName
            }
        })

        console.log('最终选项:', imageCategoryOptions.value)
    } catch (error) {
        console.error('加载图片分类失败:', error)
        // 失败时使用默认值
        imageCategoryOptions.value = [{ label: 'common', value: 'common' }]
    }
}

const handleElementRowClick = (row) => {
    // 行点击事件（可选）
}

// 统一的字段填充函数
const fillFieldsByTarget = (element, config, target) => {
    console.log(`填充 ${target} 字段组`)

    // 映射：target -> 字段前缀
    const prefixMap = {
        selector: '',       // 通用定位没有前缀
        fallback: 'fallback_',  // 备用定位
        click: 'click_',
        ocr: 'ocr_',
        start: 'start_',
        end: 'end_',
        target: 'target_',
        expected: ''        // 断言字段特殊处理
    }

    const prefix = prefixMap[target] || ''
    const typeField = prefix ? `${prefix}selector_type` : 'selector_type'
    const valueField = prefix ? `${prefix}selector` : 'selector'
    const scopeField = prefix ? `${prefix}image_scope` : 'image_scope'

    // 保存 element_id 到步骤配置（runner 优先通过 element_id 从数据库解析）
    const elementIdField = prefix ? `${prefix}element_id` : 'element_id'
    config[elementIdField] = element.id

    // 根据元素类型填充（作为 fallback，即使 element_id 失效也能通过 selector 定位）
    if (element.element_type === 'image') {
        if (element.config && element.config.image_path) {
            const fileName = element.config.image_path.split('/').pop()

            // 设置定位类型和值
            if (target === 'expected') {
                // 断言字段特殊处理
                if (config.assert_type !== undefined) {
                    config.assert_type = 'image'
                    config.expected = fileName
                }
                if (element.config.image_category && config.expected_image_scope !== undefined) {
                    config.expected_image_scope = element.config.image_category
                }
            } else {
                config[typeField] = 'image'
                config[valueField] = fileName
                // 填充图片路径
                if (element.config.image_category) {
                    config[scopeField] = element.config.image_category
                }
            }
            
            ElMessage.success(t('appAutomation.messages.elementLinkedImage', { target: getTargetTitle(target), name: element.name }))
        } else {
            ElMessage.warning(t('appAutomation.messages.imageElementNoPath'))
        }
    } else if (element.element_type === 'pos') {
        if (element.config && element.config.x !== undefined && element.config.y !== undefined) {
            const posValue = `${element.config.x}, ${element.config.y}`

            config[typeField] = 'pos'
            config[valueField] = posValue
            
            ElMessage.success(t('appAutomation.messages.elementLinkedPos', { target: getTargetTitle(target), name: element.name }))
        }
    } else if (element.element_type === 'region') {
        if (element.config &&
            element.config.x1 !== undefined &&
            element.config.y1 !== undefined &&
            element.config.x2 !== undefined &&
            element.config.y2 !== undefined) {
            const regionValue = `${element.config.x1}, ${element.config.y1}, ${element.config.x2}, ${element.config.y2}`

            config[typeField] = 'region'
            config[valueField] = regionValue
            
            ElMessage.success(t('appAutomation.messages.elementLinkedRegion', { target: getTargetTitle(target), name: element.name }))
        }
    } else {
        ElMessage.warning(t('appAutomation.messages.elementTypeNotApplicable', { type: element.element_type, target: getTargetTitle(target) }))
    }
}

// 获取目标组的显示标题
const getTargetTitle = (target) => {
    const titleMap = {
        selector: '定位',
        fallback: '备用定位',
        click: '点击定位',
        ocr: 'OCR定位',
        start: '起始定位',
        end: '结束定位',
        target: '目标定位',
        expected: '断言配置'
    }
    return titleMap[target] || target
}

const applyElement = (element) => {
    // 优先使用编辑对话框的步骤，否则使用场景步骤
    const targetStep = (customDialogVisible.value && editingActiveStep.value)
        ? editingActiveStep.value
        : activeStep.value

    if (!targetStep) {
        ElMessage.warning(t('appAutomation.messages.selectStepForElement'))
        return
    }

    // 根据元素类型自动填充配置
    if (!targetStep.config) {
        targetStep.config = {}
    }

    const config = targetStep.config
    const target = elementSelectorTarget.value
    console.log('config before:', JSON.stringify(config))

    // 保存关联信息
    const elementInfo = {
        id: element.id,
        name: element.name,
        type: element.element_type
    }

    if (target && linkedElements.value[target] !== undefined) {
        linkedElements.value[target] = elementInfo
        // 填充对应的字段
        fillFieldsByTarget(element, config, target)
    } else {
        ElMessage.warning(t('appAutomation.messages.noValidFieldGroup'))
    }

    console.log('config after:', JSON.stringify(config))
    console.log('=== applyElement 完成 ===')

    // 关闭选择器
    elementSelectorVisible.value = false
}

// 统一的清除关联函数
const clearLinkedElement = (target) => {
    linkedElements.value[target] = null

    const targetStep = (customDialogVisible.value && editingActiveStep.value)
        ? editingActiveStep.value
        : activeStep.value

    if (targetStep && targetStep.config) {
        const config = targetStep.config

        // 映射：target -> 字段前缀
        const prefixMap = {
            selector: '',
            fallback: 'fallback_',
            click: 'click_',
            ocr: 'ocr_',
            start: 'start_',
            end: 'end_',
            target: 'target_',
            expected: ''
        }

        const prefix = prefixMap[target] || ''
        const typeField = prefix ? `${prefix}selector_type` : 'selector_type'
        const valueField = prefix ? `${prefix}selector` : 'selector'
        const scopeField = prefix ? `${prefix}image_scope` : 'image_scope'

        // 清空 element_id
        const elementIdField = prefix ? `${prefix}element_id` : 'element_id'
        delete config[elementIdField]

        // 清空字段值
        if (target === 'expected') {
            if (config.expected !== undefined) {
                config.expected = ''
            }
            if (config.expected_image_scope !== undefined) {
                config.expected_image_scope = 'common'
            }
        } else {
            if (config[valueField] !== undefined) {
                config[valueField] = ''
            }
            if (config[scopeField] !== undefined) {
                config[scopeField] = 'common'
            }
        }
    }
    
    ElMessage.info(t('appAutomation.messages.elementLinkCleared', { target: getTargetTitle(target) }))
}

const getTypeTagColor = (type) => {
    const colorMap = {
        'image': 'primary',
        'pos': 'success',
        'region': 'warning'
    }
    return colorMap[type] || ''
}

// 判断字段是否需要显示数据工厂和变量助手按钮
const needsHelperButtons = (field) => {
    const helperFields = [
        'value', 'expected', 'selector', 'fallback_selector',
        'click_selector', 'ocr_selector', 'start_selector', 'end_selector', 'target_selector',
        'url', 'json', 'data', 'headers', 'params', 'left', 'right',
        'expected_list', 'items', 'then_steps', 'else_steps', 'steps',
        'try_steps', 'catch_steps', 'finally_steps', 'branches', 'extracts'
    ]
    return helperFields.includes(field)
}

// 数据工厂选择器相关方法
const openDataFactorySelector = (step, field, isEditing = false) => {
    currentDataFactoryTarget.value = { step, field, isEditing }
    showDataFactorySelector.value = true
}

const onInputFocus = (event) => {
    let target = event.target
    if (!target) return
    
    if (target.classList.contains('el-input') || target.classList.contains('el-textarea')) {
        const innerInput = target.querySelector('.el-input__inner') || target.querySelector('textarea')
        if (innerInput) {
            currentFocusedInput.value = innerInput
            return
        }
    }
    
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'DIV') {
        currentFocusedInput.value = target
    }
}

const getInputElement = () => {
    let element = currentFocusedInput.value
    if (!element) return null
    
    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
        return element
    }
    
    if (element.classList.contains('el-input') || element.classList.contains('el-textarea')) {
        return element.querySelector('.el-input__inner') || element.querySelector('textarea')
    }
    
    return element.querySelector('.el-input__inner') || element.querySelector('textarea')
}

const handleDataFactorySelect = (record) => {
    if (!record || !record.output_data || !currentDataFactoryTarget.value) {
        showDataFactorySelector.value = false
        return
    }
    
    const { step, field } = currentDataFactoryTarget.value
    
    let valueToSet = ''
    if (typeof record.output_data === 'string') {
        valueToSet = record.output_data
    } else if (record.output_data.result) {
        valueToSet = record.output_data.result
    } else if (record.output_data.output_data) {
        valueToSet = record.output_data.output_data
    } else {
        valueToSet = JSON.stringify(record.output_data)
    }
    
    const currentValue = step.config[field] || ''
    
    let inputElement = getInputElement()
    
    if (inputElement && (inputElement.tagName === 'INPUT' || inputElement.tagName === 'TEXTAREA')) {
        const cursorPosition = inputElement.selectionStart || 0
        const newValue = currentValue.substring(0, cursorPosition) + valueToSet + currentValue.substring(cursorPosition)
        step.config[field] = newValue
        
        const newCursorPosition = cursorPosition + valueToSet.length
        setTimeout(() => {
            inputElement.focus()
            inputElement.selectionStart = newCursorPosition
            inputElement.selectionEnd = newCursorPosition
        }, 50)
    } else {
        if (!currentValue) {
            step.config[field] = valueToSet
        } else {
            step.config[field] = currentValue + valueToSet
        }
    }
    
    ElMessage.success(t('appAutomation.messages.dataFactorySelected', { toolName: record.tool_name }))
    showDataFactorySelector.value = false
    currentDataFactoryTarget.value = null
    currentFocusedInput.value = null
}

// 变量助手相关方法
const openVariableHelper = (step, field, isEditing = false) => {
    currentDataFactoryTarget.value = { step, field, isEditing }
    if (variableCategories.value.length === 0) {
        loadVariableFunctions()
    }
    showVariableHelper.value = true
}

const loadVariableFunctions = async () => {
    try {
        variableLoading.value = true
        const apiResponse = await getVariableFunctions()
        
        let functionsData = []
        if (apiResponse && apiResponse.data) {
            if (Array.isArray(apiResponse.data)) {
                functionsData = apiResponse.data
            } else if (apiResponse.data.functions) {
                functionsData = apiResponse.data.functions
            } else if (typeof apiResponse.data === 'object') {
                functionsData = apiResponse.data
            }
        }
        
        const grouped = {}
        
        if (Array.isArray(functionsData)) {
            functionsData.forEach(func => {
                const category = func.category || t('appAutomation.sceneBuilder.variableCategory.uncategorized')
                if (!grouped[category]) {
                    grouped[category] = []
                }
                grouped[category].push({
                    name: func.name,
                    syntax: func.syntax,
                    desc: func.description || func.desc || '',
                    example: func.example
                })
            })
        } else if (typeof functionsData === 'object') {
            for (const [category, funcs] of Object.entries(functionsData)) {
                if (Array.isArray(funcs)) {
                    grouped[category] = funcs.map(func => ({
                        name: func.name,
                        syntax: func.syntax,
                        desc: func.description || func.desc || '',
                        example: func.example
                    }))
                }
            }
        }
        
        const categoryOrder = [
            t('appAutomation.sceneBuilder.variableCategory.randomNumber'),
            t('appAutomation.sceneBuilder.variableCategory.testData'),
            t('appAutomation.sceneBuilder.variableCategory.string'),
            t('appAutomation.sceneBuilder.variableCategory.encoding'),
            t('appAutomation.sceneBuilder.variableCategory.encryption'),
            t('appAutomation.sceneBuilder.variableCategory.dateTime'),
            'Crontab',
            t('appAutomation.sceneBuilder.variableCategory.uncategorized')
        ]
        
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
        
        for (const [category, funcs] of Object.entries(grouped)) {
            orderedCategories.push({
                label: category,
                variables: funcs
            })
        }
        
        variableCategories.value = orderedCategories
    } catch (error) {
        console.error('加载变量函数失败:', error)
        useLocalVariableCategories()
    } finally {
        variableLoading.value = false
    }
}

const useLocalVariableCategories = () => {
    variableCategories.value = [
        {
            label: t('appAutomation.sceneBuilder.variableCategory.randomNumber'),
            variables: [
                { name: 'random_int', syntax: '${random_int(min, max, count)}', desc: t('appAutomation.sceneBuilder.variable.randomInt.desc'), example: '${random_int(100, 999, 1)}' },
                { name: 'random_float', syntax: '${random_float(min, max, precision, count)}', desc: t('appAutomation.sceneBuilder.variable.randomFloat.desc'), example: '${random_float(0, 1, 2, 1)}' }
            ]
        },
        {
            label: t('appAutomation.sceneBuilder.variableCategory.randomString'),
            variables: [
                { name: 'random_string', syntax: '${random_string(length, char_type, count)}', desc: t('appAutomation.sceneBuilder.variable.randomString.desc'), example: '${random_string(8, "all", 1)}' }
            ]
        }
    ]
}

const insertVariable = (variable) => {
    if (!currentDataFactoryTarget.value) return
    
    const { step, field } = currentDataFactoryTarget.value
    const example = variable.example
    const currentValue = step.config[field] || ''
    
    let inputElement = getInputElement()
    
    if (inputElement && (inputElement.tagName === 'INPUT' || inputElement.tagName === 'TEXTAREA')) {
        const cursorPosition = inputElement.selectionStart || 0
        const newValue = currentValue.substring(0, cursorPosition) + example + currentValue.substring(cursorPosition)
        step.config[field] = newValue
        
        const newCursorPosition = cursorPosition + example.length
        setTimeout(() => {
            inputElement.focus()
            inputElement.selectionStart = newCursorPosition
            inputElement.selectionEnd = newCursorPosition
        }, 50)
    } else {
        if (!currentValue) {
            step.config[field] = example
        } else {
            step.config[field] = currentValue + example
        }
    }
    
    ElMessage.success(t('appAutomation.messages.variableInserted', { name: variable.name }))
    showVariableHelper.value = false
    currentDataFactoryTarget.value = null
    currentFocusedInput.value = null
}

// Template refs assignment
defineExpose({
    customForm: customFormRef
})
</script>

<style scoped>
.ui-test-scene-builder {
    padding: 16px;
}

.page-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
}

.page-header h3 {
    margin: 0;
}

.header-actions {
    display: flex;
    gap: 8px;
}

.scene-config {
    margin-top: 12px;
}

.scene-layout {
    margin-top: 16px;
}

.card-title {
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.scene-variables {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.scene-variable-item {
    display: grid;
    grid-template-columns: 140px 120px 120px 1fr 1fr auto;
    gap: 8px;
    align-items: center;
}

.variable-hint {
    font-size: 12px;
    color: #909399;
    margin: 0 0 8px 0;
}

.hint-danger {
    color: #f56c6c;
}

.palette-list {
    min-height: 360px;
}

.palette-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 10px;
    border: 1px dashed #dcdfe6;
    border-left-width: 4px;
    border-radius: 4px;
    margin-bottom: 8px;
    cursor: grab;
    background: var(--th-color-surface-muted);
}

.palette-left {
    display: flex;
    align-items: center;
    gap: 8px;
}

.palette-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    opacity: 0;
    transition: opacity 0.15s ease;
}

.palette-item:hover .palette-actions {
    opacity: 1;
}

.palette-empty {
    color: #909399;
    font-size: 12px;
    padding: 8px 10px;
}

.palette-name {
    font-weight: 500;
    line-height: 20px;
}

.category-control {
    border-left-color: #7c3aed !important;
    background: rgba(124, 58, 237, 0.08);
}

.category-action {
    border-left-color: #2563eb !important;
    background: rgba(37, 99, 235, 0.08);
}

.category-utility {
    border-left-color: #0f766e !important;
    background: rgba(15, 118, 110, 0.08);
}

.category-assert {
    border-left-color: #d97706 !important;
    background: rgba(217, 119, 6, 0.08);
}

.custom-steps-section {
    margin-top: 12px;
}

.custom-steps-label {
    font-size: 14px;
    font-weight: 500;
    color: #606266;
    margin-bottom: 8px;
}

.custom-edit-steps {
    display: flex;
    gap: 12px;
}

.custom-step-list {
    flex: 1;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 8px;
    min-height: 220px;
    max-height: 500px;
    overflow-y: auto;
}

.custom-step-toolbar {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
    align-items: center;
}

.custom-step-toolbar .el-select .el-input__inner {
    height: 32px;
    line-height: 32px;
}

.custom-step-toolbar .el-button {
    height: 32px;
    padding: 0 12px;
}

.custom-step-items {
    min-height: 160px;
}

.custom-step-item {
    width: 100%;
}

.custom-step-item .scene-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 20px;
    min-width: 10px;
    line-height: 1;
    padding: 0 6px;
}

.custom-step-config {
    flex: 1;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 12px;
    min-height: 220px;
    max-height: 500px;
    overflow-y: auto;
}


.scene-card {
    min-height: 480px;
}

.scene-hint {
    color: #909399;
    font-size: 13px;
    padding: 12px;
}

.scene-list {
    min-height: 420px;
}

.scene-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    cursor: pointer;
    background: var(--th-color-surface);
}

.scene-item.active {
    border-color: var(--th-color-primary);
    background: var(--th-color-info-soft);
}

.scene-item-main {
    display: flex;
    align-items: center;
    gap: 8px;
}

.scene-index {
    background: var(--th-color-primary);
    color: var(--th-color-surface);
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 10px;
}

.scene-name {
    font-weight: 500;
}

.scene-item-wrapper {
    margin-bottom: 8px;
}

.scene-item-wrapper>.scene-item {
    margin-bottom: 0;
}

.scene-item.is-expanded {
    border-color: #e6a23c;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    margin-bottom: 0;
}

.custom-sub-steps {
    border: 1px solid #e6a23c;
    border-top: none;
    border-radius: 0 0 6px 6px;
    background: var(--th-color-warning-soft);
    padding: 6px 6px 4px 6px;
}

.tree-node {
    position: relative;
}

.tree-node::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 2px;
    background-color: #e8e8e8;
}

.sub-steps-list {
    margin-bottom: 10px;
}

.sub-steps-list .sub-step-item {
    margin-bottom: 8px;
    cursor: move;
}

.sub-steps-list .sub-step-item:hover {
    background-color: #f5f7fa;
}

.if-branches {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.if-branch-block {
    border: 1px dashed #dcdfe6;
    border-radius: 6px;
    padding: 10px;
    background: #fafafa;
}

.if-branch-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
}

.if-condition-row {
    display: grid;
    grid-template-columns: 1fr 120px 1fr auto;
    gap: 8px;
    margin-bottom: 8px;
}

.if-conditions-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.sub-step-item {
    margin-bottom: 4px !important;
    padding: 7px 10px !important;
    margin-left: 16px !important;
    border-color: #dcdfe6 !important;
    background: var(--th-color-surface) !important;
    font-size: 13px;
}

.sub-step-item.active {
    border-color: #e6a23c !important;
    background: #fef0e0 !important;
}

.sub-index {
    background: #e6a23c !important;
    font-size: 11px !important;
    padding: 1px 5px !important;
}

.sub-step-toolbar {
    text-align: center;
    padding: 2px 0 4px 0;
}

.config-card {
    min-height: 480px;
}

.config-empty {
    color: #909399;
    font-size: 13px;
    padding: 16px;
}

.package-title {
    font-size: 12px;
    color: #909399;
    margin-bottom: 6px;
}

.package-list {
    max-height: 240px;
    overflow-y: auto;
    border: 1px solid #ebeef5;
    border-radius: 4px;
    padding: 6px;
}

.package-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
    border-bottom: 1px dashed #ebeef5;
}

.package-item:last-child {
    border-bottom: none;
}

.package-name {
    font-size: 12px;
    color: #303133;
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.package-meta {
    display: flex;
    gap: 8px;
    color: #909399;
    font-size: 12px;
}

.package-empty {
    color: #909399;
    font-size: 12px;
    padding: 6px 0;
}

/* 元素选择器样式 */
.element-selector-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.element-selector-filter {
    padding: 10px;
    background-color: var(--th-color-surface-muted);
    border-radius: 4px;
}

.preview-image {
    display: flex;
    justify-content: center;
    align-items: center;
}

.preview-pos,
.preview-region {
    font-size: 12px;
}

/* 字段分组样式 */
.field-group {
    margin-bottom: 20px;
    padding: 16px;
    background: var(--th-color-surface-muted);
    border-radius: 4px;
    border: 1px solid #e4e7ed;
}

.group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #dcdfe6;
}

.group-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
}

.element-linked-alert {
    margin-bottom: 12px;
}

.field-group :deep(.el-form-item) {
    margin-bottom: 12px;
}

.field-group :deep(.el-form-item__label) {
    width: 80px !important;
    text-align: left;
    padding-right: 4px;
    justify-content: flex-start;
}

.field-group :deep(.el-form-item__content) {
    flex: 1;
    min-width: 0;
}

.field-group :deep(.el-form-item__content > .el-input),
.field-group :deep(.el-form-item__content > .el-select),
.field-group :deep(.el-form-item__content > div) {
    width: 100%;
    max-width: none;
}

.field-group:last-child {
    margin-bottom: 0;
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
</style>
