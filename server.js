const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Serve static files
app.use(express.static(path.join(__dirname)));

// Global playback state
let playbackState = {
    currentTrackIndex: 0,
    isPlaying: true,
    startTime: Date.now(),
    tracks: []
};

// Load tracks from tracks.json
try {
    const tracksData = fs.readFileSync(path.join(__dirname, 'tracks.json'), 'utf8');
    playbackState.tracks = JSON.parse(tracksData);
} catch (err) {
    console.error('Failed to load tracks.json:', err);
}

// Broadcast state to all connected clients
function broadcastState() {
    const message = JSON.stringify({
        type: 'state',
        ...playbackState
    });
    
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

// WebSocket connection handling
wss.on('connection', (ws) => {
    console.log('Client connected. Total clients:', wss.clients.size);
    
    // Send current state to newly connected client
    ws.send(JSON.stringify({
        type: 'state',
        ...playbackState
    }));
    
    // Handle messages from clients
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            
            if (data.type === 'next') {
                playbackState.currentTrackIndex = (playbackState.currentTrackIndex + 1) % playbackState.tracks.length;
                playbackState.startTime = Date.now();
                broadcastState();
            } else if (data.type === 'sync') {
                // Client requesting sync
                ws.send(JSON.stringify({
                    type: 'state',
                    ...playbackState
                }));
            }
        } catch (err) {
            console.error('Error handling message:', err);
        }
    });
    
    ws.on('close', () => {
        console.log('Client disconnected. Total clients:', wss.clients.size);
    });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Radio sync server running on http://localhost:${PORT}`);
});
