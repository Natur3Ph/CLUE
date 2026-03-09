<template>
  <div style="padding: 16px;">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card>
          <div style="font-size: 14px; color: #666;">总任务数</div>
          <div style="font-size: 28px; font-weight: 600;">{{ stats.total }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div style="font-size: 14px; color: #666;">自动放行</div>
          <div style="font-size: 28px; font-weight: 600;">{{ stats.pass }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div style="font-size: 14px; color: #666;">自动拦截</div>
          <div style="font-size: 28px; font-weight: 600;">{{ stats.reject }}</div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <div style="font-size: 14px; color: #666;">平均耗时(ms)</div>
          <div style="font-size: 28px; font-weight: 600;">{{ stats.avgMs }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 16px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size: 16px; font-weight: 600;">最近任务</div>
        <el-button type="primary" @click="load">刷新</el-button>
      </div>

      <el-table
        style="width: 100%; margin-top: 12px;"
        :data="latestTasks"
        v-loading="loading"
      >
        <el-table-column prop="task_id" label="任务ID" min-width="180" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="是否安全" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_safe" type="success">安全</el-tag>
            <el-tag v-else type="danger">违规</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="inference_time_ms" label="耗时(ms)" width="120" />
        <el-table-column prop="created_at" label="创建时间" min-width="200" />
      </el-table>

      <div style="margin-top: 10px; color:#999; font-size: 12px;">
        当前显示 {{ latestTasks.length }} 条（最多 10 条）
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import { fetchAuditTasks } from "../api/task"

const loading = ref(false)
const tasks = ref([])

const stats = computed(() => {
  const list = tasks.value || []
  const total = list.length
  const pass = list.filter(t => t.status === "auto_pass").length
  const reject = list.filter(t => t.status === "auto_reject").length

  const msList = list.map(t => Number(t.inference_time_ms || 0))
  const avg = msList.length
    ? Math.round(msList.reduce((a, b) => a + b, 0) / msList.length)
    : 0

  return { total, pass, reject, avgMs: avg }
})

const latestTasks = computed(() => {
  return (tasks.value || []).slice(0, 10)
})

async function load() {
  loading.value = true
  try {
    const res = await fetchAuditTasks(100)
    tasks.value = res?.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

load()
</script>