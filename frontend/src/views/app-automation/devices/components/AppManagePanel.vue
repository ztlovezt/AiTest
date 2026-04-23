<template>
  <div class="app-manage-panel">
    <div class="panel-header">
      <div>
        <h4>{{ t("appAutomation.workbench.appManage.title") }}</h4>
        <p>{{ t("appAutomation.workbench.appManage.description") }}</p>
      </div>
      <div class="panel-actions">
        <el-button :loading="loadingCurrentApp" @click="loadCurrentApp">{{
          t("appAutomation.workbench.appManage.refreshCurrentApp")
        }}</el-button>
        <el-button :loading="installedLoading" @click="loadInstalledPackages">{{
          t("appAutomation.workbench.appManage.refreshInstalledApps")
        }}</el-button>
      </div>
    </div>

    <div class="panel-grid">
      <el-card shadow="never" class="summary-card">
        <template #header>
          <span>{{
            t("appAutomation.workbench.appManage.currentForegroundApp")
          }}</span>
        </template>
        <div class="summary-item">
          <span class="label">{{
            t("appAutomation.workbench.appManage.packageName")
          }}</span>
          <span class="value">{{ currentApp.package_name || "-" }}</span>
        </div>
        <div class="summary-item">
          <span class="label">{{
            t("appAutomation.workbench.appManage.activity")
          }}</span>
          <span class="value">{{ currentApp.activity || "-" }}</span>
        </div>
        <div class="summary-item">
          <span class="label">{{
            t("appAutomation.workbench.appManage.installedCount")
          }}</span>
          <span class="value">{{ installedPackages.length }}</span>
        </div>
      </el-card>

      <el-card shadow="never" class="install-card">
        <template #header>
          <span>{{
            t("appAutomation.workbench.appManage.installActions")
          }}</span>
        </template>

        <el-tabs v-model="installMode" class="install-tabs">
          <el-tab-pane
            :label="t('appAutomation.workbench.appManage.libraryInstall')"
            name="library"
          >
            <el-form label-width="88px" size="small">
              <el-form-item
                :label="t('appAutomation.workbench.appManage.packageLabel')"
              >
                <el-select
                  v-model="selectedPackageId"
                  filterable
                  :placeholder="
                    t(
                      'appAutomation.workbench.appManage.selectPackagePlaceholder',
                    )
                  "
                  style="width: 100%"
                >
                  <el-option
                    v-for="pkg in packages"
                    :key="pkg.id"
                    :label="`${pkg.name} (${pkg.package_name})`"
                    :value="pkg.id"
                  />
                </el-select>
              </el-form-item>

              <el-form-item
                :label="t('appAutomation.workbench.appManage.appName')"
              >
                <el-input :model-value="selectedPackage?.name || ''" disabled />
              </el-form-item>

              <el-form-item
                :label="t('appAutomation.workbench.appManage.packageName')"
              >
                <el-input
                  :model-value="selectedPackage?.package_name || ''"
                  disabled
                />
              </el-form-item>

              <el-form-item
                :label="t('appAutomation.workbench.appManage.apkStatus')"
              >
                <el-tag
                  :type="selectedPackageHasApk ? 'success' : 'info'"
                  effect="plain"
                >
                  {{
                    selectedPackageHasApk
                      ? t("appAutomation.workbench.appManage.apkUploaded")
                      : t("appAutomation.workbench.appManage.apkMissing")
                  }}
                </el-tag>
              </el-form-item>

              <div class="action-row">
                <el-button
                  type="primary"
                  :disabled="!selectedPackageHasApk"
                  :loading="installingFromLibrary"
                  @click="installFromLibrary"
                  >{{
                    t("appAutomation.workbench.appManage.installToDevice")
                  }}</el-button
                >
                <el-button
                  :disabled="!selectedPackage?.package_name"
                  :loading="actionLoading.launchLibrary"
                  @click="launchSelectedLibraryApp"
                  >{{
                    t("appAutomation.workbench.appManage.launch")
                  }}</el-button
                >
              </div>
            </el-form>
          </el-tab-pane>

          <el-tab-pane
            :label="t('appAutomation.workbench.appManage.uploadInstall')"
            name="upload"
          >
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              drag
              accept=".apk"
              :on-change="handleApkChange"
              :on-remove="handleApkRemove"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                {{ t("appAutomation.workbench.appManage.dragUploadText") }}
                <em>{{
                  t("appAutomation.workbench.appManage.clickUpload")
                }}</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  {{ t("appAutomation.workbench.appManage.uploadTip") }}
                </div>
              </template>
            </el-upload>

            <div v-if="isUploading" class="upload-progress">
              <el-progress
                :percentage="uploadProgress"
                :status="uploadStatus"
              />
              <div class="upload-message">{{ uploadMessage }}</div>
            </div>

            <div v-if="tempApk.apk_filepath" class="temp-apk-summary">
              <div class="summary-item">
                <span class="label">{{
                  t("appAutomation.workbench.appManage.appName")
                }}</span>
                <span class="value">{{ tempApk.app_name || "-" }}</span>
              </div>
              <div class="summary-item">
                <span class="label">{{
                  t("appAutomation.workbench.appManage.packageName")
                }}</span>
                <span class="value">{{ tempApk.package_name || "-" }}</span>
              </div>
              <div class="summary-item">
                <span class="label">{{
                  t("appAutomation.workbench.appManage.file")
                }}</span>
                <el-tooltip
                  :content="tempApk.apk_filename || '-'"
                  placement="top-start"
                >
                  <span class="value file-value">{{
                    tempApk.apk_filename || "-"
                  }}</span>
                </el-tooltip>
              </div>
              <div class="action-row compact">
                <el-button
                  type="primary"
                  :loading="installingTempApk"
                  @click="installTempApk()"
                  >{{
                    t("appAutomation.workbench.appManage.installToDevice")
                  }}</el-button
                >
                <el-button
                  :disabled="!tempApk.package_name"
                  :loading="actionLoading.launchTemp"
                  @click="launchTempApp"
                  >{{
                    t("appAutomation.workbench.appManage.launchAfterInstall")
                  }}</el-button
                >
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <el-card shadow="never" class="device-package-card">
        <template #header>
          <div class="device-package-header">
            <span>{{
              t("appAutomation.workbench.appManage.devicePackageManagement")
            }}</span>
            <div class="device-package-tools">
              <el-input
                v-model="packageKeyword"
                clearable
                size="small"
                :placeholder="
                  t(
                    'appAutomation.workbench.appManage.searchPackagePlaceholder',
                  )
                "
                style="width: 220px"
              />
            </div>
          </div>
        </template>

        <div class="package-list">
          <div
            v-if="installedPackagesFiltered.length"
            class="package-list-inner"
          >
            <div
              v-for="packageName in installedPackagesFiltered"
              :key="packageName"
              class="package-row"
            >
              <div class="package-meta">
                <div class="package-name">{{ packageName }}</div>
                <el-tag
                  v-if="packageName === currentApp.package_name"
                  size="small"
                  type="success"
                  effect="plain"
                  >{{
                    t("appAutomation.workbench.appManage.runningForeground")
                  }}</el-tag
                >
              </div>
              <div class="package-actions">
                <el-button
                  link
                  size="small"
                  :loading="actionLoading.launchPackage === packageName"
                  @click="launchDevicePackage(packageName)"
                  >{{
                    t("appAutomation.workbench.appManage.launch")
                  }}</el-button
                >
                <el-button
                  link
                  size="small"
                  :loading="actionLoading.stopPackage === packageName"
                  @click="stopDevicePackageAction(packageName)"
                  >{{ t("appAutomation.workbench.appManage.stop") }}</el-button
                >
                <el-button
                  link
                  size="small"
                  :loading="actionLoading.clearPackage === packageName"
                  @click="clearDevicePackageAction(packageName)"
                  >{{
                    t("appAutomation.workbench.appManage.clearDataCache")
                  }}</el-button
                >
                <el-button
                  link
                  size="small"
                  type="danger"
                  :loading="actionLoading.uninstallPackage === packageName"
                  @click="uninstallDevicePackageAction(packageName)"
                  >{{
                    t("appAutomation.workbench.appManage.uninstall")
                  }}</el-button
                >
              </div>
            </div>
          </div>
          <el-empty
            v-else
            :description="
              t('appAutomation.workbench.appManage.noInstalledPackages')
            "
          />
        </div>
      </el-card>

      <el-card shadow="never" class="output-card">
        <template #header>
          <span>{{ t("appAutomation.workbench.appManage.recentOutput") }}</span>
        </template>
        <pre>{{
          lastOutput || t("appAutomation.workbench.appManage.noOutput")
        }}</pre>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { UploadFilled } from "@element-plus/icons-vue";
