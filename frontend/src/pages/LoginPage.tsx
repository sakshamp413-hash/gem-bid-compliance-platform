import { useState } from "react";
import { RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox, Spinner } from "../components/ui";

const DEMO_CREDENTIALS = [
  { role: "Officer", email: "officer@gem.gov.in", password: "GeM@2026!officer" },
  { role: "Admin", email: "admin@gem.gov.in", password: "GeM@2026!admin" },
  { role: "Auditor", email: "auditor@gem.gov.in", password: "GeM@2026!auditor" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("officer@gem.gov.in");
  const [password, setPassword] = useState("GeM@2026!officer");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/tenders");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gov-navy p-4">
      <div className="w-full max-w-4xl overflow-hidden rounded-xl bg-white shadow-2xl md:grid md:grid-cols-2">
        <div className="hidden flex-col justify-between bg-gradient-to-br from-gov-navy to-gov-blue p-8 text-white md:flex">
          <div>
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded bg-gov-accent text-sm font-bold text-gov-navy">
              प्रमाण
            </div>
            <h1 className="text-2xl font-bold leading-snug">
              PRAMAAN · प्रमाण
            </h1>
            <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-gov-accent">
              AI-Powered GeM Bid Compliance &amp; Procurement Intelligence
            </p>
            <p className="mt-3 text-sm italic text-slate-200">
              “Understand the tender. Verify the bid. Prove the decision.”
            </p>
            <p className="mt-3 text-xs text-slate-300">
              Statutory &amp; eligibility verification for GeM procurement — Udyam, GST, PAN,
              MCA21, Make-in-India, EPFO/ESIC, OEM, DigiLocker signatures and debarment —
              with full explainability and an auditable trail.
            </p>
          </div>
          <ul className="mt-8 space-y-2 text-xs text-slate-300">
            <li>• Every flag links to evidence (document, field, quote, bounding box)</li>
            <li>• DigiLocker-style PKI signature verification + tamper detection</li>
            <li>• Hash-chained audit log with integrity verification</li>
            <li>• The system recommends — the officer decides</li>
          </ul>
        </div>
        <div className="p-8">
          <h2 className="text-lg font-semibold text-gov-navy">Sign in</h2>
          <p className="mt-1 text-xs text-slate-500">Role-aware access control</p>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="label">Email</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && <ErrorBox error={error} />}
            <button className="btn-primary w-full justify-center" disabled={busy}>
              {busy ? <Spinner label="Signing in…" /> : "Sign in"}
            </button>
          </form>
          <div className="mt-8 border-t border-slate-200 pt-4">
            <div className="label">Demo credentials (offline demo)</div>
            <div className="space-y-1.5">
              {DEMO_CREDENTIALS.map((c) => (
                <button
                  key={c.role}
                  className="flex w-full items-center justify-between rounded border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
                  onClick={() => {
                    setEmail(c.email);
                    setPassword(c.password);
                  }}
                >
                  <span className="font-semibold text-gov-blue">{c.role}</span>
                  <span className="text-slate-500">{c.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}