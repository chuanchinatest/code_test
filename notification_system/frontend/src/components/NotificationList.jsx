import { useState } from 'react'
import './NotificationList.css'

function NotificationList({ notifications, onRefresh }) {
  const [filter, setFilter] = useState('all')

  const filtered = notifications.filter(n => {
    if (filter === 'all') return true
    if (filter === 'unread') return !n.read
    return n.type === filter
  })

  const markAsRead = async (id) => {
    await fetch(`/api/notifications/${id}/read`, { method: 'POST' })
    onRefresh()
  }

  const deleteNotif = async (id) => {
    await fetch(`/api/notifications/${id}`, { method: 'DELETE' })
    onRefresh()
  }

  const getIcon = (type) => {
    const icons = {
      success: '✅',
      warning: '⚠️',
      error: '❌',
      info: 'ℹ️'
    }
    return icons[type] || '🔔'
  }

  const getTypeClass = (type) => `notif-card ${type}`

  return (
    <div className="notification-list">
      <div className="list-header">
        <h2>通知列表 ({filtered.length})</h2>
        <div className="filters">
          {['all', 'unread', 'success', 'warning', 'error', 'info'].map(f => (
            <button
              key={f}
              className={filter === f ? 'active' : ''}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? '全部' : f === 'unread' ? '未读' : f}
            </button>
          ))}
        </div>
        <button className="refresh-btn" onClick={onRefresh}>刷新</button>
      </div>

      <div className="list-content">
        {filtered.length === 0 ? (
          <div className="empty">暂无通知</div>
        ) : (
          filtered.map(n => (
            <div key={n.id} className={getTypeClass(n.type)}>
              <div className="notif-header">
                <span className="notif-icon">{getIcon(n.type)}</span>
                <span className="notif-title">{n.title}</span>
                <span className={`notif-status ${n.status}`}>{n.status}</span>
              </div>
              <p className="notif-message">{n.message}</p>
              <div className="notif-meta">
                <span>{n.category}</span>
                <span>{new Date(n.created_at).toLocaleString()}</span>
                {n.scheduled_at && (
                  <span className="scheduled">定时: {new Date(n.scheduled_at).toLocaleString()}</span>
                )}
              </div>
              <div className="notif-actions">
                {!n.read && (
                  <button onClick={() => markAsRead(n.id)}>标记已读</button>
                )}
                <button className="danger" onClick={() => deleteNotif(n.id)}>删除</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default NotificationList
