import "./MetricCard.css";

type MetricCardProps = {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
};

export default function MetricCard({ label, value, delta, positive }: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {delta != null && (
        <div className={`metric-delta ${positive ? "positive" : "negative"}`}>{delta}</div>
      )}
    </div>
  );
}
