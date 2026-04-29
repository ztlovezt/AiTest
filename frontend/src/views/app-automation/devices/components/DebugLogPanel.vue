<template>
  <div class="debug-log-panel">
    <div class="panel-header">
      <div>
        <h4>{{ t("appAutomation.workbench.logs.panelTitle") }}</h4>
        <p>{{ t("appAutomation.workbench.logs.panelDescription") }}</p>
      </div>
      <div class="header-actions">
        <el-tag :type="streamTagType" effect="plain">
          {{ streamStatusText }}
        </el-tag>
        <el-switch
          v-model="autoRefresh"
          :active-text="t('appAutomation.workbench.logs.autoRefresh')"
        />
        <el-select v-model="intervalMs" style="width: 120px">
          <el-option :value="3000" label="3s" />
          <el-option :value="5000" label="5s" />
          <el-option :value="8000" label="8s" />
        </el-select>
        <el-button :loading="loading" @click="loadLogs">
          {{ t("appAutomation.workbench.logs.refreshHistory") }}
        </el-button>
      </div>
    </div>

    <div class="toolbar-row">
      <el-radio-group v-model="scope">
        <el-radio-button value="device">
          {{ t("appAutomation.workbench.logs.scopeDevice") }}
        </el-radio-button>
        <el-radio-button value="app">
          {{ t("appAutomation.workbench.logs.scopeApp") }}
        </el-radio-button>
      </el-radio-group>
      <el-select
        v-model="packageName"
        filterable
        clearable
        :placeholder="t('appAutomation.workbench.logs.packagePlaceholder')"
        style="min-width: 260px"
        :disabled="scope === 'device'"
      >
        <el-option
          v-for="pkg in installedPackages"
          :key="pkg"
          :label="pkg"
          :value="pkg"
        />
      </el-select>
      <el-select
        v-model="level"
        clearable
        :placeholder="t('appAutomation.workbench.logs.levelPlaceholder')"
        style="width: 110px"
      >
        <el-option
          :label="t('appAutomation.workbench.logs.levels.all')"
          value=""
        />
        <el-option
          :label="t('appAutomation.workbench.logs.levels.info')"
          value="I"
        />
        <el-option
          :label="t('appAutomation.workbench.logs.levels.warn')"
          value="W"
        />
        <el-option
          :label="t('appAutomation.workbench.logs.levels.error')"
          value="E"
        />
      </el-select>
      <el-input
        v-model="keyword"
        clearable
        :placeholder="t('appAutomation.workbench.logs.keywordPlaceholder')"
        style="max-width: 220px"
      />
      <el-select v-model="lines" style="width: 120px">
        <el-option
          :value="200"
          :label="t('appAutomation.workbench.logs.linesUnit', { count: 200 })"
        />
        <el-option
          :value="400"
          :label="t('appAutomation.workbench.logs.linesUnit', { count: 400 })"
        />
        <el-option
          :value="800"
          :label="t('appAutomation.workbench.logs.linesUnit', { count: 800 })"
        />
      </el-select>
      <el-button @click="copyLogs">
        {{ t("appAutomation.workbench.logs.copy") }}
      </el-button>
      <el-button @click="exportLogs">
        {{ t("appAutomation.workbench.logs.export") }}
      </el-button>
      <el-button type="warning" @click="clearDeviceLogs">
        {{ t("appAutomation.workbench.logs.clearDeviceLogs") }}
      </el-button>
      <el-button @click="$emit('clear-events')">
        {{ t("appAutomation.workbench.logs.clearEvents") }}
      </el-button>
    </div>

    <el-alert
      v-if="streamMessage"
      class="panel-alert"
      type="info"
      :closable="false"
      :title="streamMessage"
    />

    <el-alert
      v-if="errorMessage"
      class="panel-alert"
      type="error"
      :closable="false"
      :title="errorMessage"
    />

    <div class="log-grid">
      <el-card shadow="never" class="log-card">
        <template #header>
          <div class="card-header">
            <span>{{ t("appAutomation.workbench.logs.eventCardTitle") }}</span>
            <span class="card-meta">
              {{
                t("appAutomation.workbench.logs.itemsUnit", {
                  count: operationEvents.length,
                })
              }}
            </span>
          </div>
        </template>
        <div ref="eventListRef" class="log-list">
          <div v-if="!operationEvents.length" class="empty-log">
            {{ t("appAutomation.workbench.logs.noEvents") }}
          </div>
          <div
            v-for="event in operationEvents"
            :key="event.id"
            class="event-row"
            :class="`level-${event.level || 'info'}`"
          >
            <div class="event-top">
              <span class="event-source">{{ sourceText(event.source) }}</span>
              <span class="event-time">{{ formatTime(event.timestamp) }}</span>
            </div>
            <div class="event-message">{{ event.message }}</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="log-card">
        <template #header>
          <div class="card-header">
            <span>
              {{
                scope === "app"
                  ? t("appAutomation.workbench.logs.appLogCardTitle")
                  : t("appAutomation.workbench.logs.deviceLogCardTitle")
              }}
            </span>
            <span class="card-meta">
              {{
                t("appAutomation.workbench.logs.lineCountWithStatus", {
                  count: deviceLogs.length,
                  status: streamStatusText,
                })
              }}
            </span>
          </div>
        </template>
        <div ref="deviceLogListRef" class="log-list mono">
          <div v-if="!deviceLogs.length" class="empty-log">
            {{ t("appAutomation.workbench.logs.noLogs") }}
          </div>
          <div
            v-for="(log, index) in deviceLogs"
            :key="log._key || `${log.time}-${log.pid}-${index}`"
            class="device-log-row"
            :class="`priority-${(log.priority || 'I').toLowerCase()}`"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-priority">{{ log.priority }}</span>
            <span class="log-tag">{{ log.tag }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  clearDeviceLogcat,
  getDeviceLogcat,
  getInstalledDevicePackages,
} from "@/api/app-automation";

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
  currentApp: {
    type: Object,
    default: () => ({ package_name: "", activity: "" }),
  },
  events: {
    type: Array,
    default: () => [],
  },
  active: {
    type: Boolean,
    default: false,
  },
  liveLogEntries: {
    type: Array,
    default: () => [],
  },
  logStreamStatus: {
    type: Object,
    default: () => ({}),
  },
  updateLogSubscription: {
    type: Function,
    default: null,
  },
});

