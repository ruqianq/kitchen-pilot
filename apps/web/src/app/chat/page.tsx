"use client";

import { useEffect, useRef, useState } from "react";
import Button from "@/components/Button";
import { chatApi, type ChatMessage } from "@/lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    const assistantMsg: ChatMessage = { role: "assistant", content: "" };
    const history = [...messages, userMsg];

    setMessages([...history, assistantMsg]);
    setInput("");
    setError(null);
    setStreaming(true);

    abortRef.current = chatApi.streamChat(
      text,
      messages,
      (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, content: last.content + token };
          return updated;
        });
      },
      () => setStreaming(false),
      (err) => {
        setError(err.message);
        setStreaming(false);
      },
    );
  }

  return (
    <div className="flex h-[calc(100vh-53px)] flex-col bg-zinc-50 dark:bg-black">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                Kitchen Pilot Chat
              </h2>
              <p className="mt-2 text-zinc-500">
                Ask me about meal planning, recipes, or cooking tips.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                  msg.role === "user"
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "bg-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                {msg.role === "assistant" &&
                  msg.content === "" &&
                  streaming &&
                  i === messages.length - 1 && (
                    <span className="inline-block animate-pulse text-zinc-400">
                      Thinking...
                    </span>
                  )}
              </div>
            </div>
          ))}

          {error && (
            <p className="text-center text-sm text-red-500">{error}</p>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-zinc-200 bg-white px-6 py-4 dark:border-zinc-800 dark:bg-zinc-950">
        <form onSubmit={handleSend} className="mx-auto flex max-w-3xl gap-3">
          <textarea
            className="flex-1 resize-none rounded-lg border border-zinc-300 px-4 py-3 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:focus:border-zinc-400"
            rows={1}
            placeholder="Ask about meal planning..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
            disabled={streaming}
          />
          <Button type="submit" disabled={streaming || !input.trim()}>
            {streaming ? "Sending..." : "Send"}
          </Button>
        </form>
      </div>
    </div>
  );
}
