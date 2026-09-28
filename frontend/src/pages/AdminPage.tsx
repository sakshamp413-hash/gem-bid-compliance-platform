import { useEffect, useState } from "react";
import { api, User } from "../api/client";
import { Card, Empty, ErrorBox, Spinner } from "../components/ui";

interface IntegrationItem {
  id: string;
  name: string;
  authority: string;
  status: string;
  endpoint_type: string;
  avg_latency_ms: number;
  cached_records: number;
}

export default function AdminPage() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationItem[] | null>(null);
  const [adapterMeta, setAdapterMeta] = useState<{ active_adapter: string; adapter_class: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"users" | "integrations">("users");
  const [newUser, setNewUser] = useState({ name: "", email: "", role: "officer", password: "" });
  const [saved, setSaved] = useState<string | null>(null);
  const [testingIntegrations, setTestingIntegrations] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const load = () => {
    api
      .users()
      .then(setUsers)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    api
      .integrations()
      .then((res) => {
        setIntegrations(res.integrations);
        setAdapterMeta({ active_adapter: res.active_adapter, adapter_class: res.adapter_class });
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(load, []);

  const createUser = async () => {
    try {
      await api.createUser(newUser);
      setNewUser({ name: "", email: "", role: "officer", password: "" });
      setSaved("User successfully created and assigned role.");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const runIntegrationTest = async () => {
    setTestingIntegrations(true);
    setTestResult(null);
    try {
      const res = await api.testIntegrations();
      setTestResult(`All ${res.tests_passed} statutory registries tested OK (Avg ping: ${res.average_ping_ms}ms)`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setTestingIntegrations(false);
    }
  };

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-gov-navy">Admin Console</h1>
      <p className="mb-4 text-sm text-slate-500">
        System administration: User identity management &amp; statutory registry integrations.
      </p>

      {saved && <div className="mb-3 rounded bg-green-50 p-2 text-xs text-green-700">{saved}</div>}
      {error && <ErrorBox error={error} />}

      <div className="mb-4 flex gap-2">
        <button
          className={tab === "users" ? "btn-primary" : "btn-outline"}
          onClick={() => setTab("users")}
        >
          User Management ({users?.length ?? 0})
        </button>
        <button
          className={tab === "integrations" ? "btn-primary" : "btn-outline"}
          onClick={() => setTab("integrations")}
        >
          Integration Management ({integrations?.length ?? 0})
        </button>
      </div>

      {tab === "users" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Registered users">
            {!users && <Spinner />}
            {users && users.length === 0 && <Empty />}
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-400">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Email</th>
                  <th className="pb-2">Role</th>
                </tr>
              </thead>
              <tbody>
                {users?.map((u) => (
                  <tr key={u.id} className="border-t border-slate-100">
                    <td className="py-1.5 font-medium">{u.name}</td>
                    <td className="py-1.5 text-xs text-slate-500">{u.email}</td>
                    <td className="py-1.5">
                      <span
                        className={`rounded px-2 py-0.5 text-[11px] font-semibold uppercase ${
                          u.role === "admin"
                            ? "bg-rose-100 text-rose-800"
                            : u.role === "auditor"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <Card title="Provision new user">
            <div className="space-y-3">
              <div>
                <label className="label">Full Name</label>
                <input
                  className="input"
                  value={newUser.name}
                  onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                  placeholder="e.g. S. Sharma"
                />
              </div>
              <div>
                <label className="label">Gov / Official Email</label>
                <input
                  className="input"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  placeholder="e.g. officer@gem.gov.in"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Assigned Role</label>
                  <select
                    className="input"
                    value={newUser.role}
                    onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  >
                    <option value="officer">Officer (Evaluator)</option>
                    <option value="auditor">Auditor (Watchdog)</option>
                    <option value="admin">Admin (Superuser)</option>
                  </select>
                </div>
                <div>
                  <label className="label">Password (min 8 chars)</label>
                  <input
                    className="input"
                    type="password"
                    value={newUser.password}
                    onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  />
                </div>
              </div>
              <button
                className="btn-primary"
                onClick={createUser}
                disabled={!newUser.name || !newUser.email || newUser.password.length < 8}
              >
                Create user
              </button>
            </div>
          </Card>
        </div>
      )}

      {tab === "integrations" && (
        <div className="space-y-4">
          <Card
            title="Statutory Registry Seam &amp; Connectors"
            actions={
              <button
                className="btn-primary"
                onClick={runIntegrationTest}
                disabled={testingIntegrations}
              >
                {testingIntegrations ? "Pinging connectors…" : "⚡ Test All Integrations"}
              </button>
            }
          >
            <div className="mb-4 flex flex-wrap items-center gap-4 text-xs text-slate-600">
              <div>
                Active Adapter Mode:{" "}
                <span className="font-semibold uppercase text-gov-navy">
                  {adapterMeta?.active_adapter || "MOCK"}
                </span>
              </div>
              <div>
                Seam Class:{" "}
                <span className="font-mono text-slate-700">
                  {adapterMeta?.adapter_class || "GovPortalAdapter"}
                </span>
              </div>
            </div>

            {testResult && (
              <div className="mb-4 rounded bg-emerald-50 p-2.5 text-xs font-medium text-emerald-800 border border-emerald-200">
                ✅ {testResult}
              </div>
            )}

            {!integrations && <Spinner />}
            {integrations && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-left uppercase text-slate-500">
                      <th className="px-3 py-2">Registry</th>
                      <th className="px-3 py-2">Statutory Authority</th>
                      <th className="px-3 py-2">Interface Type</th>
                      <th className="px-3 py-2">Latency</th>
                      <th className="px-3 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {integrations.map((item) => (
                      <tr key={item.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium text-gov-navy">{item.name}</td>
                        <td className="px-3 py-2 text-slate-600">{item.authority}</td>
                        <td className="px-3 py-2 font-mono text-[11px] text-slate-500">
                          {item.endpoint_type}
                        </td>
                        <td className="px-3 py-2 font-mono text-slate-600">
                          {item.avg_latency_ms} ms
                        </td>
                        <td className="px-3 py-2">
                          <span className="rounded bg-emerald-100 px-2 py-0.5 font-semibold uppercase text-emerald-800">
                            {item.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}