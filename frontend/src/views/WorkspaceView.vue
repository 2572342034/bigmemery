<template>
  <div class="workspace-shell">
    <aside class="sidebar">
      <section class="sidebar-card sidebar-card--brand">
        <p class="eyebrow">BigMemery Console</p>
        <h1>Enterprise AI Desk</h1>
        <p class="brand-copy">
          当前登录：{{ currentUser.display_name }}。对话持久化到 SQLite，知识库文件先落本地，后续可平滑切换到 OSS。
        </p>
      </section>

      <section class="sidebar-card sidebar-card--toolbar">
        <div class="toolbar-actions">
          <el-button type="primary" class="toolbar-button" @click="handleCreateConversation">
            新增对话
          </el-button>
          <el-button class="toolbar-button toolbar-button--secondary" @click="$emit('open-knowledge')">
            知识库中心
          </el-button>
        </div>

        <div class="toolbar-field">
          <label>模型切换</label>
          <el-select v-model="selectedModel" placeholder="请选择模型">
            <el-option
              v-for="item in models"
              :key="item"
              :label="shortModelName(item)"
              :value="item"
            />
          </el-select>
        </div>

        <div class="toolbar-meta">
          <div class="meta-chip">
            <span>知识库增强</span>
            <el-switch v-model="useRag" />
          </div>
          <div class="meta-chip">
            <span>流式状态</span>
            <el-tag :type="isStreaming ? 'warning' : 'success'">
              {{ isStreaming ? '生成中' : '空闲' }}
            </el-tag>
          </div>
        </div>
      </section>

      <section class="sidebar-card sidebar-card--history">
        <div class="history-head">
          <strong>历史对话</strong>
          <span>{{ historyCountLabel }}</span>
        </div>

        <div class="history-list">
          <template v-if="conversations.length">
            <article
              v-for="item in conversations"
              :key="item.id"
              class="history-item"
              :class="{ active: item.id === activeConversationId }"
            >
              <button type="button" class="history-item__main" @click="selectConversation(item.id)">
                <div class="history-item__top">
                  <strong>{{ displayConversationTitle(item) }}</strong>
                  <span>{{ formatTime(item.updated_at) }}</span>
                </div>
                <div class="history-item__meta">
                  <small>{{ shortModelName(item.model) }}</small>
                  <small>{{ item.message_count }} 条消息</small>
                </div>
              </button>

              <button
                type="button"
                class="history-item__delete"
                @click="handleDeleteConversation(item.id)"
              >
                删除
              </button>
            </article>
          </template>

          <article v-else class="history-empty">
            <strong>没有匹配的会话</strong>
            <span>试试搜索别的关键词，或创建一个新对话。</span>
          </article>
        </div>
      </section>

      <section class="sidebar-card sidebar-card--footer">
        <p class="eyebrow">Knowledge Ops</p>
        <ul>
          <li>已入库 {{ knowledgeCount }} 份资料</li>
          <li>当前模型：{{ shortModelName(selectedModel) || '-' }}</li>
          <li>检索模式：{{ useRag ? '已开启' : '已关闭' }}</li>
        </ul>
      </section>
    </aside>

    <main class="chat-stage">
      <header class="stage-header">
        <div>
          <p class="eyebrow">Active Conversation</p>
          <h2>{{ activeConversation?.title || '新对话' }}</h2>
          <span>{{ activeConversation?.id || '尚未创建会话' }}</span>
        </div>
        <div class="stage-header__actions">
          <el-button @click="$emit('open-knowledge')">前往知识库中心</el-button>
          <el-button @click="$emit('logout')">退出登录</el-button>
        </div>
      </header>

      <section class="chat-frame">
        <!-- 唯一滚动容器：消息多时只滚动这里，输入框位置固定 -->
        <div
          ref="messageListRef"
          class="chat-frame__inner"
          @scroll.passive="handleMessageScroll"
        >
          <div class="message-stream">
            <div class="message-lane">
              <div
                v-for="item in displayedMessages"
                :key="item.id"
                class="message-row"
                :class="item.role"
              >
                <div class="message-bubble">
                  <div class="message-bubble__meta">
                    <span>{{ item.role === 'user' ? currentUser.display_name : 'AI Copilot' }}</span>
                    <small>
                      {{ item.role === 'user' ? '提问' : shortModelName(activeConversation?.model || selectedModel) }}
                    </small>
                  </div>
                  <div class="message-content">{{ item.content }}</div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="lastSources.length" class="source-panel">
            <div class="source-panel__head">
              <strong>参考资料</strong>
              <span>{{ lastGrounded ? '已基于知识库作答' : '本轮未完全基于资料落地' }}</span>
            </div>

            <div class="source-grid">
              <article
                v-for="item in lastSources"
                :key="`${item.citation}-${item.title}`"
                class="source-card"
              >
                <strong>{{ item.citation }} {{ item.title }}</strong>
                <small>{{ item.source }} · score {{ item.score }}</small>
              </article>
            </div>
          </div>
        </div>
        <!-- 滚动容器结束 -->

        <footer class="composer-dock">
          <div class="composer-dock__head">
            <div>
              <strong>Ask Anything</strong>
              <span>优先检索文件知识库，未命中时自动回退到模型通用回答。</span>
            </div>
            <el-tag type="info">{{ shortModelName(selectedModel) || '-' }}</el-tag>
          </div>

          <el-input
            v-model="inputValue"
            type="textarea"
            :rows="4"
            resize="none"
            placeholder="请输入问题，按 Enter 发送，Shift + Enter 换行"
            @keydown.enter.prevent="handleEnter"
          />

          <div class="composer-dock__foot">
            <div class="composer-hints">
              <span>SQLite 会话持久化</span>
              <span>Hybrid RAG 混合检索</span>
              <span>SSE 流式输出</span>
            </div>
            <el-button type="primary" :loading="isStreaming" @click="sendMessage">
              发送消息
            </el-button>
          </div>
        </footer>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createChatStream,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
} from '../api/chat'
import { getModels } from '../api/http'
import { listKnowledge } from '../api/knowledge'

