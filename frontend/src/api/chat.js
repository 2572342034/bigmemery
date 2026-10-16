import { API_BASE_URL, getAccessToken, http } from './http'

function parseSSEChunk(rawChunk) {
  const events = []
  const blocks = rawChunk.split('\n\n').filter(Boolean)

  for (const block of blocks) {
    const lines = block.split('\n')
    const event = lines.find((line) => line.startsWith('event:'))?.slice(6).trim() || 'message'
    const dataLine = lines.find((line) => line.startsWith('data:'))
    if (!dataLine) continue

    try {
      events.push({
        event,
        data: JSON.parse(dataLine.slice(5).trim()),
      })
    } catch (error) {
      console.error('Failed to parse SSE block:', error)
    }
  }

  return events
}

export async function listConversations() {
  const { data } = await http.get('/conversations')
  return data
}

export async function getConversation(conversationId) {
  const { data } = await http.get(`/conversations/${conversationId}`)
  return data
}

export async function createConversation(payload = {}) {
  const { data } = await http.post('/conversations', payload)
  return data
}

export async function deleteConversation(conversationId) {
  const { data } = await http.delete(`/conversations/${conversationId}`)
  return data
}

export async function createChatStream(payload, handlers = {}) {
  const { onStart, onDelta, onEnd, onError } = handlers

  try {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${getAccessToken()}`,
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''

      for (const event of parts.flatMap(parseSSEChunk)) {
        if (event.event === 'start') onStart?.(event.data)
        if (event.event === 'delta') onDelta?.(event.data)
        if (event.event === 'end') onEnd?.(event.data)
        if (event.event === 'error') throw new Error(event.data.message || 'Stream error')
      }
    }

    return () => {}
  } catch (error) {
    return createEventSourceFallback(payload, handlers, error)
  }
}

export function createEventSourceFallback(payload, handlers = {}, upstreamError) {
  const { onStart, onDelta, onEnd, onError } = handlers
  const params = new URLSearchParams({
    conversation_id: payload.conversation_id,
    message: payload.message,
    token: getAccessToken(),
    use_rag: String(payload.use_rag ?? true),
  })

  if (payload.model) {
    params.set('model', payload.model)
  }

  const eventSource = new EventSource(`${API_BASE_URL}/chat/stream/es?${params.toString()}`)

  eventSource.addEventListener('start', (event) => {
    onStart?.(JSON.parse(event.data))
  })

  eventSource.addEventListener('delta', (event) => {
    onDelta?.(JSON.parse(event.data))
  })

  eventSource.addEventListener('end', (event) => {
    onEnd?.(JSON.parse(event.data))
    eventSource.close()
  })

  eventSource.addEventListener('error', (event) => {
    const message = event?.data ? JSON.parse(event.data).message : upstreamError?.message || 'SSE error'
    onError?.(new Error(message))
    eventSource.close()
  })

  return () => eventSource.close()
}
