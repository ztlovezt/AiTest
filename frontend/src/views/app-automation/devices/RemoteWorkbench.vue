<template>
  <div class="remote-workbench-page">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          {{ t("appAutomation.workbench.common.back") }}
        </el-button>
        <div class="device-meta">
          <h2>{{ pageTitle }}</h2>
        </div>
        <div v-if="currentApp.package_name">
          {{ t("appAutomation.workbench.common.currentApp") }}:
          {{ currentApp.package_name }}
        </div>
      </div>
      <div class="toolbar-right">
        <el-button type="danger" @click="confirmEndSession">
          {{ t("appAutomation.workbench.common.endSession") }}
        </el-button>
      </div>
    </div>

    <div class="page-body">
      <div class="left-panel">
        <RemoteVideoPanel
          ref="videoPanelRef"
          :device-id="deviceId"
          @status-change="handleStatusChange"
          @session-ended="handleSessionEnded"
          @operation="appendWorkbenchEvent"
          @logcat-entry="appendLiveLogEntry"
          @logcat-status="handleLogStreamStatus"
        />
      </div>

      <div class="right-panel">
        <el-tabs v-model="activeTab" class="workbench-tabs" stretch>
          <el-tab-pane
            :label="t('appAutomation.workbench.tabs.elements')"
            name="elements"
            lazy
          >
            <ElementWorkbenchPanel
              :device-id="deviceId"
              :device-name="pageTitle"
              :capture-frame="captureRemoteFrame"
              @created="handleElementCreated"
              @operation="appendWorkbenchEvent"
            />
          </el-tab-pane>
          <el-tab-pane
            :label="t('appAutomation.workbench.tabs.apps')"
            name="apps"
            lazy
          >
            <AppManagePanel
              :device-id="deviceId"
              @current-app-change="handleCurrentAppChange"
              @operation="appendWorkbenchEvent"
            />
          </el-tab-pane>
          <el-tab-pane
            :label="t('appAutomation.workbench.tabs.deviceMetrics')"
            name="deviceMetrics"
            lazy
          >
            <DeviceMetricsPanel
              :device-id="deviceId"
              :active="activeTab === 'deviceMetrics'"
              @operation="appendWorkbenchEvent"
            />
          </el-tab-pane>
          <el-tab-pane
            :label="t('appAutomation.workbench.tabs.appMetrics')"
            name="appMetrics"
            lazy
          >
            <AppPerformancePanel
              :device-id="deviceId"
              :current-app="currentApp"
              :active="activeTab === 'appMetrics'"
              @operation="appendWorkbenchEvent"
              @current-app-change="handleCurrentAppChange"
            />
          </el-tab-pane>
          <el-tab-pane
            :label="t('appAutomation.workbench.tabs.logs')"
            name="logs"
            lazy
          >
            <DebugLogPanel
              :device-id="deviceId"
              :current-app="currentApp"
              :events="workbenchEvents"
              :active="activeTab === 'logs'"
              :live-log-entries="liveLogEntries"
              :log-stream-status="logStreamStatus"
              :update-log-subscription="updateLogSubscription"
              @clear-events="clearWorkbenchEvents"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import { ArrowLeft } from "@element-plus/icons-vue";
import AppManagePanel from "./components/AppManagePanel.vue";
import AppPerformancePanel from "./components/AppPerformancePanel.vue";
import DebugLogPanel from "./components/DebugLogPanel.vue";
import DeviceMetricsPanel from "./components/DeviceMetricsPanel.vue";
import ElementWorkbenchPanel from "./components/ElementWorkbenchPanel.vue";
import RemoteVideoPanel from "./components/RemoteVideoPanel.vue";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const videoPanelRef = ref(null);
const activeTab = ref("elements");
const currentApp = ref({ package_name: "", activity: "" });
const workbenchEvents = ref([]);
const liveLogEntries = ref([]);
const logStreamStatus = ref({
  state: "idle",
  connected: false,
  enabled: false,
  message: "",
});

const deviceId = computed(() => String(route.params.id || ""));
const pageTitle = computed(() =>
  String(
    route.query.name ||
      route.params.id ||
      t("appAutomation.workbench.common.title"),
  ),
);

