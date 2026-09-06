import { useEffect, useRef } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function ChatThread({ messages }: { messages: ChatMessage[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat" ref={ref}>
      {messages.length === 0 && (
        <div className="bubble assistant">
          Hi! I'm going to ask a few questions about how you eat and what you're aiming for, then
          build you a week of meals. To start — what does a normal day of eating look like for you?
        </div>
      )}
      {messages.map((m, i) => (
        <div key={i} className={`bubble ${m.role}`}>
          {m.content}
        </div>
      ))}
    </div>
  );
}
