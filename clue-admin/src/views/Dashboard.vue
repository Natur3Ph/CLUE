<template>
  <div class="dashboard-page">
    <!-- 顶部欢迎区 -->
    <div class="hero-section">
      <div class="hero-left">
        <div class="hero-title">图像安全审核控制台</div>
        <div class="hero-desc">
          欢迎进入图像安全自动化审核系统。当前页面用于展示审核任务概览、运行状态与最近任务记录。
        </div>

        <div class="hero-actions">
          <el-button @click="goCreateTask">新建审核任务</el-button>
          <el-button @click="goTaskList">查看任务列表</el-button>
          <el-button @click="goRules">查看规则管理</el-button>
        </div>
      </div>

      <div class="hero-right">
        <div class="hero-panel">
          <div class="hero-panel-label">系统状态</div>
          <div class="hero-panel-value">运行正常</div>
          <div class="hero-panel-sub">基于 FastAPI + Vue + 多模态模型</div>
        </div>
      </div>
    </div>

    <!-- 核心统计卡片 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-card-total" shadow="hover">
          <div class="stat-label">总任务数</div>
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-footer">当前已加载任务样本统计</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-card-pass" shadow="hover">
          <div class="stat-label">自动放行</div>
          <div class="stat-value">{{ stats.pass }}</div>
          <div class="stat-footer">系统判定为安全的任务数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-card-reject" shadow="hover">
          <div class="stat-label">自动拦截</div>
          <div class="stat-value">{{ stats.reject }}</div>
          <div class="stat-footer">系统判定为违规的任务数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-card-time" shadow="hover">
          <div class="stat-label">平均耗时</div>
          <div class="stat-value">
            {{ stats.avgMs }}<span class="stat-unit"> ms</span>
          </div>
          <div class="stat-footer">单次审核平均推理耗时</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 审核概览 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :lg="12">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">审核结果概览</span>
            </div>
          </template>

          <div class="overview-item">
            <div class="overview-top">
              <span>安全通过率</span>
              <span>{{ passRate }}%</span>
            </div>
            <el-progress :percentage="passRate" :stroke-width="14" status="success" />
          </div>

          <div class="overview-item">
            <div class="overview-top">
              <span>风险拦截率</span>
              <span>{{ rejectRate }}%</span>
            </div>
            <el-progress :percentage="rejectRate" :stroke-width="14" status="exception" />
          </div>

          <div class="overview-grid">
            <div class="overview-box">
              <div class="overview-box-label">安全任务</div>
              <div class="overview-box-value">{{ stats.pass }}</div>
            </div>
            <div class="overview-box">
              <div class="overview-box-label">违规任务</div>
              <div class="overview-box-value">{{ stats.reject }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span class="panel-title">系统说明</span>
            </div>
          </template>

          <div class="info-list">
            <div class="info-item">
              <div class="info-dot"></div>
              <div class="info-text">支持基于安全规则的图像自动审核流程。</div>
            </div>
            <div class="info-item">
              <div class="info-dot"></div>
              <div class="info-text">支持规则客观化、审核任务管理、数据集与 Benchmark 测试。</div>
            </div>
            <div class="info-item">
              <div class="info-dot"></div>
              <div class="info-text">当前首页统计基于最近加载的审核任务列表生成，不改变任何后端逻辑。</div>
            </div>
            <div class="info-item">
              <div class="info-dot"></div>
              <div class="info-text">后续可继续叠加图表、规则命中统计与 Benchmark 可视化。</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近任务 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="panel-header">
          <div>
            <div class="panel-title">最近任务</div>
            <div class="panel-subtitle">展示最新审核任务记录，便于查看系统近期运行情况</div>
          </div>

          <div class="table-tools">
            <el-button @click="goTaskList">进入任务管理</el-button>
            <el-button type="primary" @click="load" :loading="loading">刷新数据</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="latestTasks"
        v-loading="loading"
        class="task-table"
        empty-text="暂无审核任务数据"
        style="width: 100%"
      >
        <el-table-column prop="task_id" label="任务ID" min-width="180" />

        <el-table-column label="任务状态" width="130">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="light">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="审核结果" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.is_safe" type="success">安全</el-tag>
            <el-tag v-else type="danger">违规</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="推理耗时" width="120">
          <template #default="{ row }">
            {{ Number(row.inference_time_ms || 0) }} ms
          </template>
        </el-table-column>

        <el-table-column label="违规规则数" width="120">
          <template #default="{ row }">
            {{ Array.isArray(row.violated_details) ? row.violated_details.length : 0 }}
          </template>
        </el-table-column>

        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        当前展示 {{ latestTasks.length }} 条最近任务记录（统计数据基于本次加载结果生成）
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { fetchAuditTasks } from '../api/task'

const router = useRouter()

const loading = ref(false)
const tasks = ref([])

const stats = computed(() => {
  const list = tasks.value || []
  const total = list.length
  const pass = list.filter((t) => t.status === 'auto_pass').length
  const reject = list.filter((t) => t.status === 'auto_reject').length

  const msList = list.map((t) => Number(t.inference_time_ms || 0))
  const avg = msList.length
    ? Math.round(msList.reduce((a, b) => a + b, 0) / msList.length)
    : 0

  return {
    total,
    pass,
    reject,
    avgMs: avg,
  }
})

const passRate = computed(() => {
  const total = stats.value.total
  if (!total) return 0
  return Number(((stats.value.pass / total) * 100).toFixed(1))
})

const rejectRate = computed(() => {
  const total = stats.value.total
  if (!total) return 0
  return Number(((stats.value.reject / total) * 100).toFixed(1))
})

const latestTasks = computed(() => {
  return (tasks.value || []).slice(0, 10)
})

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

function goCreateTask() {
  router.push('/tasks/create')
}

function goTaskList() {
  router.push('/tasks')
}

function goRules() {
  router.push('/rules')
}

async function load() {
  loading.value = true
  try {
    const res = await fetchAuditTasks(100)
    tasks.value = res?.data || []
  } catch (e) {
    console.error('加载仪表盘数据失败：', e)
  } finally {
    loading.value = false
  }
}

load()
</script>

<style scoped>
.dashboard-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100%;
  box-sizing: border-box;
}

