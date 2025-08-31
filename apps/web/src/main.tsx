import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'
const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8000'

function App() {
  const [magnet, setMagnet] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      refresh()
    }
  }, [token])

  const refresh = async () => {
    const { data } = await axios.get(`${API_BASE}/downloads`)
    setItems(data)
  }

  const login = async () => {
    const base = API_BASE.replace(/\/api\/v1$/, '')
    const { data } = await axios.post(`${base}/auth/login`, { username, password })
    const tok = data.token
    if (tok) {
      localStorage.setItem('token', tok)
      setToken(tok)
    }
  }

  const addMagnet = async () => {
    if (!magnet) return
    await axios.post(`${API_BASE}/downloads`, { magnet, savePath: '/downloads' })
    setMagnet('')
    refresh()
  }

  const pause = async (id: number) => { await axios.post(`${API_BASE}/downloads/${id}/pause`); refresh() }
  const resume = async (id: number) => { await axios.post(`${API_BASE}/downloads/${id}/resume`); refresh() }
  const del = async (id: number, delFiles: boolean) => {
    await axios.delete(`${API_BASE}/downloads/${id}`, { params: { deleteFiles: delFiles }})
    refresh()
  }

  const attachWS = (id: number) => {
    const ws = new WebSocket(`${WS_BASE}/ws/downloads/${id}`)
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data)
      setItems(prev => prev.map(it => it.id === id ? {
        ...it,
        status: msg.state || it.status,
        progress: msg.progress ?? it.progress,
        rateDown: msg.dlspeed ?? it.rateDown,
        rateUp: msg.upspeed ?? it.rateUp,
        etaSec: msg.eta ?? it.etaSec,
        name: msg.name ?? it.name,
      } : it))
    }
    ws.onclose = () => {}
  }

  if (!token) {
    return (
      <div style={{maxWidth: 400, margin: '40px auto', fontFamily: 'system-ui, sans-serif'}}>
        <h1>Music AutoDL</h1>
        <h2>Login</h2>
        <div style={{display:'flex', flexDirection:'column', gap:8}}>
          <input value={username} onChange={e=>setUsername(e.target.value)} placeholder="username" />
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="password" />
          <button onClick={login}>Login</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{maxWidth: 900, margin: '40px auto', fontFamily: 'system-ui, sans-serif'}}>
      <h1>Music AutoDL</h1>
      <div style={{display: 'flex', gap: 8}}>
        <input value={magnet} onChange={e=>setMagnet(e.target.value)} placeholder="magnet:?xt=..." style={{flex:1, padding:8}} />
        <button onClick={addMagnet}>Add</button>
      </div>
      <h2 style={{marginTop: 24}}>Downloads</h2>
      <button onClick={refresh}>Refresh</button>
      <table width="100%" cellPadding="6" style={{borderCollapse:'collapse'}}>
        <thead>
          <tr><th>ID</th><th>Name/Path</th><th>Status</th><th>Prog</th><th>DL↑/UL↑</th><th>ETA</th><th>Actions</th><th>WS</th></tr>
        </thead>
        <tbody>
          {items.map(it => (
            <tr key={it.id} style={{borderTop:'1px solid #ddd'}}>
              <td>{it.id}</td>
              <td>{it.name || it.savePath}</td>
              <td>{it.status}</td>
              <td>{Math.round((it.progress||0)*100)}%</td>
              <td>{Math.round((it.rateDown||0)/1024)} / {Math.round((it.rateUp||0)/1024)} kB/s</td>
              <td>{it.etaSec ?? '-'}</td>
              <td>
                <button onClick={()=>pause(it.id)}>Pause</button>{' '}
                <button onClick={()=>resume(it.id)}>Resume</button>{' '}
                <button onClick={()=>del(it.id, false)}>Remove</button>{' '}
                <button onClick={()=>del(it.id, true)}>Remove+Files</button>
              </td>
              <td><button onClick={()=>attachWS(it.id)}>WS</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
