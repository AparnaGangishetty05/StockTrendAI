import { useEffect, useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'

const API = 'http://127.0.0.1:8000/api'

function DashboardPage() {
  const [dashboard, setDashboard] = useState(null)
  const [progress, setProgress] = useState([])
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [dashboardRes, progressRes] = await Promise.all([
        fetch(`${API}/dashboard`),
        fetch(`${API}/progress`),
      ])
      const dashboardData = await dashboardRes.json()
      const progressData = await progressRes.json()
      setDashboard(dashboardData)
      setProgress(progressData)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const completedCount = progress.length
  const taskCount = dashboard?.tasks?.length || 0
  const completionPercent = taskCount ? Math.round((completedCount / taskCount) * 100) : 0

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-700 bg-slate-900/70 p-6 shadow-2xl">
        <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Adaptive Study Planner Agent</p>
        <h1 className="mt-2 text-3xl font-semibold">Today’s guidance</h1>
        <p className="mt-3 text-slate-300">{loading ? 'Loading your plan...' : dashboard?.explanation || 'No explanation yet.'}</p>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <section className="rounded-3xl border border-slate-700 bg-slate-900/70 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Today’s tasks</h2>
            <span className="rounded-full bg-cyan-500/15 px-3 py-1 text-sm text-cyan-300">{taskCount} tasks</span>
          </div>
          <div className="mt-4 space-y-3">
            {dashboard?.tasks?.length ? dashboard.tasks.map((task) => (
              <div key={task.id} className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-800/70 px-4 py-3">
                <div>
                  <p className="font-medium">{task.subject}</p>
                  <p className="text-sm text-slate-400">{task.topic}</p>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs ${task.completed ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
                  {task.completed ? 'Done' : 'Planned'}
                </span>
              </div>
            )) : <p className="text-slate-400">No tasks yet. Create a plan to begin.</p>}
          </div>
        </section>

        <section className="rounded-3xl border border-slate-700 bg-slate-900/70 p-6">
          <h2 className="text-xl font-semibold">Overall progress</h2>
          <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-800/70 p-4">
            <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
              <span>Completed</span>
              <span>{completedCount}/{taskCount}</span>
            </div>
            <div className="h-3 rounded-full bg-slate-700">
              <div className="h-3 rounded-full bg-cyan-500" style={{ width: `${completionPercent}%` }} />
            </div>
            <p className="mt-3 text-sm text-slate-400">{completionPercent}% of the current plan is complete.</p>
          </div>
        </section>
      </div>
    </div>
  )
}

function CreatePlanPage() {
  const [name, setName] = useState('Demo Student')
  const [examDate, setExamDate] = useState('2026-12-20')
  const [subjects, setSubjects] = useState('DBMS, Networks, Operating Systems')
  const [hours, setHours] = useState(3)
  const [message, setMessage] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    try {
      const userRes = await fetch(`${API}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      if (!userRes.ok) throw new Error('Unable to create user')

      const planRes = await fetch(`${API}/plans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exam_date: examDate,
          subjects,
          hours_per_day: Number(hours),
        }),
      })
      if (!planRes.ok) throw new Error('Unable to create plan')

      setMessage('Study plan created successfully.')
    } catch (error) {
      setMessage(error.message)
    }
  }

  return (
    <div className="rounded-3xl border border-slate-700 bg-slate-900/70 p-6 shadow-2xl">
      <h1 className="text-2xl font-semibold">Create plan</h1>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="mb-2 block text-sm text-slate-300">User Name</label>
          <input value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded-2xl border border-slate-700 bg-slate-800 px-3 py-2" />
        </div>
        <div>
          <label className="mb-2 block text-sm text-slate-300">Exam Date</label>
          <input type="date" value={examDate} onChange={(event) => setExamDate(event.target.value)} className="w-full rounded-2xl border border-slate-700 bg-slate-800 px-3 py-2" />
        </div>
        <div>
          <label className="mb-2 block text-sm text-slate-300">Subjects</label>
          <input value={subjects} onChange={(event) => setSubjects(event.target.value)} className="w-full rounded-2xl border border-slate-700 bg-slate-800 px-3 py-2" />
        </div>
        <div>
          <label className="mb-2 block text-sm text-slate-300">Hours per day</label>
          <input type="number" value={hours} onChange={(event) => setHours(event.target.value)} className="w-full rounded-2xl border border-slate-700 bg-slate-800 px-3 py-2" />
        </div>
        <button type="submit" className="w-full rounded-2xl bg-fuchsia-500 px-4 py-2 font-medium text-white">Generate study plan</button>
      </form>
      {message ? <p className="mt-4 text-sm text-cyan-300">{message}</p> : null}
    </div>
  )
}

function ProgressPage() {
  const [tasks, setTasks] = useState([])
  const [selected, setSelected] = useState([])
  const [message, setMessage] = useState('')

  const loadTasks = async () => {
    const response = await fetch(`${API}/dashboard`)
    const data = await response.json()
    setTasks(data.tasks || [])
  }

  useEffect(() => {
    loadTasks()
  }, [])

  const toggleTask = (task) => {
    setSelected((current) => current.includes(task.id) ? current.filter((id) => id !== task.id) : [...current, task.id])
  }

  const handleSave = async () => {
    const payload = tasks.filter((task) => selected.includes(task.id)).map((task) => ({ subject: task.subject, topic: task.topic }))
    if (!payload.length) {
      setMessage('Select at least one task to mark as completed.')
      return
    }

    const response = await fetch(`${API}/progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (response.ok) {
      setMessage('Progress saved successfully.')
      setSelected([])
      await loadTasks()
    } else {
      setMessage('Could not save progress.')
    }
  }

  return (
    <div className="rounded-3xl border border-slate-700 bg-slate-900/70 p-6 shadow-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Progress</h1>
        <button onClick={handleSave} className="rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950">Save completed tasks</button>
      </div>
      <div className="mt-6 space-y-3">
        {tasks.length ? tasks.map((task) => (
          <label key={task.id} className="flex cursor-pointer items-center justify-between rounded-2xl border border-slate-800 bg-slate-800/70 px-4 py-3">
            <div>
              <p className="font-medium">{task.subject}</p>
              <p className="text-sm text-slate-400">{task.topic}</p>
            </div>
            <input type="checkbox" checked={selected.includes(task.id)} onChange={() => toggleTask(task)} className="h-4 w-4 rounded border-slate-600 bg-slate-700" />
          </label>
        )) : <p className="text-slate-400">No tasks for today yet.</p>}
      </div>
      {message ? <p className="mt-4 text-sm text-cyan-300">{message}</p> : null}
    </div>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-slate-950 px-4 py-8 text-slate-50">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Full-stack agent demo</p>
            <h1 className="text-3xl font-semibold">Adaptive Study Planner Agent</h1>
          </div>
          <nav className="flex flex-wrap gap-3">
            <Link to="/" className="rounded-full border border-slate-700 px-4 py-2 text-sm">Dashboard</Link>
            <Link to="/create-plan" className="rounded-full border border-slate-700 px-4 py-2 text-sm">Create Plan</Link>
            <Link to="/progress" className="rounded-full border border-slate-700 px-4 py-2 text-sm">Progress</Link>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/create-plan" element={<CreatePlanPage />} />
          <Route path="/progress" element={<ProgressPage />} />
        </Routes>
      </div>
    </div>
  )
}

export default App