import { useI18n } from "vue-i18n";
import {
  clearDeviceAppData,
  getDeviceCurrentApp,
  getInstalledDevicePackages,
  getPackageList,
  installApkToDevice,
  launchDeviceApp,
  stopDeviceApp,
  uninstallDeviceApp,
  uploadAndExtractApk,
} from "@/api/app-automation";

const props = defineProps({
  deviceId: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["current-app-change", "operation"]);
const { t } = useI18n();

const installMode = ref("library");
const loadingCurrentApp = ref(false);
const installedLoading = ref(false);
const installingFromLibrary = ref(false);
const installingTempApk = ref(false);
const packages = ref([]);
const installedPackages = ref([]);
const selectedPackageId = ref(null);
const currentApp = ref({ package_name: "", activity: "" });
const packageKeyword = ref("");
const lastOutput = ref("");
const uploadRef = ref(null);
const isUploading = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref("");
const uploadMessage = ref("");
const tempApk = reactive({
  package_name: "",
  app_name: "",
  apk_filepath: "",
  apk_filename: "",
});
const actionLoading = reactive({
  launchLibrary: false,
  launchTemp: false,
  launchPackage: "",
  stopPackage: "",
  clearPackage: "",
  uninstallPackage: "",
});

// 应用库安装和设备已装应用都依赖同一份包数据，这里统一做派生状态。
const selectedPackage = computed(
  () =>
    packages.value.find((item) => item.id === selectedPackageId.value) || null,
);
const selectedPackageHasApk = computed(() =>
  Boolean(
    selectedPackage.value?.apk_filepath || selectedPackage.value?.apk_file_url,
  ),
);
const installedPackagesFiltered = computed(() => {
  const keyword = packageKeyword.value.trim().toLowerCase();
  if (!keyword) {
    return installedPackages.value;
  }
  return installedPackages.value.filter((item) =>
    item.toLowerCase().includes(keyword),
  );
});

const logOperation = (message, level = "info", extra = null) => {
  emit("operation", {
    source: "apps",
    level,
    message,
    extra,
    timestamp: Date.now(),
  });
};

const setOutput = (message, payload = null) => {
  // 最近一次操作的原始输出统一落在右侧面板，便于排查设备侧返回结果。
  lastOutput.value = [message, payload ? JSON.stringify(payload, null, 2) : ""]
    .filter(Boolean)
    .join("\n\n");
};

const loadPackages = async () => {
  try {
    const response = await getPackageList({ page: 1, page_size: 1000 });
    const payload =
      response.data?.success !== undefined
        ? response.data?.data
        : response.data;
    packages.value = payload?.results || payload || [];
  } catch (error) {
    console.error("Failed to load package list:", error);
    ElMessage.error(
      t("appAutomation.workbench.appManage.loadPackageListFailed"),
    );
    logOperation(
      t("appAutomation.workbench.appManage.loadPackageListFailed"),
      "error",
      error?.response?.data || error?.message,
    );
  }
};

const loadInstalledPackages = async () => {
  installedLoading.value = true;
  try {
    const response = await getInstalledDevicePackages(props.deviceId);
    installedPackages.value = response.data?.data || [];
  } catch (error) {
    console.error("Failed to load installed packages:", error);
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.loadInstalledFailed"),
    );
    logOperation(
      t("appAutomation.workbench.appManage.loadInstalledFailed"),
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    installedLoading.value = false;
  }
};

const loadCurrentApp = async () => {
  loadingCurrentApp.value = true;
  try {
    const response = await getDeviceCurrentApp(props.deviceId);
    currentApp.value = response.data?.data || {
      package_name: "",
      activity: "",
    };
    emit("current-app-change", currentApp.value);
  } catch (error) {
    console.error("Failed to load current app:", error);
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.loadCurrentAppFailed"),
    );
    logOperation(
      t("appAutomation.workbench.appManage.loadCurrentAppFailed"),
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    loadingCurrentApp.value = false;
  }
};

const installFromLibrary = async () => {
  if (!selectedPackageId.value) {
    ElMessage.warning(
      t("appAutomation.workbench.appManage.selectPackageFirst"),
    );
    return;
  }
  installingFromLibrary.value = true;
  try {
    const response = await installApkToDevice(props.deviceId, {
      package_id: selectedPackageId.value,
    });
    setOutput(
      t("appAutomation.workbench.appManage.installFromLibrarySuccess"),
      response.data?.data,
    );
    ElMessage.success(
      response.data?.message ||
        t("appAutomation.workbench.appManage.installSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.installFromLibrarySuccess")}: ${selectedPackage.value?.package_name || selectedPackageId.value}`,
      "success",
      response.data?.data,
    );
    await Promise.all([loadCurrentApp(), loadInstalledPackages()]);
  } catch (error) {
    console.error("Install from library failed:", error);
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.installFromLibraryFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.installFromLibraryFailed")}: ${selectedPackage.value?.package_name || selectedPackageId.value}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    installingFromLibrary.value = false;
  }
};

const launchSelectedLibraryApp = async () => {
  if (!selectedPackage.value?.package_name) {
    ElMessage.warning(
      t("appAutomation.workbench.appManage.selectPackageFirst"),
    );
    return;
  }
  actionLoading.launchLibrary = true;
  try {
    const response = await launchDeviceApp(props.deviceId, {
      package_name: selectedPackage.value.package_name,
    });
    setOutput(
      t("appAutomation.workbench.appManage.launchSuccess"),
      response.data?.data,
    );
    ElMessage.success(
      response.data?.message ||
        t("appAutomation.workbench.appManage.launchSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.launchSuccess")}: ${selectedPackage.value.package_name}`,
      "success",
      response.data?.data,
    );
    await loadCurrentApp();
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.launchFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.launchFailed")}: ${selectedPackage.value.package_name}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    actionLoading.launchLibrary = false;
  }
};

