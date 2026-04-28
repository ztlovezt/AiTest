<template>
  <div class="ops-log-page">
    <div class="page-header">
      <!-- <div> -->
        <h2>{{ $t("opsTools.log.title") }}</h2>
        <p>{{ $t("opsTools.log.subtitle") }}</p>
      <!-- </div> -->
    </div>

    <div class="workspace">
      <el-card shadow="never" class="left-panel">
        <template #header>
          <div class="panel-header">
            <span>{{ $t("opsTools.log.leftTitle") }}</span>
          </div>
        </template>

        <el-form label-position="top" class="left-panel__form">
          <el-form-item :label="$t('opsTools.log.environmentPlaceholder')">
            <el-select
              v-model="selectedEnvironmentId"
              filterable
              :placeholder="$t('opsTools.log.environmentPlaceholder')"
              @change="handleEnvironmentChange"
            >
              <el-option
                v-for="item in environments"
                :key="item.id"
                :label="`${item.name} (${item.env_code})`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item :label="$t('opsTools.log.directoryPlaceholder')">
            <el-select
              v-model="selectedDirectoryId"
              :disabled="!selectedEnvironmentId"
              :placeholder="$t('opsTools.log.directoryPlaceholder')"
              @change="handleDirectoryChange"
            >
              <el-option
                v-for="item in directoryOptions"
                :key="item.id"
                :label="`${item.name} (${item.path})`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <div class="left-panel__actions">
            <el-button
              type="primary"
              :disabled="!selectedEnvironmentId || !selectedDirectoryId"
              :loading="connecting"
              @click="connectEnvironment"
            >
              {{ connectionInfo.connected ? $t("opsTools.log.reconnect") : $t("opsTools.log.connect") }}
            </el-button>
            <el-button
              :disabled="!connectionInfo.connected"
              @click="disconnectEnvironment"
            >
              {{ $t("opsTools.log.disconnect") }}
            </el-button>
          </div>
        </el-form>

        <el-alert
          :title="connectionInfo.message || $t('opsTools.log.notConnected')"
          :type="connectionInfo.connected ? 'success' : 'info'"
          :closable="false"
          class="left-panel__alert"
        />

        <div class="tree-wrapper">
          <el-tree
            :key="treeKey"
            node-key="node_key"
            lazy
            :load="loadTreeNode"
            :props="{ label: 'label', isLeaf: 'isLeaf' }"
            :highlight-current="true"
            @node-click="handleNodeClick"
          >
            <template #default="{ data }">
              <div class="tree-node">
                <span class="tree-node__name">{{ data.label }}</span>
                <span v-if="!data.is_dir" class="tree-node__meta">
                  {{ formatSize(data.size) }}
                </span>
              </div>
            </template>
          </el-tree>
        </div>

        <div class="connection-card">
          <div class="connection-card__title">
            {{ $t("opsTools.log.connectionInfo") }}
          </div>
          <div class="connection-card__item">
            <span>{{ $t("opsTools.log.currentEnvironment") }}</span>
            <strong>{{ currentEnvironment?.name || "-" }}</strong>
          </div>
          <div class="connection-card__item">
            <span>{{ $t("opsTools.log.currentCategory") }}</span>
            <strong>{{ currentEnvironment?.category_name || "-" }}</strong>
          </div>
          <div class="connection-card__item">
            <span>{{ $t("opsTools.log.currentDirectory") }}</span>
            <strong>{{ currentDirectory?.path || "-" }}</strong>
          </div>
          <div class="connection-card__item">
            <span>{{ $t("opsTools.log.currentFile") }}</span>
            <strong>{{ selectedFile.name || "-" }}</strong>
          </div>
        </div>
      </el-card>

      <div class="right-panel">
        <el-card shadow="never" class="viewer-panel">
          <template #header>
            <div class="panel-header">
              <div>
                <div>{{ selectedFile.name || $t("opsTools.log.noFileSelected") }}</div>
                <!-- <div class="panel-meta">{{ selectedFile.path || "-" }}</div> -->
              </div>
              <div class="panel-meta">
                {{ filteredLogLines.length }} {{ $t("opsTools.log.lines") }}
              </div>
            </div>
          </template>

          <div class="toolbar">
            <div class="keyword-box">
              <el-tag
                v-for="item in keywords"
                :key="item.value"
                closable
                :style="{ backgroundColor: item.color, borderColor: item.color, color: '#fff' }"
                @close="removeKeyword(item.value)"
              >
                {{ item.value }}
              </el-tag>
              <el-input
                v-model="keywordInput"
                :placeholder="$t('opsTools.log.keywordPlaceholder')"
                @keyup.enter="addKeyword"
              />
              <el-button @click="addKeyword">
                {{ $t("opsTools.log.addKeyword") }}
              </el-button>
              <el-button @click="clearKeywords">
                {{ $t("opsTools.log.clearKeywords") }}
              </el-button>
            </div>

            <div class="toolbar__actions">
              <el-select v-model="lineCount" style="width: 140px" @change="reloadSelectedFile">
                <el-option :label="$t('opsTools.log.lastLines', { count: 100 })" :value="100" />
                <el-option :label="$t('opsTools.log.lastLines', { count: 200 })" :value="200" />
                <el-option :label="$t('opsTools.log.lastLines', { count: 500 })" :value="500" />
                <el-option :label="$t('opsTools.log.lastLines', { count: 800 })" :value="800" />
              </el-select>
              <el-switch
                v-model="realtimeEnabled"
                :active-text="$t('opsTools.log.realtime')"
                :disabled="!selectedFile.path || !connectionInfo.connected"
              />
              <el-select v-model="pollInterval" style="width: 120px" :disabled="!realtimeEnabled">
                <el-option :label="$t('opsTools.log.interval', { count: 2 })" :value="2000" />
                <el-option :label="$t('opsTools.log.interval', { count: 5 })" :value="5000" />
                <el-option :label="$t('opsTools.log.interval', { count: 10 })" :value="10000" />
              </el-select>
              <el-button :disabled="!selectedFile.path" @click="reloadSelectedFile">
                {{ $t("common.refresh") }}
              </el-button>
              <el-button :disabled="!selectedFile.path" @click="handleDownload">
                {{ $t("opsTools.log.download") }}
              </el-button>
              <el-button @click="clearOperationLogs">
                {{ $t("opsTools.log.clearOperations") }}
              </el-button>
            </div>
          </div>

          <div v-if="!connectionInfo.connected && !operationLogs.length" class="empty-state">
            {{ $t("opsTools.log.manualConnectHint") }}
          </div>
          <div v-else-if="!selectedFile.path && !operationLogs.length" class="empty-state">
            {{ $t("opsTools.log.emptyState") }}
          </div>
          <div v-else class="viewer-content">
            <!-- <div class="viewer-meta">
              <span>{{ $t("opsTools.log.fileSize") }}: {{ formatSize(contentMeta.size || 0) }}</span>
              <span>{{ $t("opsTools.log.keywordCount") }}: {{ keywords.length }}</span>
              <span>{{ $t("opsTools.log.operationsTitle") }}: {{ operationLogs.length }}</span>
              <span>{{ $t("opsTools.log.displayLimit", { count: MAX_RENDERED_LOG_LINES }) }}</span>
            </div> -->
            <div class="log-console">
              <template v-for="entry in consoleEntries" :key="entry.key">
                <div
                  v-if="entry.type === 'operation'"
                  class="console-row console-row--operation"
                  :class="`is-${entry.level}`"
                >
                  <span class="console-row__time">{{ entry.time }}</span>
                  <span class="console-row__message">{{ entry.message }}</span>
                </div>
                <div
                  v-else
                  class="console-row console-row--log"
                  v-html="highlightLine(entry.line)"
                />
              </template>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  browseOpsLogDirectory,
  connectOpsLogEnvironment,
  disconnectOpsLogEnvironment,
  downloadOpsLogFile,
  getOpsLogContent,
  getOpsLogEnvironments,
} from "@/api/ops-tools";

