import { useEffect, useState } from 'react'
import { getSearchTerms } from '../api/client'

export default function Rules() {
  const [terms, setTerms] = useState([])

  useEffect(() => {
    getSearchTerms()
      .then((data) => setTerms(data.results || data))
      .catch(console.error)
  }, [])

  const groups = {}
  terms.forEach((t) => {
    if (!groups[t.group_name]) groups[t.group_name] = []
    groups[t.group_name].push(t.query)
  })

  return (
    <div className="grid2">
      <div className="panel">
        <h2>Starter query groups</h2>
        <div className="rules">
          {Object.entries(groups).map(([name, queries]) => (
            <div className="rule" key={name}>
              <h3>{name}</h3>
              <code>
                {queries.map((q, i) => (
                  <span key={i}>
                    {q}
                    {i < queries.length - 1 && <br />}
                  </span>
                ))}
              </code>
            </div>
          ))}
          {Object.keys(groups).length === 0 && (
            <div className="empty">Run seed_demo to load starter queries.</div>
          )}
        </div>
      </div>
      <div className="panel">
        <h2>Qualification rules</h2>
        <div className="setting">
          <div>
            <strong>Purchase intent</strong>
            <p>Direct requests and RFPs receive the highest priority.</p>
          </div>
          <span className="pill">Required</span>
        </div>
        <div className="setting">
          <div>
            <strong>Seller promotions</strong>
            <p>Rejected from the sales queue.</p>
          </div>
          <span className="pill closed">Excluded</span>
        </div>
        <div className="setting">
          <div>
            <strong>Employment only</strong>
            <p>Review whether agency procurement is actually permitted.</p>
          </div>
          <span className="pill review">Review</span>
        </div>
        <div className="setting">
          <div>
            <strong>Missing evidence</strong>
            <p>Company, contacts and budgets stay blank.</p>
          </div>
          <span className="pill">No inference</span>
        </div>
        <div className="setting">
          <div>
            <strong>Default pilot markets</strong>
            <p>Pakistan and GCC; expand through verified sources.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
