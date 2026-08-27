import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const faq = {
  id: 1,
  question: "When is check-in?",
  answer: "Check-in begins at 4:00 PM.",
  category: "hotel",
  created_at: "2026-08-24T10:00:00Z",
  updated_at: "2026-08-24T10:00:00Z",
};

const voices = [
  { id: 1, name: "James", description: "Mature, warm British male; professional and refined.", is_active: true, preview_url: "/api/admin/voices/1/preview", updated_at: "2026-08-24T10:00:00Z" },
  { id: 2, name: "Sofia", description: "Friendly, elegant female with a light European accent.", is_active: false, preview_url: "/api/admin/voices/2/preview", updated_at: "2026-08-24T10:00:00Z" },
  { id: 3, name: "Marcus", description: "Confident, energetic, modern American male.", is_active: false, preview_url: "/api/admin/voices/3/preview", updated_at: "2026-08-24T10:00:00Z" },
  { id: 4, name: "Elena", description: "Calm, reassuring, clear American female.", is_active: false, preview_url: "/api/admin/voices/4/preview", updated_at: "2026-08-24T10:00:00Z" },
];

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

describe("Meridian admin", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse([faq])));
  });

  it("includes the integrated Playground in admin navigation", async () => {
    render(<App />);

    expect(await screen.findByRole("button", { name: "Playground" })).toBeInTheDocument();
  });

  it("loads FAQs and filters them locally", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("When is check-in?")).toBeInTheDocument();
    await user.type(screen.getByRole("searchbox"), "casino");
    expect(screen.queryByText("When is check-in?")).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("creates a FAQ and refreshes the list", async () => {
    const user = userEvent.setup();
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse({ ...faq, id: 2 }, 201))
      .mockImplementationOnce(() => jsonResponse([faq, { ...faq, id: 2 }]))
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Add FAQ" }));
    await user.type(screen.getByLabelText("Question"), "Is breakfast served?");
    await user.type(screen.getByLabelText("Answer"), "Breakfast is served daily.");
    await user.type(screen.getByLabelText("Category"), "dining");
    await user.click(screen.getByRole("button", { name: "Save FAQ" }));

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    expect(fetch.mock.calls[1][0]).toBe("/api/admin/faqs");
    expect(fetch.mock.calls[1][1].method).toBe("POST");
  });

  it("shows a converted FAQ in the library without a reload or follow-up fetch", async () => {
    const user = userEvent.setup();
    const unanswered = [{
      id: 7,
      original_question: "Is airport transfer available?",
      normalized_question: "is airport transfer available",
      frequency: 3,
      first_seen_at: "2026-08-24T10:00:00Z",
      last_seen_at: "2026-08-24T11:00:00Z",
      status: "open",
    }];
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse(unanswered))
      .mockImplementationOnce(() => jsonResponse({
        ...faq, id: 2, question: unanswered[0].original_question,
        answer: "Transfers can be arranged.",
      }, 201))
      .mockImplementation(() => jsonResponse({ detail: "Refresh unavailable" }, 503));
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Unanswered Queue" }));
    await screen.findByText("Is airport transfer available?");
    await user.click(screen.getByRole("button", { name: "Convert" }));
    await user.type(screen.getByLabelText("Answer"), "Transfers can be arranged.");
    await user.type(screen.getByLabelText("Category"), "hotel");
    await user.click(screen.getByRole("button", { name: "Create FAQ" }));

    expect(await screen.findByText("Question converted to FAQ.")).toBeInTheDocument();
    expect(screen.queryByText("Is airport transfer available?")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "FAQ Library" }));
    expect(await screen.findByText("Is airport transfer available?")).toBeInTheDocument();
    expect(screen.getByText("Transfers can be arranged.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls[2][0]).toBe("/api/admin/unanswered/7/convert");
  });

  it("retains the question and draft when conversion fails", async () => {
    const user = userEvent.setup();
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse([{
        id: 7, original_question: "Is airport transfer available?",
        frequency: 1, last_seen_at: "2026-08-24T11:00:00Z", status: "open",
      }]))
      .mockImplementationOnce(() => jsonResponse({ detail: "FAQ question already exists" }, 409));
    render(<App />);
    await screen.findByText(faq.question);
    await user.click(screen.getByRole("button", { name: "Unanswered Queue" }));
    await user.click(await screen.findByRole("button", { name: "Convert" }));
    await user.type(screen.getByLabelText("Answer"), "Transfers can be arranged.");
    await user.type(screen.getByLabelText("Category"), "hotel");
    await user.click(screen.getByRole("button", { name: "Create FAQ" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("FAQ question already exists");
    expect(screen.getByLabelText("Answer")).toHaveValue("Transfers can be arranged.");
    expect(screen.getByRole("button", { name: "Convert" })).toBeInTheDocument();
  });

  it("accepts a 1000-character FAQ question and prevents typing past the limit", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(faq.question);
    await user.click(screen.getByRole("button", { name: "Add FAQ" }));
    const question = screen.getByLabelText("Question");
    await user.click(question);
    await user.paste("q".repeat(1000));
    expect(question).toHaveValue("q".repeat(1000));
    await user.type(question, "x");
    expect(question).toHaveValue("q".repeat(1000));
  });

  it("dismisses only after confirmation", async () => {
    const user = userEvent.setup();
    const item = [{ id: 8, original_question: "Spam question", frequency: 1,
      last_seen_at: "2026-08-24T11:00:00Z", status: "open" }];
    vi.spyOn(window, "confirm").mockReturnValue(true);
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse(item))
      .mockImplementationOnce(() => jsonResponse({ ...item[0], status: "dismissed" }))
      .mockImplementationOnce(() => jsonResponse([]));
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Unanswered Queue" }));
    await screen.findByText("Spam question");
    await user.click(screen.getByRole("button", { name: "Dismiss" }));

    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4));
  });

  it("shows a useful backend error", async () => {
    fetch.mockImplementationOnce(() => jsonResponse({ detail: "Backend unavailable" }, 503));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  });

  it("shows the four-voice Voice Studio with one active voice", async () => {
    const user = userEvent.setup();
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse(voices));
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Voice Studio" }));

    expect(await screen.findByRole("heading", { name: "Voice Studio" })).toBeInTheDocument();
    expect(screen.getAllByText("Active voice")).toHaveLength(1);
    for (const voice of voices) expect(screen.getByText(voice.name)).toBeInTheDocument();
  });

  it("activates Sofia and moves the active badge", async () => {
    const user = userEvent.setup();
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse(voices))
      .mockImplementationOnce(() => jsonResponse({ ...voices[1], is_active: true }));
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Voice Studio" }));
    const sofiaCard = (await screen.findByText("Sofia")).closest("article");
    await user.click(within(sofiaCard).getByRole("button", { name: "Set active" }));

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    expect(fetch.mock.calls[2][0]).toBe("/api/admin/voices/2/activate");
    expect(fetch.mock.calls[2][1].method).toBe("POST");
    expect(await screen.findByText("Voice changed to Sofia.")).toBeInTheDocument();
    expect(within(sofiaCard).getByText("Active voice")).toBeInTheDocument();
    expect(screen.getAllByText("Active voice")).toHaveLength(1);
  });

  it("keeps the previous active badge when activation fails", async () => {
    const user = userEvent.setup();
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse(voices))
      .mockImplementationOnce(() => jsonResponse({ detail: "Activation failed" }, 503));
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Voice Studio" }));
    const jamesCard = (await screen.findByText("James")).closest("article");
    const sofiaCard = screen.getByText("Sofia").closest("article");
    await user.click(within(sofiaCard).getByRole("button", { name: "Set active" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Activation failed");
    expect(within(jamesCard).getByText("Active voice")).toBeInTheDocument();
    expect(within(sofiaCard).queryByText("Active voice")).not.toBeInTheDocument();
  });

  it("pauses the previous preview before playing another voice", async () => {
    const user = userEvent.setup();
    const audioInstances = [];
    class AudioMock {
      constructor(url) {
        this.url = url;
        this.currentTime = 0;
        this.pause = vi.fn();
        this.play = vi.fn(() => Promise.resolve());
        audioInstances.push(this);
      }
    }
    vi.stubGlobal("Audio", AudioMock);
    fetch
      .mockImplementationOnce(() => jsonResponse([faq]))
      .mockImplementationOnce(() => jsonResponse(voices));
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Voice Studio" }));
    await screen.findByText("James");
    await user.click(screen.getByRole("button", { name: "Preview James" }));
    await user.click(screen.getByRole("button", { name: "Preview Sofia" }));

    expect(audioInstances.map((audio) => audio.url)).toEqual([
      "/api/admin/voices/1/preview",
      "/api/admin/voices/2/preview",
    ]);
    expect(audioInstances[0].pause).toHaveBeenCalled();
    expect(audioInstances[1].play).toHaveBeenCalled();
  });
});
