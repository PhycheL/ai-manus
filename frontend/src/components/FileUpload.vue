<template>
  <div class="file-upload-container">
    <!-- 上传区域 -->
    <div 
      class="upload-area"
      :class="{ 'drag-over': isDragOver, 'uploading': isUploading }"
      @drop="handleDrop"
      @dragover.prevent="handleDragOver"
      @dragleave="handleDragLeave"
      @click="triggerFileSelect"
    >
      <div class="upload-content">
        <div v-if="!isUploading" class="upload-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </div>
        <div v-else class="upload-loading">
          <div class="spinner"></div>
        </div>
        
        <div class="upload-text">
          <p v-if="!isUploading" class="primary-text">
            {{ isDragOver ? '释放文件进行上传' : '点击选择文件或拖拽文件到此处' }}
          </p>
          <p v-else class="primary-text">正在上传文件...</p>
          <p class="secondary-text">
            支持所有文件格式（包括未知类型），最大 50MB
          </p>
        </div>
      </div>
      
      <!-- 上传进度 -->
      <div v-if="uploadProgress > 0" class="progress-bar">
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
    </div>
    
    <!-- 文件输入 -->
    <input
      ref="fileInput"
      type="file"
      multiple
      :accept="acceptedTypes"
      @change="handleFileSelect"
      style="display: none"
    />
    
    <!-- 已上传文件列表 -->
    <div v-if="uploadedFiles.length > 0" class="uploaded-files">
      <h4>已上传的文件</h4>
      <div class="file-list">
        <div 
          v-for="file in uploadedFiles" 
          :key="file.file_id"
          class="file-item"
          @click="$emit('file-selected', file)"
        >
          <div class="file-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
            </svg>
          </div>
          <div class="file-info">
            <div class="file-name">{{ file.filename }}</div>
            <div class="file-meta">
              {{ formatFileSize(file.size) }} • {{ file.mime_type }}
            </div>
            <div v-if="isUnknownFileType(file)" class="unknown-file-actions">
              <button 
                class="analyze-btn"
                @click.stop="analyzeUnknownFileType(file.file_id)"
                :disabled="file.analyzing"
                title="分析文件类型"
              >
                {{ file.analyzing ? '分析中...' : '智能分析' }}
              </button>
            </div>
          </div>
          <button 
            class="delete-btn"
            @click.stop="deleteFile(file.file_id)"
            title="删除文件"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="m19,6v14a2,2 0 0,1-2,2H7a2,2 0 0,1-2-2V6m3,0V4a2,2 0 0,1,2-2h4a2,2 0 0,1,2,2v2"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- 错误信息 -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { API_CONFIG } from '../api/client'

