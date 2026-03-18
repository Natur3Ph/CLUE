<template>
  <div class="rule-page">
    <!-- 顶部说明区 -->
    <div class="page-banner">
      <div>
        <div class="page-title">规则管理</div>
        <div class="page-desc">
          统一维护图像审核规则，支持规则创建、编辑、启停、删除与一键客观化。
        </div>
      </div>

      <div class="page-actions">
        <el-button @click="loadRules" :loading="loading">刷新数据</el-button>
        <el-button type="primary" @click="openCreateDialog">新建规则</el-button>
      </div>
    </div>

    <!-- 顶部统计 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-total" shadow="hover">
          <div class="stat-label">规则总数</div>
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-sub">系统当前已配置规则数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-active" shadow="hover">
          <div class="stat-label">启用规则</div>
          <div class="stat-value">{{ stats.active }}</div>
          <div class="stat-sub">参与审核流程的规则数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-object" shadow="hover">
          <div class="stat-label">已客观化</div>
          <div class="stat-value">{{ stats.objectified }}</div>
          <div class="stat-sub">已生成客观化结果的规则数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-score" shadow="hover">
          <div class="stat-label">平均客观化评分</div>
          <div class="stat-value">{{ stats.avgScore }}</div>
          <div class="stat-sub">基于当前已加载规则计算</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 表格 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <div>
            <div class="card-title">规则列表</div>
            <div class="card-subtitle">支持查看原始规则、客观化结果、预条件链与规则版本</div>
          </div>
          <div class="table-summary">当前显示 {{ rules.length }} 条规则</div>
        </div>
      </template>

      <el-table
        :data="rules"
        v-loading="loading"
        border
        class="rule-table"
        style="width: 100%"
      >
        <el-table-column prop="rule_name" label="规则名称" min-width="220" />

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="light">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="客观化评分" width="120">
          <template #default="{ row }">
            <span>{{ formatScore(row.objectiveness_score) }}</span>
          </template>
        </el-table-column>


        <el-table-column label="原始规则" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.original_rule || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="客观化规则" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.objectified_rule || '未客观化' }}
          </template>
        </el-table-column>

        <el-table-column label="预条件数" width="100">
          <template #default="{ row }">
            {{ Array.isArray(row.preconditions) ? row.preconditions.length : 0 }}
          </template>
        </el-table-column>

        <el-table-column label="更新时间" min-width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at || row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetailDialog(row)">
              查看
            </el-button>
            <el-button link type="primary" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button
              link
              type="warning"
              :loading="objectifyLoadingId === row.id"
              @click="handleObjectify(row)"
            >
              客观化
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!loading && rules.length === 0"
        description="暂无规则数据"
        class="empty-block"
      />
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑规则' : '新建规则'"
      width="760px"
      destroy-on-close
    >
      <el-form :model="form" label-width="92px">
        <el-form-item label="规则名称">
          <el-input v-model="form.rule_name" placeholder="请输入规则名称" />
        </el-form-item>

        <el-form-item label="原始规则">
          <el-input
            v-model="form.original_rule"
            type="textarea"
            :rows="4"
            placeholder="请输入原始规则描述"
          />
        </el-form-item>

        <el-form-item label="预条件链">
          <el-input
            v-model="preconditionsText"
            type="textarea"
            :rows="5"
            placeholder="一行一个预条件，例如：&#10;画面中出现明显血液&#10;画面中出现开放性伤口"
          />
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '创建规则' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="规则详情"
      width="860px"
      destroy-on-close
    >
      <div v-if="currentRule" class="detail-wrap">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="规则ID">
            {{ currentRule.id }}
          </el-descriptions-item>
          <el-descriptions-item label="规则版本">
            v{{ currentRule.version || 1 }}
          </el-descriptions-item>
          <el-descriptions-item label="规则名称">
            {{ currentRule.rule_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="启用状态">
            <el-tag :type="currentRule.is_active ? 'success' : 'info'">
              {{ currentRule.is_active ? '启用' : '停用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="客观化评分">
            {{ formatScore(currentRule.objectiveness_score) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDateTime(currentRule.updated_at || currentRule.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="原始规则" :span="2">
            {{ currentRule.original_rule || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="客观化规则" :span="2">
            {{ currentRule.objectified_rule || '未客观化' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-block">
          <div class="detail-title">预条件链</div>
          <div v-if="currentRule.preconditions?.length" class="pre-list">
            <div
              v-for="(item, index) in currentRule.preconditions"
              :key="index"
              class="pre-item"
            >
              <span class="pre-index">{{ index + 1 }}</span>
              <span class="pre-text">{{ item }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无预条件链" />
        </div>

        <div class="detail-grid">
          <div class="detail-block">
            <div class="detail-title">主观词片段</div>
            <div class="tag-list">
              <el-tag
                v-for="(item, index) in currentRule.subjective_spans || []"
                :key="index"
                class="mr8 mb8"
              >
                {{ item }}
              </el-tag>
              <span v-if="!(currentRule.subjective_spans || []).length" class="empty-inline">
                暂无
              </span>
            </div>
          </div>

          <div class="detail-block">
            <div class="detail-title">可观察信号</div>
            <div class="tag-list">
              <el-tag
                v-for="(item, index) in currentRule.observable_signals || []"
                :key="index"
                type="success"
                class="mr8 mb8"
              >
                {{ item }}
              </el-tag>
              <span v-if="!(currentRule.observable_signals || []).length" class="empty-inline">
                暂无
              </span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchRules,
  createRule,
  updateRule,
  deleteRule,
  objectifyRule,
} from '../api/rule'

const loading = ref(false)
const submitLoading = ref(false)
const objectifyLoadingId = ref(null)

const rules = ref([])

const formDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const isEdit = ref(false)

const currentRule = ref(null)

const form = ref({
  id: null,
  rule_name: '',
  original_rule: '',
  is_active: true,
})

const preconditionsText = ref('')

const stats = computed(() => {
  const list = rules.value || []
  const total = list.length
  const active = list.filter((r) => !!r.is_active).length
  const objectified = list.filter((r) => !!r.objectified_rule).length

  const scored = list
    .map((r) => Number(r.objectiveness_score || 0))
    .filter((n) => !Number.isNaN(n))

  const avgScore = scored.length
    ? (scored.reduce((a, b) => a + b, 0) / scored.length).toFixed(2)
    : '0.00'

  return {
    total,
    active,
    objectified,
    avgScore,
  }
})

function unwrap(res) {
  if (!res) return null
  if (res.status && res.data !== undefined) return res.data
  if (res.data && res.data.data !== undefined) return res.data.data
  if (res.data !== undefined) return res.data
  return res
}

function normalizeRule(item) {
  return {
    ...item,
    preconditions: Array.isArray(item.preconditions) ? item.preconditions : [],
    subjective_spans: Array.isArray(item.subjective_spans) ? item.subjective_spans : [],
    observable_signals: Array.isArray(item.observable_signals) ? item.observable_signals : [],
  }
}

function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

function formatScore(value) {
  const num = Number(value || 0)
  return num.toFixed(2)
}

async function loadRules() {
  loading.value = true
  try {
    const res = await fetchRules(true)
    const data = unwrap(res) || []
    rules.value = data.map(normalizeRule)
  } catch (err) {
    console.error(err)
    ElMessage.error('获取规则失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = {
    id: null,
    rule_name: '',
    original_rule: '',
    is_active: true,
  }
  preconditionsText.value = ''
}

function openCreateDialog() {
  isEdit.value = false
  resetForm()
  formDialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  form.value = {
    id: row.id,
    rule_name: row.rule_name || '',
    original_rule: row.original_rule || '',
    is_active: !!row.is_active,
  }
  preconditionsText.value = (row.preconditions || []).join('\n')
  formDialogVisible.value = true
}

function openDetailDialog(row) {
  currentRule.value = normalizeRule(row)
  detailDialogVisible.value = true
}

function parsePreconditions(text) {
  return String(text || '')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
}

async function handleSubmit() {
  if (!String(form.value.original_rule || '').trim()) {
    ElMessage.warning('原始规则不能为空')
    return
  }

  const payload = {
    rule_name: String(form.value.rule_name || '').trim(),
    original_rule: String(form.value.original_rule || '').trim(),
    preconditions: parsePreconditions(preconditionsText.value),
    is_active: !!form.value.is_active,
  }

  submitLoading.value = true
  try {
    if (isEdit.value && form.value.id) {
      await updateRule(form.value.id, payload)
      ElMessage.success('规则更新成功')
    } else {
      await createRule(payload)
      ElMessage.success('规则创建成功')
    }

    formDialogVisible.value = false
    await loadRules()
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除规则【${row.rule_name || row.original_rule}】吗？`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return
  }

  try {
    await deleteRule(row.id)
    ElMessage.success('删除成功')
    await loadRules()
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '删除失败')
  }
}

async function handleObjectify(row) {
  objectifyLoadingId.value = row.id
  try {
    await objectifyRule(row.id)
    ElMessage.success('规则客观化完成')
    await loadRules()
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '客观化失败')
  } finally {
    objectifyLoadingId.value = null
  }
}

onMounted(() => {
  loadRules()
})
</script>

<style scoped>
.rule-page {
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

.stat-card {
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
  line-height: 1;
}

.stat-sub {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
}

.stat-total {
  border-left: 4px solid #409eff;
}

.stat-active {
  border-left: 4px solid #67c23a;
}

.stat-object {
  border-left: 4px solid #e6a23c;
}

.stat-score {
  border-left: 4px solid #9c6bff;
}

.table-card {
  border: none;
  border-radius: 14px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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

.table-summary {
  font-size: 13px;
  color: #909399;
}

.rule-table :deep(th.el-table__cell) {
  background: #f8fafc;
  color: #606266;
  font-weight: 600;
}

.empty-block {
  margin-top: 20px;
}

.detail-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-block {
  padding: 16px;
  border-radius: 12px;
  background: #fafbfd;
  border: 1px solid #eef1f6;
}

.detail-title {
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 700;
  color: #303133;
}

.pre-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pre-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.pre-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.pre-text {
  line-height: 1.8;
  color: #606266;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.mr8 {
  margin-right: 8px;
}

.mb8 {
  margin-bottom: 8px;
}

.empty-inline {
  font-size: 13px;
  color: #909399;
}

@media (max-width: 992px) {
  .page-banner,
  .table-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>