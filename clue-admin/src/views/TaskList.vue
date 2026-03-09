<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <span style="font-weight:bold;">审核任务</span>
        <div>
          <el-button type="success" @click="goCreate">新建任务</el-button>
          <el-button type="primary" @click="load">刷新</el-button>
        </div>
      </div>
    </template>

    <el-table
      :data="tasks"
      v-loading="loading"
      style="width: 100%"
      @row-click="goDetail"
      border
      stripe
    >
      <el-table-column prop="task_id" label="任务ID" width="200" />
      <el-table-column prop="status" label="状态" width="140" />

      <el-table-column prop="is_safe" label="是否安全" width="120">
        <template #default="{ row }">
          <el-tag :type="row.is_safe ? 'success' : 'danger'">
            {{ row.is_safe ? '安全' : '不安全' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="inference_time_ms" label="耗时(ms)" width="120" />
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>

    <el-empty
      v-if="!loading && tasks.length === 0"
      description="暂无审核任务"
      style="margin-top:20px;"
    />

    <div style="margin-top:10px;color:#888;font-size:12px;">
      当前显示 {{ tasks.length }} 条数据
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchAuditTasks } from '../api/task'

const router = useRouter()

const tasks = ref([])
const loading = ref(false)

// 跳转详情
function goDetail(row) {
  router.push(`/tasks/${row.task_id}`)
}

// 统一解包：兼容 request.js 已经 return res.data 的情况
function unwrap(res) {
  if (!res) return null
  // 常见：res === {status, data}
  if (res.status && res.data !== undefined) return res.data
  // 兜底：如果未来有人绕过 request.js 拿到 axios 原响应
  if (res.data && res.data.data !== undefined) return res.data.data
  if (res.data !== undefined) return res.data
  return res
}

// 加载数据
async function load() {
  loading.value = true
  try {
    const res = await fetchAuditTasks(20)
    tasks.value = unwrap(res) || []
  } catch (err) {
    console.error(err)
    alert('获取任务失败，请确认后端已启动 http://127.0.0.1:8000')
  } finally {
    loading.value = false
  }
}

function goCreate() {
  router.push('/tasks/create')
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.el-table {
  cursor: pointer;
}
</style>