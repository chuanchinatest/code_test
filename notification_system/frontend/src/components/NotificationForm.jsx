import { useState } from 'react'
import './NotificationForm.css'

function NotificationForm({ onSuccess }) {
  const [form, setForm] = useState({
    title: '',
    message: '',
    type: 'info',
    category: 'general',
    scheduled_at: ''
  })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)

    const payload = {
      ...form,
      scheduled_at: form.scheduled_at ? new Date(form.scheduled_at).toISOString() : null
    }

    try {
      const res = await fetch('/api/notifications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()
      if (data.code === 200 || data.code === 201) {
        setForm({ title: '', message: '', type: 'info', category: 'general', scheduled_at: '' })
        onSuccess()
        alert(data.message || '创建成功')
      } else {
        alert(data.message || '创建失败')
      }
    } catch (err) {
      alert('请求失败: ' + err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="notification-form">
      <h2>创建通知</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>标题</label>
          <input
            type="text"
            value={form.title}
            onChange={e => setForm({...form, title: e.target.value})}
            required
            placeholder="输入通知标题"
          />
        </div>

        <div className="form-group">
          <label>内容</label>
          <textarea
            value={form.message}
            onChange={e => setForm({...form, message: e.target.value})}
            required
            rows={3}
            placeholder="输入通知内容"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>类型</label>
            <select value={form.type} onChange={e => setForm({...form, type: e.target.value})}>
              <option value="info">ℹ️ 信息</option>
              <option value="success">✅ 成功</option>
              <option value="warning">⚠️ 警告</option>
              <option value="error">❌ 错误</option>
            </select>
          </div>

          <div className="form-group">
            <label>分类</label>
            <input
              type="text"
              value={form.category}
              onChange={e => setForm({...form, category: e.target.value})}
              placeholder="general"
            />
          </div>
        </div>

        <div className="form-group">
          <label>定时发送（可选）</label>
          <input
            type="datetime-local"
            value={form.scheduled_at}
            onChange={e => setForm({...form, scheduled_at: e.target.value})}
          />
          <small>留空则立即发送</small>
        </div>

        <button type="submit" disabled={submitting} className="submit-btn">
          {submitting ? '创建中...' : '创建通知'}
        </button>
      </form>
    </div>
  )
}

export default NotificationForm
