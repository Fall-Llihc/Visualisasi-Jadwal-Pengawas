/* sidebar.jsx — Sidebar (read-only, GitHub Pages user view) */
const { useState, useEffect } = React;

/* ── tiny icons ── */
const SvgSearch = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg>
);
const SvgPlus = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>
);
const SvgClose = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
);

/* Default tanggal agenda: hari ini, tapi tidak sebelum hari pertama ujian */
function defaultAgendaDate() {
  var d = new Date();
  var pad = n => String(n).padStart(2, '0');
  var today = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  var min = window.DATA_DATE_MIN || '';
  return min && today < min ? min : today;
}

/* ── Sidebar (single panel) ── */
function Sidebar(props) {
  const {
    nimValue, onNimChange, onSearch, searchError,
    agendas, onAddAgenda, onRemoveAgenda,
    lastUpdate, dataRows,
    isOpen, onClose,
  } = props;

  const [agDate, setAgDate] = useState(defaultAgendaDate);
  const [agTitle, setAgTitle] = useState('');
  const [agStart, setAgStart] = useState('08:00');
  const [agEnd, setAgEnd] = useState('10:00');
  const [agErr, setAgErr] = useState('');

  function handleAdd() {
    if (!agTitle.trim()) { setAgErr('Judul wajib diisi'); return; }
    if (agStart >= agEnd) { setAgErr('Waktu mulai harus sebelum selesai'); return; }
    setAgErr('');
    onAddAgenda({ date: agDate, title: agTitle.trim(), start: agStart, end: agEnd, id: Date.now() });
    setAgTitle('');
  }

  return (
    <aside className={'sidebar' + (isOpen ? '' : ' sidebar--closed')}>
      {/* Brand */}
      <div className="sb-brand">
        <h1 className="sb-logo">NgawasChill</h1>
        <p className="sb-subtitle">Jadwal Pengawas Ujian FIF</p>
        {onClose && (
          <button className="sb-close-btn" onClick={onClose} aria-label="Tutup sidebar" title="Tutup sidebar">
            <SvgClose />
          </button>
        )}
      </div>

      {/* Body */}
      <div className="sb-scroll">
        <div className="sb-tab-body">
          {/* NIM search */}
          <div className="sb-section">
            <label className="sb-label">Cari NIM Pengawas</label>
            <div className="sb-search-row">
              <input
                className={'sb-input' + (searchError ? ' sb-input--error' : '')}
                placeholder="Masukkan NIM …"
                value={nimValue}
                onChange={e => onNimChange(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && onSearch()}
              />
            </div>
            {searchError && <p className="sb-error">{searchError}</p>}
            <button className="sb-btn sb-btn--primary" onClick={onSearch}>
              <SvgSearch /> Cari Jadwal
            </button>
          </div>

          {/* Tambah Agenda */}
          <div className="sb-section">
            <p className="sb-section-title">Tambah Agenda Eksternal</p>
            <p className="sb-hint">Agenda ini hanya dipakai untuk mendeteksi tabrakan dengan sesi pengawasan—tidak ditampilkan sebagai sesi.</p>
            <label className="sb-label-sm">Hari</label>
            <input type="date" className="sb-input sb-input--sm" value={agDate} onChange={e => setAgDate(e.target.value)} />

            <label className="sb-label-sm">Judul Agenda</label>
            <input className="sb-input sb-input--sm" placeholder="cth: Rapat Organisasi" value={agTitle} onChange={e => setAgTitle(e.target.value)} />

            <div className="sb-time-row">
              <div>
                <label className="sb-label-sm">Mulai</label>
                <input type="time" className="sb-input sb-input--sm" value={agStart} onChange={e => setAgStart(e.target.value)} />
              </div>
              <div>
                <label className="sb-label-sm">Selesai</label>
                <input type="time" className="sb-input sb-input--sm" value={agEnd} onChange={e => setAgEnd(e.target.value)} />
              </div>
            </div>
            {agErr && <p className="sb-error">{agErr}</p>}
            <button className="sb-btn sb-btn--secondary" onClick={handleAdd}><SvgPlus /> Tambah Agenda</button>
          </div>

          {/* Agenda list */}
          {agendas.length > 0 && (
            <div className="sb-section">
              <p className="sb-section-title">Agenda Tersimpan</p>
              {agendas.map(ag => (
                <div key={ag.id} className="sb-agenda-chip">
                  <div>
                    <span className="sb-agenda-title">{ag.title}</span>
                    <span className="sb-agenda-date">{formatDateIndo(ag.date).split(',')[0]}, {ag.start}–{ag.end}</span>
                  </div>
                  <button className="sb-agenda-remove" onClick={() => onRemoveAgenda(ag.id)} title="Hapus">×</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer — last update */}
      <div className="sb-footer">
        <div className="sb-update-dot"></div>
        <div>
          <p className="sb-update-label">Terakhir diperbarui</p>
          <p className="sb-update-time">{lastUpdate ? formatUpdateTime(lastUpdate) : '—'}</p>
          <p className="sb-update-rows">{dataRows} baris data</p>
        </div>
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
