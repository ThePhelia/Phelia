import { useState } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  indexerId: string | null;
  requiresCreds: boolean;
  onConnect: (id: string, creds: { username?: string; password?: string; apikey?: string }) => Promise<void>;
};

export default function ConnectModal({ open, onClose, indexerId, requiresCreds, onConnect }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [apikey, setApikey] = useState("");
  const [loading, setLoading] = useState(false);
  const disabled = loading || !indexerId;

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!indexerId) return;
    setLoading(true);
    try {
      await onConnect(indexerId, requiresCreds ? { username, password, apikey } : {});
      onClose();
      setUsername("");
      setPassword("");
      setApikey("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-white text-black p-4 rounded-xl w-[360px] space-y-3">
        {requiresCreds ? (
          <>
            <input
              className="w-full border p-2 rounded"
              placeholder="Username (если нужно)"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              className="w-full border p-2 rounded"
              placeholder="Password (если нужно)"
              value={password}
              type="password"
              onChange={(e) => setPassword(e.target.value)}
            />
            <input
              className="w-full border p-2 rounded"
              placeholder="API key (если нужно)"
              value={apikey}
              onChange={(e) => setApikey(e.target.value)}
            />
          </>
        ) : (
          <div className="text-sm">Этот индексер публичный — просто подтвердить подключение.</div>
        )}
        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose} className="border px-3 py-2 rounded">Cancel</button>
          <button
            type="submit"
            disabled={disabled}
            className={`px-3 py-2 rounded ${disabled ? "opacity-50 cursor-not-allowed" : "bg-black text-white"}`}
          >
            {loading ? "Connecting…" : "Connect"}
          </button>
        </div>
      </form>
    </div>
  );
}

