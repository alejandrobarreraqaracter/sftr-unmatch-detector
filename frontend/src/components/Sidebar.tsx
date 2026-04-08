import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  List,
  BarChart3,
  ShieldCheck,
} from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/upload", icon: Upload, label: "Upload" },
  { to: "/sessions", icon: List, label: "Sessions" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-white border-r border-zinc-200">
      <div className="flex items-center gap-2 px-6 py-5 border-b border-zinc-200">
        <ShieldCheck className="h-6 w-6 text-zinc-700" />
        <div>
          <h1 className="text-sm font-semibold text-zinc-900">SFTR Unmatch</h1>
          <p className="text-xs text-zinc-500">Detector</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive =
            item.to === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? "bg-zinc-100 text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t border-zinc-200">
        <p className="text-xs text-zinc-400">EU Regulation 2015/2365</p>
        <p className="text-xs text-zinc-400">SFTR Reconciliation Tool</p>
      </div>
    </aside>
  );
}
