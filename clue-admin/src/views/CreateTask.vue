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

      <el-form-item label="规则">
        <el-input
          type="textarea"
          v-model="rulesText"
          placeholder='示例：["图像中出现了人物的生殖器或臀部未被遮挡"]'
          :rows="4"
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
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElLoading, ElMessage } from 'element-plus'
import { createAuditTask, createBatchAuditTasks } from '../api/task'

const router = useRouter()
const route = useRoute()

const mode = ref(route.query.mode === 'batch' ? 'batch' : 'single')
const loading = ref(false)

const singleFileList = ref([])
const singleFile = ref(null)

const batchFiles = ref([])
const folderInputRef = ref(null)

const rulesText = ref('["图像中出现了人物的生殖器或臀部未被遮挡"]')

const isBatchMode = computed(() => mode.value === 'batch')

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

function formatBatchLoadingText(total, seconds) {
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  const timeText =
    minutes > 0 ? `${minutes}分${remainSeconds}秒` : `${remainSeconds}秒`

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

    ElMessage.success(
      `批量审核完成：成功 ${data.success_count || 0} 条，失败 ${data.fail_count || 0} 条`
    )
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
</script>