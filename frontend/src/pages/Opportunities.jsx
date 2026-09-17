import { useEffect, useState, useCallback } from 'react'
import { getOpportunities, downloadCsv } from '../api/client'
import OpportunityTable from '../components/OpportunityTable'

const SERVICES = [
  ['', 'All services'],
  ['ERP', 'ERP'],
  ['MANAGED_IT', 'Managed IT'],
  ['MOBILE_APP', 'Mobile app'],
  ['LMS', 'LMS'],
  ['WEBSITE', 'Website'],
  ['CUSTOM_DEV', 'Custom dev'],
  ['CLOUD_DEVOPS', 'Cloud / DevOps'],
  ['AI_AUTOMATION', 'AI / Automation'],
  ['STAFF_AUGMENTATION', 'Staff augmentation'],
  ['CYBERSECURITY', 'Cybersecurity'],
]

const STATUSES = [
  ['', 'All statuses'],
  ['new', 'New'],
  ['review', 'Review'],
  ['reviewed', 'Reviewed'],
  ['contacted', 'Contacted'],
  ['meeting', 'Meeting'],
  ['proposal', 'Proposal'],
  ['won', 'Won'],
  ['rejected', 'Rejected'],
  ['closed', 'Closed'],
]

export default function Opportunities({ onOpenLead }) {
  const [rows, setRows] = useState([])
  const [search, setSearch] = useState('')
  const [service, setService] = useState('')
  const [status, setStatus] = useState('')
  const [count, setCount] = useState(0)
  const [nextCursor, setNextCursor] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async (cursor = null, append = false) => {
    setLoading(true)
    const params = {}
    if (search) params.search = search
    if (service) params.service = service
    if (status) params.status = status
    if (cursor) params.cursor = cursor
    try {
      const data = await getOpportunities(params)
      const list = data.results || data
      const next = data.next
        ? new URL(data.next).searchParams.get('cursor')
        : null
      setRows((prev) => (append ? [...prev, ...list] : list))
      setCount(data.count ?? list.length)
      setNextCursor(next)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [search, service, status])

  useEffect(() => {
    setNextCursor(null)
    load(null, false)
  }, [load])

  const reset = () => {
    setSearch('')
    setService('')
    setStatus('')
  }

  return (
    <div className="panel">
      <div className="controls">
        <div className="control grow">
          <label htmlFor="search">Search requirements</label>
          <input
            id="search"
            placeholder="ERP, managed IT, school LMS…"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="control">
          <label htmlFor="service">Service</label>
          <select id="service" value={service} onChange={(e) => setService(e.target.value)}>
            {SERVICES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="control">
          <label htmlFor="state">Status</label>
          <select id="state" value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <button className="secondary" onClick={reset}>Reset filters</button>
      </div>
      <div className="panel-head">
        <h2>{count} opportunities</h2>
        <button className="secondary" onClick={() => downloadCsv({ search, service, status })}>
          Export filtered view
        </button>
      </div>
      <OpportunityTable rows={rows} onOpen={onOpenLead} />
      {nextCursor && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            className="secondary"
            onClick={() => load(nextCursor, true)}
            disabled={loading}
          >
            {loading ? 'Loading…' : 'Load more'}
          </button>
        </div>
      )}
    </div>
  )
}
