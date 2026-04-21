<template>
  <div class="real-device-management">
    <h2 class="page-title">真机设备管理</h2>
    
    <!-- Filter Section -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="filter-item">
            <span class="filter-label">手机品牌</span>
            <el-select v-model="filters.brand" placeholder="所有品牌" clearable>
              <el-option label="所有品牌" value="" />
              <el-option label="华为" value="华为" />
              <el-option label="OPPO" value="OPPO" />
              <el-option label="HONOR" value="HONOR" />
              <el-option label="小米" value="XiaoMi" />
              <el-option label="三星" value="三星" />
            </el-select>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="filter-item">
            <span class="filter-label">系统版本</span>
            <el-select v-model="filters.version" placeholder="所有版本" clearable>
              <el-option label="所有版本" value="" />
              <el-option label="Android 11" value="11" />
              <el-option label="Android 12" value="12" />
              <el-option label="Android 13" value="13" />
              <el-option label="Android 14" value="14" />
            </el-select>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="filter-item">
            <span class="filter-label">设备状态</span>
            <el-select v-model="filters.status" placeholder="所有状态" clearable>
              <el-option label="所有状态" value="" />
              <el-option label="在线" value="online" />
              <el-option label="离线" value="offline" />
            </el-select>
          </div>
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- Device Grid -->
    <el-card shadow="never" class="device-grid-card">
      <div class="device-grid" v-loading="loading">
        <div 
          v-for="device in filteredDevices" 
          :key="device.id" 
          class="device-card"
        >
          <div class="device-header">
            <el-tag size="small" type="info">{{ device.brand }}</el-tag>
            <el-tag 
              :type="device.status === 'online' ? 'success' : 'warning'" 
              size="small"
            >
              {{ device.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </div>
          
          <div class="device-image">
            <img :src="device.image || getDefaultImage(device.brand)" :alt="device.name" />
          </div>
          
          <div class="device-info">
            <div class="device-name">{{ device.name }}</div>
            <div class="device-serial">{{ device.serial }}</div>
            <div class="device-version">版本: {{ device.version }}</div>
          </div>
          
          <div class="device-actions">
            <el-popover
              placement="top"
              :width="280"
              trigger="hover"
              popper-class="device-info-popover"
            >
              <template #reference>
                <el-button size="small">
                  <el-icon><InfoFilled /></el-icon>
                  设备信息
                </el-button>
              </template>
              <div class="popover-device-info">
                <div class="popover-device-name">{{ device.name }}</div>
                <div class="popover-info-item">
                  <span class="label">手机卡：</span>
                  <span class="value">{{ device.simCard || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">系统版本：</span>
                  <span class="value">{{ device.version }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">CPU：</span>
                  <span class="value">{{ device.cpu || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">内存：</span>
                  <span class="value">{{ device.storage || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">运行内存：</span>
                  <span class="value">{{ device.ram || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">电池：</span>
                  <span class="value">{{ device.battery || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">分辨率：</span>
                  <span class="value">{{ device.resolution || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">屏幕尺寸：</span>
                  <span class="value">{{ device.screenSize || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">连接类型：</span>
                  <span class="value">{{ device.connectionType || '-' }}</span>
                </div>
                <div class="popover-info-item">
                  <span class="label">IP地址：</span>
                  <span class="value">{{ device.ipAddress || '-' }}</span>
                </div>
              </div>
            </el-popover>
            <el-button size="small" type="success" @click="handleUseDevice(device)">
              <el-icon><VideoPlay /></el-icon>
              立即使用
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- Pagination -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[12, 24, 48]"
          :total="totalDevices"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- Device Info Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="`设备信息 - ${currentDevice?.name}`"
      width="600px"
    >
      <el-descriptions v-if="currentDevice" :column="2" border>
        <el-descriptions-item label="设备名称">
          {{ currentDevice.name }}
        </el-descriptions-item>
        <el-descriptions-item label="品牌">
          {{ currentDevice.brand }}
        </el-descriptions-item>
        <el-descriptions-item label="序列号">
          {{ currentDevice.serial }}
        </el-descriptions-item>
        <el-descriptions-item label="系统版本">
          {{ currentDevice.version }}
        </el-descriptions-item>
        <el-descriptions-item label="设备状态">
          <el-tag :type="currentDevice.status === 'online' ? 'success' : 'warning'">
            {{ currentDevice.status === 'online' ? '在线' : '离线' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="分辨率">
          {{ currentDevice.resolution || '未知' }}
        </el-descriptions-item>
        <el-descriptions-item label="最后连接时间">
          {{ currentDevice.lastConnected || '未知' }}
        </el-descriptions-item>
        <el-descriptions-item label="备注">
          {{ currentDevice.remarks || '无' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, VideoPlay } from '@element-plus/icons-vue'

const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(24)
const dialogVisible = ref(false)
const currentDevice = ref(null)

const filters = ref({
  brand: '',
  version: '',
  status: ''
})

// Mock device data - replace with actual API call
const allDevices = ref([
  {
    id: 1,
    brand: '华为',
    name: '华为 nova 11',
    serial: '9TM9K23404015786',
    version: '4.0.0',
    status: 'offline',
    image: '',
    resolution: '1080x2400',
    lastConnected: '2024-01-15 10:30:00',
    remarks: '',
    simCard: '-',
    cpu: '高通骁龙™ 778G',
    storage: '256GB',
    ram: '8GB',
    battery: '4800毫安',
    screenSize: '6.7英寸',
    connectionType: '-',
    ipAddress: '-'
  },
  {
    id: 2,
    brand: 'OPPO',
    name: 'OPPO K9',
    serial: '6faf7764',
    version: '12',
    status: 'offline',
    image: '',
    resolution: '1080x2400',
    lastConnected: '2024-01-14 15:20:00',
    remarks: '',
    simCard: '-',
    cpu: '高通骁龙™ 768G',
    storage: '128GB',
    ram: '8GB',
    battery: '4300毫安',
    screenSize: '6.43英寸',
    connectionType: '-',
    ipAddress: '-'
  },
  {
    id: 3,
    brand: 'HONOR',
    name: 'HONOR 60',
    serial: 'AXYFV81C03005594',
    version: '12',
    status: 'offline',
    image: '',
    resolution: '2400*1080',
    lastConnected: '2024-01-13 09:15:00',
    remarks: '',
    simCard: '-',
    cpu: '高通骁龙™ 778G',
    storage: '256GB',
    ram: '8GB',
    battery: '4800毫安',
    screenSize: '6.43英寸',
    connectionType: '-',
    ipAddress: '-'
  },
  {
    id: 4,
    brand: 'XiaoMi',
    name: 'XiaoMi K40 Pro',
    serial: 'f87c1a21',
    version: '11',
    status: 'offline',
    image: '',
    resolution: '1080x2400',
    lastConnected: '2024-01-12 14:45:00',
    remarks: '',
    simCard: '-',
    cpu: '高通骁龙™ 888',
    storage: '256GB',
    ram: '8GB',
    battery: '4520毫安',
    screenSize: '6.67英寸',
    connectionType: '-',
    ipAddress: '-'
  },
  {
    id: 5,
    brand: '华为',
    name: '华为 nova 5 Pro',
    serial: '6HJDU19723002103',
    version: '3.0.0',
    status: 'offline',
    image: '',
    resolution: '1080x2340',
    lastConnected: '2024-01-11 11:30:00',
    remarks: '',
    simCard: '-',
    cpu: '麒麟980',
    storage: '256GB',
    ram: '8GB',
    battery: '3500毫安',
    screenSize: '6.39英寸',
    connectionType: '-',
    ipAddress: '-'
  },
  {
    id: 6,
    brand: '三星',
    name: '三星 Galaxy A54 5G',
    serial: 'R5CW32RABBR',
    version: '13',
    status: 'offline',
    image: '',
    resolution: '1080x2340',
    lastConnected: '2024-01-10 16:00:00',
    remarks: '',
    simCard: '-',
    cpu: 'Exynos 1380',
    storage: '128GB',
    ram: '8GB',
    battery: '5000毫安',
    screenSize: '6.4英寸',
    connectionType: '-',
    ipAddress: '-'
  }
])

const filteredDevices = computed(() => {
  let result = allDevices.value
  
  if (filters.value.brand) {
    result = result.filter(d => d.brand === filters.value.brand)
  }
  if (filters.value.version) {
    result = result.filter(d => d.version === filters.value.version)
  }
  if (filters.value.status) {
    result = result.filter(d => d.status === filters.value.status)
  }
  
  return result
})

const totalDevices = computed(() => filteredDevices.value.length)

const getDefaultImage = (brand) => {
  // Return a placeholder image based on brand
  return 'https://via.placeholder.com/200x300?text=' + brand
}

const handleSearch = () => {
  currentPage.value = 1
  ElMessage.success('搜索完成')
}

const handleReset = () => {
  filters.value = {
    brand: '',
    version: '',
    status: ''
  }
  currentPage.value = 1
}

const handleDeviceInfo = (device) => {
  currentDevice.value = device
  dialogVisible.value = true
}

const handleUseDevice = (device) => {
  if (device.status === 'offline') {
    ElMessage.warning('设备当前离线，无法使用')
    return
  }
  // TODO: Implement device usage logic (e.g., open web-scrcpy connection)
  ElMessage.success(`正在连接设备: ${device.name}`)
}

const handleSizeChange = (size) => {
  pageSize.value = size
}

const handleCurrentChange = (page) => {
  currentPage.value = page
}

onMounted(() => {
  // TODO: Load devices from API
  loading.value = false
})
</script>

<style scoped lang="scss">
.real-device-management {
  padding: 20px;
  
  .page-title {
    font-size: 20px;
    font-weight: bold;
    color: #303133;
    margin: 0 0 20px 0;
  }
  
  .filter-card {
    margin-bottom: 20px;
    
    .filter-item {
      display: flex;
      align-items: center;
      gap: 10px;
      
      .filter-label {
        white-space: nowrap;
        color: #606266;
        font-size: 14px;
      }
      
      .el-select {
        flex: 1;
      }
    }
  }
  
  .device-grid-card {
    .device-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 20px;
      margin-bottom: 20px;
      
      .device-card {
        border: 1px solid #e4e7ed;
        border-radius: 8px;
        padding: 15px;
        background: #fff;
        transition: all 0.3s;
        cursor: pointer;
        
        &:hover {
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
          transform: translateY(-2px);
        }
        
        .device-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;
        }
        
        .device-image {
          width: 100%;
          height: 180px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f5f7fa;
          border-radius: 4px;
          margin-bottom: 15px;
          
          img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
          }
        }
        
        .device-info {
          margin-bottom: 15px;
          
          .device-name {
            font-size: 16px;
            font-weight: bold;
            color: #303133;
            margin-bottom: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          
          .device-serial {
            font-size: 12px;
            color: #909399;
            margin-bottom: 4px;
          }
          
          .device-version {
            font-size: 12px;
            color: #606266;
          }
        }
        
        .device-actions {
          display: flex;
          gap: 10px;
          
          .el-button {
            flex: 1;
          }
        }
      }
    }
    
    .pagination-wrapper {
      display: flex;
      justify-content: flex-end;
      padding-top: 20px;
      border-top: 1px solid #e4e7ed;
    }
  }
}

// Popover样式
:deep(.device-info-popover) {
  padding: 0 !important;
  
  .popover-device-info {
    .popover-device-name {
      font-size: 18px;
      font-weight: bold;
      color: #303133;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #e4e7ed;
    }
    
    .popover-info-item {
      display: flex;
      padding: 6px 0;
      font-size: 14px;
      line-height: 1.6;
      
      .label {
        color: #606266;
        font-weight: 500;
        min-width: 80px;
        flex-shrink: 0;
      }
      
      .value {
        color: #303133;
        flex: 1;
      }
    }
  }
}
</style>
