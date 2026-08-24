import { useEffect, useMemo, useRef, useState } from "react";

import { faqApi } from "./api";

const emptyFaq = { question: "", answer: "", category: "" };
const emptyConvert = { answer: "", category: "" };

function formatDate(value) {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function FaqForm({ initial, onCancel, onSave }) {
  const [draft, setDraft] = useState(initial || emptyFaq);
  const update = (field) => (event) =>
    setDraft((current) => ({ ...current, [field]: event.target.value }));

  return (
    <div className="overlay" role="presentation">
      <form
        className="dialog"
        aria-label={initial ? "Edit FAQ" : "Add FAQ"}
        onSubmit={(event) => { event.preventDefault(); onSave(draft); }}
      >
        <div className="dialog-heading">
          <div><span className="eyebrow">Knowledge base</span><h2>{initial ? "Edit FAQ" : "Add FAQ"}</h2></div>
          <button className="icon-button" type="button" onClick={onCancel} aria-label="Close">×</button>
        </div>
        <label>Question<textarea value={draft.question} onChange={update("question")} required minLength="2" /></label>
        <label>Answer<textarea value={draft.answer} onChange={update("answer")} required minLength="2" rows="5" /></label>
        <label>Category<input value={draft.category} onChange={update("category")} required minLength="2" /></label>
        <div className="form-actions"><button className="button secondary" type="button" onClick={onCancel}>Cancel</button><button className="button primary" type="submit">Save FAQ</button></div>
      </form>
    </div>
  );
}

function ConvertForm({ item, onCancel, onSave }) {
  const [draft, setDraft] = useState(emptyConvert);
  return (
    <div className="overlay" role="presentation">
      <form className="dialog" aria-label="Convert unanswered question" onSubmit={(event) => { event.preventDefault(); onSave(draft); }}>
        <div className="dialog-heading"><div><span className="eyebrow">Convert to FAQ</span><h2>{item.original_question}</h2></div><button className="icon-button" type="button" onClick={onCancel} aria-label="Close">×</button></div>
        <label>Answer<textarea value={draft.answer} onChange={(event) => setDraft({ ...draft, answer: event.target.value })} required minLength="2" rows="5" /></label>
        <label>Category<input value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} required minLength="2" /></label>
        <div className="form-actions"><button className="button secondary" type="button" onClick={onCancel}>Cancel</button><button className="button primary" type="submit">Create FAQ</button></div>
      </form>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("faqs");
  const [faqs, setFaqs] = useState([]);
  const [unanswered, setUnanswered] = useState([]);
  const [voices, setVoices] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [faqDraft, setFaqDraft] = useState(undefined);
  const [convertItem, setConvertItem] = useState(undefined);
  const [previewingVoiceId, setPreviewingVoiceId] = useState(null);
  const [activatingVoice, setActivatingVoice] = useState(false);
  const audioRef = useRef(null);

  async function run(action, success) {
    setError(""); setNotice("");
    try { await action(); if (success) setNotice(success); }
    catch (reason) { setError(reason.message); }
  }

  async function loadFaqs() {
    setLoading(true);
    await run(async () => setFaqs(await faqApi.listFaqs()));
    setLoading(false);
  }

  async function loadUnanswered() {
    setLoading(true);
    await run(async () => setUnanswered(await faqApi.listUnanswered()));
    setLoading(false);
  }

  async function loadVoices() {
    setLoading(true);
    await run(async () => setVoices(await faqApi.listVoices()));
    setLoading(false);
  }

  useEffect(() => {
    loadFaqs();
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    };
  }, []);

  const filteredFaqs = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return faqs;
    return faqs.filter((faq) => [faq.question, faq.answer, faq.category].some((value) => value.toLowerCase().includes(needle)));
  }, [faqs, query]);

  function changeView(next) {
    stopPreview();
    setView(next); setError(""); setNotice("");
    if (next === "unanswered") loadUnanswered();
    if (next === "voices") loadVoices();
  }

  function stopPreview() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setPreviewingVoiceId(null);
  }

  async function togglePreview(voice) {
    setError("");
    if (previewingVoiceId === voice.id) {
      stopPreview();
      return;
    }
    stopPreview();
    const audio = new Audio(faqApi.voicePreviewUrl(voice.id));
    audioRef.current = audio;
    setPreviewingVoiceId(voice.id);
    audio.onended = () => {
      if (audioRef.current === audio) stopPreview();
    };
    audio.onerror = () => {
      if (audioRef.current === audio) stopPreview();
      setError("Voice preview is unavailable.");
    };
    try {
      await audio.play();
    } catch {
      if (audioRef.current === audio) stopPreview();
      setError("Voice preview is unavailable.");
    }
  }

  async function selectVoice(voice) {
    setActivatingVoice(true);
    await run(async () => {
      const active = await faqApi.activateVoice(voice.id);
      setVoices((current) => current.map((item) => ({
        ...item,
        is_active: item.id === active.id,
        updated_at: item.id === active.id ? active.updated_at : item.updated_at,
      })));
    }, `Voice changed to ${voice.name}.`);
    setActivatingVoice(false);
  }

  async function saveFaq(payload) {
    await run(async () => {
      if (faqDraft?.id) await faqApi.updateFaq(faqDraft.id, payload);
      else await faqApi.createFaq(payload);
      setFaqDraft(undefined);
      setFaqs(await faqApi.listFaqs());
    }, faqDraft?.id ? "FAQ updated." : "FAQ created.");
  }

  async function removeFaq(faq) {
    if (!window.confirm(`Delete “${faq.question}”?`)) return;
    await run(async () => { await faqApi.deleteFaq(faq.id); setFaqs(await faqApi.listFaqs()); }, "FAQ deleted.");
  }

  async function convert(payload) {
    await run(async () => {
      await faqApi.convertUnanswered(convertItem.id, payload);
      setConvertItem(undefined);
      setUnanswered(await faqApi.listUnanswered());
    }, "Question converted to FAQ.");
  }

  async function dismiss(item) {
    if (!window.confirm(`Dismiss “${item.original_question}”?`)) return;
    await run(async () => { await faqApi.dismissUnanswered(item.id); setUnanswered(await faqApi.listUnanswered()); }, "Question dismissed.");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">M</span><div><strong>The Meridian</strong><small>Concierge Admin</small></div></div>
        <nav aria-label="Admin sections">
          <button className={view === "faqs" ? "nav-item active" : "nav-item"} onClick={() => changeView("faqs")}>FAQ Library</button>
          <button className={view === "unanswered" ? "nav-item active" : "nav-item"} onClick={() => changeView("unanswered")}>Unanswered Queue</button>
          <button className={view === "voices" ? "nav-item active" : "nav-item"} onClick={() => changeView("voices")}>Voice Studio</button>
        </nav>
        <div className="sidebar-note"><span className="status-dot" />Backend connected</div>
      </aside>
      <main>
        <header className="page-header"><div><span className="eyebrow">The Meridian Casino & Resort</span><h1>{view === "faqs" ? "FAQ Library" : view === "unanswered" ? "Unanswered Queue" : "Voice Studio"}</h1><p>{view === "faqs" ? "Keep every guest answer accurate and searchable." : view === "unanswered" ? "Turn recurring guest questions into trusted answers." : "Choose the voice guests hear in every new conversation."}</p></div>{view === "faqs" && <button className="button primary" onClick={() => setFaqDraft(null)}>Add FAQ</button>}</header>
        {error && <div className="message error" role="alert">{error}</div>}
        {notice && <div className="message success" role="status">{notice}</div>}
        {view === "faqs" ? (
          <section>
            <div className="toolbar"><input type="search" aria-label="Search FAQs" placeholder="Search questions, answers, or categories" value={query} onChange={(event) => setQuery(event.target.value)} /><span>{filteredFaqs.length} entries</span></div>
            {loading ? <p className="empty">Loading FAQs…</p> : filteredFaqs.length === 0 ? <p className="empty">No FAQs match this search.</p> : <div className="card-grid">{filteredFaqs.map((faq) => <article className="card" key={faq.id}><div className="card-top"><span className="tag">{faq.category}</span><span className="muted">#{faq.id}</span></div><h2>{faq.question}</h2><p>{faq.answer}</p><div className="card-actions"><button className="text-button" onClick={() => setFaqDraft(faq)}>Edit</button><button className="text-button danger" onClick={() => removeFaq(faq)}>Delete</button></div></article>)}</div>}
          </section>
        ) : view === "unanswered" ? (
          <section>{loading ? <p className="empty">Loading queue…</p> : unanswered.length === 0 ? <p className="empty">The unanswered queue is clear.</p> : <div className="queue">{unanswered.map((item) => <article className="queue-row" key={item.id}><div className="frequency"><strong>{item.frequency}</strong><span>times asked</span></div><div className="queue-copy"><h2>{item.original_question}</h2><p>Last seen {formatDate(item.last_seen_at)}</p></div><div className="card-actions"><button className="button secondary" onClick={() => dismiss(item)}>Dismiss</button><button className="button primary" onClick={() => setConvertItem(item)}>Convert</button></div></article>)}</div>}</section>
        ) : (
          <section>{loading ? <p className="empty">Loading voices…</p> : voices.length === 0 ? <p className="empty">No concierge voices are available.</p> : <div className="voice-grid">{voices.map((voice) => <article className={voice.is_active ? "voice-card active-voice" : "voice-card"} key={voice.id}><div className="voice-card-top"><div className="voice-avatar" aria-hidden="true">{voice.name[0]}</div>{voice.is_active && <span className="active-badge">Active voice</span>}</div><h2>{voice.name}</h2><p>{voice.description}</p><div className="waveform" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /></div><div className="voice-actions"><button className="button secondary preview-button" type="button" aria-label={`${previewingVoiceId === voice.id ? "Stop preview" : "Preview"} ${voice.name}`} onClick={() => togglePreview(voice)}>{previewingVoiceId === voice.id ? "■ Stop preview" : "▶ Preview"}</button><button className="button primary" type="button" disabled={voice.is_active || activatingVoice} onClick={() => selectVoice(voice)}>{voice.is_active ? "Currently active" : "Set active"}</button></div></article>)}</div>}</section>
        )}
      </main>
      {faqDraft !== undefined && <FaqForm initial={faqDraft || undefined} onCancel={() => setFaqDraft(undefined)} onSave={saveFaq} />}
      {convertItem && <ConvertForm item={convertItem} onCancel={() => setConvertItem(undefined)} onSave={convert} />}
    </div>
  );
}