const props = defineProps({
  currentUser: {
    type: Object,
    required: true,
  },
})

defineEmits(['logout', 'open-knowledge'])

const currentUser = computed(() => props.currentUser)
const models = ref([])
const selectedModel = ref('')
const inputValue = ref('')
const isStreaming = ref(false)
const useRag = ref(true)
const messageListRef = ref(null)
const autoScrollEnabled = ref(true)
const conversations = ref([])
const activeConversationId = ref('')
const messages = ref([])
const stopCurrentStream = ref(null)
const lastSources = ref([])
const lastGrounded = ref(false)
const knowledgeCount = ref(0)

const activeConversation = computed(() =>
  conversations.value.find((item) => item.id === activeConversationId.value) || null,
)

const starterMessage = computed(() => ({
  id: `starter-${activeConversationId.value || 'welcome'}`,
  role: 'assistant',
  content:
    '你好，我是 AI Copilot。你可以直接提问，也可以先去知识库中心上传文件，我会优先结合资料给出更准确的回答。',
}))

const displayedMessages = computed(() =>
  messages.value.length > 0 ? messages.value : [starterMessage.value],
)

const historyCountLabel = computed(() => {
  const total = conversations.value.length
  return `最近 ${total} 条`
})

function shortModelName(model) {
  if (!model) return ''
  const [family, versionPart] = model.split(':')
  if (!versionPart) return model.split('-')[0]
  return `${family}:${versionPart.split('-')[0]}`
}

function displayConversationTitle(item) {
  return item?.title?.trim() || '新对话'
}

const NEAR_BOTTOM_OFFSET = 80

function isNearBottom(element) {
  return element.scrollHeight - element.scrollTop - element.clientHeight <= NEAR_BOTTOM_OFFSET
}

// 用户往上翻时暂停自动跟随，回到接近底部后自动恢复（类似 ChatGPT）
function handleMessageScroll() {
  const element = messageListRef.value
  if (!element) return
  autoScrollEnabled.value = isNearBottom(element)
}

function scrollToBottom(force = false) {
  nextTick(() => {
    const element = messageListRef.value
    if (!element) return
    if (messages.value.length === 0) {
      element.scrollTop = 0
      autoScrollEnabled.value = true
      return
    }
    if (!force && !autoScrollEnabled.value) return
    element.scrollTop = element.scrollHeight
    autoScrollEnabled.value = true
  })
}

