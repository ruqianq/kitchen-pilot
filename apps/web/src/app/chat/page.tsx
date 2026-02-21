"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/Button";
import { chatApi, voiceApi, type ChatMessage } from "@/lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [ttsPlaying, setTtsPlaying] = useState<number | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // Send a message through the chat pipeline (used by both text and voice)
  const sendMessage = useCallback(
    (text: string) => {
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
            updated[updated.length - 1] = {
              ...last,
              content: last.content + token,
            };
            return updated;
          });
        },
        () => setStreaming(false),
        (err) => {
          setError(err.message);
          setStreaming(false);
        },
      );
    },
    [messages, streaming],
  );

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input.trim());
  }

  // --- Push-to-Talk ---

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      audioChunksRef.current = [];

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;

        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (blob.size === 0) return;

        setTranscribing(true);
        try {
          const result = await voiceApi.stt(blob);
          if (result.text.trim()) {
            sendMessage(result.text.trim());
          }
        } catch (err) {
          setError(
            err instanceof Error ? err.message : "Transcription failed",
          );
        } finally {
          setTranscribing(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Microphone access denied. Please allow microphone access.");
    }
  }

  function stopRecording() {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    setRecording(false);
  }

  // --- TTS Playback ---

  async function handleTts(text: string, index: number) {
    // Stop any currently playing audio
    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause();
      ttsAudioRef.current = null;
    }

    if (ttsPlaying === index) {
      setTtsPlaying(null);
      return;
    }

    setTtsPlaying(index);
    try {
      const blob = await voiceApi.tts(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      ttsAudioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setTtsPlaying(null);
        ttsAudioRef.current = null;
      };
      await audio.play();
    } catch {
      setTtsPlaying(null);
    }
  }

  const busy = streaming || recording || transcribing;

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
              <p className="mt-1 text-xs text-zinc-400">
                Type a message or hold the mic button to speak.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`group relative max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                  msg.role === "user"
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "bg-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans">
                  {msg.content}
                </pre>
                {msg.role === "assistant" &&
                  msg.content === "" &&
                  streaming &&
                  i === messages.length - 1 && (
                    <span className="inline-block animate-pulse text-zinc-400">
                      Thinking...
                    </span>
                  )}
                {/* TTS button on assistant messages */}
                {msg.role === "assistant" && msg.content.length > 0 && (
                  <button
                    onClick={() => handleTts(msg.content, i)}
                    className="absolute -bottom-2 -right-2 rounded-full bg-white p-1.5 opacity-0 shadow-md transition-opacity group-hover:opacity-100 dark:bg-zinc-700"
                    title={
                      ttsPlaying === i ? "Stop playback" : "Listen to response"
                    }
                  >
                    {ttsPlaying === i ? (
                      <svg
                        className="h-3.5 w-3.5 text-red-500"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <rect x="6" y="6" width="12" height="12" rx="1" />
                      </svg>
                    ) : (
                      <svg
                        className="h-3.5 w-3.5 text-zinc-500 dark:text-zinc-300"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z"
                        />
                      </svg>
                    )}
                  </button>
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
        <form
          onSubmit={handleSend}
          className="mx-auto flex max-w-3xl items-center gap-3"
        >
          <textarea
            className="flex-1 resize-none rounded-lg border border-zinc-300 px-4 py-3 text-sm outline-none focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:focus:border-zinc-400"
            rows={1}
            placeholder={
              recording
                ? "Recording... release mic to send"
                : transcribing
                  ? "Transcribing..."
                  : "Ask about meal planning..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
            disabled={busy}
          />

          {/* Mic button */}
          <button
            type="button"
            onMouseDown={(e) => {
              e.preventDefault();
              if (!busy) startRecording();
            }}
            onMouseUp={stopRecording}
            onMouseLeave={() => {
              if (recording) stopRecording();
            }}
            onTouchStart={(e) => {
              e.preventDefault();
              if (!busy) startRecording();
            }}
            onTouchEnd={stopRecording}
            disabled={streaming || transcribing}
            className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-colors ${
              recording
                ? "bg-red-500 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
            } disabled:opacity-50`}
            title="Hold to record"
          >
            {recording && (
              <span className="absolute inset-0 animate-ping rounded-full bg-red-400 opacity-40" />
            )}
            <svg
              className="relative h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z"
              />
            </svg>
          </button>

          <Button type="submit" disabled={busy || !input.trim()}>
            {streaming
              ? "Sending..."
              : transcribing
                ? "Transcribing..."
                : "Send"}
          </Button>
        </form>
      </div>
    </div>
  );
}
