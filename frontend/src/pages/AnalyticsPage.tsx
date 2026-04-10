import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3, CalendarRange, Download, RefreshCcw, Sparkles, TrendingUp, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  analyticsChat,
  downloadAnalyticsReport,
  generateAnalyticsReport,
  generateAnalyticsComparisonReport,
  generateRegulatorySnapshot,
  getAnalyticsComparison,
  getAnalyticsDaily,
  getAnalyticsOverview,
  getRegulatoryReportPreview,
  getRegulatorySnapshotArtifacts,
  getRegulatorySnapshots,
  getAnalyticsSessionsByDay,
  getByCounterparty,
  getBySftType,
  getTopFields,
  regulatoryReportExportUrl,
  regulatorySnapshotExportUrl,
  warmRegulatorySnapshot,
  type AnalyticsComparison,
  type AnalyticsChatResponse,
  type AnalyticsDelta,
  type AnalyticsDaySession,
  type AnalyticsDailyItem,
  type AnalyticsNarrative,
  type AnalyticsOverview,
  type RegulatoryReportPreview,
  type RegulatorySnapshot,
  type RegulatorySnapshotArtifactsResponse,
  type TopFieldItem,
} from "@/lib/api";
import { toast } from "sonner";

type CounterpartyItem = {
  emisor_name: string;
  receptor_name: string;
  sessions: number;
  total_unmatches: number;
  critical_count: number;
  total_trades: number;
};

type SftTypeItem = {
  sft_type: string;
  sessions: number;
  total_unmatches: number;
  critical_count: number;
  total_trades: number;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  suggestedVisual?: "none" | "daily_trend" | "top_fields" | "counterparties" | "day_sessions" | "comparison";
  animate?: boolean;
  loading?: boolean;
  loadingPhase?: "analyzing" | "preparing";
};

const markdownComponents = {
  h1: ({children}: {children?: React.ReactNode}) => <h1 className="mt-4 mb-2 text-base font-bold text-zinc-900">{children}</h1>,
  h2: ({children}: {children?: React.ReactNode}) => <h2 className="mt-4 mb-2 text-sm font-bold text-zinc-900">{children}</h2>,
  h3: ({children}: {children?: React.ReactNode}) => <h3 className="mt-3 mb-1 text-sm font-semibold text-zinc-800">{children}</h3>,
  p: ({children}: {children?: React.ReactNode}) => <p className="mb-2 text-sm leading-6 text-zinc-700">{children}</p>,
  ul: ({children}: {children?: React.ReactNode}) => <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-zinc-700">{children}</ul>,
  ol: ({children}: {children?: React.ReactNode}) => <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-zinc-700">{children}</ol>,
  li: ({children}: {children?: React.ReactNode}) => <li className="text-sm text-zinc-700">{children}</li>,
  strong: ({children}: {children?: React.ReactNode}) => <strong className="font-semibold text-zinc-900">{children}</strong>,
  table: ({children}: {children?: React.ReactNode}) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-zinc-200">
      <table className="min-w-full border-collapse bg-white text-sm">{children}</table>
    </div>
  ),
  thead: ({children}: {children?: React.ReactNode}) => <thead className="bg-zinc-50">{children}</thead>,
  tbody: ({children}: {children?: React.ReactNode}) => <tbody>{children}</tbody>,
  tr: ({children}: {children?: React.ReactNode}) => <tr className="border-t border-zinc-200">{children}</tr>,
  th: ({children}: {children?: React.ReactNode}) => (
    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-zinc-600">{children}</th>
  ),
  td: ({children}: {children?: React.ReactNode}) => <td className="px-3 py-2 align-top text-sm text-zinc-700">{children}</td>,
  code: ({children}: {children?: React.ReactNode}) => (
    <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[0.85em] text-zinc-800">{children}</code>
  ),
} as const;

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    const match = error.message.match(/API error \d+:\s*(.*)$/s);
    return match?.[1]?.trim() || error.message;
  }
  return fallback;
}

const ANALYTICS_GUIDED_QUESTIONS = [
  "Resume la situación general del rango seleccionado.",
  "¿Qué días concentran más riesgo operativo y por qué?",
  "¿Qué campos parecen ser la principal fuente de discrepancias?",
  "¿Qué contrapartes requieren más atención en este periodo?",
  "¿Cuál sería tu recomendación prioritaria para mejorar la calidad del reporting?",
];

function formatShortDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" });
}

function getChartDayLabel(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const activeLabel = (payload as { activeLabel?: unknown }).activeLabel;
  return typeof activeLabel === "string" ? activeLabel : null;
}

