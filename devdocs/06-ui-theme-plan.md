# UI 主题切换方案（Hoppscotch 风格参考）

## 目标
在现有前端中加入“主题按钮”，点击可切换 UI 主题，使整个平台形成统一风格，并可扩展更多主题。风格参考 Hoppscotch 的设计逻辑：清爽、低干扰、冷灰中性基调 + 明确的品牌强调色、轻质感阴影、卡片/面板分层清晰。

## 项目架构与前端特性概览（基于现有代码）

### 后端
- Django + DRF，应用划分清晰（apps/…），提供 REST API。
- 功能模块多，前端以路由模块组织。

### 前端
- Vue 3 + Composition API + Vite。
- UI 组件使用 Element Plus。
- 全局样式入口：`frontend/src/assets/css/global.scss`（已引入）。
- 布局统一入口：`frontend/src/layout/index.vue`。
- 全局状态：Pinia，`frontend/src/stores/app.js` 仅包含语言设置。
- i18n：`frontend/src/locales`。

结论：适合使用“CSS 变量 + 根节点 data-theme”方式实现主题切换，并通过 Pinia 持久化主题选择。

---

## 主题策略（可执行）

### 1) 主题控制机制
- 在 `html` 或 `body` 上设置 `data-theme`：
  - `data-theme="hoppscotch-light"`
  - `data-theme="hoppscotch-dark"`
- 主题切换由 Pinia `app` store 管理，持久化在 `localStorage`。
- 初始加载时读取本地配置，应用主题。

### 2) CSS 变量体系
- 定义全局设计 tokens（颜色/字体/圆角/阴影/间距）。
- 每个主题在 `[data-theme="..."]` 下覆盖。
- 尽量通过 CSS 变量驱动 Element Plus 主题变量（`--el-color-primary` 等）。

### 3) UI 入口
- 在 `frontend/src/layout/index.vue` 顶部右侧加入“主题按钮”或下拉菜单。
- 形式建议：`el-dropdown`（可扩展多主题）。

---

## 主题设计（参考 Hoppscotch 逻辑）

### Hoppscotch Light（默认）
- 冷灰背景、白色卡片、紫色强调。
- 轻阴影、小分层、可读性强。

### Hoppscotch Dark（可选）
- 深灰背景、微亮卡片、紫色强调。
- 保持对比度、减少炫光。

---

## 主题 Tokens 建议（可直接落地）

> 这些变量会放在 `global.scss` 中，并以 `:root` 或 `[data-theme]` 控制。

### 通用变量
```
--th-font-sans: "Manrope", "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
--th-font-display: "Sora", "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;

--th-radius-sm: 8px;
--th-radius-md: 12px;
--th-radius-lg: 16px;

--th-shadow-sm: 0 6px 16px rgba(31, 41, 55, 0.08);
--th-shadow-md: 0 14px 30px rgba(31, 41, 55, 0.12);
```

### Hoppscotch Light
```
--th-color-bg: #eef2f7;
--th-color-surface: #ffffff;
--th-color-surface-muted: #f8fafc;
--th-color-text: #1f2937;
--th-color-text-muted: #6b7280;
--th-color-border: #e5e7eb;
--th-color-primary: #7c3aed;
--th-color-primary-strong: #6d28d9;
--th-color-primary-soft: #ede9fe;
```

### Hoppscotch Dark
```
--th-color-bg: #0b0f1a;
--th-color-surface: #121826;
--th-color-surface-muted: #1a2132;
--th-color-text: #e5e7eb;
--th-color-text-muted: #9ca3af;
--th-color-border: #2a3142;
--th-color-primary: #8b5cf6;
--th-color-primary-strong: #7c3aed;
--th-color-primary-soft: rgba(139, 92, 246, 0.15);
```

### Element Plus 变量覆盖建议
```
--el-color-primary: var(--th-color-primary);
--el-color-primary-light-3: var(--th-color-primary-soft);
--el-text-color-primary: var(--th-color-text);
--el-text-color-regular: var(--th-color-text-muted);
--el-border-color: var(--th-color-border);
--el-bg-color: var(--th-color-surface);
--el-bg-color-page: var(--th-color-bg);
```

---

## 实施步骤（可执行）

### Step 1: 扩展 App Store
文件：`frontend/src/stores/app.js`
- 新增 `theme` 状态（默认 `hoppscotch-light`）。
- 新增 `setTheme()` 方法：
  - 更新 store
  - 写入 `localStorage`
  - 设置 `document.documentElement.dataset.theme`
- 在 store 初始化时读取本地并执行应用。

### Step 2: 全局样式与主题变量
文件：`frontend/src/assets/css/global.scss`
- 在 `:root` 中定义通用 tokens。
- 在 `[data-theme="hoppscotch-light"]` 和 `[data-theme="hoppscotch-dark"]` 下设置颜色变量。
- 同步 Element Plus CSS 变量。

### Step 3: 布局中加入主题按钮
文件：`frontend/src/layout/index.vue`
- 在 header 右侧加一个 `el-dropdown`：
  - 选项：Hoppscotch Light / Hoppscotch Dark
  - 点击调用 `appStore.setTheme()`
- 入口位置建议放在语言切换右侧或左侧。

### Step 4: i18n 文案
文件：
- `frontend/src/locales/lang/zh-cn/nav.js`
- `frontend/src/locales/lang/en/nav.js`

新增：
- `theme.light` / `theme.dark` / `theme.switch`

### Step 5: 验证范围
- 首页、API 测试页、UI 自动化页面、表格/表单等 Element Plus 组件。
- 重点检查对比度与边框可见性。

---

## 交付清单（实现后应包含）
- `app.js` 新增主题状态与切换逻辑。
- `global.scss` 主题 token 与 Element Plus 变量覆盖。
- `layout/index.vue` 主题切换 UI。
- `i18n` 多语言支持。
- 说明文档（本文件）。

---

## 风险与注意事项
- Element Plus 组件在暗色主题下对比度不足，需要对 `el-bg-color` 和 `el-border-color` 做额外微调。
- 第三方组件（Monaco/ECharts）主题需单独适配：
  - Monaco 可按主题切换 `monaco.editor.setTheme()`。
  - ECharts 需要统一设置主题或给定颜色方案。

---

## 建议后续迭代
- 增加“主题预览小卡片”选择器。
- 增加“跟随系统主题”选项（`prefers-color-scheme`）。
- 添加浅色主题的背景装饰（圆形渐变）以增强 Hoppscotch 风格。
