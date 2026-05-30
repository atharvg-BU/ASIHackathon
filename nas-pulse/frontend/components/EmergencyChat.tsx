"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bot, Loader2, MessageSquare, Send, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ChatMessage, EmergencyChatResponse } from "@/lib/types";

type Props = {
  scenarioTime: string;
  selectedFlightId?: string;
  emergencyFlightId?: string;
  scenarioTags: string[];
  onFlagFlight?: (flightId: string) => void;
};

const starters = [
  "What historical cases are similar right now?",
  "What are the best options for the selected flight?",
  "Emergency: summarize risks and actions.",
];

function initialAssistantMessage(flightId?: string) {
  return {
    role: "assistant" as const,
    content: flightId
      ? `Emergency support chat is ready for ${flightId}. I can compare historical cases, summarize current route context, and rank high-level options. Demo only - not operational guidance.`
      : "Emergency support chat is ready. I can compare historical cases, summarize current NAS risk, and rank high-level options. Demo only - not operational guidance."
  };
}

export default function EmergencyChat({ scenarioTime, selectedFlightId, emergencyFlightId, scenarioTags, onFlagFlight }: Props) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const focusedFlightId = emergencyFlightId || selectedFlightId;
  const starterMessage = useMemo(() => initialAssistantMessage(focusedFlightId), [focusedFlightId]);
  const [messages, setMessages] = useState<ChatMessage[]>([starterMessage]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setMessages([starterMessage]);
    setInput("");
  }, [starterMessage]);

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    const historyForRequest = messages.slice(-10);
    setInput("");
    setLoading(true);
    setMessages((current) => [...current, { role: "controller", content: trimmed }]);
    try {
      const result = await api.emergencyChat<EmergencyChatResponse>({
        scenario_time: scenarioTime,
        selected_flight_id: focusedFlightId,
        scenario_tags: scenarioTags,
        message: trimmed,
        chat_history: historyForRequest
      });
      if (result.focused_flight_id && isFlagIntent(trimmed)) {
        onFlagFlight?.(result.focused_flight_id);
      }
      const localReason = result.llm_status?.reason || "";
      let source = `\n\nSource: Local fallback${localReason ? ` (${localReason})` : ""}`;
      if (result.llm_used) {
        source = `\n\nSource: Claude (${result.llm_status?.model || "Anthropic"})`;
      } else if (localReason.includes("local guardrail")) {
        source = `\n\nSource: Local guardrail (${localReason})`;
      }
      setMessages((current) => [...current, { role: "assistant", content: `${result.response}${source}` }]);
    } catch (err: any) {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: `Chat service unavailable: ${err.message}. The deterministic dashboard remains available.` }
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    sendMessage(input);
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-[1000] flex items-center gap-2 rounded-full border border-cyanline/40 bg-cyanline px-4 py-3 text-sm font-bold text-slate-950 shadow-2xl shadow-cyanline/20"
      >
        <MessageSquare size={18} />
        Emergency Chat
      </button>

      {open && (
        <section className="fixed bottom-5 right-5 z-[1100] flex h-[min(760px,calc(100vh-40px))] w-[min(620px,calc(100vw-32px))] flex-col overflow-hidden rounded-lg border border-cyanline/30 bg-[#0a131d] shadow-2xl shadow-black/50">
          <header className="flex items-center justify-between border-b border-white/10 bg-panel2 p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-danger/15 p-2 text-danger">
                <AlertTriangle size={18} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">Controller Emergency Chat</h2>
                <p className="text-xs text-slate-400">
                  {emergencyFlightId ? `Emergency flagged on ${emergencyFlightId}` : selectedFlightId ? `Focused on ${selectedFlightId}` : "Network-level support"} · {scenarioTime} UTC
                </p>
              </div>
            </div>
            <button className="rounded-md p-2 text-slate-400 hover:bg-white/10 hover:text-white" onClick={() => setOpen(false)} aria-label="Close emergency chat">
              <X size={18} />
            </button>
          </header>

          <div className="border-b border-white/10 bg-danger/10 px-4 py-2 text-xs text-danger">
            Demo only - not for operational aviation use. No cockpit instructions. Response source appears under each answer.
          </div>

          <div className="flex gap-2 overflow-x-auto border-b border-white/10 p-3">
            {starters.map((starter) => (
              <button
                key={starter}
                onClick={() => sendMessage(starter)}
                className="shrink-0 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-300 hover:border-cyanline/50 hover:text-cyanline"
              >
                {starter}
              </button>
            ))}
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`flex gap-2 ${message.role === "controller" ? "justify-end" : "justify-start"}`}>
                {message.role === "assistant" && (
                  <div className="mt-1 h-7 w-7 shrink-0 rounded-md bg-cyanline/10 p-1.5 text-cyanline">
                    <Bot size={16} />
                  </div>
                )}
                <div
                  className={`max-w-[88%] whitespace-pre-line rounded-lg p-3 text-sm leading-6 ${
                    message.role === "controller"
                      ? "bg-cyanline text-slate-950"
                      : "border border-white/10 bg-white/[0.045] text-slate-200"
                  }`}
                >
                  {message.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Loader2 size={16} className="animate-spin text-cyanline" />
                Comparing current scenario with historical memory and optimizer outputs...
              </div>
            )}
          </div>

          <form onSubmit={onSubmit} className="flex gap-2 border-t border-white/10 p-3">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about history, emergency options, or network risk..."
              className="min-w-0 flex-1 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyanline/60"
            />
            <button className="rounded-md bg-runway px-3 py-2 text-slate-950" aria-label="Send chat message">
              <Send size={18} />
            </button>
          </form>
        </section>
      )}
    </>
  );
}

function isFlagIntent(message: string) {
  const lower = message.toLowerCase();
  return ["flag", "emergency", "bird", "strike", "failure", "fuel", "urgent", "mayday"].some((token) => lower.includes(token));
}
