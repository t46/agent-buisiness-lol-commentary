/**
 * LoL AI Commentary Overlay — WebSocket client with typing animation.
 */

const FADE_OUT_DELAY = 8000;     // ms before fade-out starts
const TYPING_SPEED = 30;         // ms per character
const RECONNECT_BASE = 1000;     // ms initial reconnect delay
const RECONNECT_MAX = 10000;     // ms max reconnect delay

let ws = null;
let reconnectDelay = RECONNECT_BASE;
let fadeTimer = null;
let typingTimer = null;
let persona = null;

// DOM elements
const commentator = document.getElementById('commentator');
const avatarImg = document.getElementById('avatar');
const avatarContainer = document.getElementById('avatar-container');
const personaName = document.getElementById('persona-name');
const commentaryText = document.getElementById('commentary-text');
const cursor = document.getElementById('cursor');
const statusEl = document.getElementById('connection-status');

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/ws`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    reconnectDelay = RECONNECT_BASE;
    statusEl.textContent = 'Connected';
    statusEl.className = 'connected';
    // Hide status after 3 seconds
    setTimeout(() => { statusEl.style.opacity = '0'; }, 3000);
  };

  ws.onclose = () => {
    statusEl.textContent = 'Reconnecting...';
    statusEl.className = 'disconnected';
    statusEl.style.opacity = '0.7';
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws.close();
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleMessage(msg);
  };
}

function scheduleReconnect() {
  setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 1.5, RECONNECT_MAX);
    connect();
  }, reconnectDelay);
}

function handleMessage(msg) {
  switch (msg.type) {
    case 'init':
      handleInit(msg);
      break;
    case 'state':
      // State updates can be used for HUD display if needed
      break;
    case 'commentary':
      handleCommentary(msg.data);
      break;
  }
}

function handleInit(msg) {
  persona = msg.persona;
  if (persona) {
    avatarImg.src = persona.avatar;
    personaName.textContent = persona.name;
  }

  // Embed YouTube video if video_id is provided
  if (msg.video_id) {
    embedVideo(msg.video_id, msg.start_time || 0);
  }

  // Show most recent history item if available
  if (msg.history && msg.history.length > 0) {
    const last = msg.history[msg.history.length - 1];
    showCommentary(last.message, last.excitement || 'mid');
  }
}

function embedVideo(videoId, startTime) {
  const container = document.getElementById('video-background');
  const iframe = document.createElement('iframe');
  iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&start=${startTime}&mute=0&controls=1&modestbranding=1&rel=0`;
  iframe.allow = 'autoplay; encrypted-media';
  iframe.allowFullscreen = true;
  container.appendChild(iframe);
  container.style.display = 'block';
  document.body.classList.add('has-video');
}

function handleCommentary(data) {
  const { message, excitement } = data;
  showCommentary(message, excitement || 'mid');
}

function showCommentary(message, excitement) {
  // Cancel any pending fade or typing
  clearTimeout(fadeTimer);
  clearTimeout(typingTimer);

  // Reset state
  commentator.classList.remove('hidden', 'fading');
  commentator.classList.add('visible');
  commentaryText.textContent = '';
  cursor.classList.remove('hidden');
  cursor.classList.add('blink');

  // Set excitement class on overlay
  const overlay = document.getElementById('overlay');
  overlay.className = `excitement-${excitement}`;

  // Avatar bounce for high/hype
  if (excitement === 'high' || excitement === 'hype') {
    avatarContainer.classList.remove('bounce');
    // Force reflow for re-triggering animation
    void avatarContainer.offsetWidth;
    avatarContainer.classList.add('bounce');
  }

  // Shake for hype
  if (excitement === 'hype') {
    commentator.classList.add('shake');
    setTimeout(() => commentator.classList.remove('shake'), 600);
  }

  // Typing animation
  typeText(message, 0);
}

function typeText(message, index) {
  if (index >= message.length) {
    // Typing complete
    cursor.classList.add('hidden');
    scheduleFadeOut();
    return;
  }

  commentaryText.textContent = message.substring(0, index + 1);
  typingTimer = setTimeout(() => typeText(message, index + 1), TYPING_SPEED);
}

function scheduleFadeOut() {
  fadeTimer = setTimeout(() => {
    commentator.classList.add('fading');
    // After fade animation completes, hide
    setTimeout(() => {
      commentator.classList.remove('visible', 'fading');
      commentator.classList.add('hidden');
    }, 2000);
  }, FADE_OUT_DELAY);
}

// Start connection
connect();