defineEmits(["clear-events"]);

const { t, locale } = useI18n();

const loading = ref(false);
const autoRefresh = ref(true);
const intervalMs = ref(5000);
const scope = ref("device");
const level = ref("");
const keyword = ref("");
const lines = ref(200);
const packageName = ref("");
const installedPackages = ref([]);
const deviceLogs = ref([]);
const errorMessage = ref("");
const deviceLogListRef = ref(null);
const eventListRef = ref(null);
const pageVisible = ref(
  typeof document === "undefined" ? true : !document.hidden,
);

let pollTimer = null;
let processedLiveLogCount = 0;

const operationEvents = computed(() => props.events.slice().reverse());
const streamMessage = computed(() => props.logStreamStatus?.message || "");
const streamTagType = computed(() => {
  const state = props.logStreamStatus?.state;
  if (state === "streaming") return "success";
  if (state === "error") return "danger";
  if (state === "pending" || state === "reconnecting") return "warning";
  return "info";
});

const streamStatusText = computed(() =>
  t(
    `appAutomation.workbench.logs.status.${props.logStreamStatus?.state || "idle"}`,
  ),
);

const timeLocale = computed(() =>
  String(locale.value || "")
    .toLowerCase()
    .startsWith("zh")
    ? "zh-CN"
    : "en-US",
);

const formatTime = (timestamp) => {
  const value = Number(timestamp);
  if (!Number.isFinite(value)) {
    return "-";
  }
  return new Date(value).toLocaleTimeString(timeLocale.value, {
    hour12: false,
  });
};