export default function AnalyticsPage() {
  const dailyTrendRef = useRef<HTMLDivElement | null>(null);
  const topFieldsRef = useRef<HTMLDivElement | null>(null);
  const counterpartiesRef = useRef<HTMLDivElement | null>(null);
  const comparisonRef = useRef<HTMLDivElement | null>(null);
  const daySessionsRef = useRef<HTMLDivElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [daily, setDaily] = useState<AnalyticsDailyItem[]>([]);
  const [topFields, setTopFields] = useState<TopFieldItem[]>([]);
  const [counterparties, setCounterparties] = useState<CounterpartyItem[]>([]);
  const [sftTypes, setSftTypes] = useState<SftTypeItem[]>([]);
  const [narrative, setNarrative] = useState<AnalyticsNarrative | null>(null);
  const [regulatoryPreview, setRegulatoryPreview] = useState<RegulatoryReportPreview | null>(null);
  const [regulatorySnapshot, setRegulatorySnapshot] = useState<RegulatorySnapshot | null>(null);
  const [regulatorySnapshots, setRegulatorySnapshots] = useState<RegulatorySnapshot[]>([]);
  const [regulatoryArtifacts, setRegulatoryArtifacts] = useState<Record<number, RegulatorySnapshotArtifactsResponse["artifacts"]>>({});
  const [loading, setLoading] = useState(true);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [generatingRegulatoryPreview, setGeneratingRegulatoryPreview] = useState(false);
  const [savingRegulatorySnapshot, setSavingRegulatorySnapshot] = useState<"plain" | "ai" | null>(null);
  const [warmingSnapshotId, setWarmingSnapshotId] = useState<number | null>(null);
  const [compareFromA, setCompareFromA] = useState("2026-03-01");
  const [compareToA, setCompareToA] = useState("2026-03-15");
  const [compareFromB, setCompareFromB] = useState("2026-03-16");
  const [compareToB, setCompareToB] = useState("2026-03-31");
  const [comparison, setComparison] = useState<AnalyticsComparison | null>(null);
  const [comparing, setComparing] = useState(false);
  const [comparisonNarrative, setComparisonNarrative] = useState<AnalyticsNarrative | null>(null);
  const [generatingComparisonReport, setGeneratingComparisonReport] = useState(false);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [daySessions, setDaySessions] = useState<AnalyticsDaySession[]>([]);
  const [loadingDaySessions, setLoadingDaySessions] = useState(false);
  const [highlightDayPanel, setHighlightDayPanel] = useState(false);
  const [highlightSection, setHighlightSection] = useState<"daily_trend" | "top_fields" | "counterparties" | "comparison" | null>(null);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [askingChat, setAskingChat] = useState(false);

  const loadAnalytics = async (from?: string, to?: string) => {
    setLoading(true);
    try {
      const [overviewData, dailyData, fieldsData, counterpartyData, sftTypeData] = await Promise.all([
        getAnalyticsOverview(from, to),
        getAnalyticsDaily(from, to),
        getTopFields(10, from, to),
        getByCounterparty(from, to),
        getBySftType(from, to),
      ]);
      setOverview(overviewData);
      setDaily(dailyData);
      setTopFields(fieldsData);
      setCounterparties(counterpartyData);
      setSftTypes(sftTypeData);
    } catch {
      toast.error("Error al cargar la analítica");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  useEffect(() => {
    const loadSnapshots = async () => {
      try {
        const items = await getRegulatorySnapshots();
        setRegulatorySnapshots(items);
        const artifactEntries = await Promise.all(
          items.slice(0, 5).map(async (snapshot) => [snapshot.id, (await getRegulatorySnapshotArtifacts(snapshot.id)).artifacts] as const)
        );
        setRegulatoryArtifacts(Object.fromEntries(artifactEntries));
      } catch {
        // silent on initial load
      }
    };
    void loadSnapshots();
  }, []);

  useEffect(() => {
    if (!selectedDay || loadingDaySessions) return;
    daySessionsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    setHighlightDayPanel(true);
    const timeoutId = window.setTimeout(() => setHighlightDayPanel(false), 1800);
    return () => window.clearTimeout(timeoutId);
  }, [selectedDay, loadingDaySessions, daySessions.length]);

  useEffect(() => {
    if (chatMessages.length === 0) return;
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chatMessages]);

  const hasData = (overview?.sessions || 0) > 0;

  const topDays = useMemo(
    () => [...daily].sort((a, b) => b.total_unmatches - a.total_unmatches).slice(0, 5),
    [daily]
  );
  const worstDay = topDays[0];
  const topField = topFields[0];
  const topCounterparty = counterparties[0];

  const triggerSectionHighlight = (section: "daily_trend" | "top_fields" | "counterparties" | "comparison") => {
    setHighlightSection(section);
    window.setTimeout(() => setHighlightSection((current) => (current === section ? null : current)), 1800);
  };

  const scrollToVisual = async (visual?: ChatMessage["suggestedVisual"]) => {
    if (!visual || visual === "none") return;

    const scrollToSection = (ref: React.RefObject<HTMLDivElement | null>, section: "daily_trend" | "top_fields" | "counterparties" | "comparison") => {
      ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      triggerSectionHighlight(section);
    };

    if (visual === "day_sessions") {
      if (selectedDay) {
        daySessionsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        setHighlightDayPanel(true);
        window.setTimeout(() => setHighlightDayPanel(false), 1800);
        return;
      }
      if (worstDay?.date) {
        await handleSelectDay(worstDay.date);
      }
      return;
    }

    if (visual === "comparison") {
      if (!comparison && compareFromA && compareToA && compareFromB && compareToB) {
        await handleComparePeriods();
        window.setTimeout(() => scrollToSection(comparisonRef, "comparison"), 300);
        return;
      }
      scrollToSection(comparisonRef, "comparison");
      return;
    }

    if (visual === "daily_trend") {
      scrollToSection(dailyTrendRef, "daily_trend");
      return;
    }

    if (visual === "top_fields") {
      scrollToSection(topFieldsRef, "top_fields");
      return;
    }

    if (visual === "counterparties") {
      scrollToSection(counterpartiesRef, "counterparties");
    }
  };

  const sectionHighlightClass = (section: "daily_trend" | "top_fields" | "counterparties" | "comparison") =>
    highlightSection === section
      ? "border-[#fc7c34] bg-orange-50/60 ring-4 ring-[#fc7c34]/25 ring-offset-4 ring-offset-white animate-analytics-highlight transition-all duration-500"
      : "transition-all duration-500";

  const handleApplyFilters = () => {
    setNarrative(null);
    loadAnalytics(dateFrom || undefined, dateTo || undefined);
  };

  const handleResetFilters = () => {
    setDateFrom("");
    setDateTo("");
    setNarrative(null);
    loadAnalytics();
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const result = await generateAnalyticsReport(dateFrom || undefined, dateTo || undefined);
      setNarrative(result);
    } catch (error) {
      toast.error(getErrorMessage(error, "Error al generar el informe IA"));
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleGenerateRegulatoryPreview = async () => {
    setGeneratingRegulatoryPreview(true);
    try {
      const result = await getRegulatoryReportPreview(dateFrom || undefined, dateTo || undefined);
      setRegulatoryPreview(result);
      setRegulatorySnapshot(null);
    } catch {
      toast.error("Error al generar el preview regulatorio");
    } finally {
      setGeneratingRegulatoryPreview(false);
    }
  };

  const handleSaveRegulatorySnapshot = async (includeAiNarrative: boolean) => {
    setSavingRegulatorySnapshot(includeAiNarrative ? "ai" : "plain");
    try {
      const snapshot = await generateRegulatorySnapshot(
        dateFrom || undefined,
        dateTo || undefined,
        includeAiNarrative,
        "analytics-ui"
      );
      setRegulatorySnapshot(snapshot);
      setRegulatorySnapshots((prev) => [snapshot, ...prev.filter((item) => item.id !== snapshot.id)]);
      toast.success(includeAiNarrative ? "Snapshot regulatorio con IA guardado" : "Snapshot regulatorio guardado");
    } catch (error) {
      toast.error(getErrorMessage(error, "Error al guardar el snapshot regulatorio"));
    } finally {
      setSavingRegulatorySnapshot(null);
    }
  };

  const handleWarmSnapshot = async (snapshotId: number) => {
    setWarmingSnapshotId(snapshotId);
    try {
      await warmRegulatorySnapshot(snapshotId);
      window.setTimeout(async () => {
        try {
          const artifacts = await getRegulatorySnapshotArtifacts(snapshotId);
          setRegulatoryArtifacts((prev) => ({ ...prev, [snapshotId]: artifacts.artifacts }));
        } catch {
          // ignore
        } finally {
          setWarmingSnapshotId(null);
        }
      }, 1200);
      toast.success("Calentando artefactos del snapshot");
    } catch {
      setWarmingSnapshotId(null);
      toast.error("Error al precalentar el snapshot");
    }
  };

  const handleDownloadReport = async (format: "pdf" | "doc") => {
    if (!narrative) return;
    try {
      await downloadAnalyticsReport(format, narrative);
    } catch {
      toast.error(`Error al descargar el informe en ${format.toUpperCase()}`);
    }
  };

  const handleComparePeriods = async () => {
    if (!compareFromA || !compareToA || !compareFromB || !compareToB) {
      toast.error("Completa las cuatro fechas para comparar periodos");
      return;
    }
    setComparing(true);
    try {
      const result = await getAnalyticsComparison(compareFromA, compareToA, compareFromB, compareToB);
      setComparison(result);
      setComparisonNarrative(null);
    } catch {
      toast.error("Error al comparar periodos");
    } finally {
      setComparing(false);
    }
  };

  const handleGenerateComparisonReport = async () => {
    if (!comparison) return;
    setGeneratingComparisonReport(true);
    try {
      const result = await generateAnalyticsComparisonReport(compareFromA, compareToA, compareFromB, compareToB);
      setComparisonNarrative(result);
    } catch (error) {
      toast.error(getErrorMessage(error, "Error al generar el informe comparativo IA"));
    } finally {
      setGeneratingComparisonReport(false);
    }
  };

  const handleSelectDay = async (day: string) => {
    setSelectedDay(day);
    setLoadingDaySessions(true);
    try {
      const sessions = await getAnalyticsSessionsByDay(day);
      setDaySessions(sessions);
    } catch {
      toast.error("Error al cargar las sesiones del día");
    } finally {
      setLoadingDaySessions(false);
    }
  };

  const handleAskAnalyticsChat = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;
    const assistantMessageId = `assistant-${Date.now()}`;
    const requestStartedAt = Date.now();
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setChatMessages((prev) => [...prev, userMessage]);
    setChatQuestion("");
    setAskingChat(true);
    setChatMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        loading: true,
        suggestedVisual: "none",
        loadingPhase: "analyzing",
      },
    ]);
    const phaseTimeoutId = window.setTimeout(() => {
      setChatMessages((prev) => prev.map((message) => (
        message.id === assistantMessageId && message.loading
          ? { ...message, loadingPhase: "preparing" }
          : message
      )));
    }, 1400);
    try {
      const hasComparisonContext = Boolean(comparison && compareFromA && compareToA && compareFromB && compareToB);
      const comparisonContext = hasComparisonContext
        ? { fromA: compareFromA, toA: compareToA, fromB: compareFromB, toB: compareToB }
        : undefined;
      const resultWithContext: AnalyticsChatResponse = await analyticsChat(
        trimmed,
        dateFrom || undefined,
        dateTo || undefined,
        selectedDay || undefined,
        comparisonContext
      );
      const elapsed = Date.now() - requestStartedAt;
      const minimumLoadingMs = 2200;
      if (elapsed < minimumLoadingMs) {
        await new Promise((resolve) => window.setTimeout(resolve, minimumLoadingMs - elapsed));
      }
      setChatMessages((prev) => prev.map((message) => (
        message.id === assistantMessageId
          ? {
              ...message,
              content: resultWithContext.answer,
              suggestedVisual: resultWithContext.suggested_visual,
              animate: true,
              loading: false,
              loadingPhase: undefined,
            }
          : message
      )));
    } catch (error) {
      setChatMessages((prev) => prev.map((message) => (
        message.id === assistantMessageId
          ? {
              ...message,
              content: getErrorMessage(error, "No he podido generar la respuesta analítica en este momento."),
              animate: false,
              loading: false,
              loadingPhase: undefined,
            }
          : message
      )));
      toast.error(getErrorMessage(error, "Error al consultar el chat analítico"));
    } finally {
      window.clearTimeout(phaseTimeoutId);
      setAskingChat(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-zinc-500">Cargando analítica...</p>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <BarChart3 className="h-16 w-16 text-zinc-300" />
        <h2 className="text-xl font-semibold text-zinc-700">Sin datos analíticos todavía</h2>
        <p className="text-zinc-500">Carga sesiones diarias para ver evolución, unpair, severidades y tendencias.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Analítica</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Evolución diaria, calidad operativa y focos de discrepancia en el rango seleccionado
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <p className="text-xs font-medium text-zinc-500">Desde</p>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="h-9 w-40" />
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-zinc-500">Hasta</p>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="h-9 w-40" />
          </div>
          <Button variant="outline" size="sm" onClick={handleApplyFilters}>
            <CalendarRange className="h-4 w-4 mr-1" />
            Aplicar
          </Button>
          <Button variant="outline" size="sm" onClick={handleResetFilters}>
            <RefreshCcw className="h-4 w-4 mr-1" />
            Reset
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateReport}
            disabled={generatingReport}
            className="border-[#fc7c34] text-[#fc7c34] hover:bg-orange-50"
          >
            <Sparkles className="h-4 w-4 mr-1" />
            {generatingReport ? "Generando..." : "Informe IA"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateRegulatoryPreview}
            disabled={generatingRegulatoryPreview}
            className="border-[#243444] text-[#243444] hover:bg-zinc-100"
          >
            <Download className="h-4 w-4 mr-1" />
            {generatingRegulatoryPreview ? "Preparando..." : "Preview regulatorio"}
          </Button>
        </div>
      </div>

      {overview && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
          <MetricCard label="Sesiones" value={overview.sessions} />
          <MetricCard label="Operaciones" value={overview.total_trades} />
          <MetricCard label="Con discrepancias" value={overview.trades_with_unmatches} color="red" />
          <MetricCard label="Unpair" value={overview.unpair_trades} color="purple" />
          <MetricCard label="Discrepancias" value={overview.total_unmatches} color="red" />
          <MetricCard label="Críticas" value={overview.critical_count} color="red" />
          <MetricCard label="Advertencias" value={overview.warning_count} color="amber" />
          <MetricCard label="Resueltas" value={overview.resolved_fields} color="green" />
          <MetricCard label="Pendientes" value={overview.pending_fields} color="blue" />
          <MetricCard label="Calidad %" value={overview.quality_rate} suffix="%" />
          <MetricCard label="Resolución %" value={overview.resolution_rate} suffix="%" color="green" />
          <MetricCard label="Limpias" value={overview.clean_trades} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <InsightCard
          title="Peor día"
          value={worstDay ? new Date(`${worstDay.date}T00:00:00`).toLocaleDateString("es-ES") : "—"}
          detail={worstDay ? `${worstDay.total_unmatches} discrepancias · ${worstDay.critical_count} críticas · ${worstDay.unpair_trades} unpair` : "Sin datos"}
        />
        <InsightCard
          title="Campo más problemático"
          value={topField?.field_name || "—"}
          detail={topField ? `${topField.count} discrepancias acumuladas` : "Sin datos"}
        />
        <InsightCard
          title="Contraparte con más incidencias"
          value={topCounterparty ? `${topCounterparty.emisor_name} vs ${topCounterparty.receptor_name}` : "—"}
          detail={topCounterparty ? `${topCounterparty.total_unmatches} discrepancias en ${topCounterparty.sessions} sesiones` : "Sin datos"}
        />
      </div>

      {narrative && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2 text-orange-800">
                <Sparkles className="h-4 w-4" /> Informe analítico IA
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" className="h-7 border-orange-200 bg-white text-orange-700 hover:bg-orange-100" onClick={() => handleDownloadReport("pdf")}>
                  <Download className="h-3 w-3 mr-1" />
                  PDF
                </Button>
                <Button size="sm" variant="outline" className="h-7 border-orange-200 bg-white text-orange-700 hover:bg-orange-100" onClick={() => handleDownloadReport("doc")}>
                  <Download className="h-3 w-3 mr-1" />
                  Word
                </Button>
                <button onClick={() => setNarrative(null)} className="text-orange-400 hover:text-orange-600">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <p className="text-xs text-orange-700">
              {narrative.date_from || "inicio disponible"} - {narrative.date_to || "fin disponible"} · {narrative.provider} · {narrative.model}
            </p>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none text-zinc-700 leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{narrative.narrative}</ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}

      {regulatoryPreview && (
        <Card className="border-[#243444]/20 bg-white">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle className="text-sm flex items-center gap-2 text-[#243444]">
                  <Download className="h-4 w-4" /> Reporte regulatorio
                </CardTitle>
                <p className="mt-1 text-xs text-zinc-500">
                  {regulatoryPreview.date_from || "inicio disponible"} - {regulatoryPreview.date_to || "fin disponible"} · generado {new Date(regulatoryPreview.generated_at).toLocaleString("es-ES")}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={regulatoryReportExportUrl(dateFrom || undefined, dateTo || undefined)}
                  className="inline-flex h-8 items-center rounded-md border border-[#243444] px-3 text-sm font-medium text-[#243444] transition hover:bg-zinc-100"
                >
                  Descargar XLSX
                </a>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleSaveRegulatorySnapshot(false)}
                  disabled={savingRegulatorySnapshot !== null}
                  className="h-8"
                >
                  {savingRegulatorySnapshot === "plain" ? "Guardando..." : "Guardar snapshot"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => handleSaveRegulatorySnapshot(true)}
                  disabled={savingRegulatorySnapshot !== null}
                  className="h-8"
                >
                  {savingRegulatorySnapshot === "ai" ? "Generando IA..." : "Snapshot + IA"}
                </Button>
                <button onClick={() => setRegulatoryPreview(null)} className="text-zinc-400 hover:text-zinc-600">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
              <MetricCard label="Sesiones" value={regulatoryPreview.sessions} />
              <MetricCard label="Operaciones" value={regulatoryPreview.overview.total_trades} />
              <MetricCard label="Open items" value={regulatoryPreview.open_items_count} color="blue" />
              <MetricCard label="Críticas abiertas" value={regulatoryPreview.critical_open_items_count} color="red" />
              <MetricCard label="Resueltas" value={regulatoryPreview.overview.resolved_fields} color="green" />
              <MetricCard label="Pendientes" value={regulatoryPreview.overview.pending_fields} color="amber" />
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Top campos</p>
                <div className="mt-3 space-y-2">
                  {regulatoryPreview.top_fields.slice(0, 5).map((field) => (
                    <div key={`${field.table_number}-${field.field_name}`} className="flex items-center justify-between gap-3 text-sm">
                      <span className="truncate text-zinc-700">{field.field_name}</span>
                      <span className="shrink-0 font-semibold text-red-700">{field.count}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Open items recientes</p>
                <div className="mt-3 space-y-2">
                  {regulatoryPreview.open_items.slice(0, 5).map((item) => (
                    <div key={`${item.trade_id}-${item.field_name}-${item.field_number}`} className="rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-zinc-800">{item.field_name}</span>
                        <span className={item.severity === "CRITICAL" ? "font-semibold text-red-700" : "font-semibold text-amber-700"}>{item.severity}</span>
                      </div>
                      <p className="mt-1 text-xs text-zinc-500">
                        {item.business_date} · UTI {item.uti || "—"} · {item.status} · {item.assignee || "Sin asignar"}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {regulatorySnapshot && (
              <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-orange-800">
                      Snapshot #{regulatorySnapshot.id} guardado
                    </p>
                    <p className="mt-1 text-xs text-orange-700">
                      {new Date(regulatorySnapshot.created_at).toLocaleString("es-ES")}
                      {regulatorySnapshot.narrative_model ? ` · ${regulatorySnapshot.narrative_provider} / ${regulatorySnapshot.narrative_model}` : " · narración determinista"}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <a href={regulatorySnapshotExportUrl(regulatorySnapshot.id, "xlsx")} className="inline-flex h-8 items-center rounded-md border border-orange-200 bg-white px-3 text-sm font-medium text-orange-700 transition hover:bg-orange-100">
                      XLSX
                    </a>
                    <a href={regulatorySnapshotExportUrl(regulatorySnapshot.id, "pdf")} className="inline-flex h-8 items-center rounded-md border border-orange-200 bg-white px-3 text-sm font-medium text-orange-700 transition hover:bg-orange-100">
                      PDF
                    </a>
                    <a href={regulatorySnapshotExportUrl(regulatorySnapshot.id, "doc")} className="inline-flex h-8 items-center rounded-md border border-orange-200 bg-white px-3 text-sm font-medium text-orange-700 transition hover:bg-orange-100">
                      Word
                    </a>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="rounded-lg border border-orange-200 bg-white p-4">
                    <p className="text-xs font-medium uppercase tracking-wide text-orange-700">Riesgo residual</p>
                    <div className="mt-3 flex items-center gap-3">
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                        regulatorySnapshot.payload.risk_residual?.level === "ALTO"
                          ? "bg-red-100 text-red-700"
                          : regulatorySnapshot.payload.risk_residual?.level === "MEDIO"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-emerald-100 text-emerald-700"
                      }`}>
                        {regulatorySnapshot.payload.risk_residual?.level || "N/D"}
                      </span>
                      <span className="text-sm text-zinc-600">
                        {regulatorySnapshot.payload.risk_residual?.critical_open_items || 0} críticas abiertas · {regulatorySnapshot.payload.risk_residual?.unresolved_unpair_trades || 0} unpair pendientes
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-zinc-700">
                      {regulatorySnapshot.payload.risk_residual?.summary}
                    </p>
                  </div>

                  <div className="rounded-lg border border-orange-200 bg-white p-4">
                    <p className="text-xs font-medium uppercase tracking-wide text-orange-700">Comparación con periodo anterior</p>
                    {regulatorySnapshot.payload.comparison_to_previous_period ? (
                      <div className="mt-3 space-y-2 text-sm text-zinc-700">
                        <p>
                          {regulatorySnapshot.payload.comparison_to_previous_period.previous_date_from} - {regulatorySnapshot.payload.comparison_to_previous_period.previous_date_to}
                        </p>
                        <p>Discrepancias: {formatSignedDelta(regulatorySnapshot.payload.comparison_to_previous_period.deltas.total_unmatches?.abs)}</p>
                        <p>Críticas: {formatSignedDelta(regulatorySnapshot.payload.comparison_to_previous_period.deltas.critical_count?.abs)}</p>
                        <p>UNPAIR: {formatSignedDelta(regulatorySnapshot.payload.comparison_to_previous_period.deltas.unpair_trades?.abs)}</p>
                        <p>Calidad: {formatSignedDelta(regulatorySnapshot.payload.comparison_to_previous_period.deltas.quality_rate?.abs)} pp</p>
                        <p>Resolución: {formatSignedDelta(regulatorySnapshot.payload.comparison_to_previous_period.deltas.resolution_rate?.abs)} pp</p>
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-zinc-500">No hay periodo anterior suficiente para comparar.</p>
                    )}
                  </div>
                </div>

                {regulatorySnapshot.narrative_markdown && (
                  <div className="mt-4 rounded-lg border border-orange-200 bg-white p-4">
                    <p className="text-xs font-medium uppercase tracking-wide text-orange-700">Narrativa congelada del snapshot</p>
                    <div className="prose prose-sm mt-3 max-w-none text-zinc-700">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{regulatorySnapshot.narrative_markdown}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            )}

            {regulatorySnapshots.length > 0 && (
              <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Histórico reciente de snapshots</p>
                    <p className="mt-1 text-sm text-zinc-600">Reutiliza snapshots ya congelados y evita recalcular exportes.</p>
                  </div>
                </div>
                <div className="mt-4 space-y-3">
                  {regulatorySnapshots.slice(0, 5).map((snapshot) => {
                    const artifacts = regulatoryArtifacts[snapshot.id] || [];
                    return (
                      <div key={snapshot.id} className="rounded-lg border border-zinc-200 bg-white p-3">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                          <div>
                            <p className="text-sm font-semibold text-zinc-900">
                              Snapshot #{snapshot.id} · {snapshot.date_from || "—"} - {snapshot.date_to || "—"}
                            </p>
                            <p className="mt-1 text-xs text-zinc-500">
                              {new Date(snapshot.created_at).toLocaleString("es-ES")} · {snapshot.created_by || "sin autor"} · {snapshot.source_trades_count} operaciones
                            </p>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => handleWarmSnapshot(snapshot.id)}
                              disabled={warmingSnapshotId === snapshot.id}
                            >
                              {warmingSnapshotId === snapshot.id ? "Calentando..." : "Precalentar"}
                            </Button>
                            <a href={regulatorySnapshotExportUrl(snapshot.id, "xlsx")} className="inline-flex h-8 items-center rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100">XLSX</a>
                            <a href={regulatorySnapshotExportUrl(snapshot.id, "pdf")} className="inline-flex h-8 items-center rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100">PDF</a>
                            <a href={regulatorySnapshotExportUrl(snapshot.id, "doc")} className="inline-flex h-8 items-center rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100">Word</a>
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {["xlsx", "pdf", "doc"].map((format) => {
                            const artifact = artifacts.find((item) => item.format === format);
                            return (
                              <span key={format} className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                                artifact?.cached ? "bg-emerald-100 text-emerald-700" : "bg-zinc-100 text-zinc-600"
                              }`}>
                                {format.toUpperCase()} {artifact?.cached ? "cacheado" : "sin cache"}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Chat analítico guiado</CardTitle>
          <p className="text-sm text-zinc-500 mt-1">
            Haz preguntas sobre el rango seleccionado. El asistente responde sobre los agregados reales de la analítica actual.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {ANALYTICS_GUIDED_QUESTIONS.map((question) => (
              <Button
                key={question}
                type="button"
                variant="outline"
                size="sm"
                className="h-auto whitespace-normal text-left text-xs"
                onClick={() => handleAskAnalyticsChat(question)}
                disabled={askingChat}
              >
                {question}
              </Button>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto]">
            <Textarea
              value={chatQuestion}
              onChange={(e) => setChatQuestion(e.target.value)}
              placeholder="Escribe una pregunta analítica sobre el rango seleccionado..."
              className="min-h-[88px] bg-white"
            />
            <Button
              type="button"
              onClick={() => handleAskAnalyticsChat(chatQuestion)}
              disabled={askingChat || !chatQuestion.trim()}
              className="lg:self-end"
            >
              {askingChat ? "Consultando..." : "Preguntar"}
            </Button>
          </div>

          <div className="space-y-3">
            {chatMessages.length === 0 ? (
              <div className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 px-4 py-6 text-sm text-zinc-500">
                Todavía no hay preguntas. Usa una sugerencia o escribe una consulta libre.
              </div>
            ) : (
              chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={message.role === "user"
                    ? "rounded-lg border border-zinc-200 bg-white px-4 py-3"
                    : "rounded-lg border border-orange-200 bg-orange-50 px-4 py-3"}
                >
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    {message.role === "user" ? "Pregunta" : "Respuesta IA"}
                  </p>
                  {message.role === "user" ? (
                    <p className="text-sm text-zinc-800">{message.content}</p>
                  ) : (
                    <div className="space-y-3">
                      {message.loading ? (
                        <div className="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-white px-3 py-1.5 text-sm font-medium text-orange-700">
                          <span className="h-2 w-2 animate-pulse rounded-full bg-[#fc7c34]" />
                          {message.loadingPhase === "preparing"
                            ? "Preparando la respuesta..."
                            : "Analizando el contexto y los datos disponibles..."}
                        </div>
                      ) : (
                        <TypingMarkdown content={message.content} animate={Boolean(message.animate)} />
                      )}
                      {!message.loading && message.suggestedVisual && message.suggestedVisual !== "none" && (
                        <button
                          type="button"
                          onClick={() => void scrollToVisual(message.suggestedVisual)}
                          className="inline-flex rounded-full border border-orange-200 bg-white px-2.5 py-1 text-xs font-medium text-orange-700 transition hover:border-orange-300 hover:bg-orange-100"
                        >
                          Visual sugerido: {CHAT_VISUAL_LABELS[message.suggestedVisual]}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={chatEndRef} />
          </div>
        </CardContent>
      </Card>

      <div ref={comparisonRef}>
      <Card className={sectionHighlightClass("comparison")}>
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <CardTitle className="text-base">Comparación entre periodos</CardTitle>
              <p className="text-sm text-zinc-500 mt-1">Compara dos ventanas temporales y mide si la calidad mejora o empeora.</p>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500">Desde A</p>
                <Input type="date" value={compareFromA} onChange={(e) => setCompareFromA(e.target.value)} className="h-9 w-36" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500">Hasta A</p>
                <Input type="date" value={compareToA} onChange={(e) => setCompareToA(e.target.value)} className="h-9 w-36" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500">Desde B</p>
                <Input type="date" value={compareFromB} onChange={(e) => setCompareFromB(e.target.value)} className="h-9 w-36" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500">Hasta B</p>
                <Input type="date" value={compareToB} onChange={(e) => setCompareToB(e.target.value)} className="h-9 w-36" />
              </div>
              <Button variant="outline" size="sm" onClick={handleComparePeriods} disabled={comparing}>
                <CalendarRange className="h-4 w-4 mr-1" />
                {comparing ? "Comparando..." : "Comparar"}
              </Button>
            </div>
          </div>
        </CardHeader>
        {comparison && (
          <CardContent className="space-y-6">
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateComparisonReport}
                disabled={generatingComparisonReport}
                className="border-[#fc7c34] text-[#fc7c34] hover:bg-orange-50"
              >
                <Sparkles className="h-4 w-4 mr-1" />
                {generatingComparisonReport ? "Generando..." : "Informe comparativo IA"}
              </Button>
            </div>

            {comparisonNarrative && (
              <Card className="border-orange-200 bg-orange-50 shadow-none">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2 text-orange-800">
                      <Sparkles className="h-4 w-4" /> Informe comparativo IA
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="outline" className="h-7 border-orange-200 bg-white text-orange-700 hover:bg-orange-100" onClick={() => downloadAnalyticsReport("pdf", comparisonNarrative).catch(() => toast.error("Error al descargar el informe comparativo en PDF"))}>
                        <Download className="h-3 w-3 mr-1" />
                        PDF
                      </Button>
                      <Button size="sm" variant="outline" className="h-7 border-orange-200 bg-white text-orange-700 hover:bg-orange-100" onClick={() => downloadAnalyticsReport("doc", comparisonNarrative).catch(() => toast.error("Error al descargar el informe comparativo en Word"))}>
                        <Download className="h-3 w-3 mr-1" />
                        Word
                      </Button>
                      <button onClick={() => setComparisonNarrative(null)} className="text-orange-400 hover:text-orange-600">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none text-zinc-700 leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{comparisonNarrative.narrative}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
              <ComparisonMetricCard label="Discrepancias" delta={comparison.deltas.total_unmatches} worseWhenPositive />
              <ComparisonMetricCard label="Críticas" delta={comparison.deltas.critical_count} worseWhenPositive />
              <ComparisonMetricCard label="Unpair" delta={comparison.deltas.unpair_trades} worseWhenPositive />
              <ComparisonMetricCard label="Calidad %" delta={comparison.deltas.quality_rate} />
              <ComparisonMetricCard label="Resolución %" delta={comparison.deltas.resolution_rate} />
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <Card className="border-zinc-200 shadow-none">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Resumen de periodos</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-lg border overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-zinc-50">
                          <TableHead>Métrica</TableHead>
                          <TableHead className="text-right">Periodo A</TableHead>
                          <TableHead className="text-right">Periodo B</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        <ComparisonRow label="Sesiones" a={comparison.period_a.sessions} b={comparison.period_b.sessions} />
                        <ComparisonRow label="Operaciones" a={comparison.period_a.total_trades} b={comparison.period_b.total_trades} />
                        <ComparisonRow label="Discrepancias" a={comparison.period_a.total_unmatches} b={comparison.period_b.total_unmatches} />
                        <ComparisonRow label="Críticas" a={comparison.period_a.critical_count} b={comparison.period_b.critical_count} />
                        <ComparisonRow label="Unpair" a={comparison.period_a.unpair_trades} b={comparison.period_b.unpair_trades} />
                        <ComparisonRow label="Calidad %" a={comparison.period_a.quality_rate} b={comparison.period_b.quality_rate} />
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-zinc-200 shadow-none">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Campos que más cambian</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-lg border overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-zinc-50">
                          <TableHead>Campo</TableHead>
                          <TableHead className="text-right">A</TableHead>
                          <TableHead className="text-right">B</TableHead>
                          <TableHead className="text-right">Delta</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {comparison.top_fields_comparison.slice(0, 10).map((item) => (
                          <TableRow key={`${item.table_number}-${item.field_name}`}>
                            <TableCell className="text-sm">
                              <div className="font-medium">{item.field_name}</div>
                              <div className="text-xs text-zinc-500">Tabla {item.table_number}</div>
                            </TableCell>
                            <TableCell className="text-right text-sm">{item.count_a}</TableCell>
                            <TableCell className="text-right text-sm">{item.count_b}</TableCell>
                            <TableCell className={`text-right text-sm font-semibold ${item.delta > 0 ? "text-red-700" : item.delta < 0 ? "text-green-700" : "text-zinc-500"}`}>
                              {item.delta > 0 ? "+" : ""}{item.delta}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </div>
          </CardContent>
        )}
      </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div ref={dailyTrendRef}>
        <Card className={sectionHighlightClass("daily_trend")}>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-[#fc7c34]" />
              Evolución diaria
            </CardTitle>
            <p className="text-sm text-zinc-500">Haz clic en un punto del gráfico para ver las sesiones de ese día.</p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart
                data={daily}
                onClick={(state) => {
                  const day = getChartDayLabel(state);
                  if (day) handleSelectDay(day);
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="date" tickFormatter={formatShortDate} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  labelFormatter={(value) => new Date(`${value}T00:00:00`).toLocaleDateString("es-ES")}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <Legend />
                <Line type="monotone" dataKey="total_unmatches" name="Discrepancias" stroke="#dc2626" strokeWidth={2.5} dot={{ r: 3, cursor: "pointer" }} activeDot={{ r: 5, cursor: "pointer" }} />
                <Line type="monotone" dataKey="critical_count" name="Críticas" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 3, cursor: "pointer" }} activeDot={{ r: 5, cursor: "pointer" }} />
                <Line type="monotone" dataKey="unpair_trades" name="Unpair" stroke="#7c3aed" strokeWidth={2.5} dot={{ r: 3, cursor: "pointer" }} activeDot={{ r: 5, cursor: "pointer" }} />
                <Line type="monotone" dataKey="unmatch_trades" name="Unmatch" stroke="#0f766e" strokeWidth={2.5} dot={{ r: 3, cursor: "pointer" }} activeDot={{ r: 5, cursor: "pointer" }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Distribución operativa diaria</CardTitle>
            <p className="text-sm text-zinc-500">Haz clic en una barra para abrir el detalle de sesiones del día.</p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                data={daily}
                onClick={(state) => {
                  const day = getChartDayLabel(state);
                  if (day) handleSelectDay(day);
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="date" tickFormatter={formatShortDate} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  labelFormatter={(value) => new Date(`${value}T00:00:00`).toLocaleDateString("es-ES")}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <Legend />
                <Bar dataKey="total_trades" name="Operaciones" fill="#243444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="trades_with_unmatches" name="Con discrepancias" fill="#fc7c34" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div ref={topFieldsRef}>
        <Card className={sectionHighlightClass("top_fields")}>
          <CardHeader>
            <CardTitle className="text-base">Campos con más incidencias</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={topFields} layout="vertical" margin={{ left: 170 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="field_name" type="category" tick={{ fontSize: 11 }} width={170} />
                <Tooltip formatter={(value: number) => [value, "Discrepancias"]} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                <Bar dataKey="count" fill="#fc7c34" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Días con más incidencias</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50">
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Sesiones</TableHead>
                    <TableHead className="text-right">Operaciones</TableHead>
                    <TableHead className="text-right">Discrepancias</TableHead>
                    <TableHead className="text-right">Críticas</TableHead>
                    <TableHead className="text-right">Unpair</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topDays.map((item) => (
                    <TableRow key={item.date} className="cursor-pointer hover:bg-zinc-50" onClick={() => handleSelectDay(item.date)}>
                      <TableCell className="text-sm font-medium text-[#243444]">{new Date(`${item.date}T00:00:00`).toLocaleDateString("es-ES")}</TableCell>
                      <TableCell className="text-right text-sm">{item.sessions}</TableCell>
                      <TableCell className="text-right text-sm">{item.total_trades}</TableCell>
                      <TableCell className="text-right text-sm font-semibold text-red-700">{item.total_unmatches}</TableCell>
                      <TableCell className="text-right text-sm font-semibold text-amber-700">{item.critical_count}</TableCell>
                      <TableCell className="text-right text-sm font-semibold text-purple-700">{item.unpair_trades}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>

      {selectedDay && (
        <div ref={daySessionsRef}>
        <Card className={highlightDayPanel ? "border-[#fc7c34] bg-orange-50/70 ring-4 ring-[#fc7c34]/35 ring-offset-4 ring-offset-white animate-analytics-highlight transition-all duration-500" : "transition-all duration-500"}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">
                  Sesiones del día {new Date(`${selectedDay}T00:00:00`).toLocaleDateString("es-ES")}
                </CardTitle>
                <p className="text-sm text-zinc-500 mt-1">Drill-down desde la analítica diaria hasta las sesiones concretas.</p>
                {highlightDayPanel && (
                  <p className="mt-2 inline-flex rounded-full border border-orange-200 bg-white px-2.5 py-1 text-xs font-medium text-orange-700">
                    Detalle cargado desde la analítica diaria
                  </p>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={() => setSelectedDay(null)}>
                Cerrar
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loadingDaySessions ? (
              <p className="text-sm text-zinc-500">Cargando sesiones del día...</p>
            ) : daySessions.length === 0 ? (
              <p className="text-sm text-zinc-500">No hay sesiones para ese día.</p>
            ) : (
              <div className="rounded-lg border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-zinc-50">
                      <TableHead>#</TableHead>
                      <TableHead>Fichero</TableHead>
                      <TableHead>Contrapartes</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead className="text-right">Operaciones</TableHead>
                      <TableHead className="text-right">Discrepancias</TableHead>
                      <TableHead className="text-right">Críticas</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {daySessions.map((session) => (
                      <TableRow key={session.id}>
                        <TableCell className="text-sm text-zinc-500">{session.id}</TableCell>
                        <TableCell className="text-xs font-mono max-w-44 truncate">{session.filename || "—"}</TableCell>
                        <TableCell className="text-xs text-zinc-600">{session.emisor_name} / {session.receptor_name}</TableCell>
                        <TableCell className="text-xs">{session.sft_type}/{session.action_type}</TableCell>
                        <TableCell className="text-right text-sm">{session.total_trades}</TableCell>
                        <TableCell className="text-right text-sm font-semibold text-red-700">{session.total_unmatches}</TableCell>
                        <TableCell className="text-right text-sm font-semibold text-amber-700">{session.critical_count}</TableCell>
                        <TableCell>
                          <Link to={`/sessions/${session.id}`} className="text-sm font-medium text-[#fc7c34] hover:underline">
                            Abrir
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div ref={counterpartiesRef}>
        <Card className={sectionHighlightClass("counterparties")}>
          <CardHeader>
            <CardTitle className="text-base">Por contraparte</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50">
                    <TableHead>Emisor</TableHead>
                    <TableHead>Receptor</TableHead>
                    <TableHead className="text-right">Sesiones</TableHead>
                    <TableHead className="text-right">Operaciones</TableHead>
                    <TableHead className="text-right">Discrepancias</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {counterparties.slice(0, 8).map((item, index) => (
                    <TableRow key={`${item.emisor_name}-${item.receptor_name}-${index}`}>
                      <TableCell className="text-xs font-mono max-w-28 truncate">{item.emisor_name}</TableCell>
                      <TableCell className="text-xs font-mono max-w-28 truncate">{item.receptor_name}</TableCell>
                      <TableCell className="text-right text-sm">{item.sessions}</TableCell>
                      <TableCell className="text-right text-sm">{item.total_trades}</TableCell>
                      <TableCell className="text-right text-sm font-semibold text-red-700">{item.total_unmatches}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Por tipo SFT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50">
                    <TableHead>Tipo SFT</TableHead>
                    <TableHead className="text-right">Sesiones</TableHead>
                    <TableHead className="text-right">Operaciones</TableHead>
                    <TableHead className="text-right">Discrepancias</TableHead>
                    <TableHead className="text-right">Críticas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sftTypes.map((item) => (
                    <TableRow key={item.sft_type}>
                      <TableCell className="font-medium">{item.sft_type}</TableCell>
                      <TableCell className="text-right text-sm">{item.sessions}</TableCell>
                      <TableCell className="text-right text-sm">{item.total_trades}</TableCell>
                      <TableCell className="text-right text-sm font-semibold text-red-700">{item.total_unmatches}</TableCell>
                      <TableCell className="text-right text-sm font-semibold text-amber-700">{item.critical_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

const CHAT_VISUAL_LABELS = {
  none: "Sin visual adicional",
  daily_trend: "Evolución diaria",
  top_fields: "Campos con más incidencias",
  counterparties: "Contrapartes con más incidencias",
  day_sessions: "Sesiones del día",
  comparison: "Comparación entre periodos",
} as const;

function MetricCard({
  label,
  value,
  color,
  suffix = "",
}: {
  label: string;
  value: number;
  color?: "red" | "amber" | "purple" | "green" | "blue";
  suffix?: string;
}) {
  const colorMap = {
    red: "text-red-700",
    amber: "text-amber-700",
    purple: "text-purple-700",
    green: "text-green-700",
    blue: "text-blue-700",
  };

  return (
    <div className="rounded-lg border border-zinc-200 p-3">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`text-xl font-bold ${color ? colorMap[color] : "text-zinc-900"}`}>
        {typeof value === "number" && Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString("es-ES")}
        {suffix}
      </p>
    </div>
  );
}

function InsightCard({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-gradient-to-br from-white to-zinc-50 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{title}</p>
      <p className="mt-2 text-lg font-semibold text-zinc-900">{value}</p>
      <p className="mt-1 text-sm text-zinc-600">{detail}</p>
    </div>
  );
}

function ComparisonMetricCard({
  label,
  delta,
  worseWhenPositive = false,
}: {
  label: string;
  delta: AnalyticsDelta;
  worseWhenPositive?: boolean;
}) {
  const isPositive = delta.abs > 0;
  const tone = delta.abs === 0
    ? "text-zinc-600"
    : worseWhenPositive
      ? isPositive ? "text-red-700" : "text-green-700"
      : isPositive ? "text-green-700" : "text-red-700";

  return (
    <div className="rounded-lg border border-zinc-200 p-3">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 text-sm text-zinc-500">A: {formatMetricValue(delta.a)} · B: {formatMetricValue(delta.b)}</p>
      <p className={`mt-2 text-xl font-bold ${tone}`}>
        {delta.abs > 0 ? "+" : ""}{formatMetricValue(delta.abs)}
      </p>
      <p className="text-xs text-zinc-500">
        {delta.pct === null ? "n/a" : `${delta.pct > 0 ? "+" : ""}${delta.pct}%`}
      </p>
    </div>
  );
}

function ComparisonRow({ label, a, b }: { label: string; a: number; b: number }) {
  return (
    <TableRow>
      <TableCell className="text-sm font-medium">{label}</TableCell>
      <TableCell className="text-right text-sm">{formatMetricValue(a)}</TableCell>
      <TableCell className="text-right text-sm">{formatMetricValue(b)}</TableCell>
    </TableRow>
  );
}

function formatMetricValue(value: number) {
  return Number.isInteger(value) ? value.toLocaleString("es-ES") : value.toLocaleString("es-ES", { maximumFractionDigits: 2 });
}

function formatSignedDelta(value?: number | null) {
  if (value === null || value === undefined) return "n/d";
  return `${value > 0 ? "+" : ""}${formatMetricValue(value)}`;
}

function normalizeMarkdownForDisplay(content: string) {
  let output = content.replace(/\r\n/g, "\n");

  // Repair common malformed inline GFM tables returned by the model.
  output = output.replace(/\s+\|(?=---)/g, "\n|");

  let previous = "";
  while (previous !== output) {
    previous = output;
    output = output.replace(/\|\s+\|(?=\s*[^\s|])/g, "|\n|");
  }

  output = output.replace(/:\n(?=\|)/g, ":\n\n");

  return output;
}

function TypingMarkdown({ content, animate }: { content: string; animate: boolean }) {
  const normalizedContent = normalizeMarkdownForDisplay(content);
  const [visibleLength, setVisibleLength] = useState(animate ? 0 : normalizedContent.length);

  useEffect(() => {
    if (!animate) {
      setVisibleLength(normalizedContent.length);
      return;
    }

    setVisibleLength(0);
    let index = 0;
    const step = Math.max(2, Math.ceil(normalizedContent.length / 120));
    const intervalId = window.setInterval(() => {
      index = Math.min(normalizedContent.length, index + step);
      setVisibleLength(index);
      if (index >= normalizedContent.length) {
        window.clearInterval(intervalId);
      }
    }, 18);

    return () => window.clearInterval(intervalId);
  }, [normalizedContent, animate]);

  const visibleContent = normalizedContent.slice(0, visibleLength);
  const isTyping = visibleLength < normalizedContent.length;

  return (
    <div className="prose prose-sm max-w-none text-zinc-700">
      {isTyping ? (
        <div className="whitespace-pre-wrap text-sm leading-6 text-zinc-700">{visibleContent}</div>
      ) : (
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {visibleContent}
        </ReactMarkdown>
      )}
      {isTyping && <span className="inline-block h-4 w-2 animate-pulse rounded-sm bg-[#fc7c34] align-middle" />}
    </div>
  );
}
