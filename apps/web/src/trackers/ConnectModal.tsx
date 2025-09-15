import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

type Credentials = Record<string, string>;

type Props = {
  open: boolean;
  onClose: () => void;
  indexerId: string | null;
  requiresCreds: boolean;
  credentialFields: string[];
  providerName?: string;
  onConnect: (id: string, creds: Credentials) => Promise<void>;
  onSuccess?: () => void;
};

export default function ConnectModal({
  open,
  onClose,
  indexerId,
  requiresCreds,
  credentialFields,
  providerName,
  onConnect,
  onSuccess,
}: Props) {
  const [values, setValues] = useState<Credentials>({});
  const [loading, setLoading] = useState(false);
  const requiredFields = useMemo(() => credentialFields || [], [credentialFields]);
  const disabled = loading || !indexerId;

  if (!open) return null;

  useEffect(() => {
    if (open) {
      const nextValues: Credentials = {};
      for (const field of requiredFields) {
        nextValues[field] = "";
      }
      setValues(nextValues);
    } else {
      setValues({});
    }
  }, [open, requiredFields]);

  function handleChange(field: string) {
    return (event: ChangeEvent<HTMLInputElement>) => {
      const { value } = event.target;
      setValues((prev) => ({ ...prev, [field]: value }));
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!indexerId) return;
    setLoading(true);
    try {
      const creds = requiresCreds
        ? requiredFields.reduce<Credentials>((acc, field) => {
            acc[field] = values[field] ?? "";
            return acc;
          }, {})
        : {};
      await onConnect(indexerId, creds);
      if (onSuccess) {
        onSuccess();
      } else {
        onClose();
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-white text-black p-4 rounded-xl w-[360px] space-y-3">
        {providerName && <h4 className="font-semibold text-lg">Connect {providerName}</h4>}
        {requiresCreds ? (
          <div className="space-y-2">
            {requiredFields.map((field) => {
              const isPassword = field.toLowerCase().includes("password");
              const inputType = isPassword ? "password" : "text";
              const autoComplete = isPassword ? "current-password" : "off";
              return (
                <div key={field} className="space-y-1">
                  <label className="block text-sm font-medium text-gray-700">{field}</label>
                  <input
                    className="w-full border p-2 rounded"
                    placeholder={field}
                    value={values[field] ?? ""}
                    type={inputType}
                    onChange={handleChange(field)}
                    autoComplete={autoComplete}
                  />
                </div>
              );
            })}
          </div>
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

