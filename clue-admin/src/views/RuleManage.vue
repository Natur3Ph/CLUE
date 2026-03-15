<template>
  <el-card>
    <template #header>
      <div class="toolbar">
        <div class="left-tools">
          <span class="title">规则管理</span>

          <div class="switch-wrap">
            <span>仅启用</span>
            <el-switch v-model="onlyActive" @change="loadRules" />
            <el-link type="primary" @click="toggleShowAll">
              {{ onlyActive ? '显示全部' : '仅看启用' }}
            </el-link>
          </div>
        </div>

        <div class="right-tools">
          <el-input
            v-model="keyword"
            placeholder="搜索：规则名称 / 原始规则"
            clearable
            class="search-input"
          />
          <el-button type="primary" @click="openCreate">新增规则</el-button>
          <el-button @click="loadRules">刷新</el-button>
        </div>
      </div>
    </template>

    <el-table
      :data="filteredRules"
      v-loading="loading"
      border
      stripe
      style="width: 100%"
      row-key="id"
    >
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="rule_name" label="规则名称" width="160" />

      <el-table-column label="原始规则" min-width="240">
        <template #default="{ row }">
          <div class="text-block">{{ row.original_rule }}</div>
        </template>
      </el-table-column>

      <el-table-column label="客观化规则" min-width="260">
        <template #default="{ row }">
          <div v-if="row.objectified_rule" class="text-block objectified">
            {{ row.objectified_rule }}
          </div>
          <el-tag v-else type="info">尚未客观化</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="主观词" min-width="180">
        <template #default="{ row }">
          <div
            v-if="row.subjective_spans && row.subjective_spans.length > 0"
            class="tag-wrap"
          >
            <el-tag
              v-for="(item, idx) in row.subjective_spans"
              :key="idx"
              size="small"
              type="warning"
            >
              {{ item }}
            </el-tag>
          </div>
          <el-tag v-else type="success" size="small">无主观词</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="可观察信号" min-width="180">
        <template #default="{ row }">
          <div
            v-if="row.observable_signals && row.observable_signals.length > 0"
            class="tag-wrap"
          >
            <el-tag
              v-for="(item, idx) in row.observable_signals"
              :key="idx"
              size="small"
              type="info"
            >
              {{ item }}
            </el-tag>
          </div>
          <span v-else class="muted">暂无</span>
        </template>
      </el-table-column>

      <el-table-column label="预条件链" min-width="260">
        <template #default="{ row }">
          <div v-if="row.preconditions && row.preconditions.length > 0" class="tag-wrap">
            <el-tag
              v-for="(item, idx) in row.preconditions"
              :key="idx"
              size="small"
              effect="plain"
            >
              {{ item }}
            </el-tag>
          </div>
          <el-tag v-else type="info" size="small">暂无预条件</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="启用" width="90" align="center">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_active"
            @change="(val) => handleToggleActive(row, val)"
          />
        </template>
      </el-table-column>

      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <div class="action-wrap">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              size="small"
              type="success"
              :loading="objectifyingId === row.id"
              @click="handleObjectify(row)"
            >
              一键客观化
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="footer-tip">
      当前显示 {{ filteredRules.length }} 条（共 {{ rules.length }} 条）
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑规则' : '新增规则'"
      width="720px"
      destroy-on-close
    >
      <el-form label-width="100px">
        <el-form-item label="规则名称">
          <el-input v-model="form.rule_name" placeholder="请输入规则名称" />
        </el-form-item>

        <el-form-item label="原始规则">
          <el-input
            v-model="form.original_rule"
            type="textarea"
            :rows="4"
            placeholder="请输入原始规则"
          />
        </el-form-item>

        <el-form-item label="预条件链">
          <el-input
            v-model="preconditionsText"
            type="textarea"
            :rows="5"
            placeholder='请输入 JSON 数组，如 ["画面中出现...","...未被遮挡"]'
          />
        </el-form-item>

        <el-form-item label="是否启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          保存
        </el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchRules,
  createRule,
  updateRule,
  deleteRule,
  objectifyRule,
} from '../api/rule'
import request from '../api/request'

