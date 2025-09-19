import React from "react";

type Props = {
  jackettUrl: string;
  message?: string;
};

export function OpenJackettCard({ jackettUrl, message }: Props) {
  const instructions = [
    "Open Jackett",
    "Add or configure indexers",
    "Return to Phelia and run your search again",
  ];

  return (
    <div
      style={{
        border: "1px solid #d0d7de",
        borderRadius: 8,
        padding: 16,
        background: "#f6f8fa",
        marginBottom: 16,
      }}
    >
      <h3 style={{ marginTop: 0 }}>Jackett setup required</h3>
      {message && <p style={{ marginTop: 0 }}>{message}</p>}
      <button
        style={{
          background: "#0366d6",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          padding: "8px 14px",
          cursor: "pointer",
          marginBottom: 12,
        }}
        onClick={() => window.open(jackettUrl, "_blank", "noopener,noreferrer")}
      >
        Open Jackett
      </button>
      <ol style={{ margin: 0, paddingLeft: 20 }}>
        {instructions.map((step, index) => (
          <li key={step} style={{ marginBottom: index === instructions.length - 1 ? 0 : 4 }}>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}

export default OpenJackettCard;

