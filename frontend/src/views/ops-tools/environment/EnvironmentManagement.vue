<template>
  <div class="ops-environment-page">
    <div class="page-header">
      <div class="page-header-title">
        <h2>{{ $t("opsTools.environment.title") }}</h2>
        <p>{{ $t("opsTools.environment.subtitle") }}</p>
      </div>
      <div class="page-header__actions">
        <el-button @click="openCategoryDialog">
          {{ $t("opsTools.environment.manageCategories") }}
        </el-button>
        <el-button @click="openImportDialog">
          {{ $t("opsTools.environment.importJson") }}
        </el-button>
        <el-button type="primary" @click="openCreateDrawer">
          {{ $t("opsTools.environment.create") }}
        </el-button>
      </div>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <span>{{ $t("opsTools.environment.summary.total") }}</span>
        <strong>{{ summary.total }}</strong>
      </div>
      <div class="summary-card">
        <span>{{ $t("opsTools.environment.summary.categories") }}</span>
        <strong>{{ summary.categories }}</strong>
      </div>
      <div class="summary-card">
        <span>{{ $t("opsTools.environment.summary.active") }}</span>
        <strong>{{ summary.active }}</strong>
      </div>
    </div>

    <el-card shadow="never">
      <el-form :inline="true" :model="filters">
        <el-form-item :label="$t('opsTools.environment.filters.keyword')">
          <el-input
            v-model="filters.keyword"
            clearable
            :placeholder="$t('opsTools.environment.filters.keywordPlaceholder')"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item :label="$t('opsTools.environment.filters.category')">
          <el-select v-model="filters.category" clearable style="width: 180px">
            <el-option
              v-for="item in categoryOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('opsTools.environment.filters.type')">
          <el-select
            v-model="filters.environment_type"
            clearable
            style="width: 160px"
          >
            <el-option
              v-for="item in environmentTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            {{ $t("common.search") }}
          </el-button>
          <el-button @click="handleReset">
            {{ $t("common.reset") }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="tableData">
        <el-table-column
          prop="name"
          :label="$t('opsTools.environment.columns.name')"
          min-width="180"
        />
        <el-table-column
          :label="$t('opsTools.environment.columns.category')"
          min-width="140"
        >
          <template #default="{ row }">
            <el-tag effect="plain">{{ row.category_name || "-" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('opsTools.environment.columns.type')"
          width="120"
        >
          <template #default="{ row }">
            <el-tag :type="typeTagType(row.environment_type)">
              {{ getEnvironmentTypeLabel(row.environment_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('opsTools.environment.columns.accessMode')"
          width="120"
        >
          <template #default="{ row }">
            <el-tag effect="plain">
              {{ getAccessModeLabel(row.access_mode) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="ssh_host"
          :label="$t('opsTools.environment.columns.sshHost')"
          min-width="160"
        />
        <el-table-column
          :label="$t('opsTools.environment.columns.directories')"
          width="120"
        >
          <template #default="{ row }">
            {{ row.category_directories?.length || 0 }}
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('opsTools.environment.columns.middlewares')"
          min-width="210"
        >
          <template #default="{ row }">
            <div class="middleware-tags">
              <el-tag v-if="row.mysql_config?.enabled" size="small">MySQL</el-tag>
              <el-tag
                v-if="row.redis_config?.enabled"
                size="small"
                type="success"
              >
                Redis
              </el-tag>
              <el-tag
                v-if="row.mongo_config?.enabled"
                size="small"
                type="warning"
              >
                Mongo
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('opsTools.environment.columns.status')"
          width="100"
        >
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" disabled />
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('opsTools.environment.columns.operation')"
          fixed="right"
          width="240"
        >
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDrawer(row)">
              {{ $t("opsTools.environment.actions.edit") }}
            </el-button>
            <el-button link type="success" @click="handleTestConnection(row)">
              {{ $t("opsTools.environment.testConnection") }}
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">
              {{ $t("opsTools.environment.actions.delete") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          @current-change="loadData"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      :title="
        editingId
          ? $t('opsTools.environment.edit')
          : $t('opsTools.environment.create')
      "
      size="1180px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="118px"
        class="env-form"
      >
        <section class="form-section">
          <div class="form-section__title">
            {{ $t("opsTools.environment.sections.basic") }}
          </div>
          <div class="form-grid">
            <el-form-item prop="category">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.category')"
                  :value="selectedCategoryName"
                />
              </template>
              <el-select v-model="form.category" filterable>
                <el-option
                  v-for="item in categoryOptions"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item prop="name">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.name')"
                  :value="form.name"
                />
              </template>
              <el-input v-model="form.name" />
            </el-form-item>
            <el-form-item prop="env_code">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.code')"
                  :value="form.env_code"
                />
              </template>
              <el-input v-model="form.env_code" />
            </el-form-item>
            <el-form-item prop="environment_type">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.type')"
                  :value="getEnvironmentTypeLabel(form.environment_type)"
                />
              </template>
              <el-select v-model="form.environment_type">
                <el-option
                  v-for="item in environmentTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.isActive')"
                  :value="form.is_active ? 'true' : 'false'"
                />
              </template>
              <el-switch v-model="form.is_active" />
            </el-form-item>
            <el-form-item class="span-2">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.description')"
                  :value="form.description"
                />
              </template>
              <el-input v-model="form.description" type="textarea" :rows="3" />
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="form-section__title">
            {{ $t("opsTools.environment.sections.ssh") }}
          </div>
          <div class="form-grid">
            <el-form-item prop="ssh_host">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.sshHost')"
                  :value="form.ssh_host"
                />
              </template>
              <el-input v-model="form.ssh_host" />
            </el-form-item>
            <el-form-item prop="ssh_port">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.sshPort')"
                  :value="form.ssh_port"
                />
              </template>
              <el-input-number v-model="form.ssh_port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item prop="ssh_username">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.sshUsername')"
                  :value="form.ssh_username"
                />
              </template>
              <el-input v-model="form.ssh_username" />
            </el-form-item>
            <el-form-item prop="ssh_password">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.sshPassword')"
                  :value="form.ssh_password"
                />
              </template>
              <el-input
                v-model="form.ssh_password"
                type="password"
                show-password
              />
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="form-section__title">
            {{ $t("opsTools.environment.sections.links") }}
          </div>
          <div class="form-grid">
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.clientUrl')"
                  :value="form.client_url"
                />
              </template>
              <el-input v-model="form.client_url" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.adminUrl')"
                  :value="form.admin_url"
                />
              </template>
              <el-input v-model="form.admin_url" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.imageHost')"
                  :value="form.image_host"
                />
              </template>
              <el-input v-model="form.image_host" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.officialUrl')"
                  :value="form.official_url"
                />
              </template>
              <el-input v-model="form.official_url" />
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="form-section__title">
            {{ $t("opsTools.environment.sections.redis") }}
          </div>
          <div class="form-grid">
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.redisEnabled')"
                  :value="form.redis_enabled ? 'true' : 'false'"
                />
              </template>
              <el-switch v-model="form.redis_enabled" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.redisUseSsh')"
                  :value="form.redis_use_ssh ? 'true' : 'false'"
                />
              </template>
              <el-switch v-model="form.redis_use_ssh" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.redisHost')"
                  :value="form.redis_host"
                />
              </template>
              <el-input v-model="form.redis_host" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.redisPort')"
                  :value="form.redis_port"
                />
              </template>
              <el-input-number
                v-model="form.redis_port"
                :min="1"
                :max="65535"
              />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.redisUsername')"
                  :value="form.redis_username"
                />
              </template>
              <el-input v-model="form.redis_username" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.redisPassword')"
                  :value="form.redis_password"
                />
              </template>
              <el-input
                v-model="form.redis_password"
                type="password"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.redisDb')"
                  :value="form.redis_db"
                />
              </template>
              <el-input-number v-model="form.redis_db" :min="0" :max="64" />
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="form-section__title">
            {{ $t("opsTools.environment.sections.mysql") }}
          </div>
          <div class="form-grid">
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mysqlEnabled')"
                  :value="form.mysql_enabled ? 'true' : 'false'"
                />
              </template>
              <el-switch v-model="form.mysql_enabled" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mysqlUseSsh')"
                  :value="form.mysql_use_ssh ? 'true' : 'false'"
                />
              </template>
              <el-switch v-model="form.mysql_use_ssh" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mysqlHost')"
                  :value="form.mysql_host"
                />
              </template>
              <el-input v-model="form.mysql_host" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mysqlPort')"
                  :value="form.mysql_port"
                />
              </template>
              <el-input-number
                v-model="form.mysql_port"
                :min="1"
                :max="65535"
              />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mysqlUsername')"
                  :value="form.mysql_username"
                />
              </template>
              <el-input v-model="form.mysql_username" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mysqlPassword')"
                  :value="form.mysql_password"
                />
              </template>
              <el-input
                v-model="form.mysql_password"
                type="password"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mysqlDatabase')"
                  :value="form.mysql_database"
                />
              </template>
              <el-input v-model="form.mysql_database" />
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="form-section__title">
            {{ $t("opsTools.environment.sections.mongo") }}
          </div>
          <div class="form-grid">
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoEnabled')"
                  :value="form.mongo_enabled ? 'true' : 'false'"
                />
              </template>
              <el-switch v-model="form.mongo_enabled" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoUseSsh')"
                  :value="form.mongo_use_ssh ? 'true' : 'false'"
                />
              </template>
              <el-switch v-model="form.mongo_use_ssh" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoHost')"
                  :value="form.mongo_host"
                />
              </template>
              <el-input v-model="form.mongo_host" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoPort')"
                  :value="form.mongo_port"
                />
              </template>
              <el-input-number
                v-model="form.mongo_port"
                :min="1"
                :max="65535"
              />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoUsername')"
                  :value="form.mongo_username"
                />
              </template>
              <el-input v-model="form.mongo_username" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoPassword')"
                  :value="form.mongo_password"
                />
              </template>
              <el-input
                v-model="form.mongo_password"
                type="password"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoDatabase')"
                  :value="form.mongo_database"
                />
              </template>
              <el-input v-model="form.mongo_database" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoAuthDatabase')"
                  :value="form.mongo_auth_database"
                />
              </template>
              <el-input v-model="form.mongo_auth_database" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.mongoCollection')"
                  :value="form.mongo_collection"
                />
              </template>
              <el-input v-model="form.mongo_collection" />
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="form-section__title">
            {{ $t("opsTools.environment.sections.extra") }}
          </div>
          <div class="form-grid">
            <el-form-item class="span-2">
              <template #label>
                <CopyableFormLabel
                  :label="$t('opsTools.environment.form.extraConfig')"
                  :value="form.extra_config_text"
                />
              </template>
              <el-input
                v-model="form.extra_config_text"
                type="textarea"
                :rows="6"
              />
            </el-form-item>
          </div>
        </section>
      </el-form>

      <template #footer>
        <div class="drawer-footer">
          <el-button @click="drawerVisible = false">
            {{ $t("common.cancel") }}
          </el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ $t("common.save") }}
          </el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="importDialogVisible"
      :title="$t('opsTools.environment.importJson')"
      width="760px"
    >
      <el-input
        v-model="importText"
        type="textarea"
        :rows="16"
        :placeholder="$t('opsTools.environment.importPlaceholder')"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">
          {{ $t("common.cancel") }}
        </el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">
          {{ $t("common.confirm") }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="categoryDialogVisible"
      :title="$t('opsTools.environment.categoryDialogTitle')"
      width="1100px"
    >
      <div class="category-dialog__toolbar">
        <el-button type="primary" @click="openCategoryEditor()">
          {{ $t("opsTools.environment.createCategory") }}
        </el-button>
      </div>
      <el-table :data="categoryTableData" max-height="420">
        <el-table-column
          prop="name"
          :label="$t('opsTools.environment.categoryColumns.name')"
          min-width="160"
        />
        <el-table-column
          prop="code"
          :label="$t('opsTools.environment.categoryColumns.code')"
          min-width="120"
        />
        <el-table-column
          prop="directory_count"
          :label="$t('opsTools.environment.categoryColumns.directories')"
          width="120"
        />
        <el-table-column
          :label="$t('opsTools.environment.categoryColumns.status')"
          width="100"
        >
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" disabled />
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('opsTools.environment.columns.operation')"
          width="180"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button link type="primary" @click="openCategoryEditor(row)">
              {{ $t("opsTools.environment.actions.edit") }}
            </el-button>
            <el-button link type="danger" @click="handleDeleteCategory(row)">
              {{ $t("opsTools.environment.actions.delete") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-drawer
      v-model="categoryDrawerVisible"
      :title="
        categoryEditingId
          ? $t('opsTools.environment.editCategory')
          : $t('opsTools.environment.createCategory')
      "
      size="760px"
      destroy-on-close
      @closed="resetCategoryForm"
    >
      <el-form
        ref="categoryFormRef"
        :model="categoryForm"
        :rules="categoryRules"
        label-width="110px"
      >
        <div class="form-grid">
          <el-form-item prop="name">
            <template #label>
              <CopyableFormLabel
                :label="$t('opsTools.environment.categoryForm.name')"
                :value="categoryForm.name"
              />
            </template>
            <el-input v-model="categoryForm.name" />
          </el-form-item>
          <el-form-item prop="code">
            <template #label>
              <CopyableFormLabel
                :label="$t('opsTools.environment.categoryForm.code')"
                :value="categoryForm.code"
              />
            </template>
            <el-input v-model="categoryForm.code" />
          </el-form-item>
          <el-form-item>
            <template #label>
              <CopyableFormLabel
                :label="$t('opsTools.environment.categoryForm.sortOrder')"
                :value="categoryForm.sort_order"
              />
            </template>
            <el-input-number v-model="categoryForm.sort_order" :min="0" />
          </el-form-item>
          <el-form-item>
            <template #label>
              <CopyableFormLabel
                :label="$t('opsTools.environment.categoryForm.isActive')"
                :value="categoryForm.is_active ? 'true' : 'false'"
              />
            </template>
            <el-switch v-model="categoryForm.is_active" />
          </el-form-item>
          <el-form-item class="span-2">
            <template #label>
              <CopyableFormLabel
                :label="$t('opsTools.environment.categoryForm.description')"
                :value="categoryForm.description"
              />
            </template>
            <el-input
              v-model="categoryForm.description"
              type="textarea"
              :rows="3"
            />
          </el-form-item>
        </div>

        <div class="directory-editor">
          <div class="directory-editor__header">
            <span>{{ $t("opsTools.environment.categoryForm.directories") }}</span>
            <el-button size="small" @click="addCategoryDirectory">
              {{ $t("opsTools.environment.addDirectory") }}
            </el-button>
          </div>
          <div
            v-for="(item, index) in categoryForm.directories"
            :key="item.localKey"
            class="directory-row"
            :class="{ 'is-duplicate': duplicateDirectoryPathKeys.has(item.localKey) }"
          >
            <el-input
              v-model="item.name"
              :placeholder="$t('opsTools.environment.categoryForm.directoryName')"
            />
            <div
              class="directory-row__path"
              :class="{ 'is-duplicate': duplicateDirectoryPathKeys.has(item.localKey) }"
            >
              <el-input
                v-model="item.path"
                :placeholder="$t('opsTools.environment.categoryForm.directoryPath')"
                @blur="item.path = normalizeDirectoryPath(item.path)"
              />
            </div>
            <div class="directory-row__sort">
              <el-input-number v-model="item.sort_order" :min="0" />
            </div>
            <div class="directory-row__switch">
              <el-switch v-model="item.is_active" />
            </div>
            <div class="directory-row__actions">
              <el-button type="danger" link @click="removeCategoryDirectory(index)">
                {{ $t("common.delete") }}
              </el-button>
            </div>
            <div
              v-if="duplicateDirectoryPathKeys.has(item.localKey)"
              class="directory-row__error"
            >
              {{ $t("opsTools.environment.validation.directoryPathDuplicate") }}
            </div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="categoryDrawerVisible = false">
            {{ $t("common.cancel") }}
          </el-button>
          <el-button
            type="primary"
            :loading="categorySubmitting"
            @click="handleSaveCategory"
          >
            {{ $t("common.save") }}
          </el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="testDialogVisible"
      :title="$t('opsTools.environment.testResultTitle')"
      width="760px"
    >
      <div class="test-grid">
        <div
          v-for="(value, key) in testResults"
          :key="key"
          class="test-card"
          :class="{ 'is-fail': !value.success && !value.detail?.skipped }"
        >
          <div class="test-card__title">{{ middlewareLabel(key) }}</div>
          <div class="test-card__status">
            {{
              value.success
                ? $t("opsTools.environment.testSuccess")
                : value.detail?.skipped
                  ? $t("opsTools.environment.testSkipped")
                  : $t("opsTools.environment.testFailed")
            }}
          </div>
          <div class="test-card__message">{{ value.message }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import CopyableFormLabel from "@/views/ops-tools/components/CopyableFormLabel.vue";
import {
  createOpsCategory,
  createOpsEnvironment,
  deleteOpsCategory,
  deleteOpsEnvironment,
  getActiveOpsCategories,
  getOpsCategories,
  getOpsEnvironments,
  importOpsEnvironments,
  testOpsEnvironmentConnection,
  updateOpsCategory,
  updateOpsEnvironment,
} from "@/api/ops-tools";

const { t } = useI18n();

const loading = ref(false);
const submitting = ref(false);
const importing = ref(false);
const categorySubmitting = ref(false);
const drawerVisible = ref(false);
const importDialogVisible = ref(false);
const categoryDialogVisible = ref(false);
const categoryDrawerVisible = ref(false);
const testDialogVisible = ref(false);
const editingId = ref(null);
const categoryEditingId = ref(null);
const formRef = ref();
const categoryFormRef = ref();
const tableData = ref([]);
const categoryOptions = ref([]);
const categoryTableData = ref([]);
const testResults = ref({});
const importText = ref("");

const filters = reactive({
  keyword: "",
  category: "",
  environment_type: "",
  access_mode: "",
});

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0,
});

const form = reactive(createDefaultForm());
const categoryForm = reactive(createDefaultCategoryForm());

function createDefaultForm() {
  return {
    category: undefined,
    name: "",
    env_code: "",
    environment_type: "test",
    access_mode: "ssh",
    description: "",
    is_active: true,
    ssh_host: "",
    ssh_port: 22,
    ssh_username: "",
    ssh_password: "",
    client_url: "",
    admin_url: "",
    image_host: "",
    official_url: "",
    redis_enabled: false,
    redis_use_ssh: false,
    redis_host: "127.0.0.1",
    redis_port: 6379,
    redis_username: "",
    redis_password: "",
    redis_db: 0,
    mysql_enabled: false,
    mysql_use_ssh: false,
    mysql_host: "127.0.0.1",
    mysql_port: 3306,
    mysql_username: "",
    mysql_password: "",
    mysql_database: "",
    mongo_enabled: false,
    mongo_use_ssh: false,
    mongo_host: "127.0.0.1",
    mongo_port: 27017,
    mongo_username: "",
    mongo_password: "",
    mongo_database: "",
    mongo_auth_database: "admin",
    mongo_collection: "",
    extra_config_text: "{}",
  };
}

function createDefaultCategoryForm() {
  return {
    name: "",
    code: "",
    description: "",
    sort_order: 0,
    is_active: true,
    directories: [createDirectoryItem()],
  };
}

function createDirectoryItem(item = {}) {
  return {
    id: item.id,
    localKey: `${Date.now()}-${Math.random()}`,
    name: item.name || "",
    path: normalizeDirectoryPath(item.path),
    sort_order: item.sort_order || 0,
    is_active: item.is_active ?? true,
  };
}

function normalizeDirectoryPath(value) {
  return String(value || "").trim();
}

const environmentTypeOptions = computed(() => [
  { value: "dev", label: t("opsTools.environment.types.dev") },
  { value: "test", label: t("opsTools.environment.types.test") },
  { value: "staging", label: t("opsTools.environment.types.staging") },
  { value: "prod", label: t("opsTools.environment.types.prod") },
  { value: "other", label: t("opsTools.environment.types.other") },
]);

const accessModeOptions = computed(() => [
  { value: "ssh", label: t("opsTools.environment.accessModes.ssh") },
]);

const summary = computed(() => ({
  total: pagination.total,
  categories: categoryOptions.value.length,
  active: tableData.value.filter((item) => item.is_active).length,
}));

const selectedCategoryName = computed(
  () => categoryOptions.value.find((item) => item.id === form.category)?.name || "",
);

const duplicateDirectoryPathKeys = computed(() => {
  const pathKeyMap = new Map();
  const duplicateKeys = new Set();

  categoryForm.directories.forEach((item) => {
    const normalizedPath = normalizeDirectoryPath(item.path);
    if (!normalizedPath) {
      return;
    }
    const keys = pathKeyMap.get(normalizedPath) || [];
    keys.push(item.localKey);
    pathKeyMap.set(normalizedPath, keys);
  });

  pathKeyMap.forEach((keys) => {
    if (keys.length > 1) {
      keys.forEach((key) => duplicateKeys.add(key));
    }
  });

  return duplicateKeys;
});

const rules = computed(() => ({
  category: [
    {
      required: true,
      message: t("opsTools.environment.validation.category"),
      trigger: "change",
    },
  ],
  name: [
    {
      required: true,
      message: t("opsTools.environment.validation.name"),
      trigger: "blur",
    },
  ],
  env_code: [
    {
      required: true,
      message: t("opsTools.environment.validation.code"),
      trigger: "blur",
    },
    {
      pattern: /^[A-Za-z0-9_-]+$/,
      message: t("opsTools.environment.validation.codeFormat"),
      trigger: "blur",
    },
  ],
  environment_type: [
    {
      required: true,
      message: t("opsTools.environment.validation.type"),
      trigger: "change",
    },
  ],
  access_mode: [
    {
      required: true,
      message: t("opsTools.environment.validation.accessMode"),
      trigger: "change",
    },
  ],
  ssh_host: [
    {
      validator: (rule, value, callback) => {
        if (
          (form.access_mode === "ssh" ||
            form.mysql_use_ssh ||
            form.redis_use_ssh ||
            form.mongo_use_ssh) &&
          !value
        ) {
          callback(new Error(t("opsTools.environment.validation.sshHost")));
          return;
        }
        callback();
      },
      trigger: "blur",
    },
  ],
  ssh_username: [
    {
      validator: (rule, value, callback) => {
        if (
          (form.access_mode === "ssh" ||
            form.mysql_use_ssh ||
            form.redis_use_ssh ||
            form.mongo_use_ssh) &&
          !value
        ) {
          callback(
            new Error(t("opsTools.environment.validation.sshUsername")),
          );
          return;
        }
        callback();
      },
      trigger: "blur",
    },
  ],
}));

const categoryRules = computed(() => ({
  name: [
    {
      required: true,
      message: t("opsTools.environment.validation.categoryName"),
      trigger: "blur",
    },
  ],
  code: [
    {
      required: true,
      message: t("opsTools.environment.validation.categoryCode"),
      trigger: "blur",
    },
    {
      pattern: /^[A-Za-z0-9_-]+$/,
      message: t("opsTools.environment.validation.codeFormat"),
      trigger: "blur",
    },
  ],
}));

function middlewareLabel(key) {
  const map = {
    ssh: "SSH",
    mysql: "MySQL",
    redis: "Redis",
    mongo: "MongoDB",
  };
  return map[key] || key;
}

function getEnvironmentTypeLabel(value) {
  return (
    environmentTypeOptions.value.find((item) => item.value === value)?.label ||
    value
  );
}

function getAccessModeLabel(value) {
  return accessModeOptions.value.find((item) => item.value === value)?.label || value;
}

function typeTagType(value) {
  const map = {
    dev: "info",
    test: "success",
    staging: "warning",
    prod: "danger",
    other: "",
  };
  return map[value] || "";
}

function resetForm() {
  Object.assign(form, createDefaultForm());
  if (categoryOptions.value.length) {
    form.category = categoryOptions.value[0].id;
  }
  editingId.value = null;
  formRef.value?.clearValidate();
}

function resetCategoryForm() {
  Object.assign(categoryForm, createDefaultCategoryForm());
  categoryEditingId.value = null;
  categoryFormRef.value?.clearValidate();
}

function parseJsonField(text) {
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    throw new Error(t("opsTools.environment.validation.invalidJson"));
  }
}

function buildPayload() {
  return {
    category: form.category,
    name: form.name,
    env_code: form.env_code,
    environment_type: form.environment_type,
    access_mode: "ssh",
    description: form.description,
    ssh_host: form.ssh_host,
    ssh_port: form.ssh_port,
    ssh_username: form.ssh_username,
    ssh_password: form.ssh_password,
    client_url: form.client_url,
    admin_url: form.admin_url,
    image_host: form.image_host,
    official_url: form.official_url,
    mysql_config: {
      enabled: form.mysql_enabled,
      use_ssh: form.mysql_use_ssh,
      host: form.mysql_host,
      port: form.mysql_port,
      username: form.mysql_username,
      password: form.mysql_password,
      database: form.mysql_database,
    },
    redis_config: {
      enabled: form.redis_enabled,
      use_ssh: form.redis_use_ssh,
      host: form.redis_host,
      port: form.redis_port,
      username: form.redis_username,
      password: form.redis_password,
      db: form.redis_db,
    },
    mongo_config: {
      enabled: form.mongo_enabled,
      use_ssh: form.mongo_use_ssh,
      host: form.mongo_host,
      port: form.mongo_port,
      username: form.mongo_username,
      password: form.mongo_password,
      database: form.mongo_database,
      auth_database: form.mongo_auth_database,
      collection: form.mongo_collection,
    },
    extra_config: parseJsonField(form.extra_config_text),
    is_active: form.is_active,
  };
}

function fillForm(row) {
  const mysql = row.mysql_config || {};
  const redis = row.redis_config || {};
  const mongo = row.mongo_config || {};
  Object.assign(form, {
    ...createDefaultForm(),
    category: row.category,
    name: row.name,
    env_code: row.env_code,
    environment_type: row.environment_type,
    access_mode: "ssh",
    description: row.description,
    is_active: row.is_active,
    ssh_host: row.ssh_host,
    ssh_port: row.ssh_port,
    ssh_username: row.ssh_username,
    ssh_password: row.ssh_password,
    client_url: row.client_url,
    admin_url: row.admin_url,
    image_host: row.image_host,
    official_url: row.official_url,
    redis_enabled: !!redis.enabled,
    redis_use_ssh: !!redis.use_ssh,
    redis_host: redis.host || "127.0.0.1",
    redis_port: redis.port || 6379,
    redis_username: redis.username || "",
    redis_password: redis.password || "",
    redis_db: redis.db ?? 0,
    mysql_enabled: !!mysql.enabled,
    mysql_use_ssh: !!mysql.use_ssh,
    mysql_host: mysql.host || "127.0.0.1",
    mysql_port: mysql.port || 3306,
    mysql_username: mysql.username || "",
    mysql_password: mysql.password || "",
    mysql_database: mysql.database || "",
    mongo_enabled: !!mongo.enabled,
    mongo_use_ssh: !!mongo.use_ssh,
    mongo_host: mongo.host || "127.0.0.1",
    mongo_port: mongo.port || 27017,
    mongo_username: mongo.username || "",
    mongo_password: mongo.password || "",
    mongo_database: mongo.database || "",
    mongo_auth_database: mongo.auth_database || "admin",
    mongo_collection: mongo.collection || "",
    extra_config_text: JSON.stringify(row.extra_config || {}, null, 2),
  });
}

async function loadCategories() {
  const [activeResp, listResp] = await Promise.all([
    getActiveOpsCategories(),
    getOpsCategories({ page_size: 200 }),
  ]);
  categoryOptions.value = activeResp.data || [];
  categoryTableData.value = listResp.data.results || listResp.data || [];
}

async function loadData() {
  loading.value = true;
  try {
    const response = await getOpsEnvironments({
      page: pagination.page,
      page_size: pagination.page_size,
      keyword: filters.keyword || undefined,
      category: filters.category || undefined,
      environment_type: filters.environment_type || undefined,
      access_mode: "ssh",
    });
    tableData.value = response.data.results || response.data;
    pagination.total = response.data.count ?? tableData.value.length;
  } catch {
    ElMessage.error(t("opsTools.messages.loadEnvironmentFailed"));
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.page = 1;
  loadData();
}

function handleReset() {
  filters.keyword = "";
  filters.category = "";
  filters.environment_type = "";
  handleSearch();
}

function handleSizeChange() {
  pagination.page = 1;
  loadData();
}

function openCreateDrawer() {
  resetForm();
  drawerVisible.value = true;
}

function openEditDrawer(row) {
  resetForm();
  editingId.value = row.id;
  fillForm(row);
  drawerVisible.value = true;
}

function openImportDialog() {
  importText.value = "";
  importDialogVisible.value = true;
}

function openCategoryDialog() {
  categoryDialogVisible.value = true;
}

function openCategoryEditor(row = null) {
  resetCategoryForm();
  if (row) {
    categoryEditingId.value = row.id;
    Object.assign(categoryForm, {
      name: row.name,
      code: row.code,
      description: row.description,
      sort_order: row.sort_order,
      is_active: row.is_active,
      directories: (row.directories || []).map((item) => createDirectoryItem(item)),
    });
  }
  categoryDrawerVisible.value = true;
}

function addCategoryDirectory() {
  categoryForm.directories.push(createDirectoryItem());
}

function removeCategoryDirectory(index) {
  if (categoryForm.directories.length === 1) {
    ElMessage.warning(t("opsTools.environment.validation.categoryDirectory"));
    return;
  }
  categoryForm.directories.splice(index, 1);
}

function normalizeCategoryDirectories() {
  categoryForm.directories.forEach((item) => {
    item.name = String(item.name || "").trim();
    item.path = normalizeDirectoryPath(item.path);
  });
}

function extractErrorMessage(error, fallback) {
  const detail = error?.response?.data;
  if (typeof detail === "string" && detail) {
    return detail;
  }
  if (typeof detail?.detail === "string" && detail.detail) {
    return detail.detail;
  }
  if (Array.isArray(detail?.directories) && detail.directories.length) {
    return detail.directories[0];
  }
  return error?.message || fallback;
}

async function handleSaveCategory() {
  try {
    normalizeCategoryDirectories();
    await categoryFormRef.value.validate();
    if (categoryForm.directories.some((item) => !item.name || !item.path)) {
      ElMessage.warning(t("opsTools.environment.validation.categoryDirectory"));
      return;
    }
    if (duplicateDirectoryPathKeys.value.size) {
      ElMessage.warning(
        t("opsTools.environment.validation.directoryPathDuplicate"),
      );
      return;
    }
    categorySubmitting.value = true;
    const payload = {
      name: categoryForm.name,
      code: categoryForm.code,
      description: categoryForm.description,
      sort_order: categoryForm.sort_order,
      is_active: categoryForm.is_active,
      directories: categoryForm.directories.map((item) => ({
        id: item.id,
        name: item.name,
        path: item.path,
        sort_order: item.sort_order,
        is_active: item.is_active,
      })),
    };
    if (categoryEditingId.value) {
      await updateOpsCategory(categoryEditingId.value, payload);
    } else {
      await createOpsCategory(payload);
    }
    ElMessage.success(t("opsTools.messages.categorySaveSuccess"));
    categoryDrawerVisible.value = false;
    await loadCategories();
    await loadData();
    if (!form.category && categoryOptions.value.length) {
      form.category = categoryOptions.value[0].id;
    }
  } catch (error) {
    ElMessage.error(
      extractErrorMessage(error, t("opsTools.messages.categorySaveFailed")),
    );
  } finally {
    categorySubmitting.value = false;
  }
}

async function handleDeleteCategory(row) {
  try {
    await ElMessageBox.confirm(
      t("opsTools.messages.deleteCategoryConfirm", { name: row.name }),
      t("common.tip"),
      { type: "warning" },
    );
    await deleteOpsCategory(row.id);
    ElMessage.success(t("opsTools.messages.deleteSuccess"));
    await loadCategories();
    await loadData();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error(t("opsTools.messages.deleteFailed"));
    }
  }
}

async function handleSubmit() {
  try {
    await formRef.value.validate();
    const payload = buildPayload();
    submitting.value = true;
    if (editingId.value) {
      await updateOpsEnvironment(editingId.value, payload);
    } else {
      await createOpsEnvironment(payload);
    }
    ElMessage.success(t("opsTools.messages.saveSuccess"));
    drawerVisible.value = false;
    await loadData();
  } catch (error) {
    ElMessage.error(error?.message || t("opsTools.messages.saveFailed"));
  } finally {
    submitting.value = false;
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      t("opsTools.messages.deleteEnvironmentConfirm", { name: row.name }),
      t("common.tip"),
      { type: "warning" },
    );
    await deleteOpsEnvironment(row.id);
    ElMessage.success(t("opsTools.messages.deleteSuccess"));
    if (tableData.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1;
    }
    await loadData();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error(t("opsTools.messages.deleteFailed"));
    }
  }
}

async function handleImport() {
  let payload;
  try {
    payload = JSON.parse(importText.value);
  } catch {
    ElMessage.error(t("opsTools.messages.importInvalid"));
    return;
  }
  importing.value = true;
  try {
    const response = await importOpsEnvironments(
      Array.isArray(payload) ? payload : payload.items || [],
    );
    const { created, updated, errors } = response.data;
    if (errors?.length) {
      ElMessage.warning(
        t("opsTools.messages.importPartial", {
          created,
          updated,
          errors: errors.length,
        }),
      );
    } else {
      ElMessage.success(
        t("opsTools.messages.importSuccess", { created, updated }),
      );
    }
    importDialogVisible.value = false;
    await loadData();
  } catch {
    ElMessage.error(t("opsTools.messages.importFailed"));
  } finally {
    importing.value = false;
  }
}

async function handleTestConnection(row) {
  try {
    const response = await testOpsEnvironmentConnection(row.id);
    testResults.value = response.data.results || {};
    testDialogVisible.value = true;
  } catch {
    ElMessage.error(t("opsTools.messages.testConnectionFailed"));
  }
}

onMounted(async () => {
  await loadCategories();
  resetForm();
  await loadData();
});
</script>

<style scoped lang="scss">
.ops-environment-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  .page-header-title {  
    display: flex;
    flex-direction: row;
    gap: 16px;
  }

  h2 {
    margin: 0;
    font-size: 24px;
  }

  p {
    margin: 8px 0 0;
    color: var(--th-color-text-secondary);
  }
}

.page-header__actions,
.drawer-footer,
.category-dialog__toolbar {
  display: flex;
  gap: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 18px 20px;
  border-radius: 18px;
  background: linear-gradient(
    135deg,
    rgba(14, 165, 233, 0.08),
    rgba(59, 130, 246, 0.02)
  );
  border: 1px solid var(--th-border-color-light);

  span {
    display: block;
    color: var(--th-color-text-secondary);
    margin-bottom: 10px;
  }

  strong {
    font-size: 30px;
    line-height: 1;
  }
}

.middleware-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--th-border-color-light);
}

.form-section__title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 18px;
}

.span-2 {
  grid-column: 1 / span 2;
}

:deep(.form-grid .el-form-item) {
  margin-bottom: 14px;
}

.directory-editor {
  margin-top: 8px;
}

.directory-editor__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-weight: 600;
}

.directory-row {
  display: grid;
  grid-template-columns: minmax(160px, 220px) minmax(0, 1fr) 132px 92px 72px;
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
}

.directory-row__path {
  min-width: 0;
}

.directory-row__sort,
.directory-row__switch,
.directory-row__actions {
  display: flex;
  align-items: center;
}

.directory-row__switch {
  justify-content: center;
}

.directory-row__actions {
  justify-content: flex-end;
}

:deep(.directory-row__path.is-duplicate .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--el-color-danger) inset;
}

.directory-row__error {
  grid-column: 1 / -1;
  margin-top: -6px;
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.4;
}

:deep(.directory-row__sort .el-input-number) {
  width: 100%;
}

.test-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.test-card {
  padding: 16px;
  border: 1px solid rgba(34, 197, 94, 0.2);
  background: rgba(34, 197, 94, 0.06);
  border-radius: 14px;

  &.is-fail {
    border-color: rgba(239, 68, 68, 0.24);
    background: rgba(239, 68, 68, 0.06);
  }
}

.test-card__title {
  font-size: 16px;
  font-weight: 600;
}

.test-card__status {
  margin-top: 8px;
  font-weight: 600;
}

.test-card__message {
  margin-top: 6px;
  color: var(--th-color-text-secondary);
}

@media (max-width: 1200px) {
  .summary-grid,
  .test-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
  }

  .form-grid,
  .summary-grid,
  .test-grid {
    grid-template-columns: 1fr;
  }

  .span-2 {
    grid-column: auto;
  }

  .directory-row {
    grid-template-columns: 1fr;
  }
}
</style>
