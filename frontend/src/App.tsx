import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import TendersPage from "./pages/TendersPage";
import SubmissionsPage from "./pages/SubmissionsPage";
import BidderDetailPage from "./pages/BidderDetailPage";
import RulesPage from "./pages/RulesPage";
import AdminPage from "./pages/AdminPage";
import AuditorPage from "./pages/AuditorPage";

function Protected({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/tenders" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <Protected>
                <Layout />
              </Protected>
            }
          >
            {/* Tenders — Officer ✅, Auditor 👁️, Admin ✅ */}
            <Route path="/tenders" element={<TendersPage />} />
            <Route path="/tenders/:tenderId" element={<SubmissionsPage />} />

            {/* Submissions & Bid/Evidence Review — Officer ✅, Auditor 👁️, Admin 👁️/⚠️ */}
            <Route path="/submissions" element={<SubmissionsPage />} />
            <Route path="/submissions/:id" element={<BidderDetailPage />} />

            {/* Rules Engine — Rule Visibility for all 3 roles; Drafting/Publishing for Admin */}
            <Route
              path="/rules"
              element={
                <Protected roles={["officer", "auditor", "admin"]}>
                  <RulesPage />
                </Protected>
              }
            />

            {/* Audit Verification — Officer ✅, Auditor ✅, Admin ✅ */}
            <Route
              path="/auditor"
              element={
                <Protected roles={["officer", "auditor", "admin"]}>
                  <AuditorPage />
                </Protected>
              }
            />

            {/* Admin Console — User Management ✅ & Integration Management ✅ (Admin Only) */}
            <Route
              path="/admin"
              element={
                <Protected roles={["admin"]}>
                  <AdminPage />
                </Protected>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/tenders" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}