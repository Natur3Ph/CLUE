<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;gap:12px;">
        <el-button @click="goBack">返回</el-button>
        <span>{{ isBatchMode ? '批量创建审核任务' : '创建审核任务' }}</span>
      </div>
    </template>

    <el-form label-width="100px">
      <el-form-item label="任务模式">
        <el-radio-group v-model="mode">
          <el-radio-button label="single">单张审核</el-radio-button>
          <el-radio-button label="batch">批量审核</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="!isBatchMode" label="上传图片">
        <el-upload
          :auto-upload="false"
          :on-change="handleSingleChange"
          :limit="1"
          :file-list="singleFileList"
        >
          <el-button type="primary">选择图片</el-button>
        </el-upload>
      </el-form-item>

      <el-form-item v-else label="选择文件夹">
        <div style="display:flex;flex-direction:column;gap:8px;">
          <input
            ref="folderInputRef"
            type="file"
            multiple
            webkitdirectory
            @change="handleFolderChange"
          />
          <div style="font-size:12px;color:#666;">
            已选择 {{ batchFiles.length }} 张图片
          </div>

          <div
            v-if="batchFiles.length > 0"
            style="max-height:180px;overflow:auto;border:1px solid #eee;padding:8px;border-radius:4px;background:#fafafa;"
          >
            <div
              v-for="(f, idx) in batchFiles"
              :key="idx"
              style="font-size:12px;line-height:1.8;color:#333;"
            >
              {{ f.webkitRelativePath || f.name }}
            </div>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="选择规则">
        <div style="width:100%;display:flex;flex-direction:column;gap:10px;">
          <div style="display:flex;gap:8px;align-items:center;">
            <el-button size="small" @click="loadRules">刷新规则</el-button>
            <el-button size="small" @click="selectAllRules" :disabled="ruleOptions.length === 0">
              全选
            </el-button>
            <el-button size="small" @click="clearSelectedRules" :disabled="selectedRuleIds.length === 0">
              清空
            </el-button>
            <span style="font-size:12px;color:#666;">
              已选 {{ selectedRuleIds.length }} 条启用规则
            </span>
          </div>

          <el-select
            v-model="selectedRuleIds"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择参与审核的规则"
            style="width:100%;"
            @change="syncRulesTextFromSelection"
          >
            <el-option
              v-for="item in ruleOptions"
              :key="item.id"
              :label="`${item.rule_name}｜${item.original_rule}`"
              :value="item.id"
            />
          </el-select>

          <div
            v-if="selectedRules.length > 0"
            style="border:1px solid #eee;border-radius:6px;padding:10px;background:#fafafa;"
          >
            <div
              v-for="item in selectedRules"
              :key="item.id"
              style="padding:6px 0;border-bottom:1px dashed #e8e8e8;"
            >
              <div style="font-weight:600;color:#333;">{{ item.rule_name }}</div>
              <div style="font-size:13px;color:#666;">{{ item.original_rule }}</div>
              <div
                v-if="item.preconditions && item.preconditions.length > 0"
                style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px;"
              >
                <el-tag
                  v-for="(p, idx) in item.preconditions"
                  :key="idx"
                  size="small"
                  type="info"
                >
                  {{ p }}
                </el-tag>
              </div>
            </div>
          </div>

          <el-empty v-if="!rulesLoading && ruleOptions.length === 0" description="暂无启用规则" />
        </div>
      </el-form-item>

      <el-form-item label="规则JSON">
        <el-input
          type="textarea"
          v-model="rulesText"
          placeholder='这里会自动生成提交给后端的规则 JSON 数组'
          :rows="5"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="success" @click="submit" :loading="loading">
          {{ isBatchMode ? '开始批量审核' : '提交审核' }}
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElLoading, ElMessage } from 'element-plus'
import { createAuditTask, createBatchAuditTasks } from '../api/task'
import { fetchRules } from '../api/rule'

const router = useRouter()
const route = useRoute()

const mode = ref(route.query.mode === 'batch' ? 'batch' : 'single')
const loading = ref(false)
const rulesLoading = ref(false)

const singleFileList = ref([])
const singleFile = ref(null)

const batchFiles = ref([])
const folderInputRef = ref(null)

const ruleOptions = ref([])
const selectedRuleIds = ref([])
const rulesText = ref('[]')

const isBatchMode = computed(() => mode.value === 'batch')

const selectedRules = computed(() => {
  return ruleOptions.value.filter(item => selectedRuleIds.value.includes(item.id))
})

watch(mode, (val) => {
  if (val === 'single') {
    batchFiles.value = []
    if (folderInputRef.value) folderInputRef.value.value = ''
  } else {
    singleFile.value = null
    singleFileList.value = []
  }
})

