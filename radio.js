// Use the modular Firebase SDK (ES module imports)
import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.6.0/firebase-app.js';
import {
    getDatabase,
    ref,
    onValue,
    get,
    set,
    update
} from 'https://www.gstatic.com/firebasejs/12.6.0/firebase-database.js';

const audio = document.getElementById('audio');
const titleEl = document.getElementById('title');
const artistEl = document.getElementById('artist');
const selectorEl = document.getElementById('selector');
const coverEl = document.getElementById('cover');
const statusEl = document.getElementById('status');

let playlist = [];
let currentIndex = 0;
let db = null;
let isSynced = false;

// Base raw URL for this project's GitHub Pages repository (used as a fallback
// when the `file` or `cover` fields are local paths like `music/...`). This
// keeps the Neocities page working even if `tracks.json` still contains
// relative paths.
const RAW_BASE = 'https://raw.githubusercontent.com/LeakySponge/radiothingymagiy.github.io/main/';

function setStatus(text, cls) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.remove('status-online', 'status-sync', 'status-offline');
    if (cls) statusEl.classList.add(cls);
}

window.addEventListener('online', () => {
    if (isSynced) setStatus('Connected — online', 'status-online');
    else setStatus('Online (local)', 'status-online');
});

window.addEventListener('offline', () => {
    setStatus('Offline', 'status-offline');
});

// --- Initialize Firebase (modular) ---
async function initFirebase() {
    try {
        // Prefer an inline config exposed on the page (e.g. Pages deployment).
        // This allows you to keep `firebase-config.json` out of the repo and
        // still provide the config via an inline <script> in `index.html`.
        let firebaseConfig = window.__FIREBASE_CONFIG;
        if (!firebaseConfig) {
            // Fetch the JSON but be defensive: the fetch may return an HTML
            // error page (leading to a misleading JSON.parse error). Read
            // the response as text and attempt to parse; if parsing fails
            // include the first chunk of the response in the error to help
            // debugging.
            const configRes = await fetch('firebase-config.json');
            const text = await configRes.text();
            try {
                firebaseConfig = JSON.parse(text);
            } catch (e) {
                console.error('Failed to parse firebase-config.json; response:', text.slice(0, 1000));
                throw new Error('Invalid firebase-config.json (not JSON)');
            }
        }

        const app = initializeApp(firebaseConfig);
        db = getDatabase(app);

        console.log('Firebase (modular) initialized');
        isSynced = true;
        setStatus('Connected — waiting for state', 'status-online');
        setupFirebaseSync();
    } catch (err) {
        console.warn('Firebase not available (GitHub Pages local mode):', err);
        isSynced = false;
        setStatus('Disconnected — local mode', 'status-offline');
        loadTracksLocally();
    }
}

// --- Setup Firebase real-time sync ---
function setupFirebaseSync() {
    // Listen for track list changes
    const tracksRef = ref(db, 'radio/tracks');
    onValue(tracksRef, (snapshot) => {
        const tracks = snapshot.val();
        if (tracks && Array.isArray(tracks)) {
            // Normalize any relative paths to absolute raw.githubusercontent URLs
            playlist = tracks.map(normalizeTrackUrls);
            console.log('[Firebase] Tracks updated:', playlist.length, 'tracks');
        }
    });

    // Listen for playback state changes
    const stateRef = ref(db, 'radio/state');
    onValue(stateRef, (snapshot) => {
        const state = snapshot.val();
        if (state) {
            currentIndex = state.currentTrackIndex || 0;
            const elapsedSeconds = (Date.now() - (state.startTime || Date.now())) / 1000;
            syncPlayback(elapsedSeconds);
            setStatus('Synced — Live', 'status-sync');
        }
    });
}

// --- Sync playback to Firebase time ---
function syncPlayback(elapsedSeconds) {
    const track = playlist[currentIndex];
    if (!track) return;

    // Ensure track URLs are usable
    normalizeTrackUrls(track);
    audio.src = track.file;

    const playAudio = () => {
        // If duration is available, clamp; otherwise try to set currentTime anyway
        const clamped = Math.max(0, Math.min(elapsedSeconds, audio.duration || elapsedSeconds));
        audio.currentTime = clamped;
        audio.play().catch(handleAutoplayBlocked);
        updateDisplay(track);
    };

    if (audio.readyState >= 2) {
        playAudio();
    } else {
        audio.addEventListener('canplay', playAudio, { once: true });
        // Fallback: try after 1s in case canplay doesn't fire
        setTimeout(playAudio, 1000);
    }
}