const handleApkChange = async (file) => {
  // 临时上传模式下，先上传并解析 APK 信息，再决定是否安装到设备。
  if (!file.raw?.name?.toLowerCase().endsWith(".apk")) {
    ElMessage.error(t("appAutomation.workbench.appManage.invalidApkFile"));
    uploadRef.value?.clearFiles();
    return;
  }

  isUploading.value = true;
  uploadStatus.value = "";
  uploadProgress.value = 0;
  uploadMessage.value = t("appAutomation.workbench.appManage.uploading");

  try {
    const response = await uploadAndExtractApk(file.raw, (progressEvent) => {
      if (progressEvent.total) {
        uploadProgress.value = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total,
        );
      }
    });

    const data = response.data?.data || {};
    tempApk.package_name = data.package_name || "";
    tempApk.app_name = data.app_name || "";
    tempApk.apk_filepath = data.apk_filepath || "";
    tempApk.apk_filename = data.apk_filename || "";
    uploadStatus.value = response.data.success ? "success" : "warning";
    uploadMessage.value = response.data.success
      ? t("appAutomation.workbench.appManage.extractDone")
      : response.data.message ||
        t("appAutomation.workbench.appManage.uploadedOnly");
    setOutput(t("appAutomation.workbench.appManage.uploadInstall"), data);
    if (response.data.success) {
      ElMessage.success(
        t("appAutomation.workbench.appManage.uploadExtractSuccess"),
      );
      logOperation(
        `${t("appAutomation.workbench.appManage.uploadExtractSuccess")}: ${data.package_name || data.apk_filename}`,
        "success",
        data,
      );
    } else {
      ElMessage.warning(
        response.data.message ||
          t("appAutomation.workbench.appManage.uploadPartial"),
      );
      logOperation(
        t("appAutomation.workbench.appManage.uploadPartial"),
        "warning",
        data,
      );
    }
  } catch (error) {
    uploadStatus.value = "exception";
    uploadMessage.value =
      error?.response?.data?.message ||
      error.message ||
      t("appAutomation.workbench.appManage.uploadFailed");
    ElMessage.error(uploadMessage.value);
    logOperation(
      t("appAutomation.workbench.appManage.uploadFailed"),
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    setTimeout(() => {
      isUploading.value = false;
    }, 500);
  }
};

