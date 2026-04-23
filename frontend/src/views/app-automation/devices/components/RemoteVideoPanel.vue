<template>
  <div class="remote-video-panel">
    <div class="panel-toolbar">
      <div class="status-group">
        <el-tag :type="isConnected ? 'success' : 'info'" effect="plain">
          {{
            isConnected
              ? t("appAutomation.workbench.video.connected")
              : t("appAutomation.workbench.video.connecting")
          }}
        </el-tag>
        <span class="session-timer">{{ formatDuration(sessionDuration) }}</span>
      </div>
      <div class="toolbar-actions">
        <div class="quality-inline">
          <span class="quality-label">{{
            t("appAutomation.workbench.video.quality")
          }}</span>
          <el-tooltip :content="currentPresetTooltip" placement="top">
            <el-select
              v-model="selectedPreset"
              size="small"
              style="min-width: 90px; width: 120px"
              @change="switchPreset"
            >
              <el-option
                v-for="preset in qualitySelectOptions"
                :key="preset.value"
                :label="preset.label"
                :value="preset.value"
              />
            </el-select>
          </el-tooltip>
        </div>
        <div v-if="isConnected" class="zoom-inline">
          <el-button circle size="small" @click="zoomOut">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
          <span class="zoom-text">{{ Math.round(zoomLevel * 100) }}%</span>
          <el-button circle size="small" @click="zoomIn">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
        </div>
        <el-button size="small" @click="toggleFullscreen">
          <el-icon><FullScreen /></el-icon>
          {{ t("appAutomation.workbench.video.fullscreen") }}
        </el-button>
      </div>
    </div>

    <div ref="videoContainerRef" class="video-wrapper">
      <div class="video-stage">
        <div v-if="!isConnected && !videoReady" class="status-overlay">
          <el-icon class="loading-icon" :size="40"><Loading /></el-icon>
          <p>{{ connectionMessage }}</p>
        </div>
        <div v-else-if="isConnected && !videoReady" class="status-overlay">
          <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
          <p>{{ t("appAutomation.workbench.video.videoLoading") }}</p>
        </div>

        <video
          ref="videoRef"
          autoplay
          muted
          webkit-playsinline
          playsinline
          tabindex="0"
        ></video>
      </div>

      <div v-show="isConnected" class="bottom-controls">
        <el-button circle size="large" @click="sendKeyCommand('back')">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-button circle size="large" @click="sendKeyCommand('home')">
          <el-icon><HomeFilled /></el-icon>
        </el-button>
        <el-button circle size="large" @click="sendKeyCommand('menu')">
          <el-icon><Menu /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  ArrowLeft,
  FullScreen,
  HomeFilled,
  Loading,
  Menu,
  ZoomIn,
  ZoomOut,
} from "@element-plus/icons-vue";
import { getDevicePerformanceSnapshot } from "@/api/app-automation";

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
});

const emit = defineEmits([
  "status-change",
  "session-ended",
  "operation",
  "logcat-entry",
  "logcat-status",
]);

const { t } = useI18n();

const qualityPresetOptions = [
  { value: "smooth", key: "smooth" },
  { value: "balanced", key: "balanced" },
  { value: "clarity", key: "clarity" },
];

const presetConfigMap = {
  smooth: {
    maxSize: 720,
    maxFps: 24,
    videoBitRate: 2000000,
    labelKey: "smooth",
  },
  balanced: {
    maxSize: 900,
    maxFps: 30,
    videoBitRate: 3000000,
    labelKey: "balanced",
  },
  clarity: {
    maxSize: 1080,
    maxFps: 45,
    videoBitRate: 6000000,
    labelKey: "clarity",
  },
};

