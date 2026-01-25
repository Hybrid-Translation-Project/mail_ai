// app/static/js/writer.js

const draftIdInput = document.getElementById('draftId');
const toEmailInput = document.getElementById('toEmail');
const senderEmailInput = document.getElementById('senderEmail');
const subjectInput = document.getElementById('subject');
const bodyInput = document.getElementById('mailBody');
const statusSpan = document.getElementById('saveStatus');
const btnGenerate = document.getElementById('btnGenerate');
const aiPrompt = document.getElementById('aiPrompt');
const btnPreSend = document.getElementById('btnPreSend'); // The button that opens modal
const btnConfirmSend = document.getElementById('btnConfirmSend'); // The button inside modal

// Modal Instance (Bootstrap)
let confirmModal;

let saveTimeout;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Modal
    const modalElement = document.getElementById('confirmSendModal');
    if (modalElement) {
        confirmModal = new bootstrap.Modal(modalElement);
    }

    // 1. Add listeners to all inputs for Auto-Save
    const inputs = [toEmailInput, subjectInput, bodyInput];
    inputs.forEach(input => {
        if(input) {
            input.addEventListener('input', () => {
                showStatus('writing');
                clearTimeout(saveTimeout);
                // Auto-save after 1 second of inactivity
                saveTimeout = setTimeout(() => saveWriterDraft(false), 1000);
            });
        }
    });

    // 2. AI Generate Button Listener
    if(btnGenerate) {
        btnGenerate.addEventListener('click', generateDraft);
    }

    // 3. "Send Mail" Button -> Opens Confirmation Modal
    if(btnPreSend) {
        btnPreSend.addEventListener('click', openConfirmModal);
    }

    // 4. "Yes, Send It" Button -> Actually submits the form
    if(btnConfirmSend) {
        btnConfirmSend.addEventListener('click', submitForm);
    }
});

// --- STATUS INDICATOR ---
function showStatus(state) {
    if (!statusSpan) return;
    
    if (state === 'writing') {
        statusSpan.innerText = '✍️ Writing...';
        statusSpan.className = 'save-status saving';
    } else if (state === 'saving') {
        statusSpan.innerText = '💾 Saving...';
        statusSpan.className = 'save-status saving';
    } else if (state === 'saved') {
        statusSpan.innerText = '✅ Saved';
        statusSpan.className = 'save-status saved';
    } else if (state === 'error') {
        statusSpan.innerText = '❌ Save Error';
        statusSpan.className = 'save-status error';
    }
}

// --- SAVE FUNCTION ---
// isManual: Was it triggered by a button click?
async function saveWriterDraft(isManual = false) {
    // Don't save empty drafts
    if (!subjectInput.value && !bodyInput.value) return;

    showStatus('saving');

    const payload = {
        draft_id: draftIdInput.value || null,
        sender_email: senderEmailInput.value,
        to_email: toEmailInput.value,
        subject: subjectInput.value,
        body: bodyInput.value
    };

    try {
        const response = await fetch('/save-writer-draft', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.status === 'success') {
            showStatus('saved');
            
            // Update the hidden input with the new ID so subsequent saves are UPDATES
            if (data.draft_id) {
                draftIdInput.value = data.draft_id;
            }

            if (isManual) {
                // Clear the "Saved" message after 3 seconds if manually clicked
                setTimeout(() => showStatus(''), 3000); 
            }
        } else {
            showStatus('error');
            console.error('Save Error:', data.message);
        }
    } catch (error) {
        showStatus('error');
        console.error('Connection Error:', error);
    }
}

// Manual Save Trigger (called from HTML)
function manualSave(showNotification = false) {
    clearTimeout(saveTimeout);
    saveWriterDraft(showNotification);
}

// --- AI GENERATION ---
async function generateDraft() {
    const prompt = aiPrompt.value;
    if (!prompt) {
        alert("Please enter instructions for the AI!");
        return;
    }

    // Loading State
    const originalBtnText = btnGenerate.innerText;
    btnGenerate.disabled = true;
    btnGenerate.innerText = "⏳ Generating...";
    bodyInput.style.opacity = "0.5";

    try {
        const formData = new FormData();
        formData.append('prompt', prompt);

        const response = await fetch('/ui/writer/generate', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.draft) {
            // Clean up quotes if AI adds them
            let cleanText = data.draft.replace(/^"|"$/g, '');
            
            // Set text to body
            bodyInput.value = cleanText;
            
            // Save immediately
            saveWriterDraft();
        } else {
            alert("Error generating draft.");
        }

    } catch (error) {
        console.error(error);
        alert("Connection error.");
    } finally {
        // Reset State
        btnGenerate.disabled = false;
        btnGenerate.innerText = originalBtnText;
        bodyInput.style.opacity = "1";
    }
}

// --- MODAL & SENDING LOGIC ---

function openConfirmModal() {
    // 1. Validation: Check if fields are filled
    if (!toEmailInput.value || !subjectInput.value) {
        alert("Please fill in the Recipient and Subject fields.");
        return;
    }

    // 2. Populate Modal Data
    document.getElementById('confirmTo').innerText = toEmailInput.value;
    document.getElementById('confirmSubject').innerText = subjectInput.value;

    // 3. Show Modal
    confirmModal.show();
}

function submitForm() {
    // Submit the real form
    document.getElementById('mailForm').submit();
}

// --- VOICE COMMAND HANDLERS (Called by voice.js) ---

// 1. Clear the active field
function handleVoiceClear(targetId) {
    const target = document.getElementById(targetId);
    if (target) {
        target.value = ''; // Clear text
        
        // Show visual feedback
        const originalPlaceholder = target.placeholder;
        target.placeholder = "🗑️ Cleared...";
        setTimeout(() => target.placeholder = originalPlaceholder, 1500);
    }
}

// 2. Trigger AI Generation via Voice
function handleVoiceGenerate() {
    if (aiPrompt.value.trim().length > 0) {
        generateDraft();
    }
}

// 3. Open Confirmation Modal via Voice
function handleVoiceSend() {
    openConfirmModal();
}

// 4. Confirm Sending via Voice (When modal is open)
function handleVoiceConfirm() {
    // Only work if modal is actually open
    const modalEl = document.getElementById('confirmSendModal');
    if (modalEl.classList.contains('show')) {
        submitForm();
    }
}