const handleApkRemove = () => {
  tempApk.package_name = "";
  tempApk.app_name = "";
  tempApk.apk_filepath = "";
  tempApk.apk_filename = "";
  uploadProgress.value = 0;
  uploadStatus.value = "";
  uploadMessage.value = "";
};

const installTempApk = async ({ silent = false } = {}) => {
  // “安装后启动”会复用这个方法，因此支持 silent 模式避免重复弹成功提示。
  if (!tempApk.apk_filepath) {
    if (!silent) {
      ElMessage.warning(t("appAutomation.workbench.appManage.uploadApkFirst"));
    }
    return false;
  }
  installingTempApk.value = true;
  try {
    const response = await installApkToDevice(props.deviceId, {
      apk_filepath: tempApk.apk_filepath,
    });
    setOutput(
      t("appAutomation.workbench.appManage.installSuccess"),
      response.data?.data,
    );
    if (!silent) {
      ElMessage.success(
        response.data?.message ||
          t("appAutomation.workbench.appManage.installSuccess"),
      );
    }
    logOperation(
      `${t("appAutomation.workbench.appManage.installSuccess")}: ${tempApk.package_name || tempApk.apk_filename}`,
      "success",
      response.data?.data,
    );
    await Promise.all([loadCurrentApp(), loadInstalledPackages()]);
    return true;
  } catch (error) {
    if (!silent) {
      ElMessage.error(
        error?.response?.data?.message ||
          error.message ||
          t("appAutomation.workbench.appManage.installFailed"),
      );
    }
    logOperation(
      `${t("appAutomation.workbench.appManage.installFailed")}: ${tempApk.package_name || tempApk.apk_filename}`,
      "error",
      error?.response?.data || error?.message,
    );
    return false;
  } finally {
    installingTempApk.value = false;
  }
};

