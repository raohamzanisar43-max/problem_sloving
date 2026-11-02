import './PageHeader.css';

export default function PageHeader({ title }: { title: string; backTo?: string }) {
  return (
    <div className="page-header">
      <h1 className="page-header-title">{title}</h1>
    </div>
  );
}