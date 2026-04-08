import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getTopFields, getTrend, getByCounterparty, getBySftType, type TopFieldItem, type TrendItem } from "@/lib/api";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  const [topFields, setTopFields] = useState<TopFieldItem[]>([]);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [counterparties, setCounterparties] = useState<
    { emisor_name: string; receptor_name: string; sessions: number; total_unmatches: number; critical_count: number }[]
  >([]);
  const [sftTypes, setSftTypes] = useState<
    { sft_type: string; sessions: number; total_unmatches: number; critical_count: number }[]
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getTopFields(10), getTrend(30), getByCounterparty(), getBySftType()])
      .then(([tf, tr, cp, st]) => {
        setTopFields(tf);
        setTrend(tr.reverse());
        setCounterparties(cp);
        setSftTypes(st);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-zinc-500">Loading analytics...</p>
      </div>
    );
  }

  const hasData = topFields.length > 0 || trend.length > 0;

  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <BarChart3 className="h-16 w-16 text-zinc-300" />
        <h2 className="text-xl font-semibold text-zinc-700">No analytics data yet</h2>
        <p className="text-zinc-500">Upload and compare SFTR reports to see analytics.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Analytics</h1>
        <p className="text-sm text-zinc-500 mt-1">Unmatch trends and field analysis across all sessions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Unmatch Fields</CardTitle>
          </CardHeader>
          <CardContent>
            {topFields.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topFields} layout="vertical" margin={{ left: 120 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis
                    dataKey="field_name"
                    type="category"
                    tick={{ fontSize: 11 }}
                    width={120}
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    formatter={(value: number) => [value, "Unmatches"]}
                  />
                  <Bar dataKey="count" fill="#A32D2D" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-zinc-500 text-center py-8">No data available</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Unmatch Trend (30 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Line
                    type="monotone"
                    dataKey="total_unmatches"
                    stroke="#A32D2D"
                    strokeWidth={2}
                    name="Unmatches"
                    dot={{ r: 3 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="critical_count"
                    stroke="#854F0B"
                    strokeWidth={2}
                    name="Critical"
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-zinc-500 text-center py-8">No trend data</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">By Counterparty</CardTitle>
          </CardHeader>
          <CardContent>
            {counterparties.length > 0 ? (
              <div className="rounded-lg border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-zinc-50">
                      <TableHead>Emisor</TableHead>
                      <TableHead>Receptor</TableHead>
                      <TableHead className="text-right">Sessions</TableHead>
                      <TableHead className="text-right">Unmatches</TableHead>
                      <TableHead className="text-right">Critical</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {counterparties.map((c, i) => (
                      <TableRow key={i}>
                        <TableCell className="text-xs font-mono max-w-28 truncate">{c.emisor_name}</TableCell>
                        <TableCell className="text-xs font-mono max-w-28 truncate">{c.receptor_name}</TableCell>
                        <TableCell className="text-right text-sm">{c.sessions}</TableCell>
                        <TableCell className="text-right text-sm font-semibold text-red-700">{c.total_unmatches}</TableCell>
                        <TableCell className="text-right text-sm font-semibold text-red-700">{c.critical_count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-sm text-zinc-500 text-center py-8">No counterparty data</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">By SFT Type</CardTitle>
          </CardHeader>
          <CardContent>
            {sftTypes.length > 0 ? (
              <div className="rounded-lg border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-zinc-50">
                      <TableHead>SFT Type</TableHead>
                      <TableHead className="text-right">Sessions</TableHead>
                      <TableHead className="text-right">Unmatches</TableHead>
                      <TableHead className="text-right">Critical</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sftTypes.map((s, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{s.sft_type}</TableCell>
                        <TableCell className="text-right text-sm">{s.sessions}</TableCell>
                        <TableCell className="text-right text-sm font-semibold text-red-700">{s.total_unmatches}</TableCell>
                        <TableCell className="text-right text-sm font-semibold text-red-700">{s.critical_count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <p className="text-sm text-zinc-500 text-center py-8">No SFT type data</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
