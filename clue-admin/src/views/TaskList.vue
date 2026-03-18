<template>
  <div class="task-page">
    <!-- 顶部说明区 -->
    <div class="page-banner">
      <div>
        <div class="page-title">审核任务管理</div>
        <div class="page-desc">
          统一查看系统历史审核任务，支持任务刷新、详情查看与删除管理。
        </div>
      </div>

      <div class="page-actions">
        <el-button @click="load" :loading="loading">刷新数据</el-button>
        <el-button type="warning" @click="goBatchCreate">批量审核</el-button>
        <el-button type="primary" @click="goCreate">新建任务</el-button>
      </div>
    </div>

    <!-- 顶部统计 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-total" shadow="hover">
          <div class="stat-label">任务总数</div>
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-sub">当前列表已加载任务数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-safe" shadow="hover">
          <div class="stat-label">安全任务</div>
          <div class="stat-value">{{ stats.safe }}</div>
          <div class="stat-sub">模型判定为安全</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-risk" shadow="hover">
          <div class="stat-label">违规任务</div>
          <div class="stat-value">{{ stats.unsafe }}</div>
          <div class="stat-sub">模型判定为违规</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-time" shadow="hover">
          <div class="stat-label">平均耗时</div>
          <div class="stat-value">{{ stats.avgMs }}<span class="unit"> ms</span></div>
          <div class="stat-sub">平均推理耗时</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务表格 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <div>
            <div class="card-title">任务列表</div>
            <div class="card-subtitle">点击任意行可进入任务详情页</div>
          </div>
          <div class="table-summary">
            当前显示 {{ tasks.length }} 条数据
          </div>
        </div>
      </template>

      <el-table
        :data="tasks"
        v-loading="loading"
        class="task-table"
        style="width: 100%"
        @row-click="goDetail"
        border
      >
        <el-table-column prop="task_id" label="任务ID" min-width="190" />

        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="light">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="审核结果" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_safe ? 'success' : 'danger'">
              {{ row.is_safe ? '安全' : '违规' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="违规规则数" width="120">
          <template #default="{ row }">
            {{ Array.isArray(row.violated_details) ? row.violated_details.length : 0 }}
          </template>
        </el-table-column>

        <el-table-column label="推理耗时" width="120">
          <template #default="{ row }">
            {{ Number(row.inference_time_ms || 0) }} ms
          </template>
        </el-table-column>

        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="goDetail(row)">
              详情
            </el-button>
            <el-button
              link
              type="danger"
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
        class="empty-block"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAuditTasks, deleteAuditTask } from '../api/task'

const router = useRouter()

const tasks = ref([])
const loading = ref(false)

const stats = computed(() => {
  const list = tasks.value || []
  const total = list.length
  const safe = list.filter((t) => !!t.is_safe).length
  const unsafe = list.filter((t) => t.is_safe === false).length

  const msList = list.map((t) => Number(t.inference_time_ms || 0))
  const avgMs = msList.length
    ? Math.round(msList.reduce((a, b) => a + b, 0) / msList.length)
    : 0

  return {
    total,
    safe,
    unsafe,
    avgMs,
  }
})

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

function statusText(status) {
  if (status === 'auto_pass') return '自动放行'
  if (status === 'auto_reject') return '自动拦截'
  if (status === 'pending_review') return '待复核'
  return status || '未知状态'
}

function statusTagType(status) {
  if (status === 'auto_pass') return 'success'
  if (status === 'auto_reject') return 'danger'
  if (status === 'pending_review') return 'warning'
  return 'info'
}

function formatDateTime(value) {
  if (!value) return '-'
  const text = String(value).replace('T', ' ')
  return text.slice(0, 19)
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
.task-page {
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

.unit {
  font-size: 16px;
  font-weight: 500;
  color: #606266;
}

.stat-sub {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
}

.stat-total {
  border-left: 4px solid #409eff;
}

.stat-safe {
  border-left: 4px solid #67c23a;
}

.stat-risk {
  border-left: 4px solid #f56c6c;
}

.stat-time {
  border-left: 4px solid #e6a23c;
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

.task-table {
  cursor: pointer;
}

.task-table :deep(th.el-table__cell) {
  background: #f8fafc;
  color: #606266;
  font-weight: 600;
}

.empty-block {
  margin-top: 20px;
}

@media (max-width: 992px) {
  .page-banner,
  .table-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>