const loading = ref(false)
const saving = ref(false)
const objectifyingId = ref(null)

const onlyActive = ref(false)
const keyword = ref('')
const rules = ref([])

const dialogVisible = ref(false)
const editingId = ref(null)

const form = ref({
  rule_name: '',
  original_rule: '',
  is_active: true,
})

const preconditionsText = ref('[]')

function unwrap(res) {
  if (!res) return null
  if (res.status && res.data !== undefined) return res.data
  if (res.data && res.data.data !== undefined) return res.data.data
  if (res.data !== undefined) return res.data
  return res
}

const filteredRules = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return rules.value
  return rules.value.filter((item) => {
    return (
      String(item.rule_name || '').toLowerCase().includes(kw) ||
      String(item.original_rule || '').toLowerCase().includes(kw) ||
      String(item.objectified_rule || '').toLowerCase().includes(kw)
    )
  })
})

function toggleShowAll() {
  onlyActive.value = !onlyActive.value
  loadRules()
}

async function loadRules() {
  loading.value = true
  try {
    const res = await fetchRules(!onlyActive.value ? true : false)
    const data = unwrap(res) || []
    rules.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载规则失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = {
    rule_name: '',
    original_rule: '',
    is_active: true,
  }
  preconditionsText.value = '[]'
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = {
    rule_name: row.rule_name || '',
    original_rule: row.original_rule || '',
    is_active: !!row.is_active,
  }
  preconditionsText.value = JSON.stringify(row.preconditions || [], null, 2)
  dialogVisible.value = true
}

async function handleSave() {
  const originalRule = String(form.value.original_rule || '').trim()
  if (!originalRule) {
    ElMessage.warning('原始规则不能为空')
    return
  }

  let preconditions = []
  try {
    preconditions = JSON.parse(preconditionsText.value || '[]')
    if (!Array.isArray(preconditions)) {
      throw new Error('预条件必须是数组')
    }
  } catch {
    ElMessage.error('预条件链必须是合法 JSON 数组')
    return
  }

  saving.value = true
  try {
    const payload = {
      rule_name: form.value.rule_name,
      original_rule: originalRule,
      preconditions,
      is_active: form.value.is_active,
    }

    if (editingId.value) {
      await updateRule(editingId.value, payload)
      ElMessage.success('规则更新成功')
    } else {
      await createRule(payload)
      ElMessage.success('规则创建成功')
    }

    dialogVisible.value = false
    await loadRules()
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除规则【${row.rule_name}】吗？`,
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
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

async function handleObjectify(row) {
  objectifyingId.value = row.id
  try {
    const res = await objectifyRule(row.id)
    const data = unwrap(res)

    const index = rules.value.findIndex(item => item.id === row.id)
    if (index !== -1 && data) {
      rules.value[index] = { ...rules.value[index], ...data }
    }

    ElMessage.success('客观化完成')
    await loadRules()
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '客观化失败')
  } finally {
    objectifyingId.value = null
  }
}

async function handleToggleActive(row, value) {
  try {
    await request.patch(`/api/rules/${row.id}/active`, { is_active: value })
    ElMessage.success(value ? '规则已启用' : '规则已禁用')
  } catch (e) {
    row.is_active = !value
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '状态更新失败')
  }
}

onMounted(() => {
  loadRules()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.left-tools {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.right-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.title {
  font-size: 16px;
  font-weight: 700;
}

.switch-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-input {
  width: 300px;
}

.text-block {
  line-height: 1.7;
  color: #333;
  white-space: normal;
  word-break: break-word;
}

.objectified {
  color: #1f4b99;
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.action-wrap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.footer-tip {
  margin-top: 12px;
  color: #888;
  font-size: 12px;
}

.muted {
  color: #999;
  font-size: 12px;
}
</style>