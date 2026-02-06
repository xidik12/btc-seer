import { useEffect, useRef, useState, useCallback } from 'react'

export function useWebSocket(url) {
  const [lastMessage, setLastMessage] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const ws = useRef(null)
  const reconnectTimer = useRef(null)

  const connect = useCallback(() => {
    if (!url) return

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => setIsConnected(true)

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
        } catch {
          setLastMessage(event.data)
        }
      }

      ws.current.onclose = () => {
        setIsConnected(false)
        reconnectTimer.current = setTimeout(connect, 5000)
      }

      ws.current.onerror = () => {
        ws.current?.close()
      }
    } catch {
      reconnectTimer.current = setTimeout(connect, 5000)
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  return { lastMessage, isConnected }
}
