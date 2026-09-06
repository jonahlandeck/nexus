import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, type ProfileData } from "../api/client";
import ChatThread, { type ChatMessage } from "../components/ChatThread";
import ProfileBadges from "../components/ProfileBadges";

const STORAGE_KEY = "map.intake.session";

export default function Intake() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY) || null,
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [profile, setProfile] = useState<ProfileData>({});
  const [complete, setComplete] = useState(false);
  const [missing, setMissing] = useState<string[]>([]);

  const send = useMutation({
    mutationFn: (text: string) => api.intake(text, sessionId),
    onSuccess: (res) => {
      setSessionId(res.session_id);
      localStorage.setItem(STORAGE_KEY, res.session_id);
      setMessages((m) => [...m, { role: "assistant", content: res.assistant_message }]);
      setProfile(res.profile);
      setComplete(res.complete);
      setMissing(res.missing_fields);
    },
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || send.isPending) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setDraft("");
    send.mutate(text);
  }

  return (
    <section>
      <p>
        Tell the assistant about your diet and goals. When it has enough, you can generate a plan.
      </p>

      <ProfileBadges profile={profile} />
      {missing.length > 0 && !complete && (
        <p className="muted">Still needs: {missing.join(", ")}</p>
      )}

      <ChatThread messages={messages} />

      {send.isError && <p className="err">{(send.error as Error).message}</p>}

      <form onSubmit={submit} style={{ marginTop: "0.75rem" }}>
        <fieldset role="group">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={send.isPending ? "thinking…" : "Type your answer…"}
            disabled={send.isPending}
            autoFocus
          />
          <button type="submit" disabled={send.isPending || !draft.trim()}>
            Send
          </button>
        </fieldset>
      </form>

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
        <button
          disabled={!complete}
          onClick={() => navigate("/plan")}
          aria-busy={send.isPending}
        >
          {complete ? "Generate my meal plan →" : "Answer a few more questions to unlock the plan"}
        </button>
        <button
          className="secondary outline"
          onClick={() => {
            localStorage.removeItem(STORAGE_KEY);
            setSessionId(null);
            setMessages([]);
            setProfile({});
            setComplete(false);
            setMissing([]);
          }}
        >
          Start over
        </button>
      </div>
    </section>
  );
}
