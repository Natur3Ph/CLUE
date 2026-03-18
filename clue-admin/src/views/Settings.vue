<template>
  <div class="settings-page">
    <!-- 顶部说明区 -->
    <div class="page-banner">
      <div>
        <div class="page-title">系统设置</div>
        <div class="page-desc">
          用于管理审核运行模式、模型接口配置与关键词触发规则，提升系统灵活性与可维护性。
        </div>
      </div>

      <div class="page-actions">
        <el-button @click="loadSettings" :loading="loading">刷新数据</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存设置</el-button>
      </div>
    </div>

    <!-- 顶部概览 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-provider" shadow="hover">
          <div class="stat-label">当前运行模式</div>
          <div class="stat-value text-sm">{{ providerLabel }}</div>
          <div class="stat-sub">由 clue_provider 控制</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-api" shadow="hover">
          <div class="stat-label">API Key 状态</div>
          <div class="stat-value text-sm">
            {{ form.api_key_configured ? '已配置' : '未配置' }}
          </div>
          <div class="stat-sub">由后端运行时返回</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-model" shadow="hover">
          <div class="stat-label">审核模型</div>
          <div class="stat-value text-sm model-text">
            {{ form.openai_model || '-' }}
          </div>
          <div class="stat-sub">当前视觉审核模型名称</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-keyword" shadow="hover">
          <div class="stat-label">关键词类别数</div>
          <div class="stat-value">{{ keywordCount }}</div>
          <div class="stat-sub">当前关键词触发分类数量</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行设置 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :lg="12">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="card-title">运行模式设置</div>
          </template>

          <el-form label-width="120px">
            <el-form-item label="审核模式">
              <el-radio-group v-model="form.clue_provider">
                <el-radio-button label="mock">Mock</el-radio-button>
                <el-radio-button label="openai">OpenAI兼容</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="Mock命中率">
              <el-slider
                v-model="form.mock_hit_rate"
                :min="0"
                :max="1"
                :step="0.01"
                show-input
              />
            </el-form-item>

            <el-form-item label="随机命中率">
              <el-slider
                v-model="form.mock_random_hit_rate"
                :min="0"
                :max="1"
                :step="0.01"
                show-input
              />
            </el-form-item>

            <div class="form-tip">
              说明：Mock 模式下可通过命中率参数模拟审核结果，适合演示与开发调试。
            </div>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="card-title">运行时状态</div>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="运行模式">
              {{ form.runtime_provider || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="运行 Base URL">
              {{ form.runtime_openai_base_url || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="运行审核模型">
              {{ form.runtime_openai_model || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="运行客观化模型">
              {{ form.runtime_openai_objectify_model || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="API Key">
              <el-tag :type="form.api_key_configured ? 'success' : 'danger'">
                {{ form.api_key_configured ? '已配置' : '未配置' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <div class="form-tip mt16">
            说明：以上信息由后端 `/api/settings` 返回，用于展示当前运行时实际生效参数。 
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 模型接口配置 -->
    <el-card class="panel-card section-row" shadow="never">
  <template #header>
    <div class="config-header">
      <div class="card-title">模型接口配置</div>
      <el-button
        type="primary"
        plain
        :loading="testing"
        @click="handleTestConnection"
      >
        测试连接
      </el-button>
    </div>
  </template>

      <el-form label-width="140px">
        <el-form-item label="OpenAI Base URL">
          <el-input
            v-model="form.openai_base_url"
            placeholder="例如：https://api.openai.com/v1"
          />
        </el-form-item>

        <el-form-item label="审核模型名称">
          <el-input
            v-model="form.openai_model"
            placeholder="例如：gpt-4o-mini"
          />
        </el-form-item>

        <el-form-item label="客观化模型名称">
          <el-input
            v-model="form.openai_objectify_model"
            placeholder="例如：gpt-4o-mini"
          />
        </el-form-item>

        <div class="form-tip">
          说明：当审核模式切换为 OpenAI 兼容接口时，系统会使用这些参数作为运行配置。
        </div>
          <div v-if="testResult" class="test-result-box mt16">
        <div class="test-result-title">连接测试结果</div>

          <div v-if="testResult.connected" class="test-result success">
            <div>状态：连接成功</div>
            <div>模型：{{ testResult.model }}</div>
            <div>地址：{{ testResult.base_url }}</div>
            <div>响应耗时：{{ testResult.response_time_ms }} ms</div>
            <div v-if="testResult.reply_preview">返回内容：{{ testResult.reply_preview }}</div>
        </div>

  <div v-else class="test-result fail">
    <div>状态：连接失败</div>
    <div>原因：{{ testResult.message || '未知错误' }}</div>
  </div>
</div>
      </el-form>
    </el-card>

    <!-- 关键词触发配置 -->
    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="keyword-header">
          <div>
            <div class="card-title">关键词触发配置</div>
            <div class="card-subtitle">用于管理不同类别的触发关键词，保存时会统一提交为 keyword_triggers 对象</div>
          </div>

          <el-button @click="addKeywordRow">新增分类</el-button>
        </div>
      </template>

      <div v-if="keywordRows.length" class="keyword-list">
        <div
          v-for="(item, index) in keywordRows"
          :key="index"
          class="keyword-item"
        >
          <div class="keyword-grid">
            <div class="keyword-col">
              <div class="input-label">分类名称</div>
              <el-input
                v-model="item.key"
                placeholder="例如：暴力血腥"
              />
            </div>

            <div class="keyword-col keyword-col-wide">
              <div class="input-label">关键词列表</div>
              <el-input
                v-model="item.value"
                type="textarea"
                :rows="3"
                placeholder="多个关键词可用中文逗号、英文逗号或换行分隔"
              />
            </div>

            <div class="keyword-action">
              <el-button type="danger" plain @click="removeKeywordRow(index)">
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <el-empty v-else description="暂无关键词分类，请新增后保存" />

      <div class="form-tip mt16">
        说明：后端默认支持 `生殖器 / 暴力血腥 / 涉政 / 违禁品` 等关键词分类，前端在此页面可继续扩展与修改。
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchSettings, saveSettings, testSettingsConnection } from '../api/settings'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

const form = ref({
  clue_provider: 'mock',
  mock_hit_rate: 0.75,
  mock_random_hit_rate: 0.2,
  openai_base_url: 'https://api.openai.com/v1',
  openai_model: 'gpt-4o-mini',
  openai_objectify_model: 'gpt-4o-mini',

  runtime_provider: '',
  runtime_openai_base_url: '',
  runtime_openai_model: '',
  runtime_openai_objectify_model: '',
  api_key_configured: false,
})

const keywordRows = ref([])

const providerLabel = computed(() => {
  if (form.value.clue_provider === 'openai') return 'OpenAI兼容'
  return 'Mock'
})

const keywordCount = computed(() => keywordRows.value.length)

function unwrap(res) {
  if (!res) return null
  if (res.status && res.data !== undefined) return res.data
  if (res.data && res.data.data !== undefined) return res.data.data
  if (res.data !== undefined) return res.data
  return res
}

function objectToRows(obj) {
  const source = obj && typeof obj === 'object' ? obj : {}
  return Object.keys(source).map((key) => ({
    key,
    value: Array.isArray(source[key]) ? source[key].join('，') : '',
  }))
}

function rowsToObject(rows) {
  const out = {}
  for (const row of rows) {
    const key = String(row.key || '').trim()
    if (!key) continue

    const text = String(row.value || '').trim()
    const values = text
      .split(/[\n,，;；]/)
      .map((s) => s.trim())
      .filter(Boolean)

    out[key] = values
  }
  return out
}

function addKeywordRow() {
  keywordRows.value.push({
    key: '',
    value: '',
  })
}

function removeKeywordRow(index) {
  keywordRows.value.splice(index, 1)
}

async function loadSettings() {
  loading.value = true
  try {
    const res = await fetchSettings()
    const data = unwrap(res) || {}

    form.value = {
      clue_provider: data.clue_provider ?? 'mock',
      mock_hit_rate: Number(data.mock_hit_rate ?? 0.75),
      mock_random_hit_rate: Number(data.mock_random_hit_rate ?? 0.2),
      openai_base_url: data.openai_base_url ?? 'https://api.openai.com/v1',
      openai_model: data.openai_model ?? 'gpt-4o-mini',
      openai_objectify_model: data.openai_objectify_model ?? 'gpt-4o-mini',

      runtime_provider: data.runtime_provider ?? '',
      runtime_openai_base_url: data.runtime_openai_base_url ?? '',
      runtime_openai_model: data.runtime_openai_model ?? '',
      runtime_openai_objectify_model: data.runtime_openai_objectify_model ?? '',
      api_key_configured: !!data.api_key_configured,
    }

    keywordRows.value = objectToRows(data.keyword_triggers || {})
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '获取系统设置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const payload = {
      clue_provider: form.value.clue_provider,
      mock_hit_rate: Number(form.value.mock_hit_rate),
      mock_random_hit_rate: Number(form.value.mock_random_hit_rate),
      openai_base_url: String(form.value.openai_base_url || '').trim(),
      openai_model: String(form.value.openai_model || '').trim(),
      openai_objectify_model: String(form.value.openai_objectify_model || '').trim(),
      keyword_triggers: rowsToObject(keywordRows.value),
    }

    await saveSettings(payload)
    ElMessage.success('系统设置保存成功')
    await loadSettings()
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '保存设置失败')
  } finally {
    saving.value = false
  }
}

async function handleTestConnection() {
  testing.value = true
  testResult.value = null

  try {
    const res = await testSettingsConnection({
      openai_base_url: String(form.value.openai_base_url || '').trim(),
      openai_model: String(form.value.openai_model || '').trim(),
    })

    const data = unwrap(res) || {}
    testResult.value = data
    ElMessage.success(`连接成功，耗时 ${data.response_time_ms || 0} ms`)
  } catch (err) {
    console.error(err)
    testResult.value = {
      connected: false,
      message: err?.response?.data?.detail || '连接失败',
    }
    ElMessage.error(err?.response?.data?.detail || '测试连接失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100%;
  box-sizing: border-box;
}

.page-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 22px 24px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.page-desc {
  margin-top: 8px;
  font-size: 14px;
  color: #606266;
}

.page-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.section-row {
  margin-bottom: 16px;
}

.stat-card,
.panel-card {
  border: none;
  border-radius: 14px;
}

.stat-card :deep(.el-card__body) {
  padding: 22px 22px 18px;
}

.stat-label {
  font-size: 14px;
  color: #606266;
}

.stat-value {
  margin-top: 12px;
  font-size: 34px;
  font-weight: 700;
  color: #303133;
  line-height: 1.1;
}

.stat-value.text-sm {
  font-size: 22px;
}

.model-text {
  word-break: break-all;
}

.stat-sub {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
}

.stat-provider {
  border-left: 4px solid #409eff;
}

.stat-api {
  border-left: 4px solid #67c23a;
}

.stat-model {
  border-left: 4px solid #e6a23c;
}

.stat-keyword {
  border-left: 4px solid #9c6bff;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.card-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}

.keyword-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.keyword-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.keyword-item {
  padding: 16px;
  border-radius: 12px;
  background: #fafbfd;
  border: 1px solid #eef1f6;
}

.keyword-grid {
  display: grid;
  grid-template-columns: 220px 1fr 90px;
  gap: 14px;
  align-items: start;
}

.keyword-col {
  min-width: 0;
}

.keyword-col-wide {
  min-width: 0;
}

.keyword-action {
  display: flex;
  align-items: end;
  justify-content: flex-end;
  height: 100%;
}

.input-label {
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.form-tip {
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fafc;
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}

.mt16 {
  margin-top: 16px;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.test-result-box {
  padding: 16px;
  border-radius: 12px;
  background: #fafbfd;
  border: 1px solid #eef1f6;
}

.test-result-title {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 700;
  color: #303133;
}

.test-result {
  font-size: 13px;
  line-height: 1.9;
}

.test-result.success {
  color: #67c23a;
}

.test-result.fail {
  color: #f56c6c;
}

@media (max-width: 992px) {
  .page-banner,
  .keyword-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .keyword-grid {
    grid-template-columns: 1fr;
  }

  .keyword-action {
    justify-content: flex-start;
  }
}
</style>