<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('profile.title') }}</h1>
    </div>

    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="$t('profile.basicInfo')" name="basic">
          <el-form v-if="userStore.user" :model="formData" label-width="100px" :rules="rules" ref="formRef">
            <el-form-item :label="$t('profile.username')">
              <el-input v-model="formData.username" disabled />
            </el-form-item>
            <el-form-item :label="$t('profile.email')" prop="email">
              <el-input v-model="formData.email" />
            </el-form-item>
            <el-form-item :label="$t('profile.name')">
              <el-input v-model="formData.first_name" />
            </el-form-item>
            <el-form-item :label="$t('profile.department')">
              <el-input v-model="formData.department" />
            </el-form-item>
            <el-form-item :label="$t('profile.position')">
              <el-input v-model="formData.position" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSave" :loading="saving">{{ $t('common.save') }}</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="$t('profile.changePassword')" name="password">
          <el-form :model="passwordForm" label-width="120px" :rules="passwordRules" ref="passwordFormRef">
            <el-form-item :label="$t('profile.currentPassword')" prop="current_password">
              <el-input v-model="passwordForm.current_password" type="password" show-password />
            </el-form-item>
            <el-form-item :label="$t('profile.newPassword')" prop="new_password">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item :label="$t('profile.confirmPassword')" prop="confirm_password">
              <el-input v-model="passwordForm.confirm_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleChangePassword" :loading="changingPassword">{{ $t('profile.changePasswordButton') }}</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const userStore = useUserStore()
const activeTab = ref('basic')
const saving = ref(false)
const changingPassword = ref(false)
const formRef = ref(null)
const passwordFormRef = ref(null)

const formData = reactive({
  username: '',
  email: '',
  first_name: '',
  department: '',
  position: ''
})

const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const rules = {
  email: [
    { required: true, message: t('profile.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('profile.emailInvalid'), trigger: 'blur' }
  ]
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.new_password) {
    callback(new Error(t('profile.passwordMismatch')))
  } else {
    callback()
  }
}

const passwordRules = {
  current_password: [
    { required: true, message: t('profile.currentPasswordRequired'), trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: t('profile.newPasswordRequired'), trigger: 'blur' },
    { min: 6, message: t('profile.passwordMinLength'), trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: t('profile.confirmPasswordRequired'), trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

watch(() => userStore.user, (newUser) => {
  if (newUser) {
    formData.username = newUser.username || ''
    formData.email = newUser.email || ''
    formData.first_name = newUser.first_name || ''
    formData.department = newUser.department || ''
    formData.position = newUser.position || ''
  }
}, { immediate: true })

const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const response = await api.patch(`/auth/users/${userStore.user.id}/`, {
      email: formData.email,
      first_name: formData.first_name,
      department: formData.department,
      position: formData.position
    })
    
    userStore.user = { ...userStore.user, ...response.data }
    localStorage.setItem('user', JSON.stringify(userStore.user))
    
    ElMessage.success(t('profile.saveSuccess'))
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error(t('profile.saveFailed') + ': ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  
  try {
    await passwordFormRef.value.validate()
  } catch {
    return
  }

  changingPassword.value = true
  try {
    await api.post('/auth/change-password/', {
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password
    })
    
    ElMessage.success(t('profile.passwordChangeSuccess'))
    
    passwordForm.current_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    
  } catch (error) {
    console.error('修改密码失败:', error)
    ElMessage.error(t('profile.passwordChangeFailed') + ': ' + (error.response?.data?.error || error.message))
  } finally {
    changingPassword.value = false
  }
}
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.card-container {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

:deep(.el-form) {
  max-width: 500px;
}

:deep(.el-input) {
  width: 100%;
}
</style>
