import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Clients } from "./pages/Clients";
import { ClientDetail } from "./pages/ClientDetail";
import { EmailAccounts } from "./pages/EmailAccounts";
import { Unmatched } from "./pages/Unmatched";

function Gate({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  if (state === "checking") return <p className="muted center">Loading...</p>;
  if (state === "unauthenticated") return <Login />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/clients" element={<Clients />} />
              <Route path="/clients/:id" element={<ClientDetail />} />
              <Route path="/email-accounts" element={<EmailAccounts />} />
              <Route path="/unmatched" element={<Unmatched />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </Gate>
      </AuthProvider>
    </BrowserRouter>
  );
}
