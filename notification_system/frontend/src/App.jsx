import { useState, useEffect } from 'react'

export default function App() {
  const [items, setItems] = useState([])
  const [err, setErr] = useState(null)

  useEffect(() => {
    fetch('/api/notifications')
      .then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
      .then(d => setItems(Array.isArray(d) ? d : []))
      .catch(e => setErr(e.message))
  }, [])

  if (err) return <div style={{padding: 20, color: 'red'}}>Error: {err}</div>

  return (
    <div style={{padding: 20, fontFamily: 'system-ui'}}>
      <h1>通知中心 v2.0</h1>
      <p>共 {items.length} 条通知</p>
      {items.map(n => (
        <div key={n.id} style={{
          margin: '12px 0',
          padding: 16,
          border: '1px solid #e0e0e0',
          borderRadius: 8,
          background: n.type === 'error' ? '#ffebee' : n.type === 'success' ? '#e8f5e9' : n.type === 'warning' ? '#fff3e0' : '#e3f2fd'
        }}>
          <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8}}>
            <span>{n.type === 'success' ? '✅' : n.type === 'warning' ? '⚠️' : n.type === 'error' ? '❌' : 'ℹ️'}</span>
            <strong>{n.title}</strong>
            <span style={{
              marginLeft: 'auto',
              fontSize: 12,
              padding: '2px 8px',
              borderRadius: 12,
              background: n.status === 'pending' ? '#fff3e0' : '#e8f5e9'
            }}>{n.status}</span>
          </div>
          <p style={{margin: '8px 0', color: '#555'}}>{n.message}</p>
          <div style={{fontSize: 12, color: '#888', display: 'flex', gap: 12}}>
            <span>{n.category}</span>
            <span>{new Date(n.created_at).toLocaleString()}</span>
            {n.scheduled_at && <span style={{color: '#e65100'}}>定时: {new Date(n.scheduled_at).toLocaleString()}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
