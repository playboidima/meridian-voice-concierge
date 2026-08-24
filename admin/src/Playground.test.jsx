import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const livekit = vi.hoisted(() => ({
  agent: { state: "disconnected", microphoneTrack: undefined },
  session: {
    connectionState: "disconnected",
    isConnected: false,
    start: vi.fn(),
    end: vi.fn(),
  },
}));

vi.mock("livekit-client", () => ({
  TokenSource: { endpoint: vi.fn(() => ({ type: "endpoint" })) },
  Track: { Source: { Microphone: "microphone" } },
}));

vi.mock("@livekit/components-react", () => ({
  BarVisualizer: () => <div data-testid="visualizer" />,
  RoomAudioRenderer: () => <div data-testid="audio-renderer" />,
  SessionProvider: ({ children }) => <>{children}</>,
  StartAudio: ({ label }) => <button>{label}</button>,
  TrackToggle: ({ children }) => <button>{children}</button>,
  useAgent: () => livekit.agent,
  useSession: () => livekit.session,
}));

import Playground from "./Playground";

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

describe("Integrated playground", () => {
  beforeEach(() => {
    livekit.agent.state = "disconnected";
    livekit.session.connectionState = "disconnected";
    livekit.session.isConnected = false;
    livekit.session.start.mockReset().mockResolvedValue(undefined);
    livekit.session.end.mockReset().mockResolvedValue(undefined);
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse({ name: "Elena" })));
  });

  it("shows English test-mode copy, disconnected state, and active voice", async () => {
    render(<Playground />);

    expect(screen.getByText("Test Mode")).toBeInTheDocument();
    expect(screen.getByText("Disconnected")).toHaveClass("state-label");
    expect(await screen.findByText("Testing with Elena")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/voice/active", expect.anything());
  });

  it("starts with microphone audio and can end the session", async () => {
    const user = userEvent.setup();
    render(<Playground />);

    await user.click(screen.getByRole("button", { name: "Start conversation" }));
    expect(livekit.session.start).toHaveBeenCalledWith({
      tracks: { microphone: { enabled: true } },
    });
    await user.click(screen.getByRole("button", { name: "End conversation" }));
    expect(livekit.session.end).toHaveBeenCalled();
  });

  it("shows connection progress while Start is pending", async () => {
    let resolveStart;
    livekit.session.start.mockReturnValue(
      new Promise((resolve) => { resolveStart = resolve; }),
    );
    const user = userEvent.setup();
    render(<Playground />);

    await user.click(screen.getByRole("button", { name: "Start conversation" }));
    expect(screen.getByText("Connecting")).toBeInTheDocument();
    resolveStart();
    await waitFor(() => expect(livekit.session.start).toHaveBeenCalledTimes(1));
  });

  it("shows a retryable English error when Start fails", async () => {
    livekit.session.start.mockRejectedValueOnce(new Error("permission denied"));
    const user = userEvent.setup();
    render(<Playground />);

    await user.click(screen.getByRole("button", { name: "Start conversation" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Microphone or connection access failed. Check browser permissions and try again.",
    );
    expect(screen.getByRole("button", { name: "Start conversation" })).toBeEnabled();
  });

  it("ends the LiveKit session when leaving the Playground", () => {
    const { unmount } = render(<Playground />);

    unmount();

    expect(livekit.session.end).toHaveBeenCalled();
  });
});
