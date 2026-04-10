import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { LayoutDashboard, Upload, List, BarChart3, Cpu, LogOut, ShieldCheck } from "lucide-react";
import { activateAIProfile, getAIProfiles, getAIStatus, getMyLLMUsageLimitStatus, type AIStatus, type LLMProfile, type LLMUsageLimitStatus } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { toast } from "sonner";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Inicio" },
  { to: "/upload", icon: Upload, label: "Cargar fichero" },
  { to: "/sessions", icon: List, label: "Sesiones" },
  { to: "/analytics", icon: BarChart3, label: "Analítica" },
  { to: "/usage", icon: ShieldCheck, label: "Consumo IA" },
];

export default function Sidebar() {
  const location = useLocation();
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [profiles, setProfiles] = useState<LLMProfile[]>([]);
  const [usageLimit, setUsageLimit] = useState<LLMUsageLimitStatus | null>(null);
  const [switchingProfile, setSwitchingProfile] = useState(false);
  const { user, logout } = useAuth();

  useEffect(() => {
    Promise.all([getAIStatus(), getAIProfiles(), getMyLLMUsageLimitStatus()])
      .then(([status, availableProfiles, limitStatus]) => {
        setAIStatus(status);
        setProfiles(availableProfiles);
        setUsageLimit(limitStatus);
      })
      .catch(() => {});
  }, []);

  const handleActivateProfile = async (profileKey: string) => {
    if (!profileKey || profileKey === aiStatus?.profile_key) return;
    setSwitchingProfile(true);
    try {
      await activateAIProfile(profileKey);
      const [status, availableProfiles, limitStatus] = await Promise.all([getAIStatus(), getAIProfiles(), getMyLLMUsageLimitStatus()]);
      setAIStatus(status);
      setProfiles(availableProfiles);
      setUsageLimit(limitStatus);
      toast.success("Perfil IA actualizado");
    } catch {
      toast.error("No se pudo cambiar el perfil IA");
    } finally {
      setSwitchingProfile(false);
    }
  };

  return (
    <aside className="flex flex-col w-64 min-h-screen border-r border-zinc-200" style={{ backgroundColor: '#243444' }}>
      <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
        <img src="/logo.png" alt="qaracter" className="h-8 w-auto" />
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
                  ? "text-white"
                  : "text-white/60 hover:text-white hover:bg-white/10"
              }`}
              style={isActive ? { backgroundColor: '#fc7c34' } : {}}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t border-white/10 space-y-2">
        {user && (
          <div className="rounded-lg border border-white/10 bg-white/5 p-3">
            <p className="text-xs font-medium text-white">{user.display_name}</p>
            <p className="text-[11px] text-white/50">{user.username}</p>
            <button type="button" onClick={logout} className="mt-2 flex items-center gap-1 text-[11px] text-white/60 hover:text-white">
              <LogOut className="h-3 w-3" />
              Cerrar sesión
            </button>
          </div>
        )}
        {aiStatus && (
          <div className="flex items-center gap-2">
            <Cpu className="h-3 w-3 text-white/50" />
            <span className={`text-xs font-medium ${aiStatus.available ? "text-green-400" : "text-red-400"}`}>
              {aiStatus.label || `${aiStatus.provider} · ${aiStatus.model}`}
            </span>
            <span className={`h-1.5 w-1.5 rounded-full ${aiStatus.available ? "bg-green-400" : "bg-red-400"}`} />
          </div>
        )}
        {profiles.length > 0 && (
          <div className="space-y-1">
            <p className="text-[11px] uppercase tracking-wide text-white/40">Perfil IA demo</p>
            <Select value={aiStatus?.profile_key || profiles.find((profile) => profile.is_active)?.profile_key} onValueChange={handleActivateProfile} disabled={switchingProfile}>
              <SelectTrigger className="border-white/10 bg-white/5 text-white">
                <SelectValue placeholder="Seleccionar perfil" />
              </SelectTrigger>
              <SelectContent>
                {profiles.map((profile) => (
                  <SelectItem key={profile.profile_key} value={profile.profile_key}>
                    {profile.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        {usageLimit && (usageLimit.is_near_limit || usageLimit.is_blocked) && (
          <div className={`rounded-md border px-2 py-2 text-[11px] ${usageLimit.is_blocked ? "border-red-400/40 bg-red-500/10 text-red-200" : "border-amber-400/40 bg-amber-500/10 text-amber-100"}`}>
            <p className="font-medium">
              {usageLimit.is_blocked ? "Límite IA bloqueado" : "Consumo IA alto"}
            </p>
            <p>
              {usageLimit.total_tokens_used.toLocaleString("es-ES")} / {usageLimit.token_limit.toLocaleString("es-ES")} tokens
            </p>
          </div>
        )}
        <p className="text-xs text-white/40">Predatadas</p>
        <p className="text-xs text-white/40">Conciliación de campos clave</p>
      </div>
    </aside>
  );
}