const isConnected = ref(false);
const videoReady = ref(false);
const connectionMessage = ref(
  t("appAutomation.workbench.video.connectingDevice"),
);
const zoomLevel = ref(1);
const sessionDuration = ref(0);
const sessionStartTime = ref(null);
const selectedPreset = ref("balanced");
const recommendedPreset = ref("balanced");
const recommendationSource = ref("default");
const networkSpeedMbps = ref(null);
const sessionConfig = reactive({ ...presetConfigMap.balanced });
const appliedConfig = ref({ ...presetConfigMap.balanced });
const logSubscription = reactive({
  enabled: false,
  scope: "device",
  packageName: "",
  level: "",
  keyword: "",
  lines: 200,
});

const videoRef = ref(null);
const videoContainerRef = ref(null);

let ws = null;
let scrcpyInput = null;
let videoParser = null;
let jmuxer = null;
let timerInterval = null;
let userInitiatedClose = false;
let componentUnmounting = false;
let pendingReconnect = false;

const wsBackendUrl = computed(
  () => import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
);

const qualitySelectOptions = computed(() =>
  qualityPresetOptions.map((preset) => ({
    value: preset.value,
    label:
      preset.value === recommendedPreset.value
        ? `${t(`appAutomation.workbench.video.presets.${preset.key}`)} (${t("appAutomation.workbench.video.recommended")})`
        : t(`appAutomation.workbench.video.presets.${preset.key}`),
  })),
);

const currentPresetTooltip = computed(() => {
  const config =
    presetConfigMap[selectedPreset.value] || presetConfigMap.balanced;
  const label = t(`appAutomation.workbench.video.presets.${config.labelKey}`);
  const sourceText =
    recommendationSource.value === "browser"
      ? t("appAutomation.workbench.video.recommendation.browser")
      : recommendationSource.value === "device"
        ? t("appAutomation.workbench.video.recommendation.device")
        : t("appAutomation.workbench.video.recommendation.default");
  const speedText = Number.isFinite(networkSpeedMbps.value)
    ? `, ${t("appAutomation.workbench.video.recommendation.referenceSpeed", {
        speed: networkSpeedMbps.value.toFixed(1),
      })}`
    : "";
  return `${label}: ${config.maxSize}p / ${config.maxFps} FPS / ${(config.videoBitRate / 1000000).toFixed(1)} Mbps, ${sourceText}${speedText}`;
});

const logOperation = (message, level = "info", extra = null) => {
  emit("operation", {
    source: "remote",
    level,
    message,
    extra,
    timestamp: Date.now(),
  });
};

const emitLogStatus = (payload) => {
  emit("logcat-status", {
    enabled: logSubscription.enabled,
    scope: logSubscription.scope,
    package_name: logSubscription.packageName,
    level: logSubscription.level,
    keyword: logSubscription.keyword,
    lines: logSubscription.lines,
    ...payload,
  });
};

const sendWsJson = (payload) => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return false;
  }
  ws.send(JSON.stringify(payload));
  return true;
};

const syncLogSubscription = ({ silent = false } = {}) => {
  if (!logSubscription.enabled) {
    sendWsJson({ type: "logcat_unsubscribe" });
    emitLogStatus({
      state: "idle",
      connected: false,
      message: t("appAutomation.workbench.logs.streamClosed"),
    });
    return;
  }

  const sent = sendWsJson({
    type: "logcat_subscribe",
    enabled: true,
    scope: logSubscription.scope,
    package_name: logSubscription.packageName,
    level: logSubscription.level,
    keyword: logSubscription.keyword,
    lines: logSubscription.lines,
  });

  if (!sent) {
    emitLogStatus({
      state: "pending",
      connected: false,
      message: t("appAutomation.workbench.logs.streamPending"),
    });
    if (!silent) {
      logOperation(t("appAutomation.workbench.logs.streamCached"), "info");
    }
  }
};

const updateLogSubscription = (options = {}) => {
  logSubscription.enabled = options.enabled !== false;
  logSubscription.scope = options.scope === "app" ? "app" : "device";
  logSubscription.packageName = String(options.packageName || "").trim();
  logSubscription.level = String(options.level || "")
    .trim()
    .toUpperCase();
  logSubscription.keyword = String(options.keyword || "").trim();
  logSubscription.lines = Number(options.lines || 200);
  syncLogSubscription();
};

