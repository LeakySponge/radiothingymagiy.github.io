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
        const configRes = await fetch('firebase-config.json');
        const firebaseConfig = await configRes.json();

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
    const stateRef = ref(db, 'radio/state');

    onValue(stateRef, (snapshot) => {
        const state = snapshot.val();
        if (state && state.tracks && state.tracks.length > 0) {
            // Always adopt the server playlist and resync playback.
            playlist = state.tracks;
            currentIndex = state.currentTrackIndex || 0;
            const elapsedSeconds = (Date.now() - (state.startTime || Date.now())) / 1000;
            syncPlayback(elapsedSeconds);
            setStatus('Synced — Live', 'status-sync');
        }
    });

    // Load initial tracks (will call initializeFirebaseState when synced)
    loadTracksLocally();
}

// --- Sync playback to Firebase time ---
function syncPlayback(elapsedSeconds) {
    const track = playlist[currentIndex];
    if (!track) return;

    audio.src = track.file;

    const playAudio = () => {
        // If duration is available, clamp; otherwise try to set currentTime anyway
        const clamped = Math.max(0, Math.min(elapsedSeconds, audio.duration || elapsedSeconds));
        audio.currentTime = clamped;
        audio.play().catch(e => console.log('Autoplay blocked:', e));
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
    coverEl.src = track.cover;
    console.log('Now playing:', track);
}

// --- Load tracks locally ---
function loadTracksLocally() {
    fetch('tracks.json')
        .then(res => res.json())
        .then(tracks => {
            if (isSynced) {
                // Adopt server order; ensure DB state exists
                playlist = tracks;
                initializeFirebaseState(tracks);
            } else {
                playlist = shuffle(tracks);
                currentIndex = 0;
                setStatus('Local mode', 'status-offline');
                playSongLocally();
            }
        })
        .catch(e => console.error('Failed to load tracks.json:', e));
}

// --- Initialize Firebase state if empty ---
async function initializeFirebaseState(tracks) {
    const stateRef = ref(db, 'radio/state');
    try {
        const snapshot = await get(stateRef);
        if (!snapshot.exists()) {
            await set(stateRef, {
                currentTrackIndex: 0,
                tracks: tracks,
                startTime: Date.now(),
                lastUpdated: new Date().toISOString()
            });
        }
    } catch (err) {
        console.error('Failed to initialize Firebase state:', err);
    }
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

    audio.src = track.file;
    audio.play().catch(e => console.log('Autoplay blocked:', e));
    updateDisplay(track);
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
        if (state && state.tracks) {
            playlist = state.tracks;
            currentIndex = state.currentTrackIndex || 0;
            const elapsedSeconds = (Date.now() - (state.startTime || Date.now())) / 1000;
            syncPlayback(elapsedSeconds);
            console.log('Force synced to', currentIndex);
        } else {
            console.warn('No radio/state present in Firebase');
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
