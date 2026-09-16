export default function OpportunityTable({ rows, onOpen }) {
  if (!rows || rows.length === 0) {
    return <div className="empty">No records match these filters.</div>
  }

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase()
    let cls = 'pill'
    if (s === 'new') cls += ' pill-new'
    else if (s === 'review') cls += ' pill-review'
    else if (s === 'reviewed') cls += ' pill-reviewed'
    else if (s === 'contacted') cls += ' pill-contacted'
    else if (s === 'meeting') cls += ' pill-meeting'
    else if (s === 'proposal') cls += ' pill-proposal'
    else if (s === 'won') cls += ' pill-won'
    else if (s === 'rejected') cls += ' pill-rejected'
    else if (s === 'closed') cls += ' pill-closed'
    return <span className={cls}>{status}</span>
  }

  const getBandBadge = (band, score) => {
    let cls = 'band-tag'
    if (band === 'Hot') cls += ' band-hot'
    else if (band === 'High potential') cls += ' band-high'
    else if (band === 'Review') cls += ' band-review'
    else cls += ' band-archive'
    return (
      <div className="score-cell">
        <div className="score-val">{score}</div>
        <span className={cls}>{band}</span>
      </div>
    )
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Opportunity and Buying Signal</th>
            <th>Service Category</th>
            <th>Score & Band</th>
            <th>Sales Status</th>
            <th>Contact Evidence</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((l) => (
            <tr key={l.id} className="lead-row">
              <td style={{ maxWidth: '380px' }}>
                <button className="lead-button" onClick={() => onOpen(l.id)}>
                  {l.requirement}
                </button>
                <div className="minor" style={{ marginTop: 4 }}>
                  <span className="source-tag">{l.source || 'web_search'}</span>
                  <span> · </span>
                  <span>{(l.source_published_at || l.detected_at || '').slice(0, 10)}</span>
                  {l.company_name && (
                    <>
                      <span> · </span>
                      <strong style={{ color: '#334155' }}>{l.company_name}</strong>
                    </>
                  )}
                  {l.country && (
                    <>
                      <span> · </span>
                      <span className="country-chip">{l.country}</span>
                    </>
                  )}
                </div>
              </td>
              <td>
                <span className="pill service-pill">{l.primary_category || 'CUSTOM_DEV'}</span>
              </td>
              <td>
                {getBandBadge(l.band, l.score)}
              </td>
              <td>
                {getStatusBadge(l.status)}
              </td>
              <td>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {l.email ? (
                    <span className="contact-path published" title={l.email}>
                      <span className="dot online"></span> {l.email}
                    </span>
                  ) : (
                    <span className="contact-path url">
                      <span className="dot fallback"></span> Reference URL
                    </span>
                  )}
                  <span className="minor" style={{ fontSize: 11 }}>
                    Owner: <strong>{l.owner_name || 'Unassigned'}</strong>
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
