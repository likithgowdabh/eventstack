// WebSocket functionality for real-time updates

let socket = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 3000;

function initWebSocket(eventId) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/vote/${eventId}`;
    
    try {
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function(event) {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
            showConnectionStatus('connected');
        };
        
        socket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        socket.onclose = function(event) {
            console.log('WebSocket closed:', event.code, event.reason);
            showConnectionStatus('disconnected');
            
            // Attempt to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                setTimeout(() => {
                    reconnectAttempts++;
                    console.log(`Reconnection attempt ${reconnectAttempts}`);
                    initWebSocket(eventId);
                }, reconnectDelay);
            } else {
                showConnectionStatus('failed');
            }
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            showConnectionStatus('error');
        };
        
    } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        showConnectionStatus('failed');
    }
}

function handleWebSocketMessage(data) {
    if (data.type === 'vote_update') {
        updateVoteDisplay(data.votes_by_slot);
    }
}

function updateVoteDisplay(votesBySlot) {
    // Update vote counts and voter avatars for each time slot
    Object.keys(votesBySlot).forEach(slotId => {
        const votes = votesBySlot[slotId];
        
        // Update vote count
        const countElement = document.getElementById(`count-${slotId}`);
        if (countElement) {
            countElement.textContent = `${votes.length} vote${votes.length !== 1 ? 's' : ''}`;
        }
        
        // Update voter avatars
        const votersElement = document.getElementById(`voters-${slotId}`);
        if (votersElement) {
            votersElement.innerHTML = '';
            votes.forEach(vote => {
                const img = document.createElement('img');
                img.src = vote.avatar_url;
                img.alt = vote.username;
                img.title = vote.username;
                img.className = 'w-6 h-6 rounded-full border-2 border-white';
                votersElement.appendChild(img);
            });
        }
        
        // Update vote button state for current user
        const currentUser = getCurrentUser();
        if (currentUser) {
            const voteBtn = document.getElementById(`vote-btn-${slotId}`);
            if (voteBtn) {
                const userVoted = votes.some(vote => vote.username === currentUser.username);
                updateVoteButtonState(voteBtn, userVoted);
            }
        }
    });
    
    // Handle slots with no votes
    const allSlots = document.querySelectorAll('[data-slot-id]');
    allSlots.forEach(slot => {
        const slotId = slot.getAttribute('data-slot-id');
        if (!(slotId in votesBySlot)) {
            const countElement = document.getElementById(`count-${slotId}`);
            const votersElement = document.getElementById(`voters-${slotId}`);
            
            if (countElement) {
                countElement.textContent = '0 votes';
            }
            if (votersElement) {
                votersElement.innerHTML = '';
            }
            
            // Update vote button for current user
            const currentUser = getCurrentUser();
            if (currentUser) {
                const voteBtn = document.getElementById(`vote-btn-${slotId}`);
                if (voteBtn) {
                    updateVoteButtonState(voteBtn, false);
                }
            }
        }
    });
}

function updateVoteButtonState(button, isVoted) {
    if (isVoted) {
        button.className = 'vote-btn px-4 py-2 rounded-md transition-colors bg-github-blue text-white';
        button.innerHTML = '<i class="fas fa-check mr-1"></i>Voted';
    } else {
        button.className = 'vote-btn px-4 py-2 rounded-md transition-colors bg-gray-100 text-gray-700 hover:bg-gray-200';
        button.innerHTML = '<i class="fas fa-plus mr-1"></i>Vote';
    }
}

function getCurrentUser() {
    // Extract current user info from page context
    // This would need to be set by the template
    return window.currentUser || null;
}

function showConnectionStatus(status) {
    // Remove existing status indicators
    const existingStatus = document.getElementById('connection-status');
    if (existingStatus) {
        existingStatus.remove();
    }
    
    let statusConfig = {};
    
    switch (status) {
        case 'connected':
            statusConfig = {
                text: 'Real-time updates active',
                class: 'bg-green-100 text-green-800 border-green-200',
                icon: 'fa-wifi',
                autoHide: true
            };
            break;
        case 'disconnected':
            statusConfig = {
                text: 'Reconnecting...',
                class: 'bg-yellow-100 text-yellow-800 border-yellow-200',
                icon: 'fa-exclamation-triangle',
                autoHide: false
            };
            break;
        case 'error':
            statusConfig = {
                text: 'Connection error',
                class: 'bg-red-100 text-red-800 border-red-200',
                icon: 'fa-exclamation-circle',
                autoHide: false
            };
            break;
        case 'failed':
            statusConfig = {
                text: 'Unable to connect for real-time updates',
                class: 'bg-red-100 text-red-800 border-red-200',
                icon: 'fa-times-circle',
                autoHide: false
            };
            break;
        default:
            return;
    }
    
    // Create status indicator
    const statusElement = document.createElement('div');
    statusElement.id = 'connection-status';
    statusElement.className = `fixed top-20 right-4 z-40 px-3 py-2 rounded-md border text-sm ${statusConfig.class}`;
    statusElement.innerHTML = `
        <div class="flex items-center space-x-2">
            <i class="fas ${statusConfig.icon}"></i>
            <span>${statusConfig.text}</span>
        </div>
    `;
    
    document.body.appendChild(statusElement);
    
    // Auto-hide for success status
    if (statusConfig.autoHide) {
        setTimeout(() => {
            if (statusElement.parentElement) {
                statusElement.remove();
            }
        }, 3000);
    }
}

// Cleanup WebSocket connection when page unloads
window.addEventListener('beforeunload', function() {
    if (socket) {
        socket.close();
    }
});

// Handle page visibility changes to manage connection
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, we might want to close the connection to save resources
        // For now, we'll keep it open for real-time updates
    } else {
        // Page is visible again, ensure connection is active
        if (socket && socket.readyState === WebSocket.CLOSED) {
            // Reconnect if needed
            const eventId = window.location.pathname.split('/').pop();
            if (eventId) {
                initWebSocket(eventId);
            }
        }
    }
});