const launchTempApp = async () => {
  if (!tempApk.package_name) {
    ElMessage.warning(
      t("appAutomation.workbench.appManage.tempPackageMissing"),
    );
    return;
  }
  actionLoading.launchTemp = true;
  try {
    const installed = await installTempApk({ silent: true });
    if (!installed) {
      ElMessage.error(
        t("appAutomation.workbench.appManage.installFailedCannotLaunch"),
      );
      return;
    }
    const response = await launchDeviceApp(props.deviceId, {
      package_name: tempApk.package_name,
    });
    setOutput(
      t("appAutomation.workbench.appManage.launchAfterInstall"),
      response.data?.data,
    );
    ElMessage.success(
      response.data?.message ||
        t("appAutomation.workbench.appManage.launchSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.launchAfterInstall")}: ${tempApk.package_name}`,
      "success",
      response.data?.data,
    );
    await loadCurrentApp();
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.launchFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.launchFailed")}: ${tempApk.package_name}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    actionLoading.launchTemp = false;
  }
};

const launchDevicePackage = async (packageName) => {
  actionLoading.launchPackage = packageName;
  try {
    const response = await launchDeviceApp(props.deviceId, {
      package_name: packageName,
    });
    setOutput(
      `${t("appAutomation.workbench.appManage.launchSuccess")}: ${packageName}`,
      response.data?.data,
    );
    ElMessage.success(
      response.data?.message ||
        t("appAutomation.workbench.appManage.launchSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.launchSuccess")}: ${packageName}`,
      "success",
      response.data?.data,
    );
    await loadCurrentApp();
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.launchFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.launchFailed")}: ${packageName}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    actionLoading.launchPackage = "";
  }
};

