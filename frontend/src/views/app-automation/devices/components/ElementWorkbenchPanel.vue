<template>
  <div class="element-workbench">
    <div class="workbench-header">
      <div>
        <h4>{{ t("appAutomation.workbench.elements.title") }}</h4>
        <!-- <p>基于远控当前画面或设备截图，精确创建图片、坐标、区域元素。</p> -->
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          :disabled="!captureFrame"
          @click="captureFromRemoteFrame"
          >{{
            t("appAutomation.workbench.elements.captureCurrentFrame")
          }}</el-button
        >
        <el-button :loading="capturing" @click="captureScreen">{{
          t("appAutomation.workbench.elements.captureScreenshot")
        }}</el-button>
        <el-button @click="resetWorkspace">{{
          t("appAutomation.workbench.elements.reset")
        }}</el-button>
      </div>
    </div>

    <div class="workbench-body">
      <div class="capture-pane">
        <div class="capture-stage">
          <div
            v-if="capturedImage"
            ref="imageWrapper"
            class="image-wrapper"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseUp"
          >
            <img
              ref="imageRef"
              :src="capturedImage"
              class="capture-image"
              @load="handleImageLoad"
            />
            <div
              v-if="selection"
              class="selection-box"
              :style="selectionStyle"
              @mousedown.stop="handleSelectionMouseDown"
            >
              <button class="selection-close" @click.stop="clearSelection">
                ×
              </button>
              <div class="selection-info">{{ selectionInfo }}</div>
              <span
                v-for="handle in resizeHandles"
                :key="handle"
                class="resize-handle"
                :class="`resize-handle-${handle}`"
                @mousedown.stop="handleResizeStart(handle, $event)"
              ></span>
            </div>
            <div
              v-else-if="hasPos"
              class="position-marker"
              :style="positionMarkerStyle"
            >
              <span class="position-dot"></span>
              <span class="position-label">{{ posValue }}</span>
            </div>
          </div>
          <el-empty
            v-else
            :description="t('appAutomation.workbench.elements.emptyScreenshot')"
          />
        </div>
      </div>

      <div class="form-pane">
        <el-form label-width="100px" size="small">
          <div class="capture-toolbar">
            <div class="capture-hint">{{ captureHint }}</div>
            <el-tag v-if="captureSourceLabel" size="small" effect="plain">{{
              captureSourceLabel
            }}</el-tag>
          </div>
          <el-form-item :label="t('appAutomation.workbench.elements.device')">
            <el-input :model-value="deviceLabel" disabled />
          </el-form-item>

          <el-form-item
            :label="t('appAutomation.workbench.elements.elementName')"
            required
          >
            <el-input
              v-model="formData.name"
              :placeholder="
                t('appAutomation.workbench.elements.elementNamePlaceholder')
              "
            />
          </el-form-item>

          <el-form-item :label="t('appAutomation.workbench.elements.project')">
            <el-select
              v-model="formData.project"
              clearable
              filterable
              :placeholder="
                t('appAutomation.workbench.elements.projectPlaceholder')
              "
              style="width: 100%"
            >
              <el-option
                v-for="project in projectList"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            :label="t('appAutomation.workbench.elements.elementType')"
            required
          >
            <el-radio-group v-model="formData.element_type">
              <el-radio value="image">{{
                t("appAutomation.workbench.elements.imageElement")
              }}</el-radio>
              <el-radio value="pos">{{
                t("appAutomation.workbench.elements.posElement")
              }}</el-radio>
              <el-radio value="region">{{
                t("appAutomation.workbench.elements.regionElement")
              }}</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item :label="t('appAutomation.workbench.elements.tags')">
            <el-select
              v-model="formData.tags"
              multiple
              filterable
              allow-create
              default-first-option
              :placeholder="
                t('appAutomation.workbench.elements.tagsPlaceholder')
              "
              style="width: 100%"
            />
          </el-form-item>

          <template v-if="formData.element_type === 'image'">
            <el-divider content-position="left">{{
              t("appAutomation.workbench.elements.imageConfig")
            }}</el-divider>

            <el-form-item
              :label="t('appAutomation.workbench.elements.imageCategory')"
              required
            >
              <div class="inline-row">
                <el-select
                  v-model="formData.image_category"
                  filterable
                  :placeholder="
                    t(
                      'appAutomation.workbench.elements.imageCategoryPlaceholder',
                    )
                  "
                  style="flex: 1"
                >
                  <el-option
                    v-for="cat in imageCategories"
                    :key="cat"
                    :label="cat"
                    :value="cat"
                  />
                </el-select>
                <el-button @click="createCategoryVisible = true">
                  {{ t("appAutomation.workbench.elements.newCategory") }}
                </el-button>
              </div>
            </el-form-item>

            <el-form-item
              :label="t('appAutomation.workbench.elements.templateFileName')"
              required
            >
              <el-input
                v-model="templateFileName"
                :placeholder="
                  t(
                    'appAutomation.workbench.elements.templateFileNamePlaceholder',
                  )
                "
              />
            </el-form-item>

            <el-form-item
              :label="t('appAutomation.workbench.elements.cropRegion')"
              required
            >
              <el-input
                :model-value="regionValue"
                readonly
                :placeholder="
                  t('appAutomation.workbench.elements.cropRegionPlaceholder')
                "
              />
            </el-form-item>

            <el-form-item
              :label="t('appAutomation.workbench.elements.savePath')"
            >
              <el-input :model-value="imageSavePath" disabled />
            </el-form-item>

            <el-form-item
              :label="t('appAutomation.workbench.elements.matchThreshold')"
            >
              <el-slider
                v-model="formData.config.image_threshold"
                :min="0.5"
                :max="1"
                :step="0.05"
                show-input
              />
            </el-form-item>

            <el-form-item
              :label="t('appAutomation.workbench.elements.colorMode')"
            >
              <el-switch
                v-model="formData.config.rgb"
                :active-text="t('appAutomation.workbench.elements.rgb')"
                :inactive-text="t('appAutomation.workbench.elements.grayscale')"
              />
            </el-form-item>
          </template>

          <template v-if="formData.element_type === 'pos'">
            <el-divider content-position="left">{{
              t("appAutomation.workbench.elements.positionConfig")
            }}</el-divider>
            <el-form-item
              :label="t('appAutomation.workbench.elements.posValue')"
            >
              <el-input
                :model-value="posValue"
                readonly
                :placeholder="
                  t('appAutomation.workbench.elements.posPlaceholder')
                "
              />
            </el-form-item>
            <el-form-item>
              <el-button
                link
                type="danger"
                :disabled="!hasPos"
                @click="clearPosition"
                >{{
                  t("appAutomation.workbench.elements.clearPosition")
                }}</el-button
              >
            </el-form-item>
          </template>

          <template v-if="formData.element_type === 'region'">
            <el-divider content-position="left">{{
              t("appAutomation.workbench.elements.regionConfig")
            }}</el-divider>
            <el-form-item
              :label="t('appAutomation.workbench.elements.regionValue')"
            >
              <el-input
                :model-value="regionValue"
                readonly
                :placeholder="
                  t('appAutomation.workbench.elements.regionPlaceholder')
                "
              />
            </el-form-item>
            <el-form-item>
              <el-button
                link
                type="danger"
                :disabled="!hasRegion"
                @click="clearSelection"
                >{{
                  t("appAutomation.workbench.elements.clearRegion")
                }}</el-button
              >
            </el-form-item>
          </template>

          <div class="form-actions">
            <el-button
              type="primary"
              :loading="submitting"
              :disabled="!canSave"
              @click="handleSubmit(false)"
              >{{
                t("appAutomation.workbench.elements.saveElement")
              }}</el-button
            >
            <el-button
              :loading="submitting"
              :disabled="!canSave"
              @click="handleSubmit(true)"
              >{{
                t("appAutomation.workbench.elements.saveAndContinue")
              }}</el-button
            >
          </div>
        </el-form>
      </div>
    </div>

    <el-dialog
      v-model="createCategoryVisible"
      :title="t('appAutomation.workbench.elements.createCategoryTitle')"
      width="400px"
    >
      <el-form>
        <el-form-item
          :label="t('appAutomation.workbench.elements.categoryName')"
        >
          <el-input
            v-model="newCategoryName"
            :placeholder="
              t('appAutomation.workbench.elements.categoryNamePlaceholder')
            "
            @keyup.enter="handleCreateCategory"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createCategoryVisible = false">{{
          t("appAutomation.common.cancel")
        }}</el-button>
        <el-button
          type="primary"
          :loading="creatingCategory"
          @click="handleCreateCategory"
          >{{ t("appAutomation.common.create") }}</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  captureDeviceScreenshot,
  createAppElement,
  createAppImageCategory,
  getAppImageCategories,
  getAppProjects,
  uploadAppElementImage,
} from "@/api/app-automation";

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
  deviceName: {
    type: String,
    default: "",
  },
  captureFrame: {
    type: Function,
    default: null,
  },
});