export default {
  name: 'FileUpload',
  props: {
    sessionId: {
      type: String,
      required: true
    }
  },
  emits: ['file-uploaded', 'file-selected', 'file-analyzed'],
  setup(props, { emit }) {
    const isDragOver = ref(false)
    const isUploading = ref(false)
    const uploadProgress = ref(0)
    const errorMessage = ref('')
    const uploadedFiles = ref([])
    const fileInput = ref(null)
    
    // 支持的文件类型
    const acceptedTypes = '.txt,.csv,.json,.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.py,.js,.html,.css,.java,.cpp,.c,.xml,.md'
    
    // 最大文件大小 (50MB)
    const maxFileSize = 50 * 1024 * 1024
    
    // 获取后端地址
    const getBackendUrl = () => {
      return API_CONFIG.host || 'http://localhost:8000'
    }
    
    // 触发文件选择
    const triggerFileSelect = () => {
      if (!isUploading.value && fileInput.value) {
        fileInput.value.click()
      }
    }
    
    // 处理拖拽事件
    const handleDragOver = (e) => {
      e.preventDefault()
      isDragOver.value = true
    }
    
    const handleDragLeave = () => {
      isDragOver.value = false
    }
    
    const handleDrop = (e) => {
      e.preventDefault()
      isDragOver.value = false
      
      const files = e.dataTransfer?.files
      if (files) {
        uploadFiles(Array.from(files))
      }
    }
    
    // 处理文件选择
    const handleFileSelect = (e) => {
      const target = e.target
      const files = target.files
      if (files) {
        uploadFiles(Array.from(files))
      }
    }
    
    // 验证文件
    const validateFile = (file) => {
      if (file.size > maxFileSize) {
        return `文件 "${file.name}" 超过 50MB 大小限制`
      }
      
      // 已知支持的文件扩展名
      const knownExtensions = [
        '.txt', '.csv', '.json', '.pdf', '.doc', '.docx', 
        '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.gif',
        '.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.xml', '.md'
      ]
      
      const fileName = file.name.toLowerCase()
      const isKnownType = knownExtensions.some(ext => fileName.endsWith(ext))
      
      // 对于未知文件类型，只提示但不阻止上传
      if (!isKnownType) {
        console.log(`未知文件类型，将进行智能分析: "${file.name}"`)
      }
      
      // 所有文件都允许上传（除了大小限制）
      return null
    }
    
    // 上传文件
    const uploadFiles = async (files) => {
      if (isUploading.value) return
      
      errorMessage.value = ''
      
      for (const file of files) {
        const error = validateFile(file)
        if (error) {
          errorMessage.value = error
          return
        }
      }
      
      isUploading.value = true
      uploadProgress.value = 0
      
      try {
        const backendUrl = getBackendUrl()
        
        for (let i = 0; i < files.length; i++) {
          const file = files[i]
          const formData = new FormData()
          formData.append('file', file)
          
          const response = await axios.post(
            `${backendUrl}/sessions/${props.sessionId}/files/upload`,
            formData,
            {
              headers: {
                'Content-Type': 'multipart/form-data'
              },
              onUploadProgress: (progressEvent) => {
                if (progressEvent.total) {
                  const fileProgress = (progressEvent.loaded / progressEvent.total) * 100
                  uploadProgress.value = ((i * 100) + fileProgress) / files.length
                }
              }
            }
          )
          
          if (response.data.success) {
            const uploadedFile = response.data.data
            uploadedFiles.value.push(uploadedFile)
            emit('file-uploaded', uploadedFile)
          } else {
            throw new Error(response.data.message || '上传失败')
          }
        }
        
        uploadProgress.value = 100
        
        if (fileInput.value) {
          fileInput.value.value = ''
        }
        
      } catch (error) {
        console.error('文件上传失败:', error)
        errorMessage.value = error.message || '文件上传失败'
      } finally {
        isUploading.value = false
      }
    }
    
    // 删除文件
    const deleteFile = async (fileId) => {
      try {
        const backendUrl = getBackendUrl()
        
        const response = await axios.delete(`${backendUrl}/sessions/${props.sessionId}/files/batch`, {
          data: {
            file_ids: [fileId]
          }
        })
        
        if (response.data.success) {
          uploadedFiles.value = uploadedFiles.value.filter(f => f.file_id !== fileId)
        } else {
          throw new Error(response.data.message || '删除失败')
        }
      } catch (error) {
        console.error('删除文件失败:', error)
        errorMessage.value = error.message || '删除文件失败'
      }
    }
    
    // 加载已上传的文件
    const loadUploadedFiles = async () => {
      try {
        const backendUrl = getBackendUrl()
        const response = await axios.get(`${backendUrl}/sessions/${props.sessionId}/history`)
        
        if (response.data.success) {
          uploadedFiles.value = response.data.data.files || []
        }
      } catch (error) {
        console.error('加载文件列表失败:', error)
      }
    }
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    // 判断是否为未知文件类型
    const isUnknownFileType = (file) => {
      const knownMimeTypes = [
        'application/pdf', 'application/msword', 
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain', 'text/html', 'text/markdown',
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
        'application/json', 'application/xml', 'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed'
      ]
      
      return file.mime_type === 'application/octet-stream' || 
             !knownMimeTypes.includes(file.mime_type)
    }
    
    // 分析未知文件类型
    const analyzeUnknownFileType = async (fileId) => {
      try {
        const backendUrl = getBackendUrl()
        
        const file = uploadedFiles.value.find(f => f.file_id === fileId)
        if (file) {
          file.analyzing = true
        }
        
        const response = await axios.post(
          `${backendUrl}/sessions/${props.sessionId}/files/${fileId}/analyze-unknown-type`
        )
        
        if (response.data.success) {
          const analysisResult = response.data.data
          emit('file-analyzed', { fileId, analysisResult })
          
          // 更新文件信息
          const file = uploadedFiles.value.find(f => f.file_id === fileId)
          if (file) {
            file.analyzing = false
            file.analysis_result = analysisResult
          }
        } else {
          throw new Error(response.data.message || '分析失败')
        }
      } catch (error) {
        console.error('分析文件类型失败:', error)
        errorMessage.value = error.message || '分析文件类型失败'
        
        // 重置分析状态
        const file = uploadedFiles.value.find(f => f.file_id === fileId)
        if (file) {
          file.analyzing = false
        }
      }
    }
    
    // 获取文件历史
    const fetchFileHistory = async () => {
      try {
        const backendUrl = getBackendUrl()
        const sessionId = 'current-session'
        
        const response = await axios.get(`${backendUrl}/sessions/${sessionId}/history`)
        
        if (response.data.success) {
          uploadedFiles.value = response.data.data.files
        } else {
          throw new Error(response.data.message || '获取文件历史失败')
        }
      } catch (error) {
        console.error('获取文件历史失败:', error)
        errorMessage.value = error.message || '获取文件历史失败'
      }
    }
    
    // 搜索文件
    const searchFiles = async (query) => {
      try {
        const backendUrl = getBackendUrl()
        const sessionId = 'current-session'
        
        const response = await axios.get(`${backendUrl}/sessions/${sessionId}/files/search`, {
          params: { q: query }
        })
        
        if (response.data.success) {
          uploadedFiles.value = response.data.data.results
        } else {
          throw new Error(response.data.message || '搜索文件失败')
        }
      } catch (error) {
        console.error('搜索文件失败:', error)
        errorMessage.value = error.message || '搜索文件失败'
      }
    }
    
    // 获取文件详情
    const getFileDetail = async (fileId) => {
      try {
        const backendUrl = getBackendUrl()
        const sessionId = 'current-session'
        
        const response = await axios.get(`${backendUrl}/sessions/${sessionId}/files/${fileId}/detail`)
        
        if (response.data.success) {
          return response.data.data
        } else {
          throw new Error(response.data.message || '获取文件详情失败')
        }
      } catch (error) {
        console.error('获取文件详情失败:', error)
        errorMessage.value = error.message || '获取文件详情失败'
        return null
      }
    }
    
    onMounted(() => {
      loadUploadedFiles()
    })
    
    return {
      isDragOver,
      isUploading,
      uploadProgress,
      errorMessage,
      uploadedFiles,
      fileInput,
      acceptedTypes,
      triggerFileSelect,
      handleDragOver,
      handleDragLeave,
      handleDrop,
      handleFileSelect,
      deleteFile,
      formatFileSize,
      isUnknownFileType,
      analyzeUnknownFileType,
      fetchFileHistory,
      searchFiles,
      getFileDetail
    }
  }
}
</script>

<style scoped>
.file-upload-container {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: #fafafa;
  position: relative;
  overflow: hidden;
}

.upload-area:hover {
  border-color: #3b82f6;
  background-color: #f0f9ff;
}

.upload-area.drag-over {
  border-color: #3b82f6;
  background-color: #eff6ff;
  transform: scale(1.02);
}

.upload-area.uploading {
  pointer-events: none;
  opacity: 0.7;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon {
  color: #6b7280;
}

.upload-loading .spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.upload-text {
  color: #374151;
}

.primary-text {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 8px 0;
}

.secondary-text {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  background-color: #e5e7eb;
}

.progress-fill {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.3s ease;
}

.uploaded-files {
  margin-top: 24px;
}

.uploaded-files h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.file-item:hover {
  border-color: #3b82f6;
  background-color: #f0f9ff;
}

.file-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.delete-btn {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
  flex-shrink: 0;
}

.delete-btn:hover {
  background-color: #fee2e2;
}

.error-message {
  margin-top: 12px;
  padding: 12px;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 14px;
}

.unknown-file-actions {
  margin-top: 8px;
}

.analyze-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.analyze-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
  transform: translateY(-1px);
}

.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style> 