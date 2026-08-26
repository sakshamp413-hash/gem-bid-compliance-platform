import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import TendersPage from "./pages/TendersPage";
import SubmissionsPage from "./pages/SubmissionsPage";
import BidderDetailPage from "./pages/BidderDetailPage";
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
            <Route path="/tenders" element={<TendersPage />} />
            <Route path="/tenders/:tenderId" element={<SubmissionsPage />} />
            <Route path="/submissions" element={<SubmissionsPage />} />
            <Route path="/submissions/:id" element={<BidderDetailPage />} />
            <Route
              path="/admin"
              element={
                <Protected roles={["admin"]}>
                  <AdminPage />
                </Protected>
              }
            />
            <Route
              path="/auditor"
              element={
                <Protected roles={["auditor", "admin"]}>
                  <AuditorPage />
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