const formatDuration = (seconds) => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
};

const cloneConfig = (config) => ({
  maxSize: Number(config.maxSize),
  maxFps: Number(config.maxFps),
  videoBitRate: Number(config.videoBitRate),
});

const assignSessionConfig = (config) => {
  sessionConfig.maxSize = Number(config.maxSize);
  sessionConfig.maxFps = Number(config.maxFps);
  sessionConfig.videoBitRate = Number(config.videoBitRate);
};

const applyPresetConfig = (preset) => {
  const config = presetConfigMap[preset];
  if (!config) {
    return;
  }
  assignSessionConfig(config);
};

const recommendPresetBySpeed = (speedMbps, effectiveType = "") => {
  const normalizedType = String(effectiveType || "").toLowerCase();
  if (normalizedType.includes("2g") || speedMbps < 5) {
    return "smooth";
  }
  if (normalizedType.includes("3g") || speedMbps < 15) {
    return "balanced";
  }
  return "clarity";
};

const resolveRecommendation = async () => {
  const browserConnection =
    navigator.connection ||
    navigator.mozConnection ||
    navigator.webkitConnection;
  const browserDownlink = Number(browserConnection?.downlink);
  if (Number.isFinite(browserDownlink) && browserDownlink > 0) {
    networkSpeedMbps.value = browserDownlink;
    recommendationSource.value = "browser";
    return recommendPresetBySpeed(
      browserDownlink,
      browserConnection?.effectiveType,
    );
  }

  try {
    const response = await getDevicePerformanceSnapshot(props.deviceId);
    const deviceKbps = Number(response.data?.data?.network?.download_kbps);
    if (Number.isFinite(deviceKbps) && deviceKbps > 0) {
      networkSpeedMbps.value = deviceKbps / 1024;
      recommendationSource.value = "device";
      return recommendPresetBySpeed(networkSpeedMbps.value);
    }
  } catch (error) {
    console.warn("Failed to resolve remote quality recommendation:", error);
  }

  networkSpeedMbps.value = null;
  recommendationSource.value = "default";
  return "balanced";
};

const syncRecommendedPreset = async ({ forceApply = false } = {}) => {
  const preset = await resolveRecommendation();
  recommendedPreset.value = preset;
  if (forceApply) {
    selectedPreset.value = preset;
    applyPresetConfig(preset);
    appliedConfig.value = cloneConfig(sessionConfig);
  }
};

const startTimer = () => {
  sessionStartTime.value = Date.now();
  stopTimer();
  timerInterval = setInterval(() => {
    sessionDuration.value = Math.floor(
      (Date.now() - sessionStartTime.value) / 1000,
    );
  }, 1000);
};

const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
};

const loadScripts = async () => {
  if (window.JMUXER_LOADED) {
    return;
  }

  const scripts = [
    "/scrcpy/jmuxer.min.js",
    "/scrcpy/exp-golomb.js",
    "/scrcpy/h264-sps-parser.js",
    "/scrcpy/video_parser.js",
    "/scrcpy/input.js",
  ];

  for (const src of scripts) {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  window.JMUXER_LOADED = true;
};

const initJMuxer = () => {
  jmuxer = new JMuxer({
    node: videoRef.value,
    mode: "video",
    flushingTime: 0,
    fps: Number(sessionConfig.maxFps || 30),
    clearBuffer: true,
    debug: false,
    onReady: () => {
      videoReady.value = true;
    },
    onError: (error) => {
      console.error("JMuxer error:", error);
      ElMessage.error(t("appAutomation.workbench.video.decodeError"));
    },
  });
};

const initInput = (width, height) => {
  if (scrcpyInput) {
    return;
  }

  const inputDataCallback = (data) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const dataView = data instanceof ArrayBuffer ? new DataView(data) : null;
    const packetType = dataView ? dataView.getUint8(0) : null;
    const touchAction =
      packetType === 2 && dataView.byteLength > 1 ? dataView.getUint8(1) : null;
    const isHighFrequencyPacket =
      (packetType === 2 && touchAction === 2) || packetType === 3;
    if (isHighFrequencyPacket && ws.bufferedAmount > 65536) {
      return;
    }

    ws.send(data);
  };

  scrcpyInput = new ScrcpyInput(
    inputDataCallback,
    videoRef.value,
    width,
    height,
    false,
  );
};

