import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

const root = document.getElementById('root')

try {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
} catch (err) {
  root.innerHTML = `
    <div style="padding: 20px; color: red; font-family: sans-serif;">
      <h2>React Error</h2>
      <p>${err.message}</p>
      <pre>${err.stack}</pre>
    </div>
  `
}
