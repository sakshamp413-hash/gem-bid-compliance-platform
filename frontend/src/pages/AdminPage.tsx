import { useEffect, useState } from "react";
import { api, User } from "../api/client";
import { Card, Empty, ErrorBox, Spinner } from "../components/ui";

export default function AdminPage() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [rules, setRules] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"users" | "rules">("users");
  const [newUser, setNewUser] = useState({ name: "", email: "", role: "officer", password: "" });
  const [saved, setSaved] = useState<string | null>(null);

  const load = () => {
    api
      .users()
      .then(setUsers)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    api
      .rules()
      .then((r) => setRules(r.data))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };
  useEffect(load, []);

  const createUser = async () => {
    try {
      await api.createUser(newUser);
      setNewUser({ name: "", email: "", role: "officer", password: "" });
      setSaved("User created");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const saveRules = async () => {
    if (!rules) return;
    try {
      await api.updateRules(rules as Record<string, unknown>);
      setSaved("Rule set saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-gov-navy">Admin</h1>
      <p className="mb-4 text-sm text-slate-500">Manage users and the compliance rule set (rules are data, not code).</p>
      {saved && <div className="mb-3 rounded bg-green-50 p-2 text-xs text-green-700">{saved}</div>}
      {error && <ErrorBox error={error} />}
      <div className="mb-4 flex gap-2">
        <button className={tab === "users" ? "btn-primary" : "btn-outline"} onClick={() => setTab("users")}>
          Users
        </button>
        <button className={tab === "rules" ? "btn-primary" : "btn-outline"} onClick={() => setTab("rules")}>
          Rule set (weights & thresholds)
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
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold uppercase">{u.role}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <Card title="Create user">
            <div className="space-y-3">
              <div>
                <label className="label">Name</label>
                <input className="input" value={newUser.name} onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} />
              </div>
              <div>
                <label className="label">Email</label>
                <input className="input" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Role</label>
                  <select className="input" value={newUser.role} onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}>
                    <option value="officer">officer</option>
                    <option value="admin">admin</option>
                    <option value="auditor">auditor</option>
                  </select>
                </div>
                <div>
                  <label className="label">Password</label>
                  <input className="input" type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} />
                </div>
              </div>
              <button className="btn-primary" onClick={createUser} disabled={!newUser.name || !newUser.email || newUser.password.length < 8}>
                Create user
              </button>
            </div>
          </Card>
        </div>
      )}

      {tab === "rules" && rules && (
        <Card
          title="Rule set (editable YAML-derived data)"
          actions={
            <button className="btn-primary" onClick={saveRules}>
              Save rule set
            </button>
          }
        >
          <p className="mb-3 text-[11px] text-slate-500">
            Thresholds are configurable — verify against current DPIIT / MSME / GeM policy before production use.
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <div className="label">Weights</div>
              <textarea
                className="input min-h-64 font-mono text-[11px]"
                value={JSON.stringify(rules.weights, null, 2)}
                onChange={(e) => {
                  try {
                    const weights = JSON.parse(e.target.value);
                    setRules({ ...rules, weights });
                  } catch {
                    /* keep last valid */
                  }
                }}
              />
            </div>
            <div>
              <div className="label">MSME classification caps (₹ crore)</div>
              <pre className="min-h-64 overflow-auto rounded bg-slate-900 p-3 text-[11px] text-green-300">
                {JSON.stringify(rules.msme, null, 2)}
              </pre>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}