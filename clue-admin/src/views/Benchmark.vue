<template>
  <div class="benchmark-page">
    <!-- 顶部说明区 -->
    <div class="page-banner">
      <div>
        <div class="page-title">Benchmark 测试</div>
        <div class="page-desc">
          基于测试数据集运行批量图像审核评测，并展示准确率、精确率、召回率、F1 值及错误样本。
        </div>
      </div>

      <div class="page-actions">
        <el-button @click="loadBenchmarkRuns" :loading="loadingRuns">刷新记录</el-button>
      </div>
    </div>

    <!-- 启动评测 -->
    <el-card class="panel-card section-row" shadow="never">
      <template #header>
        <div class="card-title">启动新评测</div>
      </template>

      <el-form :inline="true" class="run-form">
        <el-form-item label="选择数据集">
          <el-select
            v-model="runForm.dataset_id"
            placeholder="请选择数据集"
            style="width: 260px"
          >
            <el-option
              v-for="item in datasets"
              :key="item.id"
              :label="`${item.dataset_name}（${item.total_count}张）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="评测名称">
          <el-input
            v-model="runForm.run_name"
            placeholder="例如：openai_benchmark_run_01"
            style="width: 260px"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="running" @click="handleRunBenchmark">
            开始评测
          </el-button>
        </el-form-item>
      </el-form>

      <div class="form-tip">
        说明：运行评测时，系统会读取当前数据集与当前启用规则，对样本逐一执行审核并统计性能指标。
      </div>
    </el-card>

    <!-- 顶部统计 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-total" shadow="hover">
          <div class="stat-label">评测总数</div>
          <div class="stat-value">{{ summary.totalRuns }}</div>
          <div class="stat-sub">历史 Benchmark 记录数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-accuracy" shadow="hover">
          <div class="stat-label">Accuracy</div>
          <div class="stat-value">{{ selectedMetrics.accuracy }}</div>
          <div class="stat-sub">当前详情记录</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-precision" shadow="hover">
          <div class="stat-label">Precision</div>
          <div class="stat-value">{{ selectedMetrics.precision }}</div>
          <div class="stat-sub">当前详情记录</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-recall" shadow="hover">
          <div class="stat-label">Recall</div>
          <div class="stat-value">{{ selectedMetrics.recall }}</div>
          <div class="stat-sub">当前详情记录</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-f1" shadow="hover">
          <div class="stat-label">F1 Score</div>
          <div class="stat-value">{{ selectedMetrics.f1 }}</div>
          <div class="stat-sub">当前详情记录</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-tp" shadow="hover">
          <div class="stat-label">TP</div>
          <div class="stat-value">{{ selectedMetrics.tp }}</div>
          <div class="stat-sub">违规识别正确数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-tn" shadow="hover">
          <div class="stat-label">TN</div>
          <div class="stat-value">{{ selectedMetrics.tn }}</div>
          <div class="stat-sub">安全识别正确数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="3">
        <el-card class="stat-card stat-wrong" shadow="hover">
          <div class="stat-label">错误样本</div>
          <div class="stat-value">{{ selectedMetrics.wrong }}</div>
          <div class="stat-sub">当前详情记录</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 评测记录 + 详情 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :lg="14">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="table-header">
              <div>
                <div class="card-title">评测记录</div>
                <div class="card-subtitle">展示历史 Benchmark 结果，可点击查看详情</div>
              </div>
              <div class="table-summary">当前显示 {{ benchmarkRuns.length }} 条记录</div>
            </div>
          </template>

          <el-table
            :data="benchmarkRuns"
            v-loading="loadingRuns"
            border
            class="benchmark-table"
            style="width: 100%"
          >
            <el-table-column prop="run_name" label="评测名称" min-width="180" />
            <el-table-column prop="provider" label="Provider" width="100" />
            <el-table-column prop="total_count" label="总数" width="80" />
            <el-table-column label="Accuracy" width="100">
              <template #default="{ row }">
                {{ formatPercent(row.accuracy) }}
              </template>
            </el-table-column>
            <el-table-column label="Precision" width="100">
              <template #default="{ row }">
                {{ formatPercent(row.precision) }}
              </template>
            </el-table-column>
            <el-table-column label="Recall" width="100">
              <template #default="{ row }">
                {{ formatPercent(row.recall) }}
              </template>
            </el-table-column>
            <el-table-column label="F1" width="90">
              <template #default="{ row }">
                {{ formatPercent(row.f1_score) }}
              </template>
            </el-table-column>
            <el-table-column label="时间" min-width="170">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link @click="handleViewDetail(row)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty
            v-if="!loadingRuns && benchmarkRuns.length === 0"
            description="暂无评测记录"
            class="empty-block"
          />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="card-title">评测详情</div>
          </template>

          <div v-if="selectedRunDetail">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="评测名称">
                {{ selectedRunDetail.run_name }}
              </el-descriptions-item>
              <el-descriptions-item label="数据集ID">
                {{ selectedRunDetail.dataset_id }}
              </el-descriptions-item>
              <el-descriptions-item label="Provider">
                {{ selectedRunDetail.provider }}
              </el-descriptions-item>
              <el-descriptions-item label="总样本数">
                {{ selectedRunDetail.total_count }}
              </el-descriptions-item>
              <el-descriptions-item label="安全样本数">
                {{ selectedRunDetail.safe_count }}
              </el-descriptions-item>
              <el-descriptions-item label="违规样本数">
                {{ selectedRunDetail.unsafe_count }}
              </el-descriptions-item>
              <el-descriptions-item label="TP / TN / FP / FN">
                {{ selectedRunDetail.tp }} /
                {{ selectedRunDetail.tn }} /
                {{ selectedRunDetail.fp }} /
                {{ selectedRunDetail.fn }}
              </el-descriptions-item>
              <el-descriptions-item label="Accuracy">
                {{ formatPercent(selectedRunDetail.accuracy) }}
              </el-descriptions-item>
              <el-descriptions-item label="Precision">
                {{ formatPercent(selectedRunDetail.precision) }}
              </el-descriptions-item>
              <el-descriptions-item label="Recall">
                {{ formatPercent(selectedRunDetail.recall) }}
              </el-descriptions-item>
              <el-descriptions-item label="F1 Score">
                {{ formatPercent(selectedRunDetail.f1_score) }}
              </el-descriptions-item>
              <el-descriptions-item label="平均推理耗时">
                {{ selectedRunDetail.avg_inference_time_ms }} ms
              </el-descriptions-item>
            </el-descriptions>

            <div class="wrong-box">
              <div class="wrong-header">
                <div class="wrong-title">
                  错误样本（{{ selectedRunDetail.wrong_items?.length || 0 }}）
                </div>
              </div>

              <el-table
                :data="selectedRunDetail.wrong_items || []"
                border
                size="small"
                max-height="320"
                class="wrong-table"
              >
                <el-table-column prop="filename" label="文件名" min-width="140" />
                <el-table-column label="真值" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.ground_truth_is_safe ? 'success' : 'danger'">
                      {{ row.ground_truth_is_safe ? '安全' : '违规' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="预测" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.predicted_is_safe ? 'success' : 'danger'">
                      {{ row.predicted_is_safe ? '安全' : '违规' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="耗时" width="80">
                  <template #default="{ row }">
                    {{ row.inference_time_ms || 0 }} ms
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <el-empty v-else description="请选择一条评测记录查看详情" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchDatasets,
  runBenchmark,
  fetchBenchmarkRuns,
  fetchBenchmarkRunDetail,
} from '../api/benchmark'

const datasets = ref([])
const benchmarkRuns = ref([])
const selectedRunDetail = ref(null)

const loadingRuns = ref(false)
const running = ref(false)

const runForm = ref({
  dataset_id: null,
  run_name: '',
})

const summary = computed(() => {
  return {
    totalRuns: benchmarkRuns.value.length,
  }
})

const selectedMetrics = computed(() => {
  const d = selectedRunDetail.value
  if (!d) {
    return {
      accuracy: '-',
      precision: '-',
      recall: '-',
      f1: '-',
      tp: '-',
      tn: '-',
      wrong: '-',
    }
  }

  return {
    accuracy: formatPercent(d.accuracy),
    precision: formatPercent(d.precision),
    recall: formatPercent(d.recall),
    f1: formatPercent(d.f1_score),
    tp: d.tp ?? 0,
    tn: d.tn ?? 0,
    wrong: (d.wrong_items || []).length,
  }
})

const formatPercent = (value) => {
  const num = Number(value || 0)
  return `${(num * 100).toFixed(2)}%`
}

const formatDateTime = (value) => {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

const loadDatasets = async () => {
  try {
    const res = await fetchDatasets()
    datasets.value = res.data || []
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '获取数据集失败')
  }
}

const loadBenchmarkRuns = async () => {
  loadingRuns.value = true
  try {
    const res = await fetchBenchmarkRuns()
    benchmarkRuns.value = res.data || []
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '获取评测记录失败')
  } finally {
    loadingRuns.value = false
  }
}

const handleRunBenchmark = async () => {
  if (!runForm.value.dataset_id) {
    ElMessage.warning('请先选择数据集')
    return
  }
  if (!runForm.value.run_name.trim()) {
    ElMessage.warning('请先输入评测名称')
    return
  }

  running.value = true
  try {
    const res = await runBenchmark({
      dataset_id: runForm.value.dataset_id,
      run_name: runForm.value.run_name.trim(),
    })

    // 注意：request.js 已经统一 return res.data
    const run = res?.data || null

    ElMessage.success('Benchmark 运行成功')
    await loadBenchmarkRuns()

    if (run && run.id) {
      await handleViewDetail(run)
    }
  } catch (err) {
    console.error('运行 Benchmark 失败：', err)
    ElMessage.error(err?.response?.data?.detail || err?.message || '运行 Benchmark 失败')
  } finally {
    running.value = false
  }
}

const handleViewDetail = async (row) => {
  try {
    const res = await fetchBenchmarkRunDetail(row.id)
    selectedRunDetail.value = res?.data || null
  } catch (err) {
    console.error('获取评测详情失败：', err)
    ElMessage.error(err?.response?.data?.detail || err?.message || '获取评测详情失败')
  }
}

onMounted(async () => {
  await loadDatasets()
  await loadBenchmarkRuns()
})
</script>

<style scoped>
.benchmark-page {
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

.panel-card,
.stat-card {
  border: none;
  border-radius: 14px;
}

.run-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.form-tip {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fafc;
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}

.stat-card :deep(.el-card__body) {
  padding: 20px 18px 16px;
}

.stat-label {
  font-size: 13px;
  color: #606266;
}

.stat-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.1;
}

.stat-sub {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}

.stat-total {
  border-left: 4px solid #409eff;
}

.stat-accuracy {
  border-left: 4px solid #67c23a;
}

.stat-precision {
  border-left: 4px solid #e6a23c;
}

.stat-recall {
  border-left: 4px solid #f56c6c;
}

.stat-f1 {
  border-left: 4px solid #9c6bff;
}

.stat-tp {
  border-left: 4px solid #2ec7c9;
}

.stat-tn {
  border-left: 4px solid #73c0de;
}

.stat-wrong {
  border-left: 4px solid #ff7875;
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

.benchmark-table :deep(th.el-table__cell),
.wrong-table :deep(th.el-table__cell) {
  background: #f8fafc;
  color: #606266;
  font-weight: 600;
}

.wrong-box {
  margin-top: 16px;
}

.wrong-header {
  margin-bottom: 10px;
}

.wrong-title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
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