function normalizeMessages(items = []) {
  return items
    .filter((item) => item.role !== 'system')
    .map((item) => ({
      id: item.id,
      role: item.role,
      content: item.content,
    }))
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

function createAssistantPlaceholder() {
  const message = {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '',
  }
  messages.value.push(message)
  return message
}

async function loadModels() {
  const data = await getModels()
  models.value = data.models || []
  if (!selectedModel.value) {
    selectedModel.value = data.default_model || data.models?.[0] || ''
  }
}

async function loadConversationList() {
  conversations.value = await listConversations()
}

async function loadKnowledgeCount() {
  const items = await listKnowledge()
  knowledgeCount.value = items.length
}

async function selectConversation(conversationId) {
  activeConversationId.value = conversationId
  const data = await getConversation(conversationId)
  messages.value = normalizeMessages(data.messages)
  selectedModel.value = data.model || selectedModel.value
  useRag.value = data.use_rag ?? true
  lastSources.value = data.latest_sources || []
  lastGrounded.value = data.latest_grounded ?? false
  scrollToBottom(true)
}

async function ensureConversation() {
  if (activeConversationId.value) return
  if (conversations.value.length > 0) {
    await selectConversation(conversations.value[0].id)
    return
  }
  await handleCreateConversation()
}

async function handleCreateConversation() {
  const created = await createConversation({
    model: selectedModel.value,
    use_rag: useRag.value,
  })
  await loadConversationList()
  activeConversationId.value = created.id
  messages.value = []
  lastSources.value = []
  lastGrounded.value = false
  selectedModel.value = created.model || selectedModel.value
  useRag.value = created.use_rag ?? true
  scrollToBottom(true)
}

async function handleDeleteConversation(conversationId) {
  try {
    await ElMessageBox.confirm(
      '是否继续删除？',
      '删除会话',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        customClass: 'delete-conversation-box',
      },
    )
    await deleteConversation(conversationId)
    if (activeConversationId.value === conversationId) {
      activeConversationId.value = ''
      messages.value = []
      lastSources.value = []
      lastGrounded.value = false
    }
    await loadConversationList()
    await ensureConversation()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || error.message || '删除失败')
    }
  }
}

async function sendMessage() {
  const content = inputValue.value.trim()
  if (!content || isStreaming.value) return

  await ensureConversation()

  messages.value.push({
    id: crypto.randomUUID(),
    role: 'user',
    content,
  })

  const assistantMessage = createAssistantPlaceholder()
  lastSources.value = []
  lastGrounded.value = false
  inputValue.value = ''
  isStreaming.value = true
  scrollToBottom(true)

  const payload = {
    conversation_id: activeConversationId.value,
    message: content,
    model: selectedModel.value,
    use_rag: useRag.value,
  }

  stopCurrentStream.value = await createChatStream(payload, {
    onStart(data) {
      lastSources.value = data.sources || []
      lastGrounded.value = data.grounded ?? false
    },
    onDelta(data) {
      assistantMessage.content = data.full_text
      scrollToBottom()
    },
    async onEnd(data) {
      isStreaming.value = false
      stopCurrentStream.value = null
      lastSources.value = data.sources || []
      lastGrounded.value = data.grounded ?? false
      await loadConversationList()
      await selectConversation(activeConversationId.value)
    },
    onError(error) {
      assistantMessage.content = `请求失败：${error.message}`
      isStreaming.value = false
      stopCurrentStream.value = null
      ElMessage.error(error.message || '对话失败')
    },
  })
}

function handleEnter(event) {
  if (event.shiftKey) return
  sendMessage()
}

onMounted(async () => {
  try {
    await loadModels()
    await loadConversationList()
    await loadKnowledgeCount()
    await ensureConversation()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '工作台初始化失败')
  }
})
</script>

