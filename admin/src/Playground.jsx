import { useEffect, useState } from "react";
import {
  BarVisualizer,
  RoomAudioRenderer,
  SessionProvider,
  StartAudio,
  TrackToggle,
  useAgent,
  useSession,
} from "@livekit/components-react";
import { TokenSource, Track } from "livekit-client";

import { faqApi } from "./api";

const tokenSource = TokenSource.endpoint("/api/livekit/token");

function displayState(session, agentState, starting, error) {
  if (error || agentState === "failed") return "Error";
  if (starting || session.connectionState === "connecting") return "Connecting";
  if (agentState === "listening") return "Listening";
  if (agentState === "thinking") return "Thinking";
  if (agentState === "speaking") return "Speaking";
  if (session.isConnected) return "Connecting";
  return "Disconnected";
}

function PlaygroundPanel({ session }) {
  const agent = useAgent(session);
  const [activeVoice, setActiveVoice] = useState("");
  const [voiceError, setVoiceError] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const state = displayState(session, agent.state, starting, error);

  useEffect(() => {
    let current = true;
    faqApi.activeVoice()
      .then((voice) => { if (current) setActiveVoice(voice.name); })
      .catch(() => { if (current) setVoiceError("Active voice is unavailable."); });
    return () => { current = false; };
  }, []);

  useEffect(() => () => { void session.end(); }, [session]);

  async function startConversation() {
    setError("");
    setStarting(true);
    try {
      await session.start({ tracks: { microphone: { enabled: true } } });
    } catch {
      setError(
        "Microphone or connection access failed. Check browser permissions and try again.",
      );
    } finally {
      setStarting(false);
    }
  }

  async function endConversation() {
    setError("");
    try {
      await session.end();
    } catch {
      setError("The conversation could not be ended cleanly. Please try again.");
    }
  }

  function mediaError() {
    setError(
      "Microphone or connection access failed. Check browser permissions and try again.",
    );
  }

  return (
    <section className="playground" data-lk-theme="default">
      <div className="playground-card">
        <div className="playground-meta">
          <span className="test-mode-badge">Test Mode</span>
          <span>{activeVoice ? `Testing with ${activeVoice}` : voiceError || "Loading active voice…"}</span>
        </div>

        <div className={`conversation-state state-${state.toLowerCase()}`}>
          <span className="state-orb" aria-hidden="true" />
          <strong className="state-label">{state}</strong>
          <p>
            {state === "Disconnected"
              ? "Start a private test conversation with the Meridian concierge."
              : state === "Listening"
                ? "Ask a question about The Meridian."
                : state === "Thinking"
                  ? "The concierge is checking the knowledge base."
                  : state === "Speaking"
                    ? "The concierge is responding."
                    : state === "Error"
                      ? "The test session needs your attention."
                      : "Preparing your voice session…"}
          </p>
        </div>

        <BarVisualizer
          className="agent-visualizer"
          state={agent.state}
          barCount={9}
          track={agent.microphoneTrack}
        />

        {error && <div className="message error playground-error" role="alert">{error}</div>}

        <div className="playground-controls">
          <button
            className="button primary"
            type="button"
            disabled={starting || session.connectionState !== "disconnected"}
            onClick={startConversation}
          >
            Start conversation
          </button>
          <TrackToggle
            className="button secondary microphone-button"
            source={Track.Source.Microphone}
            showIcon={false}
            disabled={!session.isConnected}
            onDeviceError={mediaError}
          >
            Microphone
          </TrackToggle>
          <button
            className="button secondary end-button"
            type="button"
            disabled={starting}
            onClick={endConversation}
          >
            End conversation
          </button>
        </div>

        <StartAudio className="button secondary audio-unlock" label="Enable agent audio" />
        <RoomAudioRenderer />
      </div>
      <p className="playground-note">
        Test sessions use the currently active voice and the latest saved FAQ content.
      </p>
    </section>
  );
}

export default function Playground() {
  const session = useSession(tokenSource, { agentName: "meridian-concierge" });
  return (
    <SessionProvider session={session}>
      <PlaygroundPanel session={session} />
    </SessionProvider>
  );
}