const initVideoParser = () => {
  videoParser = new VideoParser(({ type, data }) => {
    if (type === "nalu") {
      jmuxer.feed({ video: data });
    } else if (type === "init") {
      jmuxer.feed({ video: data.sps });
      jmuxer.feed({ video: data.pps });
    } else if (type === "screen_size") {
      initInput(data.width, data.height);
    } else if (type === "size_change" && scrcpyInput) {
      scrcpyInput.resizeScreen(data.width, data.height);
    }
  });
};

const destroyPlayback = () => {
  if (jmuxer) {
    jmuxer.destroy();
    jmuxer = null;
  }
  if (scrcpyInput) {
    scrcpyInput.destroy();
    scrcpyInput = null;
  }
  videoParser = null;
  videoReady.value = false;
};

const resetPlayback = () => {
  destroyPlayback();
  initJMuxer();
  initVideoParser();
};

const emitStatus = () => {
  emit("status-change", {
    connected: isConnected.value,
    message: connectionMessage.value,
  });
};

const buildWsUrl = () => {
  const backendUrl = wsBackendUrl.value;
  const token = localStorage.getItem("access_token");
  const params = new URLSearchParams({
    max_size: String(sessionConfig.maxSize),
    max_fps: String(sessionConfig.maxFps),
    video_bit_rate: String(sessionConfig.videoBitRate),
  });
  if (token) {
    params.set("token", token);
  }
  return (
    backendUrl.replace(/^http/, "ws") +
    `/ws/app-automation/remote-device/${encodeURIComponent(props.deviceId)}/?${params.toString()}`
  );
};

const handleSocketMessage = (message) => {
  if (message.type === "connected") {
    isConnected.value = true;
    connectionMessage.value = t(
      "appAutomation.workbench.video.connectedSuccess",
    );
    appliedConfig.value = cloneConfig(sessionConfig);
    emitStatus();
    startTimer();
    syncLogSubscription({ silent: true });
    logOperation(
      t("appAutomation.workbench.video.sessionConnected", {
        deviceId: props.deviceId,
      }),
      "success",
      {
        ...cloneConfig(sessionConfig),
        preset: selectedPreset.value,
      },
    );
    return;
  }

  if (message.type === "logcat_entry") {
    emit("logcat-entry", message.data || null);
    return;
  }

  if (message.type === "logcat_status") {
    emit("logcat-status", message.data || null);
    return;
  }

  if (message.type === "error") {
    connectionMessage.value =
      message.message || t("appAutomation.workbench.video.connectionFailed");
    emitStatus();
    ElMessage.error(connectionMessage.value);
    logOperation(
      t("appAutomation.workbench.video.sessionError", {
        message: connectionMessage.value,
      }),
      "error",
    );
  }
};