const emit = defineEmits(["created", "operation"]);
const { t } = useI18n();

const imageRef = ref(null);
const imageWrapper = ref(null);
const capturing = ref(false);
const submitting = ref(false);
const capturedImage = ref("");
const captureSource = ref("");
const projectList = ref([]);
const imageCategories = ref(["common"]);
const createCategoryVisible = ref(false);
const newCategoryName = ref("");
const creatingCategory = ref(false);

const selection = ref(null);
const selecting = ref(false);
const startPoint = ref(null);
const action = ref(null);
const resizeHandle = ref(null);
const moveOffset = ref(null);
const imageSize = ref({ width: 0, height: 0 });
const resizeHandles = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];

const formData = reactive({
  name: "",
  element_type: "image",
  image_category: "common",
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
    image_path: "",
    file_hash: "",
  },
});

const templateFileName = ref("");

const deviceLabel = computed(() => props.deviceName || props.deviceId);
const captureSourceLabel = computed(() => {
  if (captureSource.value === "remote-frame") {
    return t("appAutomation.workbench.elements.sourceRemoteFrame");
  }
  if (captureSource.value === "device-screenshot") {
    return t("appAutomation.workbench.elements.sourceDeviceScreenshot");
  }
  return "";
});
const captureHint = computed(() => {
  // 根据元素类型动态提示交互方式，避免用户在同一张图上误用操作。
  if (formData.element_type === "image") {
    return t("appAutomation.workbench.elements.captureHintImage");
  }
  if (formData.element_type === "pos") {
    return t("appAutomation.workbench.elements.captureHintPos");
  }
  return t("appAutomation.workbench.elements.captureHintRegion");
});

