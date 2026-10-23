/* app.jsx — Root App component (read-only user view) */
const { useState, useEffect, useCallback } = React;

/* ── icon: hamburger ── */
const SvgMenu = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
);

/* Interval cek data baru (version.json kecil; data.json hanya diambil kalau berubah) */
const DATA_POLL_MS = 3 * 60 * 1000;

/* Helper: cek apakah viewport mobile (≤860px) */
function isMobileViewport() {
  return typeof window !== 'undefined' && window.matchMedia('(max-width: 860px)').matches;
}

function App() {
  const [nim, setNim] = useState('');
  const [searchError, setSearchError] = useState('');
  const [proctor, setProctor] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(window.LAST_UPDATE_RAW || '');
  const [dataRows, setDataRows] = useState(window.DATA_ROWS || 0);
  const [agendas, setAgendas] = useState(() => {
    try { return JSON.parse(localStorage.getItem('vj_agendas') || '[]'); }
    catch { return []; }
  });

  // Sidebar visibility — default: terbuka di desktop, tertutup di mobile
  const [sidebarOpen, setSidebarOpen] = useState(() => !isMobileViewport());
  const [isMobile, setIsMobile] = useState(() => isMobileViewport());

  // Sinkronkan state saat ukuran viewport berubah (rotate / resize)
  useEffect(() => {
    function handleResize() {
      const mobile = isMobileViewport();
      setIsMobile(mobile);
      // Saat user resize ke desktop, otomatis buka sidebar.
      // Saat resize ke mobile, otomatis tutup supaya tidak menutupi konten.
      setSidebarOpen(!mobile);
    }
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Fallback untuk browser yang belum support 100dvh — set --app-vh ke
  // window.innerHeight aktual (sudah memperhitungkan address bar mobile).
  // CSS sudah pakai progressive enhancement: 100vh → var(--app-vh) → 100dvh.
  useEffect(() => {
    function setAppVh() {
      document.documentElement.style.setProperty(
        '--app-vh', window.innerHeight + 'px'
      );
    }
    setAppVh();
    window.addEventListener('resize', setAppVh);
    window.addEventListener('orientationchange', setAppVh);
    // visualViewport mendeteksi saat address bar mobile collapse/expand
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', setAppVh);
    }
    return () => {
      window.removeEventListener('resize', setAppVh);
      window.removeEventListener('orientationchange', setAppVh);
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('resize', setAppVh);
      }
    };
  }, []);

  // Tutup sidebar otomatis di mobile saat user menekan Esc
  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape' && isMobile && sidebarOpen) setSidebarOpen(false);
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isMobile, sidebarOpen]);

  // persist agendas
  useEffect(() => {
    localStorage.setItem('vj_agendas', JSON.stringify(agendas));
  }, [agendas]);

  // restore last searched NIM
  useEffect(() => {
    var last = localStorage.getItem('vj_last_nim');
    if (last && PROCTOR_DB[last]) {
      setNim(last);
      setProctor(PROCTOR_DB[last]);
    }
  }, []);

  // Refresh waktu commit terakhir folder /data via GitHub API.
  // Kalau gagal, tetap pakai LAST_UPDATE_RAW yang sudah di-embed di data.js.
  useEffect(() => {
    if (typeof window.fetchLatestCommitTime === 'function') {
      window.fetchLatestCommitTime(function (raw) {
        if (raw) setLastUpdate(raw);
      });
    }
  }, []);

  // Live update: cek data baru berkala + saat tab kembali aktif, tanpa reload.
  // Jadwal pengawas yang sedang dibuka ikut diganti dengan versi terbaru.
  useEffect(() => {
    if (typeof window.fetchLatestData !== 'function') return;
    function poll() {
      if (document.hidden) return;
      window.fetchLatestData(function (d) {
        setLastUpdate(d.lastUpdate || '');
        setDataRows(d.rows || 0);
        setProctor(prev => (prev ? (PROCTOR_DB[prev.nim] || null) : prev));
      });
    }
    const id = setInterval(poll, DATA_POLL_MS);
    document.addEventListener('visibilitychange', poll);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', poll);
    };
  }, []);

  const handleSearch = useCallback(() => {
    setSearchError('');
    var v = nim.trim();
    if (!v) { setSearchError('NIM tidak boleh kosong'); return; }
    if (/[^0-9]/.test(v)) { setSearchError('Mohon masukkan NIM (angka), bukan nama.'); return; }
    var p = PROCTOR_DB[v];
    if (!p) { setSearchError('NIM ' + v + ' tidak ditemukan.'); return; }
    setProctor(p);
    localStorage.setItem('vj_last_nim', v);
    // Auto-tutup sidebar di mobile setelah pencarian sukses
    if (isMobile) setSidebarOpen(false);
  }, [nim, isMobile]);

  function addAgenda(ag) { setAgendas(prev => [...prev, ag]); }
  function removeAgenda(id) { setAgendas(prev => prev.filter(a => a.id !== id)); }

  return (
    <div className="app-layout">
      {/* Backdrop hanya muncul di mobile saat sidebar terbuka */}
      {isMobile && sidebarOpen && (
        <div className="sb-backdrop" onClick={() => setSidebarOpen(false)} />
      )}

      <Sidebar
        nimValue={nim}
        onNimChange={v => { setNim(v); setSearchError(''); }}
        onSearch={handleSearch}
        searchError={searchError}
        agendas={agendas}
        onAddAgenda={addAgenda}
        onRemoveAgenda={removeAgenda}
        lastUpdate={lastUpdate}
        dataRows={dataRows}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Hamburger button — muncul saat sidebar tertutup */}
      {!sidebarOpen && (
        <button
          className="sb-open-btn"
          onClick={() => setSidebarOpen(true)}
          aria-label="Buka sidebar"
          title="Buka sidebar"
        >
          <SvgMenu />
        </button>
      )}

      <main className={'main-content' + (sidebarOpen && !isMobile ? '' : ' main-content--full')}>
        {proctor ? <ScheduleView proctor={proctor} agendas={agendas} /> : <EmptyState />}
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
