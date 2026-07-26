import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Layout() {
  const { logout } = useAuth();

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="brand">Client CRM</div>
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/clients">Clients</NavLink>
        <NavLink to="/unmatched">Unmatched</NavLink>
        <NavLink to="/email-accounts">Email Accounts</NavLink>
        <button className="link-button" onClick={() => logout()}>
          Sign out
        </button>
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