const stopDevicePackageAction = async (packageName) => {
  actionLoading.stopPackage = packageName;
  try {
    const response = await stopDeviceApp(props.deviceId, {
      package_name: packageName,
    });
    setOutput(
      `${t("appAutomation.workbench.appManage.stopSuccess")}: ${packageName}`,
      response.data?.data,
    );
    ElMessage.success(
      response.data?.message ||
        t("appAutomation.workbench.appManage.stopSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.stopSuccess")}: ${packageName}`,
      "success",
      response.data?.data,
    );
    await loadCurrentApp();
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.stopFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.stopFailed")}: ${packageName}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    actionLoading.stopPackage = "";
  }
};

const clearDevicePackageAction = async (packageName) => {
  // 清理运行数据会导致应用回到初始状态，因此必须做二次确认。
  try {
    await ElMessageBox.confirm(
      t("appAutomation.workbench.appManage.clearConfirmMessage", {
        packageName,
      }),
      t("appAutomation.workbench.appManage.clearConfirmTitle"),
      {
        type: "warning",
        confirmButtonText: t(
          "appAutomation.workbench.appManage.clearConfirmAction",
        ),
        cancelButtonText: t("appAutomation.common.cancel"),
      },
    );
  } catch {
    return;
  }

  actionLoading.clearPackage = packageName;
  try {
    const response = await clearDeviceAppData(props.deviceId, {
      package_name: packageName,
    });
    setOutput(
      `${t("appAutomation.workbench.appManage.clearSuccess")}: ${packageName}`,
      response.data?.data,
    );
    ElMessage.success(
      response.data?.message ||
        t("appAutomation.workbench.appManage.clearSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.clearSuccess")}: ${packageName}`,
      "success",
      response.data?.data,
    );
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.clearFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.clearFailed")}: ${packageName}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    actionLoading.clearPackage = "";
  }
};

const uninstallDevicePackageAction = async (packageName) => {
  try {
    await ElMessageBox.confirm(
      t("appAutomation.workbench.appManage.uninstallConfirmMessage", {
        packageName,
      }),
      t("appAutomation.workbench.appManage.uninstallConfirmTitle"),
      {
        type: "warning",
      },
    );
  } catch {
    return;
  }

  actionLoading.uninstallPackage = packageName;
  try {
    const response = await uninstallDeviceApp(props.deviceId, {
      package_name: packageName,
    });
    setOutput(
      `${t("appAutomation.workbench.appManage.uninstallSuccess")}: ${packageName}`,
      response.data?.data,
    );
    ElMessage.success(
      response.data?.message ||
        t("appAutomation.workbench.appManage.uninstallSuccess"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.uninstallSuccess")}: ${packageName}`,
      "success",
      response.data?.data,
    );
    await Promise.all([loadCurrentApp(), loadInstalledPackages()]);
  } catch (error) {
    ElMessage.error(
      error?.response?.data?.message ||
        error.message ||
        t("appAutomation.workbench.appManage.uninstallFailed"),
    );
    logOperation(
      `${t("appAutomation.workbench.appManage.uninstallFailed")}: ${packageName}`,
      "error",
      error?.response?.data || error?.message,
    );
  } finally {
    actionLoading.uninstallPackage = "";
  }
};

onMounted(async () => {
  await Promise.all([
    loadPackages(),
    loadCurrentApp(),
    loadInstalledPackages(),
  ]);
});
</script>

<style scoped>
.app-manage-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-header {
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

.panel-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.panel-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.7fr) minmax(360px, 1fr);
  gap: 16px;
}

.summary-card,
.install-card,
.device-package-card,
.output-card {
  border-radius: 16px;
}

.install-card,
.output-card {
  min-height: 0;
}

.device-package-card {
  grid-column: 1 / -1;
}

.output-card {
  grid-column: 1 / -1;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
}

.summary-item:last-child {
  border-bottom: 0;
}

.label {
  color: #6b7280;
  flex-shrink: 0;
}

.value {
  color: #111827;
  text-align: right;
  word-break: break-all;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.action-row.compact {
  margin-top: 16px;
}

.upload-progress {
  margin-top: 16px;
}

.upload-message {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.temp-apk-summary {
  margin-top: 16px;
}

.file-value {
  max-width: 420px;
  text-align: right;
  white-space: normal;
  word-break: break-all;
}

.device-package-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.device-package-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.package-list {
  min-height: 280px;
}

.package-list-inner {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow: auto;
}

.package-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fbfdff;
}

.package-meta {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.package-name {
  color: #111827;
  font-size: 14px;
  word-break: break-all;
}

.package-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.output-card pre {
  margin: 0;
  min-height: 180px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1200px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .panel-header,
  .device-package-header,
  .package-row {
    flex-direction: column;
    align-items: stretch;
  }

  .package-actions,
  .panel-actions {
    justify-content: flex-end;
  }
}
</style>
