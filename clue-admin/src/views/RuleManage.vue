<template>
  <div style="padding: 16px">
    <el-card shadow="hover">
      <template #header>
        <div style="display:flex; align-items:center; justify-content:space-between;">
          <div style="font-weight:700;">规则管理</div>

          <div style="display:flex; gap:10px; align-items:center;">
            <el-switch v-model="showAll" active-text="显示全部" inactive-text="仅启用" />

            <el-input
              v-model="keyword"
              placeholder="搜索：规则名称 / 原始规则"
              clearable
              style="width: 320px"
            />

            <el-button type="primary" @click="openCreate()">新增规则</el-button>
            <el-button @click="openBatch()">批量导入</el-button>
            <el-button @click="load()" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="filteredRules"
        v-loading="loading"
        style="width: 100%"
        row-key="id"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="rule_name" label="规则名称" min-width="160" />

        <el-table-column
          prop="original_rule"
          label="原始规则"
          min-width="360"
          show-overflow-tooltip
        />

        <el-table-column label="预条件" min-width="260">
          <template #default="{ row }">
            <div v-if="row.preconditions && row.preconditions.length">
              <el-tag
                v-for="(p, idx) in row.preconditions"
                :key="idx"
                style="margin-right:6px; margin-bottom:6px"
              >
                {{ typeof p === 'object' && p !== null ? (p.text || JSON.stringify(p)) : p }}
              </el-tag>
            </div>
            <span v-else style="color:#999;">无</span>
          </template>
        </el-table-column>

        <el-table-column label="启用" width="120">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="(val) => onToggle(row, val)"
            />
          </template>
        </el-table-column>

        <el-table-column prop="version" label="版本" width="90" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />

        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>

            <!-- ✅ 新增：一键客观化 -->
            <el-button
              size="small"
              type="success"
              :loading="row._objectifying === true"
              @click="onObjectify(row)"
            >
              一键客观化
            </el-button>

            <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 12px; color:#666;">
        当前显示 {{ filteredRules.length }} 条（共 {{ rules.length }} 条）
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增规则' : '编辑规则'"
      width="720px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="规则名称">
          <el-input v-model="form.rule_name" placeholder="例如：裸露/生殖器/臀部未遮挡" />
        </el-form-item>

        <el-form-item label="原始规则">
          <el-input
            v-model="form.original_rule"
            type="textarea"
            :rows="3"
            placeholder="例如：图像中出现了人物的生殖器或臀部未被遮挡"
          />
        </el-form-item>

        <el-form-item label="预条件">
          <el-input
            v-model="preconditionsText"
            type="textarea"
            :rows="3"
            placeholder="一行一个预条件（可为空）&#10;例如：画面中出现明显血液"
          />
          <div style="font-size:12px; color:#888; margin-top:6px;">
            预条件会保存为数组：["条件1","条件2"...]
          </div>
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入弹窗 -->
    <el-dialog v-model="batchVisible" title="批量导入规则" width="720px">
      <div style="color:#666; margin-bottom:10px;">
        支持两种格式（任选其一）：
        <div style="margin-top:6px;">
          1）每行一个“原始规则”，系统自动生成 rule_name<br/>
          2）每行：规则名称 | 原始规则（用竖线分隔）
        </div>
      </div>

      <el-input
        v-model="batchText"
        type="textarea"
        :rows="10"
        placeholder="示例：&#10;裸露/生殖器/臀部未遮挡 | 图像中出现了人物的生殖器或臀部未被遮挡&#10;包含人物因严重受伤流血而濒临死亡的画面"
      />

      <template #footer>
        <el-button @click="batchVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onBatchImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchRules, createRule, updateRule, deleteRule, objectifyRule } from '../api/rule'

const loading = ref(false)
const saving = ref(false)

const showAll = ref(true)
const keyword = ref('')
const rules = ref([])

const dialogVisible = ref(false)
const dialogMode = ref('create') // create | edit
const form = ref({
  id: null,
  rule_name: '',
  original_rule: '',
  preconditions: [],
  is_active: true
})
const preconditionsText = ref('')

const batchVisible = ref(false)
const batchText = ref('')

function normalizePreconditionsTextToArray(text) {
  if (!text) return []
  return text
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)
}

function makeRuleNameFromOriginal(original) {
  const s = (original || '').trim()
  if (!s) return '未命名规则'
  return s.length > 12 ? s.slice(0, 12) + '...' : s
}