const { t } = useI18n();
const MAX_RENDERED_LOG_LINES = 800;
const MAX_OPERATION_LOGS = 80;

const environments = ref([]);
const directoryOptions = ref([]);
const selectedEnvironmentId = ref();
const selectedDirectoryId = ref();
const currentPath = ref("");
const selectedFile = ref({});
const contentMeta = ref({});
const logLines = ref([]);
const keywordInput = ref("");
const keywords = ref([]);
const lineCount = ref(200);
const pollInterval = ref(5000);
const realtimeEnabled = ref(false);
const connecting = ref(false);
const treeKey = ref(0);
const operationLogs = ref([]);
const connectionInfo = ref({
  connected: false,
  message: "",
});

let pollTimer = null;

const keywordPalette = [
  "#ef4444",
  "#f59e0b",
  "#10b981",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
];

const currentEnvironment = computed(() =>
  environments.value.find((item) => item.id === selectedEnvironmentId.value),
);

const currentDirectory = computed(() =>
  directoryOptions.value.find((item) => item.id === selectedDirectoryId.value),
);

const filteredLogLines = computed(() => {
  if (!keywords.value.length) {
    return logLines.value;
  }
  return logLines.value.filter((line) =>
    keywords.value.some((item) => line.includes(item.value)),
  );
});

