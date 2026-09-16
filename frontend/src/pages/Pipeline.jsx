import { useEffect, useState } from 'react'
import { getPipeline } from '../api/client'

const STAGES = ['reviewed', 'contacted', 'meeting', 'proposal', 'won']

export default function Pipeline({ onOpenLead }) {
  const [lanes, setLanes] = useState({})

  useEffect(() => {
    getPipeline().then(setLanes).catch(console.error)
  }, [])

  return (
    <div className="panel">
      <h2>Reviewed sales stages</h2>
      <p className="sub" style={{ marginBottom: 18 }}>
        Change a lead&apos;s status in its detail view to move it into a stage.
      </p>
      <div className="pipeline">
        {STAGES.map((stage) => {
          const rows = lanes[stage] || []
          return (
            <div className="lane" key={stage}>
              <h3>
                {stage.charAt(0).toUpperCase() + stage.slice(1)}{' '}
                <span className="minor">{rows.length}</span>
              </h3>
              {!rows.length ? (
                <div className="empty">No examples</div>
              ) : (
                rows.map((l) => (
                  <div className="lane-card" key={l.id}>
                    <button className="lead-button" onClick={() => onOpenLead(l.id)}>
                      {l.requirement}
                    </button>
                    <p>{l.owner_name || 'Unassigned'}</p>
                    <span className="pill">{l.score} / 100</span>
                  </div>
                ))
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
