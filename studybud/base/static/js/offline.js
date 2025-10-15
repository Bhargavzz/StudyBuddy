/**
 * Offline Message Queue System for StudyBuddy
 * 
 * Behavior:
 * - Online: Message rendered immediately (optimistic) → Posted to Django → DB saves → Supabase notifies others
 * - Offline: Message rendered immediately → Stored in localStorage → When online, syncs with server
 */

class OfflineMessageQueue {
    constructor(roomId, currentUserId, currentUsername, currentAvatar) {
        this.roomId = roomId;
        this.currentUserId = currentUserId;
        this.currentUsername = currentUsername;
        this.currentAvatar = currentAvatar;
        this.storageKey = `offline_messages_${roomId}`;
        
        // Check network status
        this.isOnline = navigator.onLine;
        this.setupNetworkListeners();
        
        // Initialize sync when page loads if online
        if (this.isOnline) {
            this.syncOfflineMessages();
        }
    }
    
    setupNetworkListeners() {
        window.addEventListener('online', () => {
            console.log('🟢 Network is back online');
            this.isOnline = true;
            this.syncOfflineMessages();
        });
        
        window.addEventListener('offline', () => {
            console.log('🔴 Network is offline');
            this.isOnline = false;
        });
    }
    
    generateClientId() {
        return 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    getCurrentTimestamp() {
        return new Date().toISOString();
    }
    
    async sendMessage(messageText) {
        const clientId = this.generateClientId();
        const messageData = {
            client_id: clientId,
            body: messageText,
            timestamp: this.getCurrentTimestamp(),
            user_id: this.currentUserId,
            username: this.currentUsername,
            avatar_url: this.currentAvatar
        };
        
        if (this.isOnline) {
            // Online: Send to Django via AJAX (no page reload, no optimistic message)
            try {
                await this.postToDjango(messageText);
                // Message will appear via Supabase realtime - don't add optimistic message
            } catch (error) {
                console.log('Send failed, adding to offline queue:', error);
                // If send fails, show optimistic message and queue it
                this.addMessageToDOM(messageData, true);
                this.addToOfflineQueue(messageData);
            }
        } else {
            // Offline: Show with offline styling and add to queue
            this.addMessageToDOM(messageData, true); // Show as "sending..."
            this.addToOfflineQueue(messageData);
        }
    }
    
    async postToDjango(messageText) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        try {
            const response = await fetch(`/room/${this.roomId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'  // This tells Django it's AJAX
                },
                body: new URLSearchParams({ 
                    body: messageText,
                    csrfmiddlewaretoken: csrfToken
                })
            });
            
            if (response.ok) {
                console.log('✅ Message posted to Django successfully');
                return true;
            } else {
                console.error('❌ Django post failed with status:', response.status);
                return false;
            }
        } catch (error) {
            console.error('❌ Error posting to Django:', error);
            return false;
        }
    }
    
    addToOfflineQueue(messageData) {
        const queue = this.getOfflineQueue();
        queue.push(messageData);
        localStorage.setItem(this.storageKey, JSON.stringify(queue));
        console.log('📦 Message added to offline queue:', messageData.client_id);
    }
    
    getOfflineQueue() {
        const stored = localStorage.getItem(this.storageKey);
        return stored ? JSON.parse(stored) : [];
    }
    
    clearOfflineQueue() {
        localStorage.removeItem(this.storageKey);
    }
    
    async syncOfflineMessages() {
        const queue = this.getOfflineQueue();
        if (queue.length === 0) return;
        
        console.log(`🔄 Syncing ${queue.length} offline messages...`);
        
        // New approach: Remove optimistic messages and send each one through normal Django flow
        // This ensures Supabase realtime works properly
        
        for (const messageData of queue) {
            try {
                // Remove the optimistic message from DOM
                const optimisticElement = document.querySelector(`[data-client-id="${messageData.client_id}"]`);
                if (optimisticElement) {
                    optimisticElement.remove();
                }
                
                // Send through normal Django flow (this will trigger Supabase realtime)
                await this.postToDjango(messageData.body);
                console.log('✅ Message synced:', messageData.client_id);
                
                // Small delay to avoid overwhelming the server
                await new Promise(resolve => setTimeout(resolve, 100));
                
            } catch (error) {
                console.error('❌ Error syncing message:', messageData.client_id, error);
                // If sync fails, keep the optimistic message but mark it as failed
                const optimisticElement = document.querySelector(`[data-client-id="${messageData.client_id}"]`);
                if (optimisticElement) {
                    optimisticElement.style.opacity = '0.5';
                    const dateElement = optimisticElement.querySelector('.thread__date');
                    if (dateElement) {
                        dateElement.textContent = 'Failed to send';
                        dateElement.style.color = 'red';
                    }
                }
                return; // Stop syncing if one message fails
            }
        }
        
        // Clear the queue only if all messages were successfully synced
        this.clearOfflineQueue();
        console.log('🧹 All offline messages synced and queue cleared');
    }
    
    addMessageToDOM(messageData, isOptimistic = false) {
        const threadsContainer = document.getElementById('threadsContainer');
        if (!threadsContainer) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = 'thread';
        messageElement.setAttribute('data-client-id', messageData.client_id);
        
        if (isOptimistic) {
            messageElement.classList.add('thread--optimistic');
        }
        
        messageElement.innerHTML = `
            <div class="thread__top">
                <div class="thread__author">
                    <a href="/user-profile/${messageData.user_id}" class="thread__authorInfo">
                        <div class="avatar avatar--small">
                            <img src="${messageData.avatar_url || 'https://avatar.iran.liara.run/public/17'}" 
                                 onerror="this.onerror=null;this.src='https://avatar.iran.liara.run/public/17';" />
                        </div>
                        <span>@${messageData.username}</span>
                    </a>
                    <span class="thread__date">
                        ${isOptimistic ? 'Sending...' : 'just now'}
                    </span>
                </div>
            </div>
            <div class="thread__details">
                ${messageData.body}
            </div>
        `;
        
        // Add to bottom (newest at bottom)
        threadsContainer.appendChild(messageElement);
        
        // Auto-scroll to show new message
        threadsContainer.scrollTop = threadsContainer.scrollHeight;
    }
}

// Global function to be called from room.html
window.__sb_addMessageFromRealtime = function(messageData) {
    // Add ALL messages from Supabase realtime (including your own)
    if (window.__offline_queue) {
        window.__offline_queue.addMessageToDOM(messageData, false);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for room data to be available
    setTimeout(() => {
        if (typeof window.__ROOM_ID__ !== 'undefined' && 
            typeof window.__CURRENT_USER_ID__ !== 'undefined') {
            
            window.__offline_queue = new OfflineMessageQueue(
                window.__ROOM_ID__,
                window.__CURRENT_USER_ID__,
                window.__CURRENT_USERNAME__,
                window.__CURRENT_AVATAR__
            );
            
            // ALWAYS override form to prevent page reload
            const messageForm = document.getElementById('messageForm');
            const messageInput = document.getElementById('messageInput');
            
            if (messageForm && messageInput) {
                messageForm.addEventListener('submit', function(e) {
                    e.preventDefault(); // Always prevent default form submission
                    
                    const message = messageInput.value.trim();
                    if (!message) return;
                    
                    // Use offline queue system (it handles online/offline automatically)
                    window.__offline_queue.sendMessage(message);
                    
                    // Clear input
                    messageInput.value = '';
                });
            }
        }
    }, 100);
});