const connectWebSocket = () => {
  ws = new WebSocket(buildWsUrl());
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    connectionMessage.value = t("appAutomation.workbench.video.waitingVideo");
    emitStatus();
  };

  ws.onmessage = (event) => {
    if (typeof event.data === "string") {
      try {
        handleSocketMessage(JSON.parse(event.data));
      } catch (error) {
        console.error("Invalid websocket message:", event.data, error);
      }
      return;
    }

    if (videoParser) {
      videoParser.appendData(new Uint8Array(event.data));
    }
  };

  ws.onclose = (event) => {
    isConnected.value = false;
    videoReady.value = false;
    connectionMessage.value = t("appAutomation.workbench.video.disconnected");
    stopTimer();
    emitStatus();
    emitLogStatus({
      state: pendingReconnect ? "reconnecting" : "disconnected",
      connected: false,
      message: pendingReconnect
        ? t("appAutomation.workbench.logs.streamReconnecting")
        : t("appAutomation.workbench.logs.streamDisconnected"),
    });

    if (pendingReconnect && !componentUnmounting) {
      pendingReconnect = false;
      resetPlayback();
      connectWebSocket();
      return;
    }

    if (userInitiatedClose) {
      logOperation(
        t("appAutomation.workbench.video.sessionClosed", {
          deviceId: props.deviceId,
        }),
        "info",
      );
      emit("session-ended");
      userInitiatedClose = false;
    } else if (!componentUnmounting && event.code !== 1000) {
      ElMessage.warning(
        t("appAutomation.workbench.video.connectionInterrupted"),
      );
      logOperation(
        t("appAutomation.workbench.video.connectionInterruptedLog", {
          deviceId: props.deviceId,
        }),
        "warning",
        {
          code: event.code,
          reason: event.reason,
        },
      );
    }
  };

  ws.onerror = () => {
    connectionMessage.value = t(
      "appAutomation.workbench.video.connectionFailed",
    );
    emitStatus();
    emitLogStatus({
      state: "error",
      connected: false,
      message: t("appAutomation.workbench.logs.streamUnavailable"),
    });
    ElMessage.error(t("appAutomation.workbench.video.websocketError"));
    logOperation(
      t("appAutomation.workbench.video.connectionError", {
        deviceId: props.deviceId,
      }),
      "error",
    );
  };
};

const applyZoom = () => {
  if (videoRef.value) {
    videoRef.value.style.transform = `scale(${zoomLevel.value})`;
  }
};

const reopenSession = () => {
  resetPlayback();
  connectWebSocket();
};

const switchPreset = (preset) => {
  if (!presetConfigMap[preset]) {
    return;
  }

  selectedPreset.value = preset;
  applyPresetConfig(preset);

  const nextConfig = cloneConfig(sessionConfig);
  const configChanged =
    nextConfig.maxSize !== Number(appliedConfig.value.maxSize) ||
    nextConfig.maxFps !== Number(appliedConfig.value.maxFps) ||
    nextConfig.videoBitRate !== Number(appliedConfig.value.videoBitRate);

  if (!configChanged) {
    return;
  }

  const canCloseSocket =
    ws &&
    (ws.readyState === WebSocket.OPEN ||
      ws.readyState === WebSocket.CONNECTING);
  if (canCloseSocket) {
    pendingReconnect = true;
    ws.close(1000, "Reopen with new session config");
  } else {
    reopenSession();
  }

  ElMessage.success(
    t("appAutomation.workbench.video.presetSwitched", {
      preset: t(
        `appAutomation.workbench.video.presets.${presetConfigMap[preset].labelKey}`,
      ),
    }),
  );
  logOperation(t("appAutomation.workbench.video.presetUpdated"), "info", {
    preset,
    ...nextConfig,
  });
};

const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value + 0.1, 3);
  applyZoom();
};

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value - 0.1, 0.5);
  applyZoom();
};

const sendKeyCommand = (key) => {
  if (!scrcpyInput) {
    return;
  }

  let keyCode = null;
  if (key === "back") {
    keyCode = 4;
  } else if (key === "home") {
    keyCode = 3;
  } else if (key === "menu") {
    keyCode = 187;
  }

  if (!keyCode) {
    return;
  }

  const keyEvent = {
    getModifierState: () => false,
    shiftKey: false,
    ctrlKey: false,
    altKey: false,
    metaKey: false,
    repeat: 0,
  };

  scrcpyInput.snedKeyCode(keyEvent, 0, keyCode);
  setTimeout(() => {
    scrcpyInput.snedKeyCode(keyEvent, 1, keyCode);
  }, 100);
};