const sourceText = (source) => {
  const mapping = {
    remote: "remote",
    apps: "apps",
    elements: "elements",
    "device-metrics": "deviceMetrics",
    "app-metrics": "appMetrics",
    workbench: "workbench",
  };
  return t(
    `appAutomation.workbench.logs.sources.${mapping[source] || "workbench"}`,
  );
};

const currentPackageName = () => {
  if (scope.value !== "app") {
    return "";
  }
  return String(
    packageName.value || props.currentApp?.package_name || "",
  ).trim();
};

const normalizeLogItem = (item) => {
  if (!item) {
    return null;
  }
  const normalized = {
    ...item,
    time: item.time || "",
    pid: item.pid || "",
    tid: item.tid || "",
    priority: item.priority || "I",
    tag: item.tag || "",
    message: item.message || "",
    raw:
      item.raw ||
      `${item.time || ""} ${item.priority || "I"} ${item.tag || ""}: ${item.message || ""}`.trim(),
  };
  normalized._key = [
    normalized.time,
    normalized.pid,
    normalized.tid,
    normalized.priority,
    normalized.tag,
    normalized.message,
  ].join("|");
  return normalized;
};

const mergeLogLines = (items, { replace = false } = {}) => {
  const incoming = (items || []).map(normalizeLogItem).filter(Boolean);
  const merged = replace ? [] : deviceLogs.value.slice();
  const seen = new Set(merged.map((item) => item._key));

  for (const item of incoming) {
    if (seen.has(item._key)) {
      continue;
    }
    merged.push(item);
    seen.add(item._key);
  }

  deviceLogs.value = merged.slice(-Number(lines.value || 200));
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const syncPolling = () => {
  stopPolling();
  if (!props.active || !autoRefresh.value || !pageVisible.value) {
    return;
  }
  pollTimer = setInterval(() => {
    loadLogs({ silent: true });
  }, intervalMs.value);
};

const syncStreamSubscription = () => {
  if (typeof props.updateLogSubscription !== "function") {
    return;
  }
  props.updateLogSubscription({
    enabled: props.active && pageVisible.value,
    scope: scope.value,
    packageName: currentPackageName(),
    level: level.value,
    keyword: keyword.value,
    lines: lines.value,
  });
};

const handleVisibilityChange = () => {
  pageVisible.value = !document.hidden;
  if (!pageVisible.value) {
    stopPolling();
    syncStreamSubscription();
    return;
  }
  if (props.active) {
    loadLogs({ silent: true });
  }
  syncPolling();
  syncStreamSubscription();
};

const scrollToBottom = async (targetRef) => {
  await nextTick();
  const el = targetRef.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
};

const loadInstalledPackages = async () => {
  try {
    const response = await getInstalledDevicePackages(props.deviceId);
    installedPackages.value = response.data?.data || [];
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.message ||
      error.message ||
      t("appAutomation.workbench.logs.loadPackagesFailed");
  }
};

const loadLogs = async ({ silent = false } = {}) => {
  loading.value = !silent;
  try {
    const response = await getDeviceLogcat(props.deviceId, {
      scope: scope.value,
      package_name: currentPackageName(),
      level: level.value,
      keyword: keyword.value,
      lines: lines.value,
    });
    mergeLogLines(response.data?.data?.lines || [], { replace: true });
    errorMessage.value = "";
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.message ||
      error.message ||
      t("appAutomation.workbench.logs.loadLogsFailed");
    if (!silent) {
      ElMessage.error(errorMessage.value);
    }
  } finally {
    loading.value = false;
  }
};

const clearDeviceLogs = async () => {
  try {
    await clearDeviceLogcat(props.deviceId);
    deviceLogs.value = [];
    ElMessage.success(t("appAutomation.workbench.logs.clearSuccess"));
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.logs.clearFailed"),
    );
  }
};

const copyLogs = async () => {
  const payload = deviceLogs.value.map((item) => item.raw).join("\n");
  if (!payload) {
    ElMessage.warning(t("appAutomation.workbench.logs.copyEmpty"));
    return;
  }
  try {
    await navigator.clipboard.writeText(payload);
    ElMessage.success(t("appAutomation.workbench.logs.copySuccess"));
  } catch (error) {
    ElMessage.error(
      t("appAutomation.workbench.logs.copyFailed", {
        message: error?.message || "clipboard unavailable",
      }),
    );
  }
};

