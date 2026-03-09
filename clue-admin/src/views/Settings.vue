<template>
  <div style="padding: 16px">
    <el-card shadow="hover">
      <template #header>
        <div style="display:flex; align-items:center; justify-content:space-between;">
          <div style="font-weight:700;">系统设置</div>
          <div style="display:flex; gap:10px;">
            <el-button @click="load" :loading="loading">刷新</el-button>
            <el-button type="primary" @click="onSave" :loading="saving">保存设置</el-button>
          </div>
        </div>
      </template>

      <el-alert
        title="本页面用于调整审核引擎行为参数。修改后将影响自动审核结果。"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 12px"
      />

      <el-form :model="form" label-width="160px" style="max-width: 980px">

        <!-- 审核模式 -->
        <el-form-item label="审核模式">
          <el-select v-model="form.clue_provider" style="width: 260px">
            <el-option label="模拟模式（本地演示）" value="mock" />
            <el-option label="真实模型模式（预留）" value="openai" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">模拟参数设置</el-divider>

        <!-- 命中概率 -->
        <el-form-item label="关键词命中触发概率">
          <div style="display:flex; align-items:center; gap:12px; width: 100%;">
            <el-slider
              v-model="form.mock_hit_rate"
              :min="0"
              :max="1"
              :step="0.01"
              style="max-width: 520px"
            />
            <div style="color:#666; width: 60px;">
              {{ form.mock_hit_rate.toFixed(2) }}
            </div>
          </div>
        </el-form-item>

        <!-- 随机兜底 -->
        <el-form-item label="随机补偿触发概率">
          <div style="display:flex; align-items:center; gap:12px; width: 100%;">
            <el-slider
              v-model="form.mock_random_hit_rate"
              :min="0"
              :max="1"
              :step="0.01"
              style="max-width: 520px"
            />
            <div style="color:#666; width: 60px;">
              {{ form.mock_random_hit_rate.toFixed(2) }}
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">规则触发关键词</el-divider>

        <el-form-item label="关键词配置（JSON）">
          <div style="width: 100%;">
            <el-input
              v-model="keywordText"
              type="textarea"
              :rows="12"
              placeholder="请输入合法的 JSON 对象"
            />
          </div>
        </el-form-item>

        <el-divider content-position="left">系统检测</el-divider>

        <el-form-item label="接口连通测试">
          <el-button @click="ping" :loading="pinging">测试接口</el-button>
          <span v-if="pingResult" style="margin-left: 12px; color:#666;">
            {{ pingResult }}
          </span>
        </el-form-item>

      </el-form>
    </el-card>
  </div>
</template>

<script setup>
/*
==========================================
参数说明（论文可引用）

1. 关键词命中触发概率
   当规则文本中包含设定关键词时，
   按此概率决定是否判定违规。

2. 随机补偿触发概率
   若未命中任何关键词，
   按此概率随机触发一条规则，
   用于模拟真实模型的不确定性。

3. 审核模式
   - 模拟模式：使用本地概率与关键词机制
   - 真实模型模式：预留接口（需后端接入）

==========================================
*/

import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchSettings, saveSettings } from '../api/settings'

const loading = ref(false)
const saving = ref(false)
const pinging = ref(false)
const pingResult = ref('')

const form = ref({
  clue_provider: 'mock',
  mock_hit_rate: 0.75,
  mock_random_hit_rate: 0.2,
  keyword_triggers: {},
})

const keywordText = ref('')

function prettyJson(obj) {
  return JSON.stringify(obj ?? {}, null, 2)
}

function safeParseJson(text) {
  try {
    return { ok: true, value: JSON.parse(text) }
  } catch (e) {
    return { ok: false }
  }
}

function unwrap(res) {
  if (!res) return null
  if (res.status && res.data !== undefined) return res.data
  if (res.data && res.data.data !== undefined) return res.data.data
  if (res.data !== undefined) return res.data
  return res
}

async function load() {
  loading.value = true
  try {
    const res = await fetchSettings()
    const data = unwrap(res)

    form.value = {
      clue_provider: data?.clue_provider ?? 'mock',
      mock_hit_rate: Number(data?.mock_hit_rate ?? 0.75),
      mock_random_hit_rate: Number(data?.mock_random_hit_rate ?? 0.2),
      keyword_triggers: data?.keyword_triggers ?? {},
    }

    keywordText.value = prettyJson(form.value.keyword_triggers)
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function onSave() {
  const parsed = safeParseJson(keywordText.value)
  if (!parsed.ok) {
    ElMessage.error('关键词 JSON 格式错误')
    return
  }

  const payload = {
    clue_provider: form.value.clue_provider,
    mock_hit_rate: Number(form.value.mock_hit_rate),
    mock_random_hit_rate: Number(form.value.mock_random_hit_rate),
    keyword_triggers: parsed.value,
  }

  saving.value = true
  try {
    await saveSettings(payload)
    ElMessage.success('保存成功')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function ping() {
  pinging.value = true
  try {
    await fetchSettings()
    pingResult.value = '接口正常'
  } catch {
    pingResult.value = '接口不可用'
  } finally {
    pinging.value = false
  }
}

onMounted(load)
</script>