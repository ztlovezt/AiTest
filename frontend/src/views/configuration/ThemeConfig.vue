<template>
  <div class="theme-config page-container">
    <div class="page-header">
      <h2 class="page-title">{{ $t('menu.themeConfig') }}</h2>
    </div>

    <div class="theme-grid">
      <!-- 主题一：Indigo -->
      <div
        class="theme-card theme-indigo"
        :class="{ active: appStore.colorTheme === 'indigo' }"
        @click="selectTheme('indigo')"
      >
        <div class="theme-preview indigo-preview">
          <div class="preview-sidebar">
            <div class="preview-logo"></div>
            <div class="preview-menu-item"></div>
            <div class="preview-menu-item active"></div>
            <div class="preview-menu-item"></div>
          </div>
          <div class="preview-main">
            <div class="preview-header"></div>
            <div class="preview-content">
              <div class="preview-card"></div>
              <div class="preview-card"></div>
            </div>
          </div>
        </div>
        <div class="theme-info">
          <div class="theme-name-row">
            <span class="theme-name">{{ $t('themeConfig.indigo') }}</span>
            <el-tag v-if="appStore.colorTheme === 'indigo'" type="primary" size="small" effect="dark" round>
              {{ $t('themeConfig.current') }}
            </el-tag>
          </div>
          <p class="theme-desc">{{ $t('themeConfig.indigoDesc') }}</p>
          <div class="theme-colors">
            <span class="color-dot" style="background: #5b5bd6"></span>
            <span class="color-dot" style="background: #4747c2"></span>
            <span class="color-dot" style="background: #eef0ff"></span>
            <span class="color-dot" style="background: #7c7ce0"></span>
          </div>
        </div>
      </div>

      <!-- 主题二：Semi Orange -->
      <div
        class="theme-card theme-orange"
        :class="{ active: appStore.colorTheme === 'semi-orange' }"
        @click="selectTheme('semi-orange')"
      >
        <div class="theme-preview orange-preview">
          <div class="preview-sidebar">
            <div class="preview-logo"></div>
            <div class="preview-menu-item"></div>
            <div class="preview-menu-item active"></div>
            <div class="preview-menu-item"></div>
          </div>
          <div class="preview-main">
            <div class="preview-header"></div>
            <div class="preview-content">
              <div class="preview-card"></div>
              <div class="preview-card"></div>
            </div>
          </div>
        </div>
        <div class="theme-info">
          <div class="theme-name-row">
            <span class="theme-name">{{ $t('themeConfig.semiOrange') }}</span>
            <el-tag v-if="appStore.colorTheme === 'semi-orange'" size="small" effect="dark" round
              style="--el-tag-bg-color: #F5722B; --el-tag-border-color: #F5722B; --el-tag-text-color: #fff;">
              {{ $t('themeConfig.current') }}
            </el-tag>
          </div>
          <p class="theme-desc">{{ $t('themeConfig.semiOrangeDesc') }}</p>
          <div class="theme-colors">
            <span class="color-dot" style="background: #F5722B"></span>
            <span class="color-dot" style="background: #D4580D"></span>
            <span class="color-dot" style="background: #FFF3EB"></span>
            <span class="color-dot" style="background: #E8793A"></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const appStore = useAppStore()

const selectTheme = (themeKey) => {
  if (appStore.colorTheme === themeKey) return
  appStore.setColorTheme(themeKey)
  ElMessage.success(t('themeConfig.applied'))
}
</script>

<style scoped>
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 24px;
  max-width: 900px;
}

.theme-card {
  background: var(--th-color-surface);
  border: 2px solid var(--th-color-border);
  border-radius: var(--th-radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
}

.theme-card:hover {
  transform: translateY(-2px);
}

.theme-card.active {
  border-color: var(--th-color-primary);
  box-shadow: 0 0 0 3px var(--th-color-primary-soft), 0 8px 24px rgba(0, 0, 0, 0.08);
}

/* 主题预览 */
.theme-preview {
  height: 180px;
  display: flex;
  padding: 12px;
  gap: 8px;
  background: #f1f5f9;
  position: relative;
}

.preview-sidebar {
  width: 48px;
  background: #ffffff;
  border-radius: 8px;
  padding: 8px 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preview-logo {
  width: 100%;
  height: 18px;
  border-radius: 4px;
  background: #e2e8f0;
}

.preview-menu-item {
  width: 100%;
  height: 10px;
  border-radius: 3px;
  background: #e2e8f0;
}

.preview-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-header {
  height: 20px;
  background: #ffffff;
  border-radius: 6px;
}

.preview-content {
  flex: 1;
  display: flex;
  gap: 8px;
}

.preview-card {
  flex: 1;
  background: #ffffff;
  border-radius: 6px;
}

/* Indigo 主题预览色 */
.indigo-preview .preview-menu-item.active {
  background: #5b5bd6;
}

.indigo-preview .preview-logo {
  background: linear-gradient(135deg, #5b5bd6, #7c7ce0);
}

/* Semi Orange 主题预览色 */
.orange-preview .preview-menu-item.active {
  background: #F5722B;
}

.orange-preview .preview-logo {
  background: linear-gradient(135deg, #F5722B, #E8793A);
}

/* Hover 效果根据预览主题色 */
.theme-card.theme-indigo:hover {
  border-color: #5b5bd6;
  box-shadow: 0 8px 24px rgba(91, 91, 214, 0.15);
}

.theme-card.theme-orange:hover {
  border-color: #F5722B;
  box-shadow: 0 8px 24px rgba(245, 114, 43, 0.15);
}

/* 主题信息 */
.theme-info {
  padding: 16px;
}

.theme-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.theme-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--th-color-text);
}

.theme-desc {
  font-size: 13px;
  color: var(--th-color-text-muted);
  margin: 0 0 12px;
  line-height: 1.5;
}

.theme-colors {
  display: flex;
  gap: 8px;
}

.color-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--th-color-border);
}
</style>
