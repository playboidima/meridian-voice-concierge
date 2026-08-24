import { render, screen, waitFor } from "@testing-library/react";
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

  it("converts an unanswered question", async () => {
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
      .mockImplementationOnce(() => jsonResponse(faq, 201))
      .mockImplementationOnce(() => jsonResponse([]));
    render(<App />);

    await screen.findByText("When is check-in?");
    await user.click(screen.getByRole("button", { name: "Unanswered Queue" }));
    await screen.findByText("Is airport transfer available?");
    await user.click(screen.getByRole("button", { name: "Convert" }));
    await user.type(screen.getByLabelText("Answer"), "Transfers can be arranged.");
    await user.type(screen.getByLabelText("Category"), "hotel");
    await user.click(screen.getByRole("button", { name: "Create FAQ" }));

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4));
    expect(fetch.mock.calls[2][0]).toBe("/api/admin/unanswered/7/convert");
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
});