// --- Update UI with track info ---
function updateDisplay(track) {
    titleEl.textContent = track.title;
    artistEl.textContent = track.selectedBy || 'Unknown Artist';
    selectorEl.textContent = 'Selected by: ' + (track.selectedBy || 'DJ AutoShuffle');
    // Normalize cover URL if needed before assigning it
    if (track.cover && !track.cover.startsWith('http')) {
        coverEl.src = RAW_BASE + track.cover.replace(/^\/+/, '');
    } else {
        coverEl.src = track.cover;
    }
    console.log('Now playing:', track);
}

// --- Load tracks locally (fallback) ---
function loadTracksLocally() {
    fetch('tracks.json')
        .then(res => res.json())
        .then(tracks => {
            // Normalize relative paths that may still be present in tracks.json
            playlist = shuffle(tracks.map(normalizeTrackUrls));
            currentIndex = 0;
            setStatus('Local mode', 'status-offline');
            playSongLocally();
        })
        .catch(e => console.error('Failed to load tracks.json:', e));
}

// --- Shuffle function ---
function shuffle(list) {
    for (let i = list.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [list[i], list[j]] = [list[j], list[i]];
    }
    return list;
}

// --- Local playback (fallback) ---
function playSongLocally() {
    const track = playlist[currentIndex];
    if (!track) return;

    normalizeTrackUrls(track);
    audio.src = track.file;
    audio.play().catch(handleAutoplayBlocked);
    updateDisplay(track);
}

// If a track object contains relative `file` or `cover` paths, convert them to
// raw.githubusercontent.com URLs so the browser can fetch the bytes directly.
function normalizeTrackUrls(track) {
    if (!track || typeof track !== 'object') return track;

    if (track.file && !track.file.startsWith('http')) {
        // support entries like "music/foo.mp3" or "/music/foo.mp3"
        track.file = RAW_BASE + track.file.replace(/^\/+/, '');
    }

    if (track.cover && !track.cover.startsWith('http')) {
        track.cover = RAW_BASE + track.cover.replace(/^\/+/, '');
    }

    return track;
}

// Handle autoplay-blocked exceptions by asking the user to interact and then
// resuming playback. This improves UX on modern browsers that block autoplay
// with sound until a user gesture occurs.
function handleAutoplayBlocked(err) {
    console.log('Autoplay blocked:', err);
    setStatus('Autoplay blocked — click anywhere to start', 'status-offline');

    const resume = () => {
        audio.play().then(() => {
            setStatus(isSynced ? 'Synced — Live' : 'Local mode', isSynced ? 'status-sync' : 'status-offline');
        }).catch(e => console.log('Play after gesture failed:', e));
        document.removeEventListener('click', resume);
    };

    document.addEventListener('click', resume, { once: true });
}

// --- Move to next song ---
audio.addEventListener('ended', async () => {
    if (isSynced && db) {
        currentIndex = (currentIndex + 1) % playlist.length;
        try {
            await update(ref(db, 'radio/state'), {
                currentTrackIndex: currentIndex,
                startTime: Date.now(),
                lastUpdated: new Date().toISOString()
            });
        } catch (err) {
            console.error('Failed to update Firebase state on ended:', err);
        }
    } else {
        currentIndex = (currentIndex + 1) % playlist.length;
        playSongLocally();
    }
});

// --- Initialize ---
initFirebase();

// --- Force sync helper (for dev/testing) ---
async function forceFirebaseSync() {
    if (!isSynced || !db) {
        console.warn('Firebase not initialized; cannot force sync');
        return;
    }

    try {
        const snapshot = await get(ref(db, 'radio/state'));
        const state = snapshot.val();
        if (state && playlist.length > 0) {
            currentIndex = state.currentTrackIndex || 0;
            const elapsedSeconds = (Date.now() - (state.startTime || Date.now())) / 1000;
            syncPlayback(elapsedSeconds);
            console.log('Force synced to', currentIndex);
        } else {
            console.warn('No radio/state present in Firebase or no tracks loaded');
        }
    } catch (err) {
        console.error('Force sync failed:', err);
    }
}

window.forceFirebaseSync = forceFirebaseSync;

// Attach button listener if present
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('force-sync');
    if (btn) btn.addEventListener('click', () => forceFirebaseSync());
});
