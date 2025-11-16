let playlist = [];
let index = 0;
const player = document.getElementById("player");

function updateTime() {
    const now = new Date();
    document.getElementById("time").innerText =
        now.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
}
setInterval(updateTime, 1000);
updateTime();

function shuffleNext() {
    let newIndex = index;
    while (newIndex === index && playlist.length > 1) {
        newIndex = Math.floor(Math.random() * playlist.length);
    }
    loadTrack(newIndex);
    player.play();
}

function loadTrack(i) {
    index = i;
    const t = playlist[i];

    document.getElementById("trackName").textContent = t.title;
    document.getElementById("selectedBy").textContent = "Selected by: " + t.selectedBy;
    document.getElementById("albumArt").src = t.cover;

    player.src = t.file;
}

function buildTrackList() {
    let container = document.getElementById("trackList");
    container.innerHTML = "";
    playlist.forEach((t, i) => {
        let card = document.createElement("div");
        card.className = "track-card";
        card.onclick = () => { loadTrack(i); player.play(); };

        card.innerHTML = `
            <img src="${t.cover}">
            <div>${t.title}</div>
        `;
        container.appendChild(card);
    });
}

fetch("tracks.json")
    .then(r => r.json())
    .then(data => {
        playlist = data;
        buildTrackList();
        loadTrack(0);
    });

player.onended = shuffleNext;
