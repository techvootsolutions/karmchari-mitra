// Modal functions handled by Bootstrap data-attributes
function closeModal() {
    // Legacy support or if needed to close programmatically
    const modalEl = document.getElementById('addCandidateModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) {
        modal.hide();
    }
}

async function bulkUploadResumes() {
    const fileInput = document.getElementById('resumeUpload');
    const statusDiv = document.getElementById('parsingStatus');
    const files = fileInput.files;

    if (files.length === 0) return;

    // Show loading
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `<div style="margin-bottom: 5px;">Starting import of ${files.length} files...</div>`;

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const statusId = `status-${i}`;

        // Append status line
        statusDiv.innerHTML += `<div id="${statusId}" style="margin-bottom: 2px; font-size: 0.8rem;">
            <i class="fas fa-spinner fa-spin"></i> ${file.name}
        </div>`;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/import_resume', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            const statusEl = document.getElementById(statusId);
            if (result.success) {
                statusEl.innerHTML = `<span style="color: green;"><i class="fas fa-check"></i> ${file.name}</span>`;
                successCount++;
            } else {
                statusEl.innerHTML = `<span style="color: red;"><i class="fas fa-times"></i> ${file.name}: ${result.error}</span>`;
                failCount++;
            }
        } catch (error) {
            const statusEl = document.getElementById(statusId);
            statusEl.innerHTML = `<span style="color: red;"><i class="fas fa-exclamation-triangle"></i> ${file.name} Failed</span>`;
            failCount++;
        }
    }

    // Final Summary
    statusDiv.innerHTML += `<div style="margin-top: 10px; font-weight: bold;">
        Done: ${successCount} Imported, ${failCount} Failed.
        <br>Reloading...
    </div>`;

    // Reload after short delay if any success
    if (successCount > 0) {
        setTimeout(() => location.reload(), 2000);
    }
}

// Close modal when clicking outside
window.onclick = function (event) {
    if (event.target == document.getElementById('addModal')) {
        closeModal();
    }
}

async function callCandidate(candidateId) {
    if (!confirm('Are you sure you want to call this candidate with the AI Agent?')) {
        return;
    }

    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = 'Calling...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/make_call', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ candidate_id: candidateId })
        });

        const data = await response.json();

        if (data.success) {
            alert('Call initiated successfully!');
            location.reload();
        } else {
            alert('Failed to initiate call: ' + data.error);
        }
    } catch (error) {
        alert('Error: ' + error);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

async function syncCalls() {
    const btn = event.target;
    // Store original icon/text
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-sync fa-spin"></i>';
    btn.disabled = true;

    try {
        const response = await fetch('/api/sync_calls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            alert(`Sync Complete! Updated ${data.updated} calls.`);
            location.reload();
        } else {
            alert('Sync failed: ' + data.message);
        }
    } catch (error) {
        alert('Error: ' + error);
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

async function exportToSheets() {
    const btn = event.target;
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-file-export fa-spin"></i>';
    btn.disabled = true;

    try {
        const response = await fetch('/api/export_sheets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            alert(data.message);
        } else {
            alert('Export failed: ' + data.error);
        }
    } catch (error) {
        alert('Error: ' + error);
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

async function startCallSession() {
    if (!confirm('This will initiate calls to ALL pending candidates. Are you sure?')) {
        return;
    }

    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/start_queue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.success) {
            alert(`Queue Processed:\nTotal: ${data.results.total}\nInitiated: ${data.results.initiated}\nFailed: ${data.results.failed}`);
            location.reload();
        } else {
            alert('Queue Failed: ' + (data.message || data.error));
        }
    } catch (error) {
        alert('Error: ' + error);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function deleteCandidate(candidateId) {
    if (!confirm('Are you sure you want to delete this candidate? This action cannot be undone.')) {
        return;
    }

    const btn = event.target.closest('button');
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/delete_candidate/${candidateId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            // Optional: Remove row without reload for smoother feel
            // btn.closest('tr').remove();
            // But reload is safer for stats update
            location.reload();
        } else {
            alert('Failed to delete: ' + data.error);
            btn.innerHTML = originalContent;
            btn.disabled = false;
        }
    } catch (error) {
        alert('Error: ' + error);
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

document.getElementById('addForm').onsubmit = async function (e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/add_candidate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            location.reload();
        } else {
            alert('Error adding candidate');
        }
    } catch (error) {
        alert('Error: ' + error);
    }
}
