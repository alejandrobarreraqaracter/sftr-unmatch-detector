import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Coins, Cpu, Users } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  getLLMUsageByModel,
  getLLMUsageByUser,
  getLLMUsageDaily,
  getMyLLMUsageLimitStatus,
  getLLMUsageOverview,
  type LLMUsageByModelItem,
  type LLMUsageByUserItem,
  type LLMUsageDailyItem,
  type LLMUsageLimitStatus,
  type LLMUsageOverview,
} from "@/lib/api";
import { toast } from "sonner";

function money(value: number) {
  return `$${value.toFixed(4)}`;
}

export default function UsageDashboardPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [overview, setOverview] = useState<LLMUsageOverview | null>(null);
  const [limitStatus, setLimitStatus] = useState<LLMUsageLimitStatus | null>(null);
  const [daily, setDaily] = useState<LLMUsageDailyItem[]>([]);
  const [byUser, setByUser] = useState<LLMUsageByUserItem[]>([]);
  const [byModel, setByModel] = useState<LLMUsageByModelItem[]>([]);

  const load = async (from?: string, to?: string) => {
    try {
      const [overviewData, dailyData, byUserData, byModelData, limitData] = await Promise.all([
        getLLMUsageOverview(from, to),
        getLLMUsageDaily(from, to),
        getLLMUsageByUser(from, to),
        getLLMUsageByModel(from, to),
        getMyLLMUsageLimitStatus(),
      ]);
      setOverview(overviewData);
      setDaily(dailyData);
      setByUser(byUserData);
      setByModel(byModelData);
      setLimitStatus(limitData);
    } catch {
      toast.error("Error al cargar el consumo IA");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">Desde</label>
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-[170px]" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">Hasta</label>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-[170px]" />
        </div>
        <button
          type="button"
          onClick={() => void load(dateFrom || undefined, dateTo || undefined)}
          className="rounded-md bg-[#fc7c34] px-4 py-2 text-sm font-medium text-white"
        >
          Aplicar
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <UsageCard title="Requests" icon={Cpu} value={overview?.total_requests ?? 0} />
        <UsageCard title="Input tokens" icon={Coins} value={(overview?.total_input_tokens ?? 0).toLocaleString("es-ES")} />
        <UsageCard title="Output tokens" icon={Coins} value={(overview?.total_output_tokens ?? 0).toLocaleString("es-ES")} />
        <UsageCard title="Coste total" icon={Users} value={money(overview?.total_cost ?? 0)} />
      </div>

      {limitStatus && (
        <Card className={limitStatus.is_blocked ? "border-red-300 bg-red-50" : limitStatus.is_near_limit ? "border-amber-300 bg-amber-50" : "border-emerald-200 bg-emerald-50"}>
          <CardHeader>
            <CardTitle>Ventana activa de consumo por usuario</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-zinc-700">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Usuario</p>
                <p className="font-semibold">{limitStatus.display_name}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Ventana</p>
                <p className="font-semibold">{limitStatus.window_hours} horas</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Tokens usados</p>
                <p className="font-semibold">{limitStatus.total_tokens_used.toLocaleString("es-ES")} / {limitStatus.token_limit.toLocaleString("es-ES")}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">Reposición</p>
                <p className="font-semibold">{new Date(limitStatus.resets_at).toLocaleString("es-ES")}</p>
              </div>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/80">
              <div
                className={`h-full rounded-full ${limitStatus.is_blocked ? "bg-red-500" : limitStatus.is_near_limit ? "bg-amber-500" : "bg-emerald-500"}`}
                style={{ width: `${Math.min((limitStatus.total_tokens_used / Math.max(limitStatus.token_limit, 1)) * 100, 100)}%` }}
              />
            </div>
            {limitStatus.active_alerts.length > 0 && (
              <div className="space-y-1">
                {limitStatus.active_alerts.map((alert) => (
                  <p key={alert} className={limitStatus.is_blocked ? "text-red-700" : "text-amber-700"}>
                    {alert}
                  </p>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Evolución diaria de coste</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="total_cost" name="Coste" stroke="#fc7c34" strokeWidth={2} />
                <Line type="monotone" dataKey="requests" name="Requests" stroke="#243444" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Tokens por día</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="input_tokens" name="Input" fill="#243444" />
                <Bar dataKey="output_tokens" name="Output" fill="#fc7c34" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Consumo por usuario</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Usuario</TableHead>
                  <TableHead>Requests</TableHead>
                  <TableHead>Input</TableHead>
                  <TableHead>Output</TableHead>
                  <TableHead>Coste</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {byUser.map((item) => (
                  <TableRow key={item.username}>
                    <TableCell>{item.display_name}</TableCell>
                    <TableCell>{item.requests}</TableCell>
                    <TableCell>{item.input_tokens.toLocaleString("es-ES")}</TableCell>
                    <TableCell>{item.output_tokens.toLocaleString("es-ES")}</TableCell>
                    <TableCell>{money(item.total_cost)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Consumo por modelo</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Proveedor</TableHead>
                  <TableHead>Modelo</TableHead>
                  <TableHead>Requests</TableHead>
                  <TableHead>Tokens</TableHead>
                  <TableHead>Coste</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {byModel.map((item) => (
                  <TableRow key={`${item.provider}-${item.model}`}>
                    <TableCell>{item.provider}</TableCell>
                    <TableCell>{item.model}</TableCell>
                    <TableCell>{item.requests}</TableCell>
                    <TableCell>{(item.input_tokens + item.output_tokens).toLocaleString("es-ES")}</TableCell>
                    <TableCell>{money(item.total_cost)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function UsageCard({ title, value, icon: Icon }: { title: string; value: string | number; icon: typeof Cpu }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 pt-6">
        <div className="rounded-full bg-orange-50 p-3">
          <Icon className="h-5 w-5 text-[#fc7c34]" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500">{title}</p>
          <p className="text-2xl font-bold text-zinc-900">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
