import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import PageHeader from '../components/PageHeader';
import './SalesPipelinePage.css';

interface Opportunity {
  id: string;
  requirement: string;
  score: number;
  band: string;
}

interface PipelineSection {
  title: string;
  stageKey: string;
  data: Opportunity[];
}

const STAGES = [
  { key: 'new', label: 'New' },
  { key: 'review', label: 'Reviewed' },
  { key: 'contacted', label: 'Contacted' },
  { key: 'closed', label: 'Closed (Won)' },
  { key: 'rejected', label: 'Rejected (Lost)' },
];

export default function SalesPipelinePage() {
  const [sections, setSections] = useState<PipelineSection[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadPipeline = useCallback(async () => {
    try {
      const responses = await Promise.all(
        STAGES.map((stage) =>
          apiClient.get('/opportunities/', { params: { status: stage.key, ordering: '-detected_at' } })
        )
      );
      const built = STAGES.map((stage, i) => ({
        title: `${stage.label} (${responses[i].data.count ?? 0})`,
        stageKey: stage.key,
        data: responses[i].data.results ?? responses[i].data,
      }));
      setSections(built);
    } catch (err) {
      console.log('Error loading pipeline:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPipeline();
  }, [loadPipeline]);

  return (
    <div className="pipeline-page">
      <PageHeader title="Sales Pipeline" />
            {loading ? (
        <div className="pipeline-loading">Loading...</div>
      ) : (
        <div className="pipeline-board">
          {sections.map((section) => (
            <div key={section.stageKey} className="pipeline-column">
              <div className="pipeline-column-header">{section.title}</div>
              <div className="pipeline-column-body">
                {section.data.length === 0 ? (
                  <p className="pipeline-empty">No opportunities in this stage.</p>
                ) : (
                  section.data.map((item) => (
                    <div key={item.id} className="pipeline-card" onClick={() => navigate(`/lead/${item.id}`)}>
                      <p className="pipeline-card-title">{item.requirement ?? 'Untitled'}</p>
                      <p className="pipeline-card-meta">
                        {item.band} · Score {item.score}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}