<style scoped>
.workspace-shell {
  /* 固定为视口高度，页面本身不再滚动，滚动只发生在内部容器 */
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  display: grid;
  grid-template-columns: 296px minmax(0, 1fr);
  gap: 24px;
  padding: 18px;
  background:
    radial-gradient(circle at top left, rgba(14, 165, 233, 0.1), transparent 18%),
    linear-gradient(180deg, #08111f 0%, #0f172a 42%, #0b1220 100%);
}

.sidebar {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 12px;
  height: 100%;
  min-height: 0;
}

.sidebar-card,
.stage-header,
.chat-frame,
.composer-dock,
.source-panel {
  border: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(10, 18, 32, 0.84);
  box-shadow: 0 22px 70px rgba(2, 6, 23, 0.28);
  backdrop-filter: blur(18px);
}

.sidebar-card {
  border-radius: 24px;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.sidebar-card--brand h1 {
  margin: 2px 0 6px;
  color: #f8fafc;
  font-size: 24px;
  line-height: 1.04;
}

.eyebrow {
  margin: 0 0 8px;
  color: #38bdf8;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 11px;
  font-weight: 700;
}

.brand-copy,
.sidebar-card--footer li {
  margin: 0;
  color: #94a3b8;
  line-height: 1.6;
}

.toolbar-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.toolbar-button {
  width: 100%;
  height: 40px;
  margin: 0;
  border-radius: 14px;
  font-weight: 600;
}

.toolbar-button--secondary {
  color: #dbeafe;
  border-color: rgba(56, 189, 248, 0.22);
  background: rgba(8, 47, 73, 0.28);
}

.toolbar-field {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.58);
}

.toolbar-field label,
.meta-chip span,
.history-head span,
.history-item__top span,
.history-item__meta small,
.stage-header span,
.composer-dock__head span,
.composer-hints span,
.source-panel__head span {
  color: #94a3b8;
  font-size: 12px;
}

.toolbar-meta {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.meta-chip {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.58);
}

.history-head,
.history-item__top,
.history-item__meta,
.stage-header,
.composer-dock__head,
.composer-dock__foot,
.source-panel__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.history-head {
  align-items: center;
  margin-bottom: 8px;
}

.history-head strong,
.source-panel__head strong,
.composer-dock__head strong {
  color: #f8fafc;
}

.sidebar-card--history {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  padding-bottom: 10px;
}

.history-list {
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 4px;
  margin-right: -2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.28) transparent;
}

.history-list::-webkit-scrollbar {
  width: 8px;
}

.history-list::-webkit-scrollbar-track {
  background: transparent;
}

.history-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.28);
}

.history-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 80px;
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.08);
  background: linear-gradient(180deg, rgba(16, 26, 45, 0.92), rgba(15, 23, 42, 0.62));
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.history-item:hover,
.history-item.active {
  transform: translateY(-1px);
  border-color: rgba(56, 189, 248, 0.28);
  box-shadow: 0 16px 30px rgba(8, 47, 73, 0.18);
}

.history-item__main,
.history-item__delete {
  border: 0;
  cursor: pointer;
}

.history-item__main {
  min-width: 0;
  padding: 2px;
  background: transparent;
  text-align: left;
}

.history-item__top strong {
  display: -webkit-box;
  overflow: hidden;
  color: #f8fafc;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.history-item__meta {
  margin-top: 6px;
}

.history-item__delete {
  min-width: 54px;
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(30, 41, 59, 0.88);
  color: #cbd5e1;
  font-size: 12px;
  transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.history-item__delete:hover {
  border-color: rgba(56, 189, 248, 0.22);
  background: rgba(15, 23, 42, 0.96);
  color: #f8fafc;
}

.history-empty {
  display: grid;
  place-items: center;
  gap: 8px;
  min-height: 160px;
  padding: 24px 18px;
  border-radius: 20px;
  border: 1px dashed rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.38);
  text-align: center;
  color: #94a3b8;
}

.history-empty strong {
  color: #e2e8f0;
}

.sidebar-card--footer ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
  color: #94a3b8;
}

.sidebar-card--footer {
  gap: 8px;
}

.chat-stage {
  /* 占满 workspace-shell 的行高，并让内部 1fr 行可以被压缩 */
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
}

.stage-header {
  align-items: center;
  padding: 18px 24px;
  border-radius: 28px;
}

.stage-header h2 {
  margin: 6px 0 4px;
  color: #f8fafc;
  font-size: 28px;
  line-height: 1.08;
}

.stage-header__actions {
  display: flex;
  gap: 10px;
}

.chat-frame {
  min-height: 0;
  border-radius: 28px;
  /* 两行：内容区（可伸缩、可滚动）+ 输入框（固定高度） */
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  overflow: hidden;
  padding: 0;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.12), transparent 18%),
    linear-gradient(180deg, rgba(2, 6, 23, 0.88), rgba(12, 22, 40, 0.84));
}

/* 唯一滚动区：消息再多也只在内部滚动，输入框位置不变 */
.chat-frame__inner {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 24px;
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.28) transparent;
}

.chat-frame__inner::-webkit-scrollbar {
  width: 8px;
}

.chat-frame__inner::-webkit-scrollbar-track {
  background: transparent;
}

.chat-frame__inner::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.28);
}

.chat-frame__inner::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.45);
}

.message-stream {
  /* 内容少时撑满剩余空间，内容多时保持自然高度交给父级滚动（不能被压缩） */
  flex: 1 0 auto;
}

.message-lane {
  width: min(940px, 100%);
  margin: 0 auto;
}