const exportLogs = () => {
  const payload = deviceLogs.value.map((item) => item.raw).join("\n");
  const blob = new Blob([payload], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `device-log-${props.deviceId}-${Date.now()}.txt`;
  link.click();
  URL.revokeObjectURL(url);
};

watch(
  () => props.currentApp?.package_name,
  (value) => {
    if (scope.value === "app" && value && !packageName.value) {
      packageName.value = value;
    }
  },
  { immediate: true },
);

watch(scope, async (value) => {
  if (value === "app" && !packageName.value && props.currentApp?.package_name) {
    packageName.value = props.currentApp.package_name;
  }
  if (props.active) {
    await loadLogs({ silent: true });
  }
  syncStreamSubscription();
});

watch([autoRefresh, intervalMs], syncPolling);

watch([level, keyword, lines, packageName], async () => {
  if (props.active) {
    await loadLogs({ silent: true });
    syncPolling();
  }
  syncStreamSubscription();
});

watch(deviceLogs, () => {
  scrollToBottom(deviceLogListRef);
});

watch(operationEvents, () => {
  scrollToBottom(eventListRef);
});

watch(
  () => props.liveLogEntries.length,
  () => {
    if (props.liveLogEntries.length < processedLiveLogCount) {
      processedLiveLogCount = 0;
    }
    const delta = props.liveLogEntries.slice(processedLiveLogCount);
    processedLiveLogCount = props.liveLogEntries.length;
    if (!delta.length) {
      return;
    }
    mergeLogLines(delta);
  },
);

watch(
  () => props.active,
  async (active) => {
    if (active) {
      if (!installedPackages.value.length) {
        await loadInstalledPackages();
      }
      await loadLogs({ silent: true });
      syncPolling();
      syncStreamSubscription();
    } else {
      stopPolling();
      syncStreamSubscription();
    }
  },
  { immediate: true },
);

onMounted(() => {
  if (props.currentApp?.package_name) {
    packageName.value = props.currentApp.package_name;
  }
  document.addEventListener("visibilitychange", handleVisibilityChange);
});

onUnmounted(() => {
  stopPolling();
  document.removeEventListener("visibilitychange", handleVisibilityChange);
  if (typeof props.updateLogSubscription === "function") {
    props.updateLogSubscription({ enabled: false });
  }
});
</script>

<style scoped>
.debug-log-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header,
.toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.panel-header h4 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.panel-header p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.header-actions,
.toolbar-row {
  flex-wrap: wrap;
}

.panel-alert {
  margin-top: -4px;
}

.log-grid {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
}

.log-card {
  border-radius: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.card-meta {
  color: #6b7280;
  font-size: 12px;
}

.log-list {
  height: 560px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mono {
  font-family: Consolas, monospace;
  font-size: 12px;
}

.empty-log {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.event-row {
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.event-row.level-success {
  border-color: rgba(22, 163, 74, 0.2);
}

.event-row.level-warning {
  border-color: rgba(245, 158, 11, 0.25);
}

.event-row.level-error {
  border-color: rgba(220, 38, 38, 0.22);
}

.event-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
}

.event-message {
  margin-top: 8px;
  color: #111827;
  line-height: 1.6;
}

.device-log-row {
  display: grid;
  grid-template-columns: 110px 32px 180px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f8fafc;
  color: #0f172a;
}

.priority-e,
.priority-f {
  background: rgba(254, 226, 226, 0.85);
}

.priority-w {
  background: rgba(254, 243, 199, 0.85);
}

.priority-i {
  background: rgba(239, 246, 255, 0.85);
}

.log-tag {
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-message {
  word-break: break-word;
}

@media (max-width: 1200px) {
  .log-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .panel-header,
  .toolbar-row {
    flex-direction: column;
  }

  .device-log-row {
    grid-template-columns: 1fr;
  }
}
</style>
