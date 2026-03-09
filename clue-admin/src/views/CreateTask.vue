<template>
  <el-card>
    <template #header>
      <div style="display:flex;align-items:center;gap:12px;">
        <el-button @click="goBack">返回</el-button>
        <span>创建审核任务</span>
      </div>
    </template>

    <el-form label-width="100px">
      <el-form-item label="上传图片">
        <el-upload
          :auto-upload="false"
          :on-change="handleChange"
          :limit="1"
          :file-list="fileList"
        >
          <el-button type="primary">选择图片</el-button>
        </el-upload>
      </el-form-item>

      <el-form-item label="规则">
        <el-input
          type="textarea"
          v-model="rulesText"
          placeholder='示例：["图像中出现了人物的生殖器或臀部未被遮挡"]'
        />
      </el-form-item>

      <el-form-item>
        <el-button type="success" @click="submit" :loading="loading">
          提交审核
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'

const router = useRouter()

const fileList = ref([])
const file = ref(null)
const rulesText = ref('["图像中出现了人物的生殖器或臀部未被遮挡"]')
const loading = ref(false)

function handleChange(uploadFile) {
  file.value = uploadFile.raw
  fileList.value = [uploadFile]
}

function goBack() {
  router.push('/tasks')
}

async function submit() {
  if (!file.value) {
    alert('请先选择图片')
    return
  }

  loading.value = true

  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('rules', rulesText.value)

  try {
    await request.post('/api/moderate', formData)
    alert('任务创建成功')
    router.push('/tasks')
  } catch (e) {
    console.error(e)
    alert('提交失败，请检查后端是否正常')
  } finally {
    loading.value = false
  }
}
</script>