const goBack = () => {
  if (window.history.length > 1) {
    router.back();
    return;
  }
  router.push({ name: "AppDeviceList" });
};

const handleStatusChange = () => {};

const handleCurrentAppChange = (appInfo) => {
  currentApp.value = appInfo || { package_name: "", activity: "" };
};

const appendWorkbenchEvent = (event) => {
  workbenchEvents.value = [
    ...workbenchEvents.value.slice(-199),
    {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: event?.timestamp || Date.now(),
      source: event?.source || "workbench",
      level: event?.level || "info",
      message:
        event?.message || t("appAutomation.workbench.common.defaultEvent"),
      extra: event?.extra || null,
    },
  ];
};

const clearWorkbenchEvents = () => {
  workbenchEvents.value = [];
};

const appendLiveLogEntry = (entry) => {
  if (!entry) {
    return;
  }
  liveLogEntries.value = [...liveLogEntries.value.slice(-799), entry];
};

const handleLogStreamStatus = (status) => {
  logStreamStatus.value = {
    ...logStreamStatus.value,
    ...(status || {}),
  };
};

const updateLogSubscription = (options) => {
  videoPanelRef.value?.updateLogSubscription?.(options);
};

const captureRemoteFrame = () =>
  videoPanelRef.value?.captureCurrentFrame?.() || null;

const handleElementCreated = () => {
  ElMessage.success(t("appAutomation.workbench.messages.elementSaved"));
};

const handleSessionEnded = () => {
  ElMessage.success(t("appAutomation.workbench.messages.sessionEnded"));
  appendWorkbenchEvent({
    source: "workbench",
    level: "info",
    message: t("appAutomation.workbench.messages.sessionEndedAndBack"),
  });
  goBack();
};

const confirmEndSession = async () => {
  try {
    await ElMessageBox.confirm(
      t("appAutomation.workbench.messages.confirmEndSession"),
      t("appAutomation.workbench.common.endSession"),
      {
        type: "warning",
        confirmButtonText: t("appAutomation.workbench.messages.confirmEnd"),
        cancelButtonText: t("appAutomation.common.cancel"),
      },
    );
    appendWorkbenchEvent({
      source: "workbench",
      level: "warning",
      message: t("appAutomation.workbench.messages.manualEndSession"),
    });
    videoPanelRef.value?.closeSession();
  } catch {
    // noop
  }
};

onMounted(() => {
  appendWorkbenchEvent({
    source: "workbench",
    level: "info",
    message: t("appAutomation.workbench.messages.workbenchOpened", {
      deviceId: deviceId.value,
    }),
  });
});
</script>

<style scoped lang="scss">
.remote-workbench-page {
  flex: 1;
  height: 100%;
  min-height: 0;
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  box-sizing: border-box;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px 0;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.device-meta h2 {
  margin: 0;
  font-size: 22px;
  color: #111827;
}

.toolbar-right {
  display: flex;
  gap: 10px;
}

.page-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(420px, 1.15fr) minmax(0, 1.65fr);
  gap: 12px;
  padding: 0 24px 20px;
  overflow: hidden;
  box-sizing: border-box;
}

.left-panel,
.right-panel {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.right-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  overflow: hidden;
}

.workbench-tabs {
  height: 100%;
  flex: 1;
  min-height: 0;
}

:deep(.workbench-tabs .el-tabs__header) {
  margin: 0;
  padding: 0 16px;
  border-bottom: 1px solid #edf2f7;
}

:deep(.workbench-tabs .el-tabs__content) {
  height: calc(100% - 56px);
  overflow: hidden;
}

:deep(.workbench-tabs .el-tab-pane) {
  height: 100%;
  padding: 16px;
  overflow: auto;
}

@media (max-width: 1280px) {
  .page-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-toolbar {
    flex-direction: column;
    align-items: stretch;
    padding: 16px 16px 0;
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
  }

  .toolbar-right {
    justify-content: flex-end;
  }

  .page-body {
    padding: 0 16px 16px;
  }
}
</style>
