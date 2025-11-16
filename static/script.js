// Lightweight frontend for the Python backend
const player = document.getElementById("player");
let playlist = [];
let idx = 0;
let shuffleMode = true; // default: shuffle on
let playedHistory = [];

function secsToClock(s) {
  s = Math.floor(s||0);
  const mm = Math.floor(s/60);
  const ss = s % 60;
  return `${mm}:${String(ss).padStart(2,'0')}`;
}

async function loadPlaylist() {
  try {
    const res = await fetch("/api/tracks", {cache: "no-store"});
    if (!res.ok) throw new Error("no tracks");
    playlist = await res.json();
    buildTrackList();
    if (playlist.length > 0) {
      chooseInitial();
    }
  } catch (e) {
    console.warn("Failed to load tracks:", e);
  }
}

function buildTrackList() {
  const el = document.getElementById("trackList");
  el.innerHTML = "";
  playlist.forEach((t, i) => {
    const c = document.createElement("div");
    c.className = "track-card";
    const img = document.createElement("img");
    img.src = t.art || "/static/placeholder.jpg";
    const title = document.createElement("div");
    title.className = "t";
    title.textContent = t.title;
    const sub = document.createElement("div");
    sub.className = "s";
    sub.textContent = (t.artist ? `${t.artist} • ` : "") + secsToClock(t.duration);
    c.appendChild(img);
    c.appendChild(title);
    c.appendChild(sub);
    c.onclick = () => {
      loadTrack(i, true); // play selected track (counts as user gesture)
    }
    el.appendChild(c);
  });
}

function chooseInitial() {
  if (shuffleMode) {
    idx = Math.floor(Math.random() * playlist.length);
  } else {
    idx = 0;
  }
  loadTrack(idx, false);
}

function loadTrack(i, playImmediately = true) {
  if (!playlist.length) return;
  idx = i % playlist.length;
  const track = playlist[idx];
  // set UI
  document.getElementById("title").textContent = track.title || track.file;
  document.getElementById("selected").textContent = "Selected by —";
  document.getElementById("albumArt").src = track.art || "/static/placeholder.jpg";

  player.src = `/music/${encodeURIComponent(track.file)}`;

  // Autoplay policy: call play() after a short timeout to give browser time.
  if (playImmediately) {
    player.play().catch(err => {
      // If blocked, do nothing; clicking a card will start playback.
      console.warn("play blocked:", err);
    });
  }
}

function nextTrack() {
  if (!playlist.length) return;
  if (shuffleMode) {
    let newIdx = idx;
    if (playlist.length > 1) {
      while (newIdx === idx) {
        newIdx = Math.floor(Math.random() * playlist.length);
      }
    }
    loadTrack(newIdx, true);
  } else {
    loadTrack((idx + 1) % playlist.length, true);
  }
}

// play next on end
player.addEventListener("ended", () => {
  nextTrack();
});

// update clock in UI
setInterval(() => {
  const now = new Date();
  const hhmm = now.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
  document.getElementById("time").textContent = hhmm;
}, 1000);

// init
loadPlaylist();