const filteredRules = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return rules.value
  return rules.value.filter(r => {
    const a = (r.rule_name || '').toLowerCase()
    const b = (r.original_rule || '').toLowerCase()
    return a.includes(kw) || b.includes(kw)
  })
})

async function load() {
  loading.value = true
  try {
    const res = await fetchRules(showAll.value)

    const list =
      Array.isArray(res) ? res :
      Array.isArray(res?.data) ? res.data :
      Array.isArray(res?.data?.data) ? res.data.data :
      Array.isArray(res?.data?.data?.data) ? res.data.data.data :
      []

    rules.value = list.map(r => ({
      ...r,
      preconditions: r.preconditions || [],
      _objectifying: false
    }))
  } catch (e) {
    ElMessage.error('拉取规则失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  form.value = {
    id: null,
    rule_name: '',
    original_rule: '',
    preconditions: [],
    is_active: true
  }
  preconditionsText.value = ''
  dialogVisible.value = true
}

function openEdit(row) {
  dialogMode.value = 'edit'
  form.value = {
    id: row.id,
    rule_name: row.rule_name || '',
    original_rule: row.original_rule || '',
    preconditions: row.preconditions || [],
    is_active: !!row.is_active
  }
  preconditionsText.value = (row.preconditions || []).map(p => (typeof p === 'object' && p ? (p.text || '') : p)).join('\n')
  dialogVisible.value = true
}

async function onSave() {
  const payload = {
    rule_name: (form.value.rule_name || '').trim(),
    original_rule: (form.value.original_rule || '').trim(),
    preconditions: normalizePreconditionsTextToArray(preconditionsText.value),
    is_active: !!form.value.is_active
  }

  if (!payload.original_rule) {
    ElMessage.warning('原始规则不能为空')
    return
  }
  if (!payload.rule_name) {
    payload.rule_name = makeRuleNameFromOriginal(payload.original_rule)
  }

  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      await createRule(payload)
      ElMessage.success('创建成功')
    } else {
      await updateRule(form.value.id, payload)
      ElMessage.success('保存成功')
    }
    dialogVisible.value = false
    await load()
  } catch (e) {
    console.error(e)
    ElMessage.error('保存失败（检查后端接口）')
  } finally {
    saving.value = false
  }
}

async function onToggle(row, val) {
  const oldVal = !val
  try {
    await updateRule(row.id, { is_active: !!val })
    ElMessage.success(val ? '已启用' : '已停用')
  } catch (e) {
    console.error(e)
    row.is_active = oldVal
    ElMessage.error('切换失败')
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除规则【${row.rule_name || row.id}】吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
  } catch {
    return
  }

  saving.value = true
  try {
    await deleteRule(row.id)
    ElMessage.success('删除成功')
    await load()
  } catch (e) {
    console.error(e)
    ElMessage.error('删除失败')
  } finally {
    saving.value = false
  }
}

async function onObjectify(row) {
  if (!row || !row.id) return

  row._objectifying = true
  try {
    await objectifyRule(row.id)
    ElMessage.success('已生成预条件链')
    await load()
  } catch (e) {
    console.error(e)
    ElMessage.error('客观化失败（检查后端是否已实现 /api/rules/{id}/objectify）')
  } finally {
    row._objectifying = false
  }
}

function openBatch() {
  batchText.value = ''
  batchVisible.value = true
}

async function onBatchImport() {
  const lines = (batchText.value || '')
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)

  if (!lines.length) {
    ElMessage.warning('请输入至少一行规则')
    return
  }

  saving.value = true
  try {
    for (const line of lines) {
      let rule_name = ''
      let original_rule = ''
      if (line.includes('|')) {
        const [a, b] = line.split('|').map(s => s.trim())
        rule_name = a
        original_rule = b
      } else {
        original_rule = line
        rule_name = makeRuleNameFromOriginal(original_rule)
      }
      if (!original_rule) continue
      await createRule({
        rule_name,
        original_rule,
        preconditions: [],
        is_active: true
      })
    }
    ElMessage.success(`导入完成：${lines.length} 条`)
    batchVisible.value = false
    await load()
  } catch (e) {
    console.error(e)
    ElMessage.error('导入失败')
  } finally {
    saving.value = false
  }
}

watch(showAll, async () => {
  await load()
})

onMounted(() => {
  load()
})
</script>