const logOperation = (message, level = "info", extra = null) => {
  emit("operation", {
    source: "elements",
    level,
    message,
    extra,
    timestamp: Date.now(),
  });
};

const selectionStyle = computed(() => {
  if (!selection.value) {
    return {};
  }
  const x1 = Math.min(selection.value.x1, selection.value.x2);
  const y1 = Math.min(selection.value.y1, selection.value.y2);
  const x2 = Math.max(selection.value.x1, selection.value.x2);
  const y2 = Math.max(selection.value.y1, selection.value.y2);
  return {
    left: `${x1}px`,
    top: `${y1}px`,
    width: `${x2 - x1}px`,
    height: `${y2 - y1}px`,
  };
});

const selectionInfo = computed(() => {
  if (!selection.value) {
    return "";
  }
  const width = Math.abs(selection.value.x2 - selection.value.x1);
  const height = Math.abs(selection.value.y2 - selection.value.y1);
  return `${Math.round(width)} × ${Math.round(height)}`;
});

const imageSavePath = computed(() => {
  const imageCategory = formData.image_category || "common";
  const filename = templateFileName.value || "template.png";
  return `Template/${imageCategory}/${filename}`;
});

const posValue = computed(() => {
  if (formData.config.x === null || formData.config.y === null) {
    return "";
  }
  return `${formData.config.x},${formData.config.y}`;
});

const regionValue = computed(() => {
  if (
    [
      formData.config.x1,
      formData.config.y1,
      formData.config.x2,
      formData.config.y2,
    ].some((item) => item === null || item === undefined)
  ) {
    return "";
  }
  return `${formData.config.x1},${formData.config.y1},${formData.config.x2},${formData.config.y2}`;
});

const hasPos = computed(
  () =>
    Number.isFinite(formData.config.x) && Number.isFinite(formData.config.y),
);
const hasRegion = computed(() =>
  [
    formData.config.x1,
    formData.config.y1,
    formData.config.x2,
    formData.config.y2,
  ].every((item) => Number.isFinite(item)),
);

const positionMarkerStyle = computed(() => {
  if (
    !hasPos.value ||
    !imageRef.value ||
    !imageSize.value.width ||
    !imageSize.value.height
  ) {
    return {};
  }
  const clientWidth = imageRef.value.clientWidth || 1;
  const clientHeight = imageRef.value.clientHeight || 1;
  return {
    left: `${(formData.config.x / imageSize.value.width) * clientWidth}px`,
    top: `${(formData.config.y / imageSize.value.height) * clientHeight}px`,
  };
});

