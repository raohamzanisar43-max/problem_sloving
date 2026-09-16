import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOpportunities, getStats, downloadCsv } from '../api/client'
import OpportunityTable from '../components/OpportunityTable'

export default function Overview({ onOpenLead }) {
  const [stats, setStats] = useState(null)
  const [rows, setRows] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    getStats().then(setStats).catch(console.error)
    getOpportunities({ ordering: '-score' })
      .then((data) => {
        const list = data.results || data
        setRows(
          list.filter((l) => !['rejected', 'closed'].includes(l.status)).slice(0, 10)
        )
      })
      .catch(console.error)
  }, [])

  const statCards = [
    ['Collected examples', stats?.collected ?? '—', 'From database'],
    ['Explicit open buyers', stats?.explicit_buyers ?? '—', 'Buyer evidence present'],
    ['Awaiting review', stats?.awaiting_review ?? '—', 'Intent requires a check'],
    ['Published email', stats?.published_email ?? '—', 'Mailbox unverified'],
  ]

  return (
    <>
      <div className="intro" style={{ marginTop: 0 }}>
        <div />
        <button className="primary" onClick={() => downloadCsv()}>
          Export example leads
        </button>
      </div>

      <div className="stats">
        {statCards.map(([label, num, hint]) => (
          <div className="stat" key={label}>
            <span className="label">{label}</span>
            <strong>{num}</strong>
            <span className="hint">{hint}</span>
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>Prioritized opportunities</h2>
          <button className="secondary" onClick={() => navigate('/opportunities')}>
            Open full queue
          </button>
        </div>
        <OpportunityTable rows={rows} onOpen={onOpenLead} />
      </div>

      <div className="grid2">
        <div className="panel">
          <h2>How a post becomes an opportunity</h2>
          <div className="flow-list">
            {[
              ['1', 'Collect supported sources', 'Licensed web search, approved feeds and manual references.'],
              ['2', 'Check intent and evidence', 'Separate buyers, sellers, hiring and uncertain requirements.'],
              ['3', 'Rank and review', 'Keep verified facts, score factors and duplicate candidates.'],
              ['4', 'Assign and export', 'Work the lead in the queue and report through Excel.'],
            ].map(([step, title, desc]) => (
              <div className="flow-row" key={step}>
                <span className="step">{step}</span>
                <div>
                  <strong>{title}</strong>
                  <p>{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <h2>Review first</h2>
          <p className="sub">
            An employment post may indicate hiring demand. Check whether the buyer accepts an agency before approaching.
          </p>
          <div className="evidence">“We are hiring a full time mobile developer.”</div>
          <button
            className="secondary"
            onClick={() => {
              const hiring = rows.find((r) => r.public_id === 'demo-3')
              if (hiring) onOpenLead(hiring.id)
            }}
          >
            Inspect hiring signal
          </button>
        </div>
      </div>
    </>
  )
}