const captureCurrentFrame = () => {
  if (!videoRef.value || !videoReady.value) {
    throw new Error(t("appAutomation.workbench.video.frameNotReady"));
  }

  const width = videoRef.value.videoWidth;
  const height = videoRef.value.videoHeight;
  if (!width || !height) {
    throw new Error(t("appAutomation.workbench.video.frameSizeInvalid"));
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error(t("appAutomation.workbench.video.canvasCreateFailed"));
  }

  ctx.drawImage(videoRef.value, 0, 0, width, height);
  return {
    content: canvas.toDataURL("image/png"),
    width,
    height,
    filename: `remote_frame_${Date.now()}.png`,
    source: "remote-frame",
    timestamp: Date.now(),
  };
};

const toggleFullscreen = async () => {
  if (!document.fullscreenElement) {
    try {
      await videoContainerRef.value?.requestFullscreen?.();
      logOperation(t("appAutomation.workbench.video.enterFullscreen"), "info");
    } catch (error) {
      ElMessage.error(
        t("appAutomation.workbench.video.fullscreenFailed", {
          message: error.message,
        }),
      );
      logOperation(
        t("appAutomation.workbench.video.fullscreenFailedLog"),
        "error",
        error?.message,
      );
    }
    return;
  }

  await document.exitFullscreen();
  logOperation(t("appAutomation.workbench.video.exitFullscreen"), "info");
};

const closeSession = () => {
  const canCloseSocket =
    ws &&
    (ws.readyState === WebSocket.OPEN ||
      ws.readyState === WebSocket.CONNECTING);
  userInitiatedClose = true;
  pendingReconnect = false;
  if (canCloseSocket) {
    ws.close(1000, "User ended session");
  } else {
    emit("session-ended");
  }
};

onMounted(async () => {
  try {
    await loadScripts();
    await syncRecommendedPreset({ forceApply: true });
    resetPlayback();
    connectWebSocket();
  } catch (error) {
    console.error("Remote panel init failed:", error);
    connectionMessage.value = t("appAutomation.workbench.video.initFailed");
    emitStatus();
    emitLogStatus({
      state: "error",
      connected: false,
      message: t("appAutomation.workbench.logs.streamInitFailed"),
    });
    ElMessage.error(
      t("appAutomation.workbench.video.initFailedWithMessage", {
        message: error.message,
      }),
    );
  }
});

onUnmounted(() => {
  componentUnmounting = true;
  pendingReconnect = false;
  stopTimer();
  if (ws) {
    ws.close(1000, "Component unmounted");
  }
  destroyPlayback();
});

defineExpose({
  closeSession,
  captureCurrentFrame,
  updateLogSubscription,
});
</script>

<style scoped lang="scss">
.remote-video-panel {
  flex: 1;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #fafcff;
  gap: 12px;
}

.status-group {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.session-timer {
  font-size: 13px;
  font-family: Consolas, monospace;
  color: #4b5563;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.quality-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quality-label {
  font-size: 12px;
  color: #6b7280;
}

.zoom-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 2px 4px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.zoom-text {
  min-width: 44px;
  text-align: center;
  font-size: 12px;
  color: #4b5563;
}

.video-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.video-stage {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #f6f8fb 0%, #eef2f7 100%);
  overflow: hidden;
  touch-action: none;
}

.status-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #6b7280;
  z-index: 2;
}

.loading-icon {
  animation: rotate 1.8s linear infinite;
}

video {
  width: auto;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  outline: none;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.14);
  transform-origin: center center;
  user-select: none;
  touch-action: none;
}

.bottom-controls {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 16px;
  background: #fafcff;
}

@media (max-width: 1200px) {
  .panel-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .bottom-controls {
    gap: 16px;
    padding: 12px;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}
</style>