const canSave = computed(() => {
  if (!formData.name.trim()) {
    return false;
  }
  if (formData.element_type === "image") {
    return Boolean(
      capturedImage.value &&
      templateFileName.value.trim() &&
      formData.image_category &&
      hasRegion.value,
    );
  }
  if (formData.element_type === "pos") {
    return hasPos.value;
  }
  if (formData.element_type === "region") {
    return hasRegion.value;
  }
  return false;
});

const resetFormOnly = () => {
  formData.name = "";
  formData.element_type = "image";
  formData.image_category = "common";
  formData.project = null;
  formData.tags = [];
  formData.config = {
    image_threshold: 0.7,
    rgb: false,
    x: null,
    y: null,
    x1: null,
    y1: null,
    x2: null,
    y2: null,
    image_path: "",
    file_hash: "",
  };
  templateFileName.value = "";
  clearSelection();
  clearPosition();
};

const resetWorkspace = () => {
  resetFormOnly();
  capturedImage.value = "";
  captureSource.value = "";
};

const loadProjects = async () => {
  try {
    const response = await getAppProjects({ page: 1, page_size: 1000 });
    const payload =
      response.data?.success !== undefined
        ? response.data?.data
        : response.data;
    projectList.value = payload?.results || payload || [];
  } catch (error) {
    console.error("Failed to load projects:", error);
  }
};

const loadImageCategories = async () => {
  try {
    const response = await getAppImageCategories();
    if (response.data.success && Array.isArray(response.data.data)) {
      imageCategories.value = response.data.data.map(
        (item) => item.name || item,
      );
    }
  } catch (error) {
    console.error("Failed to load image categories:", error);
    imageCategories.value = ["common"];
  }
};

const captureScreen = async () => {
  capturing.value = true;
  try {
    const response = await captureDeviceScreenshot(props.deviceId);
    const result = response.data;
    if (!result.success || !result.data?.content) {
      ElMessage.error(
        result.msg || t("appAutomation.workbench.elements.screenshotFailed"),
      );
      logOperation(
        t("appAutomation.workbench.elements.screenshotFailed"),
        "error",
        result,
      );
      return;
    }
    capturedImage.value = result.data.content;
    captureSource.value = "device-screenshot";
    clearPosition();
    clearSelection();
    ElMessage.success(t("appAutomation.workbench.elements.screenshotSuccess"));
    logOperation(
      t("appAutomation.workbench.elements.screenshotSuccess"),
      "success",
    );
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.msg ||
        error.message ||
        t("appAutomation.workbench.elements.screenshotFailed"),
    );
    logOperation(
      t("appAutomation.workbench.elements.screenshotFailed"),
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    capturing.value = false;
  }
};

const captureFromRemoteFrame = async () => {
  if (!props.captureFrame) {
    ElMessage.warning(
      t("appAutomation.workbench.elements.remoteFrameNotReady"),
    );
    return;
  }
  try {
    const frame = await props.captureFrame();
    if (!frame?.content) {
      ElMessage.warning(
        t("appAutomation.workbench.elements.remoteFrameUnavailable"),
      );
      return;
    }
    capturedImage.value = frame.content;
    captureSource.value = frame.source || "remote-frame";
    clearPosition();
    clearSelection();
    ElMessage.success(t("appAutomation.workbench.elements.remoteFrameLoaded"));
    logOperation(
      t("appAutomation.workbench.elements.remoteFrameLoaded"),
      "success",
    );
  } catch (error) {
    ElMessage.error(
      error?.message ||
        t("appAutomation.workbench.elements.remoteFrameLoadFailed"),
    );
    logOperation(
      t("appAutomation.workbench.elements.remoteFrameLoadFailed"),
      "error",
      error?.message || error,
    );
  }
};

const handleImageLoad = () => {
  if (!imageRef.value) {
    return;
  }
  imageSize.value = {
    width: imageRef.value.naturalWidth || imageRef.value.width,
    height: imageRef.value.naturalHeight || imageRef.value.height,
  };
};

const getImageRect = () => {
  if (!imageWrapper.value || !imageRef.value) {
    return null;
  }
  return imageWrapper.value.getBoundingClientRect();
};

