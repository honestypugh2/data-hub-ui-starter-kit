import React from "react";

const STATUS_LABELS: Record<string, string> = {
  pending: "⏳ Pending",
  completed: "✅ Completed",
  failed: "❌ Failed",
};

interface Props {
  status: string;
}

const StatusBadge: React.FC<Props> = ({ status }) => {
  return (
    <span className={`status status-${status}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
};

export default StatusBadge;
