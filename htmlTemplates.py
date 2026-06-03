css = '''
<style>
footer {visibility: hidden;}
/* Hide only the Clear Cache option from menu */
[data-testid="stMainMenu"] ul li:last-child {display: none;}

/* Push main content up so fixed bar doesn't cover it */
.main .block-container {
    padding-bottom: 100px !important;
}

/* Hide default streamlit input and button at bottom, we'll use fixed bar */
.fixed-input-bar {
    position: fixed;
    bottom: 0;
    left: 320px; /* sidebar width */
    right: 0;
    background: white;
    padding: 14px 24px;
    border-top: 1px solid #e0e0e0;
    z-index: 999;
    display: flex;
    gap: 10px;
    align-items: center;
    box-shadow: 0 -2px 12px rgba(0,0,0,0.06);
}

.fixed-input-bar input {
    flex: 1;
    padding: 12px 16px;
    border-radius: 24px;
    border: 1.5px solid #d0d0d0;
    font-size: 0.95rem;
    outline: none;
    transition: border 0.2s;
}

.fixed-input-bar input:focus {
    border-color: #667eea;
}

.chat-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 10px 0;
}

.chat-bubble {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    max-width: 85%;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

.chat-bubble.user {
    flex-direction: row-reverse;
    margin-left: auto;
}

.chat-bubble.bot {
    flex-direction: row;
    margin-right: auto;
}

.avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}

.avatar.user-avatar {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
}

.avatar.bot-avatar {
    background: linear-gradient(135deg, #f093fb, #f5576c);
    color: white;
}

.bubble-content {
    padding: 12px 16px;
    border-radius: 18px;
    font-size: 0.95rem;
    line-height: 1.5;
    max-width: 100%;
    word-wrap: break-word;
}

.user .bubble-content {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-bottom-right-radius: 4px;
}

.bot .bubble-content {
    background: #f0f2f6;
    color: #1a1a2e;
    border-bottom-left-radius: 4px;
    border: 1px solid #e0e0e0;
}
</style>
'''

user_template = '''
<div class="chat-bubble user">
    <div class="avatar user-avatar">👤</div>
    <div class="bubble-content">{{MSG}}</div>
</div>
'''

bot_template = '''
<div class="chat-bubble bot">
    <div class="avatar bot-avatar">🤖</div>
    <div class="bubble-content">{{MSG}}</div>
</div>
'''