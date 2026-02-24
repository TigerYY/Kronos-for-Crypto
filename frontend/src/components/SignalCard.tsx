import "./SignalCard.css";

type SignalCardProps = {
  action: string;
};

export default function SignalCard({ action }: SignalCardProps) {
  const cls =
    action === "BUY"
      ? "signal-card signal-buy"
      : action === "SELL"
        ? "signal-card signal-sell"
        : "signal-card signal-hold";
  const label = action === "BUY" ? "▲ BUY" : action === "SELL" ? "▼ SELL" : "◆ HOLD";
  return (
    <div className={cls}>
      <span className="signal-label">{label}</span>
    </div>
  );
}