.message-row {
  display: flex;
  margin-bottom: 20px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-bubble {
  width: min(760px, 82%);
  padding: 16px 18px;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(15, 23, 42, 0.82);
  color: #e2e8f0;
}

.message-row.user .message-bubble {
  background: linear-gradient(180deg, rgba(8, 47, 73, 0.94), rgba(14, 116, 144, 0.78));
}

.message-bubble__meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.message-content {
  white-space: pre-wrap;
  line-height: 1.85;
}

.source-panel {
  width: min(940px, 100%);
  margin: 16px auto 0; /* ✅ 原来用 gap:16px，改成 margin 更可控 */
  padding: 14px 18px;
  border-radius: 22px;
  background: rgba(8, 15, 28, 0.94);
}

.source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.source-card {
  padding: 12px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(56, 189, 248, 0.14);
}

.source-card strong {
  display: block;
  margin-bottom: 6px;
  color: #e2e8f0;
}

.source-card small {
  color: #94a3b8;
}

.composer-dock {
  width: 100%;
  margin: 0;
  padding: 18px 24px 20px;
  border-radius: 0 0 28px 28px;
  background: rgba(9, 17, 30, 0.94);
  box-shadow: 0 -8px 30px rgba(2, 6, 23, 0.36);
}

.composer-dock__head {
  align-items: center;
  margin-bottom: 14px;
}

.composer-dock__head strong {
  display: block;
  color: #f8fafc;
  margin-bottom: 4px;
}

.composer-dock__foot {
  align-items: center;
  margin-top: 14px;
}

.composer-hints {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

:deep(.stage-header__actions .el-button),
:deep(.composer-dock .el-button) {
  border-radius: 14px;
}

:deep(.composer-dock .el-textarea__inner) {
  min-height: 118px !important;
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(248, 250, 252, 0.96);
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner),
:deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.16) inset;
}

:deep(.delete-conversation-box) {
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(11, 19, 33, 0.98), rgba(15, 23, 42, 0.98));
  box-shadow: 0 24px 60px rgba(2, 6, 23, 0.48);
}

:deep(.delete-conversation-box .el-message-box__header) {
  padding-bottom: 4px;
}

:deep(.delete-conversation-box .el-message-box__title) {
  color: #f8fafc;
  font-weight: 700;
}

:deep(.delete-conversation-box .el-message-box__close) {
  color: #94a3b8;
}

:deep(.delete-conversation-box .el-message-box__content) {
  color: #cbd5e1;
}

:deep(.delete-conversation-box .el-message-box__status) {
  color: #f59e0b !important;
}

:deep(.delete-conversation-box .el-message-box__message) {
  color: #cbd5e1;
  line-height: 1.7;
}

:deep(.delete-conversation-box .el-message-box__btns) {
  padding-top: 10px;
}

:deep(.delete-conversation-box .el-button) {
  border-radius: 12px;
}

:deep(.delete-conversation-box .el-button:not(.el-button--primary)) {
  border-color: rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.88);
  color: #cbd5e1;
}

:deep(.delete-conversation-box .el-button--primary) {
  border-color: rgba(239, 68, 68, 0.18);
  background: linear-gradient(180deg, #ef4444, #dc2626);
  color: #fff;
}

@media (max-width: 1180px) {
  .workspace-shell {
    grid-template-columns: 280px minmax(0, 1fr);
  }

  .message-stream {
    padding-left: 0;
    padding-right: 0;
  }

  .chat-frame__inner {
    padding: 18px;
  }
}

@media (max-width: 980px) {
  /* 窄屏恢复整页滚动，聊天框单独给一个视口高度 */
  .workspace-shell {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .sidebar,
  .chat-stage {
    height: auto;
    min-height: 0;
  }

  .sidebar {
    grid-template-rows: auto auto auto auto;
    max-height: none;
  }

  .stage-header,
  .stage-header__actions,
  .composer-dock__head,
  .composer-dock__foot {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-actions,
  .toolbar-meta {
    grid-template-columns: 1fr;
  }

  .history-list {
    max-height: 440px;
  }

  .chat-frame {
    min-height: 0;
    height: max(520px, calc(100dvh - 200px));
    padding: 0;
    grid-template-rows: minmax(0, 1fr) auto;
  }

  .chat-frame__inner {
    padding: 18px;
  }

  .source-panel,
  .composer-dock {
    width: 100%;
  }

  .message-stream {
    padding-bottom: 0;
  }
}
</style>