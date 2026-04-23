<template>
  <div class="device-management">
    <!-- 椤甸潰鏍囬鍜屾搷浣滄寜閽?-->
    <div class="device-header">
      <h3>{{ t('appAutomation.device.title') }}</h3>
      <div class="device-actions">
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="refreshing"
          @click="refreshDevices"
        >
          {{ t('appAutomation.common.refresh') }}
        </el-button>
        <el-button
          type="success"
          :icon="Plus"
          @click="showAddRemoteDialog"
        >
          {{ t('appAutomation.device.newDevice') }}
        </el-button>
      </div>
    </div>

    <!-- 璁惧鍒楄〃 -->
    <el-table
      v-loading="loading"
      :data="devices"
      style="width: 100%; margin-top: 20px"
      :empty-text="emptyText"
    >
      <el-table-column prop="name" :label="t('appAutomation.device.deviceName')" min-width="150">
        <template #default="{ row }">
          <span>{{ row.name || row.device_id }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="device_id" :label="t('appAutomation.device.deviceId')" min-width="180" />

      <el-table-column prop="status" :label="t('appAutomation.device.status')" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="locked_by" :label="t('appAutomation.device.owner')" width="120">
        <template #default="{ row }">
          <span v-if="row.locked_by_name">
            {{ row.locked_by_name }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column prop="locked_at" :label="t('appAutomation.device.lastUsed')" width="180">
        <template #default="{ row }">
          <span v-if="row.locked_at">
            {{ formatDate(row.locked_at) }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column prop="android_version" :label="t('appAutomation.device.platformVersion')" width="120" />

      <el-table-column prop="connection_type" :label="t('appAutomation.device.platform')" width="120">
        <template #default="{ row }">
          <el-tag
            :type="getConnectionType(row.connection_type) === 'local' ? 'primary' : 'warning'"
            size="small"
          >
            {{ getConnectionTypeName(row.connection_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="ip_address" :label="t('appAutomation.common.ipAddress')" width="150">
        <template #default="{ row }">
          <span v-if="row.ip_address">
            {{ row.ip_address }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column prop="usage_count" :label="t('appAutomation.device.usageCount')" width="100" />

      <el-table-column prop="updated_at" :label="t('appAutomation.device.createTime')" width="180">
        <template #default="{ row }">
          {{ formatDate(row.updated_at) }}
        </template>
      </el-table-column>

      <el-table-column :label="t('appAutomation.common.operation')" width="300" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            size="small"
            type="warning"
            @click="goToRemoteConnection(row)"
          >
            <el-icon><Monitor /></el-icon>&nbsp;
            {{ t('appAutomation.device.remoteConnect') }}
          </el-button>
          <el-button
            v-if="row.status === 'available' || row.status === 'online'"
            link
            size="small"
            type="primary"
            @click="lockDevice(row)"
          >
            {{ t('appAutomation.device.lock') }}
          </el-button>
          <el-button
            v-if="row.status === 'locked'"
            link
            size="small"
            type="success"
            @click="unlockDevice(row)"
          >
            {{ t('appAutomation.device.unlock') }}
          </el-button>
          <el-button
            v-if="isRemoteDevice(row.connection_type) && row.status === 'offline'"
            link
            size="small"
            type="warning"
            :loading="reconnectingDevices[row.id]"
            @click="reconnectDevice(row)"
          >
            {{ t('appAutomation.device.reconnect') }}
          </el-button>
          <el-button
            link
            size="small"
            @click="viewDeviceInfo(row)"
          >
            {{ t('appAutomation.common.detail') }}
          </el-button>
          <el-button
            v-if="isRemoteDevice(row.connection_type) && (row.status === 'online' || row.status === 'available')"
            link
            size="small"
            type="warning"
            @click="disconnectDevice(row)"
          >
            {{ t('appAutomation.device.disconnect') }}
          </el-button>
          <el-button
            link
            size="small"
            type="danger"
            @click="handleDeleteDevice(row)"
          >
            {{ t('appAutomation.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 娣诲姞杩滅▼璁惧瀵硅瘽妗?-->
    <el-dialog
      v-model="addRemoteDialogVisible"
      :title="t('appAutomation.device.newDevice')"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="remoteDeviceFormRef"
        :model="remoteDeviceForm"
        :rules="remoteDeviceRules"
        label-width="100px"
      >
        <el-form-item :label="t('appAutomation.common.ipAddress')" prop="ip_address">
          <el-input
            v-model="remoteDeviceForm.ip_address"
            :placeholder="t('appAutomation.device.ipAddressPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="t('appAutomation.device.port')" prop="port">
          <el-input-number
            v-model="remoteDeviceForm.port"
            :min="1"
            :max="65535"
            :placeholder="t('appAutomation.device.portPlaceholder')"
            style="width: 100%"
          />
        </el-form-item>

        <el-alert
          :title="t('appAutomation.device.tip')"
          type="info"
          :closable="false"
          style="margin-top: 10px"
        >
          <div>{{ t('appAutomation.device.ensure') }}：</div>
          <div>1. {{ t('appAutomation.device.adbDebug') }}</div>
          <div>2. {{ t('appAutomation.device.networkAdb') }}</div>
          <div>3. {{ t('appAutomation.device.networkConnection') }}</div>
        </el-alert>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="addRemoteDialogVisible = false">{{ t('appAutomation.common.cancel') }}</el-button>
          <el-button
            type="primary"
            :loading="connecting"
            @click="connectRemoteDevice"
          >
            {{ t('appAutomation.device.connect') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 璁惧璇︽儏瀵硅瘽妗?-->
    <el-dialog
      v-model="deviceInfoDialogVisible"
      :title="t('appAutomation.device.deviceName')"
      width="600px"
    >
      <el-descriptions v-if="selectedDevice" :column="2" border>
        <el-descriptions-item :label="t('appAutomation.device.deviceName')">
          {{ selectedDevice.name || selectedDevice.device_id }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.deviceId')">
          {{ selectedDevice.device_id }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.status')">
          <el-tag :type="getStatusType(selectedDevice.status)" size="small">
            {{ getStatusText(selectedDevice.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.owner')">
          {{ selectedDevice.locked_by_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.lastUsed')">
          {{ selectedDevice.locked_at ? formatDate(selectedDevice.locked_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.platformVersion')">
          {{ selectedDevice.android_version || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.platform')">
          <el-tag
            :type="getConnectionType(selectedDevice.connection_type) === 'local' ? 'primary' : 'warning'"
            size="small"
          >
            {{ getConnectionTypeName(selectedDevice.connection_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.common.ipAddress')">
          {{ selectedDevice.ip_address || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.port')">
          {{ selectedDevice.port || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.usageCount')">
          {{ selectedDevice.usage_count || 0 }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.createTime')">
          {{ formatDate(selectedDevice.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('appAutomation.device.updateTime')">
          {{ formatDate(selectedDevice.updated_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="deviceInfoDialogVisible = false">{{ t('appAutomation.common.close') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Monitor } from '@element-plus/icons-vue'
import {
  getDeviceList,
  discoverDevices,
  lockDevice as apiLockDevice,
  unlockDevice as apiUnlockDevice,
  connectDevice,
  disconnectDevice as apiDisconnectDevice,
  deleteDevice
} from '@/api/app-automation'
import { getDeviceStatusType, getDeviceStatusText, formatDateTime } from '@/utils/app-automation-helpers'

import { useRouter } from 'vue-router'

const { t } = useI18n()
const router = useRouter()

// Refs
const remoteDeviceFormRef = ref(null)

// 鍝嶅簲寮忔暟鎹?
const devices = ref([])
const loading = ref(false)
const refreshing = ref(false)
const connecting = ref(false)
const reconnectingDevices = ref({})
const addRemoteDialogVisible = ref(false)
const deviceInfoDialogVisible = ref(false)
const selectedDevice = ref(null)
const emptyText = ref(t('appAutomation.messages.noDevicesHint'))
const refreshTimer = ref(null)

const remoteDeviceForm = ref({
  ip_address: '',
  port: 5555
})

const remoteDeviceRules = {
  ip_address: [
    { required: true, message: t('appAutomation.messages.pleaseEnterIpAddress'), trigger: 'blur' },
    {
      pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
      message: t('appAutomation.messages.invalidIpAddress'),
      trigger: 'blur'
    }
  ],
  port: [
    { required: true, message: t('appAutomation.messages.pleaseEnterPort'), trigger: 'blur' }
  ]
}

// 鏂规硶
const getDevices = async () => {
  loading.value = true
  try {
    const res = await getDeviceList({ page: 1, page_size: 1000 })
    devices.value = res.data.results || []
    if (devices.value.length === 0) {
      emptyText.value = t('appAutomation.messages.noDevicesHint')
    }
  } catch (error) {
    console.error('鑾峰彇璁惧鍒楄〃澶辫触:', error)
    ElMessage.error(t('appAutomation.messages.getDeviceListFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
  } finally {
    loading.value = false
  }
}

const refreshDevices = async () => {
  refreshing.value = true
  try {
    const res = await discoverDevices()
    if (res.data.success) {
      devices.value = res.data.devices || []
      ElMessage.success(res.data.message || t('appAutomation.messages.deviceListRefreshed'))
    } else {
      ElMessage.error(res.data.message || t('appAutomation.messages.refreshDeviceListFailed'))
    }
  } catch (error) {
    console.error('鍒锋柊璁惧鍒楄〃澶辫触:', error)
    ElMessage.error(t('appAutomation.messages.refreshDeviceListFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
  } finally {
    refreshing.value = false
  }
}

const showAddRemoteDialog = () => {
  addRemoteDialogVisible.value = true
  remoteDeviceForm.value = {
    ip_address: '',
    port: 5555
  }
  if (remoteDeviceFormRef.value) {
    remoteDeviceFormRef.value.clearValidate()
  }
}

const connectRemoteDevice = async () => {
  if (!remoteDeviceFormRef.value) return
  
  remoteDeviceFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    connecting.value = true
    try {
      const res = await connectDevice({
        ip_address: remoteDeviceForm.value.ip_address,
        port: remoteDeviceForm.value.port
      })
      
      if (res.data.success) {
        ElMessage.success(res.data.message || t('appAutomation.messages.remoteDeviceConnected'))
        addRemoteDialogVisible.value = false
        await getDevices()
      } else {
        ElMessage.error(res.data.message || t('appAutomation.messages.connectRemoteDeviceFailed'))
      }
    } catch (error) {
      console.error('杩炴帴杩滅▼璁惧澶辫触:', error)
      ElMessage.error(t('appAutomation.messages.connectRemoteDeviceFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
    } finally {
      connecting.value = false
    }
  })
}

const reconnectDevice = async (device) => {
  if (!device.ip_address || !device.port) {
    ElMessage.error(t('appAutomation.messages.deviceInfoIncomplete'))
    return
  }

  reconnectingDevices.value[device.id] = true
  
  try {
    const res = await connectDevice({
      ip_address: device.ip_address,
      port: device.port
    })

    if (res.data.success) {
      ElMessage.success(t('appAutomation.messages.deviceReconnectSuccess'))
      await getDevices()
    } else {
      ElMessage.error(res.data.message || t('appAutomation.messages.deviceReconnectFailed'))
    }
  } catch (error) {
    console.error('璁惧閲嶈繛澶辫触:', error)
    ElMessage.error(t('appAutomation.messages.deviceReconnectFailed'))
  } finally {
    reconnectingDevices.value[device.id] = false
  }
}

const disconnectDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      t('appAutomation.messages.disconnectDeviceConfirm', { name: device.name || device.device_id }),
      t('appAutomation.messages.tip'),
      {
        confirmButtonText: t('appAutomation.messages.confirm'),
        cancelButtonText: t('appAutomation.messages.cancel'),
        type: 'warning'
      }
    )

    const res = await apiDisconnectDevice(device.id)

    if (res.data.success) {
      ElMessage.success(t('appAutomation.messages.deviceDisconnected'))
      await getDevices()
    } else {
      ElMessage.error(res.data.message || t('appAutomation.messages.disconnectDeviceFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('鏂紑璁惧澶辫触:', error)
      ElMessage.error(t('appAutomation.messages.disconnectDeviceFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
    }
  }
}

const viewDeviceInfo = (device) => {
  selectedDevice.value = device
  deviceInfoDialogVisible.value = true
}

const lockDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      t('appAutomation.messages.lockDeviceConfirm', { name: device.name || device.device_id }),
      t('appAutomation.messages.tip'),
      {
        confirmButtonText: t('appAutomation.messages.confirm'),
        cancelButtonText: t('appAutomation.messages.cancel'),
        type: 'warning'
      }
    )

    const res = await apiLockDevice(device.id)

    if (res.data.success) {
      ElMessage.success(t('appAutomation.messages.deviceLocked'))
      await getDevices()
    } else {
      ElMessage.error(res.data.message || t('appAutomation.messages.lockDeviceFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('閿佸畾璁惧澶辫触:', error)
      ElMessage.error(t('appAutomation.messages.lockDeviceFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
    }
  }
}

const unlockDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      t('appAutomation.messages.unlockDeviceConfirm', { name: device.name || device.device_id }),
      t('appAutomation.messages.tip'),
      {
        confirmButtonText: t('appAutomation.messages.confirm'),
        cancelButtonText: t('appAutomation.messages.cancel'),
        type: 'warning'
      }
    )

    const res = await apiUnlockDevice(device.id)

    if (res.data.success) {
      ElMessage.success(t('appAutomation.messages.deviceUnlocked'))
      await getDevices()
    } else {
      ElMessage.error(res.data.message || t('appAutomation.messages.unlockDeviceFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('瑙ｉ攣璁惧澶辫触:', error)
      ElMessage.error(t('appAutomation.messages.unlockDeviceFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
    }
  }
}

const handleDeleteDevice = async (device) => {
  try {
    await ElMessageBox.confirm(
      t('appAutomation.messages.deleteDeviceConfirm', { name: device.name || device.device_id }),
      t('appAutomation.messages.deleteDeviceTitle'),
      {
        confirmButtonText: t('appAutomation.messages.confirm'),
        cancelButtonText: t('appAutomation.messages.cancel'),
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )

    const res = await deleteDevice(device.id)

    if (res.status === 204 || res.status === 200) {
      ElMessage.success(t('appAutomation.messages.deviceDeleted'))
      await getDevices()
    } else {
      ElMessage.error(res.data?.message || t('appAutomation.messages.deleteDeviceFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('鍒犻櫎璁惧澶辫触:', error)
      ElMessage.error(t('appAutomation.messages.deleteDeviceFailed') + ': ' + (error.message || t('appAutomation.messages.unknownError')))
    }
  }
}

const formatDate = formatDateTime
const getStatusType = getDeviceStatusType
const getStatusText = (status) => getDeviceStatusText(status, t)

const getConnectionType = (type) => {
  // emulator, remote_emulator, remote, usb 绛?
  if (type === 'emulator' || type === 'usb') {
    return 'local'
  }
  return 'remote'
}

const getConnectionTypeName = (type) => {
  const typeMap = {
    'emulator': '本地模拟器',
    'remote_emulator': '远程模拟器',
    'remote': '远程设备',
    'usb': 'USB设备'
  }
  return typeMap[type] || type
}

const isRemoteDevice = (type) => {
  return type === 'remote_emulator' || type === 'remote'
}

// 璺宠浆鍒拌繙绋嬭繛鎺ラ〉闈?
const goToRemoteConnection = (row) => {
  if (!row || !row.id) {
    ElMessage.warning('设备信息不完整')
    return
  }
  router.push({
    name: 'AppRemoteWorkbench',
    params: {
      id: row.id
    },
    query: {
      name: row.name || row.device_id
    }
  })
}

// 鐢熷懡鍛ㄦ湡
onMounted(() => {
  getDevices()

  // 30绉掕嚜鍔ㄥ埛鏂拌澶囧垪琛?
  refreshTimer.value = setInterval(() => {
    getDevices()
  }, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})
</script>

<style scoped lang="scss">
.device-management {
  padding: 20px;
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h3 {
    margin: 0;
    font-size: 20px;
    color: #303133;
  }
}

.device-actions {
  display: flex;
  gap: 10px;
}

.dialog-footer {
  text-align: right;
}
</style>

