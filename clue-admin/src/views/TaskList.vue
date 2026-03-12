<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <span style="font-weight:bold;">审核任务</span>
        <div>
          <el-button type="success" @click="goCreate">新建任务</el-button>
          <el-button type="warning" @click="goBatchCreate">批量审核</el-button>
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

      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            type="danger"
            size="small"
            @click.stop="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAuditTasks, deleteAuditTask } from '../api/task'

const router = useRouter()

const tasks = ref([])
const loading = ref(false)

function goDetail(row) {
  router.push(`/tasks/${row.task_id}`)
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
    const res = await fetchAuditTasks(20)
    tasks.value = unwrap(res) || []
  } catch (err) {
    console.error(err)
    ElMessage.error('获取任务失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

function goCreate() {
  router.push('/tasks/create')
}

function goBatchCreate() {
  router.push('/tasks/create?mode=batch')
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除审核任务【${row.task_id}】吗？`,
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
    await deleteAuditTask(row.task_id)
    ElMessage.success('删除成功')
    await load()
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || err?.message || '删除失败')
  }
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