const consoleEntries = computed(() => {
  const operationEntries = [...operationLogs.value]
    .reverse()
    .map((item) => ({
      key: item.id,
      type: "operation",
      level: item.type,
      time: item.time,
      message: item.message,
    }));
  const logEntries = filteredLogLines.value.map((line, index) => ({
    key: `log-${index}-${line.slice(0, 16)}`,
    type: "log",
    line,
  }));
  return [...operationEntries, ...logEntries];
});

function appendOperation(type, message) {
  operationLogs.value.unshift({
    id: `${Date.now()}-${Math.random()}`,
    type,
    time: new Date().toLocaleTimeString(),
    message,
  });
  operationLogs.value = operationLogs.value.slice(0, MAX_OPERATION_LOGS);
}

function clearOperationLogs() {
  operationLogs.value = [];
}

function clearRealtimeTimer() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function resetFileState() {
  currentPath.value = "";
  selectedFile.value = {};
  contentMeta.value = {};
  logLines.value = [];
  realtimeEnabled.value = false;
  clearRealtimeTimer();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightLine(line) {
  let output = escapeHtml(line);
  const sortedKeywords = [...keywords.value].sort(
    (left, right) => right.value.length - left.value.length,
  );
  sortedKeywords.forEach((item) => {
    const regex = new RegExp(escapeRegExp(item.value), "gi");
    output = output.replace(
      regex,
      `<span class="log-mark" style="background:${item.color};">${item.value}</span>`,
    );
  });
  return output;
}

function addKeyword() {
  const value = keywordInput.value.trim();
  if (!value) {
    return;
  }
  if (keywords.value.some((item) => item.value === value)) {
    keywordInput.value = "";
    return;
  }
  const color = keywordPalette[keywords.value.length % keywordPalette.length];
  keywords.value.push({ value, color });
  keywordInput.value = "";
}

function removeKeyword(value) {
  keywords.value = keywords.value.filter((item) => item.value !== value);
}

function clearKeywords() {
  keywords.value = [];
}

async function loadEnvironments() {
  try {
    const response = await getOpsLogEnvironments();
    environments.value = response.data || [];
    selectedEnvironmentId.value = undefined;
    selectedDirectoryId.value = undefined;
    directoryOptions.value = [];
    connectionInfo.value.message = t("opsTools.log.manualConnectHint");
  } catch {
    ElMessage.error(t("opsTools.messages.loadEnvironmentFailed"));
  }
}

function handleEnvironmentChange() {
  const environment = currentEnvironment.value;
  directoryOptions.value = environment?.category_directories || [];
  selectedDirectoryId.value = directoryOptions.value[0]?.id;
  resetFileState();
  treeKey.value += 1;
  connectionInfo.value = {
    connected: false,
    message: t("opsTools.log.manualConnectHint"),
  };
}

function handleDirectoryChange() {
  resetFileState();
  treeKey.value += 1;
  connectionInfo.value = {
    connected: false,
    message: t("opsTools.log.manualConnectHint"),
  };
}

async function connectEnvironment() {
  if (!selectedEnvironmentId.value || !selectedDirectoryId.value) {
    return;
  }
  connecting.value = true;
  try {
    const response = await connectOpsLogEnvironment({
      environment_id: selectedEnvironmentId.value,
      directory_id: selectedDirectoryId.value,
    });
    directoryOptions.value = response.data.directories || directoryOptions.value;
    connectionInfo.value = {
      connected: !!response.data.connection?.success,
      message: response.data.connection?.message || t("opsTools.log.notConnected"),
    };
    treeKey.value += 1;
    appendOperation(
      connectionInfo.value.connected ? "success" : "error",
      connectionInfo.value.message,
    );
  } catch (error) {
    connectionInfo.value = {
      connected: false,
      message: error?.response?.data?.detail || t("opsTools.messages.connectFailed"),
    };
    appendOperation("error", connectionInfo.value.message);
  } finally {
    connecting.value = false;
  }
}

async function disconnectEnvironment() {
  if (!selectedEnvironmentId.value) {
    return;
  }
  try {
    await disconnectOpsLogEnvironment({
      environment_id: selectedEnvironmentId.value,
      directory_id: selectedDirectoryId.value,
    });
  } catch {
    // 后端断开只负责释放会话，这里仍然继续清理前端状态。
  }
  connectionInfo.value = {
    connected: false,
    message: t("opsTools.log.disconnected"),
  };
  treeKey.value += 1;
  resetFileState();
  appendOperation("info", t("opsTools.log.disconnected"));
}

async function loadTreeNode(node, resolve) {
  if (!connectionInfo.value.connected || !selectedEnvironmentId.value || !selectedDirectoryId.value) {
    resolve([]);
    return;
  }
  const path = node.level === 0 ? "" : node.data.path;
  try {
    const response = await browseOpsLogDirectory({
      environment_id: selectedEnvironmentId.value,
      directory_id: selectedDirectoryId.value,
      path,
    });
    currentPath.value = response.data.current_path || path;
    const nodes = (response.data.items || []).map((item) => ({
      ...item,
      label: item.name,
      isLeaf: !item.is_dir,
      node_key: item.path || item.name,
    }));
    resolve(nodes);
    if (node.level === 0) {
      appendOperation("info", t("opsTools.log.directoryLoaded", { count: nodes.length }));
    }
  } catch (error) {
    appendOperation(
      "error",
      error?.response?.data?.detail || t("opsTools.messages.loadLogFailed"),
    );
    resolve([]);
  }
}

async function handleNodeClick(data) {
  if (data.is_dir) {
    return;
  }
  selectedFile.value = data;
  await loadFileContent(data.path);
}

async function loadFileContent(path, silent = false) {
  if (!connectionInfo.value.connected || !path) {
    return;
  }
  try {
    const response = await getOpsLogContent({
      environment_id: selectedEnvironmentId.value,
      directory_id: selectedDirectoryId.value,
      path,
      lines: Math.min(lineCount.value, MAX_RENDERED_LOG_LINES),
    });
    selectedFile.value = {
      path: response.data.path,
      name: response.data.name,
    };
    contentMeta.value = response.data;
    logLines.value = (response.data.lines || []).slice(-MAX_RENDERED_LOG_LINES);
    if (!silent) {
      appendOperation(
        "success",
        t("opsTools.log.fileLoaded", {
          name: response.data.name,
          count: response.data.line_count,
        }),
      );
    }
  } catch (error) {
    appendOperation(
      "error",
      error?.response?.data?.detail || t("opsTools.messages.loadLogFailed"),
    );
  }
}

function reloadSelectedFile() {
  if (selectedFile.value.path) {
    loadFileContent(selectedFile.value.path);
  }
}

async function handleDownload() {
  if (!selectedFile.value.path) {
    return;
  }
  try {
    const response = await downloadOpsLogFile({
      environment_id: selectedEnvironmentId.value,
      directory_id: selectedDirectoryId.value,
      path: selectedFile.value.path,
    });
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = selectedFile.value.name || "log.txt";
    link.click();
    window.URL.revokeObjectURL(url);
    appendOperation("success", t("opsTools.log.downloadSuccess"));
  } catch {
    ElMessage.error(t("opsTools.messages.downloadFailed"));
  }
}

function startRealtime() {
  clearRealtimeTimer();
  if (!realtimeEnabled.value || !selectedFile.value.path) {
    return;
  }
  pollTimer = setInterval(() => {
    loadFileContent(selectedFile.value.path, true);
  }, pollInterval.value);
  appendOperation("info", t("opsTools.log.realtimeStarted"));
}

function formatSize(size) {
  if (!size) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

watch(
  () => [realtimeEnabled.value, pollInterval.value, selectedFile.value.path],
  () => {
    if (realtimeEnabled.value && selectedFile.value.path) {
      startRealtime();
    } else {
      clearRealtimeTimer();
    }
  },
  { deep: true },
);

watch(
  () => keywords.value.map((item) => item.value).join(","),
  () => {
    if (selectedFile.value.path) {
      appendOperation("info", t("opsTools.log.keywordUpdated"));
    }
  },
);

onMounted(loadEnvironments);
onBeforeUnmount(clearRealtimeTimer);
</script>

<style scoped lang="scss">
.ops-log-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: hidden;
}

.page-header {
  display: flex;
  flex-direction: row;
  gap: 16px;
  flex-shrink: 0;

  h2 {
    margin: 0;
    font-size: 24px;
  }

  p {
    margin: 8px 0 0;
    color: var(--th-color-text-secondary);
  }
}

.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.left-panel,
.right-panel {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.left-panel,
.viewer-panel {
  height: 100%;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.left-panel,
.viewer-panel {
  :deep(.el-card) {
    height: 100%;
  }

  :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
}

.left-panel__form {
  flex-shrink: 0;

  :deep(.el-form-item) {
    margin-bottom: 14px;
  }
}

.left-panel__actions {
  display: flex;
  gap: 12px;
}

.left-panel__alert {
  margin: 12px 0;
}

.tree-wrapper {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 0;
  border: 1px solid var(--th-border-color-light);
  border-radius: 12px;
}

.tree-node {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}

.tree-node__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-node__meta,
.panel-meta,
.viewer-meta {
  color: var(--th-color-text-secondary);
  font-size: 12px;
}

.connection-card {
  margin-top: 14px;
  flex-shrink: 0;
  padding: 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.04);
}

.connection-card__title {
  font-weight: 600;
  margin-bottom: 12px;
}

.connection-card__item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;

  span {
    color: var(--th-color-text-secondary);
  }

  strong {
    max-width: 180px;
    text-align: right;
    word-break: break-all;
  }
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
  padding-bottom: 6px;
}

.keyword-box {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;

  .el-input {
    width: 220px;
  }
}

.toolbar__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.viewer-panel {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.viewer-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  gap: 12px;
}

.viewer-meta {
  flex-shrink: 0;
}

.log-console {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 18px;
  border-radius: 4px;
  background: #141414;
  color: #d7f9e9;
  font-family: Consolas, "Courier New", monospace;
  line-height: 1.7;
}

.console-row {
  white-space: pre-wrap;
  word-break: break-word;
}

.console-row--operation {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.2);
}

.console-row--operation.is-success {
  color: #10b981;
}

.console-row--operation.is-error {
  color: #ef4444;
}

.console-row--operation.is-info {
  color: #3b82f6;
}

.console-row__time {
  color: var(--th-color-text-secondary);
}

.empty-state {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 0;
  color: var(--th-color-text-secondary);
}

:deep(.log-mark) {
  color: #fff;
  padding: 0 4px;
  border-radius: 4px;
}

@media (max-width: 1200px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-direction: column;
  }
}
</style>
