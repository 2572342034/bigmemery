<template>
  <div class="knowledge-page">
    <aside class="knowledge-sidebar">
      <section class="hero-card">
        <p class="eyebrow">Knowledge Hub</p>
        <h1>企业知识库中心</h1>
        <p class="hero-copy">
          以文件为单位管理知识资产。当前文件先存本地磁盘，后续可无缝切换到阿里 OSS。
        </p>
        <div class="hero-actions">
          <el-button type="primary" @click="$emit('back-chat')">返回智能对话</el-button>
          <el-button @click="$emit('logout')">退出登录</el-button>
        </div>
      </section>

      <section class="stats-card">
        <div class="stat-item">
          <span>资料总数</span>
          <strong>{{ documents.length }}</strong>
        </div>
        <div class="stat-item">
          <span>可直接引用</span>
          <strong>{{ readyCount }}</strong>
        </div>
        <div class="stat-item">
          <span>仅关键词检索</span>
          <strong>{{ keywordOnlyCount }}</strong>
        </div>
        <div class="stat-item">
          <span>本地存储体量</span>
          <strong>{{ totalSizeLabel }}</strong>
        </div>
      </section>

      <section class="sidebar-card">
        <p class="eyebrow">Upload Tips</p>
        <ul>
          <li>建议优先上传制度、SOP、FAQ、产品说明、项目纪要等原始资料。</li>
          <li>支持 `txt / md / csv / json / pdf / docx / xlsx`。</li>
          <li>上传后系统会提取文本、写入 SQLite 元数据，并同步到 Chroma 检索索引。</li>
        </ul>
      </section>
    </aside>

    <main class="knowledge-main">
      <header class="page-header">
        <div>
          <p class="eyebrow">File-Centric RAG</p>
          <h2>上传知识文件</h2>
          <span>统一沉淀可检索、可追溯、可扩展到对象存储的企业知识资产。</span>
        </div>
        <div class="page-actions">
          <el-select v-model="uploadSource" class="source-select" placeholder="资料分类">
            <el-option label="规章制度" value="规章制度" />
            <el-option label="产品资料" value="产品资料" />
            <el-option label="项目文档" value="项目文档" />
            <el-option label="FAQ / 工单" value="FAQ / 工单" />
            <el-option label="会议纪要" value="会议纪要" />
            <el-option label="其他资料" value="其他资料" />
          </el-select>
        </div>
      </header>

      <section class="upload-grid">
        <div class="upload-card">
          <el-upload
            drag
            multiple
            :show-file-list="false"
            :http-request="handleUploadRequest"
            accept=".txt,.md,.markdown,.csv,.json,.log,.pdf,.docx,.xlsx"
          >
            <div class="upload-dropzone">
              <strong>拖拽文件到这里，或点击上传</strong>
              <span>按文件入库，当前落地到本地存储，后续可平移到 OSS。</span>
            </div>
          </el-upload>
        </div>

        <div class="status-card">
          <p class="eyebrow">Storage Strategy</p>
          <h3>本地文件存储</h3>
          <p>
            上传的原始文件会先保存到服务端本地目录，并保留文件元数据，方便后续替换为对象存储。
          </p>
          <div class="status-list">
            <span>当前模式：Local Disk</span>
            <span>后续扩展：Aliyun OSS</span>
            <span>索引方式：Hybrid RAG + Chroma</span>
          </div>
        </div>
      </section>

      <section class="library-card">
        <div class="toolbar">
          <div class="toolbar-group">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索标题、文件名、来源"
              clearable
            />
          </div>
          <div class="toolbar-group toolbar-group--end">
            <el-select v-model="statusFilter" placeholder="索引状态" clearable>
              <el-option label="全部状态" value="" />
              <el-option label="已就绪" value="ready" />
              <el-option label="关键词检索" value="keyword_only" />
            </el-select>
          </div>
        </div>

        <el-table
          :data="filteredDocuments"
          v-loading="loading"
          empty-text="还没有上传知识文件"
          class="knowledge-table"
          :row-class-name="() => 'knowledge-row'"
        >
          <el-table-column label="文件 / 标题" min-width="260">
            <template #default="{ row }">
              <div class="file-cell">
                <strong>{{ primaryFileLabel(row) }}</strong>
                <span>{{ secondaryFileLabel(row) }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="来源分类" min-width="120">
            <template #default="{ row }">
              <el-tag effect="plain">{{ row.source }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="状态" min-width="120">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.index_status)">
                {{ statusText(row.index_status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="大小" width="110">
            <template #default="{ row }">
              <span class="metric-text">{{ formatBytes(row.file_size) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="Chunks" width="90" align="center">
            <template #default="{ row }">
              <span class="metric-text">{{ row.chunk_count }}</span>
            </template>
          </el-table-column>

          <el-table-column label="创建时间" min-width="150">
            <template #default="{ row }">
              <span>{{ formatTime(row.created_at) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="238">
            <template #default="{ row }">
              <div class="row-actions">
                <button
                  type="button"
                  class="action-chip action-chip--primary"
                  @click="openPreview(row.id)"
                >
                  查看详情
                </button>
                <button
                  type="button"
                  class="action-chip action-chip--secondary"
                  @click="handleDownload(row)"
                >
                  下载
                </button>
                <button
                  type="button"
                  class="action-chip action-chip--danger"
                  @click="handleDelete(row.id)"
                >
                  删除
                </button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </main>

    <el-drawer
      v-model="previewVisible"
      title="知识文件详情"
      direction="rtl"
      size="560px"
    >
      <template v-if="activeDocument">
        <div class="preview-meta">
          <div class="meta-item">
            <span>文件名</span>
            <strong>{{ activeDocument.file_name || activeDocument.title }}</strong>
          </div>
          <div class="meta-item">
            <span>来源分类</span>
            <strong>{{ activeDocument.source }}</strong>
          </div>
          <div class="meta-item">
            <span>索引状态</span>
            <strong>{{ statusText(activeDocument.index_status) }}</strong>
          </div>
          <div class="meta-item">
            <span>本地路径</span>
            <strong>{{ activeDocument.file_path || '手工录入' }}</strong>
          </div>
        </div>

        <div class="preview-content">
          <h4>提取内容</h4>
          <pre>{{ activeDocument.content }}</pre>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteKnowledge,
  downloadKnowledgeFile,
  getKnowledge,
  listKnowledge,
  uploadKnowledgeFile,
} from '../api/knowledge'

defineProps({
  currentUser: {
    type: Object,
    required: true,
  },
})

defineEmits(['back-chat', 'logout'])

const loading = ref(false)
const previewVisible = ref(false)
const documents = ref([])
const activeDocument = ref(null)
const searchKeyword = ref('')
const statusFilter = ref('')
const uploadSource = ref('规章制度')

const readyCount = computed(() =>
  documents.value.filter((item) => item.index_status === 'ready').length,
)
const keywordOnlyCount = computed(() =>
  documents.value.filter((item) => item.index_status === 'keyword_only').length,
)
const totalSizeLabel = computed(() =>
  formatBytes(documents.value.reduce((sum, item) => sum + (item.file_size || 0), 0)),
)
const filteredDocuments = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return documents.value.filter((item) => {
    const hitKeyword =
      !keyword
      || [item.title, item.file_name, item.source]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(keyword))
    const hitStatus = !statusFilter.value || item.index_status === statusFilter.value
    return hitKeyword && hitStatus
  })
})

function primaryFileLabel(row) {
  return row.file_name || row.title || '未命名文件'
}

function secondaryFileLabel(row) {
  const fileName = row.file_name || ''
  const normalizedTitle = (row.title || '').trim()
  const normalizedFileStem = fileName.includes('.')
    ? fileName.slice(0, fileName.lastIndexOf('.')).trim()
    : fileName.trim()

  if (normalizedTitle && normalizedTitle !== fileName && normalizedTitle !== normalizedFileStem) {
    return normalizedTitle
  }

  return `${row.source || '未分类'} · ${formatBytes(row.file_size)}`
}

function statusText(status) {
  if (status === 'ready') return '已就绪'
  if (status === 'keyword_only') return '关键词检索'
  if (status === 'processing') return '处理中'
  return status || '未知'
}

function statusTagType(status) {
  if (status === 'ready') return 'success'
  if (status === 'keyword_only') return 'warning'
  if (status === 'processing') return 'info'
  return ''
}

function formatBytes(value = 0) {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  const size = value / 1024 ** index
  return `${size.toFixed(size >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadDocuments() {
  loading.value = true
  try {
    documents.value = await listKnowledge()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '知识库加载失败')
  } finally {
    loading.value = false
  }
}

async function handleUploadRequest(option) {
  const file = option.file
  try {
    await uploadKnowledgeFile({
      file,
      source: uploadSource.value,
      onUploadProgress(event) {
        if (!event.total) return
        option.onProgress?.({ percent: Math.round((event.loaded / event.total) * 100) })
      },
    })
    option.onSuccess?.({}, file)
    ElMessage.success(`${file.name} 已上传并入库`)
    await loadDocuments()
  } catch (error) {
    option.onError?.(error)
    ElMessage.error(error.response?.data?.detail || error.message || '上传失败')
  }
}

async function openPreview(documentId) {
  try {
    activeDocument.value = await getKnowledge(documentId)
    previewVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '读取详情失败')
  }
}

async function handleDownload(row) {
  try {
    const blob = await downloadKnowledgeFile(row.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = row.file_name || `${row.title}.txt`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '下载失败')
  }
}

async function handleDelete(documentId) {
  try {
    await ElMessageBox.confirm(
      '删除后会同步移除本地文件、SQLite 元数据以及 Chroma 向量索引。是否继续？',
      '删除知识文件',
      { type: 'warning' },
    )
    await deleteKnowledge(documentId)
    if (activeDocument.value?.id === documentId) {
      activeDocument.value = null
      previewVisible.value = false
    }
    ElMessage.success('知识文件已删除')
    await loadDocuments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || error.message || '删除失败')
    }
  }
}

onMounted(loadDocuments)
</script>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 20px;
  padding: 20px;
}

.knowledge-sidebar,
.hero-card,
.stats-card,
.sidebar-card,
.page-header,
.upload-card,
.status-card,
.library-card {
  background: rgba(7, 14, 28, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 24px 80px rgba(2, 6, 23, 0.34);
}

.knowledge-sidebar {
  border-radius: 30px;
  padding: 18px;
  display: grid;
  align-content: start;
  gap: 14px;
}

.hero-card,
.stats-card,
.sidebar-card,
.page-header,
.upload-card,
.status-card,
.library-card {
  border-radius: 26px;
  padding: 20px;
}

.eyebrow {
  margin: 0 0 12px;
  color: #38bdf8;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 11px;
  font-weight: 700;
}

.hero-card h1,
.page-header h2 {
  margin: 0;
  color: #f8fafc;
}

.hero-card h1 {
  font-size: 34px;
  line-height: 1.08;
}

.hero-copy,
.status-card p,
.sidebar-card li,
.page-header span {
  color: #94a3b8;
  line-height: 1.75;
}

.hero-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.stats-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.stat-item {
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(15, 23, 42, 0.58));
}

.stat-item span {
  display: block;
  color: #94a3b8;
  font-size: 12px;
}

.stat-item strong {
  display: block;
  margin-top: 8px;
  color: #f8fafc;
  font-size: 22px;
}

.sidebar-card ul {
  margin: 0;
  padding-left: 18px;
  color: #94a3b8;
}

.knowledge-main {
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 18px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: end;
}

.page-actions {
  display: flex;
  gap: 12px;
}

.source-select {
  width: 180px;
}

.upload-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 18px;
}

.upload-dropzone {
  display: grid;
  gap: 8px;
  color: #e2e8f0;
}

.upload-dropzone strong {
  font-size: 18px;
}

.upload-dropzone span,
.status-list span {
  color: #94a3b8;
}

.status-card h3 {
  margin: 0 0 10px;
  color: #f8fafc;
}

.status-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.library-card {
  overflow: hidden;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar-group {
  flex: 1;
}

.toolbar-group--end {
  display: flex;
  justify-content: end;
  flex: 0 0 220px;
}

.knowledge-table :deep(th.el-table__cell) {
  background: rgba(17, 33, 57, 0.96);
  color: #dbe7f5;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
}

.knowledge-table :deep(td.el-table__cell),
.knowledge-table :deep(.el-table__body),
.knowledge-table :deep(.el-table__inner-wrapper::before) {
  background: transparent;
}

.knowledge-table :deep(.el-table) {
  background: transparent;
  color: #dbe7f5;
}

.knowledge-table :deep(.el-table__body-wrapper) {
  background: linear-gradient(180deg, rgba(10, 20, 36, 0.88), rgba(8, 16, 29, 0.82));
}

.knowledge-table :deep(.knowledge-row) {
  background: rgba(255, 255, 255, 0.02);
}

.knowledge-table :deep(.knowledge-row:hover > td.el-table__cell) {
  background: rgba(59, 130, 246, 0.08) !important;
}

.knowledge-table :deep(td.el-table__cell) {
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.file-cell {
  display: grid;
  gap: 4px;
}

.file-cell strong {
  color: #f8fafc;
}

.file-cell span {
  color: #94a3b8;
  font-size: 12px;
}

.metric-text {
  color: #dbe7f5;
  font-variant-numeric: tabular-nums;
}

.row-actions {
  display: flex;
  justify-content: flex-start;
  gap: 8px;
  flex-wrap: nowrap;
}

.action-chip {
  min-width: 64px;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  font-size: 12px;
  line-height: 1;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.action-chip:hover {
  transform: translateY(-1px);
}

.action-chip--primary {
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.92), rgba(29, 78, 216, 0.92));
  border-color: rgba(96, 165, 250, 0.32);
  color: #eff6ff;
}

.action-chip--primary:hover {
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.96), rgba(37, 99, 235, 0.96));
  color: #ffffff;
}

.action-chip--secondary {
  background: rgba(30, 41, 59, 0.88);
  border-color: rgba(100, 116, 139, 0.26);
  color: #e2e8f0;
}

.action-chip--secondary:hover {
  background: rgba(51, 65, 85, 0.96);
  color: #f8fafc;
}

.action-chip--danger {
  background: rgba(127, 29, 29, 0.16);
  border-color: rgba(248, 113, 113, 0.18);
  color: #fecaca;
}

.action-chip--danger:hover {
  background: rgba(153, 27, 27, 0.24);
  color: #fee2e2;
}

.preview-meta {
  display: grid;
  gap: 12px;
}

.meta-item {
  padding: 14px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.meta-item span {
  display: block;
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
}

.meta-item strong {
  color: #0f172a;
  word-break: break-all;
}

.preview-content {
  margin-top: 18px;
}

.preview-content h4 {
  margin: 0 0 10px;
  color: #0f172a;
}

.preview-content pre {
  margin: 0;
  padding: 16px;
  border-radius: 18px;
  background: #eff6ff;
  color: #0f172a;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 60vh;
  overflow: auto;
}

:deep(.el-upload-dragger),
:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.16) inset;
}

:deep(.el-upload-dragger) {
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 22%),
    linear-gradient(180deg, rgba(2, 6, 23, 0.86), rgba(15, 23, 42, 0.74));
  border: 1px dashed rgba(56, 189, 248, 0.3);
}

:deep(.el-drawer) {
  background: #f3f7fb;
}

@media (max-width: 1180px) {
  .knowledge-page {
    grid-template-columns: 1fr;
  }

  .upload-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .page-header,
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-group--end {
    flex: 1;
  }

  .stats-card {
    grid-template-columns: 1fr;
  }

  .hero-actions {
    flex-direction: column;
  }
}
</style>