.hero-section {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 24px 28px;
  border-radius: 16px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
}

.hero-left {
  flex: 1;
}

.hero-title {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
}

.hero-desc {
  margin-top: 10px;
  max-width: 720px;
  font-size: 14px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.92);
}

.hero-actions {
  margin-top: 18px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-right {
  width: 240px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.hero-panel {
  width: 100%;
  padding: 18px 20px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(4px);
  text-align: left;
}

.hero-panel-label {
  font-size: 13px;
  opacity: 0.9;
}

.hero-panel-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
}

.hero-panel-sub {
  margin-top: 8px;
  font-size: 13px;
  opacity: 0.9;
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

.stat-unit {
  font-size: 16px;
  font-weight: 500;
  color: #606266;
}

.stat-footer {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
}

.stat-card-total {
  border-left: 4px solid #409eff;
}

.stat-card-pass {
  border-left: 4px solid #67c23a;
}

.stat-card-reject {
  border-left: 4px solid #f56c6c;
}

.stat-card-time {
  border-left: 4px solid #e6a23c;
}

.panel-card,
.table-card {
  border-radius: 14px;
  border: none;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}

.overview-item + .overview-item {
  margin-top: 18px;
}

.overview-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}

.overview-grid {
  margin-top: 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.overview-box {
  padding: 16px;
  border-radius: 12px;
  background: #f8fafc;
}

.overview-box-label {
  font-size: 13px;
  color: #909399;
}

.overview-box-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.info-dot {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 50%;
  background: #409eff;
  flex-shrink: 0;
}

.info-text {
  font-size: 14px;
  line-height: 1.8;
  color: #606266;
}

.table-tools {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.task-table :deep(th.el-table__cell) {
  background: #f8fafc;
  color: #606266;
  font-weight: 600;
}

.table-footer {
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
}

@media (max-width: 992px) {
  .hero-section {
    flex-direction: column;
  }

  .hero-right {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>