import React from 'react'
import useAeroStore from '../../store/useAeroStore.js'

export default function ConnectionIndicator() {
  // Correct store field names: connectionStatus and apiLastPing
  const connectionStatus = useAeroStore((s) => s.connectionStatus)
  const apiLastPing      = useAeroStore((s) => s.apiLastPing)

  const status = (connectionStatus ?? 'CONNECTING').toUpperCase()

  const dotClass =
    status === 'ONLINE'
      ? 'bg-status-healthy animate-pulse-slow'
      : status === 'OFFLINE'
      ? 'bg-status-critical animate-blink'
      : 'bg-status-warning animate-pulse'

  const textClass =
    status === 'ONLINE'
      ? 'text-status-healthy'
      : status === 'OFFLINE'
      ? 'text-status-critical'
      : 'text-status-warning'

  const label =
    status === 'ONLINE'   ? 'API CONNECTED' :
    status === 'OFFLINE'  ? 'API OFFLINE'   : 'CONNECTING...'

  const pingLabel = apiLastPing
    ? new Date(apiLastPing).toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      })
    : null

  return (
    <div className="flex items-center gap-1.5 font-mono text-xs select-none">
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotClass}`} />
      <span className={`uppercase tracking-wider ${textClass}`}>{label}</span>
      {pingLabel && (
        <span className="text-text-muted hidden sm:inline">· {pingLabel}</span>
      )}
    </div>
  )
}