const getSelectionInNatural = () => {
  if (!selection.value || !imageRef.value) {
    return null;
  }
  // 页面展示尺寸与原图尺寸通常不同，保存前必须还原为原图坐标。
  const scaleX = imageSize.value.width / imageRef.value.clientWidth;
  const scaleY = imageSize.value.height / imageRef.value.clientHeight;
  const x1 = Math.min(selection.value.x1, selection.value.x2);
  const y1 = Math.min(selection.value.y1, selection.value.y2);
  const x2 = Math.max(selection.value.x1, selection.value.x2);
  const y2 = Math.max(selection.value.y1, selection.value.y2);
  return {
    x1: Math.round(x1 * scaleX),
    y1: Math.round(y1 * scaleY),
    x2: Math.round(x2 * scaleX),
    y2: Math.round(y2 * scaleY),
  };
};

const updateSelectionValues = () => {
  const natural = getSelectionInNatural();
  if (!natural) {
    return;
  }
  formData.config.x1 = natural.x1;
  formData.config.y1 = natural.y1;
  formData.config.x2 = natural.x2;
  formData.config.y2 = natural.y2;
};

const handleMouseDown = (event) => {
  if (!capturedImage.value || !imageWrapper.value) {
    return;
  }
  const rect = getImageRect();
  if (!rect) {
    return;
  }
  // 所有选区、坐标、区域操作都从同一个起点手势进入，后续由 action 区分行为。
  const x = Math.max(0, Math.min(event.clientX - rect.left, rect.width));
  const y = Math.max(0, Math.min(event.clientY - rect.top, rect.height));
  selecting.value = true;
  startPoint.value = { x, y };
  action.value = "create";
  selection.value = { x1: x, y1: y, x2: x, y2: y };
  event.preventDefault();
};

const handleMouseMove = (event) => {
  if (!selecting.value || !selection.value) {
    return;
  }
  const rect = getImageRect();
  if (!rect) {
    return;
  }
  const x = Math.max(0, Math.min(event.clientX - rect.left, rect.width));
  const y = Math.max(0, Math.min(event.clientY - rect.top, rect.height));

  if (action.value === "create" && startPoint.value) {
    selection.value = {
      x1: startPoint.value.x,
      y1: startPoint.value.y,
      x2: x,
      y2: y,
    };
  } else if (action.value === "move" && moveOffset.value) {
    const width = Math.abs(selection.value.x2 - selection.value.x1);
    const height = Math.abs(selection.value.y2 - selection.value.y1);
    const left = Math.max(
      0,
      Math.min(x - moveOffset.value.x, rect.width - width),
    );
    const top = Math.max(
      0,
      Math.min(y - moveOffset.value.y, rect.height - height),
    );
    selection.value = { x1: left, y1: top, x2: left + width, y2: top + height };
  } else if (action.value === "resize" && resizeHandle.value) {
    selection.value = resizeSelection(
      selection.value,
      resizeHandle.value,
      x,
      y,
      rect,
    );
  }
  event.preventDefault();
};

const handleMouseUp = () => {
  if (!selecting.value) {
    return;
  }

  if (action.value === "create" && selection.value) {
    // 对于坐标元素，极小选区视为一次点击；否则按框选区域处理。
    const width = Math.abs(selection.value.x2 - selection.value.x1);
    const height = Math.abs(selection.value.y2 - selection.value.y1);
    if (width < 5 && height < 5) {
      if (formData.element_type === "pos" && imageRef.value) {
        const scaleX = imageSize.value.width / imageRef.value.clientWidth;
        const scaleY = imageSize.value.height / imageRef.value.clientHeight;
        formData.config.x = Math.round(selection.value.x1 * scaleX);
        formData.config.y = Math.round(selection.value.y1 * scaleY);
      }
      selection.value = null;
    } else {
      clearPosition();
      updateSelectionValues();
    }
  } else if (action.value === "move" || action.value === "resize") {
    updateSelectionValues();
  }

  selecting.value = false;
  startPoint.value = null;
  action.value = null;
  resizeHandle.value = null;
  moveOffset.value = null;
};

const handleSelectionMouseDown = (event) => {
  const rect = getImageRect();
  if (!rect || !selection.value) {
    return;
  }
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const x1 = Math.min(selection.value.x1, selection.value.x2);
  const y1 = Math.min(selection.value.y1, selection.value.y2);
  selecting.value = true;
  action.value = "move";
  moveOffset.value = { x: x - x1, y: y - y1 };
  event.preventDefault();
};