function handleSingleChange(uploadFile) {
  singleFile.value = uploadFile.raw
  singleFileList.value = [uploadFile]
}

function handleFolderChange(e) {
  const files = Array.from(e.target.files || [])
  const imageFiles = files.filter((f) => {
    const name = (f.name || '').toLowerCase()
    return (
      (f.type && f.type.startsWith('image/')) ||
      name.endsWith('.jpg') ||
      name.endsWith('.jpeg') ||
      name.endsWith('.png') ||
      name.endsWith('.webp') ||
      name.endsWith('.gif') ||
      name.endsWith('.bmp')
    )
  })
  batchFiles.value = imageFiles
}

function goBack() {
  router.push('/tasks')
}

function unwrap(res) {
  if (!res) return null
  if (res.status && res.data !== undefined) return res.data
  if (res.data && res.data.data !== undefined) return res.data.data
  if (res.data !== undefined) return res.data
  return res
}

async function loadRules() {
  rulesLoading.value = true
  try {
    const res = await fetchRules(false) // 只拉启用规则
    const data = unwrap(res) || []
    ruleOptions.value = Array.isArray(data) ? data : []

    if (ruleOptions.value.length > 0 && selectedRuleIds.value.length === 0) {
      selectedRuleIds.value = [ruleOptions.value[0].id]
      syncRulesTextFromSelection()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载规则失败')
  } finally {
    rulesLoading.value = false
  }
}

function syncRulesTextFromSelection() {
  const rules = selectedRules.value.map(item => item.original_rule)
  rulesText.value = JSON.stringify(rules, null, 2)
}

function selectAllRules() {
  selectedRuleIds.value = ruleOptions.value.map(item => item.id)
  syncRulesTextFromSelection()
}

function clearSelectedRules() {
  selectedRuleIds.value = []
  rulesText.value = '[]'
}

function formatBatchLoadingText(total, seconds) {
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  const timeText = minutes > 0 ? `${minutes}分${remainSeconds}秒` : `${remainSeconds}秒`

  return `
系统正在逐张调用模型进行批量审核，请耐心等待…

本次提交图片：${total} 张
已等待时间：${timeText}

提示：
1. 图片数量较多时，审核可能持续较长时间
2. 审核过程中请尽量不要关闭页面或刷新浏览器
3. 审核完成后系统会自动返回任务列表
  `.trim()
}

async function submit() {
  if (selectedRuleIds.value.length === 0) {
    ElMessage.warning('请至少选择一条规则')
    return
  }

  if (!rulesText.value || rulesText.value === '[]') {
    ElMessage.warning('规则内容为空')
    return
  }

  if (!isBatchMode.value) {
    if (!singleFile.value) {
      ElMessage.warning('请先选择图片')
      return
    }

    loading.value = true
    let loadingInstance = null

    try {
      loadingInstance = ElLoading.service({
        lock: true,
        text: '系统正在提交审核任务，请稍候...',
        background: 'rgba(0, 0, 0, 0.45)',
      })

      const formData = new FormData()
      formData.append('file', singleFile.value)
      formData.append('rules', rulesText.value)

      await createAuditTask(formData)
      ElMessage.success('任务创建成功')
      router.push('/tasks')
    } catch (e) {
      console.error(e)
      ElMessage.error(e?.response?.data?.detail || e?.message || '提交失败，请检查后端是否正常')
    } finally {
      loading.value = false
      if (loadingInstance) loadingInstance.close()
    }
    return
  }

  if (batchFiles.value.length === 0) {
    ElMessage.warning('请先选择包含图片的文件夹')
    return
  }

  loading.value = true
  let loadingInstance = null
  let timer = null
  let seconds = 0

  try {
    loadingInstance = ElLoading.service({
      lock: true,
      text: formatBatchLoadingText(batchFiles.value.length, seconds),
      background: 'rgba(0, 0, 0, 0.45)',
    })

    timer = setInterval(() => {
      seconds += 1
      const textNode = loadingInstance?.$el?.querySelector('.el-loading-text')
      if (textNode) {
        textNode.innerText = formatBatchLoadingText(batchFiles.value.length, seconds)
      }
    }, 1000)

    const formData = new FormData()
    batchFiles.value.forEach((f) => {
      formData.append('files', f)
    })
    formData.append('rules', rulesText.value)

    const res = await createBatchAuditTasks(formData)
    const data = res?.data || {}

    ElMessage.success(`批量审核完成：成功 ${data.success_count || 0} 条，失败 ${data.fail_count || 0} 条`)
    router.push('/tasks')
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '批量提交失败，请检查后端是否正常')
  } finally {
    loading.value = false
    if (timer) clearInterval(timer)
    if (loadingInstance) loadingInstance.close()
  }
}

onMounted(() => {
  loadRules()
})
</script>