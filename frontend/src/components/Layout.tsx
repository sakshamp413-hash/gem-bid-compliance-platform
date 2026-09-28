import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// Nav items mapped to the RBAC matrix capabilities
const NAV = [
  { to: "/tenders",     label: "Tenders",          roles: ["officer", "admin", "auditor"] },
  { to: "/submissions", label: "Submissions",       roles: ["officer", "admin", "auditor"] },
  { to: "/rules",       label: "Compliance Rules",  roles: ["officer", "admin", "auditor"] },
  { to: "/auditor",     label: "Audit Integrity",   roles: ["officer", "admin", "auditor"] },
  { to: "/admin",       label: "Admin Console",     roles: ["admin"] },
];

/** Role-specific badge colour and label */
const ROLE_META: Record<string, { label: string; colour: string }> = {
  officer: { label: "Officer",  colour: "text-gov-accent" },
  auditor: { label: "Auditor",  colour: "text-amber-300" },
  admin:   { label: "Admin",    colour: "text-rose-300" },
};

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const items = NAV.filter((n) => n.roles.includes(user.role));
  const meta = ROLE_META[user.role] ?? { label: user.role, colour: "text-gov-accent" };

  return (
    <div className="min-h-screen">
      <header className="bg-gov-navy text-white shadow-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Link to="/tenders" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded bg-gov-accent font-bold text-gov-navy text-xs">
              प्र
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold tracking-wide">PRAMAAN प्रमाण</span>
                <span className="hidden rounded bg-emerald-800/80 px-1.5 py-0.5 text-[9px] font-semibold tracking-wider text-emerald-200 sm:inline-block">
                  DEMO MODE (SYNTHETIC)
                </span>
              </div>
              <div className="text-[11px] text-slate-300">
                AI-Powered GeM Bid Compliance &amp; Procurement Intelligence
              </div>
            </div>
          </Link>
          <div className="flex items-center gap-4">
            <nav className="hidden items-center gap-1 md:flex">
              {items.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  className={({ isActive }) =>
                    `rounded px-3 py-1.5 text-sm transition-colors ${
                      isActive ? "bg-gov-blue text-white" : "text-slate-300 hover:bg-white/10 hover:text-white"
                    }`
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </nav>
            <div className="text-right">
              <div className="text-sm font-medium">{user.name}</div>
              {/* Role badge — colour-coded per role */}
              <div className={`text-[11px] font-semibold uppercase ${meta.colour}`}>
                {meta.label}
                {user.role === "admin" && (
                  <span className="ml-1 rounded bg-rose-900/60 px-1 py-0.5 text-[9px]">⚠ decisions flagged</span>
                )}
              </div>
            </div>
            <button
              className="rounded border border-white/30 px-2 py-1 text-xs text-slate-200 hover:bg-white/10"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}