const handleResizeStart = (handle, event) => {
  selecting.value = true;
  action.value = "resize";
  resizeHandle.value = handle;
  event.preventDefault();
};

const resizeSelection = (sel, handle, x, y, rect) => {
  let { x1, y1, x2, y2 } = sel;
  const clampX = Math.max(0, Math.min(x, rect.width));
  const clampY = Math.max(0, Math.min(y, rect.height));
  if (handle.includes("n")) y1 = clampY;
  if (handle.includes("s")) y2 = clampY;
  if (handle.includes("w")) x1 = clampX;
  if (handle.includes("e")) x2 = clampX;
  return { x1, y1, x2, y2 };
};

const clearSelection = () => {
  selection.value = null;
  action.value = null;
  resizeHandle.value = null;
  moveOffset.value = null;
  formData.config.x1 = null;
  formData.config.y1 = null;
  formData.config.x2 = null;
  formData.config.y2 = null;
};

const clearPosition = () => {
  formData.config.x = null;
  formData.config.y = null;
};

const base64ToBlob = (base64, type = "image/png") => {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i += 1) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  return new Blob([new Uint8Array(byteNumbers)], { type });
};

const buildImageBlob = async () => {
  if (!capturedImage.value || !selection.value || !imageRef.value) {
    return null;
  }

  // 图片元素只保存用户框选的区域，而不是整张截图。
  const img = imageRef.value;
  const sel = selection.value;
  const scaleX = imageSize.value.width / img.clientWidth;
  const scaleY = imageSize.value.height / img.clientHeight;
  const x1 = Math.min(sel.x1, sel.x2);
  const y1 = Math.min(sel.y1, sel.y2);
  const x2 = Math.max(sel.x1, sel.x2);
  const y2 = Math.max(sel.y1, sel.y2);
  const cropX = Math.round(x1 * scaleX);
  const cropY = Math.round(y1 * scaleY);
  const cropWidth = Math.round((x2 - x1) * scaleX);
  const cropHeight = Math.round((y2 - y1) * scaleY);

  const canvas = document.createElement("canvas");
  canvas.width = cropWidth;
  canvas.height = cropHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return null;
  }
  ctx.drawImage(
    img,
    cropX,
    cropY,
    cropWidth,
    cropHeight,
    0,
    0,
    cropWidth,
    cropHeight,
  );
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
};

const handleSubmit = async (resetAfterSave) => {
  // 三种元素类型的校验规则不同，提交前在前端先挡一层，减少无效请求。
  if (!formData.name.trim()) {
    ElMessage.warning(
      t("appAutomation.workbench.elements.elementNameRequired"),
    );
    return;
  }
  if (formData.element_type === "image") {
    if (!capturedImage.value) {
      ElMessage.warning(t("appAutomation.workbench.elements.captureRequired"));
      return;
    }
    if (!templateFileName.value.trim()) {
      ElMessage.warning(
        t("appAutomation.workbench.elements.templateFileRequired"),
      );
      return;
    }
    if (!formData.image_category) {
      ElMessage.warning(
        t("appAutomation.workbench.elements.imageCategoryRequired"),
      );
      return;
    }
    if (!hasRegion.value) {
      ElMessage.warning(
        t("appAutomation.workbench.elements.imageRegionRequired"),
      );
      return;
    }
  }
  if (formData.element_type === "pos" && !hasPos.value) {
    ElMessage.warning(t("appAutomation.workbench.elements.posRequired"));
    return;
  }
  if (formData.element_type === "region" && !hasRegion.value) {
    ElMessage.warning(t("appAutomation.workbench.elements.regionRequired"));
    return;
  }

  submitting.value = true;
  try {
    if (formData.element_type === "image") {
      const imageBlob = await buildImageBlob();
      if (!imageBlob) {
        ElMessage.error(
          t("appAutomation.workbench.elements.imageProcessFailed"),
        );
        return;
      }
      const file = new File([imageBlob], templateFileName.value.trim(), {
        type: "image/png",
      });
      const uploadResponse = await uploadAppElementImage(
        file,
        formData.image_category || "common",
      );
      if (!uploadResponse.data.success) {
        ElMessage.error(
          uploadResponse.data.message ||
            t("appAutomation.workbench.elements.imageUploadFailed"),
        );
        logOperation(
          t("appAutomation.workbench.elements.imageUploadFailed"),
          "error",
          uploadResponse.data,
        );
        return;
      }
      formData.config.image_path = uploadResponse.data.data.image_path;
      formData.config.file_hash = uploadResponse.data.data.file_hash;
    }

    const submitData = {
      name: formData.name.trim(),
      element_type: formData.element_type,
      project: formData.project || null,
      tags: formData.tags,
      config: {
        ...formData.config,
        image_category: formData.image_category || "common",
      },
    };

    await createAppElement(submitData);
    ElMessage.success(t("appAutomation.workbench.elements.createSuccess"));
    logOperation(
      `${t("appAutomation.workbench.elements.createSuccess")}: ${submitData.name}`,
      "success",
      submitData,
    );
    emit("created");
    if (resetAfterSave) {
      resetFormOnly();
    }
  } catch (error) {
    console.error("Create element failed:", error);
    ElMessage.error(
      error?.response?.data?.message ||
        error?.response?.data?.detail ||
        error.message ||
        t("appAutomation.workbench.elements.createFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.elements.createFailed")}: ${formData.name || t("appAutomation.workbench.elements.unnamedElement")}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    submitting.value = false;
  }
};

