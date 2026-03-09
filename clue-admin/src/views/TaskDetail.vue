<template>
  <el-card v-loading="loading">
    <template #header>
      <div style="display:flex;align-items:center;gap:12px;">
        <el-button @click="goBack">返回</el-button>
        <span>任务详情：{{ taskId }}</span>
      </div>
    </template>

    <div v-if="task">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">{{ task.task_id }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ task.status }}</el-descriptions-item>
        <el-descriptions-item label="是否安全">
          <el-tag :type="task.is_safe ? 'success' : 'danger'">
            {{ task.is_safe ? '安全' : '不安全' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="耗时(ms)">{{ task.inference_time_ms }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ task.created_at }}</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top:16px;">
        <h3>违规命中详情</h3>
        <el-empty v-if="!details.length" description="暂无违规命中" />
        <el-tag v-for="(r, idx) in details" :key="idx" type="danger" style="margin:4px;">
          {{ r }}
        </el-tag>
      </div>

      <div style="margin-top:16px;">
        <h3>图片</h3>
        <el-alert
          type="info"
          show-icon
          title="本图片为审核存档，仅用于安全评估与结果追溯。"
        />
        <div style="margin-top:8px;">
          <img
            v-if="task.image_url"
            :src="task.image_url"
            style="max-width:500px;border:1px solid #eee;border-radius:6px;"
          />
          <div v-else style="color:#888;">暂无 image_url</div>
        </div>
      </div>
    </div>

    <el-empty v-else description="未找到任务数据" />
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../api/request'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id

const loading = ref(false)
const task = ref(null)

const details = computed(() => {
  const raw = task.value?.violated_details || task.value?.violated_rules || []
  if (Array.isArray(raw)) return raw
  return []
})

function goBack() {
  router.push('/tasks')
}

// 统一解包：兼容 request.js 已经 return res.data 的情况
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
    // 先用“列表接口 + 前端过滤”兜底（因为你后端暂时没 /api/audit-tasks/{id}）
    const res = await request.get('/api/audit-tasks', { params: { limit: 200 } })
    const list = unwrap(res) || []
    task.value = list.find(t => t.task_id === taskId) || null
  } catch (e) {
    console.error(e)
    task.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>