const handleCreateCategory = async () => {
  const name = newCategoryName.value.trim();
  if (!name) {
    ElMessage.warning(
      t("appAutomation.workbench.elements.categoryNameRequired"),
    );
    return;
  }
  creatingCategory.value = true;
  try {
    const response = await createAppImageCategory(name);
    if (!response.data.success) {
      ElMessage.error(
        response.data.message ||
          t("appAutomation.workbench.elements.categoryCreateFailed"),
      );
      return;
    }
    await loadImageCategories();
    formData.image_category = response.data.data.name;
    newCategoryName.value = "";
    createCategoryVisible.value = false;
    ElMessage.success(
      t("appAutomation.workbench.elements.categoryCreateSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.elements.categoryCreateSuccess")}: ${response.data.data.name}`,
      "success",
    );
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.elements.categoryCreateFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.elements.categoryCreateFailed")}: ${name}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    creatingCategory.value = false;
  }
};

watch(
  () => formData.element_type,
  (elementType) => {
    if (elementType === "pos") {
      clearSelection();
      return;
    }
    clearPosition();
  },
);

onMounted(async () => {
  await Promise.all([loadProjects(), loadImageCategories()]);
});
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
  flex-wrap: wrap;
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
  flex-direction: column;
  padding: 16px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
}

.capture-toolbar {
  width: 100%;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.capture-hint {
  font-size: 13px;
  color: #4b5563;
}

.form-pane {
  padding: 16px;
  overflow: auto;
}

.capture-stage {
  flex: 1;
  min-height: 0;
  width: 100%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-wrapper {
  position: relative;
  cursor: crosshair;
  display: flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  user-select: none;
}

.capture-image {
  display: block;
  width: auto;
  height: 100%;
  max-width: 100%;
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

.position-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.position-dot {
  display: block;
  width: 14px;
  height: 14px;
  border: 3px solid #ef4444;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.16);
}

.position-label {
  position: absolute;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(17, 24, 39, 0.82);
  color: #fff;
  font-size: 12px;
  white-space: nowrap;
}

.resize-handle {
  position: absolute;
  width: 10px;
  height: 10px;
  background: #fff;
  border: 1px solid #409eff;
  border-radius: 50%;
}

.resize-handle-nw {
  left: -6px;
  top: -6px;
  cursor: nwse-resize;
}
.resize-handle-n {
  left: calc(50% - 5px);
  top: -6px;
  cursor: ns-resize;
}
.resize-handle-ne {
  right: -6px;
  top: -6px;
  cursor: nesw-resize;
}
.resize-handle-e {
  right: -6px;
  top: calc(50% - 5px);
  cursor: ew-resize;
}
.resize-handle-se {
  right: -6px;
  bottom: -6px;
  cursor: nwse-resize;
}
.resize-handle-s {
  left: calc(50% - 5px);
  bottom: -6px;
  cursor: ns-resize;
}
.resize-handle-sw {
  left: -6px;
  bottom: -6px;
  cursor: nesw-resize;
}
.resize-handle-w {
  left: -6px;
  top: calc(50% - 5px);
  cursor: ew-resize;
}

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
